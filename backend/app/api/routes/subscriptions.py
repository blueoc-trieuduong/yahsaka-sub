from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.models.models import Subscription
from app.models.packages import GetPackageForSubscription
from app.models.subscriptions import Status
from app.services.subscription import (
    create_subscription_checkout_service,
    create_subscription_from_stripe,
    get_current_active_subscription_and_package,
    get_subscription_history_for_user,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/current-subscription")
async def get_current_subscription(current_user=CurrentUser, session=SessionDep):
    try:
        subscription_data = await get_current_active_subscription_and_package(
            session, current_user.id
        )
        return subscription_data

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/subscription-hisotry")
async def get_subscription_history(current_user=CurrentUser, session=SessionDep):
    try:
        subscription_history = await get_subscription_history_for_user(
            session, current_user.id
        )
        return subscription_history

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post("/")
async def create_subscription(
    data: GetPackageForSubscription, current_user=CurrentUser, session=SessionDep
):
    package_id = data.get("packageId")
    if not package_id:
        raise HTTPException(status_code=400, detail="Missing packageId")

    try:
        checkout_url = await create_subscription_checkout_service(
            session, package_id, current_user.id
        )
        return {"checkout_url": checkout_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_subscription(
    data: GetPackageForSubscription, current_user=CurrentUser, session=SessionDep
):
    package_id = data.get("id")
    if not package_id:
        raise HTTPException(status_code=400, detail="Missing packageId")

    try:
        checkout_url = await create_subscription_checkout_service(
            session, package_id, current_user.id
        )
        return {"checkout_url": checkout_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def handle_stripe_webhook(request: Request, session=SessionDep):
    try:
        event = request.json()

        if event.get("type") == "checkout.session.completed":
            subscription_id = event["data"]["object"]["subscription"]
            metadata = event["data"]["object"]["metadata"]
            user_id = metadata.get("user_id")
            package_id = metadata.get("package_id")

            new_subscription = await create_subscription_from_stripe(
                session=session,
                stripe_sub_id=subscription_id,
                user_id=user_id,
                package_id=package_id,
            )
            return {"status": "success", "subscription_id": new_subscription.id}

        elif event.get("type") == "customer.subscription.updated":
            subscription_id = event["data"]["object"]["id"]
            status = event["data"]["object"]["status"]

            subscription = (
                session.query(Subscription)
                .filter(Subscription.stripe_sub_id == subscription_id)
                .first()
            )

            if subscription:
                if status == "active":
                    subscription.current_status = Status.UPGRADED
                elif status == "canceled":
                    subscription.current_status = Status.CANCELED
                else:
                    subscription.current_status = Status.PENDING

                subscription.updated_at = datetime.now()
                await session.commit()

            return {
                "status": "subscription updated",
                "subscription_id": subscription.id,
            }

        elif event.get("type") == "customer.subscription.deleted":
            subscription_id = event["data"]["object"]["id"]

            subscription = (
                session.query(Subscription)
                .filter(Subscription.stripe_sub_id == subscription_id)
                .first()
            )

            if subscription:
                subscription.current_status = Status.CANCELED
                subscription.unsubscribe_at = datetime.now()
                await session.commit()

            return {
                "status": "subscription canceled",
                "subscription_id": subscription.id,
            }

        elif event.get("type") == "invoice.payment_succeeded":
            subscription_id = event["data"]["object"]["subscription"]

            subscription = (
                session.query(Subscription)
                .filter(Subscription.stripe_sub_id == subscription_id)
                .first()
            )

            if subscription:
                subscription.current_status = Status.ACTIVE
                subscription.updated_at = datetime.now()
                await session.commit()

            return {"status": "payment succeeded", "subscription_id": subscription.id}

        return {"status": "unhandled event"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook handling failed: {e}")


@router.post("/change-plan")
async def change_subscription_plan(
    data: dict, current_user=Depends(get_current_user), session=Depends(SessionDep)
):
    new_package_id = data.get("packageId")
    if not new_package_id:
        raise HTTPException(status_code=400, detail="Missing new packageId")

    try:
        current_subscription = (
            session.query(Subscription)
            .filter(
                Subscription.user_id == current_user.id,
                Subscription.current_status == "active",
            )
            .first()
        )

        if not current_subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")

        checkout_url = await update_stripe_subscription(
            session, current_subscription.stripe_sub_id, new_package_id
        )
        return {"checkout_url": checkout_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
