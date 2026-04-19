import uuid
from django.db import models
from django.contrib.auth.models import User


class AdminUser(models.Model):

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Admin: {self.user.username}"



class AuditLog(models.Model):

    class Action(models.TextChoices):
        CANCEL_EVENT          = 'CANCEL_EVENT',          'Cancel Event'
        POSTPONE_EVENT        = 'POSTPONE_EVENT',        'Postpone Event'
        PUBLISH_EVENT         = 'PUBLISH_EVENT',         'Publish Event'
        CLOSE_EVENT           = 'CLOSE_EVENT',           'Close Event'
        SEND_ADDRESS          = 'SEND_ADDRESS',          'Send Address'
        MANUAL_ADDRESS_REVEAL = 'MANUAL_ADDRESS_REVEAL', 'Manual Address Reveal'

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin     = models.ForeignKey(AdminUser, on_delete=models.PROTECT, related_name='audit_logs')
    action    = models.CharField(max_length=50, choices=Action.choices)
    target    = models.CharField(max_length=200, help_text="ID of the affected entity")
    notes     = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.admin} — {self.action} at {self.timestamp}"