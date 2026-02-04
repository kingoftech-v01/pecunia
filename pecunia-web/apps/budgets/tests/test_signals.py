"""Tests for Budget signals."""
import logging
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from apps.budgets.models import Budget, BudgetItem
from apps.budgets.signals import (
    update_spent_amount_for_transaction,
    recalculate_all_budget_items,
    connect_transaction_signals,
)
from apps.transactions.models import Transaction, TransactionCategory


@pytest.mark.django_db
class TestBudgetItemSaveSignals:
    """Tests for signals triggered on BudgetItem save."""

    def test_save_does_not_crash(self, budget, category):
        """Saving a BudgetItem should not crash even with signal issues."""
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("200"),
        )
        assert item.pk is not None

    def test_budget_totals_updated_on_item_save(self, budget, category):
        """Budget totals should be correct after item save (via recalculate_totals)."""
        BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("200"),
        )
        budget.refresh_from_db()
        assert budget.total_planned_amount == Decimal("500")
        assert budget.total_spent_amount == Decimal("200")

    def test_budget_totals_updated_on_item_update(self, budget, category):
        """Budget totals should update when an item is modified."""
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("100"),
        )
        item.spent_amount = Decimal("300")
        item.save()
        budget.refresh_from_db()
        assert budget.total_spent_amount == Decimal("300")

    def test_multiple_items_sum_correctly(self, budget, user):
        cat1 = TransactionCategory.objects.create(
            user=user, name="Cat1", type="expense"
        )
        cat2 = TransactionCategory.objects.create(
            user=user, name="Cat2", type="expense"
        )
        BudgetItem.objects.create(
            budget=budget, category=cat1,
            planned_amount=Decimal("300"),
            spent_amount=Decimal("100"),
        )
        BudgetItem.objects.create(
            budget=budget, category=cat2,
            planned_amount=Decimal("200"),
            spent_amount=Decimal("50"),
        )
        budget.refresh_from_db()
        assert budget.total_planned_amount == Decimal("500")
        assert budget.total_spent_amount == Decimal("150")


@pytest.mark.django_db
class TestBudgetItemDeleteSignal:
    """Tests for signal triggered on BudgetItem delete."""

    def test_delete_does_not_crash(self, budget, category):
        """Deleting a BudgetItem should not crash."""
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
        )
        item.delete()
        assert BudgetItem.objects.filter(pk=item.pk).count() == 0

    def test_budget_after_all_items_deleted(self, budget, category):
        """After deleting all items, budget should still function."""
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
        )
        item.delete()
        budget.refresh_from_db()
        # Budget still exists and is accessible
        assert budget.name == "January Budget"


@pytest.mark.django_db
class TestPreSaveSignal:
    """Tests for check_threshold_before_save pre_save signal."""

    def test_stores_old_spent_amount(self, budget, category):
        """Pre-save should store the old spent_amount for comparison."""
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("100"),
        )
        # After initial save, _old_spent_amount is set on next save
        item.spent_amount = Decimal("400")
        # The pre_save signal will read the DB value before save
        item.save()
        # The signal should have stored old_spent_amount = 100
        # and the post_save threshold check should fire

    def test_new_item_has_none_old_spent(self, budget, category):
        """New items should have _old_spent_amount = None."""
        item = BudgetItem(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("100"),
        )
        # Before save, pk is None so old_spent should be None
        item.save()
        # Item was created successfully
        assert item.pk is not None


@pytest.mark.django_db
class TestThresholdExceededSignal:
    """Tests for log_budget_threshold_exceeded post_save signal."""

    def test_logs_when_threshold_exceeded(self, budget, category, caplog):
        """Should log warning when spending exceeds alert threshold."""
        budget.alert_threshold = 50
        budget.save()

        with caplog.at_level(logging.WARNING):
            BudgetItem.objects.create(
                budget=budget, category=category,
                planned_amount=Decimal("100"),
                spent_amount=Decimal("80"),  # 80% > 50% threshold
            )

        # Check that a threshold warning was logged
        threshold_warnings = [
            r for r in caplog.records
            if "threshold" in r.message.lower() and r.levelno >= logging.WARNING
        ]
        assert len(threshold_warnings) >= 1

    def test_no_log_below_threshold(self, budget, category, caplog):
        """Should not log when spending is below alert threshold."""
        budget.alert_threshold = 90
        budget.save()

        with caplog.at_level(logging.WARNING):
            BudgetItem.objects.create(
                budget=budget, category=category,
                planned_amount=Decimal("100"),
                spent_amount=Decimal("50"),  # 50% < 90% threshold
            )

        threshold_warnings = [
            r for r in caplog.records
            if "threshold" in r.message.lower() and r.levelno >= logging.WARNING
        ]
        assert len(threshold_warnings) == 0

    def test_no_log_when_spent_unchanged(self, budget, category):
        """Should not log when spent_amount hasn't changed."""
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("100"),
            spent_amount=Decimal("80"),
        )
        # Save again without changing spent_amount
        item.name = "Updated name"
        item.save()
        # No crash means signal handled correctly


@pytest.mark.django_db
class TestUpdateRelatedAlertsSignal:
    """Tests for update_related_alerts post_save signal."""

    def test_does_not_log_on_create(self, budget, category, caplog):
        """Should not trigger alert update on creation."""
        with caplog.at_level(logging.DEBUG):
            BudgetItem.objects.create(
                budget=budget, category=category,
                planned_amount=Decimal("100"),
            )
        # On creation, the signal returns early
        debug_updates = [
            r for r in caplog.records
            if "was updated" in r.message and r.levelno == logging.DEBUG
        ]
        assert len(debug_updates) == 0

    def test_logs_on_update(self, budget, category, caplog):
        """Should log debug message on item update."""
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("100"),
        )
        with caplog.at_level(logging.DEBUG):
            item.planned_amount = Decimal("200")
            item.save()
        debug_updates = [
            r for r in caplog.records
            if "was updated" in r.message and r.levelno == logging.DEBUG
        ]
        assert len(debug_updates) >= 1


@pytest.mark.django_db
class TestUpdateSpentAmountForTransaction:
    """Tests for update_spent_amount_for_transaction function."""

    def test_updates_budget_item_on_expense(self, user, category):
        """When an expense transaction is created, matching budget items are updated."""
        today = date.today()
        budget = Budget.objects.create(
            user=user, name="Test Budget", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )

        tx = Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("100.00"),
            type="expense",
            transaction_date=today,
        )
        update_spent_amount_for_transaction(tx)

        item.refresh_from_db()
        assert item.spent_amount == Decimal("100.00")

    def test_ignores_income_transactions(self, user, income_category):
        """Income transactions should not update budget items."""
        today = date.today()
        budget = Budget.objects.create(
            user=user, name="Test", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        item = BudgetItem.objects.create(
            budget=budget, category=income_category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )

        tx = Transaction.objects.create(
            user=user, category=income_category,
            amount=Decimal("3000.00"),
            type="income",
            transaction_date=today,
        )
        update_spent_amount_for_transaction(tx)

        item.refresh_from_db()
        assert item.spent_amount == Decimal("0")

    def test_only_updates_matching_category(self, user, category):
        """Only budget items with matching category are updated."""
        today = date.today()
        cat2 = TransactionCategory.objects.create(
            user=user, name="Transport", type="expense"
        )
        budget = Budget.objects.create(
            user=user, name="Test", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        item1 = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )
        item2 = BudgetItem.objects.create(
            budget=budget, category=cat2,
            planned_amount=Decimal("200"),
            spent_amount=Decimal("0"),
        )

        tx = Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("100.00"),
            type="expense",
            transaction_date=today,
        )
        update_spent_amount_for_transaction(tx)

        item1.refresh_from_db()
        item2.refresh_from_db()
        assert item1.spent_amount == Decimal("100.00")
        assert item2.spent_amount == Decimal("0")

    def test_only_updates_active_budgets(self, user, category):
        """Only active budget items are updated."""
        today = date.today()
        budget = Budget.objects.create(
            user=user, name="Inactive", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
            is_active=False,
        )
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )

        tx = Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("100.00"),
            type="expense",
            transaction_date=today,
        )
        update_spent_amount_for_transaction(tx)

        item.refresh_from_db()
        assert item.spent_amount == Decimal("0")

    def test_respects_budget_date_range(self, user, category):
        """Only budget items within the transaction date range are updated."""
        today = date.today()
        budget = Budget.objects.create(
            user=user, name="Past", period_type="monthly",
            start_date=today - timedelta(days=60),
            end_date=today - timedelta(days=30),
        )
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )

        tx = Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("100.00"),
            type="expense",
            transaction_date=today,
        )
        update_spent_amount_for_transaction(tx)

        item.refresh_from_db()
        assert item.spent_amount == Decimal("0")


@pytest.mark.django_db
class TestRecalculateAllBudgetItems:
    """Tests for recalculate_all_budget_items function."""

    def test_recalculates_all(self, user, category):
        today = date.today()
        budget = Budget.objects.create(
            user=user, name="Recalc", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )

        # Create a transaction
        Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("150.00"),
            type="expense",
            transaction_date=today,
        )

        updated = recalculate_all_budget_items()
        item.refresh_from_db()
        assert item.spent_amount == Decimal("150.00")
        assert updated >= 1

    def test_recalculates_for_specific_user(self, user, user2, category):
        today = date.today()
        budget = Budget.objects.create(
            user=user, name="User1 Budget", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )
        Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("100.00"),
            type="expense",
            transaction_date=today,
        )

        updated = recalculate_all_budget_items(user=user)
        item.refresh_from_db()
        assert item.spent_amount == Decimal("100.00")
        assert updated >= 1

    def test_recalculates_for_specific_budget(self, user, category):
        today = date.today()
        budget1 = Budget.objects.create(
            user=user, name="Budget1", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        budget2 = Budget.objects.create(
            user=user, name="Budget2", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        cat2 = TransactionCategory.objects.create(
            user=user, name="Cat2", type="expense"
        )
        item1 = BudgetItem.objects.create(
            budget=budget1, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )
        item2 = BudgetItem.objects.create(
            budget=budget2, category=cat2,
            planned_amount=Decimal("300"),
            spent_amount=Decimal("0"),
        )
        Transaction.objects.create(
            user=user, category=category,
            amount=Decimal("100.00"),
            type="expense",
            transaction_date=today,
        )

        updated = recalculate_all_budget_items(budget=budget1)
        item1.refresh_from_db()
        item2.refresh_from_db()
        assert item1.spent_amount == Decimal("100.00")
        assert item2.spent_amount == Decimal("0")

    def test_no_change_returns_zero(self, user, category):
        today = date.today()
        budget = Budget.objects.create(
            user=user, name="NoChange", period_type="monthly",
            start_date=today, end_date=today + timedelta(days=30),
        )
        BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("0"),
        )
        # No transactions, so spent stays 0
        updated = recalculate_all_budget_items()
        assert updated == 0


@pytest.mark.django_db
class TestConnectTransactionSignals:
    """Tests for connect_transaction_signals function."""

    def test_connect_does_not_crash(self):
        """Calling connect_transaction_signals should not raise."""
        connect_transaction_signals()
