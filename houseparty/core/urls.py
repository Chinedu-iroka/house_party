from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

def test_base(request):
    return render(request, 'test.html')

handler404 = 'events.views.custom_404'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', test_base),
    path('', include('events.urls')),
]