"""Tests for src/database/models/budget.py — Budget and BudgetItem models."""

from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from database.models.budget import Budget, BudgetItem, BudgetPeriodType


class TestBudgetPeriodType:
    """Tests for BudgetPeriodType enum."""

    def test_monthly(self):
        assert BudgetPeriodType.MONTHLY.value == "monthly"

    def test_weekly(self):
        assert BudgetPeriodType.WEEKLY.value == "weekly"

    def test_all_values_unique(self):
        values = [p.value for p in BudgetPeriodType]
        assert len(values) == len(set(values))

    def test_is_str_enum(self):
        assert isinstance(BudgetPeriodType.DAILY, str)


class TestBudgetCreation:
    """Tests for Budget model creation."""

    def test_create_budget(self):
        budget = Budget(
            id=1, user_id=1, name="Monthly Budget",
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
        )
        assert budget.name == "Monthly Budget"
        assert budget.period_type == BudgetPeriodType.MONTHLY

    def test_defaults(self):
        budget = Budget(
            id=1, user_id=1, name="Test",
            start_date=date(2024, 1, 1),
        )
        assert budget.is_active is True
        assert budget.is_synced is False


class TestBudgetProperties:
    """Tests for Budget computed properties."""

    def _budget_with_items(self):
        budget = Budget(
            id=1, user_id=1, name="Monthly",
            period_type=BudgetPeriodType.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        item1 = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("300"),
        )
        item2 = BudgetItem(
            id=2, budget_id=1, category_id=2,
            planned_amount=Decimal("300"), spent_amount=Decimal("350"),
        )
        budget.items = [item1, item2]
        return budget

    def test_total_planned(self):
        budget = self._budget_with_items()
        assert budget.total_planned == Decimal("800")

    def test_total_spent(self):
        budget = self._budget_with_items()
        assert budget.total_spent == Decimal("650")

    def test_total_remaining(self):
        budget = self._budget_with_items()
        assert budget.total_remaining == Decimal("150")

    def test_overall_progress_percentage(self):
        budget = self._budget_with_items()
        progress = budget.overall_progress_percentage
        assert 80 < progress < 82  # 650/800 = 81.25%

    def test_progress_percentage_zero_planned(self):
        budget = Budget(id=1, user_id=1, name="Empty", start_date=date(2024, 1, 1))
        budget.items = []
        assert budget.overall_progress_percentage == 0.0

    def test_is_over_budget_false(self):
        budget = self._budget_with_items()
        assert budget.is_over_budget is False

    def test_is_over_budget_true(self):
        budget = Budget(id=1, user_id=1, name="Over", start_date=date(2024, 1, 1))
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("100"), spent_amount=Decimal("200"),
        )
        budget.items = [item]
        assert budget.is_over_budget is True

    def test_is_current_true(self):
        today = date.today()
        budget = Budget(
            id=1, user_id=1, name="Current",
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=5),
        )
        assert budget.is_current is True

    def test_is_current_false_past(self):
        budget = Budget(
            id=1, user_id=1, name="Past",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 31),
        )
        assert budget.is_current is False

    def test_is_current_no_end_date(self):
        budget = Budget(
            id=1, user_id=1, name="Open",
            start_date=date(2020, 1, 1),
            end_date=None,
        )
        assert budget.is_current is True


class TestBudgetMethods:
    """Tests for Budget methods."""

    def test_get_item_by_category_found(self):
        budget = Budget(id=1, user_id=1, name="Test", start_date=date(2024, 1, 1))
        item = BudgetItem(id=1, budget_id=1, category_id=5, planned_amount=Decimal("100"))
        budget.items = [item]
        assert budget.get_item_by_category(5) is item

    def test_get_item_by_category_not_found(self):
        budget = Budget(id=1, user_id=1, name="Test", start_date=date(2024, 1, 1))
        budget.items = []
        assert budget.get_item_by_category(99) is None

    def test_calculate_progress(self):
        budget = Budget(id=1, user_id=1, name="Test", start_date=date(2024, 1, 1))
        item1 = BudgetItem(id=1, budget_id=1, category_id=1,
                            planned_amount=Decimal("100"), spent_amount=Decimal("90"))
        item2 = BudgetItem(id=2, budget_id=1, category_id=2,
                            planned_amount=Decimal("100"), spent_amount=Decimal("110"))
        item3 = BudgetItem(id=3, budget_id=1, category_id=3,
                            planned_amount=Decimal("100"), spent_amount=Decimal("30"))
        budget.items = [item1, item2, item3]
        progress = budget.calculate_progress()
        assert progress["items_over_budget"] == 1
        assert progress["items_warning"] == 1
        assert progress["items_on_track"] == 1

    def test_mark_as_synced(self):
        budget = Budget(id=1, user_id=1, name="Test", start_date=date(2024, 1, 1))
        budget.mark_as_synced(42)
        assert budget.server_id == 42
        assert budget.is_synced is True

    def test_mark_as_unsynced(self):
        budget = Budget(id=1, user_id=1, name="Test", start_date=date(2024, 1, 1), is_synced=True)
        budget.mark_as_unsynced()
        assert budget.is_synced is False

    def test_repr(self):
        budget = Budget(
            id=1, name="Monthly",
            period_type=BudgetPeriodType.MONTHLY,
            is_active=True,
        )
        assert "Monthly" in repr(budget)
        assert "monthly" in repr(budget)


class TestBudgetClassMethods:
    """Tests for Budget class methods with mocked session."""

    def test_get_by_server_id(self):
        mock_session = MagicMock()
        mock_q = MagicMock()
        mock_session.query.return_value = mock_q
        mock_q.filter.return_value = mock_q
        mock_q.first.return_value = Budget(id=1, server_id=42)

        result = Budget.get_by_server_id(mock_session, 42)
        assert result.server_id == 42

    def test_get_active(self):
        mock_session = MagicMock()
        mock_q = MagicMock()
        mock_session.query.return_value = mock_q
        mock_q.filter.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.all.return_value = []

        result = Budget.get_active(mock_session, user_id=1)
        assert result == []

    def test_get_all_for_user_active_only(self):
        mock_session = MagicMock()
        mock_q = MagicMock()
        mock_session.query.return_value = mock_q
        mock_q.filter.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.all.return_value = []

        result = Budget.get_all_for_user(mock_session, user_id=1, include_inactive=False)
        assert result == []


class TestBudgetItem:
    """Tests for BudgetItem model."""

    def test_creation(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("200"),
        )
        assert item.planned_amount == Decimal("500")
        assert item.spent_amount == Decimal("200")

    def test_remaining_amount(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("200"),
        )
        assert item.remaining_amount == Decimal("300")

    def test_progress_percentage(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("200"), spent_amount=Decimal("100"),
        )
        assert item.progress_percentage == 50.0

    def test_progress_percentage_zero_planned_no_spent(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("0"), spent_amount=Decimal("0"),
        )
        assert item.progress_percentage == 0.0

    def test_progress_percentage_zero_planned_with_spent(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("0"), spent_amount=Decimal("50"),
        )
        assert item.progress_percentage == 100.0

    def test_is_over_budget(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("100"), spent_amount=Decimal("150"),
        )
        assert item.is_over_budget is True

    def test_is_not_over_budget(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("100"), spent_amount=Decimal("50"),
        )
        assert item.is_over_budget is False

    def test_is_synced(self):
        item = BudgetItem(id=1, budget_id=1, category_id=1, server_id=42)
        assert item.is_synced is True

    def test_is_not_synced(self):
        item = BudgetItem(id=1, budget_id=1, category_id=1)
        assert item.is_synced is False

    def test_add_spending(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("200"),
        )
        item.add_spending(Decimal("100"))
        assert item.spent_amount == Decimal("300")

    def test_add_spending_negative_refund(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("200"),
        )
        item.add_spending(Decimal("-50"))
        assert item.spent_amount == Decimal("150")

    def test_reset_spending(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("200"),
        )
        item.reset_spending()
        assert item.spent_amount == Decimal("0")

    def test_update_planned(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"),
        )
        item.update_planned(Decimal("800"))
        assert item.planned_amount == Decimal("800")

    def test_calculate_progress_on_track(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("200"),
        )
        progress = item.calculate_progress()
        assert progress["status"] == "on_track"

    def test_calculate_progress_warning(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("100"), spent_amount=Decimal("90"),
        )
        progress = item.calculate_progress()
        assert progress["status"] == "warning"

    def test_calculate_progress_over_budget(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("100"), spent_amount=Decimal("150"),
        )
        progress = item.calculate_progress()
        assert progress["status"] == "over_budget"

    def test_mark_as_synced(self):
        item = BudgetItem(id=1, budget_id=1, category_id=1)
        item.mark_as_synced(42)
        assert item.server_id == 42

    def test_repr(self):
        item = BudgetItem(
            id=1, budget_id=1, category_id=1,
            planned_amount=Decimal("500"), spent_amount=Decimal("200"),
        )
        assert "500" in repr(item)
        assert "200" in repr(item)
