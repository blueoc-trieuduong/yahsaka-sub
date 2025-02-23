import uuid
from datetime import datetime
from enum import Enum

from app.models.packages import PackagePublic
from sqlmodel import Field, SQLModel


class Status(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    CANCELED = "canceled"
    UPGRADED = "upgraded"
    DOWNGRADED = "downgraded"
    EXPIRED = "expired"


class SubscriptionBase(SQLModel):
    stripe_sub_id: str | None = Field(max_length=255, nullable=True)
    current_status: Status  = Field(
        default=Status.ACTIVE,
    ) 
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    unsubscribe_at: datetime | None = Field(default=None, nullable=True)
    unsubscribe_reasons: str | None = Field(nullable=True)


class SubscriptionPublic(SubscriptionBase):
    id: uuid.UUID


class SubscriptionCreate(SubscriptionBase):
    id: uuid.UUID
    user_id: uuid.UUID = Field(foreign_key="user.id")
    package_id: uuid.UUID = Field(foreign_key="package.id")


class Subscription(SubscriptionBase):
    id: uuid.UUID
    user_id: uuid.UUID = Field(foreign_key="user.id")
    package_id: uuid.UUID = Field(foreign_key="package.id")


class SubscriptionWithPackageInfo(SQLModel):
    created_at: datetime
    updated_at: datetime
    package: PackagePublic


class SubscriptionHistoryItem(SQLModel):
    subscription_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    unsubscribe_at: datetime | None
    package: PackagePublic

class SubscriptionHistory(SQLModel):
    data: list[SubscriptionHistoryItem]
    total: int