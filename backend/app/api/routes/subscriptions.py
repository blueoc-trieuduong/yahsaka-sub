from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models.models import Subscription
from app.models.subscriptions import (
    CheckoutCreateOrUpdate,
    Status,
    SubscriptionPublic,
    SubscriptionsPublic,
)
from app.services.subscriptions import (
    SubscriptionServices,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/current", response_model=SubscriptionPublic)
def get_current_subscription(
    current_user: CurrentUser, session: SessionDep
) -> SubscriptionPublic:
    return SubscriptionServices.get_current_active_subscription(
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
        session=session, package_id=checkout_create.package_id, org_id=current_user.org_id
    )
    return {"checkout_url": checkout_url}


@router.post("/webhook")
async def handle_stripe_webhook(request: Request, session: SessionDep):
    try:
        print("Webhook accessed")
        event = await request.json()
        print("Received event:", event)

        if event.get("type") == "checkout.session.completed":
            subscription_id = event["data"]["object"]["subscription"]
            metadata = event["data"]["object"]["metadata"]
            org_id = metadata.get("org_id")
            package_id = metadata.get("package_id")
            print(f"Checkout session completed for org_id: {org_id}, package_id: {package_id}, subscription_id: {subscription_id}")

            new_subscription =  SubscriptionServices.create_subscription_from_stripe(
                session=session,
                stripe_sub_id=subscription_id,
                org_id=org_id,
                package_id=package_id,
            )
            
            return {"status": "success", "subscription_id": new_subscription.id}

        elif event.get("type") == "customer.subscription.updated":
            subscription_id = event["data"]["object"]["id"]
            status = event["data"]["object"]["status"]

            subscription = session.exec(
                select(Subscription).where(
                    Subscription.stripe_sub_id == subscription_id
                )
            ).first()

            if subscription:
                if status == Status.ACTIVE:
                    subscription.status = Status.UPGRADED
                elif status == Status.CANCELED:
                    subscription.status = Status.CANCELED
                else:
                    subscription.status = Status.PENDING

                subscription.updated_at = datetime.now()
                session.commit()

            return {
                "status": "subscription updated",
                "subscription_id": subscription.id,
            }

        elif event.get("type") == "customer.subscription.deleted":
            subscription_id = event["data"]["object"]["id"]

            subscription = session.exec(
                select(Subscription).where(
                    Subscription.stripe_sub_id == subscription_id
                )
            ).first()

            if subscription:
                subscription.status = Status.CANCELED
                subscription.unsubscribe_at = datetime.now()
                await session.commit()

            return {
                "status": "subscription canceled",
                "subscription_id": subscription.id,
            }

        elif event.get("type") == "invoice.payment_succeeded":
            subscription_id = event["data"]["object"]["subscription"]

            statement = select(Subscription).where(
                Subscription.stripe_sub_id == subscription_id
            )
            result = session.exec(statement)
            subscription = result.first()

            if subscription:
                subscription.status = Status.ACTIVE
                subscription.updated_at = datetime.now()
                await session.commit()

            return {"status": "payment succeeded", "subscription_id": subscription.id}

        return {"status": "unhandled event"}

    except Exception as e:
        print(f"Error handling webhook: {e}")
        raise HTTPException(status_code=400, detail=f"Webhook handling failed: {e}")


@router.post("/change-plan")
async def change_subscription_plan(
    checkout_update: CheckoutCreateOrUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    try:
        statement = select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == Status.ACTIVE,
        )
        current_subscription = session.exec(statement).first()
        if not current_subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")

        checkout_url = await SubscriptionServices.update_stripe_subscription(
            session, current_subscription.stripe_sub_id, checkout_update.package_id
        )
        return {"checkout_url": checkout_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
