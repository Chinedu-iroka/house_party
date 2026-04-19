from django.contrib import admin
from .models import AdminUser, AuditLog


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display  = ['user', 'created_at']
    readonly_fields = ['id', 'created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ['admin', 'action', 'target', 'timestamp']
    list_filter   = ['action']
    readonly_fields = ['id', 'timestamp']