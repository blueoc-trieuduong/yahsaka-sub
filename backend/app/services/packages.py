from uuid import UUID

from fastapi import HTTPException
from sqlmodel import func, select
from starlette import status

from app.api.deps import SessionDep
from app.models.models import Package
from app.models.packages import PackageCreate, PackagePublic, PackagesPublic
from app.services.stripes import StripeServices


class PackageServices:
    def get_packages_by_app_id(*, session: SessionDep, app_id: UUID) -> PackagesPublic:
        try:
            statement = (
                select(Package)
                .where(Package.app_id == app_id)
                .order_by(Package.created_at)
            )
            count_statement = select(func.count()).select_from(statement)

            count = session.exec(count_statement).one()
            packages = session.exec(statement).all()

            return PackagesPublic(data=packages, count=count)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching packages: {str(e)}",
            )

    def create_package(
        *, session: SessionDep, package_data: PackageCreate, app_id: UUID
    ) -> PackagePublic:
        try:
            try:
                stripe_product = StripeServices.create_stripe_product(
                    package_data.title, package_data.description
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stripe Product creation failed: {str(e)}",
                )

            try:
                stripe_price = StripeServices.create_stripe_price(
                    stripe_product.id, package_data.price
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stripe Price creation failed: {str(e)}",
                )

            new_package = {
                **package_data.model_dump(),
                "app_id": app_id,
                "stripe_product_id": stripe_product.id,
                "stripe_price_id": stripe_price.id,
            }
            new_package = Package.model_validate(new_package)

            session.add(new_package)
            session.commit()
            session.refresh(new_package)

            return PackagePublic.model_validate(new_package)

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )
