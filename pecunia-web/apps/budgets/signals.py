"""
Django signals for Budget models.

This module contains signals for automatic updates of budget items
and creation of alerts when thresholds are reached.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Budget, BudgetItem

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BudgetItem)
def update_budget_total_on_item_save(sender, instance, created, **kwargs):
    """
    Update the budget's total_planned when a budget item is saved.

    This signal ensures the budget's total_planned stays in sync
    with the sum of all its items' planned amounts.
    """
    try:
        budget = instance.budget
        total = BudgetItem.objects.filter(
            budget=budget
        ).aggregate(
            total=Sum('planned_amount')
        )['total'] or Decimal('0.00')

        if budget.total_planned != total:
            Budget.objects.filter(pk=budget.pk).update(total_planned=total)
            logger.info(
                f"Updated budget '{budget.name}' total_planned to {total}"
            )
    except Exception as e:
        logger.error(f"Error updating budget total: {e}")


@receiver(post_delete, sender=BudgetItem)
def update_budget_total_on_item_delete(sender, instance, **kwargs):
    """
    Update the budget's total_planned when a budget item is deleted.
    """
    try:
        budget = instance.budget
        total = BudgetItem.objects.filter(
            budget=budget
        ).aggregate(
            total=Sum('planned_amount')
        )['total'] or Decimal('0.00')

        Budget.objects.filter(pk=budget.pk).update(total_planned=total)
        logger.info(
            f"Updated budget '{budget.name}' total_planned to {total} after item deletion"
        )
    except Exception as e:
        logger.error(f"Error updating budget total after deletion: {e}")


@receiver(pre_save, sender=BudgetItem)
def check_threshold_before_save(sender, instance, **kwargs):
    """
    Store the old spent_amount before save for comparison.

    Django's post_save signal doesn't provide the old field values, only the
    new ones. To detect if spent_amount actually changed (vs. other fields),
    we capture the old value in pre_save and attach it to the instance. The
    post_save handler then compares old vs. new to avoid false threshold alerts.
    """
    # Capture old value here because post_save only sees new values.
    if instance.pk:
        try:
            old_instance = BudgetItem.objects.get(pk=instance.pk)
            instance._old_spent_amount = old_instance.spent_amount
        except BudgetItem.DoesNotExist:
            instance._old_spent_amount = None
    else:
        instance._old_spent_amount = None


@receiver(post_save, sender=BudgetItem)
def log_budget_threshold_exceeded(sender, instance, created, **kwargs):
    """
    Log when spending reaches or exceeds budget threshold.

    This signal monitors budget item spending and logs warnings
    when the spending percentage exceeds the budget's alert threshold.
    """
    # Skip if spent_amount hasn't changed (except for new items)
    old_spent = getattr(instance, '_old_spent_amount', None)
    if not created and old_spent is not None and old_spent == instance.spent_amount:
        return

    try:
        if instance.planned_amount and instance.planned_amount > 0:
            percentage = (instance.spent_amount / instance.planned_amount) * 100
            budget = instance.budget
            if percentage >= budget.alert_threshold:
                category_name = instance.category.name if instance.category else 'Uncategorized'
                logger.warning(
                    f"Budget threshold reached for item "
                    f"'{category_name}' at {percentage:.1f}% "
                    f"in budget '{budget.name}'"
                )
    except Exception as e:
        logger.error(f"Error checking budget threshold: {e}")


def update_spent_amount_for_transaction(transaction_instance):
    """
    Update budget item spent amounts when a transaction is created/modified.

    This function should be called from transaction signals to update
    the corresponding budget items.

    Args:
        transaction_instance: The Transaction instance that was saved
    """
    from django.db.models import Sum

    try:
        # Only process expense transactions
        if transaction_instance.type != 'expense':
            return

        # Find relevant budget items for this transaction
        budget_items = BudgetItem.objects.filter(
            budget__user=transaction_instance.user,
            budget__is_active=True,
            budget__start_date__lte=transaction_instance.transaction_date,
            budget__end_date__gte=transaction_instance.transaction_date,
            category=transaction_instance.category
        ).select_related('budget', 'category')

        for budget_item in budget_items:
            # Import here to avoid circular imports
            from apps.transactions.models import Transaction

            # Recalculate spent amount from all transactions
            total_spent = Transaction.objects.filter(
                user=budget_item.budget.user,
                category=budget_item.category,
                transaction_date__gte=budget_item.budget.start_date,
                transaction_date__lte=budget_item.budget.end_date,
                type='expense',
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')

            # Update if changed
            if budget_item.spent_amount != total_spent:
                budget_item.spent_amount = total_spent
                budget_item.save(update_fields=['spent_amount', 'updated_at'])

                logger.info(
                    f"Updated spent amount for '{budget_item.category.name}' "
                    f"in budget '{budget_item.budget.name}' to {total_spent}"
                )

    except Exception as e:
        logger.error(f"Error updating spent amount for transaction: {e}")


def recalculate_all_budget_items(user=None, budget=None):
    """
    Recalculate spent amounts for all or specific budget items.

    This function can be used for bulk updates or periodic reconciliation.

    Args:
        user: Optional user to filter budgets
        budget: Optional specific budget to recalculate
    """
    from apps.transactions.models import Transaction

    queryset = BudgetItem.objects.filter(
        budget__is_active=True,
    ).select_related('budget', 'category')

    if user:
        queryset = queryset.filter(budget__user=user)

    if budget:
        queryset = queryset.filter(budget=budget)

    updated_count = 0

    for budget_item in queryset:
        total_spent = Transaction.objects.filter(
            user=budget_item.budget.user,
            category=budget_item.category,
            transaction_date__gte=budget_item.budget.start_date,
            transaction_date__lte=budget_item.budget.end_date,
            type='expense',
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        if budget_item.spent_amount != total_spent:
            budget_item.spent_amount = total_spent
            budget_item.save(update_fields=['spent_amount', 'updated_at'])
            updated_count += 1

    logger.info(f"Recalculated {updated_count} budget items")
    return updated_count


def connect_transaction_signals():
    """
    Connect signals for Transaction model updates.

    This should be called from the transactions app's ready() method
    to properly connect cross-app signals.
    """
    try:
        from apps.transactions.models import Transaction

        @receiver(post_save, sender=Transaction)
        def handle_transaction_save(sender, instance, created, **kwargs):
            """Handle transaction save for budget updates."""
            update_spent_amount_for_transaction(instance)

        @receiver(post_delete, sender=Transaction)
        def handle_transaction_delete(sender, instance, **kwargs):
            """Handle transaction deletion for budget updates."""
            update_spent_amount_for_transaction(instance)

        logger.info("Connected transaction signals for budget updates")

    except ImportError:
        logger.warning(
            "Could not import Transaction model. "
            "Budget signals for transactions not connected."
        )


# Signal to mark related alerts as outdated when budget item is modified
@receiver(post_save, sender=BudgetItem)
def update_related_alerts(sender, instance, created, **kwargs):
    """
    Handle related alerts when a budget item is significantly modified.

    If the planned_amount changes, existing alerts may no longer be accurate.
    """
    if created:
        return

    # Check if planned_amount changed (would need pre_save to track this)
    # For now, just log the update
    logger.debug(f"Budget item '{instance}' was updated")
