from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, SQLModel, select

from app.core.security import decode_token, get_password_hash
from app.models.models import Org, User
from app.models.users import Roles, UserPublic, UserRegister, UserUpdate


class UserServices:
    def register_user(*, session: Session, user_register: UserRegister) -> UserPublic:
        UserServices.check_register_user(session=session, user_register=user_register)
        try:
            org_obj = Org.model_validate(user_register.org)
            session.add(org_obj)
            user_obj = User.model_validate(
                user_register.user,
                update={
                    "password": get_password_hash(user_register.user.password),
                    "org_id": org_obj.id,
                    "role": Roles.OWNER.value,
                },
            )
            session.add(user_obj)
            session.commit()
            session.refresh(org_obj, user_obj)
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register: {str(e)}",
            )
        return UserPublic.model_validate(user_obj)

    def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
        user_data = user_in.model_dump(exclude_unset=True)
        extra_data = {}
        if "password" in user_data:
            password = user_data["password"]
            hashed_password = get_password_hash(password)
            extra_data["hashed_password"] = hashed_password
        db_user.sqlmodel_update(user_data, update=extra_data)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user

    def get_user_by_email(*, session: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        session_user = session.exec(statement).first()
        return session_user

    def verify_email_token(*, session: Session, token: str) -> UserRegister:
        token_data = decode_token(token=token)
        user_register = UserRegister.model_validate_json(token_data.sub)
        user = UserServices.get_user_by_email(
            session=session, email=user_register.user.email
        )
        if user:
            raise HTTPException(
                status_code=409,
                detail="The user with this email already exists in the system",
            )
        return user_register

    def check_existing_entity(
        *,
        session: Session,
        model: SQLModel,
        attribute: str,
        value: Any,
        detail_message: str,
    ):
        existing_entity = session.exec(
            select(model).where(getattr(model, attribute) == value)
        ).first()
        if existing_entity:
            raise HTTPException(status_code=409, detail=detail_message)

    def check_register_user(*, session: Session, user_register: UserRegister) -> None:
        UserServices.check_existing_entity(
            session=session,
            model=User,
            attribute="email",
            value=user_register.user.email,
            detail_message="The user with this email already exists in the system",
        )

        UserServices.check_existing_entity(
            session=session,
            model=User,
            attribute="phone_number",
            value=user_register.user.phone_number,
            detail_message="User with this phone number already exists",
        )

        UserServices.check_existing_entity(
            session=session,
            model=Org,
            attribute="company_prefix",
            value=user_register.org.company_prefix,
            detail_message="Org with this prefix already exists",
        )
