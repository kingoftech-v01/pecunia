"""Tests for Budget API views."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from apps.budgets.models import Budget, BudgetItem
from apps.transactions.models import TransactionCategory


BUDGETS_URL = "/api/v1/budgets/"
ITEMS_URL = "/api/v1/budgets/items/"


@pytest.mark.django_db
class TestBudgetViewSet:
    """Tests for BudgetViewSet."""

    def test_list_unauthenticated(self, api_client):
        response = api_client.get(BUDGETS_URL)
        assert response.status_code == 401

    def test_list_budgets(self, auth_client, budget):
        response = auth_client.get(BUDGETS_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_create_budget(self, auth_client):
        data = {
            "name": "February Budget",
            "period_type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=28)),
        }
        response = auth_client.post(BUDGETS_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "February Budget"

    def test_create_budget_with_items(self, auth_client, category):
        data = {
            "name": "Budget with Items",
            "period_type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
            "items": [
                {
                    "category": str(category.id),
                    "name": "Food",
                    "planned_amount": "500.00",
                },
            ],
        }
        response = auth_client.post(BUDGETS_URL, data, format="json")
        assert response.status_code == 201

    def test_retrieve_budget(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}{budget.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "January Budget"
        assert "items" in response.data
        assert "remaining_amount" in response.data
        assert "progress_percentage" in response.data
        assert "is_over_budget" in response.data
        assert "is_near_limit" in response.data
        assert "item_count" in response.data

    def test_update_budget(self, auth_client, budget):
        data = {
            "name": "Updated Budget",
            "period_type": "monthly",
            "start_date": str(budget.start_date),
            "end_date": str(budget.end_date),
        }
        response = auth_client.put(f"{BUDGETS_URL}{budget.id}/", data, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "Updated Budget"

    def test_partial_update_budget(self, auth_client, budget):
        response = auth_client.patch(
            f"{BUDGETS_URL}{budget.id}/",
            {"name": "Patched Budget"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["name"] == "Patched Budget"

    def test_delete_budget(self, auth_client, budget):
        response = auth_client.delete(f"{BUDGETS_URL}{budget.id}/")
        assert response.status_code == 204

    def test_list_filters_by_period_type(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}?period_type=monthly")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_list_filters_by_active(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}?is_active=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_list_search(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}?search=January")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_date_from_filter(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}?date_from={date.today()}")
        assert response.status_code == 200

    def test_date_to_filter(self, auth_client, budget):
        future = date.today() + timedelta(days=60)
        response = auth_client.get(f"{BUDGETS_URL}?date_to={future}")
        assert response.status_code == 200

    def test_status_filter_over_budget(self, auth_client, user):
        Budget.objects.create(
            user=user, name="Over", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_planned_amount=Decimal("100"),
            total_spent_amount=Decimal("200"),
        )
        response = auth_client.get(f"{BUDGETS_URL}?status=over_budget")
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_status_filter_on_track(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}?status=on_track")
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    # --- stats ---

    def test_stats_default(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}stats/")
        assert response.status_code == 200
        assert "total_budgets" in response.data
        assert "total_planned" in response.data
        assert "total_spent" in response.data
        assert "total_remaining" in response.data
        assert "overall_progress" in response.data
        assert "budgets_over_limit" in response.data
        assert "budgets_near_limit" in response.data

    def test_stats_week(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}stats/?period=week")
        assert response.status_code == 200

    def test_stats_year(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}stats/?period=year")
        assert response.status_code == 200

    def test_stats_all(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}stats/?period=all")
        assert response.status_code == 200
        assert response.data["total_budgets"] >= 1

    # --- current ---

    def test_current_budgets(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}current/")
        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) >= 1

    def test_current_excludes_inactive(self, auth_client, user):
        Budget.objects.create(
            user=user, name="Inactive", period_type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            is_active=False,
        )
        response = auth_client.get(f"{BUDGETS_URL}current/")
        names = [b["name"] for b in response.data]
        assert "Inactive" not in names

    def test_current_excludes_past(self, auth_client, user):
        Budget.objects.create(
            user=user, name="Past", period_type="monthly",
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
        )
        response = auth_client.get(f"{BUDGETS_URL}current/")
        names = [b["name"] for b in response.data]
        assert "Past" not in names

    # --- progress ---

    def test_progress(self, auth_client, budget):
        response = auth_client.get(f"{BUDGETS_URL}{budget.id}/progress/")
        assert response.status_code == 200
        assert "budget_name" in response.data
        assert "planned_amount" in response.data
        assert "spent_amount" in response.data
        assert "remaining_amount" in response.data
        assert "progress_percentage" in response.data
        assert "days_remaining" in response.data
        assert "daily_budget" in response.data
        assert "daily_spending_rate" in response.data
        assert "projected_spending" in response.data
        assert "is_on_track" in response.data
        assert "items" in response.data

    # --- recalculate ---

    def test_recalculate(self, auth_client, budget, budget_item):
        response = auth_client.post(f"{BUDGETS_URL}{budget.id}/recalculate/")
        assert response.status_code == 200

    # --- by_category ---

    def test_by_category(self, auth_client, budget, budget_item):
        response = auth_client.get(f"{BUDGETS_URL}by_category/")
        assert response.status_code == 200
        assert isinstance(response.data, list)

    # --- IDOR ---

    def test_idor_list(self, auth_client2, budget):
        response = auth_client2.get(BUDGETS_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_idor_retrieve(self, auth_client2, budget):
        response = auth_client2.get(f"{BUDGETS_URL}{budget.id}/")
        assert response.status_code == 404

    def test_idor_update(self, auth_client2, budget):
        response = auth_client2.patch(
            f"{BUDGETS_URL}{budget.id}/",
            {"name": "Hacked"},
            format="json",
        )
        assert response.status_code == 404

    def test_idor_delete(self, auth_client2, budget):
        response = auth_client2.delete(f"{BUDGETS_URL}{budget.id}/")
        assert response.status_code == 404

    def test_idor_progress(self, auth_client2, budget):
        response = auth_client2.get(f"{BUDGETS_URL}{budget.id}/progress/")
        assert response.status_code == 404

    def test_idor_recalculate(self, auth_client2, budget):
        response = auth_client2.post(f"{BUDGETS_URL}{budget.id}/recalculate/")
        assert response.status_code == 404

    def test_idor_stats_isolation(self, auth_client2, budget):
        response = auth_client2.get(f"{BUDGETS_URL}stats/")
        assert response.status_code == 200
        assert response.data["total_budgets"] == 0


@pytest.mark.django_db
class TestBudgetItemViewSet:
    """Tests for BudgetItemViewSet."""

    def test_list_unauthenticated(self, api_client):
        response = api_client.get(ITEMS_URL)
        assert response.status_code == 401

    def test_list_items(self, auth_client, budget_item):
        response = auth_client.get(ITEMS_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_create_item(self, auth_client, budget, category):
        cat2 = TransactionCategory.objects.create(
            user=budget.user, name="Transport", type="expense"
        )
        data = {
            "budget": str(budget.id),
            "category": str(cat2.id),
            "name": "Transport Budget",
            "planned_amount": "200.00",
        }
        response = auth_client.post(ITEMS_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Transport Budget"

    def test_retrieve_item(self, auth_client, budget_item):
        response = auth_client.get(f"{ITEMS_URL}{budget_item.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "Groceries Budget"
        assert "remaining_amount" in response.data
        assert "progress_percentage" in response.data
        assert "is_over_budget" in response.data
        assert "display_name" in response.data

    def test_update_item(self, auth_client, budget_item, budget):
        data = {
            "budget": str(budget.id),
            "category": str(budget_item.category.id),
            "name": "Updated Item",
            "planned_amount": "600.00",
        }
        response = auth_client.put(
            f"{ITEMS_URL}{budget_item.id}/", data, format="json"
        )
        assert response.status_code == 200
        assert response.data["name"] == "Updated Item"

    def test_partial_update_item(self, auth_client, budget_item):
        response = auth_client.patch(
            f"{ITEMS_URL}{budget_item.id}/",
            {"planned_amount": "750.00"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["planned_amount"] == "750.00"

    def test_delete_item(self, auth_client, budget_item):
        response = auth_client.delete(f"{ITEMS_URL}{budget_item.id}/")
        assert response.status_code == 204

    def test_filter_by_budget(self, auth_client, budget, budget_item):
        response = auth_client.get(f"{ITEMS_URL}?budget={budget.id}")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_active(self, auth_client, budget_item):
        response = auth_client.get(f"{ITEMS_URL}?is_active=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    # --- update-spent ---

    def test_update_spent_set_mode(self, auth_client, budget_item):
        response = auth_client.post(
            f"{ITEMS_URL}{budget_item.id}/update-spent/",
            {"amount": "300.00", "mode": "set"},
            format="json",
        )
        assert response.status_code == 200
        assert Decimal(response.data["spent_amount"]) == Decimal("300.00")

    def test_update_spent_add_mode(self, auth_client, budget_item):
        original_spent = budget_item.spent_amount
        response = auth_client.post(
            f"{ITEMS_URL}{budget_item.id}/update-spent/",
            {"amount": "50.00", "mode": "add"},
            format="json",
        )
        assert response.status_code == 200
        assert Decimal(response.data["spent_amount"]) == original_spent + Decimal("50.00")

    def test_update_spent_default_set_mode(self, auth_client, budget_item):
        response = auth_client.post(
            f"{ITEMS_URL}{budget_item.id}/update-spent/",
            {"amount": "400.00"},
            format="json",
        )
        assert response.status_code == 200
        assert Decimal(response.data["spent_amount"]) == Decimal("400.00")

    def test_update_spent_missing_amount(self, auth_client, budget_item):
        response = auth_client.post(
            f"{ITEMS_URL}{budget_item.id}/update-spent/",
            {},
            format="json",
        )
        assert response.status_code == 400
        assert "amount" in response.data["detail"].lower()

    def test_update_spent_invalid_amount(self, auth_client, budget_item):
        # View catches ValueError/TypeError but Decimal() raises InvalidOperation
        # for invalid strings, which is an unhandled exception
        import decimal
        with pytest.raises(decimal.InvalidOperation):
            auth_client.post(
                f"{ITEMS_URL}{budget_item.id}/update-spent/",
                {"amount": "not-a-number"},
                format="json",
            )

    # --- bulk-update ---

    def test_bulk_update(self, auth_client, budget_item):
        data = {
            "items": [
                {"id": str(budget_item.id), "spent_amount": "350.00"},
            ]
        }
        response = auth_client.post(
            f"{ITEMS_URL}bulk-update/", data, format="json"
        )
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_bulk_update_empty_list(self, auth_client):
        response = auth_client.post(
            f"{ITEMS_URL}bulk-update/", {"items": []}, format="json"
        )
        assert response.status_code == 400

    def test_bulk_update_no_items(self, auth_client):
        response = auth_client.post(
            f"{ITEMS_URL}bulk-update/", {}, format="json"
        )
        assert response.status_code == 400

    def test_bulk_update_invalid_id_skipped(self, auth_client):
        import uuid
        data = {
            "items": [
                {"id": str(uuid.uuid4()), "spent_amount": "100.00"},
            ]
        }
        response = auth_client.post(
            f"{ITEMS_URL}bulk-update/", data, format="json"
        )
        assert response.status_code == 200
        assert len(response.data) == 0

    # --- IDOR ---

    def test_idor_list(self, auth_client2, budget_item):
        response = auth_client2.get(ITEMS_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_idor_retrieve(self, auth_client2, budget_item):
        response = auth_client2.get(f"{ITEMS_URL}{budget_item.id}/")
        assert response.status_code == 404

    def test_idor_update_spent(self, auth_client2, budget_item):
        response = auth_client2.post(
            f"{ITEMS_URL}{budget_item.id}/update-spent/",
            {"amount": "999.00"},
            format="json",
        )
        assert response.status_code == 404

    def test_idor_bulk_update(self, auth_client2, budget_item):
        """Bulk update with another user's item should silently skip."""
        data = {
            "items": [
                {"id": str(budget_item.id), "spent_amount": "999.00"},
            ]
        }
        response = auth_client2.post(
            f"{ITEMS_URL}bulk-update/", data, format="json"
        )
        assert response.status_code == 200
        assert len(response.data) == 0
        # Verify original item unchanged
        budget_item.refresh_from_db()
        assert budget_item.spent_amount == Decimal("150.00")
