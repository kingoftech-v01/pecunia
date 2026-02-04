"""
Minimal URL configuration for banking tests.

Avoids importing frontend_urls modules that may not exist.
"""
from django.urls import path, include

urlpatterns = [
    path('api/v1/banking/', include(('apps.banking.urls', 'banking'), namespace='banking')),
]
