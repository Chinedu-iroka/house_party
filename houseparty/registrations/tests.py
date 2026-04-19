from django.test import TestCase
from django.utils import timezone
from datetime import date, time
from events.models import Event, TicketTier
from .models import Registration


class RegistrationModelTest(TestCase):

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
            status=Registration.Status.PENDING,
            payment_status=Registration.PaymentStatus.UNPAID,
        )

    def test_registration_created_successfully(self):
        self.assertEqual(self.registration.full_name, "Chinedu Test")
        self.assertEqual(self.registration.status, Registration.Status.PENDING)
        self.assertEqual(self.registration.payment_status, Registration.PaymentStatus.UNPAID)

    def test_registration_default_status(self):
        self.assertEqual(self.registration.status, "PENDING")

    def test_is_confirmed_false_when_pending(self):
        self.assertFalse(self.registration.is_confirmed)

    def test_is_confirmed_true_when_paid(self):
        self.registration.status = Registration.Status.CONFIRMED
        self.registration.payment_status = Registration.PaymentStatus.PAID
        self.registration.save()
        self.assertTrue(self.registration.is_confirmed)

    def test_registration_str(self):
        self.assertIn("Chinedu Test", str(self.registration))
        self.assertIn("Euphoria Night", str(self.registration))