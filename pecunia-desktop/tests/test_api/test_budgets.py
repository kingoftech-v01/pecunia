"""Tests for src/api/budgets.py — Budgets API client."""

from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

import pytest

from api.client import APIResponse, APIError
from api.budgets import (
    Budget, BudgetItem, BudgetWithItems, BudgetProgress, BudgetAlert,
    BudgetSummary, BudgetFilter, BudgetItemProgress, BudgetVsActualReport,
    PaginatedBudgets, BudgetsAPI, BudgetStatus, BudgetItemType,
)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def api(mock_client):
    return BudgetsAPI(mock_client)


class TestBudget:
    """Tests for Budget dataclass."""

    def test_from_dict_full(self):
        data = {
            "id": "b1", "name": "Monthly", "amount": "2000",
            "period": "monthly", "category": "all",
            "is_active": True, "rollover": True, "notify_at_percent": 90,
        }
        budget = Budget.from_dict(data)
        assert budget.id == "b1"
        assert budget.amount == Decimal("2000")
        assert budget.rollover is True
        assert budget.notify_at_percent == 90

    def test_from_dict_defaults(self):
        budget = Budget.from_dict({"id": "b2", "name": "Test"})
        assert budget.amount == Decimal("0")
        assert budget.is_active is True
        assert budget.rollover is False

    def test_to_dict(self):
        budget = Budget(id="b1", name="Test", amount=Decimal("500"), period="monthly")
        d = budget.to_dict()
        assert d["name"] == "Test"
        assert d["amount"] == Decimal("500")


class TestBudgetItem:
    """Tests for BudgetItem."""

    def test_from_dict(self):
        data = {"id": "i1", "budget_id": "b1", "name": "Food", "amount": "300"}
        item = BudgetItem.from_dict(data)
        assert item.name == "Food"
        assert item.amount == Decimal("300")

    def test_to_dict(self):
        item = BudgetItem(id="i1", budget_id="b1", name="Food", amount=Decimal("300"))
        d = item.to_dict()
        assert d["budget_id"] == "b1"


class TestBudgetWithItems:
    """Tests for BudgetWithItems."""

    def test_from_dict(self):
        data = {
            "budget": {"id": "b1", "name": "Test", "amount": "1000", "period": "monthly"},
            "items": [
                {"id": "i1", "budget_id": "b1", "name": "Food", "amount": "300"},
                {"id": "i2", "budget_id": "b1", "name": "Transport", "amount": "200"},
            ],
        }
        result = BudgetWithItems.from_dict(data)
        assert result.budget.name == "Test"
        assert len(result.items) == 2


class TestBudgetProgress:
    """Tests for BudgetProgress."""

    def test_from_dict(self):
        data = {
            "budget_id": "b1", "budget_name": "Monthly",
            "budget_amount": 2000, "spent_amount": 1500,
            "remaining_amount": 500, "percent_used": 75,
            "status": "on_track", "period_start": "2024-01-01", "period_end": "2024-01-31",
        }
        prog = BudgetProgress.from_dict(data)
        assert prog.percent_used == 75
        assert prog.is_exceeded is False
        assert prog.is_warning is False

    def test_is_exceeded(self):
        data = {
            "budget_id": "b1", "budget_name": "Monthly",
            "budget_amount": 2000, "spent_amount": 2500,
            "percent_used": 125, "status": "exceeded",
            "period_start": "2024-01-01", "period_end": "2024-01-31",
        }
        prog = BudgetProgress.from_dict(data)
        assert prog.is_exceeded is True

    def test_is_warning(self):
        data = {
            "budget_id": "b1", "budget_name": "Monthly",
            "budget_amount": 2000, "spent_amount": 1800,
            "percent_used": 90, "status": "warning",
            "period_start": "2024-01-01", "period_end": "2024-01-31",
        }
        prog = BudgetProgress.from_dict(data)
        assert prog.is_warning is True


class TestBudgetAlert:
    """Tests for BudgetAlert."""

    def test_from_dict(self):
        data = {
            "id": "a1", "budget_id": "b1", "budget_name": "Monthly",
            "alert_type": "warning", "message": "80% spent",
            "percent_used": 80, "created_at": "2024-01-20",
        }
        alert = BudgetAlert.from_dict(data)
        assert alert.alert_type == "warning"
        assert alert.is_read is False


class TestBudgetSummary:
    """Tests for BudgetSummary."""

    def test_from_dict(self):
        data = {
            "total_budgeted": 5000, "total_spent": 3000,
            "total_remaining": 2000, "budget_count": 5,
            "on_track_count": 3, "warning_count": 1, "exceeded_count": 1,
        }
        summary = BudgetSummary.from_dict(data)
        assert summary.budget_count == 5
        assert summary.total_remaining == 2000


class TestBudgetFilter:
    """Tests for BudgetFilter."""

    def test_empty_filter(self):
        f = BudgetFilter(active_only=False)
        params = f.to_params()
        assert "active_only" not in params

    def test_active_filter(self):
        f = BudgetFilter(active_only=True)
        params = f.to_params()
        assert params["active_only"] == "true"

    def test_full_filter(self):
        f = BudgetFilter(
            active_only=True, category="food", period="monthly",
            min_amount=100, max_amount=5000, search="grocery",
        )
        params = f.to_params()
        assert params["category"] == "food"
        assert params["min_amount"] == 100


class TestBudgetVsActualReport:
    """Tests for BudgetVsActualReport."""

    def test_from_dict(self):
        data = {
            "budget_id": "b1", "budget_name": "Monthly",
            "period_start": "2024-01-01", "period_end": "2024-01-31",
            "total_budgeted": 2000, "total_actual": 1500,
        }
        report = BudgetVsActualReport.from_dict(data)
        assert report.is_under_budget is True
        assert report.is_over_budget is False

    def test_over_budget(self):
        data = {
            "budget_id": "b1", "budget_name": "Monthly",
            "period_start": "2024-01-01", "period_end": "2024-01-31",
            "total_budgeted": 2000, "total_actual": 2500,
        }
        report = BudgetVsActualReport.from_dict(data)
        assert report.is_over_budget is True


class TestPaginatedBudgets:
    """Tests for PaginatedBudgets."""

    def test_from_dict(self):
        data = {
            "items": [{"id": "b1", "name": "Monthly", "amount": 2000, "period": "monthly"}],
            "total": 1, "page": 1, "page_size": 50,
        }
        result = PaginatedBudgets.from_dict(data)
        assert len(result.items) == 1
        assert result.total_pages == 1


class TestBudgetsAPI:
    """Tests for BudgetsAPI methods."""

    async def test_list_budgets(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"items": [{"id": "b1", "name": "Monthly", "amount": 2000, "period": "monthly"}],
                  "total": 1, "page": 1, "page_size": 50},
        )
        result = await api.list()
        assert len(result.items) == 1

    async def test_list_budgets_legacy_format(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data=[{"id": "b1", "name": "Monthly", "amount": 2000, "period": "monthly"}],
        )
        result = await api.list()
        assert len(result.items) == 1

    async def test_get_budget(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "b1", "name": "Monthly", "amount": 2000, "period": "monthly", "items": []},
        )
        result = await api.get("b1")
        assert result.budget.name == "Monthly"

    async def test_create_budget(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=201,
            data={"id": "b_new", "name": "New", "amount": 1000, "period": "monthly"},
        )
        budget = Budget(id="", name="New", amount=Decimal("1000"), period="monthly")
        created = await api.create(budget)
        assert created.id == "b_new"

    async def test_update_budget(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "b1", "name": "Updated", "amount": 3000, "period": "monthly"},
        )
        updated = await api.update("b1", {"name": "Updated", "amount": 3000})
        assert updated.name == "Updated"

    async def test_delete_budget(self, api, mock_client):
        mock_client.delete.return_value = APIResponse(success=True, status_code=200, data={})
        result = await api.delete("b1")
        assert result is True

    async def test_get_progress(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"budget_id": "b1", "budget_name": "Monthly", "budget_amount": 2000,
                  "spent_amount": 1000, "remaining_amount": 1000, "percent_used": 50,
                  "status": "on_track", "period_start": "2024-01-01", "period_end": "2024-01-31"},
        )
        progress = await api.get_progress("b1")
        assert progress.percent_used == 50

    async def test_get_summary(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"total_budgeted": 5000, "total_spent": 3000, "total_remaining": 2000,
                  "budget_count": 3, "on_track_count": 2, "warning_count": 1, "exceeded_count": 0},
        )
        summary = await api.get_summary()
        assert summary.budget_count == 3

    async def test_list_items(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data=[{"id": "i1", "budget_id": "b1", "name": "Food", "amount": 300}],
        )
        items = await api.list_items("b1")
        assert len(items) == 1

    async def test_create_item(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=201,
            data={"id": "i_new", "budget_id": "b1", "name": "New", "amount": 100},
        )
        item = BudgetItem(id="", budget_id="b1", name="New", amount=Decimal("100"))
        created = await api.create_item("b1", item)
        assert created.id == "i_new"

    async def test_delete_item(self, api, mock_client):
        mock_client.delete.return_value = APIResponse(success=True, status_code=200, data={})
        result = await api.delete_item("b1", "i1")
        assert result is True

    async def test_get_alerts(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data=[{"id": "a1", "budget_id": "b1", "budget_name": "Monthly",
                   "alert_type": "warning", "message": "80%", "percent_used": 80, "created_at": "2024-01-20"}],
        )
        alerts = await api.get_alerts()
        assert len(alerts) == 1

    async def test_mark_alert_read(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(success=True, status_code=200, data={})
        result = await api.mark_alert_read("a1")
        assert result is True

    async def test_activate_deactivate(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "b1", "name": "Test", "amount": 1000, "period": "monthly", "is_active": True},
        )
        result = await api.activate("b1")
        assert result.is_active is True

    async def test_duplicate_budget(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=201,
            data={"id": "b_copy", "name": "Monthly Copy", "amount": 2000, "period": "monthly"},
        )
        result = await api.duplicate("b1", "Monthly Copy")
        assert result.id == "b_copy"

    async def test_get_budget_vs_actual(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"budget_id": "b1", "budget_name": "Monthly",
                  "period_start": "2024-01-01", "period_end": "2024-01-31",
                  "total_budgeted": 2000, "total_actual": 1800},
        )
        report = await api.get_budget_vs_actual("b1")
        assert report.is_under_budget is True
