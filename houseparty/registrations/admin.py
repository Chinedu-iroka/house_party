from django.contrib import admin
from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'email', 'event', 'tier', 'status', 'payment_status', 'registered_at']
    list_filter   = ['status', 'payment_status', 'event']
    search_fields = ['full_name', 'email', 'phone', 'payment_reference']
    readonly_fields = ['id', 'created_at']