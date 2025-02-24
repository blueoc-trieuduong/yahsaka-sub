from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.api.deps import SessionDep
from app.models.models import Package, Subscription
from app.models.subscriptions import (
    Status,
    SubscriptionCreate,
    SubscriptionPublic,
    SubscriptionsPublic,
)
from app.services.stripes import (
    StripeServices,
)


class SubscriptionServices:
    def create_subscription_checkout(
        *, session: SessionDep, package_id: UUID, user_id: UUID
    ):
        try:
            print("package_id", package_id)
            package = session.get(Package, package_id)
            if not package:
                raise HTTPException(status_code=404, detail="Package not found")

            price_id = package.stripe_price_id
            if not price_id:
                raise HTTPException(
                    status_code=400, detail="No price ID associated with this package"
                )
            print("price_id", price_id)
            stripe_session = StripeServices.create_stripe_checkout(
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
    ) -> SubscriptionCreate:
        try:
            print('createSub access')
            new_subscription = SubscriptionCreate(
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
                status_code=500,
                detail=f"Unexpected error while saving subscription: {e}",
            )

    async def update_stripe_subscription(
        session, stripe_sub_id: str, new_package_id: str
    ):
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

            stripe_response = StripeServices.update_stripe_subscription_on_stripe(
                stripe_sub_id, price_id
            )

            if not stripe_response:
                raise HTTPException(
                    status_code=400, detail="Failed to update Stripe subscription"
                )

            subscription_statement = select(Subscription).where(
                Subscription.stripe_sub_id == stripe_sub_id
            )
            subscription_result = await session.exec(subscription_statement)
            subscription = subscription_result.first()

            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")

            subscription.package_id = new_package_id
            subscription.status = Status.UPGRADED
            await session.refresh(subscription)

            return stripe_response.get("url")

        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during subscription update: {e}",
            )

    def get_current_active_subscription(
        *, session: Session, org_id: UUID
    ) -> SubscriptionPublic:
        try:
            statement = select(Subscription).where(
                Subscription.org_id == org_id,
                Subscription.status == Status.ACTIVE,
            )
            active_subscription = session.exec(statement).first()

            if not active_subscription:
                raise HTTPException(
                    status_code=404, detail="No active subscription found for this user"
                )

            return SubscriptionPublic.model_validate(active_subscription)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching subscription and package: {e}"
            )

    def get_subscription_history(
        *, session: Session, org_id: UUID, page_index: int = 0, page_size: int = 10
    ) -> SubscriptionsPublic:
        try:
            statement = select(Subscription).where(Subscription.org_id == org_id)
            count_statement = select(func.count()).select_from(statement)

            count = session.exec(count_statement).one()
            subscriptions = session.exec(
                statement.offset(page_index * page_size).limit(page_size)
            ).all()

            subscriptions_list: list[SubscriptionPublic] = []
            for sub in subscriptions:
                sub = SubscriptionPublic.model_validate(sub)
                subscriptions_list.append(sub)

            return SubscriptionsPublic(data=subscriptions_list, count=count)

        except Exception as e:
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Error fetching subscription history: {e}",
            )
