from datetime import datetime

from sqlmodel import Field, SQLModel


class OrgBase(SQLModel):
    name: str = Field(max_length=255)
    phone_number: str = Field(max_length=255)
    email: str = Field(max_length=255)
    industry: str = Field(max_length=255)
    company_prefix: str = Field(unique=True, max_length=25)
    country: str = Field(max_length=255)
    address: str | None = Field(default=None, max_length=255, nullable=True)
    tax_code: str | None = Field(default=None, max_length=255, nullable=True)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)


class OrgCreate(SQLModel):
    name: str = Field(max_length=255)
    phone_number: str = Field(max_length=255)
    email: str = Field(max_length=255)
    industry: str = Field(max_length=255)
    company_prefix: str = Field(unique=True, max_length=25)
    country: str = Field(max_length=255)
    address: str | None = Field(default=None, max_length=255, nullable=True)
    tax_code: str | None = Field(default=None, max_length=255, nullable=True)


class OrgUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    company_prefix: str | None = Field(default=None, max_length=25)
    country: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    tax_code: str | None = Field(default=None, max_length=255)


class OrgPublic(OrgBase):
    id: int


class TimesheetOrgCreate:
    organization_id: int = Field(gt=0)
    organization_name: str = Field(max_length=255)
    phone_number: str = Field(max_length=255)
    email: str = Field(max_length=255)
    industry: str = Field(max_length=255)
    company_prefix: str = Field(unique=True, max_length=25)
    country: str = Field(max_length=255)
    address: str | None = Field(default=None, max_length=255, nullable=True)
    tax_code: str | None = Field(default=None, max_length=255, nullable=True)
    max_employees: int = Field(gt=0)
    admin_first_name: str = Field(default=None, max_length=255, nullable=True)
    admin_last_name: str = Field(default=None, max_length=255, nullable=True)
    admin_email: str = Field(default=None, max_length=255, nullable=True)
    password: str = Field(default=None, max_length=255, nullable=True)
    password_confirmation: str = Field(default=None, max_length=255, nullable=True)


class TimesheetOrgUpdate:
    organization_name: str = Field(max_length=255)
    phone_number: str = Field(max_length=255)
    email: str = Field(max_length=255)
    industry: str = Field(max_length=255)
    company_prefix: str = Field(unique=True, max_length=25)
    country: str = Field(max_length=255)
    address: str | None = Field(default=None, max_length=255, nullable=True)
    tax_code: str | None = Field(default=None, max_length=255, nullable=True)
    max_employees: int = Field(gt=0)
