from django.contrib import admin
from .models import Event, TicketTier


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display  = ['name', 'date', 'start_time', 'zone', 'status', 'address_sent']
    list_filter   = ['status', 'date']
    search_fields = ['name', 'zone']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(TicketTier)
class TicketTierAdmin(admin.ModelAdmin):
    list_display  = ['name', 'event', 'price', 'total_slots', 'reserved_slots', 'confirmed_slots']
    list_filter   = ['event']
    readonly_fields = ['id', 'created_at']