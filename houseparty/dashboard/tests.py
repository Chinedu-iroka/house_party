from django.test import TestCase
from django.contrib.auth.models import User
from .models import AdminUser, AuditLog


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
        self.user = User.objects.create_user(
            username='testadmin',
            password='testpass123'
        )
        self.admin = AdminUser.objects.create(user=self.user)
        self.log = AuditLog.objects.create(
            admin=self.admin,
            action=AuditLog.Action.PUBLISH_EVENT,
            target='some-event-uuid',
            notes='Published Euphoria Night'
        )

    def test_audit_log_created(self):
        self.assertEqual(self.log.action, AuditLog.Action.PUBLISH_EVENT)
        self.assertEqual(self.log.target, 'some-event-uuid')

    def test_audit_log_str(self):
        self.assertIn('testadmin', str(self.log))