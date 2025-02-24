from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.models.packages import PackagePublic


class Status(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    CANCELED = "canceled"
    UPGRADED = "upgraded"
    DOWNGRADED = "downgraded"
    EXPIRED = "expired"


class SubscriptionBase(SQLModel):
    stripe_sub_id: str | None = Field(max_length=255, nullable=True)
    status: str = Field(default=Status.ACTIVE)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    unsubscribe_at: datetime | None = Field(default=None, nullable=True)
    unsubscribe_reasons: str | None = Field(nullable=True)


class SubscriptionCreate(SQLModel):
    id: UUID
    stripe_sub_id: str | None = Field(max_length=255, nullable=True)
    org_id: UUID = Field(foreign_key="user.id")
    package_id: UUID = Field(foreign_key="package.id")
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)


class SubscriptionPublic(SubscriptionBase):
    package: PackagePublic


class SubscriptionsPublic(SQLModel):
    data: list[SubscriptionPublic]
    count: int


class CheckoutCreateOrUpdate(SQLModel):
    package_id: UUID
