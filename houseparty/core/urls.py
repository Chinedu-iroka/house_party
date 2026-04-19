from django.contrib import admin
from django.urls import path
from django.shortcuts import render

def test_base(request):
    return render(request, 'test.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', test_base),
]