import logging
from django.core.mail import EmailMessage
from django.conf import settings

logger = logging.getLogger(__name__)


def send_confirmation_email(registration, pdf_buffer):
    try:
        subject = f"You're registered — {registration.event.name}"
        body = f"""Hi {registration.full_name},

Your registration for {registration.event.name} has been confirmed!

Event Details:
- Tier: {registration.tier.name} ({registration.tier.inclusions})
- Date: {registration.event.date.strftime('%A, %d %B %Y')}
- Time: {registration.event.start_time.strftime('%I:%M %p')}
- Zone: {registration.event.zone}

Your full address will be sent to you 24 hours before the event.

Please find your invoice attached.

See you there,
HouseParty
"""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.email],
        )

        email.attach(
            f"HouseParty_Invoice_{registration.payment_reference}.pdf",
            pdf_buffer.read(),
            'application/pdf'
        )

        email.send()
        logger.info(f"Confirmation email sent to {registration.email}")

    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        raise


def send_address_email(registration, full_address):
    try:
        subject = f"Your event is tomorrow — here is the address"
        body = f"""Hi {registration.full_name},

Your event is tomorrow! Here are your final details:

Event: {registration.event.name}
Date: {registration.event.date.strftime('%A, %d %B %Y')}
Time: {registration.event.start_time.strftime('%I:%M %p')}
Address: {full_address}

See you there,
HouseParty
"""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.email],
        )
        email.send()
        logger.info(f"Address email sent to {registration.email}")

    except Exception as e:
        logger.error(f"Failed to send address email: {e}")
        raise



def send_transfer_email(registration, original_event, next_event):
    try:
        subject = f"Your registration has been moved — {next_event.name}"
        body = f"""Hi {registration.full_name},

We want to let you know that {original_event.name} has been cancelled or postponed.

Your registration has been automatically transferred to:

Event: {next_event.name}
Date: {next_event.date.strftime('%A, %d %B %Y')}
Time: {next_event.start_time.strftime('%I:%M %p')}
Zone: {next_event.zone}

Your payment has been carried over — no action is needed from you.
You will receive the full address 24 hours before the new event date.

Thank you for your understanding,
HouseParty
"""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.email],
        )
        email.send()
        logger.info(f"Transfer email sent to {registration.email}")
    except Exception as e:
        logger.error(f"Failed to send transfer email: {e}")
        raise