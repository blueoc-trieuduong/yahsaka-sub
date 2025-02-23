from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.users import UserPublic, UserRegister


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class UserToken(Token):
    user: UserPublic


class TokenPayload(SQLModel):
    sub: str | UserRegister | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


class VerifyEmailPayload(SQLModel):
    token: str


class EmailPayload(SQLModel):
    email: EmailStr
