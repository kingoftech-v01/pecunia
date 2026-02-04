"""
Tests for Stripe webhooks.

Tests signature verification, idempotency, event routing, and all handler functions.
"""
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from django.utils import timezone

from apps.subscriptions.models import (
    SubscriptionPlan,
    Subscription,
    SubscriptionEvent,
    Invoice,
)
from apps.subscriptions.webhooks import (
    WebhookIdempotencyManager,
    WebhookErrorNotifier,
    WebhookEventLogger,
    stripe_webhook,
    route_webhook_event,
    WEBHOOK_HANDLERS,
)


# =============================================================================
# WebhookIdempotencyManager Tests
# =============================================================================

@pytest.mark.django_db
class TestWebhookIdempotencyManager:

    def setup_method(self):
        cache.clear()

    def test_get_cache_key(self):
        key = WebhookIdempotencyManager.get_cache_key('evt_123')
        assert key == 'stripe_webhook_processed_evt_123'

    def test_event_not_processed(self):
        assert WebhookIdempotencyManager.is_event_processed('evt_new') is False

    def test_mark_event_processed(self):
        WebhookIdempotencyManager.mark_event_processed('evt_mark')
        assert WebhookIdempotencyManager.is_event_processed('evt_mark') is True

    def test_idempotency_cache_based(self):
        """Event should be detected as processed from cache."""
        WebhookIdempotencyManager.mark_event_processed('evt_cache')
        assert WebhookIdempotencyManager.is_event_processed('evt_cache') is True

    def test_idempotency_db_fallback(self, user, db):
        """Event should be detected from DB if cache is evicted."""
        plan = SubscriptionPlan.objects.create(
            name="Test", slug="test-idem", tier="premium",
            price_monthly=Decimal("9.99"),
        )
        sub = Subscription.objects.create(
            user=user, plan=plan, status='active',
        )
        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type='test',
            stripe_event_id='evt_db_fallback',
        )
        # Clear cache to force DB fallback
        cache.clear()
        assert WebhookIdempotencyManager.is_event_processed('evt_db_fallback') is True

    def test_get_event_hash(self):
        data1 = {'type': 'checkout.session.completed', 'id': 'evt_1'}
        data2 = {'type': 'checkout.session.completed', 'id': 'evt_1'}
        data3 = {'type': 'checkout.session.completed', 'id': 'evt_2'}

        hash1 = WebhookIdempotencyManager.get_event_hash(data1)
        hash2 = WebhookIdempotencyManager.get_event_hash(data2)
        hash3 = WebhookIdempotencyManager.get_event_hash(data3)

        assert hash1 == hash2  # Same data = same hash
        assert hash1 != hash3  # Different data = different hash


# =============================================================================
# WebhookErrorNotifier Tests
# =============================================================================

class TestWebhookErrorNotifier:

    def test_notify_error_logs(self):
        """Should log the error without raising."""
        WebhookErrorNotifier.notify_error(
            event_type='test.event',
            event_id='evt_err_test',
            error=Exception("Test error"),
            context={'test': True},
        )
        # Should not raise

    @override_settings(WEBHOOK_ERROR_EMAILS=['admin@example.com'])
    @patch('apps.subscriptions.webhooks.WebhookErrorNotifier._send_email_notification')
    def test_notify_sends_email(self, mock_send):
        WebhookErrorNotifier.notify_error(
            event_type='test.event',
            event_id='evt_email',
            error=Exception("Error"),
        )
        mock_send.assert_called_once()

    @override_settings(SLACK_WEBHOOK_URL='https://hooks.slack.com/test')
    @patch('apps.subscriptions.webhooks.WebhookErrorNotifier._send_slack_notification')
    def test_notify_sends_slack(self, mock_send):
        WebhookErrorNotifier.notify_error(
            event_type='test.event',
            event_id='evt_slack',
            error=Exception("Error"),
        )
        mock_send.assert_called_once()


# =============================================================================
# WEBHOOK_HANDLERS Registry Tests
# =============================================================================

class TestWebhookHandlers:

    def test_handlers_registered(self):
        """Verify expected event types are registered."""
        expected_events = [
            'checkout.session.completed',
            'customer.subscription.updated',
            'customer.subscription.deleted',
            'invoice.paid',
            'invoice.payment_failed',
        ]
        for event_type in expected_events:
            assert event_type in WEBHOOK_HANDLERS, f"Handler missing for {event_type}"


# =============================================================================
# route_webhook_event Tests
# =============================================================================

@pytest.mark.django_db
class TestRouteWebhookEvent:

    def test_route_unknown_event(self):
        """Unknown events should be handled gracefully."""
        event = {
            'id': 'evt_unknown',
            'type': 'unknown.event.type',
            'data': {'object': {}},
        }
        # Should not raise; returns False for unhandled
        result = route_webhook_event('unknown.event.type', {}, event)
        assert result is False

    def test_route_checkout_completed(self):
        mock_handler = MagicMock()
        event = {
            'id': 'evt_checkout',
            'type': 'checkout.session.completed',
            'data': {'object': {'id': 'cs_test'}},
        }
        with patch.dict(WEBHOOK_HANDLERS, {'checkout.session.completed': mock_handler}):
            result = route_webhook_event('checkout.session.completed', {'id': 'cs_test'}, event)
        assert result is True
        mock_handler.assert_called_once()


# =============================================================================
# stripe_webhook View Tests
# =============================================================================

@pytest.mark.django_db
class TestStripeWebhookView:

    def setup_method(self):
        self.factory = RequestFactory()
        cache.clear()

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_webhook_valid_signature(self, mock_stripe_service):
        """Test webhook with valid signature verification."""
        mock_event = {
            'id': 'evt_valid',
            'type': 'checkout.session.completed',
            'data': {'object': {'id': 'cs_test'}},
        }
        mock_stripe_service.verify_webhook_signature.return_value = mock_event

        request = self.factory.post(
            '/subscriptions/webhooks/stripe/',
            data=json.dumps(mock_event),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='t=123,v1=abc',
        )

        with patch('apps.subscriptions.webhooks.route_webhook_event', return_value=True):
            response = stripe_webhook(request)
        assert response.status_code == 200

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_webhook_invalid_signature(self, mock_stripe_service):
        """Test webhook rejects invalid signature."""
        mock_stripe_service.verify_webhook_signature.side_effect = Exception(
            "Invalid signature"
        )

        request = self.factory.post(
            '/subscriptions/webhooks/stripe/',
            data=b'{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_sig',
        )

        response = stripe_webhook(request)
        assert response.status_code == 400

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_webhook_idempotency(self, mock_stripe_service):
        """Test that duplicate events are skipped."""
        mock_event = {
            'id': 'evt_duplicate',
            'type': 'checkout.session.completed',
            'data': {'object': {'id': 'cs_test'}},
        }
        mock_stripe_service.verify_webhook_signature.return_value = mock_event

        # Mark event as already processed
        WebhookIdempotencyManager.mark_event_processed('evt_duplicate')

        request = self.factory.post(
            '/subscriptions/webhooks/stripe/',
            data=json.dumps(mock_event),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='t=123,v1=abc',
        )

        response = stripe_webhook(request)
        assert response.status_code == 200  # Returns OK but skips processing

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('apps.subscriptions.webhooks.stripe_service')
    @patch('apps.subscriptions.webhooks.route_webhook_event')
    def test_webhook_handler_error_returns_500(self, mock_route, mock_stripe_service):
        """Handler errors should return 500 for Stripe to retry."""
        mock_event = {
            'id': 'evt_error',
            'type': 'invoice.paid',
            'data': {'object': {}},
        }
        mock_stripe_service.verify_webhook_signature.return_value = mock_event
        mock_route.side_effect = Exception("Handler error")

        request = self.factory.post(
            '/subscriptions/webhooks/stripe/',
            data=json.dumps(mock_event),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='t=123,v1=abc',
        )

        response = stripe_webhook(request)
        assert response.status_code == 500

    def test_webhook_missing_signature(self):
        """Test webhook without signature header."""
        request = self.factory.post(
            '/subscriptions/webhooks/stripe/',
            data=b'{}',
            content_type='application/json',
        )
        response = stripe_webhook(request)
        assert response.status_code == 400


# =============================================================================
# Webhook Handler Function Tests
# =============================================================================

@pytest.mark.django_db
class TestWebhookHandlers:

    @pytest.fixture
    def plan(self, db):
        return SubscriptionPlan.objects.create(
            name="Premium", slug="premium-wh", tier="premium",
            price_monthly=Decimal("9.99"),
            stripe_price_id_monthly="price_wh_monthly",
        )

    @pytest.fixture
    def subscription(self, user, plan):
        return Subscription.objects.create(
            user=user, plan=plan,
            status=Subscription.Status.ACTIVE,
            stripe_subscription_id='sub_wh_test',
            stripe_customer_id='cus_wh_test',
        )

    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_handle_checkout_completed(self, mock_stripe_service, user, plan):
        from apps.subscriptions.webhooks import handle_checkout_completed

        user.stripe_customer_id = 'cus_wh_test'
        user.save()

        event = {
            'id': 'evt_checkout_test',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_completed',
                    'customer': 'cus_wh_test',
                    'subscription': 'sub_new_123',
                    'metadata': {
                        'user_id': str(user.id),
                        'plan_id': str(plan.id),
                    },
                }
            },
        }
        mock_stripe_service.get_subscription.return_value = {
            'id': 'sub_new_123',
            'status': 'active',
            'current_period_start': 1704067200,
            'current_period_end': 1706745600,
            'items': {'data': [{'price': {'id': 'price_wh_monthly'}}]},
        }
        mock_stripe_service.timestamp_to_datetime.return_value = timezone.now()

        data = event['data']['object']
        handle_checkout_completed(data, event)

    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_handle_subscription_updated(self, mock_stripe_service, subscription):
        from apps.subscriptions.webhooks import handle_subscription_updated

        event = {
            'id': 'evt_sub_updated',
            'type': 'customer.subscription.updated',
            'data': {
                'object': {
                    'id': 'sub_wh_test',
                    'status': 'active',
                    'cancel_at_period_end': False,
                    'current_period_start': 1704067200,
                    'current_period_end': 1706745600,
                    'items': {'data': [{'price': {'id': 'price_wh_monthly'}}]},
                },
                'previous_attributes': {
                    'status': 'trialing',
                },
            },
        }
        mock_stripe_service.timestamp_to_datetime.return_value = timezone.now()

        data = event['data']['object']
        handle_subscription_updated(data, event)
        subscription.refresh_from_db()

    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_handle_subscription_deleted(self, mock_stripe_service, subscription, user):
        from apps.subscriptions.webhooks import handle_subscription_deleted

        event = {
            'id': 'evt_sub_deleted',
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'id': 'sub_wh_test',
                    'status': 'canceled',
                }
            },
        }

        data = event['data']['object']
        handle_subscription_deleted(data, event)
        subscription.refresh_from_db()
        assert subscription.status == 'canceled'
        user.refresh_from_db()
        assert user.subscription_tier == 'free'

    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_handle_invoice_paid(self, mock_stripe_service, subscription):
        from apps.subscriptions.webhooks import handle_invoice_paid

        event = {
            'id': 'evt_invoice_paid',
            'type': 'invoice.paid',
            'data': {
                'object': {
                    'id': 'in_paid_123',
                    'subscription': 'sub_wh_test',
                    'number': 'INV-2024-001',
                    'amount_due': 999,
                    'amount_paid': 999,
                    'currency': 'eur',
                    'status': 'paid',
                    'payment_intent': 'pi_123',
                    'invoice_pdf': 'https://files.stripe.com/pdf/123',
                    'hosted_invoice_url': 'https://invoice.stripe.com/i/123',
                    'period_start': 1704067200,
                    'period_end': 1706745600,
                }
            },
        }
        mock_stripe_service.timestamp_to_datetime.return_value = timezone.now()
        mock_stripe_service.amount_to_decimal.return_value = Decimal('9.99')

        data = event['data']['object']
        handle_invoice_paid(data, event)
        # Check invoice was created
        assert Invoice.objects.filter(stripe_invoice_id='in_paid_123').exists()

    @patch('apps.subscriptions.webhooks.stripe_service')
    def test_handle_invoice_payment_failed(self, mock_stripe_service, subscription):
        from apps.subscriptions.webhooks import handle_invoice_payment_failed

        event = {
            'id': 'evt_payment_failed',
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'id': 'in_failed_123',
                    'subscription': 'sub_wh_test',
                    'number': 'INV-FAIL-001',
                    'amount_due': 999,
                    'amount_paid': 0,
                    'currency': 'eur',
                    'status': 'open',
                    'payment_intent': 'pi_failed',
                }
            },
        }
        mock_stripe_service.timestamp_to_datetime.return_value = timezone.now()
        mock_stripe_service.amount_to_decimal.return_value = Decimal('9.99')

        data = event['data']['object']
        handle_invoice_payment_failed(data, event)
        subscription.refresh_from_db()
        assert subscription.status == 'past_due'
