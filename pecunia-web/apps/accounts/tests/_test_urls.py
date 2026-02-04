"""
Minimal URL config for accounts view tests.
Avoids importing broken ROOT_URLCONF from other apps.
"""
from django.urls import path, include

urlpatterns = [
    path("api/v1/accounts/", include("apps.accounts.urls")),
]
