from datetime import datetime, timedelta
from uuid import UUID
import requests
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlmodel import Session, desc, func, select
from app.core.config import settings
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
        *, session: SessionDep, package_id: UUID, org_id: UUID
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
                {"priceId": price_id, "org_id": org_id, "package_id": package_id}
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

    def create_subscription_from_stripe(
        session: Session, stripe_sub_id: str, org_id: str, package_id: str
    ) -> SubscriptionCreate:
        try:
            print('createSub access')

            new_subscription = Subscription(
                stripe_sub_id=stripe_sub_id,
                org_id=org_id,
                package_id=package_id,
            )

            session.add(new_subscription)
            session.commit()
            session.refresh(new_subscription)

            return new_subscription

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error while saving subscription: {e}",
            )

    def update_stripe_subscription(
        session, stripe_sub_id: str, new_package_id: str
    ):
        try:
            statement = select(Package).where(Package.id == new_package_id)
            new_package = session.exec(statement).first()

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
            subscription = session.exec(subscription_statement).first()

            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")

            subscription.package_id = new_package_id
            subscription.status = Status.UPGRADED
            session.refresh(subscription)

            return stripe_response.get("url")

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during subscription update: {e}",
            )
        

    def downgrade_subscription(
    *, session: Session, current_subscription: Subscription, new_package_id: str
    ) -> SubscriptionPublic:
        headers = {
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        statement = select(Package).where(Package.id == new_package_id)
        new_package = session.exec(statement).first()
        if not new_package:
            raise HTTPException(status_code=404, detail="Package not found")

        stripe_sub_id = current_subscription.stripe_sub_id
        print('stripe_sub_id', stripe_sub_id)
        stripe_subscription_response = requests.get(
            f"https://api.stripe.com/v1/subscriptions/{stripe_sub_id}",
            headers=headers,
        )
        
        if stripe_subscription_response.status_code != 200:
            raise Exception(f"Failed to get subscription from Stripe: {stripe_subscription_response.text}")

        stripe_subscription = stripe_subscription_response.json()
        subscription_item_id = stripe_subscription["items"]["data"][0]["id"]

        update_params = {
            "items[0][id]": subscription_item_id,
            "items[0][price]": new_package.stripe_price_id,  
            "proration_behavior": "none", 
            "billing_cycle_anchor": "unchanged",  
        }

        update_response = requests.post(
            f"https://api.stripe.com/v1/subscriptions/{stripe_sub_id}",
            headers=headers,
            data=update_params,
        )

        if update_response.status_code != 200:
            raise Exception(f"Failed to update subscription: {update_response.text}")

        current_subscription.status = Status.DOWNGRADED
        current_subscription.package_id = new_package_id
        current_subscription.updated_at = datetime.utcnow()

        session.add(current_subscription)
        session.commit()
        session.refresh(current_subscription)

        return SubscriptionPublic.model_validate(current_subscription)


    def get_current_active_subscription(
    *, session: Session, org_id: UUID, isActive: bool
    ) -> SubscriptionPublic:
        try:
            now = datetime.utcnow()

            if isActive:
                status_filter = [Status.ACTIVE, Status.CANCELED] 
            else:
                status_filter = [Status.PENDING]

            statement = select(Subscription).where(
                Subscription.org_id == org_id,
                Subscription.status.in_(status_filter),
                Subscription.expired_date >= now  
            ).order_by(desc(Subscription.created_at))

            subscription = session.exec(statement).first()
            if not subscription:
                raise HTTPException(
                    status_code=404, detail=f"No valid {status_filter} subscription found for this user"
                )
            return SubscriptionPublic.model_validate(subscription)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching subscription: {e}"
            )
        

    def get_next_subscription(
    *, session: Session, org_id: UUID, isActive: bool
    ) -> SubscriptionPublic:
        try:
            now = datetime.utcnow()

            if isActive:
                status_filter = [Status.ACTIVE, Status.CANCELED] 
            else:
                status_filter = [Status.PENDING]

            statement = select(Subscription).where(
                Subscription.org_id == org_id,
                Subscription.status.in_(status_filter),
                Subscription.expired_date >= now  
            ).order_by(desc(Subscription.created_at))

            subscription = session.exec(statement).first()
            if not subscription:
                raise HTTPException(
                    status_code=404, detail=f"No valid {status_filter} subscription found for this user"
                )
            return SubscriptionPublic.model_validate(subscription)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching subscription: {e}"
            )    
        
    def get_new_subscription(
    *, session: Session, org_id: UUID
    ) -> SubscriptionPublic:
        try:
            statement = select(Subscription).where(
                Subscription.org_id == org_id,
            ).order_by(desc(Subscription.created_at))  

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
            statement = select(Subscription).where(Subscription.org_id == org_id).order_by(desc(Subscription.created_at))
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


    def create_subscription_upgrade(session, package_id, org_id, subscription_id):
            print('accessService')
            package = session.get(Package, package_id)
            if not package:
                raise HTTPException(status_code=404, detail="Package not found")
            
            checkout_data = {
                "price_id": package.stripe_price_id,
                "org_id": org_id,
                "package_id": package_id,
                "subscription_id": subscription_id
            }
            print('checkoutdata', checkout_data)
            
            checkout_session = StripeServices.create_proration_checkout(checkout_data)
            return checkout_session