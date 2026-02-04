"""
Subscriptions API Views.

DRF ViewSets and APIViews for subscription management.
"""
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.db import transaction

from .models import SubscriptionPlan, Subscription, SubscriptionEvent, Invoice
from .serializers import (
    SubscriptionPlanSerializer,
    SubscriptionPlanListSerializer,
    SubscriptionSerializer,
    SubscriptionSummarySerializer,
    SubscriptionEventSerializer,
    InvoiceSerializer,
    InvoiceListSerializer,
    PaymentHistorySerializer,
    CheckoutRequestSerializer,
    CheckoutSessionResponseSerializer,
    CancelSubscriptionSerializer,
    UpdateSubscriptionSerializer,
    PortalRequestSerializer,
    PortalResponseSerializer,
    SubscriptionFeaturesSerializer,
    PaymentMethodSerializer,
)
from .stripe_service import stripe_service

logger = logging.getLogger(__name__)


# =============================================================================
# Subscription Plan ViewSet
# =============================================================================

class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for subscription plan information.

    Provides list-only access to active subscription plans.

    Endpoints:
    - GET /api/v1/subscriptions/plans/ - List all active plans
    - GET /api/v1/subscriptions/plans/{uuid}/ - Get plan details
    """
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        """Return active subscription plans ordered by display_order."""
        return SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SubscriptionPlanListSerializer
        return SubscriptionPlanSerializer


# =============================================================================
# Subscription ViewSet (Current User)
# =============================================================================

class SubscriptionViewSet(viewsets.ViewSet):
    """
    ViewSet for current user's subscription management.

    Provides read-only access to the authenticated user's subscription.

    Endpoints:
    - GET /api/v1/subscriptions/current/ - Get current subscription
    - GET /api/v1/subscriptions/current/features/ - Get available features
    - GET /api/v1/subscriptions/current/events/ - Get event history
    - POST /api/v1/subscriptions/current/cancel/ - Cancel subscription
    - POST /api/v1/subscriptions/current/reactivate/ - Reactivate subscription
    - POST /api/v1/subscriptions/current/change-plan/ - Change subscription plan
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_subscription(self):
        """Return the current user's subscription or None."""
        try:
            return self.request.user.subscription
        except Subscription.DoesNotExist:
            return None

    def list(self, request):
        """
        Get current user's subscription details.

        Returns:
            Subscription details including plan information.
        """
        subscription = self.get_subscription()
        if not subscription:
            return Response(
                {'detail': 'No subscription found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Get current user's subscription (alias for list).

        This endpoint is for /current/ route.
        """
        return self.list(request)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get subscription summary for profile display.

        Returns:
            Simplified subscription information.
        """
        subscription = self.get_subscription()
        if not subscription:
            return Response(
                {'detail': 'No subscription found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = SubscriptionSummarySerializer(subscription)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def features(self, request):
        """
        Get available features for current subscription.

        Returns:
            Feature limits and flags for the subscription plan.
        """
        subscription = self.get_subscription()
        if not subscription:
            # Return free tier features
            try:
                free_plan = SubscriptionPlan.objects.get(tier='free')
                data = {
                    'tier': 'free',
                    'max_bank_accounts': free_plan.max_bank_accounts,
                    'max_budgets': free_plan.max_budgets,
                    'max_transactions_per_month': free_plan.max_transactions_per_month,
                    'max_categories': free_plan.max_categories,
                    'max_family_members': free_plan.max_family_members,
                    'ai_categorization': free_plan.ai_categorization,
                    'ai_insights': free_plan.ai_insights,
                    'export_csv': free_plan.export_csv,
                    'export_pdf': free_plan.export_pdf,
                    'bank_sync': free_plan.bank_sync,
                    'recurring_transactions': free_plan.recurring_transactions,
                    'custom_categories': free_plan.custom_categories,
                    'budget_alerts': free_plan.budget_alerts,
                    'multi_currency': free_plan.multi_currency,
                    'priority_support': free_plan.priority_support,
                    'api_access': free_plan.api_access,
                }
            except SubscriptionPlan.DoesNotExist:
                data = {'tier': 'free'}
            return Response(data)

        plan = subscription.plan
        data = {
            'tier': plan.tier,
            'max_bank_accounts': plan.max_bank_accounts,
            'max_budgets': plan.max_budgets,
            'max_transactions_per_month': plan.max_transactions_per_month,
            'max_categories': plan.max_categories,
            'max_family_members': plan.max_family_members,
            'ai_categorization': plan.ai_categorization,
            'ai_insights': plan.ai_insights,
            'export_csv': plan.export_csv,
            'export_pdf': plan.export_pdf,
            'bank_sync': plan.bank_sync,
            'recurring_transactions': plan.recurring_transactions,
            'custom_categories': plan.custom_categories,
            'budget_alerts': plan.budget_alerts,
            'multi_currency': plan.multi_currency,
            'priority_support': plan.priority_support,
            'api_access': plan.api_access,
        }
        serializer = SubscriptionFeaturesSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def events(self, request):
        """
        Get subscription event history.

        Returns:
            List of subscription events (last 20).
        """
        subscription = self.get_subscription()
        if not subscription:
            return Response([])

        events = subscription.events.all()[:20]
        serializer = SubscriptionEventSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """
        Cancel the current subscription.

        Request body:
        - cancel_at_period_end: bool (default: True)
        - reason: string (optional)

        Returns:
            Success message or error.
        """
        subscription = self.get_subscription()
        if not subscription or not subscription.stripe_subscription_id:
            return Response(
                {'detail': 'No active subscription found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CancelSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cancel_at_period_end = serializer.validated_data.get('cancel_at_period_end', True)
        reason = serializer.validated_data.get('reason', '')

        success, error = stripe_service.cancel_subscription(
            subscription.stripe_subscription_id,
            at_period_end=cancel_at_period_end
        )

        if not success:
            logger.error(f"Failed to cancel subscription: {error}")
            return Response(
                {'detail': f'Failed to cancel subscription: {error}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update local subscription
        subscription.cancel_at_period_end = cancel_at_period_end
        if not cancel_at_period_end:
            subscription.status = 'canceled'
        subscription.save()

        # Log event
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='canceled',
            description=f'Subscription canceled (at_period_end={cancel_at_period_end}). Reason: {reason}',
            metadata={'reason': reason, 'at_period_end': cancel_at_period_end}
        )

        logger.info(f"Subscription canceled for user {request.user.email}")
        return Response({'detail': 'Subscription canceled successfully.'})

    @action(detail=False, methods=['post'])
    def reactivate(self, request):
        """
        Reactivate a canceled subscription.

        Only works if subscription is set to cancel at period end.

        Returns:
            Success message or error.
        """
        subscription = self.get_subscription()
        if not subscription or not subscription.stripe_subscription_id:
            return Response(
                {'detail': 'No subscription found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not subscription.cancel_at_period_end:
            return Response(
                {'detail': 'Subscription is not scheduled for cancellation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, error = stripe_service.reactivate_subscription(
            subscription.stripe_subscription_id
        )

        if not success:
            logger.error(f"Failed to reactivate subscription: {error}")
            return Response(
                {'detail': f'Failed to reactivate subscription: {error}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update local subscription
        subscription.cancel_at_period_end = False
        subscription.save()

        # Log event
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type='reactivated',
            description='Subscription reactivated',
        )

        logger.info(f"Subscription reactivated for user {request.user.email}")
        return Response({'detail': 'Subscription reactivated successfully.'})

    @action(detail=False, methods=['post'], url_path='change-plan')
    def change_plan(self, request):
        """
        Change subscription plan (upgrade/downgrade).

        Request body:
        - new_plan_id: UUID
        - billing_interval: string (optional)

        Returns:
            Updated subscription details.
        """
        subscription = self.get_subscription()
        if not subscription or not subscription.stripe_subscription_id:
            return Response(
                {'detail': 'No active subscription found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UpdateSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_plan = serializer.validated_data['new_plan_id']
        billing_interval = serializer.validated_data.get(
            'billing_interval',
            subscription.billing_interval
        )

        # Get the appropriate Stripe price ID
        if billing_interval == 'year':
            new_price_id = new_plan.stripe_price_id_yearly
        else:
            new_price_id = new_plan.stripe_price_id_monthly

        if not new_price_id:
            return Response(
                {'detail': 'Plan pricing not configured.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, error = stripe_service.update_subscription(
            subscription.stripe_subscription_id,
            new_price_id
        )

        if not success:
            logger.error(f"Failed to update subscription: {error}")
            return Response(
                {'detail': f'Failed to update subscription: {error}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine if upgrade or downgrade
        tier_order = ['free', 'premium', 'pro', 'business']
        old_index = tier_order.index(subscription.plan.tier) if subscription.plan.tier in tier_order else 0
        new_index = tier_order.index(new_plan.tier) if new_plan.tier in tier_order else 0
        event_type = 'upgraded' if new_index > old_index else 'downgraded'

        # Update local subscription
        old_plan_name = subscription.plan.name
        subscription.plan = new_plan
        subscription.billing_interval = billing_interval
        subscription.save()

        # Update user's subscription tier
        request.user.subscription_tier = new_plan.tier
        request.user.save(update_fields=['subscription_tier'])

        # Log event
        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type=event_type,
            description=f'Plan changed from {old_plan_name} to {new_plan.name}',
            metadata={
                'old_plan': old_plan_name,
                'new_plan': new_plan.name,
                'billing_interval': billing_interval,
            }
        )

        logger.info(f"Subscription {event_type} for user {request.user.email}: {old_plan_name} -> {new_plan.name}")
        return Response({
            'detail': f'Plan changed to {new_plan.name} successfully.',
            'subscription': SubscriptionSerializer(subscription).data
        })


# =============================================================================
# Checkout View
# =============================================================================

class CreateCheckoutView(APIView):
    """
    API endpoint for creating Stripe Checkout sessions.

    POST /api/v1/subscriptions/checkout/
    Creates a new checkout session for subscription purchase.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Create a Stripe Checkout session.

        Request body:
        - plan_id: UUID of the subscription plan
        - billing_interval: 'month' or 'year'
        - success_url: URL to redirect after success (optional)
        - cancel_url: URL to redirect if canceled (optional)

        Returns:
            session_id: Stripe session ID
            url: Checkout URL to redirect user
        """
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan_id']
        billing_interval = serializer.validated_data['billing_interval']
        success_url = serializer.validated_data.get('success_url')
        cancel_url = serializer.validated_data.get('cancel_url')

        # Get the appropriate Stripe price ID
        if billing_interval == 'year':
            price_id = plan.stripe_price_id_yearly
        else:
            price_id = plan.stripe_price_id_monthly

        if not price_id:
            return Response(
                {'detail': 'Plan pricing not configured for this billing interval.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already has an active subscription
        try:
            existing_subscription = request.user.subscription
            if existing_subscription.is_active:
                return Response(
                    {'detail': 'You already have an active subscription. Please upgrade instead.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Subscription.DoesNotExist:
            pass

        # Create checkout session
        result = stripe_service.create_checkout_session(
            user=request.user,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'plan_id': str(plan.id),
                'billing_interval': billing_interval,
            }
        )

        if not result:
            logger.error(f"Failed to create checkout session for user {request.user.email}")
            return Response(
                {'detail': 'Failed to create checkout session.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"Checkout session created for user {request.user.email}: {result.get('session_id')}")
        response_serializer = CheckoutSessionResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


# =============================================================================
# Portal View
# =============================================================================

class CreatePortalView(APIView):
    """
    API endpoint for Stripe Billing Portal.

    POST /api/v1/subscriptions/portal/
    Creates a billing portal session for subscription management.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Create a Stripe Billing Portal session.

        Request body:
        - return_url: URL to return to after portal (optional)

        Returns:
            url: Portal URL to redirect user
        """
        serializer = PortalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return_url = serializer.validated_data.get('return_url')

        # Get customer ID
        customer_id = None
        try:
            customer_id = request.user.subscription.stripe_customer_id
        except Subscription.DoesNotExist:
            pass

        if not customer_id and hasattr(request.user, 'stripe_customer_id'):
            customer_id = request.user.stripe_customer_id

        if not customer_id:
            return Response(
                {'detail': 'No billing information found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        portal_url = stripe_service.create_billing_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )

        if not portal_url:
            logger.error(f"Failed to create billing portal for user {request.user.email}")
            return Response(
                {'detail': 'Failed to create billing portal session.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"Billing portal session created for user {request.user.email}")
        response_serializer = PortalResponseSerializer({'url': portal_url})
        return Response(response_serializer.data)


# =============================================================================
# Payment History ViewSet
# =============================================================================

class PaymentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payment/invoice history.

    Provides read-only access to payment history for the authenticated user.

    Endpoints:
    - GET /api/v1/subscriptions/payments/ - List payment history
    - GET /api/v1/subscriptions/payments/{uuid}/ - Get payment details
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Return invoices for the current user's subscription."""
        try:
            subscription = self.request.user.subscription
            return Invoice.objects.filter(subscription=subscription).order_by('-created_at')
        except Subscription.DoesNotExist:
            return Invoice.objects.none()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return InvoiceListSerializer
        return PaymentHistorySerializer


# =============================================================================
# Legacy/Additional Views
# =============================================================================

class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for invoice history (legacy endpoint).

    Endpoints:
    - GET /api/v1/subscriptions/invoices/ - List invoices
    - GET /api/v1/subscriptions/invoices/{uuid}/ - Get invoice details
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Return invoices for the current user's subscription."""
        try:
            return Invoice.objects.filter(subscription=self.request.user.subscription)
        except Subscription.DoesNotExist:
            return Invoice.objects.none()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceSerializer


class PaymentMethodsAPIView(APIView):
    """
    API endpoint for payment methods.

    GET /api/v1/subscriptions/payment-methods/
    Returns saved payment methods for the user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get user's payment methods.

        Returns:
            List of payment methods with card details.
        """
        customer_id = None
        try:
            customer_id = request.user.subscription.stripe_customer_id
        except Subscription.DoesNotExist:
            pass

        if not customer_id and hasattr(request.user, 'stripe_customer_id'):
            customer_id = request.user.stripe_customer_id

        if not customer_id:
            return Response([])

        payment_methods = stripe_service.get_payment_methods(customer_id)

        # Get default payment method
        customer = stripe_service.get_customer(customer_id)
        default_pm_id = None
        if customer and customer.get('invoice_settings'):
            default_pm_id = customer['invoice_settings'].get('default_payment_method')

        result = []
        for pm in payment_methods:
            card = pm.get('card', {})
            result.append({
                'id': pm.id,
                'brand': card.get('brand', '').title(),
                'last4': card.get('last4', '****'),
                'exp_month': card.get('exp_month'),
                'exp_year': card.get('exp_year'),
                'is_default': pm.id == default_pm_id,
            })

        serializer = PaymentMethodSerializer(result, many=True)
        return Response(serializer.data)


# Backward compatibility aliases
CheckoutSessionAPIView = CreateCheckoutView
BillingPortalAPIView = CreatePortalView
