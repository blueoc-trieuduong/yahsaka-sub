from uuid import UUID

from fastapi import APIRouter

from app.api.deps import (
    SessionDep,
)
from app.models.packages import PackageCreate, PackagePublic, PackagesPublic
from app.services.packages import PackageServices

router = APIRouter(prefix="/apps", tags=["Packages"])


@router.get("/{app_id}/packages", response_model=PackagesPublic)
def read_all_package_service(
    session: SessionDep,
    app_id: UUID,
) -> PackagesPublic:
    return PackageServices.get_packages_by_app_id(session=session, app_id=app_id)


@router.post("/{app_id}/packages", response_model=PackagePublic)
def create_package(
    package_create: PackageCreate,
    session: SessionDep,
    app_id: UUID,
) -> PackagePublic:
    return PackageServices.create_package(
        session=session, package_data=package_create, app_id=app_id
    )
