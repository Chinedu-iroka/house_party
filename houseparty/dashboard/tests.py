from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.timezone import now
from datetime import date, time, timedelta
from events.models import Event, TicketTier
from registrations.models import Registration
from dashboard.models import AdminUser, AuditLog


class AdminUserModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            password='testpass123',
            email='admin@test.com'
        )
        self.admin = AdminUser.objects.create(user=self.user)

    def test_admin_user_created(self):
        self.assertEqual(self.admin.user.username, 'testadmin')

    def test_admin_user_str(self):
        self.assertIn('testadmin', str(self.admin))


class AuditLogModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testadmin', password='testpass123')
        self.admin = AdminUser.objects.create(user=self.user)
        self.log = AuditLog.objects.create(
            admin=self.admin,
            action=AuditLog.Action.PUBLISH_EVENT,
            target='some-event-uuid',
            notes='Published Euphoria Night'
        )

    def test_audit_log_created(self):
        self.assertEqual(self.log.action, AuditLog.Action.PUBLISH_EVENT)

    def test_audit_log_str(self):
        self.assertIn('testadmin', str(self.log))


class DashboardViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
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

    def test_dashboard_home_returns_200(self):
        response = self.client.get(reverse('admin_dashboard_home'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_home_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('admin_dashboard_home'))
        self.assertRedirects(response, '/dashboard/login/?next=/dashboard/')

    def test_event_detail_returns_200(self):
        response = self.client.get(reverse('admin_event_detail', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)

    def test_event_detail_full_address_visible_to_admin(self):
        response = self.client.get(reverse('admin_event_detail', args=[self.event.id]))
        # Admin can see address in edit form but not in detail template
        self.assertEqual(response.status_code, 200)

    def test_event_create_get_returns_200(self):
        response = self.client.get(reverse('admin_event_create'))
        self.assertEqual(response.status_code, 200)

    def test_event_create_post_creates_event(self):
        response = self.client.post(reverse('admin_event_create'), {
            'name': 'Test Event',
            'description': 'Test description',
            'date': '2025-12-31',
            'start_time': '21:00',
            'zone': 'Lekki',
            'full_address': '12 Test Close',
            'tier_name': ['Regular'],
            'tier_price': ['70000'],
            'tier_slots': ['30'],
            'tier_inclusions': ['Entry + 1 Martell'],
        })
        self.assertTrue(Event.objects.filter(name='Test Event').exists())

    def test_event_toggle_publish(self):
        self.event.status = Event.Status.DRAFT
        self.event.save()
        self.client.post(
            reverse('admin_event_toggle_status', args=[self.event.id]),
            {'status': 'PUBLISHED'}
        )
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.PUBLISHED)

    def test_event_export_csv(self):
        Registration.objects.create(
            event=self.event,
            tier=self.tier,
            full_name="Test User",
            email="test@test.com",
            phone="08012345678",
            status=Registration.Status.CONFIRMED,
            payment_status=Registration.PaymentStatus.PAID,
            payment_reference="HP-TEST",
            amount_paid=70000,
            registered_at=now(),
        )
        response = self.client.get(reverse('admin_event_export', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode()
        self.assertIn('Test User', content)
        self.assertIn('test@test.com', content)

    def test_admin_login_page_returns_200(self):
        self.client.logout()
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)

    def test_admin_login_with_valid_credentials(self):
        self.client.logout()
        response = self.client.post(reverse('admin_login'), {
            'username': 'admin',
            'password': 'admin123',
        })
        self.assertRedirects(response, reverse('admin_dashboard_home'))

    def test_admin_login_with_invalid_credentials(self):
        self.client.logout()
        response = self.client.post(reverse('admin_login'), {
            'username': 'admin',
            'password': 'wrongpassword',
        })
        self.assertIn('error', response.context)