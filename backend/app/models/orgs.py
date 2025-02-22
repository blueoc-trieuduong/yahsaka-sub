import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class OrgBase(SQLModel):
    name: str = Field(max_length=255)
    slug: str = Field(max_length=255)
    company_prefix: str = Field(max_length=255)
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


class OrgPublic(OrgBase):
    id: uuid.UUID
