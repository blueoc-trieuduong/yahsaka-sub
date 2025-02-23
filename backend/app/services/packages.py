from http.client import HTTPException
from importlib.resources import Package

from backend.app.api.deps import SessionDep
from sqlmodel import func, select
from starlette import status

from app.models.packages import PackageCreate, PackageListPublic
from app.services.stripe import create_stripe_price, create_stripe_product


class PackageService:
    def get_all_package_service(
        self, session: SessionDep, limit: int = 100, offset: int = 0
    ) -> PackageListPublic:
        try:
            packages = session.exec(select(Package).offset(offset).limit(limit)).all()

            total = session.exec(select(func.count(Package.id))).one_or_none() or 0

            return PackageListPublic(data=packages, total=total)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching packages: {str(e)}",
            )

    def create_package_service(
        self, session: SessionDep, package_data: PackageCreate
    ) -> Package:
        try:
            new_package = Package(
                app_id=package_data.app_id,
                title=package_data.title,
                description=package_data.description,
                price=package_data.price,
                max_workplaces=package_data.max_workplaces,
                max_employees=package_data.max_employees,
                created_at=package_data.created_at,
            )

            session.add(new_package)
            session.commit()
            session.refresh(new_package)

            try:
                stripe_product = create_stripe_product(
                    new_package.title, new_package.description
                )
            except Exception as e:
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stripe Product creation failed: {str(e)}",
                )

            try:
                stripe_price = create_stripe_price(stripe_product.id, new_package.price)
            except Exception as e:
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stripe Price creation failed: {str(e)}",
                )

            new_package.stripe_product_id = stripe_product.id
            new_package.stripe_price_id = stripe_price.id

            session.add(new_package)
            session.commit()
            session.refresh(new_package)

            return new_package

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )
