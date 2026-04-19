from django.test import TestCase
from django.utils import timezone
from datetime import date, time
from .models import Event, TicketTier


class EventModelTest(TestCase):

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

    def test_event_created_successfully(self):
        self.assertEqual(self.event.name, "Euphoria Night")
        self.assertEqual(self.event.status, Event.Status.PUBLISHED)

    def test_event_default_status_is_draft(self):
        event = Event.objects.create(
            name="New Event",
            description="TBD",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="VI",
            full_address="Private",
        )
        self.assertEqual(event.status, Event.Status.DRAFT)

    def test_event_str(self):
        self.assertIn("Euphoria Night", str(self.event))

    def test_event_is_published_property(self):
        self.assertTrue(self.event.is_published)

    def test_event_ordering_by_date(self):
        Event.objects.create(
            name="Later Event",
            description="TBD",
            date=date(2026, 1, 15),
            start_time=time(21, 0),
            zone="Ikoyi",
            full_address="Private",
        )
        events = Event.objects.all()
        self.assertEqual(events[0].name, "Euphoria Night")


class TicketTierModelTest(TestCase):

    def setUp(self):
        self.event = Event.objects.create(
            name="Euphoria Night",
            description="A night to remember",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="Lekki",
            full_address="12 Private Close, Lekki Phase 1",
        )
        self.tier = TicketTier.objects.create(
            event=self.event,
            name="Regular",
            price=70000,
            inclusions="Entry + 1 Martell",
            total_slots=30,
            reserved_slots=5,
            confirmed_slots=10,
        )

    def test_tier_created_successfully(self):
        self.assertEqual(self.tier.name, "Regular")
        self.assertEqual(self.tier.total_slots, 30)

    def test_available_slots_calculation(self):
        # 30 - 5 reserved - 10 confirmed = 15
        self.assertEqual(self.tier.available_slots, 15)

    def test_available_slots_never_negative(self):
        self.tier.reserved_slots = 20
        self.tier.confirmed_slots = 20
        self.tier.save()
        self.assertEqual(self.tier.available_slots, 0)

    def test_is_sold_out_false(self):
        self.assertFalse(self.tier.is_sold_out)

    def test_is_sold_out_true(self):
        self.tier.confirmed_slots = 30
        self.tier.reserved_slots = 0
        self.tier.save()
        self.assertTrue(self.tier.is_sold_out)

    def test_fill_percentage(self):
        # 5 + 10 = 15 out of 30 = 50%
        self.assertEqual(self.tier.fill_percentage, 50)

    def test_tier_str(self):
        self.assertIn("Regular", str(self.tier))
        self.assertIn("Euphoria Night", str(self.tier))


from django.test import TestCase, Client
from django.urls import reverse


class AgeGateViewTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_age_gate_renders_on_first_visit(self):
        response = self.client.get(reverse('age_gate'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public/age_gate.html')

    def test_homepage_redirects_to_age_gate_without_session(self):
        response = self.client.get(reverse('homepage'))
        self.assertRedirects(response, reverse('age_gate'))

    def test_age_gate_yes_sets_session_and_redirects(self):
        response = self.client.post(reverse('age_gate'), {'age_confirm': 'yes'})
        self.assertRedirects(response, reverse('homepage'))
        self.assertTrue(self.client.session.get('age_verified'))

    def test_age_gate_no_redirects_to_exit(self):
        response = self.client.post(reverse('age_gate'), {'age_confirm': 'no'})
        self.assertRedirects(response, reverse('age_exit'))

    def test_age_gate_skips_if_already_verified(self):
        session = self.client.session
        session['age_verified'] = True
        session.save()
        response = self.client.get(reverse('age_gate'))
        self.assertRedirects(response, reverse('homepage'))

    def test_homepage_accessible_after_age_verification(self):
        session = self.client.session
        session['age_verified'] = True
        session.save()
        response = self.client.get(reverse('homepage'))
        self.assertEqual(response.status_code, 200)

    def test_age_exit_page_renders(self):
        response = self.client.get(reverse('age_exit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public/age_exit.html')