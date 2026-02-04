"""
Tests for Subscriptions API views.

Tests ViewSets, checkout, portal, payment history, and subscription management.
"""
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.subscriptions.models import (
    SubscriptionPlan,
    Subscription,
    SubscriptionEvent,
    Invoice,
)


@pytest.fixture
def plan(db):
    return SubscriptionPlan.objects.create(
        name="Premium",
        slug="premium-view",
        tier="premium",
        price_monthly=Decimal("9.99"),
        price_yearly=Decimal("99.99"),
        stripe_price_id_monthly="price_monthly_123",
        stripe_price_id_yearly="price_yearly_456",
        max_bank_accounts=5,
        ai_categorization=True,
    )


@pytest.fixture
def free_plan(db):
    return SubscriptionPlan.objects.create(
        name="Free",
        slug="free-view",
        tier="free",
        price_monthly=Decimal("0.00"),
        price_yearly=Decimal("0.00"),
        max_bank_accounts=1,
        ai_categorization=False,
    )


@pytest.fixture
def subscription(user, plan):
    return Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.ACTIVE,
        billing_cycle='monthly',
        stripe_subscription_id='sub_test123',
        stripe_customer_id='cus_test123',
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )


# =============================================================================
# SubscriptionPlanViewSet Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionPlanViewSet:

    def test_list_requires_auth(self, api_client, plan):
        resp = api_client.get('/api/v1/subscriptions/plans/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_plans(self, auth_client, plan):
        resp = auth_client.get('/api/v1/subscriptions/plans/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) >= 1

    def test_list_excludes_inactive(self, auth_client, db):
        SubscriptionPlan.objects.create(
            name="Active", slug="active-plan", tier="premium",
            price_monthly=Decimal("9.99"), is_active=True,
        )
        SubscriptionPlan.objects.create(
            name="Inactive", slug="inactive-plan", tier="pro",
            price_monthly=Decimal("19.99"), is_active=False,
        )
        resp = auth_client.get('/api/v1/subscriptions/plans/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        names = [p['name'] for p in data]
        assert "Active" in names
        assert "Inactive" not in names

    def test_retrieve_plan(self, auth_client, plan):
        resp = auth_client.get(f'/api/v1/subscriptions/plans/{plan.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == 'Premium'
        assert 'max_bank_accounts' in resp.data


# =============================================================================
# SubscriptionViewSet Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionViewSet:

    def test_list_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/subscriptions/current/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_no_subscription(self, auth_client):
        resp = auth_client.get('/api/v1/subscriptions/current/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_with_subscription(self, auth_client, subscription):
        resp = auth_client.get('/api/v1/subscriptions/current/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['status'] == 'active'

    def test_summary_no_subscription(self, auth_client):
        resp = auth_client.get('/api/v1/subscriptions/current/summary/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_summary_with_subscription(self, auth_client, subscription):
        resp = auth_client.get('/api/v1/subscriptions/current/summary/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'plan_name' in resp.data

    def test_events_no_subscription(self, auth_client):
        resp = auth_client.get('/api/v1/subscriptions/current/events/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []

    def test_events_with_subscription(self, auth_client, subscription):
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='created',
            description='Test event.',
        )
        resp = auth_client.get('/api/v1/subscriptions/current/events/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    @patch('apps.subscriptions.views.stripe_service')
    def test_cancel_subscription(self, mock_stripe, auth_client, subscription):
        mock_stripe.cancel_subscription.return_value = None
        resp = auth_client.post('/api/v1/subscriptions/current/cancel/', {}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert 'canceled' in resp.data['detail'].lower()

    def test_cancel_no_subscription(self, auth_client):
        resp = auth_client.post('/api/v1/subscriptions/current/cancel/', {}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.subscriptions.views.stripe_service')
    def test_cancel_stripe_error(self, mock_stripe, auth_client, subscription):
        from apps.subscriptions.stripe_service import StripeServiceError
        mock_stripe.cancel_subscription.side_effect = StripeServiceError("Stripe error")
        resp = auth_client.post('/api/v1/subscriptions/current/cancel/', {}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.subscriptions.views.stripe_service')
    def test_reactivate_subscription(self, mock_stripe, auth_client, subscription):
        subscription.cancel_at_period_end = True
        subscription.save()
        mock_stripe.reactivate_subscription.return_value = None
        resp = auth_client.post('/api/v1/subscriptions/current/reactivate/')
        assert resp.status_code == status.HTTP_200_OK

    def test_reactivate_not_scheduled(self, auth_client, subscription):
        resp = auth_client.post('/api/v1/subscriptions/current/reactivate/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_reactivate_no_subscription(self, auth_client):
        resp = auth_client.post('/api/v1/subscriptions/current/reactivate/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.subscriptions.views.stripe_service')
    def test_change_plan(self, mock_stripe, auth_client, subscription, db):
        new_plan = SubscriptionPlan.objects.create(
            name="Pro", slug="pro-change", tier="pro",
            price_monthly=Decimal("19.99"),
        )
        mock_stripe.update_subscription.return_value = None
        resp = auth_client.post('/api/v1/subscriptions/current/change-plan/', {
            'new_plan_id': str(new_plan.id),
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK

    def test_change_plan_no_subscription(self, auth_client, plan):
        resp = auth_client.post('/api/v1/subscriptions/current/change-plan/', {
            'new_plan_id': str(plan.id),
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# CreateCheckoutView Tests
# =============================================================================

@pytest.mark.django_db
class TestCreateCheckoutView:

    @patch('apps.subscriptions.views.stripe_service')
    def test_create_checkout(self, mock_stripe, auth_client, plan):
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe.create_checkout_session.return_value = mock_session

        resp = auth_client.post('/api/v1/subscriptions/checkout/', {
            'plan_id': str(plan.id),
            'billing_interval': 'month',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['session_id'] == "cs_test_123"
        assert resp.data['url'] == "https://checkout.stripe.com/test"

    def test_checkout_requires_auth(self, api_client, plan):
        resp = api_client.post('/api/v1/subscriptions/checkout/', {
            'plan_id': str(plan.id),
            'billing_interval': 'month',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.subscriptions.views.stripe_service')
    def test_checkout_with_active_subscription(self, mock_stripe, auth_client, subscription, plan):
        resp = auth_client.post('/api/v1/subscriptions/checkout/', {
            'plan_id': str(plan.id),
            'billing_interval': 'month',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already have an active subscription' in resp.data['detail'].lower()

    @patch('apps.subscriptions.views.stripe_service')
    def test_checkout_stripe_error(self, mock_stripe, auth_client, plan):
        from apps.subscriptions.stripe_service import StripeServiceError
        mock_stripe.create_checkout_session.side_effect = StripeServiceError("Stripe error")
        resp = auth_client.post('/api/v1/subscriptions/checkout/', {
            'plan_id': str(plan.id),
            'billing_interval': 'month',
        }, format='json')
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_checkout_invalid_plan(self, auth_client):
        resp = auth_client.post('/api/v1/subscriptions/checkout/', {
            'plan_id': str(uuid.uuid4()),
            'billing_interval': 'month',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# CreatePortalView Tests
# =============================================================================

@pytest.mark.django_db
class TestCreatePortalView:

    @patch('apps.subscriptions.views.stripe_service')
    def test_create_portal(self, mock_stripe, auth_client, subscription):
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/session/test"
        mock_stripe.create_portal_session.return_value = mock_session

        resp = auth_client.post('/api/v1/subscriptions/portal/', {}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert 'url' in resp.data

    @patch('apps.subscriptions.views.stripe_service')
    def test_portal_stripe_error(self, mock_stripe, auth_client, subscription):
        from apps.subscriptions.stripe_service import StripeServiceError
        mock_stripe.create_portal_session.side_effect = StripeServiceError("Error")
        resp = auth_client.post('/api/v1/subscriptions/portal/', {}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_portal_requires_auth(self, api_client):
        resp = api_client.post('/api/v1/subscriptions/portal/', {}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# PaymentHistoryViewSet Tests
# =============================================================================

@pytest.mark.django_db
class TestPaymentHistoryViewSet:

    def test_list_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/subscriptions/payments/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_no_subscription(self, auth_client):
        resp = auth_client.get('/api/v1/subscriptions/payments/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) == 0

    def test_list_with_invoices(self, auth_client, subscription):
        Invoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='inv_test',
            invoice_number='INV-001',
            amount_due=Decimal("9.99"),
            currency='EUR',
            status='paid',
        )
        resp = auth_client.get('/api/v1/subscriptions/payments/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data['results'] if 'results' in resp.data else resp.data
        assert len(data) >= 1


# =============================================================================
# PaymentMethodsAPIView Tests
# =============================================================================

@pytest.mark.django_db
class TestPaymentMethodsAPIView:

    def test_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/subscriptions/payment-methods/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_customer_id(self, auth_client):
        resp = auth_client.get('/api/v1/subscriptions/payment-methods/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == []

    @patch('apps.subscriptions.views.stripe_service')
    def test_with_payment_methods(self, mock_stripe, auth_client, subscription):
        mock_stripe.get_payment_methods.return_value = [
            MagicMock(
                id='pm_123',
                get=lambda k, d='': {'card': {'brand': 'visa', 'last4': '4242', 'exp_month': 12, 'exp_year': 2025}}.get(k, d),
                **{'card': {'brand': 'visa', 'last4': '4242', 'exp_month': 12, 'exp_year': 2025}}
            )
        ]
        mock_stripe.get_customer.return_value = {
            'invoice_settings': {'default_payment_method': 'pm_123'}
        }

        resp = auth_client.get('/api/v1/subscriptions/payment-methods/')
        assert resp.status_code == status.HTTP_200_OK
