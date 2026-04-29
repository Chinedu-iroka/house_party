from celery import shared_task
from django.utils.timezone import now
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_confirmation_task(self, registration_id):
    try:
        from registrations.models import Registration
        from .email import send_confirmation_email
        from .sms import send_confirmation_sms
        from .pdf import generate_invoice

        registration = Registration.objects.get(id=registration_id)

        # Generate PDF invoice
        pdf_buffer = generate_invoice(registration)

        # Send confirmation email with PDF
        send_confirmation_email(registration, pdf_buffer)

        # Send confirmation SMS
        send_confirmation_sms(registration)

        # Mark invoice as sent
        registration.invoice_sent = True
        registration.save(update_fields=['invoice_sent'])

        logger.info(f"Confirmation sent to {registration.email}")

    except Exception as exc:
        logger.error(f"send_confirmation_task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_address_reveal_task(self, event_id):
    try:
        from events.models import Event
        from registrations.models import Registration
        from .email import send_address_email
        from .sms import send_address_sms

        event = Event.objects.get(id=event_id)

        if event.address_sent:
            logger.info(f"Address already sent for event {event.name} — skipping")
            return

        registrations = Registration.objects.filter(
            event=event,
            status='CONFIRMED',
            address_sent=False,
        )

        for registration in registrations:
            send_address_email(registration, event.full_address)
            send_address_sms(registration, event.full_address)
            registration.address_sent = True
            registration.save(update_fields=['address_sent'])

        event.address_sent = True
        event.save(update_fields=['address_sent'])

        logger.info(f"Address reveal complete for event: {event.name}")

    except Exception as exc:
        logger.error(f"send_address_reveal_task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


def schedule_address_reveal(registration):
    from events.models import Event
    event = registration.event
    reveal_datetime = datetime.combine(event.date, event.start_time) - timedelta(hours=24)

    # Make timezone aware
    from django.utils.timezone import make_aware
    import pytz
    lagos_tz = pytz.timezone('Africa/Lagos')
    reveal_datetime = make_aware(reveal_datetime, lagos_tz)

    if now() >= reveal_datetime:
        # Already past the 24hr window — send immediately
        send_address_reveal_task.delay(str(event.id))
    else:
        send_address_reveal_task.apply_async(
            args=[str(event.id)],
            eta=reveal_datetime
        )