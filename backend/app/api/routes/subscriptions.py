from datetime import datetime, timedelta

import requests
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, HTTPException, Request
from sqlmodel import desc, select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models.models import Subscription
from app.models.subscriptions import (
    CheckoutCreateOrUpdate,
    Status,
    SubscriptionPublic,
    SubscriptionsPublic,
    SubscriptionUpgrade,
)
from app.services.subscriptions import (
    SubscriptionServices,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/current", response_model=SubscriptionPublic)
def get_current_subscription(
    current_user: CurrentUser, session: SessionDep, isActive: bool = True
) -> SubscriptionPublic:
    return SubscriptionServices.get_current_active_subscription(
        session=session, org_id=current_user.org_id, isActive=isActive
    )


@router.get("/next", response_model=SubscriptionPublic)
def get_next_subscription(
    current_user: CurrentUser, session: SessionDep
) -> SubscriptionPublic:
    return SubscriptionServices.get_next_subscription(
        session=session, org_id=current_user.org_id
    )


@router.get("/new", response_model=SubscriptionPublic)
def get_new_subscription(
    current_user: CurrentUser, session: SessionDep
) -> SubscriptionPublic:
    return SubscriptionServices.get_new_subscription(
        session=session, org_id=current_user.org_id
    )


@router.get("/history")
def get_subscription_history(
    current_user: CurrentUser,
    session: SessionDep,
    page_index: int = 0,
    page_size: int = 10,
) -> SubscriptionsPublic:
    return SubscriptionServices.get_subscription_history(
        session=session,
        org_id=current_user.org_id,
        page_index=page_index,
        page_size=page_size,
    )


@router.post("/checkout")
def create_checkout_url(
    checkout_create: CheckoutCreateOrUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    checkout_url = SubscriptionServices.create_subscription_checkout(
        session=session,
        package_id=checkout_create.package_id,
        org_id=current_user.org_id,
    )
    return {"checkout_url": checkout_url}


@router.post("/webhook")
async def handle_stripe_webhook(request: Request, session: SessionDep):
    try:
        event = await request.json()
        if event.get("type") == "checkout.session.completed":
            session_data = event["data"]["object"]
            metadata = session_data.get("metadata", {})
            subscription_id = session_data.get("subscription")
            org_id = metadata.get("org_id")
            package_id = metadata.get("package_id")

            if metadata.get("subscription_id") and metadata.get("new_price_id"):
                subscription_id = metadata["subscription_id"]
                new_price_id = metadata["new_price_id"]

                headers = {
                    "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                subscription_response = requests.get(
                    f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
                    headers=headers,
                )

                if subscription_response.status_code != 200:
                    raise Exception(
                        f"Failed to get subscription: {subscription_response.text}"
                    )

                stripe_subscription = subscription_response.json()
                subscription_item_id = stripe_subscription["items"]["data"][0]["id"]

                update_params = {
                    "items[0][id]": subscription_item_id,
                    "items[0][price]": new_price_id,
                    "proration_behavior": "none",
                    "billing_cycle_anchor": "unchanged",
                }

                update_response = requests.post(
                    f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
                    headers=headers,
                    data=update_params,
                )

                if update_response.status_code != 200:
                    raise Exception(
                        f"Failed to update subscription: {update_response.text}"
                    )

                existing_subscription = session.exec(
                    select(Subscription)
                    .where(
                        Subscription.stripe_sub_id == subscription_id,
                        Subscription.status == Status.ACTIVE,
                    )
                    .order_by(desc(Subscription.expired_date))
                ).first()

                if existing_subscription:
                    existing_subscription.status = Status.UPGRADED
                    existing_subscription.updated_at = datetime.utcnow()
                    session.commit()

                new_active_date = existing_subscription.expired_date + timedelta(days=1)
                new_expired_date = new_active_date + relativedelta(months=1)

                new_subscription = Subscription(
                    org_id=existing_subscription.org_id,
                    package_id=package_id,
                    stripe_sub_id=subscription_id,
                    status=Status.ACTIVE,
                    active_date=new_active_date,
                    expired_date=new_expired_date,
                )

                session.add(new_subscription)
                session.commit()
                session.refresh(new_subscription)

                return {
                    "status": "subscription upgraded",
                    "subscription_id": subscription_id,
                }

            else:
                if not subscription_id:
                    return {"status": "no subscription found in session"}

                existing_subscription = session.exec(
                    select(Subscription).where(
                        Subscription.stripe_sub_id == subscription_id
                    )
                ).first()

                if existing_subscription:
                    return {
                        "status": "subscription already exists",
                        "subscription_id": subscription_id,
                    }

                new_subscription = SubscriptionServices.create_subscription_from_stripe(
                    session=session,
                    stripe_sub_id=subscription_id,
                    org_id=org_id,
                    package_id=package_id,
                )

                return {
                    "status": "subscription created",
                    "subscription_id": subscription_id,
                }

        elif event.get("type") == "invoice.payment_succeeded":
            subscription_id = event["data"]["object"]["subscription"]
            if not subscription_id:
                return {"status": "no subscription found in invoice"}

            now = datetime.now()

            active_subscription = session.exec(
                select(Subscription).where(
                    Subscription.stripe_sub_id == subscription_id,
                    Subscription.status == Status.ACTIVE,
                    Subscription.expired_date > now,
                )
            ).first()

            if active_subscription:
                return {
                    "status": "subscription still active",
                    "subscription_id": active_subscription.id,
                }

            pending_subscription = session.exec(
                select(Subscription).where(
                    Subscription.stripe_sub_id == subscription_id,
                    Subscription.status == Status.PENDING,
                )
            ).first()

            if pending_subscription:
                pending_subscription.status = Status.ACTIVE
                pending_subscription.updated_at = now

                active_subscription_old = session.exec(
                    select(Subscription).where(
                        Subscription.stripe_sub_id == subscription_id,
                        Subscription.status == Status.ACTIVE,
                    )
                ).first()

                if active_subscription_old:
                    active_subscription_old.status = Status.DONE

                session.commit()
                return {
                    "status": "pending subscription activated",
                    "subscription_id": pending_subscription.id,
                }

            latest_subscription = session.exec(
                select(Subscription)
                .where(Subscription.stripe_sub_id == subscription_id)
                .order_by(desc(Subscription.created_at))
            ).first()

            if latest_subscription:
                print("✅ Đánh dấu subscription cũ thành DONE.")
                latest_subscription.status = Status.DONE
                session.commit()

            new_active_date = latest_subscription.expired_date + timedelta(days=1)
            new_expired_date = new_active_date + relativedelta(months=1)

            new_subscription = Subscription(
                org_id=latest_subscription.org_id,
                package_id=latest_subscription.package_id,
                stripe_sub_id=subscription_id,
                status=Status.ACTIVE,
                active_date=new_active_date,
                expired_date=new_expired_date,
            )

            session.add(new_subscription)
            session.commit()
            session.refresh(new_subscription)

            return {
                "status": "new subscription created after payment",
                "subscription_id": new_subscription.id,
            }

        return {"status": "unhandled event"}

    except Exception as e:
        print(f"Error handling webhook: {e}")
        raise HTTPException(status_code=400, detail=f"Webhook handling failed: {e}")


@router.post("/upgrade-plan")
def upgrade_subscription(
    upgrade_data: SubscriptionUpgrade,
    current_user: CurrentUser,
    session: SessionDep,
):
    checkout_url = SubscriptionServices.create_subscription_upgrade(
        session=session,
        package_id=upgrade_data.package_id,
        org_id=current_user.org_id,
        subscription_id=upgrade_data.subscription_id,
    )
    return {"checkout_url": checkout_url}


@router.post("/downgrade")
def downgrade_subscription_plan(
    checkout_update: CheckoutCreateOrUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    try:
        statement = select(Subscription).where(
            Subscription.org_id == current_user.org_id,
            Subscription.status == Status.ACTIVE,
        )
        current_subscription = session.exec(statement).first()
        if not current_subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")

        return SubscriptionServices.downgrade_subscription(
            session=session,
            current_subscription=current_subscription,
            new_package_id=checkout_update.package_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel")
def cancel_subscription_plan(
    checkout_update: CheckoutCreateOrUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    try:
        statement = select(Subscription).where(
            Subscription.org_id == current_user.org_id,
            Subscription.status == Status.ACTIVE,
        )
        current_subscription = session.exec(statement).first()
        if not current_subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")

        return SubscriptionServices.downgrade_subscription(
            session=session,
            current_subscription=current_subscription,
            new_package_id=checkout_update.package_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
