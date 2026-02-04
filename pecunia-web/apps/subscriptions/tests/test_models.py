"""
Tests for Subscriptions models.

Tests SubscriptionPlan, Subscription, PaymentHistory, SubscriptionEvent, and Invoice.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.subscriptions.models import (
    SubscriptionPlan,
    Subscription,
    PaymentHistory,
    SubscriptionEvent,
    Invoice,
)


# =============================================================================
# SubscriptionPlan Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionPlan:

    @pytest.fixture
    def plan(self, db):
        return SubscriptionPlan.objects.create(
            name="Premium",
            slug="premium",
            tier="premium",
            price_monthly=Decimal("9.99"),
            price_yearly=Decimal("99.99"),
            stripe_price_id_monthly="price_monthly_123",
            stripe_price_id_yearly="price_yearly_456",
            features=["AI categorization", "Bank sync"],
            limits={"accounts": 5, "transactions_per_month": 5000},
            max_bank_accounts=5,
            max_budgets=10,
            ai_categorization=True,
            ai_insights=True,
        )

    def test_create_plan(self, plan):
        assert plan.pk is not None
        assert plan.name == "Premium"
        assert plan.slug == "premium"
        assert plan.tier == "premium"
        assert str(plan) == "Premium ($9.99/mo)"

    def test_get_stripe_price_id_monthly(self, plan):
        assert plan.get_stripe_price_id('monthly') == "price_monthly_123"

    def test_get_stripe_price_id_yearly(self, plan):
        assert plan.get_stripe_price_id('yearly') == "price_yearly_456"

    def test_get_stripe_price_id_default(self, plan):
        # Non-'yearly' defaults to monthly
        assert plan.get_stripe_price_id('unknown') == "price_monthly_123"

    def test_get_price_monthly(self, plan):
        assert plan.get_price('monthly') == Decimal("9.99")

    def test_get_price_yearly(self, plan):
        assert plan.get_price('yearly') == Decimal("99.99")

    def test_yearly_savings_percentage(self, plan):
        # Monthly * 12 = 119.88; yearly = 99.99; savings = 19.89; 19.89/119.88 = ~16%
        savings = plan.yearly_savings_percentage
        assert savings == 16  # int(16.58...) = 16

    def test_yearly_savings_property(self, plan):
        assert plan.yearly_savings == plan.yearly_savings_percentage

    def test_yearly_savings_zero_monthly(self, db):
        plan = SubscriptionPlan.objects.create(
            name="Free", slug="free", tier="free",
            price_monthly=Decimal("0.00"), price_yearly=Decimal("0.00"),
        )
        assert plan.yearly_savings_percentage == 0

    def test_get_limit(self, plan):
        assert plan.get_limit('accounts') == 5
        assert plan.get_limit('transactions_per_month') == 5000
        assert plan.get_limit('nonexistent') is None
        assert plan.get_limit('nonexistent', 99) == 99

    def test_has_feature(self, plan):
        assert plan.has_feature("AI categorization") is True
        assert plan.has_feature("Bank sync") is True
        assert plan.has_feature("Nonexistent") is False

    def test_is_active_default(self, plan):
        assert plan.is_active is True

    def test_feature_fields(self, plan):
        assert plan.max_bank_accounts == 5
        assert plan.max_budgets == 10
        assert plan.ai_categorization is True
        assert plan.ai_insights is True


# =============================================================================
# Subscription Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscription:

    @pytest.fixture
    def plan(self, db):
        return SubscriptionPlan.objects.create(
            name="Premium", slug="premium-test", tier="premium",
            price_monthly=Decimal("9.99"), price_yearly=Decimal("99.99"),
            features=["AI"], limits={"accounts": 5},
        )

    @pytest.fixture
    def subscription(self, user, plan):
        return Subscription.objects.create(
            user=user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            billing_cycle='monthly',
            stripe_subscription_id='sub_test123',
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

    def test_create_subscription(self, subscription):
        assert subscription.pk is not None
        assert "Premium" in str(subscription)

    def test_is_active_when_active(self, subscription):
        assert subscription.is_active is True

    def test_is_active_when_trialing(self, subscription):
        subscription.status = Subscription.Status.TRIALING
        subscription.save()
        assert subscription.is_active is True

    def test_is_active_when_canceled(self, subscription):
        subscription.status = Subscription.Status.CANCELED
        subscription.save()
        assert subscription.is_active is False

    def test_is_active_when_past_due(self, subscription):
        subscription.status = Subscription.Status.PAST_DUE
        subscription.save()
        assert subscription.is_active is False

    def test_is_trialing(self, subscription):
        subscription.status = Subscription.Status.TRIALING
        subscription.save()
        assert subscription.is_trialing is True

    def test_is_on_trial(self, subscription):
        subscription.status = Subscription.Status.TRIALING
        subscription.save()
        assert subscription.is_on_trial is True

    def test_billing_interval_alias(self, subscription):
        assert subscription.billing_interval == 'monthly'

    def test_tier_property(self, subscription):
        assert subscription.tier == 'premium'

    def test_days_until_renewal(self, subscription):
        days = subscription.days_until_renewal
        assert days is not None
        assert days >= 29  # Should be ~30

    def test_days_until_renewal_none(self, subscription):
        subscription.current_period_end = None
        subscription.save()
        assert subscription.days_until_renewal is None

    def test_is_canceled_false(self, subscription):
        assert subscription.is_canceled is False

    def test_is_canceled_status(self, subscription):
        subscription.status = Subscription.Status.CANCELED
        subscription.save()
        assert subscription.is_canceled is True

    def test_is_canceled_at_period_end(self, subscription):
        subscription.cancel_at_period_end = True
        subscription.save()
        assert subscription.is_canceled is True

    def test_get_feature_limit(self, subscription):
        assert subscription.get_feature_limit('accounts') == 5
        assert subscription.get_feature_limit('nonexistent') is None

    def test_has_feature(self, subscription):
        assert subscription.has_feature("AI") is True
        assert subscription.has_feature("Nonexistent") is False

    def test_all_status_choices(self):
        expected = ['active', 'past_due', 'canceled', 'trialing',
                    'incomplete', 'incomplete_expired', 'unpaid', 'paused']
        actual = [c[0] for c in Subscription.Status.choices]
        assert set(expected) == set(actual)


# =============================================================================
# PaymentHistory Tests
# =============================================================================

@pytest.mark.django_db
class TestPaymentHistory:

    @pytest.fixture
    def payment(self, user):
        return PaymentHistory.objects.create(
            user=user,
            amount=Decimal("9.99"),
            currency="USD",
            status=PaymentHistory.Status.SUCCEEDED,
            stripe_payment_intent_id="pi_test123",
        )

    def test_create_payment(self, payment):
        assert payment.pk is not None
        assert "9.99" in str(payment)

    def test_is_successful(self, payment):
        assert payment.is_successful is True

    def test_is_not_successful(self, payment):
        payment.status = PaymentHistory.Status.FAILED
        payment.save()
        assert payment.is_successful is False

    def test_net_amount(self, payment):
        assert payment.net_amount == Decimal("9.99")

    def test_net_amount_with_refund(self, payment):
        payment.refunded_amount = Decimal("3.00")
        payment.save()
        assert payment.net_amount == Decimal("6.99")

    def test_formatted_amount_usd(self, payment):
        assert payment.formatted_amount == "$9.99"

    def test_formatted_amount_eur(self, user):
        payment = PaymentHistory.objects.create(
            user=user,
            amount=Decimal("10.00"),
            currency="EUR",
            status=PaymentHistory.Status.SUCCEEDED,
        )
        assert payment.formatted_amount == "\u20ac10.00"

    def test_formatted_amount_gbp(self, user):
        payment = PaymentHistory.objects.create(
            user=user,
            amount=Decimal("8.50"),
            currency="GBP",
            status=PaymentHistory.Status.SUCCEEDED,
        )
        assert payment.formatted_amount == "\u00a38.50"

    def test_formatted_amount_unknown_currency(self, user):
        payment = PaymentHistory.objects.create(
            user=user,
            amount=Decimal("100.00"),
            currency="JPY",
            status=PaymentHistory.Status.SUCCEEDED,
        )
        assert payment.formatted_amount == "JPY100.00"

    def test_all_status_choices(self):
        expected = ['succeeded', 'pending', 'failed', 'refunded',
                    'partially_refunded', 'canceled']
        actual = [c[0] for c in PaymentHistory.Status.choices]
        assert set(expected) == set(actual)


# =============================================================================
# SubscriptionEvent Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionEvent:

    @pytest.fixture
    def plan(self, db):
        return SubscriptionPlan.objects.create(
            name="Test", slug="test-evt", tier="premium",
            price_monthly=Decimal("9.99"),
        )

    @pytest.fixture
    def subscription(self, user, plan):
        return Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
        )

    def test_create_event(self, subscription):
        event = SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='created',
            description='Subscription created.',
        )
        assert event.pk is not None
        assert event.event_type == 'created'

    def test_event_with_metadata(self, subscription):
        event = SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='upgraded',
            description='Plan upgraded.',
            metadata={'old_plan': 'free', 'new_plan': 'premium'},
        )
        assert event.metadata == {'old_plan': 'free', 'new_plan': 'premium'}

    def test_event_with_stripe_id(self, subscription):
        event = SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='updated',
            stripe_event_id='evt_test123',
        )
        assert event.stripe_event_id == 'evt_test123'


# =============================================================================
# Invoice Tests
# =============================================================================

@pytest.mark.django_db
class TestInvoice:

    @pytest.fixture
    def plan(self, db):
        return SubscriptionPlan.objects.create(
            name="Test", slug="test-inv", tier="premium",
            price_monthly=Decimal("9.99"),
        )

    @pytest.fixture
    def subscription(self, user, plan):
        return Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
        )

    def test_create_invoice(self, subscription):
        invoice = Invoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='inv_test123',
            invoice_number='INV-001',
            amount_due=Decimal("9.99"),
            amount_paid=Decimal("9.99"),
            currency='USD',
            status='paid',
        )
        assert invoice.pk is not None
        assert "INV-001" in str(invoice)

    def test_invoice_ordering(self, subscription):
        inv1 = Invoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='inv_1',
            amount_due=Decimal("9.99"),
        )
        inv2 = Invoice.objects.create(
            subscription=subscription,
            stripe_invoice_id='inv_2',
            amount_due=Decimal("9.99"),
        )
        invoices = list(Invoice.objects.filter(subscription=subscription))
        assert invoices[0] == inv2  # Newest first
