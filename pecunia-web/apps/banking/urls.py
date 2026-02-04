"""
Banking URLs - API routing.

Provides REST API endpoints for bank connections and accounts.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# API Router
router = DefaultRouter()
router.register(r'connections', views.BankConnectionViewSet, basename='connection')
router.register(r'accounts', views.BankAccountViewSet, basename='account')
router.register(r'sync-logs', views.SyncLogViewSet, basename='sync-log')

app_name = 'banking-api'

urlpatterns = [
    # OAuth callback
    path('callback/', views.BankConnectionCallbackView.as_view(), name='callback'),

    # Institution search
    path('institutions/', views.InstitutionSearchView.as_view(), name='institutions'),

    # Sync all
    path('sync-all/', views.SyncAllView.as_view(), name='sync-all'),

    # Router URLs
    path('', include(router.urls)),
]
