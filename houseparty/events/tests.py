import uuid
from django.test import TestCase, Client
from django.utils import timezone
from datetime import date, time
from .models import Event, TicketTier
from django.urls import reverse


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






class HomepageViewTest(TestCase):

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

    def test_homepage_returns_200(self):
        response = self.client.get(reverse('homepage'))
        self.assertEqual(response.status_code, 200)

    def test_homepage_uses_correct_template(self):
        response = self.client.get(reverse('homepage'))
        self.assertTemplateUsed(response, 'public/homepage.html')

    def test_homepage_shows_published_events(self):
        response = self.client.get(reverse('homepage'))
        self.assertEqual(len(response.context['events']), 1)
        self.assertEqual(response.context['events'][0]['event'].name, "Euphoria Night")

    def test_homepage_does_not_show_draft_events(self):
        Event.objects.create(
            name="Draft Event",
            description="Not visible",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="VI",
            full_address="Private",
            status=Event.Status.DRAFT,
        )
        response = self.client.get(reverse('homepage'))
        self.assertEqual(len(response.context['events']), 1)

    def test_homepage_slot_data_attached(self):
        response = self.client.get(reverse('homepage'))
        event_data = response.context['events'][0]
        self.assertIn('tiers', event_data)
        self.assertEqual(event_data['tiers'][0]['available'], 30)
        self.assertFalse(event_data['tiers'][0]['is_sold_out'])

    def test_homepage_marks_sold_out_correctly(self):
        self.tier.confirmed_slots = 30
        self.tier.save()
        response = self.client.get(reverse('homepage'))
        event_data = response.context['events'][0]
        self.assertTrue(event_data['is_sold_out'])


class EventDetailViewTest(TestCase):

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

    def test_event_detail_returns_200(self):
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)

    def test_event_detail_uses_correct_template(self):
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        self.assertTemplateUsed(response, 'public/event_detail.html')

    def test_event_detail_shows_correct_event(self):
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        self.assertEqual(response.context['event'].name, "Euphoria Night")

    def test_event_detail_full_address_not_in_context(self):
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        content = response.content.decode()
        self.assertNotIn("12 Private Close", content)

    def test_event_detail_404_for_draft_event(self):
        draft = Event.objects.create(
            name="Draft Event",
            description="Not visible",
            date=date(2025, 12, 31),
            start_time=time(21, 0),
            zone="VI",
            full_address="Private",
            status=Event.Status.DRAFT,
        )
        response = self.client.get(reverse('event_detail', args=[draft.id]))
        self.assertEqual(response.status_code, 404)

    def test_event_detail_404_for_invalid_uuid(self):
        fake_id = uuid.uuid4()
        response = self.client.get(reverse('event_detail', args=[fake_id]))
        self.assertEqual(response.status_code, 404)


class SlotCountAPITest(TestCase):

    def setUp(self):
        self.client = Client()
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
            reserved_slots=5,
            confirmed_slots=10,
        )

    def test_slot_api_returns_200(self):
        response = self.client.get(reverse('slot_count_api', args=[self.tier.id]))
        self.assertEqual(response.status_code, 200)

    def test_slot_api_returns_correct_available(self):
        response = self.client.get(reverse('slot_count_api', args=[self.tier.id]))
        data = response.json()
        self.assertEqual(data['available'], 15)

    def test_slot_api_returns_correct_total(self):
        response = self.client.get(reverse('slot_count_api', args=[self.tier.id]))
        data = response.json()
        self.assertEqual(data['total'], 30)

    def test_slot_api_sold_out_false(self):
        response = self.client.get(reverse('slot_count_api', args=[self.tier.id]))
        data = response.json()
        self.assertFalse(data['sold_out'])

    def test_slot_api_sold_out_true(self):
        self.tier.confirmed_slots = 30
        self.tier.reserved_slots = 0
        self.tier.save()
        response = self.client.get(reverse('slot_count_api', args=[self.tier.id]))
        data = response.json()
        self.assertTrue(data['sold_out'])

    def test_slot_api_404_for_invalid_tier(self):
        fake_id = uuid.uuid4()
        response = self.client.get(reverse('slot_count_api', args=[fake_id]))
        self.assertEqual(response.status_code, 404)