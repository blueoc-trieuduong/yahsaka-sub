import uuid
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.models.packages import PackagePublic
from app.utils import get_current_date, get_next_month_date


class Status(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    CANCELED = "canceled"
    UPGRADED = "upgraded"
    DOWNGRADED = "downgraded"
    EXPIRED = "expired"
    DONE = "done"


class SubscriptionBase(SQLModel):
    stripe_sub_id: str | None = Field(max_length=255, nullable=True)
    status: str = Field(default=Status.ACTIVE)
    active_date: datetime = Field(default_factory=get_current_date)
    expired_date: datetime = Field(default_factory=get_next_month_date)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    unsubscribe_at: datetime | None = Field(default=None, nullable=True)
    unsubscribe_reasons: str | None = Field(default=None, nullable=True)


class SubscriptionCreate(SQLModel):
    stripe_sub_id: str | None = Field(default=None, max_length=255, nullable=True)
    org_id: UUID = Field(foreign_key="org.id")
    package_id: UUID = Field(foreign_key="package.id")
    status: str = Field(default=Status.ACTIVE)
    active_date: datetime | None = Field(default_factory=get_current_date)
    expired_date: datetime | None = Field(default_factory=get_next_month_date)


class SubscriptionPublic(SubscriptionBase):
    id: uuid.UUID
    package: PackagePublic


class SubscriptionsPublic(SQLModel):
    data: list[SubscriptionPublic]
    count: int


class CheckoutCreateOrUpdate(SQLModel):
    package_id: UUID


class SubscriptionUpgrade(SQLModel):
    package_id: str
    subscription_id: str
