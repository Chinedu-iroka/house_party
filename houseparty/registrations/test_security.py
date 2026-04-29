from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, time
from events.models import Event, TicketTier
from dashboard.models import AdminUser


class SecurityTest(TestCase):

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

    def test_full_address_not_in_homepage(self):
        """S8-06 — full_address never appears on public pages"""
        response = self.client.get(reverse('homepage'))
        self.assertNotIn(b'12 Private Close', response.content)

    def test_full_address_not_in_event_detail(self):
        """S8-06 — full_address never appears on event detail page"""
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        self.assertNotIn(b'12 Private Close', response.content)

    def test_full_address_not_in_register_page(self):
        """S8-06 — full_address never appears on registration page"""
        response = self.client.get(
            reverse('register', args=[self.event.id, self.tier.id])
        )
        self.assertNotIn(b'12 Private Close', response.content)

    def test_admin_dashboard_redirects_unauthenticated(self):
        """S8-07 — admin routes reject unauthenticated requests"""
        client = Client()
        response = client.get(reverse('admin_dashboard_home'))
        self.assertRedirects(response, '/dashboard/login/?next=/dashboard/')

    def test_admin_event_create_redirects_unauthenticated(self):
        """S8-07 — create event route protected"""
        client = Client()
        response = client.get(reverse('admin_event_create'))
        self.assertEqual(response.status_code, 302)

    def test_webhook_rejects_missing_signature(self):
        """S8-08 — webhook rejects requests with no signature"""
        import json
        response = self.client.post(
            reverse('paystack_webhook'),
            data=json.dumps({'event': 'charge.success'}).encode(),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_rejects_invalid_signature(self):
        """S8-08 — webhook rejects requests with wrong signature"""
        import json
        response = self.client.post(
            reverse('paystack_webhook'),
            data=json.dumps({'event': 'charge.success'}).encode(),
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='completelywrongsignature',
        )
        self.assertEqual(response.status_code, 400)

    def test_age_gate_blocks_direct_url_access(self):
        """S8-09 — age gate cannot be bypassed via direct URL"""
        client = Client()
        response = client.get(reverse('homepage'))
        self.assertRedirects(response, reverse('age_gate'))

    def test_draft_event_not_accessible_publicly(self):
        """S8-09 — draft events return 404 to public"""
        self.event.status = Event.Status.DRAFT
        self.event.save()
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        self.assertEqual(response.status_code, 404)

    def test_cancelled_event_not_accessible_publicly(self):
        """S8-09 — cancelled events return 404 to public"""
        self.event.status = Event.Status.CANCELLED
        self.event.save()
        response = self.client.get(reverse('event_detail', args=[self.event.id]))
        self.assertEqual(response.status_code, 404)