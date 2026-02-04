"""
Subscriptions Frontend URLs - HTML page routing.

Provides URL patterns for user-facing HTML pages.
"""
from django.urls import path
from . import template_views

app_name = 'subscriptions'

urlpatterns = [
    # Pricing page (public)
    path('pricing/', template_views.pricing_view, name='pricing'),

    # Subscription management
    path('', template_views.subscription_view, name='subscription'),
    path('billing/', template_views.billing_view, name='billing'),

    # Checkout flow
    path('checkout/<uuid:plan_id>/', template_views.checkout_view, name='checkout'),
    path('success/', template_views.checkout_success_view, name='success'),
    path('cancel/', template_views.checkout_cancel_view, name='cancel'),

    # Subscription actions
    path('cancel-subscription/', template_views.cancel_subscription_view, name='cancel-subscription'),
    path('reactivate/', template_views.reactivate_subscription_view, name='reactivate'),
    path('change-plan/', template_views.change_plan_view, name='change-plan'),

    # Billing portal redirect
    path('billing-portal/', template_views.billing_portal_view, name='billing-portal'),

    # Invoice detail
    path('invoices/<uuid:invoice_id>/', template_views.invoice_detail_view, name='invoice-detail'),

    # Event history
    path('events/', template_views.subscription_events_view, name='events'),

    # Support
    path('support/', template_views.contact_support_view, name='support'),

    # HTMX partials
    path('htmx/status/', template_views.htmx_subscription_status, name='htmx-status'),
    path('htmx/billing-summary/', template_views.htmx_billing_summary, name='htmx-billing-summary'),
    path('htmx/plan-comparison/', template_views.htmx_plan_comparison, name='htmx-plan-comparison'),
]
