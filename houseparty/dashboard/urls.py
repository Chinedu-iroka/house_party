from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/login/', views.admin_login, name='admin_login'),
    path('dashboard/logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard_home, name='admin_dashboard_home'),
    path('dashboard/events/create/', views.event_create, name='admin_event_create'),
    path('dashboard/events/<uuid:event_id>/', views.event_detail_dashboard, name='admin_event_detail'),
    path('dashboard/events/<uuid:event_id>/edit/', views.event_edit, name='admin_event_edit'),
    path('dashboard/events/<uuid:event_id>/status/', views.event_toggle_status, name='admin_event_toggle_status'),
    path('dashboard/events/<uuid:event_id>/cancel/', views.event_cancel, name='admin_event_cancel'),
    path('dashboard/events/<uuid:event_id>/postpone/', views.event_postpone, name='admin_event_postpone'),
    path('dashboard/events/<uuid:event_id>/send-address/', views.event_send_address, name='admin_event_send_address'),
    path('dashboard/events/<uuid:event_id>/export/', views.event_export_csv, name='admin_event_export'),
]