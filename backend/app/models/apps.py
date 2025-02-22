from datetime import datetime

from sqlmodel import Field, SQLModel


class AppBase(SQLModel):
    name: str = Field(max_length=255)
    description: str | None = Field(max_length=500, nullable=True)
    created_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
    updated_at: datetime | None = Field(default_factory=datetime.now, nullable=True)
