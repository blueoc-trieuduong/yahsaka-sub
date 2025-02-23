import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import SQLModel, select

from app.api.deps import SessionDep
from app.models.models import Package, Subscription
from app.models.packages import PackagePublic
from app.models.subscriptions import Status
from app.services.stripe import (
    create_stripe_checkout,
    update_stripe_subscription_on_stripe,
)


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


async def create_subscription_checkout_service(
    session: SessionDep, package_id: str, user_id: str
):
    try:
        package = session.get(Package, package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")

        price_id = package.stripe_price_id
        if not price_id:
            raise HTTPException(
                status_code=400, detail="No price ID associated with this package"
            )

        stripe_session = create_stripe_checkout(
            {"priceId": price_id, "user_id": user_id, "package_id": package_id}
        )

        if not stripe_session:
            raise HTTPException(
                status_code=400, detail="Failed to create Stripe Checkout Session"
            )

        return stripe_session.get("url")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during subscription creation: {e}",
        )


async def create_subscription_from_stripe(
    session: SessionDep, stripe_sub_id: str, user_id: str, package_id: str
) -> Subscription:
    try:
        new_subscription = Subscription(
            stripe_sub_id=stripe_sub_id,
            user_id=user_id,
            package_id=package_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        session.add(new_subscription)
        await session.commit()
        await session.refresh(new_subscription)

        return new_subscription

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Unexpected error while saving subscription: {e}"
        )


async def update_stripe_subscription(session, stripe_sub_id: str, new_package_id: str):
    try:
        statement = select(Package).where(Package.id == new_package_id)
        result = await session.exec(statement)
        new_package = result.first()

        if not new_package:
            raise HTTPException(status_code=404, detail="Package not found")

        price_id = new_package.stripe_price_id
        if not price_id:
            raise HTTPException(
                status_code=400, detail="No price ID associated with this package"
            )

        stripe_response = update_stripe_subscription_on_stripe(stripe_sub_id, price_id)

        if not stripe_response:
            raise HTTPException(
                status_code=400, detail="Failed to update Stripe subscription"
            )

        subscription_statement = select(Subscription).where(Subscription.stripe_sub_id == stripe_sub_id)
        subscription_result = await session.exec(subscription_statement)
        subscription = subscription_result.first()

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        subscription.package_id = new_package_id
        subscription.current_status = Status.UPGRADED  #
        await session.refresh(subscription)

        return stripe_response.get("url")

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Unexpected error during subscription update: {e}"
        )


async def get_current_active_subscription_and_package(session, user_id):
    try:
        statement = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.current_status == Status.ACTIVE,
        )
        result = await session.exec(statement)
        active_subscription = result.first()

        if not active_subscription:
            raise HTTPException(
                status_code=404, detail="No active subscription found for this user"
            )

        package_statement = select(Package).where(
            Package.id == active_subscription.package_id
        )
        package_result = await session.exec(package_statement)
        package = package_result.first()

        if not package:
            raise HTTPException(
                status_code=404, detail="Package not found for this subscription"
            )

        package_info = PackagePublic(
            id=package.id,
            title=package.title,
            description=package.description,
            stripe_product_id=package.stripe_product_id,
            stripe_price_id=package.stripe_price_id,
            price=package.price,
            max_workplaces=package.max_workplaces,
            max_employees=package.max_employees,
            is_active=package.is_active,
            created_at=package.created_at,
            updated_at=package.updated_at,
        )

        subscription_with_package = SubscriptionWithPackageInfo(
            created_at=active_subscription.created_at,
            updated_at=active_subscription.updated_at,
            package=package_info,
        )

        return subscription_with_package

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching subscription and package: {e}"
        )


async def get_current_active_subscription_and_package(session, user_id):
    try:
        statement = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.current_status == Status.ACTIVE,
        )
        result = await session.exec(statement)
        active_subscription = result.first()

        if not active_subscription:
            raise HTTPException(
                status_code=404, detail="No active subscription found for this user"
            )

        package_statement = select(Package).where(
            Package.id == active_subscription.package_id
        )
        package_result = await session.exec(package_statement)
        package = package_result.first()

        if not package:
            raise HTTPException(
                status_code=404, detail="Package not found for this subscription"
            )

        package_info = PackagePublic(
            id=package.id,
            title=package.title,
            description=package.description,
            stripe_product_id=package.stripe_product_id,
            stripe_price_id=package.stripe_price_id,
            price=package.price,
            max_workplaces=package.max_workplaces,
            max_employees=package.max_employees,
            is_active=package.is_active,
            created_at=package.created_at,
            updated_at=package.updated_at,
        )

        subscription_with_package = SubscriptionWithPackageInfo(
            created_at=active_subscription.created_at,
            updated_at=active_subscription.updated_at,
            package=package_info,
        )

        return subscription_with_package

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching subscription and package: {e}"
        )


async def get_subscription_history_for_user(session, user_id):
    try:
        statement = select(Subscription).where(Subscription.user_id == user_id)
        result = await session.exec(statement)
        subscriptions = result.all()

        if not subscriptions:
            raise HTTPException(
                status_code=404, detail="No subscriptions found for this user"
            )

        subscription_history_list = []

        for sub in subscriptions:
            package_statement = select(Package).where(Package.id == sub.package_id)
            package_result = await session.exec(package_statement)
            package = package_result.first()

            if not package:
                raise HTTPException(
                    status_code=404,
                    detail=f"Package not found for subscription {sub.id}",
                )

            subscription_item = SubscriptionHistoryItem(
                subscription_id=sub.id,
                status=sub.current_status,
                created_at=sub.created_at,
                updated_at=sub.updated_at,
                unsubscribe_at=sub.unsubscribe_at,
                package=PackagePublic(
                    id=package.id,
                    title=package.title,
                    description=package.description,
                    stripe_product_id=package.stripe_product_id,
                    stripe_price_id=package.stripe_price_id,
                    price=package.price,
                    max_workplaces=package.max_workplaces,
                    max_employees=package.max_employees,
                    is_active=package.is_active,
                    created_at=package.created_at,
                    updated_at=package.updated_at,
                ),
            )

            subscription_history_list.append(subscription_item)

        return SubscriptionHistory(
            data=subscription_history_list, total=len(subscription_history_list)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching subscription history: {e}"
        )
