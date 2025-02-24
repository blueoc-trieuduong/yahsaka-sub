from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import (
    SessionDep,
)
from app.models.models import Package
from app.models.packages import PackageCreate, PackagePublic, PackagesPublic
from app.services.packages import PackageServices

router = APIRouter(prefix="/apps", tags=["Packages"])


@router.get("/{app_id}/packages", response_model=PackagesPublic)
def get_packages_by_app_id(
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


@router.get("/{app_id}/packages/{package_id}", response_model=PackagePublic)
def get_package_by_id(
    session: SessionDep,
    package_id: UUID,
    app_id: UUID,
) -> PackagePublic:
    statement = select(Package).where(
        Package.id == package_id, Package.app_id == app_id
    )
    package = session.exec(statement).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return PackagePublic.model_validate(package)
