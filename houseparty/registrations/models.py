import uuid
from django.db import models
from events.models import Event, TicketTier


class Registration(models.Model):

    class Status(models.TextChoices):
        PENDING     = 'PENDING',     'Pending'
        CONFIRMED   = 'CONFIRMED',   'Confirmed'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'
        CANCELLED   = 'CANCELLED',   'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID   = 'UNPAID',   'Unpaid'
        PAID     = 'PAID',     'Paid'
        REFUNDED = 'REFUNDED', 'Refunded'

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event                 = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='registrations')
    tier                  = models.ForeignKey(TicketTier, on_delete=models.PROTECT, related_name='registrations')
    full_name             = models.CharField(max_length=200)
    email                 = models.EmailField()
    phone                 = models.CharField(max_length=20)
    status                = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_reference     = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_status        = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    amount_paid           = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reservation_expires_at = models.DateTimeField(null=True, blank=True)
    invoice_sent          = models.BooleanField(default=False)
    address_sent          = models.BooleanField(default=False)
    registered_at         = models.DateTimeField(null=True, blank=True)
    transferred_to        = models.ForeignKey(
        Event,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transferred_registrations'
    )
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} — {self.event.name} ({self.tier.name})"

    @property
    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED and self.payment_status == self.PaymentStatus.PAID