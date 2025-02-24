from http.client import HTTPException

import requests
from sqlmodel import SQLModel

from app.core.config import settings


class StripeId(SQLModel):
    id: str


class StripeServices:
    def create_stripe_checkout(data):
        try:
            print('dataSession', data)
            payload = {
            "mode": "subscription",
            "success_url": "https://truongnguyen94.wixsite.com/yashaka-timesheet/checkout",
            "cancel_url": "https://truongnguyen94.wixsite.com/yashaka-timesheet",
            "line_items[0][price]": data["priceId"],  
            "line_items[0][quantity]": "1",
            "subscription_data[trial_from_plan]": "false",
            "metadata[org_id]": data["org_id"],
            "metadata[package_id]": data["package_id"],
        }

            headers = {
                "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            response = requests.post(
                "https://api.stripe.com/v1/checkout/sessions",
                headers=headers,
                data=payload,
            )

            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()

        except Exception as error:
            print(f"Error creating Stripe Checkout: {error}")
            raise HTTPException(
                status_code=400, detail=f"Stripe Checkout failed: {error}"
            )

    def create_stripe_product(title, description) -> StripeId:
        url = "https://api.stripe.com/v1/products"
        headers = {
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"name": title, "description": description}
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            product_data = response.json()
            return StripeId(id=product_data["id"])
        else:
            raise Exception(f"Failed to create Stripe product: {response.text}")

    def create_stripe_price(stripe_product_id, price) -> StripeId:
        url = "https://api.stripe.com/v1/prices"
        headers = {
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "unit_amount": str(int(price * 100)),
            "currency": "usd",
            "product": stripe_product_id,
            "recurring[interval]": "month",
        }
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            price_data = response.json()
            return StripeId(id=price_data["id"])
        else:
            raise Exception(f"Failed to create Stripe price: {response.text}")

    def update_stripe_subscription_on_stripe(stripe_sub_id, new_price_id):
        try:
            payload = {
                "items[0][price]": new_price_id,
                "proration_behavior": "create_prorations",
            }

            headers = {
                "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            response = requests.post(
                f"https://api.stripe.com/v1/subscriptions/{stripe_sub_id}",
                headers=headers,
                data=payload,
            )

            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()

        except Exception as error:
            print(f"Error updating Stripe subscription: {error}")
            raise HTTPException(
                status_code=400, detail=f"Stripe subscription update failed: {error}"
            )

    def update_subscription(item, stripe_product_id, stripe_price_id):
        item["stripeProductId"] = stripe_product_id.id
        item["stripePriceId"] = stripe_price_id.id
        print("Subscription updated:", item)
        return item
