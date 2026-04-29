from django.urls import path
from . import views

urlpatterns = [
    path('events/<uuid:event_id>/register/<uuid:tier_id>/', views.register, name='register'),
    path('registration/checkout/<uuid:registration_id>/', views.checkout, name='checkout'),
    path('registration/success/<uuid:registration_id>/', views.registration_success, name='registration_success'),
    path('registration/failed/', views.registration_failed, name='registration_failed'),
    path('registration/release/<uuid:registration_id>/', views.release_slot_api, name='release_slot_api'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
]