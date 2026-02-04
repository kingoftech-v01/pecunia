"""
Tests for Subscriptions serializers.

Tests all serializer validation, field mapping, and edge cases.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.subscriptions.models import (
    SubscriptionPlan,
    Subscription,
    SubscriptionEvent,
    Invoice,
)
from apps.subscriptions.serializers import (
    SubscriptionPlanSerializer,
    SubscriptionPlanListSerializer,
    SubscriptionSerializer,
    SubscriptionSummarySerializer,
    SubscriptionEventSerializer,
    PaymentHistorySerializer,
    InvoiceSerializer,
    InvoiceListSerializer,
    CheckoutRequestSerializer,
    CancelSubscriptionSerializer,
    UpdateSubscriptionSerializer,
    PortalRequestSerializer,
    SubscriptionFeaturesSerializer,
    PaymentMethodSerializer,
)


@pytest.fixture
def plan(db):
    return SubscriptionPlan.objects.create(
        name="Premium",
        slug="premium-ser",
        tier="premium",
        price_monthly=Decimal("9.99"),
        price_yearly=Decimal("99.99"),
        max_bank_accounts=5,
        max_budgets=10,
        ai_categorization=True,
        is_featured=True,
    )


@pytest.fixture
def subscription(user, plan):
    return Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.ACTIVE,
        billing_cycle='monthly',
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )


# =============================================================================
# Plan Serializer Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionPlanSerializer:

    def test_serialize_plan(self, plan):
        serializer = SubscriptionPlanSerializer(plan)
        data = serializer.data
        assert data['name'] == "Premium"
        assert data['tier'] == "premium"
        assert 'price_monthly' in data
        assert 'price_yearly' in data
        assert 'yearly_savings' in data
        assert 'max_bank_accounts' in data
        assert 'ai_categorization' in data
        assert 'is_featured' in data

    def test_list_serializer(self, plan):
        serializer = SubscriptionPlanListSerializer(plan)
        data = serializer.data
        assert 'id' in data
        assert 'name' in data
        assert 'price_monthly' in data
        assert 'yearly_savings' in data
        # List serializer has fewer fields
        assert 'max_bank_accounts' not in data


# =============================================================================
# Subscription Serializer Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionSerializer:

    def test_serialize_subscription(self, subscription):
        serializer = SubscriptionSerializer(subscription)
        data = serializer.data
        assert data['status'] == 'active'
        assert data['is_active'] is True
        assert data['is_on_trial'] is False
        assert data['tier'] == 'premium'
        assert data['billing_interval'] == 'monthly'
        assert 'plan' in data
        assert data['plan']['name'] == 'Premium'

    def test_summary_serializer(self, subscription):
        serializer = SubscriptionSummarySerializer(subscription)
        data = serializer.data
        assert data['plan_name'] == 'Premium'
        assert data['tier'] == 'premium'
        assert data['is_active'] is True


# =============================================================================
# Event and Invoice Serializer Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionEventSerializer:

    def test_serialize_event(self, subscription):
        event = SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='created',
            description='Subscription created.',
            metadata={'plan': 'premium'},
        )
        serializer = SubscriptionEventSerializer(event)
        data = serializer.data
        assert data['event_type'] == 'created'
        assert data['description'] == 'Subscription created.'
        assert data['metadata'] == {'plan': 'premium'}


@pytest.mark.django_db
class TestInvoiceSerializer:

    def test_serialize_invoice(self, subscription):
        invoice = Invoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='inv_test',
            invoice_number='INV-001',
            amount_due=Decimal("9.99"),
            amount_paid=Decimal("9.99"),
            currency='EUR',
            status='paid',
        )
        serializer = InvoiceSerializer(invoice)
        data = serializer.data
        assert data['invoice_number'] == 'INV-001'
        assert data['status'] == 'paid'

    def test_list_serializer(self, subscription):
        invoice = Invoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='inv_list',
            invoice_number='INV-002',
            amount_due=Decimal("9.99"),
            currency='EUR',
            status='open',
        )
        serializer = InvoiceListSerializer(invoice)
        data = serializer.data
        assert 'invoice_number' in data
        assert 'amount_due' in data
        # List serializer has fewer fields
        assert 'invoice_pdf_url' not in data


# =============================================================================
# Checkout Request Serializer Tests
# =============================================================================

@pytest.mark.django_db
class TestCheckoutRequestSerializer:

    def test_valid_request(self, plan):
        serializer = CheckoutRequestSerializer(data={
            'plan_id': str(plan.id),
            'billing_interval': 'month',
        })
        assert serializer.is_valid(), serializer.errors

    def test_yearly_billing(self, plan):
        serializer = CheckoutRequestSerializer(data={
            'plan_id': str(plan.id),
            'billing_interval': 'year',
        })
        assert serializer.is_valid()

    def test_invalid_plan_id(self):
        serializer = CheckoutRequestSerializer(data={
            'plan_id': str(uuid.uuid4()),
            'billing_interval': 'month',
        })
        assert not serializer.is_valid()
        assert 'plan_id' in serializer.errors

    def test_inactive_plan(self, db):
        plan = SubscriptionPlan.objects.create(
            name="Inactive", slug="inactive-checkout", tier="premium",
            price_monthly=Decimal("5.00"), is_active=False,
        )
        serializer = CheckoutRequestSerializer(data={
            'plan_id': str(plan.id),
            'billing_interval': 'month',
        })
        assert not serializer.is_valid()

    def test_invalid_billing_interval(self, plan):
        serializer = CheckoutRequestSerializer(data={
            'plan_id': str(plan.id),
            'billing_interval': 'weekly',
        })
        assert not serializer.is_valid()

    def test_with_optional_urls(self, plan):
        serializer = CheckoutRequestSerializer(data={
            'plan_id': str(plan.id),
            'billing_interval': 'month',
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
        })
        assert serializer.is_valid()


# =============================================================================
# Cancel and Update Serializer Tests
# =============================================================================

class TestCancelSubscriptionSerializer:

    def test_default_values(self):
        serializer = CancelSubscriptionSerializer(data={})
        assert serializer.is_valid()
        assert serializer.validated_data['cancel_at_period_end'] is True

    def test_cancel_immediately(self):
        serializer = CancelSubscriptionSerializer(data={
            'cancel_at_period_end': False,
        })
        assert serializer.is_valid()
        assert serializer.validated_data['cancel_at_period_end'] is False

    def test_with_reason(self):
        serializer = CancelSubscriptionSerializer(data={
            'reason': 'Too expensive',
        })
        assert serializer.is_valid()
        assert serializer.validated_data['reason'] == 'Too expensive'


@pytest.mark.django_db
class TestUpdateSubscriptionSerializer:

    def test_valid_plan_change(self, plan):
        serializer = UpdateSubscriptionSerializer(data={
            'new_plan_id': str(plan.id),
        })
        assert serializer.is_valid()

    def test_invalid_plan(self):
        serializer = UpdateSubscriptionSerializer(data={
            'new_plan_id': str(uuid.uuid4()),
        })
        assert not serializer.is_valid()

    def test_with_billing_interval(self, plan):
        serializer = UpdateSubscriptionSerializer(data={
            'new_plan_id': str(plan.id),
            'billing_interval': 'year',
        })
        assert serializer.is_valid()


# =============================================================================
# Portal and Features Serializer Tests
# =============================================================================

class TestPortalRequestSerializer:

    def test_empty_valid(self):
        serializer = PortalRequestSerializer(data={})
        assert serializer.is_valid()

    def test_with_return_url(self):
        serializer = PortalRequestSerializer(data={
            'return_url': 'https://example.com/settings',
        })
        assert serializer.is_valid()

    def test_invalid_url(self):
        serializer = PortalRequestSerializer(data={
            'return_url': 'not-a-url',
        })
        assert not serializer.is_valid()


class TestSubscriptionFeaturesSerializer:

    def test_serialize_features(self):
        data = {
            'tier': 'premium',
            'max_bank_accounts': 5,
            'max_budgets': 10,
            'max_transactions_per_month': 5000,
            'max_categories': 50,
            'max_family_members': 3,
            'ai_categorization': True,
            'ai_insights': True,
            'export_csv': True,
            'export_pdf': True,
            'bank_sync': True,
            'recurring_transactions': True,
            'custom_categories': True,
            'budget_alerts': True,
            'multi_currency': True,
            'priority_support': True,
            'api_access': True,
        }
        serializer = SubscriptionFeaturesSerializer(data)
        assert serializer.data['tier'] == 'premium'
        assert serializer.data['ai_categorization'] is True


class TestPaymentMethodSerializer:

    def test_serialize_method(self):
        data = {
            'id': 'pm_123',
            'brand': 'Visa',
            'last4': '4242',
            'exp_month': 12,
            'exp_year': 2025,
            'is_default': True,
        }
        serializer = PaymentMethodSerializer(data)
        assert serializer.data['brand'] == 'Visa'
        assert serializer.data['is_default'] is True
