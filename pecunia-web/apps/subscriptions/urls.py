"""
Subscriptions URLs - API routing.

Provides REST API endpoints for subscription management.

Endpoints:
- GET  /api/v1/subscriptions/plans/              - List all active plans
- GET  /api/v1/subscriptions/plans/{uuid}/       - Get plan details
- GET  /api/v1/subscriptions/current/            - Get current user's subscription
- GET  /api/v1/subscriptions/current/features/   - Get available features
- GET  /api/v1/subscriptions/current/events/     - Get subscription events
- POST /api/v1/subscriptions/current/cancel/     - Cancel subscription
- POST /api/v1/subscriptions/current/reactivate/ - Reactivate subscription
- POST /api/v1/subscriptions/current/change-plan/ - Change subscription plan
- POST /api/v1/subscriptions/checkout/           - Create checkout session
- POST /api/v1/subscriptions/portal/             - Create billing portal session
- GET  /api/v1/subscriptions/payments/           - List payment history
- GET  /api/v1/subscriptions/payments/{uuid}/    - Get payment details
- POST /api/v1/subscriptions/webhooks/stripe/    - Stripe webhook endpoint
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import webhooks

# API Router
router = DefaultRouter()
router.register(r'plans', views.SubscriptionPlanViewSet, basename='plan')
router.register(r'current', views.SubscriptionViewSet, basename='subscription')
router.register(r'payments', views.PaymentHistoryViewSet, basename='payment')
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')

app_name = 'subscriptions'

urlpatterns = [
    # Checkout Session
    path('checkout/', views.CreateCheckoutView.as_view(), name='checkout'),

    # Billing Portal
    path('portal/', views.CreatePortalView.as_view(), name='portal'),

    # Payment Methods
    path('payment-methods/', views.PaymentMethodsAPIView.as_view(), name='payment-methods'),

    # Stripe Webhook - Primary endpoint
    path('webhooks/stripe/', webhooks.stripe_webhook, name='webhook-stripe'),

    # Legacy webhook endpoint (for backward compatibility)
    path('webhook/', webhooks.stripe_webhook, name='webhook'),

    # Router URLs (must be last)
    path('', include(router.urls)),
]

# Optional: Test webhook endpoint (only in DEBUG mode)
from django.conf import settings
if settings.DEBUG:
    urlpatterns.insert(
        -1,  # Insert before router URLs
        path('webhooks/stripe/test/', webhooks.stripe_webhook_test, name='webhook-stripe-test'),
    )
