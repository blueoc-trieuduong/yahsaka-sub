from sqlmodel import Session

from app.core.security import verify_password
from app.models.models import User
from app.services.users import UserServices


class LoginServices:
    def authenticate(*, session: Session, email: str, password: str) -> User | None:
        db_user = UserServices.get_user_by_email(session=session, email=email)
        if not db_user:
            return None
        if not verify_password(password, db_user.hashed_password):
            return None
        return db_user
