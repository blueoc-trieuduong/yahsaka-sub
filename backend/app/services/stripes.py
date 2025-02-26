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
            "success_url": "https://truongnguyen94.wixsite.com/yashaka-timesheet/thankyou-page",
            "cancel_url": "https://truongnguyen94.wixsite.com/yashaka-timesheet",
            "line_items[0][price]": data["priceId"], 
            "line_items[0][quantity]": "1",
            # "subscription_data[trial_from_plan]": "false",
            # "subscription_data[proration_behavior]": "create_prorations",  
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
    
    def create_proration_checkout(data):
        try:
            headers = {
                "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            response = requests.get(
                f"https://api.stripe.com/v1/subscriptions/{data['subscription_id']}",
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not retrieve subscription")
            print('res sucess')
            subscription = response.json()
            subscription_item_id = subscription["items"]["data"][0]["id"]
            customer_id = subscription["customer"]
            preview_params = {
                "customer": customer_id,
                "subscription": data["subscription_id"],
                "subscription_items[0][id]": subscription_item_id,
                "subscription_items[0][price]": data["price_id"]
            }
            print('ready battle')
            preview_response = requests.get(
                "https://api.stripe.com/v1/invoices/upcoming",
                headers=headers,
                params=preview_params
            )

            
            if preview_response.status_code != 200:
                print('loi o day ne')
                print(preview_response.status_code)
                raise HTTPException(status_code=400, detail="Failed to preview prorated charges")
            
            preview_data = preview_response.json()
            prorated_amount = sum(
                item["amount"] for item in preview_data["lines"]["data"] if item.get("proration", False)
            )


            print('previewData', preview_data)
            print('prorated_amount', prorated_amount)

            success_url = "https://truongnguyen94.wixsite.com/yashaka-timesheet/thankyou-page"
            cancel_url = "https://truongnguyen94.wixsite.com/yashaka-timesheet?upgrade_cancelled=true"
            print('preIf')
            if prorated_amount > 0:
                print('inIf')
                checkout_params = {
                    "mode": "payment",
                    "success_url": success_url,
                    "cancel_url": cancel_url,
                    "line_items[0][price_data][currency]": "usd",  
                    "line_items[0][price_data][product_data][name]": "Plan Upgrade - Prorated Amount",
                    "line_items[0][price_data][unit_amount]": prorated_amount,
                    "line_items[0][quantity]": 1,
                    "customer": customer_id,
                    "payment_intent_data[metadata][subscription_id]": data["subscription_id"],
                    "payment_intent_data[metadata][new_price_id]": data["price_id"],
                    "payment_intent_data[metadata][org_id]": data["org_id"],
                    "payment_intent_data[metadata][package_id]": data["package_id"],
                }
                print('outif')
                
                checkout_response = requests.post(
                    "https://api.stripe.com/v1/checkout/sessions",
                    headers=headers,
                    data=checkout_params
                )
                print('response', checkout_response)
                print('response', checkout_response.status_code)
                
                if checkout_response.status_code != 200:
                    print('asdfadsfasssss')
                    raise HTTPException(status_code=400, detail="Failed to create checkout session")
                print('response', checkout_response.json())
                return checkout_response.json().get("url")
            
            else:
                print('else')
                update_params = {
                    "items[0][id]": subscription_item_id,
                    "items[0][price]": data["price_id"],
                    "metadata[org_id]": data["org_id"],
                    "metadata[package_id]": data["package_id"],
                }
                
                update_response = requests.post(
                    f"https://api.stripe.com/v1/subscriptions/{data['subscription_id']}",
                    headers=headers,
                    data=update_params
                )
                
                if update_response.status_code != 200:
                    raise HTTPException(status_code=400, detail="Failed to update subscription")
                
                return success_url
        
        except Exception as error:
            print(f"Error in subscription upgrade process: {error}")
            raise HTTPException(
                status_code=400, detail=f"Subscription upgrade failed: {error}"
            )
