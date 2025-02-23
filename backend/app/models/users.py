import uuid
from datetime import datetime
from enum import Enum

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.orgs import OrgCreate, OrgPublic


class Roles(str, Enum):
    OWNER = "Owner"
    MEMBER = "Member"


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    phone_number: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    first_name: str = Field(max_length=255)
    last_name: str = Field(max_length=255)
    role: str = Field(max_length=255, default=Roles.OWNER.value)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)


class UserCreate(SQLModel):
    email: EmailStr = Field(max_length=255)
    phone_number: str = Field(max_length=255)
    first_name: str = Field(max_length=255)
    last_name: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    role: str = Field(max_length=255, default=Roles.OWNER.value)


class UserRegister(SQLModel):
    user: UserCreate
    org: OrgCreate


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class UserDetails(SQLModel):
    user: UserPublic
    org: OrgPublic
