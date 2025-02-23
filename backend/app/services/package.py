from http.client import HTTPException
from importlib.resources import Package

from backend.app.api.deps import SessionDep
from sqlmodel import func, select

from app.models.packages import PackageCreate, PackageListPublic
from app.services.stripe import create_stripe_price, create_stripe_product

# Define the response schema for multiple packages


async def get_all_package_service(
    *, session: SessionDep, limit: int = 100, offset: int = 0
) -> PackageListPublic:
    query = select(Package).offset(offset).limit(limit)

    query_count = select(func.count(Package.id))

    result = await session.exec(query)
    packages = result.all()

    count_result = await session.exec(query_count)
    total = count_result.one_or_none() or 0

    return PackageListPublic(data=packages, total=total)


async def create_package_service(
    *, session: SessionDep, package_data: PackageCreate
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
        await session.commit()
        await session.refresh(new_package)

        try:
            stripe_product = create_stripe_product(
                new_package.title, new_package.description
            )
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=400, detail=f"Stripe Product creation failed: {e}"
            )

        try:
            stripe_price = create_stripe_price(stripe_product.id, new_package.price)
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=400, detail=f"Stripe Price creation failed: {e}"
            )

        new_package.stripe_product_id = stripe_product.id
        new_package.stripe_price_id = stripe_price.id

        session.add(new_package)
        await session.commit()
        await session.refresh(new_package)

        return new_package

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
