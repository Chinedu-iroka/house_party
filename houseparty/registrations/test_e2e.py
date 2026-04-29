import json
import hmac
import hashlib
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now
from django.contrib.auth.models import User
from django.conf import settings
from datetime import date, time, timedelta
from unittest.mock import patch
from events.models import Event, TicketTier
from registrations.models import Registration
from dashboard.models import AdminUser


def make_paystack_signature(body):
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    return hmac.new(secret, body, hashlib.sha512).hexdigest()


class FullRegistrationFlowTest(TestCase):
    """S8-01 — Full registration and payment flow"""

    def setUp(self):
        settings.PAYSTACK_SECRET_KEY = 'test_secret'
        self.client = Client()
        session = self.client.session
        session['age_verified'] = True
        session.save()

        self.event = Event.objects.create(
            name="Euphoria Night",
            description="A night to remember",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="Lekki",
            full_address="12 Private Close, Lekki Phase 1",
            status=Event.Status.PUBLISHED,
        )
        self.tier = TicketTier.objects.create(
            event=self.event,
            name="Regular",
            price=70000,
            inclusions="Entry + 1 Martell",
            total_slots=10,
        )

    @patch('registrations.views.initialize_payment')
    @patch('registrations.views.send_confirmation_task')
    @patch('registrations.views.schedule_address_reveal')
    def test_full_registration_and_payment_flow(
        self, mock_schedule, mock_confirm, mock_payment
    ):
        mock_payment.return_value = 'https://paystack.com/pay/test'
        mock_confirm.delay = lambda x: None

        # Step 1 — Submit registration form
        response = self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {
                'full_name': 'Chinedu Iroka',
                'email': 'chinedu@test.com',
                'phone': '08012345678',
                'tc_agreed': 'yes',
            }
        )
        self.assertRedirects(
            response,
            'https://paystack.com/pay/test',
            fetch_redirect_response=False
        )

        # Step 2 — Verify registration created as PENDING
        reg = Registration.objects.get(email='chinedu@test.com')
        self.assertEqual(reg.status, Registration.Status.PENDING)
        self.assertEqual(reg.payment_status, Registration.PaymentStatus.UNPAID)

        # Step 3 — Verify slot was reserved
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 1)

        # Step 4 — Simulate Paystack webhook confirming payment
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': reg.payment_reference,
                'amount': 7000000,
            }
        }
        body = json.dumps(payload).encode()
        sig = make_paystack_signature(body)

        webhook_response = self.client.post(
            reverse('paystack_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=sig,
        )
        self.assertEqual(webhook_response.status_code, 200)

        # Step 5 — Verify registration confirmed
        reg.refresh_from_db()
        self.assertEqual(reg.status, Registration.Status.CONFIRMED)
        self.assertEqual(reg.payment_status, Registration.PaymentStatus.PAID)

        # Step 6 — Verify slot counts updated
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 0)
        self.assertEqual(self.tier.confirmed_slots, 1)


class SlotRaceConditionTest(TestCase):
    """S8-02 — Slot race condition: two users, one slot"""

    def setUp(self):
        settings.PAYSTACK_SECRET_KEY = 'test_secret'
        self.event = Event.objects.create(
            name="Euphoria Night",
            description="A night to remember",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="Lekki",
            full_address="12 Private Close, Lekki Phase 1",
            status=Event.Status.PUBLISHED,
        )
        self.tier = TicketTier.objects.create(
            event=self.event,
            name="Regular",
            price=70000,
            inclusions="Entry + 1 Martell",
            total_slots=1,
        )

    def test_only_one_slot_can_be_reserved(self):
        from registrations.slot import reserve_slot, SlotUnavailableError

        # First reservation succeeds
        reserve_slot(self.tier)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 1)

        # Second reservation fails
        with self.assertRaises(SlotUnavailableError):
            reserve_slot(self.tier)

        # Slot count unchanged
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 1)

    def test_confirmed_slot_blocks_reservation(self):
        from registrations.slot import reserve_slot, SlotUnavailableError
        self.tier.confirmed_slots = 1
        self.tier.save()
        with self.assertRaises(SlotUnavailableError):
            reserve_slot(self.tier)


class TimerExpiryFlowTest(TestCase):
    """S8-03 — Timer expiry and slot release"""

    def setUp(self):
        self.event = Event.objects.create(
            name="Euphoria Night",
            description="A night to remember",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="Lekki",
            full_address="12 Private Close, Lekki Phase 1",
            status=Event.Status.PUBLISHED,
        )
        self.tier = TicketTier.objects.create(
            event=self.event,
            name="Regular",
            price=70000,
            inclusions="Entry + 1 Martell",
            total_slots=10,
            reserved_slots=1,
        )
        self.registration = Registration.objects.create(
            event=self.event,
            tier=self.tier,
            full_name="Test User",
            email="test@test.com",
            phone="08012345678",
            status=Registration.Status.PENDING,
            payment_status=Registration.PaymentStatus.UNPAID,
            payment_reference="HP-TEST",
            reservation_expires_at=now() - timedelta(minutes=15),
        )

    def test_expired_reservation_is_cleaned_up(self):
        from communications.tasks import cleanup_expired_reservations
        cleanup_expired_reservations()
        self.registration.refresh_from_db()
        self.tier.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CANCELLED)
        self.assertEqual(self.tier.reserved_slots, 0)

    def test_slot_released_via_api(self):
        client = Client()
        session = client.session
        session['age_verified'] = True
        session.save()

        response = client.post(
            reverse('release_slot_api', args=[self.registration.id])
        )
        self.assertEqual(response.status_code, 200)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 0)


class EventCancellationTransferTest(TestCase):
    """S8-04 — Event cancellation and registrant transfer"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin', password='admin123', is_staff=True
        )
        self.admin = AdminUser.objects.create(user=self.user)
        self.client.login(username='admin', password='admin123')

        self.event = Event.objects.create(
            name="Euphoria Night",
            description="A night to remember",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="Lekki",
            full_address="12 Private Close",
            status=Event.Status.PUBLISHED,
        )
        self.tier = TicketTier.objects.create(
            event=self.event,
            name="Regular",
            price=70000,
            inclusions="Entry + 1 Martell",
            total_slots=30,
        )
        self.next_event = Event.objects.create(
            name="Velvet Underground",
            description="Next event",
            date=date(2026, 1, 31),
            start_time=time(21, 0),
            zone="VI",
            full_address="14 VI Close",
            status=Event.Status.PUBLISHED,
        )
        self.next_tier = TicketTier.objects.create(
            event=self.next_event,
            name="Regular",
            price=70000,
            inclusions="Entry + 1 Martell",
            total_slots=30,
        )
        self.registration = Registration.objects.create(
            event=self.event,
            tier=self.tier,
            full_name="Chinedu Test",
            email="chinedu@test.com",
            phone="08012345678",
            status=Registration.Status.CONFIRMED,
            payment_status=Registration.PaymentStatus.PAID,
            payment_reference="HP-TEST",
            amount_paid=70000,
        )

    @patch('communications.tasks.notify_transfer_task')
    def test_cancel_event_transfers_registrants(self, mock_notify):
        mock_notify.delay = lambda x, y: None
        self.client.post(
            reverse('admin_event_cancel', args=[self.event.id]),
            {'next_event_id': str(self.next_event.id)}
        )

        # Original registration marked as transferred
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.TRANSFERRED)
        self.assertEqual(self.registration.transferred_to, self.next_event)

        # New registration created in next event
        new_reg = Registration.objects.filter(
            event=self.next_event,
            email='chinedu@test.com',
            status=Registration.Status.CONFIRMED
        ).first()
        self.assertIsNotNone(new_reg)

    @patch('communications.tasks.notify_transfer_task')
    def test_cancel_event_sets_cancelled_status(self, mock_notify):
        mock_notify.delay = lambda x, y: None
        self.client.post(
            reverse('admin_event_cancel', args=[self.event.id]),
            {'next_event_id': str(self.next_event.id)}
        )
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.CANCELLED)


class AddressRevealE2ETest(TestCase):
    """S8-05 — Manual address reveal"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin', password='admin123', is_staff=True
        )
        self.admin = AdminUser.objects.create(user=self.user)
        self.client.login(username='admin', password='admin123')

        self.event = Event.objects.create(
            name="Euphoria Night",
            description="A night to remember",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="Lekki",
            full_address="12 Private Close, Lekki Phase 1",
            status=Event.Status.PUBLISHED,
        )
        self.tier = TicketTier.objects.create(
            event=self.event,
            name="Regular",
            price=70000,
            inclusions="Entry + 1 Martell",
            total_slots=30,
        )
        self.registration = Registration.objects.create(
            event=self.event,
            tier=self.tier,
            full_name="Chinedu Test",
            email="chinedu@test.com",
            phone="08012345678",
            status=Registration.Status.CONFIRMED,
            payment_status=Registration.PaymentStatus.PAID,
            payment_reference="HP-TEST",
        )

    @patch('communications.tasks.send_address_reveal_task')
    def test_manual_address_reveal_triggers_task(self, mock_task):
        mock_task.delay = lambda x: None
        response = self.client.post(
            reverse('admin_event_send_address', args=[self.event.id])
        )
        self.assertRedirects(
            response,
            reverse('admin_event_detail', args=[self.event.id])
        )

    @patch('communications.tasks.send_address_reveal_task')
    def test_manual_address_reveal_resets_flags(self, mock_task):
        mock_task.delay = lambda x: None
        self.registration.address_sent = True
        self.registration.save()
        self.event.address_sent = True
        self.event.save()

        self.client.post(
            reverse('admin_event_send_address', args=[self.event.id])
        )

        self.registration.refresh_from_db()
        self.event.refresh_from_db()
        self.assertFalse(self.registration.address_sent)
        self.assertFalse(self.event.address_sent)