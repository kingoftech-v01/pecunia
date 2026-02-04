"""
Pecunia URL Configuration.

Main URL routing for the application.
Includes both frontend (HTML) and API routes.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAdminUser

from apps.dashboard.urls import api_urlpatterns as dashboard_api_urls
from apps.dashboard.urls import landing_urlpatterns as landing_urls


class AuthenticatedSchemaView(SpectacularAPIView):
    permission_classes = [IsAdminUser]


class AuthenticatedSwaggerView(SpectacularSwaggerView):
    permission_classes = [IsAdminUser]

# API v1 URL patterns
api_v1_patterns = [
    path('accounts/', include(('apps.accounts.urls', 'accounts'), namespace='accounts')),
    path('transactions/', include(('apps.transactions.urls', 'transactions'), namespace='transactions')),
    path('budgets/', include(('apps.budgets.urls', 'budgets'), namespace='budgets')),
    path('banking/', include(('apps.banking.urls', 'banking'), namespace='banking')),
    path('ai/', include(('apps.ai.urls', 'ai'), namespace='ai')),
    path('subscriptions/', include(('apps.subscriptions.urls', 'subscriptions'), namespace='subscriptions')),
    path('sync/', include(('apps.sync.urls', 'sync'), namespace='sync')),
    path('dashboard/', include((dashboard_api_urls, 'dashboard'), namespace='dashboard')),
]

# Frontend URL patterns (authenticated pages)
frontend_patterns = [
    path('accounts/', include('apps.accounts.frontend_urls')),
    path('transactions/', include('apps.transactions.frontend_urls')),
    path('budgets/', include('apps.budgets.frontend_urls')),
    path('banking/', include('apps.banking.frontend_urls')),
    path('ai/', include('apps.ai.frontend_urls')),
    path('subscriptions/', include('apps.subscriptions.frontend_urls')),
    path('dashboard/', include(('apps.dashboard.urls', 'dashboard'), namespace='dashboard')),
]

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation (requires admin authentication)
    path('api/schema/', AuthenticatedSchemaView.as_view(), name='schema'),
    path('api/docs/', AuthenticatedSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API v1
    path('api/v1/', include((api_v1_patterns, 'api'), namespace='api-v1')),

    # Landing pages (public, unauthenticated)
    path('', include((landing_urls, 'landing'), namespace='landing')),

    # Frontend (HTML with HTMX/Alpine.js) - authenticated pages
    path('app/', include((frontend_patterns, 'frontend'), namespace='frontend')),
]
