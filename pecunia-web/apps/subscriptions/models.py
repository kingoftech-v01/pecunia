"""
Subscriptions Models.

Subscription plans, user subscriptions, and payment history.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator


class SubscriptionPlan(models.Model):
    """
    Represents a subscription plan with Stripe price IDs.
    Contains both monthly and yearly pricing options.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name of the plan (e.g., 'Professional', 'Enterprise')"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly identifier for the plan"
    )

    # Plan tier
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('pro', 'Professional'),
        ('business', 'Business'),
    ]
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default='free',
        help_text="Subscription tier level"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Description of the plan"
    )
    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Three-letter ISO currency code"
    )

    # Stripe Price IDs
    stripe_price_id_monthly = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Price ID for monthly billing (e.g., 'price_xxx')"
    )
    stripe_price_id_yearly = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Price ID for yearly billing (e.g., 'price_xxx')"
    )

    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monthly price in the default currency"
    )
    price_yearly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Yearly price in the default currency"
    )

    # Plan details stored as JSON
    features = models.JSONField(
        default=list,
        blank=True,
        help_text="List of features included in this plan (e.g., ['AI categorization', 'Bank sync', 'Priority support'])"
    )
    limits = models.JSONField(
        default=dict,
        blank=True,
        help_text="Usage limits for this plan (e.g., {'accounts': 5, 'transactions_per_month': 1000, 'budgets': 10})"
    )

    # Feature limits
    max_bank_accounts = models.PositiveIntegerField(default=1)
    max_budgets = models.PositiveIntegerField(default=3)
    max_transactions_per_month = models.PositiveIntegerField(default=100)
    max_categories = models.PositiveIntegerField(default=10)
    max_family_members = models.PositiveIntegerField(default=0)

    # Feature flags
    ai_categorization = models.BooleanField(default=False)
    ai_insights = models.BooleanField(default=False)
    export_csv = models.BooleanField(default=True)
    export_pdf = models.BooleanField(default=False)
    bank_sync = models.BooleanField(default=False)
    recurring_transactions = models.BooleanField(default=False)
    custom_categories = models.BooleanField(default=False)
    budget_alerts = models.BooleanField(default=False)
    multi_currency = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)

    # Display
    is_featured = models.BooleanField(default=False)

    # Plan management
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this plan is available for new subscriptions"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which plans are displayed (lower = first)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'price_monthly']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"

    def get_stripe_price_id(self, billing_cycle: str) -> str | None:
        """Get the appropriate Stripe price ID based on billing cycle."""
        if billing_cycle == 'yearly':
            return self.stripe_price_id_yearly
        return self.stripe_price_id_monthly

    def get_price(self, billing_cycle: str) -> Decimal:
        """Get the price based on billing cycle."""
        if billing_cycle == 'yearly':
            return self.price_yearly
        return self.price_monthly

    @property
    def yearly_savings_percentage(self) -> int:
        """Calculate the percentage saved by choosing yearly billing."""
        if self.price_monthly <= 0:
            return 0
        yearly_from_monthly = self.price_monthly * 12
        if yearly_from_monthly <= 0:
            return 0
        savings = ((yearly_from_monthly - self.price_yearly) / yearly_from_monthly) * 100
        return int(savings)

    @property
    def yearly_savings(self) -> int:
        """Alias for yearly_savings_percentage for serializer compatibility."""
        return self.yearly_savings_percentage

    def get_limit(self, key: str, default=None):
        """Get a specific limit value from the limits JSON."""
        return self.limits.get(key, default)

    def has_feature(self, feature: str) -> bool:
        """Check if plan includes a specific feature."""
        return feature in self.features


class Subscription(models.Model):
    """
    Represents a user's subscription to a plan.
    Linked to Stripe subscription for billing management.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELED = 'canceled', 'Canceled'
        TRIALING = 'trialing', 'Trialing'
        INCOMPLETE = 'incomplete', 'Incomplete'
        INCOMPLETE_EXPIRED = 'incomplete_expired', 'Incomplete Expired'
        UNPAID = 'unpaid', 'Unpaid'
        PAUSED = 'paused', 'Paused'

    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )

    # Stripe identifiers
    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text="Stripe Subscription ID (e.g., 'sub_xxx')"
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Customer ID (e.g., 'cus_xxx')"
    )

    # Subscription status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY
    )

    # Billing period
    current_period_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Start of the current billing period"
    )
    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of the current billing period"
    )

    # Cancellation
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text="Whether the subscription will cancel at the end of the period"
    )
    canceled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscription was canceled"
    )

    # Trial
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['stripe_subscription_id']),
            models.Index(fields=['stripe_customer_id']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"

    @property
    def is_active(self) -> bool:
        """Check if the subscription is currently active."""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]

    @property
    def is_trialing(self) -> bool:
        """Check if the subscription is in trial period."""
        return self.status == self.Status.TRIALING

    @property
    def days_until_renewal(self) -> int | None:
        """Calculate days until the next billing date."""
        if not self.current_period_end:
            return None
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)

    @property
    def billing_interval(self) -> str:
        """Alias for billing_cycle for serializer compatibility."""
        return self.billing_cycle

    @billing_interval.setter
    def billing_interval(self, value):
        self.billing_cycle = value

    @property
    def is_on_trial(self) -> bool:
        """Check if subscription is on trial (alias for is_trialing)."""
        return self.is_trialing

    @property
    def tier(self) -> str:
        """Return the plan's tier."""
        return self.plan.tier if self.plan else 'free'

    @property
    def is_canceled(self) -> bool:
        """Check if the subscription is canceled or will cancel."""
        return self.status == self.Status.CANCELED or self.cancel_at_period_end

    def get_feature_limit(self, feature_key: str, default=None):
        """Get a specific limit from the plan's limits."""
        return self.plan.limits.get(feature_key, default)

    def has_feature(self, feature: str) -> bool:
        """Check if the subscription's plan includes a specific feature."""
        return feature in self.plan.features


class PaymentHistory(models.Model):
    """
    Records all payment transactions for audit and user reference.
    """

    class Status(models.TextChoices):
        SUCCEEDED = 'succeeded', 'Succeeded'
        PENDING = 'pending', 'Pending'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        PARTIALLY_REFUNDED = 'partially_refunded', 'Partially Refunded'
        CANCELED = 'canceled', 'Canceled'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_history'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )

    # Stripe identifiers
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text="Stripe PaymentIntent ID (e.g., 'pi_xxx')"
    )
    stripe_invoice_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Invoice ID (e.g., 'in_xxx')"
    )
    stripe_charge_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Charge ID (e.g., 'ch_xxx')"
    )

    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Payment amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Three-letter ISO currency code (e.g., 'USD', 'EUR')"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the payment"
    )

    # Payment method info (for display purposes)
    payment_method_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Type of payment method (e.g., 'card', 'bank_transfer')"
    )
    payment_method_last4 = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text="Last 4 digits of card or account"
    )
    payment_method_brand = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Card brand (e.g., 'visa', 'mastercard')"
    )

    # Refund info
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    refund_reason = models.TextField(blank=True)

    # Invoice URL for download
    invoice_pdf_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to download the invoice PDF"
    )
    hosted_invoice_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL to view the hosted invoice"
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional payment metadata"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment Histories'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency} ({self.status})"

    @property
    def is_successful(self) -> bool:
        """Check if the payment was successful."""
        return self.status == self.Status.SUCCEEDED

    @property
    def net_amount(self) -> Decimal:
        """Calculate the net amount after refunds."""
        return self.amount - self.refunded_amount

    @property
    def formatted_amount(self) -> str:
        """Return a formatted amount with currency symbol."""
        currency_symbols = {
            'USD': '$',
            'EUR': '\u20ac',
            'GBP': '\u00a3',
            'CAD': 'CA$',
            'AUD': 'A$',
        }
        symbol = currency_symbols.get(self.currency.upper(), self.currency)
        return f"{symbol}{self.amount:.2f}"


class SubscriptionEvent(models.Model):
    """
    Logs subscription lifecycle events for audit trail.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_type = models.CharField(max_length=50)
    description = models.TextField(blank=True, default='')
    stripe_event_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Subscription Event'
        verbose_name_plural = 'Subscription Events'

    def __str__(self):
        return f"{self.event_type} - {self.subscription}"


class Invoice(models.Model):
    """
    Invoice records for subscription payments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    stripe_invoice_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    invoice_number = models.CharField(max_length=100, blank=True, default='')
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='EUR')
    status = models.CharField(max_length=20, default='open')
    invoice_pdf_url = models.URLField(max_length=500, blank=True, default='')
    hosted_invoice_url = models.URLField(max_length=500, blank=True, default='')
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.amount_due} {self.currency}"
