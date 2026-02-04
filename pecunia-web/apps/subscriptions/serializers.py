"""
Subscriptions Serializers.

DRF serializers for subscription management API.
"""
from rest_framework import serializers
from .models import SubscriptionPlan, Subscription, SubscriptionEvent, Invoice


# =============================================================================
# Subscription Plan Serializers
# =============================================================================

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for subscription plan details.

    Returns plan information including features and pricing.
    """
    yearly_savings = serializers.IntegerField(read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'tier', 'name', 'description',
            'price_monthly', 'price_yearly', 'currency',
            'yearly_savings',
            # Feature limits
            'max_bank_accounts', 'max_budgets',
            'max_transactions_per_month', 'max_categories',
            'max_family_members',
            # Feature flags
            'ai_categorization', 'ai_insights',
            'export_csv', 'export_pdf', 'bank_sync',
            'recurring_transactions', 'custom_categories',
            'budget_alerts', 'multi_currency',
            'priority_support', 'api_access',
            # Display
            'is_featured', 'display_order',
        ]
        read_only_fields = fields


class SubscriptionPlanListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for plan listings.

    Used for pricing page display.
    """
    yearly_savings = serializers.IntegerField(read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'tier', 'name', 'description',
            'price_monthly', 'price_yearly', 'currency',
            'yearly_savings', 'is_featured',
        ]
        read_only_fields = fields


# =============================================================================
# Subscription Serializers
# =============================================================================

class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for user subscription details.

    Returns full subscription information with plan details.
    """
    plan = SubscriptionPlanSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_on_trial = serializers.BooleanField(read_only=True)
    days_until_renewal = serializers.IntegerField(read_only=True)
    tier = serializers.CharField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'billing_interval',
            'current_period_start', 'current_period_end',
            'trial_start', 'trial_end',
            'cancel_at_period_end', 'canceled_at',
            'is_active', 'is_on_trial', 'days_until_renewal', 'tier',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class SubscriptionSummarySerializer(serializers.ModelSerializer):
    """
    Simplified serializer for subscription summary.

    Used for user profile display.
    """
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    tier = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_until_renewal = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan_name', 'tier', 'status',
            'billing_interval', 'current_period_end',
            'cancel_at_period_end', 'is_active', 'days_until_renewal',
        ]
        read_only_fields = fields


class SubscriptionEventSerializer(serializers.ModelSerializer):
    """
    Serializer for subscription event logs.

    Used for audit trail display.
    """

    class Meta:
        model = SubscriptionEvent
        fields = [
            'id', 'event_type', 'description',
            'metadata', 'created_at',
        ]
        read_only_fields = fields


# =============================================================================
# Payment History Serializers
# =============================================================================

class PaymentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for payment history entries.

    Returns invoice/payment information for billing history.
    """
    plan_name = serializers.CharField(source='subscription.plan.name', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'stripe_invoice_id',
            'amount_due', 'amount_paid', 'currency', 'status',
            'invoice_pdf_url', 'hosted_invoice_url',
            'period_start', 'period_end', 'due_date', 'paid_at',
            'plan_name', 'created_at',
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for invoice details.

    Returns invoice information for billing history.
    """

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'stripe_invoice_id',
            'amount_due', 'amount_paid', 'currency', 'status',
            'invoice_pdf_url', 'hosted_invoice_url',
            'period_start', 'period_end', 'due_date', 'paid_at',
            'created_at',
        ]
        read_only_fields = fields


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for invoice listings.

    Used for billing history display.
    """

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'amount_due',
            'currency', 'status', 'paid_at', 'created_at',
        ]
        read_only_fields = fields


# =============================================================================
# Checkout Request Serializers
# =============================================================================

class CheckoutRequestSerializer(serializers.Serializer):
    """
    Serializer for creating a checkout session.

    Validates input for Stripe checkout.
    """
    plan_id = serializers.UUIDField(
        required=True,
        help_text="UUID of the subscription plan to purchase."
    )
    billing_interval = serializers.ChoiceField(
        choices=['month', 'year'],
        default='month',
        help_text="Billing interval: 'month' or 'year'."
    )
    success_url = serializers.URLField(
        required=False,
        help_text="URL to redirect after successful checkout."
    )
    cancel_url = serializers.URLField(
        required=False,
        help_text="URL to redirect if checkout is canceled."
    )

    def validate_plan_id(self, value):
        """Validate that the plan exists and is active."""
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return plan
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan.")


# Alias for backward compatibility
CheckoutSessionCreateSerializer = CheckoutRequestSerializer


class CheckoutSessionResponseSerializer(serializers.Serializer):
    """
    Serializer for checkout session response.

    Returns checkout session details.
    """
    session_id = serializers.CharField(read_only=True)
    url = serializers.URLField(read_only=True)


# =============================================================================
# Portal Serializers
# =============================================================================

class PortalRequestSerializer(serializers.Serializer):
    """
    Serializer for billing portal request.

    Validates input for Stripe Customer Portal.
    """
    return_url = serializers.URLField(
        required=False,
        help_text="URL to return to after portal session."
    )


# Alias for backward compatibility
BillingPortalSerializer = PortalRequestSerializer


class PortalResponseSerializer(serializers.Serializer):
    """
    Serializer for billing portal response.

    Returns portal URL.
    """
    url = serializers.URLField(read_only=True)


# Alias for backward compatibility
BillingPortalResponseSerializer = PortalResponseSerializer


# =============================================================================
# Subscription Management Serializers
# =============================================================================

class CancelSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for subscription cancellation.

    Validates cancellation options.
    """
    cancel_at_period_end = serializers.BooleanField(
        default=True,
        help_text="If True, cancel at end of current period. If False, cancel immediately."
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional reason for cancellation."
    )


class UpdateSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for subscription plan change.

    Validates plan upgrade/downgrade requests.
    """
    new_plan_id = serializers.UUIDField(
        required=True,
        help_text="UUID of the new subscription plan."
    )
    billing_interval = serializers.ChoiceField(
        choices=['month', 'year'],
        required=False,
        help_text="New billing interval (optional)."
    )

    def validate_new_plan_id(self, value):
        """Validate that the new plan exists and is active."""
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return plan
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan.")


# =============================================================================
# Feature Serializers
# =============================================================================

class SubscriptionFeaturesSerializer(serializers.Serializer):
    """
    Serializer for subscription feature checks.

    Returns feature availability for current subscription.
    """
    tier = serializers.CharField(read_only=True)

    # Limits
    max_bank_accounts = serializers.IntegerField(read_only=True)
    max_budgets = serializers.IntegerField(read_only=True)
    max_transactions_per_month = serializers.IntegerField(read_only=True)
    max_categories = serializers.IntegerField(read_only=True)
    max_family_members = serializers.IntegerField(read_only=True)

    # Features
    ai_categorization = serializers.BooleanField(read_only=True)
    ai_insights = serializers.BooleanField(read_only=True)
    export_csv = serializers.BooleanField(read_only=True)
    export_pdf = serializers.BooleanField(read_only=True)
    bank_sync = serializers.BooleanField(read_only=True)
    recurring_transactions = serializers.BooleanField(read_only=True)
    custom_categories = serializers.BooleanField(read_only=True)
    budget_alerts = serializers.BooleanField(read_only=True)
    multi_currency = serializers.BooleanField(read_only=True)
    priority_support = serializers.BooleanField(read_only=True)
    api_access = serializers.BooleanField(read_only=True)


# =============================================================================
# Payment Method Serializers
# =============================================================================

class PaymentMethodSerializer(serializers.Serializer):
    """
    Serializer for payment method display.

    Returns card details (from Stripe).
    """
    id = serializers.CharField(read_only=True)
    brand = serializers.CharField(read_only=True)
    last4 = serializers.CharField(read_only=True)
    exp_month = serializers.IntegerField(read_only=True)
    exp_year = serializers.IntegerField(read_only=True)
    is_default = serializers.BooleanField(read_only=True)
