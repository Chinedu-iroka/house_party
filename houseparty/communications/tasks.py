from celery import shared_task
from celery.utils.log import get_task_logger
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

        # S6-03 — Duplicate send protection at event level
        if event.address_sent:
            logger.info(f"Address already sent for {event.name} — skipping")
            return

        # Get only confirmed registrants who haven't received the address yet
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
            logger.info(f"Address sent to {registration.email}")

        # Mark event as address revealed
        event.address_sent = True
        event.save(update_fields=['address_sent'])

        logger.info(f"Address reveal complete for: {event.name}")

    except Exception as exc:
        logger.error(f"send_address_reveal_task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_reservations(self):
    try:
        from registrations.models import Registration
        from events.models import TicketTier
        from django.db import transaction

        expired = Registration.objects.filter(
            status=Registration.Status.PENDING,
            reservation_expires_at__lt=now(),
        )

        count = 0
        for registration in expired:
            with transaction.atomic():
                tier = TicketTier.objects.select_for_update().get(
                    id=registration.tier.id
                )
                tier.reserved_slots = max(0, tier.reserved_slots - 1)
                tier.save()

            registration.status = Registration.Status.CANCELLED
            registration.save(update_fields=['status'])
            count += 1
            logger.info(f"Expired reservation released for {registration.email}")

        logger.info(f"Cleanup complete — {count} expired reservations released")

    except Exception as exc:
        logger.error(f"cleanup_expired_reservations failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


def schedule_address_reveal(registration):
    """
    Schedule the address reveal task for 24 hours before the event.
    Called when a registration is confirmed.
    S6-04 — If already past the window, send immediately.
    """
    import pytz
    from django.utils.timezone import make_aware

    event = registration.event
    lagos_tz = pytz.timezone('Africa/Lagos')

    # Calculate reveal datetime — 24 hours before event start
    naive_event_dt = datetime.combine(event.date, event.start_time)
    event_dt = make_aware(naive_event_dt, lagos_tz)
    reveal_dt = event_dt - timedelta(hours=24)

    if now() >= reveal_dt:
        # Already past the 24hr window — send immediately (late registrant)
        logger.info(f"Past reveal window for {event.name} — sending address immediately")
        send_address_reveal_task.delay(str(event.id))
    else:
        # Schedule for exactly 24 hours before
        send_address_reveal_task.apply_async(
            args=[str(event.id)],
            eta=reveal_dt,
        )
        logger.info(f"Address reveal scheduled for {reveal_dt} for event {event.name}")



@shared_task(bind=True, max_retries=3)
def notify_transfer_task(self, original_event_id, next_event_id):
    try:
        from events.models import Event
        from registrations.models import Registration
        from .email import send_transfer_email
        from .sms import send_transfer_sms

        original_event = Event.objects.get(id=original_event_id)
        next_event = Event.objects.get(id=next_event_id)

        transferred = Registration.objects.filter(
            event=original_event,
            status=Registration.Status.TRANSFERRED,
        )

        for registration in transferred:
            send_transfer_email(registration, original_event, next_event)
            send_transfer_sms(registration, next_event)
            logger.info(f"Transfer notification sent to {registration.email}")

    except Exception as exc:
        logger.error(f"notify_transfer_task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)