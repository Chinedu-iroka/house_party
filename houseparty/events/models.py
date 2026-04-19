import uuid
from django.db import models


class Event(models.Model):

    class Status(models.TextChoices):
        DRAFT       = 'DRAFT',       'Draft'
        PUBLISHED   = 'PUBLISHED',   'Published'
        CLOSED      = 'CLOSED',      'Closed'
        CANCELLED   = 'CANCELLED',   'Cancelled'
        POSTPONED   = 'POSTPONED',   'Postponed'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=200)
    description  = models.TextField()
    date         = models.DateField()
    start_time   = models.TimeField()
    zone         = models.CharField(max_length=100, help_text="Public location zone e.g. Lekki")
    full_address = models.TextField(help_text="Private — never expose publicly")
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    next_event   = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='previous_events',
        help_text="Next event for cancellation transfers"
    )
    address_sent = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.name} — {self.date}"

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED



class TicketTier(models.Model):

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event           = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tiers')
    name            = models.CharField(max_length=100, help_text="e.g. Regular, VIP")
    price           = models.DecimalField(max_digits=10, decimal_places=2)
    inclusions      = models.TextField(help_text="e.g. Entry + 2 Martell")
    total_slots     = models.PositiveIntegerField()
    reserved_slots  = models.PositiveIntegerField(default=0)
    confirmed_slots = models.PositiveIntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.event.name} — {self.name} (₦{self.price})"

    @property
    def available_slots(self):
        available = self.total_slots - self.reserved_slots - self.confirmed_slots
        return max(0, available)

    @property
    def is_sold_out(self):
        return self.available_slots <= 0

    @property
    def fill_percentage(self):
        if self.total_slots == 0:
            return 100
        filled = self.reserved_slots + self.confirmed_slots
        return min(100, int((filled / self.total_slots) * 100))