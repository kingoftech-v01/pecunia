"""
Stripe Webhooks Handler.

Handles all Stripe webhook events with idempotency and error notification.
"""
import json
import logging
import hashlib
from functools import wraps
from typing import Callable, Dict, Any, Optional

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.cache import cache

from .models import (
    Subscription,
    SubscriptionPlan,
    SubscriptionEvent,
    Invoice,
)
from .stripe_service import stripe_service

logger = logging.getLogger(__name__)


# =============================================================================
# Idempotency Helper
# =============================================================================

class WebhookIdempotencyManager:
    """
    Manages webhook event idempotency using cache.

    Prevents duplicate processing of the same webhook event.
    """
    CACHE_PREFIX = 'stripe_webhook_processed_'
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    @classmethod
    def get_cache_key(cls, event_id: str) -> str:
        """Generate cache key for event."""
        return f"{cls.CACHE_PREFIX}{event_id}"

    @classmethod
    def is_event_processed(cls, event_id: str) -> bool:
        """Check if event has already been processed."""
        return cache.get(cls.get_cache_key(event_id)) is not None

    @classmethod
    def mark_event_processed(cls, event_id: str) -> None:
        """Mark event as processed."""
        cache.set(
            cls.get_cache_key(event_id),
            timezone.now().isoformat(),
            cls.CACHE_TIMEOUT
        )

    @classmethod
    def get_event_hash(cls, event_data: Dict[str, Any]) -> str:
        """Generate hash from event data for deduplication."""
        data_str = json.dumps(event_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


# =============================================================================
# Error Notification
# =============================================================================

class WebhookErrorNotifier:
    """
    Handles error notifications for webhook failures.

    Sends alerts to configured channels (email, Slack, etc.).
    """

    @classmethod
    def notify_error(
        cls,
        event_type: str,
        event_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Notify about webhook processing error.

        Args:
            event_type: Stripe event type.
            event_id: Stripe event ID.
            error: Exception that occurred.
            context: Additional context information.
        """
        error_message = f"Stripe webhook error: {event_type} ({event_id}): {str(error)}"
        logger.error(error_message, exc_info=True, extra={
            'event_type': event_type,
            'event_id': event_id,
            'context': context,
        })

        # Send email notification to admins if configured
        if hasattr(settings, 'WEBHOOK_ERROR_EMAILS') and settings.WEBHOOK_ERROR_EMAILS:
            cls._send_email_notification(event_type, event_id, error, context)

        # Send Slack notification if configured
        if hasattr(settings, 'SLACK_WEBHOOK_URL') and settings.SLACK_WEBHOOK_URL:
            cls._send_slack_notification(event_type, event_id, error, context)

    @classmethod
    def _send_email_notification(
        cls,
        event_type: str,
        event_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send email notification to admins."""
        try:
            from django.core.mail import mail_admins

            subject = f"Stripe Webhook Error: {event_type}"
            message = f"""
Stripe Webhook Processing Error

Event Type: {event_type}
Event ID: {event_id}
Error: {str(error)}
Time: {timezone.now().isoformat()}

Context:
{json.dumps(context or {}, indent=2)}
            """
            mail_admins(subject, message, fail_silently=True)
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    @classmethod
    def _send_slack_notification(
        cls,
        event_type: str,
        event_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send Slack notification."""
        try:
            import requests

            slack_url = settings.SLACK_WEBHOOK_URL
            payload = {
                'text': f":warning: *Stripe Webhook Error*",
                'attachments': [{
                    'color': 'danger',
                    'fields': [
                        {'title': 'Event Type', 'value': event_type, 'short': True},
                        {'title': 'Event ID', 'value': event_id, 'short': True},
                        {'title': 'Error', 'value': str(error), 'short': False},
                        {'title': 'Time', 'value': timezone.now().isoformat(), 'short': True},
                    ]
                }]
            }
            requests.post(slack_url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")


# =============================================================================
# Event Logging
# =============================================================================

class WebhookEventLogger:
    """
    Logs webhook events for auditing and debugging.
    """

    @classmethod
    def log_event_received(cls, event_type: str, event_id: str) -> None:
        """Log that an event was received."""
        logger.info(f"Stripe webhook received: {event_type} ({event_id})")

    @classmethod
    def log_event_processed(cls, event_type: str, event_id: str, result: str = 'success') -> None:
        """Log that an event was processed."""
        logger.info(f"Stripe webhook processed: {event_type} ({event_id}) - {result}")

    @classmethod
    def log_event_skipped(cls, event_type: str, event_id: str, reason: str) -> None:
        """Log that an event was skipped."""
        logger.info(f"Stripe webhook skipped: {event_type} ({event_id}) - {reason}")


# =============================================================================
# Webhook Event Handlers
# =============================================================================

def handle_checkout_completed(data: Dict[str, Any], event: Dict[str, Any]) -> None:
    """
    Handle successful checkout session completion.

    Creates or updates subscription after successful payment.

    Args:
        data: Checkout session data from Stripe.
        event: Full Stripe event object.
    """
    from apps.accounts.models import User

    customer_id = data.get('customer')
    subscription_id = data.get('subscription')
    metadata = data.get('metadata', {})
    user_id = metadata.get('user_id')

    if not user_id:
        logger.warning(f"Missing user_id in checkout session metadata: {data.get('id')}")
        return

    if not subscription_id:
        logger.warning(f"Missing subscription_id in checkout session: {data.get('id')}")
        return

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User not found for checkout completion: {user_id}")
        raise ValueError(f"User not found: {user_id}")

    # Get plan from metadata
    plan_id = metadata.get('plan_id')
    billing_interval = metadata.get('billing_interval', 'month')

    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        logger.error(f"Plan not found for checkout completion: {plan_id}")
        raise ValueError(f"Plan not found: {plan_id}")

    # Get subscription details from Stripe
    stripe_sub = stripe_service.get_subscription(subscription_id)
    if not stripe_sub:
        raise ValueError(f"Could not retrieve Stripe subscription: {subscription_id}")

    with transaction.atomic():
        # Create or update subscription
        subscription, created = Subscription.objects.update_or_create(
            user=user,
            defaults={
                'plan': plan,
                'stripe_subscription_id': subscription_id,
                'stripe_customer_id': customer_id,
                'status': stripe_sub.get('status', 'active'),
                'billing_interval': billing_interval,
                'current_period_start': stripe_service.timestamp_to_datetime(
                    stripe_sub.get('current_period_start', 0)
                ) if stripe_sub.get('current_period_start') else None,
                'current_period_end': stripe_service.timestamp_to_datetime(
                    stripe_sub.get('current_period_end', 0)
                ) if stripe_sub.get('current_period_end') else None,
            }
        )

        # Handle trial period
        if stripe_sub.get('trial_start'):
            subscription.trial_start = stripe_service.timestamp_to_datetime(
                stripe_sub['trial_start']
            )
        if stripe_sub.get('trial_end'):
            subscription.trial_end = stripe_service.timestamp_to_datetime(
                stripe_sub['trial_end']
            )
            subscription.status = 'trialing'
        subscription.save()

        # Update user's subscription tier and customer ID
        user.subscription_tier = plan.tier
        if not user.stripe_customer_id:
            user.stripe_customer_id = customer_id
        user.save(update_fields=['subscription_tier', 'stripe_customer_id'])

        # Log subscription event
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='created' if created else 'updated',
            description=f'Subscription {"created" if created else "updated"} via checkout',
            stripe_event_id=event.get('id'),
            metadata={
                'plan_id': str(plan_id),
                'plan_name': plan.name,
                'billing_interval': billing_interval,
                'checkout_session_id': data.get('id'),
            }
        )

    logger.info(f"Checkout completed for user {user.email}: subscription {'created' if created else 'updated'}")


def handle_subscription_updated(data: Dict[str, Any], event: Dict[str, Any]) -> None:
    """
    Handle subscription update events.

    Updates local subscription record with changes from Stripe.

    Args:
        data: Subscription data from Stripe.
        event: Full Stripe event object.
    """
    subscription_id = data.get('id')

    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        logger.warning(f"Subscription not found for update: {subscription_id}")
        return

    # Track changes for event logging
    changes = []

    # Update status
    new_status = data.get('status')
    if new_status and new_status != subscription.status:
        changes.append(f"status: {subscription.status} -> {new_status}")
        subscription.status = new_status

    # Update cancel_at_period_end
    new_cancel_at_period_end = data.get('cancel_at_period_end', False)
    if new_cancel_at_period_end != subscription.cancel_at_period_end:
        changes.append(f"cancel_at_period_end: {subscription.cancel_at_period_end} -> {new_cancel_at_period_end}")
        subscription.cancel_at_period_end = new_cancel_at_period_end

    # Update period dates
    if data.get('current_period_start'):
        subscription.current_period_start = stripe_service.timestamp_to_datetime(
            data['current_period_start']
        )
    if data.get('current_period_end'):
        subscription.current_period_end = stripe_service.timestamp_to_datetime(
            data['current_period_end']
        )

    # Update canceled_at
    if data.get('canceled_at'):
        subscription.canceled_at = stripe_service.timestamp_to_datetime(
            data['canceled_at']
        )

    # Update trial dates
    if data.get('trial_start'):
        subscription.trial_start = stripe_service.timestamp_to_datetime(
            data['trial_start']
        )
    if data.get('trial_end'):
        subscription.trial_end = stripe_service.timestamp_to_datetime(
            data['trial_end']
        )

    # Check for plan change
    items = data.get('items', {}).get('data', [])
    if items:
        price_id = items[0].get('price', {}).get('id')
        if price_id:
            # Try to find plan by price ID
            plan = SubscriptionPlan.objects.filter(
                models.Q(stripe_price_id_monthly=price_id) |
                models.Q(stripe_price_id_yearly=price_id)
            ).first()

            if plan and plan != subscription.plan:
                old_plan_name = subscription.plan.name
                changes.append(f"plan: {old_plan_name} -> {plan.name}")
                subscription.plan = plan

                # Update user's subscription tier
                subscription.user.subscription_tier = plan.tier
                subscription.user.save(update_fields=['subscription_tier'])

    subscription.save()

    # Log event
    SubscriptionEvent.objects.create(
        subscription=subscription,
        event_type='updated',
        description=f'Subscription updated: {", ".join(changes) if changes else "no tracked changes"}',
        stripe_event_id=event.get('id'),
        metadata={
            'changes': changes,
            'new_status': subscription.status,
        }
    )

    logger.info(f"Subscription {subscription_id} updated: {', '.join(changes) if changes else 'minor changes'}")


def handle_subscription_deleted(data: Dict[str, Any], event: Dict[str, Any]) -> None:
    """
    Handle subscription deletion/cancellation.

    Marks subscription as canceled and updates user tier.

    Args:
        data: Subscription data from Stripe.
        event: Full Stripe event object.
    """
    subscription_id = data.get('id')

    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        logger.warning(f"Subscription not found for deletion: {subscription_id}")
        return

    with transaction.atomic():
        # Update subscription status
        subscription.status = 'canceled'
        subscription.canceled_at = timezone.now()
        subscription.save()

        # Update user's subscription tier to free
        subscription.user.subscription_tier = 'free'
        subscription.user.save(update_fields=['subscription_tier'])

        # Log event
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='canceled',
            description='Subscription canceled/deleted',
            stripe_event_id=event.get('id'),
            metadata={
                'cancellation_reason': data.get('cancellation_details', {}).get('reason'),
                'canceled_at': subscription.canceled_at.isoformat(),
            }
        )

    logger.info(f"Subscription {subscription_id} canceled for user {subscription.user.email}")


def handle_invoice_paid(data: Dict[str, Any], event: Dict[str, Any]) -> None:
    """
    Handle successful invoice payment.

    Creates/updates invoice record and logs payment event.

    Args:
        data: Invoice data from Stripe.
        event: Full Stripe event object.
    """
    subscription_id = data.get('subscription')
    if not subscription_id:
        # One-time payment, not subscription-related
        logger.info(f"Invoice paid for non-subscription: {data.get('id')}")
        return

    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        logger.warning(f"Subscription not found for paid invoice: {subscription_id}")
        return

    with transaction.atomic():
        # Create or update invoice record
        invoice, created = Invoice.objects.update_or_create(
            stripe_invoice_id=data.get('id'),
            defaults={
                'subscription': subscription,
                'stripe_payment_intent_id': data.get('payment_intent'),
                'invoice_number': data.get('number', ''),
                'amount_due': stripe_service.amount_to_decimal(
                    data.get('amount_due', 0),
                    data.get('currency', 'eur')
                ),
                'amount_paid': stripe_service.amount_to_decimal(
                    data.get('amount_paid', 0),
                    data.get('currency', 'eur')
                ),
                'currency': data.get('currency', 'EUR').upper(),
                'status': 'paid',
                'invoice_pdf_url': data.get('invoice_pdf', ''),
                'hosted_invoice_url': data.get('hosted_invoice_url', ''),
                'period_start': stripe_service.timestamp_to_datetime(
                    data['period_start']
                ) if data.get('period_start') else None,
                'period_end': stripe_service.timestamp_to_datetime(
                    data['period_end']
                ) if data.get('period_end') else None,
                'due_date': stripe_service.timestamp_to_datetime(
                    data['due_date']
                ) if data.get('due_date') else None,
                'paid_at': stripe_service.timestamp_to_datetime(
                    data.get('status_transitions', {}).get('paid_at', 0)
                ) if data.get('status_transitions', {}).get('paid_at') else timezone.now(),
            }
        )

        # Update subscription status if it was past_due
        if subscription.status == 'past_due':
            subscription.status = 'active'
            subscription.save(update_fields=['status'])

        # Log event
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='invoice_paid',
            description=f'Invoice {data.get("number", "N/A")} paid - {data.get("currency", "EUR").upper()} {stripe_service.amount_to_decimal(data.get("amount_paid", 0), data.get("currency", "eur"))}',
            stripe_event_id=event.get('id'),
            metadata={
                'invoice_id': data.get('id'),
                'invoice_number': data.get('number'),
                'amount_paid': data.get('amount_paid'),
                'currency': data.get('currency'),
            }
        )

    logger.info(f"Invoice {data.get('id')} paid for subscription {subscription_id}")


def handle_invoice_payment_failed(data: Dict[str, Any], event: Dict[str, Any]) -> None:
    """
    Handle failed invoice payment.

    Updates subscription status and notifies user/admins.

    Args:
        data: Invoice data from Stripe.
        event: Full Stripe event object.
    """
    subscription_id = data.get('subscription')
    if not subscription_id:
        logger.info(f"Invoice payment failed for non-subscription: {data.get('id')}")
        return

    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        logger.warning(f"Subscription not found for failed invoice: {subscription_id}")
        return

    with transaction.atomic():
        # Update subscription status
        subscription.status = 'past_due'
        subscription.save(update_fields=['status'])

        # Create or update invoice record
        Invoice.objects.update_or_create(
            stripe_invoice_id=data.get('id'),
            defaults={
                'subscription': subscription,
                'stripe_payment_intent_id': data.get('payment_intent'),
                'invoice_number': data.get('number', ''),
                'amount_due': stripe_service.amount_to_decimal(
                    data.get('amount_due', 0),
                    data.get('currency', 'eur')
                ),
                'amount_paid': stripe_service.amount_to_decimal(
                    data.get('amount_paid', 0),
                    data.get('currency', 'eur')
                ),
                'currency': data.get('currency', 'EUR').upper(),
                'status': 'open',  # Payment failed, invoice still open
                'invoice_pdf_url': data.get('invoice_pdf', ''),
                'hosted_invoice_url': data.get('hosted_invoice_url', ''),
            }
        )

        # Log event
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='invoice_payment_failed',
            description=f'Invoice payment failed: {data.get("number", "N/A")} - Attempt {data.get("attempt_count", 1)}',
            stripe_event_id=event.get('id'),
            metadata={
                'invoice_id': data.get('id'),
                'invoice_number': data.get('number'),
                'attempt_count': data.get('attempt_count'),
                'next_payment_attempt': data.get('next_payment_attempt'),
            }
        )

    # Notify about payment failure
    WebhookErrorNotifier.notify_error(
        event_type='invoice.payment_failed',
        event_id=event.get('id', 'unknown'),
        error=Exception(f"Payment failed for subscription {subscription_id}"),
        context={
            'user_email': subscription.user.email,
            'invoice_number': data.get('number'),
            'attempt_count': data.get('attempt_count'),
            'amount_due': data.get('amount_due'),
        }
    )

    logger.warning(f"Invoice payment failed for subscription {subscription_id}")


# =============================================================================
# Event Router
# =============================================================================

# Map Stripe event types to handler functions
WEBHOOK_HANDLERS: Dict[str, Callable] = {
    'checkout.session.completed': handle_checkout_completed,
    'customer.subscription.updated': handle_subscription_updated,
    'customer.subscription.deleted': handle_subscription_deleted,
    'invoice.paid': handle_invoice_paid,
    'invoice.payment_failed': handle_invoice_payment_failed,
}


def route_webhook_event(event_type: str, data: Dict[str, Any], event: Dict[str, Any]) -> bool:
    """
    Route webhook event to appropriate handler.

    Args:
        event_type: Stripe event type string.
        data: Event data object.
        event: Full event object.

    Returns:
        True if event was handled, False otherwise.
    """
    handler = WEBHOOK_HANDLERS.get(event_type)

    if handler:
        handler(data, event)
        return True

    logger.debug(f"No handler registered for event type: {event_type}")
    return False


# =============================================================================
# Main Webhook View
# =============================================================================

@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """
    Main Stripe webhook endpoint.

    Handles signature verification, idempotency, and event routing.

    Args:
        request: Django HTTP request.

    Returns:
        HTTP response (200 for success, 400 for bad request, 500 for error).
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    # Verify webhook signature and construct event
    event = stripe_service.construct_webhook_event(payload, sig_header)

    if not event:
        logger.error("Webhook signature verification failed")
        return HttpResponse(
            json.dumps({'error': 'Invalid signature'}),
            status=400,
            content_type='application/json'
        )

    event_id = event.get('id', 'unknown')
    event_type = event.get('type', 'unknown')

    # Log event received
    WebhookEventLogger.log_event_received(event_type, event_id)

    # Check idempotency - skip if already processed
    if WebhookIdempotencyManager.is_event_processed(event_id):
        WebhookEventLogger.log_event_skipped(event_type, event_id, 'already processed')
        return HttpResponse(
            json.dumps({'status': 'already_processed'}),
            status=200,
            content_type='application/json'
        )

    try:
        # Get event data
        data = event.get('data', {}).get('object', {})

        # Route to appropriate handler
        handled = route_webhook_event(event_type, data, event)

        # Mark event as processed
        WebhookIdempotencyManager.mark_event_processed(event_id)

        # Log success
        if handled:
            WebhookEventLogger.log_event_processed(event_type, event_id)
        else:
            WebhookEventLogger.log_event_skipped(event_type, event_id, 'no handler')

        return HttpResponse(
            json.dumps({'status': 'success', 'handled': handled}),
            status=200,
            content_type='application/json'
        )

    except Exception as e:
        # Log and notify error
        WebhookErrorNotifier.notify_error(
            event_type=event_type,
            event_id=event_id,
            error=e,
            context={'payload_preview': str(payload)[:500]}
        )

        # Return 500 to trigger Stripe retry
        return HttpResponse(
            json.dumps({'error': str(e)}),
            status=500,
            content_type='application/json'
        )


# =============================================================================
# Additional Webhook Endpoints (for testing/debugging)
# =============================================================================

@csrf_exempt
@require_POST
def stripe_webhook_test(request: HttpRequest) -> HttpResponse:
    """
    Test webhook endpoint (only available in DEBUG mode).

    Accepts unverified webhooks for local development.
    """
    if not settings.DEBUG:
        return HttpResponse(status=404)

    try:
        payload = json.loads(request.body)
        event_type = payload.get('type', 'unknown')
        event_id = payload.get('id', f'test_{timezone.now().timestamp()}')
        data = payload.get('data', {}).get('object', {})

        logger.info(f"Test webhook received: {event_type}")

        handled = route_webhook_event(event_type, data, payload)

        return HttpResponse(
            json.dumps({'status': 'success', 'handled': handled, 'test_mode': True}),
            status=200,
            content_type='application/json'
        )

    except json.JSONDecodeError:
        return HttpResponse(
            json.dumps({'error': 'Invalid JSON'}),
            status=400,
            content_type='application/json'
        )
    except Exception as e:
        logger.error(f"Test webhook error: {e}")
        return HttpResponse(
            json.dumps({'error': str(e)}),
            status=500,
            content_type='application/json'
        )


# Import for models.Q
from django.db import models
