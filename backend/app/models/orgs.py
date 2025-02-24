import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class OrgBase(SQLModel):
    name: str = Field(max_length=255)
    slug: str = Field(unique=True, max_length=255)
    company_prefix: str = Field(unique=True, max_length=25)
    country: str = Field(max_length=255)
    address: str | None = Field(default=None, max_length=255, nullable=True)
    tax_code: str | None = Field(default=None, max_length=255, nullable=True)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)


class OrgCreate(SQLModel):
    name: str = Field(max_length=255)
    slug: str = Field(max_length=255)
    company_prefix: str = Field(max_length=255)
    country: str = Field(max_length=255)


class OrgUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    company_prefix: str | None = Field(default=None, max_length=25)
    country: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    tax_code: str | None = Field(default=None, max_length=255)


class OrgPublic(OrgBase):
    id: uuid.UUID


class OrgInvitation(SQLModel):
    email: EmailStr
