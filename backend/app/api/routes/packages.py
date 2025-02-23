from fastapi import APIRouter

from app.api.deps import (
    SessionDep,
)
from app.models.packages import PackageCreate, PackageListPublic
from app.models.subscriptions import SubscriptionBase
from app.services.packages import PackageService

router = APIRouter()


@router.get("/", response_model=PackageListPublic)
def read_all_package_service(
    session: SessionDep,
    limit: int = 100,
) -> PackageListPublic:
    return PackageService.get_all_package_service(
        session=session,
        limit=limit,
    )


@router.post("/", response_model=PackageCreate)
def create_package(
    subscription: SubscriptionBase,
    session: SessionDep,
) -> PackageCreate:
    return PackageService.create_package_service(
        session=session,
        subscription=subscription,
    )
