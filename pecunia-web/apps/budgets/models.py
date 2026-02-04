"""
Budgets Models.

Budget planning and tracking data models.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Budget(models.Model):
    """
    Budget model for financial planning.

    Represents a budget period with planned spending limits.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    PERIOD_CHOICES = [
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ]
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        default='monthly'
    )

    start_date = models.DateField()
    end_date = models.DateField()

    total_planned_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_spent_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    is_active = models.BooleanField(default=True)
    is_rollover = models.BooleanField(
        default=False,
        help_text='Roll over unused budget to next period'
    )

    # Notification settings
    alert_threshold = models.IntegerField(
        default=80,
        help_text='Alert when spending reaches this percentage'
    )
    notify_on_exceed = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'budget'
        verbose_name_plural = 'budgets'
        ordering = ['-start_date', 'name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.period_type})"

    @property
    def remaining_amount(self):
        """Calculate remaining budget amount."""
        return self.total_planned_amount - self.total_spent_amount

    @property
    def progress_percentage(self):
        """Calculate budget progress as percentage."""
        if self.total_planned_amount == 0:
            return Decimal('0.00')
        return (self.total_spent_amount / self.total_planned_amount) * 100

    @property
    def is_over_budget(self):
        """Check if budget has been exceeded."""
        return self.total_spent_amount > self.total_planned_amount

    @property
    def is_near_limit(self):
        """Check if spending is near the alert threshold."""
        return self.progress_percentage >= self.alert_threshold

    def recalculate_totals(self):
        """Recalculate total amounts from budget items."""
        from django.db.models import Sum
        totals = self.items.aggregate(
            planned=Sum('planned_amount'),
            spent=Sum('spent_amount')
        )
        self.total_planned_amount = totals['planned'] or Decimal('0.00')
        self.total_spent_amount = totals['spent'] or Decimal('0.00')
        self.save(update_fields=['total_planned_amount', 'total_spent_amount', 'updated_at'])


class BudgetItem(models.Model):
    """
    Budget item model for category-specific budget allocation.

    Represents a portion of the budget allocated to a specific category.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name='items'
    )
    category = models.ForeignKey(
        'transactions.TransactionCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='budget_items'
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Optional custom name for the budget item'
    )
    planned_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    spent_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'budget item'
        verbose_name_plural = 'budget items'
        ordering = ['-planned_amount']
        unique_together = ['budget', 'category']

    def __str__(self):
        display_name = self.name or (self.category.name if self.category else 'Uncategorized')
        return f"{display_name}: {self.planned_amount}"

    @property
    def remaining_amount(self):
        """Calculate remaining amount for this item."""
        return self.planned_amount - self.spent_amount

    @property
    def progress_percentage(self):
        """Calculate item progress as percentage."""
        if self.planned_amount == 0:
            return Decimal('0.00')
        return (self.spent_amount / self.planned_amount) * 100

    @property
    def is_over_budget(self):
        """Check if item has exceeded budget."""
        return self.spent_amount > self.planned_amount

    @property
    def display_name(self):
        """Return the display name for this item."""
        if self.name:
            return self.name
        if self.category:
            return self.category.name
        return 'Uncategorized'

    def save(self, *args, **kwargs):
        """Override save to update budget totals."""
        super().save(*args, **kwargs)
        self.budget.recalculate_totals()
