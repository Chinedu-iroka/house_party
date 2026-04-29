import json
import hmac
import hashlib
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from datetime import date, time
from unittest.mock import patch
from events.models import Event, TicketTier
from registrations.models import Registration


def make_signature(body):
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    return hmac.new(secret, body, hashlib.sha512).hexdigest()


class PaystackWebhookTest(TestCase):

    def setUp(self):
        self.client = Client()
        settings.PAYSTACK_SECRET_KEY = 'test_secret_key'

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
            reserved_slots=1,
        )
        self.registration = Registration.objects.create(
            event=self.event,
            tier=self.tier,
            full_name="Chinedu Test",
            email="chinedu@test.com",
            phone="08012345678",
            status=Registration.Status.PENDING,
            payment_status=Registration.PaymentStatus.UNPAID,
            payment_reference="HP-TEST123",
        )

    def _post_webhook(self, payload):
        body = json.dumps(payload).encode('utf-8')
        signature = make_signature(body)
        return self.client.post(
            reverse('paystack_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

    def test_webhook_rejects_invalid_signature(self):
        body = json.dumps({'event': 'charge.success'}).encode()
        response = self.client.post(
            reverse('paystack_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='invalidsignature',
        )
        self.assertEqual(response.status_code, 400)

    @patch('registrations.views.send_confirmation_task')
    @patch('registrations.views.schedule_address_reveal')
    def test_charge_success_confirms_registration(self, mock_schedule, mock_confirm):
        mock_confirm.delay = lambda x: None
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': 'HP-TEST123',
                'amount': 7000000,
            }
        }
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        self.assertEqual(self.registration.payment_status, Registration.PaymentStatus.PAID)

    @patch('registrations.views.send_confirmation_task')
    @patch('registrations.views.schedule_address_reveal')
    def test_charge_success_updates_slot_counts(self, mock_schedule, mock_confirm):
        mock_confirm.delay = lambda x: None
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': 'HP-TEST123',
                'amount': 7000000,
            }
        }
        self._post_webhook(payload)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 0)
        self.assertEqual(self.tier.confirmed_slots, 1)

    @patch('registrations.views.send_confirmation_task')
    @patch('registrations.views.schedule_address_reveal')
    def test_duplicate_webhook_ignored(self, mock_schedule, mock_confirm):
        mock_confirm.delay = lambda x: None
        self.registration.payment_status = Registration.PaymentStatus.PAID
        self.registration.status = Registration.Status.CONFIRMED
        self.registration.save()

        payload = {
            'event': 'charge.success',
            'data': {'reference': 'HP-TEST123', 'amount': 7000000}
        }
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)

    def test_charge_failed_cancels_registration(self):
        payload = {
            'event': 'charge.failed',
            'data': {'reference': 'HP-TEST123'}
        }
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CANCELLED)

    def test_charge_failed_releases_slot(self):
        payload = {
            'event': 'charge.failed',
            'data': {'reference': 'HP-TEST123'}
        }
        self._post_webhook(payload)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.reserved_slots, 0)

    def test_unknown_reference_returns_200(self):
        payload = {
            'event': 'charge.success',
            'data': {'reference': 'UNKNOWN-REF', 'amount': 7000000}
        }
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)

    def test_unhandled_event_returns_200(self):
        payload = {'event': 'transfer.success', 'data': {}}
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)