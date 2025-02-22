import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class SubscriptionBase(SQLModel):
    stripe_sub_id: str = Field(max_length=255, nullable=True)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    unsubscribe_at: datetime | None = Field(default=None, nullable=True)
    unsubscribe_reasons: str | None = Field(
        nullable=True
    )  # multiple reasons divided by ;


class SubscriptionPublic(SubscriptionBase):
    id: uuid.UUID


class SubscriptionCreate(SubscriptionBase):
    pass
