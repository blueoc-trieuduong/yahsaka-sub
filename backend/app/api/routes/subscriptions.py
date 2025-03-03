from datetime import datetime
import requests
from fastapi import APIRouter, HTTPException, Request
from sqlmodel import desc, select
from fastapi import Request
from dateutil.relativedelta import relativedelta
from app.core.config import settings
from app.api.deps import CurrentUser, SessionDep
from app.models.models import Subscription
from app.models.subscriptions import (
    CheckoutCreateOrUpdate,
    Status,
    SubscriptionPublic,
    SubscriptionUpgrade,
    SubscriptionsPublic,
)
from datetime import datetime, timedelta
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
        session=session, package_id=checkout_create.package_id, org_id=current_user.org_id
    )
    return {"checkout_url": checkout_url}



@router.post("/webhook")
async def handle_stripe_webhook(request: Request, session: SessionDep):
    try:
        print("🔔 Webhook accessed")
        event = await request.json()
        print("Received event:", event)

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
                    headers=headers
                )

                if subscription_response.status_code != 200:
                    raise Exception(f"Failed to get subscription: {subscription_response.text}")

                stripe_subscription = subscription_response.json()
                subscription_item_id = stripe_subscription["items"]["data"][0]["id"]

                update_params = {
                    "items[0][id]": subscription_item_id,
                    "items[0][price]": new_price_id,
                    "proration_behavior": "none",
                    "billing_cycle_anchor": "unchanged"
                }

                update_response = requests.post(
                    f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
                    headers=headers,
                    data=update_params
                )

                if update_response.status_code != 200:
                    raise Exception(f"Failed to update subscription: {update_response.text}")

                existing_subscription = session.exec(
                    select(Subscription).where(Subscription.stripe_sub_id == subscription_id)
                ).first()

                if existing_subscription:
                    print("✅ Subscription được nâng cấp, đánh dấu là UPGRADED.")
                    existing_subscription.status = Status.UPGRADED
                    existing_subscription.updated_at = datetime.utcnow()
                    session.commit()

                print("🔔 Tạo subscription mới sau khi upgrade.")
                new_subscription = SubscriptionServices.create_subscription_from_stripe(
                    session=session,
                    stripe_sub_id=subscription_id,
                    org_id=org_id,
                    package_id=package_id,
                )

                return {"status": "subscription upgraded", "subscription_id": subscription_id}

            else:
                if not subscription_id:
                    return {"status": "no subscription found in session"}

                existing_subscription = session.exec(
                    select(Subscription).where(Subscription.stripe_sub_id == subscription_id)
                ).first()

                if existing_subscription:
                    return {"status": "subscription already exists", "subscription_id": subscription_id}

                print("🔔 Tạo subscription mới từ checkout session.")
                new_subscription = SubscriptionServices.create_subscription_from_stripe(
                    session=session,
                    stripe_sub_id=subscription_id,
                    org_id=org_id,
                    package_id=package_id,
                )

                return {"status": "subscription created", "subscription_id": subscription_id}

        elif event.get("type") == "invoice.payment_succeeded":
            print("🔔 Stripe vừa tự động trừ tiền! Kiểm tra subscription...")

            subscription_id = event["data"]["object"]["subscription"]
            if not subscription_id:
                return {"status": "no subscription found in invoice"}

            pending_subscription = session.exec(
                select(Subscription).where(
                    Subscription.stripe_sub_id == subscription_id,
                    Subscription.status == Status.PENDING
                )
            ).first()

            if pending_subscription:
                print("✅ Subscription PENDING được kích hoạt.")
                pending_subscription.status = Status.ACTIVE
                pending_subscription.updated_at = datetime.utcnow()
                session.commit()

                return {"status": "pending subscription activated", "subscription_id": pending_subscription.id}

            # 🔹 Nếu không có PENDING, tạo subscription mới
            active_subscription = session.exec(
                select(Subscription).where(
                    Subscription.stripe_sub_id == subscription_id,
                    Subscription.status == Status.ACTIVE
                )
            ).first()

            if active_subscription:
                print("✅ Đánh dấu subscription cũ thành DONE.")
                active_subscription.status = Status.DONE
                session.commit()

            # Tạo subscription mới cho tháng tiếp theo
            new_active_date = active_subscription.expired_date + timedelta(days=1)
            new_expired_date = new_active_date + relativedelta(months=1)

            print("🔔 Tạo subscription mới sau khi Stripe trừ tiền.")
            new_subscription = Subscription(
                org_id=active_subscription.org_id,
                package_id=active_subscription.package_id,
                stripe_sub_id=subscription_id,
                status=Status.ACTIVE,
                active_date=new_active_date,
                expired_date=new_expired_date,
            )

            session.add(new_subscription)
            session.commit()
            session.refresh(new_subscription)

            return {"status": "new subscription created after payment", "subscription_id": new_subscription.id}

        return {"status": "unhandled event"}

    except Exception as e:
        print(f"Error handling webhook: {e}")
        raise HTTPException(status_code=400, detail=f"Webhook handling failed: {e}")


# @router.post("/webhook")
# async def handle_stripe_webhook(request: Request, session: SessionDep):
#     try:
#         print("Webhook accessed")
#         event = await request.json()
#         print("Received event:", event)
        
#         if event.get("type") == "checkout.session.completed":
#             session_data = event["data"]["object"]
#             metadata = session_data.get("metadata", {})
#             subscription_id = session_data.get("subscription")
#             org_id = metadata.get("org_id")
#             package_id = metadata.get("package_id")
            
#             if metadata.get("subscription_id") and metadata.get("new_price_id"):
#                 subscription_id = metadata["subscription_id"]
#                 new_price_id = metadata["new_price_id"]
                
#                 headers = {
#                     "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
#                     "Content-Type": "application/x-www-form-urlencoded",
#                 }
                
#                 subscription_response = requests.get(
#                     f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
#                     headers=headers
#                 )
                
#                 if subscription_response.status_code != 200:
#                     raise Exception(f"Failed to get subscription: {subscription_response.text}")
                    
#                 subscription = subscription_response.json()
#                 subscription_item_id = subscription["items"]["data"][0]["id"]
                
#                 update_params = {
#                     "items[0][id]": subscription_item_id,
#                     "items[0][price]": new_price_id,
#                     "proration_behavior": "none",
#                     "billing_cycle_anchor": "unchanged"
#                 }
                
#                 update_response = requests.post(
#                     f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
#                     headers=headers,
#                     data=update_params
#                 )
                
#                 if update_response.status_code != 200:
#                     raise Exception(f"Failed to update subscription: {update_response.text}")
                
#                 subscription_db = session.exec(
#                     select(Subscription).where(
#                         Subscription.stripe_sub_id == subscription_id
#                     )
#                 ).first()
#                 if subscription_db:
#                     subscription_db.status = Status.UPGRADED.value
#                     subscription_db.updated_at = datetime.now()
#                     session.add(subscription_db)
#                     session.commit()
                    
#                 return {"status": "subscription upgraded", "subscription_id": subscription_id}
#             else:
#                 if not subscription_id:
#                     return {"status": "no subscription found in session"}
                    
#                 new_subscription = SubscriptionServices.create_subscription_from_stripe(
#                     session=session,
#                     stripe_sub_id=subscription_id,
#                     org_id=org_id,
#                     package_id=package_id,
#                 )
#                 return {"status": "success", "subscription_id": new_subscription.id}
        
#         elif event.get("type") == "customer.subscription.updated":
#             subscription_id = event["data"]["object"]["id"]
#             status = event["data"]["object"]["status"]
#             subscription = session.exec(
#                 select(Subscription).where(
#                     Subscription.stripe_sub_id == subscription_id
#                 )
#             ).first()
#             if subscription:
#                 if subscription.status != Status.UPGRADED.value:
#                     if status == "active":
#                         subscription.status = Status.ACTIVE.value
#                     elif status == "canceled":
#                         subscription.status = Status.CANCELED.value
#                     else:
#                         subscription.status = Status.PENDING.value
#                     subscription.updated_at = datetime.now()
#                     session.commit()

#             return {
#                 "status": "subscription updated",
#                 "subscription_id": subscription.id if subscription else None,
#             }

        
#         elif event.get("type") == "customer.subscription.deleted":
#             subscription_id = event["data"]["object"]["id"]
#             subscription = session.exec(
#                 select(Subscription).where(
#                     Subscription.stripe_sub_id == subscription_id
#                 )
#             ).first()
            
#             if subscription:
#                 subscription.status = Status.CANCELED.value
#                 subscription.unsubscribe_at = datetime.now()
#                 session.commit()
                
#             return {
#                 "status": "subscription canceled",
#                 "subscription_id": subscription.id if subscription else None,
#             }
        
#         elif event.get("type") == "invoice.payment_succeeded":
#             print("🔔 Stripe vừa tự động trừ tiền! Kiểm tra subscription...")

#             subscription_id = event["data"]["object"]["subscription"]
#             if not subscription_id:
#                 return {"status": "no subscription found in invoice"}
            
#             pending_subscription = session.exec(
#                 select(Subscription).where(
#                     Subscription.stripe_sub_id == subscription_id,
#                     Subscription.status == Status.PENDING
#                 )
#             ).first()

#             if pending_subscription:
#                 print("✅ Found pending subscription, activating it.")
#                 pending_subscription.status = Status.ACTIVE
#                 pending_subscription.updated_at = datetime.utcnow()
#                 session.commit()

#                 active_subscription = session.exec(
#                     select(Subscription).where(
#                         Subscription.stripe_sub_id == subscription_id,
#                         Subscription.status == Status.ACTIVE
#                     )
#                 ).first()
                
#                 if active_subscription:
#                     active_subscription.status = Status.DONE
#                     session.commit()

#                 return {
#                     "status": "pending subscription activated",
#                     "subscription_id": pending_subscription.id
#                 }

#             statement = select(Subscription).where(
#                 Subscription.stripe_sub_id == subscription_id
#             ).order_by(desc(Subscription.created_at))
            
#             subscriptions = session.exec(statement).all()
#             if not subscriptions:
#                 return {"status": "subscription not found in database"}

#             for sub in subscriptions:
#                 sub.status = Status.DONE
#                 session.add(sub)

#             session.commit()

#             latest_subscription = subscriptions[0]  
#             package_id = latest_subscription.package_id
#             org_id = latest_subscription.org_id
            
#             new_active_date = latest_subscription.expired_date + timedelta(days=1)
#             new_expired_date = new_active_date + relativedelta(months=1)

#             new_subscription = Subscription(
#                 org_id=org_id,
#                 package_id=package_id,
#                 stripe_sub_id=subscription_id,
#                 status=Status.ACTIVE,
#                 active_date=new_active_date,
#                 expired_date=new_expired_date,
#             )

#             session.add(new_subscription)
#             session.commit()
#             session.refresh(new_subscription)

#             return {
#                 "status": "new subscription created after payment",
#                 "subscription_id": new_subscription.id,
#             }

#         return {"status": "unhandled event"}
        
#     except Exception as e:
#         print(f"Error handling webhook: {e}")
#         raise HTTPException(status_code=400, detail=f"Webhook handling failed: {e}")


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
        subscription_id=upgrade_data.subscription_id
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
            session=session, current_subscription=current_subscription, new_package_id=checkout_update.package_id
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
            session=session, current_subscription=current_subscription, new_package_id=checkout_update.package_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


        
