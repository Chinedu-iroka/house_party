import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone, message):
    try:
        api_key = settings.SMS_API_KEY
        sender_id = settings.SMS_SENDER_ID

        response = requests.post(
            "https://api.ng.termii.com/api/sms/send",
            json={
                "to": phone,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "api_key": api_key,
                "channel": "generic",
            },
            timeout=10,
        )
        logger.info(f"SMS sent to {phone}: {response.status_code}")
        return response.json()

    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return None


def send_confirmation_sms(registration):
    message = (
        f"Confirmed! {registration.event.name} | "
        f"{registration.tier.name} | "
        f"{registration.event.date.strftime('%d %b %Y')} | "
        f"Zone: {registration.event.zone} | "
        f"Full address sent 24hrs before."
    )
    send_sms(registration.phone, message)


def send_address_sms(registration, full_address):
    message = (
        f"{registration.event.name} is tomorrow! "
        f"Address: {full_address} | "
        f"Time: {registration.event.start_time.strftime('%I:%M %p')}"
    )
    send_sms(registration.phone, message)



def send_transfer_sms(registration, next_event):
    message = (
        f"Update: Your HouseParty registration has been moved to "
        f"{next_event.name} on {next_event.date.strftime('%d %b %Y')}. "
        f"Check your email for details."
    )
    send_sms(registration.phone, message)