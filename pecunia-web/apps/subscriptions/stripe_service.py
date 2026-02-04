"""
Stripe Service Module.

Handles all Stripe API interactions for subscription management.
Uses idempotency keys and webhook signature verification.
"""
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import stripe
from django.conf import settings
from django.utils import timezone

from .models import PaymentHistory, Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)


class StripeServiceError(Exception):
    """Base exception for Stripe service errors."""

    def __init__(self, message: str, stripe_error: Exception | None = None):
        self.message = message
        self.stripe_error = stripe_error
        super().__init__(self.message)


class StripeService:
    """
    Service class for managing Stripe operations.
    Handles customers, subscriptions, checkout sessions, and webhooks.
    """

    def __init__(self):
        """Initialize Stripe with API key from settings."""
        self.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
        self.webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        self.success_url = getattr(settings, 'STRIPE_SUCCESS_URL', '/subscriptions/success/')
        self.cancel_url = getattr(settings, 'STRIPE_CANCEL_URL', '/subscriptions/cancel/')
        self.portal_return_url = getattr(settings, 'STRIPE_PORTAL_RETURN_URL', '/account/billing/')

        if self.api_key:
            stripe.api_key = self.api_key
        else:
            logger.warning("STRIPE_SECRET_KEY not configured in settings")

    def _generate_idempotency_key(self, prefix: str = '') -> str:
        """Generate a unique idempotency key for Stripe requests."""
        unique_id = str(uuid.uuid4())
        if prefix:
            return f"{prefix}_{unique_id}"
        return unique_id

    def _get_absolute_url(self, path: str, request=None) -> str:
        """Convert a relative path to an absolute URL."""
        if path.startswith('http'):
            return path

        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        if request:
            base_url = f"{request.scheme}://{request.get_host()}"

        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    # ==================== Customer Management ====================

    def create_customer(self, user, metadata: dict | None = None) -> stripe.Customer:
        """
        Create a Stripe customer for a user.

        Args:
            user: Django user instance
            metadata: Optional additional metadata to store

        Returns:
            Stripe Customer object

        Raises:
            StripeServiceError: If customer creation fails
        """
        try:
            customer_metadata = {
                'user_id': str(user.id),
                'django_user_email': user.email,
            }
            if metadata:
                customer_metadata.update(metadata)

            customer = stripe.Customer.create(
                email=user.email,
                name=getattr(user, 'get_full_name', lambda: user.email)(),
                metadata=customer_metadata,
                idempotency_key=self._generate_idempotency_key(f"customer_{user.id}")
            )

            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for user {user.id}: {e}")
            raise StripeServiceError(
                f"Failed to create customer: {e.user_message if hasattr(e, 'user_message') else str(e)}",
                stripe_error=e
            )

    def get_or_create_customer(self, user) -> stripe.Customer:
        """
        Get existing Stripe customer or create a new one.

        Args:
            user: Django user instance

        Returns:
            Stripe Customer object
        """
        # Check if user has a subscription with customer ID
        subscription = getattr(user, 'subscription', None)
        if subscription and subscription.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
                if not customer.get('deleted'):
                    return customer
            except stripe.error.InvalidRequestError:
                # Customer doesn't exist, create a new one
                pass

        # Search for existing customer by email
        try:
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                return customers.data[0]
        except stripe.error.StripeError:
            pass

        # Create new customer
        return self.create_customer(user)

    def update_customer(self, customer_id: str, **kwargs) -> stripe.Customer:
        """
        Update a Stripe customer's information.

        Args:
            customer_id: Stripe customer ID
            **kwargs: Fields to update (email, name, metadata, etc.)

        Returns:
            Updated Stripe Customer object
        """
        try:
            customer = stripe.Customer.modify(customer_id, **kwargs)
            logger.info(f"Updated Stripe customer {customer_id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe customer {customer_id}: {e}")
            raise StripeServiceError(f"Failed to update customer: {str(e)}", stripe_error=e)

    # ==================== Checkout Session ====================

    def create_checkout_session(
        self,
        user,
        plan: SubscriptionPlan,
        billing_cycle: str = 'monthly',
        success_url: str | None = None,
        cancel_url: str | None = None,
        trial_days: int | None = None,
        promotion_code: str | None = None,
        request=None
    ) -> stripe.checkout.Session:
        """
        Create a Stripe Checkout Session for subscription.

        Args:
            user: Django user instance
            plan: SubscriptionPlan instance
            billing_cycle: 'monthly' or 'yearly'
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            trial_days: Number of trial days
            promotion_code: Promotion code to apply
            request: Django request object for building absolute URLs

        Returns:
            Stripe Checkout Session object

        Raises:
            StripeServiceError: If session creation fails
        """
        stripe_price_id = plan.get_stripe_price_id(billing_cycle)
        if not stripe_price_id:
            raise StripeServiceError(
                f"No Stripe price ID configured for plan '{plan.name}' with {billing_cycle} billing"
            )

        customer = self.get_or_create_customer(user)

        # Build URLs
        final_success_url = self._get_absolute_url(
            success_url or self.success_url,
            request
        ) + '?session_id={CHECKOUT_SESSION_ID}'

        final_cancel_url = self._get_absolute_url(
            cancel_url or self.cancel_url,
            request
        )

        session_params = {
            'customer': customer.id,
            'mode': 'subscription',
            'payment_method_types': ['card'],
            'line_items': [{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            'success_url': final_success_url,
            'cancel_url': final_cancel_url,
            'metadata': {
                'user_id': str(user.id),
                'plan_id': str(plan.id),
                'plan_slug': plan.slug,
                'billing_cycle': billing_cycle,
            },
            'subscription_data': {
                'metadata': {
                    'user_id': str(user.id),
                    'plan_id': str(plan.id),
                    'billing_cycle': billing_cycle,
                },
            },
            'allow_promotion_codes': True,
        }

        # Add trial period if specified
        if trial_days and trial_days > 0:
            session_params['subscription_data']['trial_period_days'] = trial_days

        # Add specific promotion code if provided
        if promotion_code:
            try:
                promo = stripe.PromotionCode.list(code=promotion_code, active=True, limit=1)
                if promo.data:
                    session_params['discounts'] = [{'promotion_code': promo.data[0].id}]
                    session_params.pop('allow_promotion_codes', None)
            except stripe.error.StripeError:
                pass  # Ignore if promo code not found

        try:
            session = stripe.checkout.Session.create(
                **session_params,
                idempotency_key=self._generate_idempotency_key(f"checkout_{user.id}_{plan.id}")
            )

            logger.info(
                f"Created checkout session {session.id} for user {user.id}, "
                f"plan {plan.slug}, cycle {billing_cycle}"
            )
            return session

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise StripeServiceError(
                f"Failed to create checkout session: {str(e)}",
                stripe_error=e
            )

    # ==================== Customer Portal ====================

    def create_portal_session(
        self,
        user,
        return_url: str | None = None,
        request=None
    ) -> stripe.billing_portal.Session:
        """
        Create a Stripe Customer Portal session for managing billing.

        Args:
            user: Django user instance
            return_url: URL to return to after portal session
            request: Django request object for building absolute URLs

        Returns:
            Stripe Billing Portal Session object

        Raises:
            StripeServiceError: If session creation fails
        """
        subscription = getattr(user, 'subscription', None)
        if not subscription or not subscription.stripe_customer_id:
            raise StripeServiceError("User does not have an active subscription with Stripe")

        final_return_url = self._get_absolute_url(
            return_url or self.portal_return_url,
            request
        )

        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=final_return_url,
            )

            logger.info(
                f"Created portal session for user {user.id}, "
                f"customer {subscription.stripe_customer_id}"
            )
            return portal_session

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise StripeServiceError(
                f"Failed to create billing portal session: {str(e)}",
                stripe_error=e
            )

    # ==================== Subscription Management ====================

    def cancel_subscription(
        self,
        subscription: Subscription,
        cancel_immediately: bool = False,
        cancellation_reason: str | None = None
    ) -> stripe.Subscription:
        """
        Cancel a Stripe subscription.

        Args:
            subscription: Django Subscription instance
            cancel_immediately: If True, cancel now. If False, cancel at period end.
            cancellation_reason: Optional reason for cancellation

        Returns:
            Updated Stripe Subscription object

        Raises:
            StripeServiceError: If cancellation fails
        """
        if not subscription.stripe_subscription_id:
            raise StripeServiceError("Subscription has no Stripe subscription ID")

        try:
            if cancel_immediately:
                stripe_sub = stripe.Subscription.delete(
                    subscription.stripe_subscription_id
                )
                subscription.status = Subscription.Status.CANCELED
                subscription.canceled_at = timezone.now()
            else:
                stripe_sub = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True,
                    metadata={
                        'cancellation_reason': cancellation_reason or 'User requested',
                        'canceled_by': 'user',
                    }
                )
                subscription.cancel_at_period_end = True
                subscription.canceled_at = timezone.now()

            subscription.save(update_fields=['status', 'cancel_at_period_end', 'canceled_at', 'updated_at'])

            logger.info(
                f"Canceled subscription {subscription.stripe_subscription_id} "
                f"({'immediately' if cancel_immediately else 'at period end'})"
            )
            return stripe_sub

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise StripeServiceError(
                f"Failed to cancel subscription: {str(e)}",
                stripe_error=e
            )

    def reactivate_subscription(self, subscription: Subscription) -> stripe.Subscription:
        """
        Reactivate a subscription that was set to cancel at period end.

        Args:
            subscription: Django Subscription instance

        Returns:
            Updated Stripe Subscription object
        """
        if not subscription.stripe_subscription_id:
            raise StripeServiceError("Subscription has no Stripe subscription ID")

        if not subscription.cancel_at_period_end:
            raise StripeServiceError("Subscription is not set to cancel at period end")

        try:
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False,
            )

            subscription.cancel_at_period_end = False
            subscription.canceled_at = None
            subscription.save(update_fields=['cancel_at_period_end', 'canceled_at', 'updated_at'])

            logger.info(f"Reactivated subscription {subscription.stripe_subscription_id}")
            return stripe_sub

        except stripe.error.StripeError as e:
            logger.error(f"Failed to reactivate subscription: {e}")
            raise StripeServiceError(
                f"Failed to reactivate subscription: {str(e)}",
                stripe_error=e
            )

    def update_subscription(
        self,
        subscription: Subscription,
        new_plan: SubscriptionPlan,
        new_billing_cycle: str | None = None,
        proration_behavior: str = 'create_prorations'
    ) -> stripe.Subscription:
        """
        Update a subscription to a new plan or billing cycle.

        Args:
            subscription: Django Subscription instance
            new_plan: New SubscriptionPlan to switch to
            new_billing_cycle: Optional new billing cycle ('monthly' or 'yearly')
            proration_behavior: How to handle prorations
                ('create_prorations', 'none', 'always_invoice')

        Returns:
            Updated Stripe Subscription object

        Raises:
            StripeServiceError: If update fails
        """
        if not subscription.stripe_subscription_id:
            raise StripeServiceError("Subscription has no Stripe subscription ID")

        billing_cycle = new_billing_cycle or subscription.billing_cycle
        new_price_id = new_plan.get_stripe_price_id(billing_cycle)

        if not new_price_id:
            raise StripeServiceError(
                f"No Stripe price ID for plan '{new_plan.name}' with {billing_cycle} billing"
            )

        try:
            # Get current subscription to find the item ID
            current_stripe_sub = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            )

            if not current_stripe_sub.get('items', {}).get('data'):
                raise StripeServiceError("Could not find subscription items")

            subscription_item_id = current_stripe_sub['items']['data'][0]['id']

            # Update the subscription with idempotency key
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    'id': subscription_item_id,
                    'price': new_price_id,
                }],
                proration_behavior=proration_behavior,
                metadata={
                    'plan_id': str(new_plan.id),
                    'plan_slug': new_plan.slug,
                    'billing_cycle': billing_cycle,
                },
                idempotency_key=self._generate_idempotency_key(
                    f"update_sub_{subscription.id}_{new_plan.id}"
                )
            )

            # Update local subscription
            subscription.plan = new_plan
            subscription.billing_cycle = billing_cycle
            if subscription.cancel_at_period_end:
                subscription.cancel_at_period_end = False
                subscription.canceled_at = None
            subscription.save()

            logger.info(
                f"Updated subscription {subscription.stripe_subscription_id} "
                f"to plan {new_plan.slug} ({billing_cycle})"
            )
            return stripe_sub

        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {e}")
            raise StripeServiceError(
                f"Failed to update subscription: {str(e)}",
                stripe_error=e
            )

    def get_subscription_status(self, subscription: Subscription) -> dict:
        """
        Get the current status of a subscription from Stripe.

        Args:
            subscription: Django Subscription instance

        Returns:
            Dictionary with subscription status information
        """
        if not subscription.stripe_subscription_id:
            return {
                'status': subscription.status,
                'synced': False,
                'message': 'No Stripe subscription ID'
            }

        try:
            stripe_sub = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id,
                expand=['latest_invoice', 'default_payment_method']
            )

            return {
                'status': stripe_sub.status,
                'synced': True,
                'current_period_start': datetime.fromtimestamp(
                    stripe_sub.current_period_start, tz=timezone.utc
                ),
                'current_period_end': datetime.fromtimestamp(
                    stripe_sub.current_period_end, tz=timezone.utc
                ),
                'cancel_at_period_end': stripe_sub.cancel_at_period_end,
                'canceled_at': (
                    datetime.fromtimestamp(stripe_sub.canceled_at, tz=timezone.utc)
                    if stripe_sub.canceled_at else None
                ),
                'latest_invoice': stripe_sub.get('latest_invoice'),
                'default_payment_method': stripe_sub.get('default_payment_method'),
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription status: {e}")
            return {
                'status': subscription.status,
                'synced': False,
                'error': str(e)
            }

    # ==================== Webhook Handling ====================

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> stripe.Event:
        """
        Verify a Stripe webhook signature and return the event.

        Args:
            payload: Raw request body bytes
            signature: Stripe-Signature header value

        Returns:
            Verified Stripe Event object

        Raises:
            StripeServiceError: If verification fails
        """
        if not self.webhook_secret:
            raise StripeServiceError("Webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            return event

        except stripe.error.SignatureVerificationError as e:
            logger.warning(f"Invalid webhook signature: {e}")
            raise StripeServiceError("Invalid webhook signature", stripe_error=e)
        except ValueError as e:
            logger.warning(f"Invalid webhook payload: {e}")
            raise StripeServiceError("Invalid webhook payload")

    def handle_webhook_event(self, event: stripe.Event) -> dict:
        """
        Handle a verified Stripe webhook event.

        Args:
            event: Verified Stripe Event object

        Returns:
            Dictionary with handling result
        """
        event_type = event.type
        event_data = event.data.object

        handlers = {
            'checkout.session.completed': self._handle_checkout_completed,
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.paid': self._handle_invoice_paid,
            'invoice.payment_failed': self._handle_invoice_payment_failed,
            'customer.created': self._handle_customer_created,
            'customer.updated': self._handle_customer_updated,
        }

        handler = handlers.get(event_type)
        if handler:
            try:
                result = handler(event_data)
                logger.info(f"Handled webhook event: {event_type}")
                return {'handled': True, 'event_type': event_type, 'result': result}
            except Exception as e:
                logger.error(f"Error handling webhook {event_type}: {e}")
                return {'handled': False, 'event_type': event_type, 'error': str(e)}
        else:
            logger.debug(f"Unhandled webhook event type: {event_type}")
            return {'handled': False, 'event_type': event_type, 'message': 'No handler'}

    def _handle_checkout_completed(self, session: dict) -> dict:
        """Handle successful checkout session completion."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_id = session.get('metadata', {}).get('user_id')
        if not user_id:
            return {'status': 'skipped', 'reason': 'No user_id in metadata'}

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return {'status': 'error', 'reason': f'User {user_id} not found'}

        stripe_subscription_id = session.get('subscription')
        if not stripe_subscription_id:
            return {'status': 'skipped', 'reason': 'No subscription in session'}

        # Get or create subscription
        plan_id = session.get('metadata', {}).get('plan_id')
        billing_cycle = session.get('metadata', {}).get('billing_cycle', 'monthly')

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return {'status': 'error', 'reason': f'Plan {plan_id} not found'}

        # Retrieve full subscription from Stripe
        stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)

        subscription, created = Subscription.objects.update_or_create(
            user=user,
            defaults={
                'plan': plan,
                'stripe_subscription_id': stripe_subscription_id,
                'stripe_customer_id': session.get('customer'),
                'status': stripe_sub.status,
                'billing_cycle': billing_cycle,
                'current_period_start': datetime.fromtimestamp(
                    stripe_sub.current_period_start, tz=timezone.utc
                ),
                'current_period_end': datetime.fromtimestamp(
                    stripe_sub.current_period_end, tz=timezone.utc
                ),
            }
        )

        return {
            'status': 'success',
            'subscription_id': str(subscription.id),
            'created': created
        }

    def _handle_subscription_created(self, stripe_sub: dict) -> dict:
        """Handle subscription created event."""
        return self._sync_subscription(stripe_sub)

    def _handle_subscription_updated(self, stripe_sub: dict) -> dict:
        """Handle subscription updated event."""
        return self._sync_subscription(stripe_sub)

    def _handle_subscription_deleted(self, stripe_sub: dict) -> dict:
        """Handle subscription deleted/canceled event."""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub['id']
            )
            subscription.status = Subscription.Status.CANCELED
            subscription.canceled_at = timezone.now()
            subscription.save(update_fields=['status', 'canceled_at', 'updated_at'])

            return {'status': 'success', 'subscription_id': str(subscription.id)}
        except Subscription.DoesNotExist:
            return {'status': 'skipped', 'reason': 'Subscription not found'}

    def _sync_subscription(self, stripe_sub: dict) -> dict:
        """Synchronize a Stripe subscription with the local database."""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub['id']
            )
        except Subscription.DoesNotExist:
            return {'status': 'skipped', 'reason': 'Subscription not found locally'}

        subscription.status = stripe_sub['status']
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_sub['current_period_start'], tz=timezone.utc
        )
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_sub['current_period_end'], tz=timezone.utc
        )
        subscription.cancel_at_period_end = stripe_sub.get('cancel_at_period_end', False)

        if stripe_sub.get('canceled_at'):
            subscription.canceled_at = datetime.fromtimestamp(
                stripe_sub['canceled_at'], tz=timezone.utc
            )

        subscription.save()

        return {'status': 'success', 'subscription_id': str(subscription.id)}

    def _handle_invoice_paid(self, invoice: dict) -> dict:
        """Handle successful invoice payment."""
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return {'status': 'skipped', 'reason': 'No subscription on invoice'}

        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=subscription_id
            )
        except Subscription.DoesNotExist:
            return {'status': 'skipped', 'reason': 'Subscription not found'}

        # Record payment history
        payment_intent_id = invoice.get('payment_intent')

        # Avoid duplicates
        if payment_intent_id and PaymentHistory.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).exists():
            return {'status': 'skipped', 'reason': 'Payment already recorded'}

        amount = Decimal(invoice.get('amount_paid', 0)) / 100  # Convert from cents

        payment = PaymentHistory.objects.create(
            user=subscription.user,
            subscription=subscription,
            stripe_payment_intent_id=payment_intent_id,
            stripe_invoice_id=invoice.get('id'),
            amount=amount,
            currency=invoice.get('currency', 'usd').upper(),
            status=PaymentHistory.Status.SUCCEEDED,
            description=f"Subscription payment for {subscription.plan.name}",
            invoice_pdf_url=invoice.get('invoice_pdf'),
            hosted_invoice_url=invoice.get('hosted_invoice_url'),
        )

        # Update subscription status if needed
        if subscription.status in [Subscription.Status.PAST_DUE, Subscription.Status.UNPAID]:
            subscription.status = Subscription.Status.ACTIVE
            subscription.save(update_fields=['status', 'updated_at'])

        return {
            'status': 'success',
            'payment_id': str(payment.id),
            'amount': str(amount)
        }

    def _handle_invoice_payment_failed(self, invoice: dict) -> dict:
        """Handle failed invoice payment."""
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return {'status': 'skipped', 'reason': 'No subscription on invoice'}

        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=subscription_id
            )
        except Subscription.DoesNotExist:
            return {'status': 'skipped', 'reason': 'Subscription not found'}

        # Record failed payment
        payment_intent_id = invoice.get('payment_intent')
        amount = Decimal(invoice.get('amount_due', 0)) / 100

        PaymentHistory.objects.create(
            user=subscription.user,
            subscription=subscription,
            stripe_payment_intent_id=payment_intent_id,
            stripe_invoice_id=invoice.get('id'),
            amount=amount,
            currency=invoice.get('currency', 'usd').upper(),
            status=PaymentHistory.Status.FAILED,
            description=f"Failed payment for {subscription.plan.name}",
        )

        # Update subscription status
        subscription.status = Subscription.Status.PAST_DUE
        subscription.save(update_fields=['status', 'updated_at'])

        return {'status': 'success', 'action': 'marked_past_due'}

    def _handle_customer_created(self, customer: dict) -> dict:
        """Handle customer created event."""
        return {'status': 'acknowledged', 'customer_id': customer.get('id')}

    def _handle_customer_updated(self, customer: dict) -> dict:
        """Handle customer updated event."""
        return {'status': 'acknowledged', 'customer_id': customer.get('id')}

    # ==================== Utility Methods ====================

    def get_invoices(
        self,
        customer_id: str,
        limit: int = 10
    ) -> list[stripe.Invoice]:
        """
        Get invoices for a customer.

        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices to return

        Returns:
            List of Stripe Invoice objects
        """
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            return list(invoices.data)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get invoices: {e}")
            return []

    def get_upcoming_invoice(self, subscription: Subscription) -> stripe.Invoice | None:
        """
        Get the upcoming invoice for a subscription.

        Args:
            subscription: Django Subscription instance

        Returns:
            Stripe Invoice object or None
        """
        if not subscription.stripe_customer_id:
            return None

        try:
            invoice = stripe.Invoice.upcoming(
                customer=subscription.stripe_customer_id
            )
            return invoice
        except stripe.error.InvalidRequestError:
            # No upcoming invoice (e.g., subscription canceled)
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get upcoming invoice: {e}")
            return None

    def sync_subscription_from_stripe(self, subscription: Subscription) -> bool:
        """
        Sync local subscription data from Stripe.

        Args:
            subscription: Django Subscription instance

        Returns:
            True if sync was successful
        """
        if not subscription.stripe_subscription_id:
            return False

        try:
            stripe_sub = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            )

            subscription.status = stripe_sub.status
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start, tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=timezone.utc
            )
            subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end

            if stripe_sub.canceled_at:
                subscription.canceled_at = datetime.fromtimestamp(
                    stripe_sub.canceled_at, tz=timezone.utc
                )

            subscription.save()

            logger.info(f"Synced subscription {subscription.id} from Stripe")
            return True

        except stripe.error.StripeError as e:
            logger.error(f"Failed to sync subscription from Stripe: {e}")
            return False


# Singleton instance for convenience
stripe_service = StripeService()
