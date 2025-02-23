from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class PackageBase(SQLModel):
    title: str = Field(max_length=255)
    description: str | None = Field(max_length=500, nullable=True)
    stripe_product_id: str = Field(max_length=255)
    stripe_price_id: str = Field(max_length=255)
    price: int = Field(gt=0)
    max_workplaces: int = Field(gt=0)
    max_employees: int = Field(gt=0)
    is_active: bool = Field(default=True)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)


class PackagePublic(PackageBase):
    id: UUID


class PackageCreate(SQLModel):
    title: str = Field(max_length=255)
    description: str | None = Field(max_length=500, nullable=True)
    price: int = Field(gt=0)
    max_workplaces: int = Field(gt=0)
    max_employees: int = Field(gt=0)
    is_active: bool = Field(default=True)


class PackagesPublic(SQLModel):
    data: list[PackagePublic]
    count: int
