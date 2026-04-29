from django.test import TestCase
from django.utils.timezone import now
from datetime import date, time, timedelta
from unittest.mock import patch, MagicMock
from events.models import Event, TicketTier
from registrations.models import Registration
from communications.tasks import (
    send_address_reveal_task,
    cleanup_expired_reservations,
    schedule_address_reveal,
)


class AddressRevealTaskTest(TestCase):

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
            payment_reference="HP-TEST123",
        )

    @patch('communications.email.send_address_email')
    @patch('communications.sms.send_address_sms')
    def test_address_reveal_sends_to_confirmed_registrants(self, mock_sms, mock_email):
        send_address_reveal_task(str(self.event.id))
        mock_email.assert_called_once_with(self.registration, self.event.full_address)
        mock_sms.assert_called_once_with(self.registration, self.event.full_address)

    @patch('communications.email.send_address_email')
    @patch('communications.sms.send_address_sms')
    def test_address_reveal_marks_registration_as_sent(self, mock_sms, mock_email):
        send_address_reveal_task(str(self.event.id))
        self.registration.refresh_from_db()
        self.assertTrue(self.registration.address_sent)

    @patch('communications.email.send_address_email')
    @patch('communications.sms.send_address_sms')
    def test_address_reveal_marks_event_as_sent(self, mock_sms, mock_email):
        send_address_reveal_task(str(self.event.id))
        self.event.refresh_from_db()
        self.assertTrue(self.event.address_sent)

    @patch('communications.email.send_address_email')
    @patch('communications.sms.send_address_sms')
    def test_address_reveal_skips_if_already_sent(self, mock_sms, mock_email):
        self.event.address_sent = True
        self.event.save()
        send_address_reveal_task(str(self.event.id))
        mock_email.assert_not_called()
        mock_sms.assert_not_called()

    @patch('communications.email.send_address_email')
    @patch('communications.sms.send_address_sms')
    def test_address_reveal_skips_pending_registrants(self, mock_sms, mock_email):
        self.registration.status = Registration.Status.PENDING
        self.registration.save()
        send_address_reveal_task(str(self.event.id))
        mock_email.assert_not_called()

    @patch('communications.email.send_address_email')
    @patch('communications.sms.send_address_sms')
    def test_address_reveal_skips_already_notified_registrants(self, mock_sms, mock_email):
        self.registration.address_sent = True
        self.registration.save()
        send_address_reveal_task(str(self.event.id))
        mock_email.assert_not_called()


class ExpiryCleanupTaskTest(TestCase):

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
            total_slots=30,
            reserved_slots=2,
        )

    def _make_registration(self, expires_at):
        return Registration.objects.create(
            event=self.event,
            tier=self.tier,
            full_name="Test User",
            email="test@test.com",
            phone="08012345678",
            status=Registration.Status.PENDING,
            payment_status=Registration.PaymentStatus.UNPAID,
            payment_reference=f"HP-{Registration.objects.count()}",
            reservation_expires_at=expires_at,
        )

    def test_expired_registration_is_cancelled(self):
        expired_time = now() - timedelta(minutes=15)
        reg = self._make_registration(expired_time)
        cleanup_expired_reservations()
        reg.refresh_from_db()
        self.assertEqual(reg.status, Registration.Status.CANCELLED)

    def test_expired_registration_releases_slot(self):
        expired_time = now() - timedelta(minutes=15)
        self._make_registration(expired_time)
        initial_reserved = self.tier.reserved_slots
        cleanup_expired_reservations()
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, initial_reserved - 1)

    def test_active_reservation_not_cancelled(self):
        active_time = now() + timedelta(minutes=5)
        reg = self._make_registration(active_time)
        cleanup_expired_reservations()
        reg.refresh_from_db()
        self.assertEqual(reg.status, Registration.Status.PENDING)

    def test_multiple_expired_registrations_all_cancelled(self):
        expired_time = now() - timedelta(minutes=15)
        reg1 = self._make_registration(expired_time)
        reg2 = self._make_registration(expired_time)
        cleanup_expired_reservations()
        reg1.refresh_from_db()
        reg2.refresh_from_db()
        self.assertEqual(reg1.status, Registration.Status.CANCELLED)
        self.assertEqual(reg2.status, Registration.Status.CANCELLED)

    def test_reserved_slots_never_go_negative(self):
        self.tier.reserved_slots = 0
        self.tier.save()
        expired_time = now() - timedelta(minutes=15)
        self._make_registration(expired_time)
        cleanup_expired_reservations()
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 0)

    def test_confirmed_registrations_not_touched(self):
        reg = Registration.objects.create(
            event=self.event,
            tier=self.tier,
            full_name="Confirmed User",
            email="confirmed@test.com",
            phone="08012345678",
            status=Registration.Status.CONFIRMED,
            payment_status=Registration.PaymentStatus.PAID,
            payment_reference="HP-CONFIRMED",
            reservation_expires_at=now() - timedelta(minutes=15),
        )
        cleanup_expired_reservations()
        reg.refresh_from_db()
        self.assertEqual(reg.status, Registration.Status.CONFIRMED)


class ScheduleAddressRevealTest(TestCase):

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
            payment_reference="HP-TEST123",
        )

    @patch('communications.tasks.send_address_reveal_task')
    def test_past_window_sends_immediately(self, mock_task):
        # Event date in the past means we're past the reveal window
        self.event.date = date(2020, 1, 1)
        self.event.save()
        self.registration.event = self.event
        schedule_address_reveal(self.registration)
        mock_task.delay.assert_called_once_with(str(self.event.id))

    @patch('communications.tasks.send_address_reveal_task')
    def test_future_window_schedules_task(self, mock_task):
        # Event date far in the future
        from datetime import date as d
        self.event.date = date(2030, 1, 1)
        self.event.save()
        self.registration.event = self.event
        schedule_address_reveal(self.registration)
        mock_task.apply_async.assert_called_once()