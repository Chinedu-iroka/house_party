from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now
from datetime import date, time, timedelta
from unittest.mock import patch
from events.models import Event, TicketTier
from .models import Registration
from .slot import reserve_slot, release_slot, SlotUnavailableError


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


class SlotReservationTest(TestCase):

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
            total_slots=5,
        )

    def test_reserve_slot_increments_reserved(self):
        reserve_slot(self.tier)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 1)

    def test_reserve_slot_multiple_times(self):
        reserve_slot(self.tier)
        reserve_slot(self.tier)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 2)

    def test_reserve_slot_raises_when_full(self):
        self.tier.confirmed_slots = 5
        self.tier.save()
        with self.assertRaises(SlotUnavailableError):
            reserve_slot(self.tier)

    def test_reserve_slot_raises_when_reserved_full(self):
        self.tier.reserved_slots = 5
        self.tier.save()
        with self.assertRaises(SlotUnavailableError):
            reserve_slot(self.tier)

    def test_reserve_slot_raises_when_combined_full(self):
        self.tier.reserved_slots = 2
        self.tier.confirmed_slots = 3
        self.tier.save()
        with self.assertRaises(SlotUnavailableError):
            reserve_slot(self.tier)

    def test_release_slot_decrements_reserved(self):
        self.tier.reserved_slots = 3
        self.tier.save()
        release_slot(self.tier)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 2)

    def test_release_slot_never_goes_negative(self):
        self.tier.reserved_slots = 0
        self.tier.save()
        release_slot(self.tier)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 0)


class RegistrationFormTest(TestCase):

    def setUp(self):
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
            total_slots=30,
        )

    def test_register_get_returns_200(self):
        response = self.client.get(
            reverse('register', args=[self.event.id, self.tier.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_register_uses_correct_template(self):
        response = self.client.get(
            reverse('register', args=[self.event.id, self.tier.id])
        )
        self.assertTemplateUsed(response, 'public/register.html')

    def test_register_missing_name_shows_error(self):
        response = self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {'full_name': '', 'email': 'test@test.com',
             'phone': '08012345678', 'tc_agreed': 'yes'}
        )
        self.assertIn('full_name', response.context['errors'])

    def test_register_invalid_email_shows_error(self):
        response = self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {'full_name': 'Test User', 'email': 'notanemail',
             'phone': '08012345678', 'tc_agreed': 'yes'}
        )
        self.assertIn('email', response.context['errors'])

    def test_register_missing_phone_shows_error(self):
        response = self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {'full_name': 'Test User', 'email': 'test@test.com',
             'phone': '', 'tc_agreed': 'yes'}
        )
        self.assertIn('phone', response.context['errors'])

    def test_register_missing_tc_shows_error(self):
        response = self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {'full_name': 'Test User', 'email': 'test@test.com',
             'phone': '08012345678'}
        )
        self.assertIn('tc_agreed', response.context['errors'])

    def test_register_sold_out_shows_sold_out_page(self):
        self.tier.confirmed_slots = 30
        self.tier.save()
        response = self.client.get(
            reverse('register', args=[self.event.id, self.tier.id])
        )
        self.assertTemplateUsed(response, 'public/sold_out.html')

    @patch('registrations.views.initialize_payment')
    def test_valid_form_creates_pending_registration(self, mock_payment):
        mock_payment.return_value = 'https://paystack.com/pay/test'
        response = self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {'full_name': 'Chinedu Test', 'email': 'chinedu@test.com',
             'phone': '08012345678', 'tc_agreed': 'yes'}
        )
        reg = Registration.objects.filter(email='chinedu@test.com').first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.status, Registration.Status.PENDING)
        self.assertEqual(reg.payment_status, Registration.PaymentStatus.UNPAID)

    @patch('registrations.views.initialize_payment')
    def test_valid_form_reserves_slot(self, mock_payment):
        mock_payment.return_value = 'https://paystack.com/pay/test'
        self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {'full_name': 'Chinedu Test', 'email': 'chinedu@test.com',
             'phone': '08012345678', 'tc_agreed': 'yes'}
        )
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 1)

    @patch('registrations.views.initialize_payment')
    def test_valid_form_redirects_to_paystack(self, mock_payment):
        mock_payment.return_value = 'https://paystack.com/pay/test'
        response = self.client.post(
            reverse('register', args=[self.event.id, self.tier.id]),
            {'full_name': 'Chinedu Test', 'email': 'chinedu@test.com',
             'phone': '08012345678', 'tc_agreed': 'yes'}
        )
        self.assertRedirects(
            response,
            'https://paystack.com/pay/test',
            fetch_redirect_response=False
        )