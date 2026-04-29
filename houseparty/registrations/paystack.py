import hmac
import hashlib
import requests
from django.conf import settings


PAYSTACK_BASE_URL = "https://api.paystack.co"


def initialize_payment(reference, amount, email, registration_id):
    """
    Initialise a Paystack transaction.
    Returns the authorization URL to redirect the user to.
    """
    secret_key = settings.PAYSTACK_SECRET_KEY

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    # Paystack expects amount in kobo (multiply naira by 100)
    payload = {
        "reference": reference,
        "amount": int(amount * 100),
        "email": email,
        "currency": "NGN",
        "metadata": {
            "registration_id": registration_id,
        },
        "callback_url": f"{settings.SITE_URL}/registration/success/{registration_id}/",
    }

    try:
        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=headers,
            timeout=10,
        )
        data = response.json()

        if data.get("status"):
            return data["data"]["authorization_url"]
        return None

    except Exception as e:
        print(f"Paystack init error: {e}")
        return None


def verify_webhook_signature(request_body, signature):
    """
    Verify that a webhook request genuinely came from Paystack.
    Uses HMAC-SHA512 with the Paystack secret key.
    """
    secret_key = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    expected = hmac.new(secret_key, request_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def refund_transaction(reference):
    """
    Trigger a full refund for a transaction via Paystack API.
    """
    secret_key = settings.PAYSTACK_SECRET_KEY

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    payload = {"transaction": reference}

    try:
        response = requests.post(
            f"{PAYSTACK_BASE_URL}/refund",
            json=payload,
            headers=headers,
            timeout=10,
        )
        return response.json()
    except Exception as e:
        print(f"Paystack refund error: {e}")
        return None