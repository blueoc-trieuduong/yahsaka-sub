import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.security import (
    create_jwt_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.common import (
    EmailPayload,
    InviteOrgPayload,
    Message,
    VerifyEmailPayload,
)
from app.models.models import Org, User
from app.models.users import (
    InviteOrgTokenPayload,
    JoinOrgPayload,
    Roles,
    UpdatePassword,
    UserDetails,
    UserProfileUpdate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
)
from app.services.users import UserServices
from app.utils import (
    generate_email_verify_email,
    generate_invite_org_email,
    send_email,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()

    return UsersPublic(data=users, count=count)


@router.put("/me", response_model=UserDetails)
def update_user_me(
    *, session: SessionDep, user_in: UserProfileUpdate, current_user: CurrentUser
) -> UserDetails:
    """
    Update own user and own org.
    """
    user_update = user_in.user

    if user_update and user_update.phone_number:
        existing_user = session.exec(
            select(User).where(User.phone_number == user_update.phone_number)
        ).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this phone number already exists"
            )
    user_data = user_update.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)

    if current_user.role == Roles.OWNER:
        org_update = user_in.org
        if org_update:
            if org_update.slug:
                existing_org = session.exec(
                    select(Org).where(Org.slug == org_update.slug)
                ).first()
                if existing_org and existing_org.id != current_user.org_id:
                    raise HTTPException(
                        status_code=409, detail="Org with this slug already exists"
                    )
            if org_update.company_prefix:
                existing_org = session.exec(
                    select(Org).where(Org.company_prefix == org_update.company_prefix)
                ).first()
                if existing_org and existing_org.id != current_user.org_id:
                    raise HTTPException(
                        status_code=409, detail="Org with this prefix already exists"
                    )
            org_data = org_update.model_dump(exclude_unset=True)
            current_user.org.sqlmodel_update(org_data)
            session.add(current_user.org)

    session.commit()
    session.refresh(current_user)
    return UserDetails.model_validate({"user": current_user, "org": current_user.org})


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.get("/me/details", response_model=UserDetails)
def read_user_details(current_user: CurrentUser) -> Any:
    """
    Get user details, contains user and org.
    """
    return UserDetails.model_validate({"user": current_user, "org": current_user.org})


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Message:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/check-email", response_model=Message)
def check_email(session: SessionDep, payload: EmailPayload) -> Message:
    """
    Check existed email when user registers to the system
    """
    user = UserServices.get_user_by_email(session=session, email=payload.email)
    if user:
        raise HTTPException(
            status_code=409,
            detail="The user with this email already exists in the system",
        )
    return Message(message="Email is valid")


@router.post("/verify-email", response_model=UserPublic)
def verify_email(session: SessionDep, payload: VerifyEmailPayload) -> UserPublic:
    """
    Verify email after user registers to the system
    """
    user_register = UserServices.verify_email_token(
        session=session, token=payload.token
    )
    user = UserServices.register_user(session=session, user_register=user_register)
    return user


@router.post("/register")
def register_user(session: SessionDep, payload: UserRegister) -> Message:
    """
    Register user by sending email verfification
    """
    UserServices.check_register_user(session=session, user_register=payload)

    verify_token = create_jwt_token(
        payload=payload.model_dump_json(),
        expires_delta=timedelta(hours=settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS),
    )
    email_data = generate_email_verify_email(
        name=payload.user.first_name, token=verify_token
    )
    send_email(
        email_to=payload.user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Email verification link sent")


@router.post("/join-org", response_model=UserPublic)
def join_org(
    session: SessionDep,
    payload: JoinOrgPayload,
) -> UserPublic:
    """
    User join org by token and register to the system
    """
    token_data = decode_token(token=payload.token)
    invite_org_payload = InviteOrgTokenPayload.model_validate_json(token_data.sub)
    org_id = invite_org_payload.org_id
    email = invite_org_payload.email

    user = UserServices.get_user_by_email(session=session, email=email)

    if user:
        if user.org_id == org_id:
            raise HTTPException(
                status_code=400,
                detail="The user is already in this org",
            )
        raise HTTPException(
            status_code=400,
            detail="The user already has an org",
        )
    user_obj = User.model_validate(
        payload.user,
        update={
            "email": email,
            "password": get_password_hash(payload.user.password),
            "org_id": org_id,
            "role": Roles.MEMBER.value,
        },
    )
    session.add(user_obj)
    session.commit()
    session.refresh(user_obj)

    return UserPublic.model_validate(user_obj)


@router.post("/invite-org/{org_id}", response_model=Message)
def invite_org(
    session: SessionDep,
    org_id: uuid.UUID,
    current_user: CurrentUser,
    payload: InviteOrgPayload,
) -> Message:
    """
    Invite org by sending email to user
    """
    if current_user.org_id != org_id or current_user.role != Roles.OWNER.value:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges to invite to this org",
        )

    user = UserServices.get_user_by_email(session=session, email=payload.email)

    if user:
        if user.org_id == org_id:
            raise HTTPException(
                status_code=400,
                detail="The user is already in this org",
            )
        raise HTTPException(
            status_code=400,
            detail="The user already has an org",
        )

    verify_token = create_jwt_token(
        payload=InviteOrgTokenPayload(
            email=payload.email, org_id=org_id
        ).model_dump_json(),
        expires_delta=timedelta(hours=settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS),
    )
    email_data = generate_invite_org_email(
        org_name=current_user.org.name, token=verify_token
    )

    send_email(
        email_to=payload.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Org invitation email sent")


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = UserServices.get_user_by_email(
            session=session, email=user_in.email
        )
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = UserServices.update_user(
        session=session, db_user=db_user, user_in=user_in
    )
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
