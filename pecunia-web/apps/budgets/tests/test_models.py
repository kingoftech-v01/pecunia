"""Tests for Budget models."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from apps.budgets.models import Budget, BudgetItem
from apps.transactions.models import TransactionCategory


@pytest.mark.django_db
class TestBudget:
    """Tests for Budget model."""

    def test_str(self, budget):
        assert str(budget) == "January Budget (monthly)"

    def test_remaining_amount(self, budget):
        expected = budget.total_planned_amount - budget.total_spent_amount
        assert budget.remaining_amount == expected

    def test_remaining_amount_positive(self):
        """Test with specific values."""
        b = Budget(total_planned_amount=Decimal("1000"), total_spent_amount=Decimal("300"))
        assert b.remaining_amount == Decimal("700")

    def test_remaining_amount_negative(self):
        b = Budget(total_planned_amount=Decimal("500"), total_spent_amount=Decimal("700"))
        assert b.remaining_amount == Decimal("-200")

    def test_progress_percentage(self, budget):
        expected = (budget.total_spent_amount / budget.total_planned_amount) * 100
        assert budget.progress_percentage == expected

    def test_progress_percentage_zero_planned(self, user):
        b = Budget.objects.create(
            user=user, name="Empty", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_planned_amount=Decimal("0"),
            total_spent_amount=Decimal("0"),
        )
        assert b.progress_percentage == Decimal("0.00")

    def test_is_over_budget_false(self, budget):
        # Default fixture: spent < planned
        assert budget.is_over_budget is False

    def test_is_over_budget_true(self, user):
        b = Budget.objects.create(
            user=user, name="Over", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_planned_amount=Decimal("100"),
            total_spent_amount=Decimal("200"),
        )
        assert b.is_over_budget is True

    def test_is_over_budget_equal(self, user):
        b = Budget.objects.create(
            user=user, name="Equal", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_planned_amount=Decimal("100"),
            total_spent_amount=Decimal("100"),
        )
        assert b.is_over_budget is False

    def test_is_near_limit(self, user):
        b = Budget.objects.create(
            user=user, name="Near", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_planned_amount=Decimal("100"),
            total_spent_amount=Decimal("85"),
            alert_threshold=80,
        )
        assert b.is_near_limit is True

    def test_is_near_limit_false(self, user):
        b = Budget.objects.create(
            user=user, name="Safe", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_planned_amount=Decimal("100"),
            total_spent_amount=Decimal("50"),
            alert_threshold=80,
        )
        assert b.is_near_limit is False

    def test_recalculate_totals(self, user, category):
        b = Budget.objects.create(
            user=user, name="Calc", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_planned_amount=Decimal("0"),
            total_spent_amount=Decimal("0"),
        )
        BudgetItem.objects.create(
            budget=b, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("200"),
        )
        # After BudgetItem.save(), recalculate_totals is called
        b.refresh_from_db()
        assert b.total_planned_amount == Decimal("500")
        assert b.total_spent_amount == Decimal("200")

    def test_recalculate_totals_multiple_items(self, user, category):
        b = Budget.objects.create(
            user=user, name="Multi", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        cat2 = TransactionCategory.objects.create(
            user=user, name="Transport", type="expense"
        )
        BudgetItem.objects.create(
            budget=b, category=category,
            planned_amount=Decimal("300"),
            spent_amount=Decimal("100"),
        )
        BudgetItem.objects.create(
            budget=b, category=cat2,
            planned_amount=Decimal("200"),
            spent_amount=Decimal("50"),
        )
        b.refresh_from_db()
        assert b.total_planned_amount == Decimal("500")
        assert b.total_spent_amount == Decimal("150")

    def test_default_values(self, user):
        b = Budget.objects.create(
            user=user, name="Defaults", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        assert b.total_planned_amount == Decimal("0.00")
        assert b.total_spent_amount == Decimal("0.00")
        assert b.is_active is True
        assert b.is_rollover is False
        assert b.alert_threshold == 80
        assert b.notify_on_exceed is True

    def test_ordering(self, user):
        Budget.objects.create(
            user=user, name="Earlier",
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
        )
        Budget.objects.create(
            user=user, name="Later",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        budgets = list(Budget.objects.filter(user=user))
        assert budgets[0].start_date >= budgets[-1].start_date

    def test_verbose_names(self):
        assert Budget._meta.verbose_name == "budget"
        assert Budget._meta.verbose_name_plural == "budgets"


@pytest.mark.django_db
class TestBudgetItem:
    """Tests for BudgetItem model."""

    def test_str_with_name(self, budget_item):
        assert str(budget_item) == "Groceries Budget: 500.00"

    def test_str_with_category_only(self, budget, category):
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("100.00"),
        )
        assert str(item) == "Groceries: 100.00"

    def test_str_uncategorized(self, budget):
        item = BudgetItem.objects.create(
            budget=budget,
            planned_amount=Decimal("100"),
        )
        assert "Uncategorized" in str(item)

    def test_remaining_amount(self, budget_item):
        expected = budget_item.planned_amount - budget_item.spent_amount
        assert budget_item.remaining_amount == expected

    def test_progress_percentage(self, budget_item):
        expected = (budget_item.spent_amount / budget_item.planned_amount) * 100
        assert budget_item.progress_percentage == expected

    def test_progress_percentage_zero_planned(self, budget):
        item = BudgetItem.objects.create(
            budget=budget,
            planned_amount=Decimal("0"),
            spent_amount=Decimal("0"),
        )
        assert item.progress_percentage == Decimal("0.00")

    def test_is_over_budget_false(self, budget_item):
        assert budget_item.is_over_budget is False

    def test_is_over_budget_true(self, budget):
        item = BudgetItem.objects.create(
            budget=budget,
            planned_amount=Decimal("100"),
            spent_amount=Decimal("200"),
        )
        assert item.is_over_budget is True

    def test_display_name_with_name(self, budget_item):
        assert budget_item.display_name == "Groceries Budget"

    def test_display_name_with_category(self, budget, category):
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("100"),
        )
        assert item.display_name == "Groceries"

    def test_display_name_uncategorized(self, budget):
        item = BudgetItem.objects.create(
            budget=budget,
            planned_amount=Decimal("100"),
        )
        assert item.display_name == "Uncategorized"

    def test_save_triggers_recalculate(self, budget, category):
        item = BudgetItem.objects.create(
            budget=budget, category=category,
            planned_amount=Decimal("500"),
            spent_amount=Decimal("200"),
        )
        budget.refresh_from_db()
        assert budget.total_planned_amount == Decimal("500")
        assert budget.total_spent_amount == Decimal("200")

    def test_update_item_recalculates(self, budget_item):
        budget = budget_item.budget
        budget_item.planned_amount = Decimal("800")
        budget_item.save()
        budget.refresh_from_db()
        assert budget.total_planned_amount == Decimal("800")

    def test_unique_together_budget_category(self, budget, category, budget_item):
        """Cannot create two items with same budget and category."""
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            BudgetItem.objects.create(
                budget=budget, category=category,
                planned_amount=Decimal("100"),
            )

    def test_default_spent_amount(self, budget):
        item = BudgetItem.objects.create(
            budget=budget,
            planned_amount=Decimal("100"),
        )
        assert item.spent_amount == Decimal("0.00")

    def test_timestamps(self, budget_item):
        assert budget_item.created_at is not None
        assert budget_item.updated_at is not None

    def test_verbose_names(self):
        assert BudgetItem._meta.verbose_name == "budget item"
        assert BudgetItem._meta.verbose_name_plural == "budget items"
