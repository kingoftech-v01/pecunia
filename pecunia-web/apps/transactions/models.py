"""
Transactions Models.

Financial transactions and categories data models.
"""
import uuid
from django.db import models
from django.conf import settings


class TransactionCategory(models.Model):
    """
    Transaction category model.

    Allows users to organize transactions by custom categories.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transaction_categories'
    )
    name = models.CharField(max_length=100)
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#6366f1')
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'transaction category'
        verbose_name_plural = 'transaction categories'
        ordering = ['name']
        unique_together = ['user', 'name', 'type']

    def __str__(self):
        return f"{self.name} ({self.type})"


class Transaction(models.Model):
    """
    Financial transaction model.

    Represents income and expense transactions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    bank_account = models.ForeignKey(
        'banking.BankAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    merchant = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=255, blank=True)

    transaction_date = models.DateField()
    is_recurring = models.BooleanField(default=False)
    is_manual = models.BooleanField(default=True)

    # AI categorization
    ai_category_suggestion = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_suggested_transactions'
    )
    ai_confidence = models.FloatField(null=True, blank=True)

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'transaction'
        verbose_name_plural = 'transactions'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['user', 'type']),
            models.Index(fields=['user', 'category']),
        ]

    def __str__(self):
        return f"{self.type}: {self.amount} on {self.transaction_date}"

    @property
    def signed_amount(self):
        """Return amount with sign based on transaction type."""
        if self.type == 'expense':
            return -abs(self.amount)
        return abs(self.amount)


class RecurringTransaction(models.Model):
    """
    Recurring transaction template.

    Defines templates for recurring income/expenses.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurring_transactions'
    )
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurring_transactions'
    )

    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_occurrence = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'recurring transaction'
        verbose_name_plural = 'recurring transactions'
        ordering = ['next_occurrence']

    def __str__(self):
        return f"{self.name} ({self.frequency})"
