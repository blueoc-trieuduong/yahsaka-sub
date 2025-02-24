import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.apps import AppBase
from app.models.orgs import OrgBase
from app.models.packages import PackageBase
from app.models.subscriptions import SubscriptionBase
from app.models.users import UserBase


class BaseModel(SQLModel):
    pass


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(foreign_key="org.id")
    password: str = Field(min_length=8, max_length=40)

    org: "Org" = Relationship(back_populates="users")


class Org(OrgBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    users: list[User] = Relationship(back_populates="org")
    subscriptions: list["Subscription"] = Relationship(back_populates="org")


class Subscription(SubscriptionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(foreign_key="org.id")
    package_id: uuid.UUID = Field(foreign_key="package.id")

    org: "Org" = Relationship(back_populates="subscriptions")
    package: "Package" = Relationship(back_populates="subscriptions")


class Package(PackageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    app_id: uuid.UUID = Field(foreign_key="app.id")

    app: "App" = Relationship(back_populates="packages")
    subscriptions: list["Subscription"] = Relationship(back_populates="package")


class App(AppBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    packages: list["Package"] = Relationship(back_populates="app")
