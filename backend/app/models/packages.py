import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class PackageBase(SQLModel):
    title: str = Field(max_length=255)
    description: str | None = Field(max_length=500, nullable=True)
    stripe_product_id: str = Field(max_length=255)
    stripe_price_id: str = Field(max_length=255)
    price: int = Field(gt=0)
    max_workspaces: int = Field(gt=0)
    max_employees: int = Field(gt=0)
    is_active: bool = Field(default=True)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)


class PackagePublic(PackageBase):
    id: uuid.UUID
