from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('age-gate/', views.age_gate, name='age_gate'),
    path('age-gate/exit/', views.age_exit, name='age_exit'),
]