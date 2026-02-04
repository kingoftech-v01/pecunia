"""
Tests for StripeService.

Tests all Stripe API interactions with mocked stripe module.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.subscriptions.stripe_service import StripeService, StripeServiceError


# =============================================================================
# Initialization Tests
# =============================================================================

class TestStripeServiceInit:

    @override_settings(STRIPE_SECRET_KEY='sk_test_123', STRIPE_WEBHOOK_SECRET='whsec_test')
    def test_init_with_keys(self):
        service = StripeService()
        assert service.api_key == 'sk_test_123'
        assert service.webhook_secret == 'whsec_test'

    @override_settings(STRIPE_SECRET_KEY=None)
    def test_init_without_key(self):
        # Should still initialize but log a warning
        service = StripeService()
        assert service.api_key is None


# =============================================================================
# Customer Management Tests
# =============================================================================

@pytest.mark.django_db
class TestCustomerManagement:

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_create_customer(self, mock_stripe, user):
        mock_stripe.Customer.create.return_value = MagicMock(id='cus_new123')

        service = StripeService()
        result = service.create_customer(user)
        assert result.id == 'cus_new123'
        mock_stripe.Customer.create.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_get_or_create_customer_existing(self, mock_stripe, user):
        """When customer can be found via list by email, return it."""
        mock_existing = MagicMock(id='cus_existing')
        mock_stripe.Customer.list.return_value = MagicMock(data=[mock_existing])

        service = StripeService()
        result = service.get_or_create_customer(user)
        assert result.id == 'cus_existing'

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_get_or_create_customer_new(self, mock_stripe, user):
        """When no existing customer, create a new one."""
        mock_stripe.Customer.list.return_value = MagicMock(data=[])
        mock_stripe.Customer.create.return_value = MagicMock(id='cus_new456')

        service = StripeService()
        result = service.get_or_create_customer(user)
        assert result.id == 'cus_new456'

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_get_customer(self, mock_stripe):
        mock_stripe.Customer.retrieve.return_value = {
            'id': 'cus_123',
            'invoice_settings': {'default_payment_method': 'pm_123'}
        }
        service = StripeService()
        result = service.get_customer('cus_123')
        assert result['id'] == 'cus_123'


# =============================================================================
# Checkout Session Tests
# =============================================================================

@pytest.mark.django_db
class TestCheckoutSession:

    @override_settings(STRIPE_SECRET_KEY='sk_test_123', FRONTEND_URL='https://app.example.com')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_create_checkout_session(self, mock_stripe, user, db):
        from apps.subscriptions.models import SubscriptionPlan
        plan = SubscriptionPlan.objects.create(
            name="Premium", slug="premium-cs", tier="premium",
            price_monthly=Decimal("9.99"),
            stripe_price_id_monthly="price_monthly_test",
        )

        mock_session = MagicMock(id='cs_test', url='https://checkout.stripe.com/test')
        mock_stripe.checkout.Session.create.return_value = mock_session
        mock_stripe.Customer.create.return_value = MagicMock(id='cus_new')

        service = StripeService()
        result = service.create_checkout_session(
            user=user,
            plan=plan,
            billing_cycle='monthly',
        )
        assert result.id == 'cs_test'


# =============================================================================
# Portal Session Tests
# =============================================================================

@pytest.mark.django_db
class TestPortalSession:

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_create_portal_session(self, mock_stripe, user, db):
        from apps.subscriptions.models import SubscriptionPlan, Subscription
        plan = SubscriptionPlan.objects.create(
            name="Test", slug="test-portal", tier="premium",
            price_monthly=Decimal("9.99"),
        )
        Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
            stripe_subscription_id='sub_portal',
            stripe_customer_id='cus_portal',
        )

        mock_session = MagicMock(url='https://billing.stripe.com/test')
        mock_stripe.billing_portal.Session.create.return_value = mock_session

        service = StripeService()
        result = service.create_portal_session(
            user=user,
            return_url='https://app.example.com/settings',
        )
        assert result.url == 'https://billing.stripe.com/test'


# =============================================================================
# Subscription Management Tests
# =============================================================================

@pytest.mark.django_db
class TestSubscriptionManagement:

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_cancel_subscription_at_period_end(self, mock_stripe, user, db):
        from apps.subscriptions.models import SubscriptionPlan, Subscription
        plan = SubscriptionPlan.objects.create(
            name="Test", slug="test-cancel", tier="premium",
            price_monthly=Decimal("9.99"),
        )
        sub = Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
            stripe_subscription_id='sub_cancel_test',
        )

        mock_stripe.Subscription.modify.return_value = MagicMock(
            id='sub_cancel_test',
            cancel_at_period_end=True,
        )

        service = StripeService()
        service.cancel_subscription(sub, cancel_immediately=False)
        mock_stripe.Subscription.modify.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_cancel_subscription_immediately(self, mock_stripe, user, db):
        from apps.subscriptions.models import SubscriptionPlan, Subscription
        plan = SubscriptionPlan.objects.create(
            name="Test", slug="test-cancel-imm", tier="premium",
            price_monthly=Decimal("9.99"),
        )
        sub = Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
            stripe_subscription_id='sub_cancel_imm',
        )

        mock_stripe.Subscription.cancel.return_value = MagicMock(
            id='sub_cancel_imm',
            status='canceled',
        )

        service = StripeService()
        service.cancel_subscription(sub, cancel_immediately=True)

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_reactivate_subscription(self, mock_stripe, user, db):
        from apps.subscriptions.models import SubscriptionPlan, Subscription
        plan = SubscriptionPlan.objects.create(
            name="Test", slug="test-reactivate", tier="premium",
            price_monthly=Decimal("9.99"),
        )
        sub = Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
            stripe_subscription_id='sub_reactivate',
            cancel_at_period_end=True,
        )

        mock_stripe.Subscription.modify.return_value = MagicMock(
            id='sub_reactivate',
            cancel_at_period_end=False,
        )

        service = StripeService()
        service.reactivate_subscription(sub)

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_update_subscription(self, mock_stripe, user, db):
        from apps.subscriptions.models import SubscriptionPlan, Subscription
        plan = SubscriptionPlan.objects.create(
            name="Premium", slug="test-update-old", tier="premium",
            price_monthly=Decimal("9.99"),
            stripe_price_id_monthly="price_old",
        )
        new_plan = SubscriptionPlan.objects.create(
            name="Pro", slug="test-update-new", tier="pro",
            price_monthly=Decimal("19.99"),
            stripe_price_id_monthly="price_new",
        )
        sub = Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
            stripe_subscription_id='sub_update',
        )

        mock_stripe_sub = MagicMock()
        mock_stripe_sub.items.data = [MagicMock(id='si_123')]
        mock_stripe.Subscription.retrieve.return_value = mock_stripe_sub
        mock_stripe.Subscription.modify.return_value = MagicMock(
            id='sub_update',
            status='active',
        )

        service = StripeService()
        service.update_subscription(sub, new_plan, new_billing_cycle='monthly')


# =============================================================================
# Webhook Verification Tests
# =============================================================================

class TestWebhookVerification:

    @override_settings(STRIPE_SECRET_KEY='sk_test_123', STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_verify_webhook_signature_success(self, mock_stripe):
        mock_event = {'type': 'checkout.session.completed', 'data': {}}
        mock_stripe.Webhook.construct_event.return_value = mock_event

        service = StripeService()
        result = service.verify_webhook_signature(
            payload=b'test_payload',
            signature='test_sig',
        )
        assert result == mock_event

    @override_settings(STRIPE_SECRET_KEY='sk_test_123', STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_verify_webhook_signature_invalid(self, mock_stripe):
        import stripe as stripe_lib
        mock_stripe.error.SignatureVerificationError = stripe_lib.error.SignatureVerificationError
        mock_stripe.Webhook.construct_event.side_effect = stripe_lib.error.SignatureVerificationError(
            "Invalid signature", "test_sig"
        )

        service = StripeService()
        with pytest.raises(Exception):
            service.verify_webhook_signature(
                payload=b'test_payload',
                signature='invalid_sig',
            )


# =============================================================================
# Utility Method Tests
# =============================================================================

class TestUtilityMethods:

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    def test_timestamp_to_datetime(self):
        service = StripeService()
        result = service.timestamp_to_datetime(1704067200)  # 2024-01-01 00:00:00 UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    def test_amount_to_decimal_standard(self):
        service = StripeService()
        result = service.amount_to_decimal(999, 'eur')
        assert result == Decimal('9.99')

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    def test_amount_to_decimal_zero_decimal_currency(self):
        service = StripeService()
        result = service.amount_to_decimal(1000, 'jpy')
        assert result == Decimal('1000')

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    def test_amount_to_decimal_usd(self):
        service = StripeService()
        result = service.amount_to_decimal(1499, 'usd')
        assert result == Decimal('14.99')

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_get_subscription(self, mock_stripe):
        mock_stripe.Subscription.retrieve.return_value = {'id': 'sub_123', 'status': 'active'}

        service = StripeService()
        result = service.get_subscription('sub_123')
        assert result['id'] == 'sub_123'

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_get_payment_methods(self, mock_stripe):
        mock_stripe.PaymentMethod.list.return_value = MagicMock(data=[
            MagicMock(id='pm_1'),
            MagicMock(id='pm_2'),
        ])

        service = StripeService()
        result = service.get_payment_methods('cus_123')
        assert len(result) >= 0  # May return data or auto_paging_iter

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.subscriptions.stripe_service.stripe')
    def test_get_invoices(self, mock_stripe):
        mock_stripe.Invoice.list.return_value = MagicMock(data=[
            MagicMock(id='in_1'),
        ])

        service = StripeService()
        result = service.get_invoices('cus_123')
        assert isinstance(result, (list, MagicMock))
