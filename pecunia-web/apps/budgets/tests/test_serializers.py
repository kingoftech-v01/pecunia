"""Tests for Budget serializers."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from rest_framework.test import APIRequestFactory

from apps.budgets.models import Budget, BudgetItem
from apps.budgets.serializers import (
    BudgetSerializer,
    BudgetListSerializer,
    BudgetWithItemsSerializer,
    BudgetItemSerializer,
    BudgetItemCreateSerializer,
    BudgetStatsSerializer,
    BudgetProgressSerializer,
    CategoryBudgetSummarySerializer,
)
from apps.transactions.models import TransactionCategory


@pytest.fixture
def api_rf():
    return APIRequestFactory()


@pytest.fixture
def fake_request(api_rf, user):
    request = api_rf.get("/")
    request.user = user
    return request


@pytest.fixture
def fake_request_user2(api_rf, user2):
    request = api_rf.get("/")
    request.user = user2
    return request


@pytest.mark.django_db
class TestBudgetItemSerializer:
    """Tests for BudgetItemSerializer."""

    def test_computed_fields(self, budget_item):
        serializer = BudgetItemSerializer(budget_item)
        data = serializer.data
        assert "remaining_amount" in data
        assert "progress_percentage" in data
        assert "is_over_budget" in data
        assert "display_name" in data
        assert "category_name" in data
        assert "category_color" in data

    def test_remaining_amount(self, budget_item):
        serializer = BudgetItemSerializer(budget_item)
        expected = str(budget_item.planned_amount - budget_item.spent_amount)
        assert serializer.data["remaining_amount"] == expected

    def test_validate_budget_idor(self, budget, fake_request_user2):
        """User2 cannot create item for user1's budget."""
        data = {
            "budget": str(budget.id),
            "planned_amount": "100.00",
        }
        serializer = BudgetItemSerializer(
            data=data, context={"request": fake_request_user2}
        )
        assert not serializer.is_valid()
        assert "budget" in serializer.errors

    def test_validate_budget_own(self, budget, fake_request, category):
        """User can create item for their own budget."""
        cat2 = TransactionCategory.objects.create(
            user=budget.user, name="New Cat", type="expense"
        )
        data = {
            "budget": str(budget.id),
            "category": str(cat2.id),
            "planned_amount": "100.00",
        }
        serializer = BudgetItemSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors

    def test_read_only_fields(self):
        ro = BudgetItemSerializer.Meta.read_only_fields
        assert "id" in ro
        assert "created_at" in ro
        assert "updated_at" in ro


@pytest.mark.django_db
class TestBudgetItemCreateSerializer:
    """Tests for BudgetItemCreateSerializer."""

    def test_fields(self):
        fields = BudgetItemCreateSerializer.Meta.fields
        assert "category" in fields
        assert "name" in fields
        assert "planned_amount" in fields
        assert "notes" in fields

    def test_valid_data(self, category):
        data = {
            "category": str(category.id),
            "name": "Groceries",
            "planned_amount": "500.00",
        }
        serializer = BudgetItemCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestBudgetSerializer:
    """Tests for BudgetSerializer."""

    def test_create_sets_user(self, fake_request):
        data = {
            "name": "Test Budget",
            "period_type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
        }
        serializer = BudgetSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        budget = serializer.save()
        assert budget.user == fake_request.user

    def test_computed_fields(self, budget, fake_request):
        serializer = BudgetSerializer(budget, context={"request": fake_request})
        data = serializer.data
        assert "remaining_amount" in data
        assert "progress_percentage" in data
        assert "is_over_budget" in data
        assert "is_near_limit" in data
        assert "items" in data
        assert "item_count" in data

    def test_item_count_zero(self, budget, fake_request):
        serializer = BudgetSerializer(budget, context={"request": fake_request})
        assert serializer.data["item_count"] == 0

    def test_item_count_with_items(self, budget, budget_item, fake_request):
        serializer = BudgetSerializer(budget, context={"request": fake_request})
        assert serializer.data["item_count"] == 1

    def test_read_only_fields(self):
        ro = BudgetSerializer.Meta.read_only_fields
        assert "id" in ro
        assert "total_planned_amount" in ro
        assert "total_spent_amount" in ro
        assert "created_at" in ro
        assert "updated_at" in ro


@pytest.mark.django_db
class TestBudgetListSerializer:
    """Tests for BudgetListSerializer."""

    def test_fields(self, budget):
        serializer = BudgetListSerializer(budget)
        data = serializer.data
        assert "id" in data
        assert "name" in data
        assert "period_type" in data
        assert "remaining_amount" in data
        assert "progress_percentage" in data
        assert "is_over_budget" in data
        assert "item_count" in data
        # Should NOT have detailed fields
        assert "items" not in data
        assert "description" not in data

    def test_item_count(self, budget, budget_item):
        serializer = BudgetListSerializer(budget)
        assert serializer.data["item_count"] == 1


@pytest.mark.django_db
class TestBudgetWithItemsSerializer:
    """Tests for BudgetWithItemsSerializer."""

    def test_create_without_items(self, fake_request):
        data = {
            "name": "No Items",
            "period_type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
        }
        serializer = BudgetWithItemsSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        budget = serializer.save()
        assert budget.items.count() == 0

    def test_create_with_items(self, fake_request, category):
        data = {
            "name": "With Items",
            "period_type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
            "items": [
                {
                    "category": str(category.id),
                    "name": "Groceries",
                    "planned_amount": "500.00",
                },
            ],
        }
        serializer = BudgetWithItemsSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        budget = serializer.save()
        assert budget.items.count() == 1

    def test_update_replaces_items(self, fake_request, budget, budget_item, category):
        cat2 = TransactionCategory.objects.create(
            user=budget.user, name="Transport", type="expense"
        )
        data = {
            "name": budget.name,
            "period_type": budget.period_type,
            "start_date": str(budget.start_date),
            "end_date": str(budget.end_date),
            "items": [
                {
                    "category": str(cat2.id),
                    "name": "Transport",
                    "planned_amount": "200.00",
                },
            ],
        }
        serializer = BudgetWithItemsSerializer(
            budget, data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.items.count() == 1
        assert updated.items.first().name == "Transport"

    def test_update_without_items_key_preserves(self, fake_request, budget, budget_item):
        """When items key is not provided, existing items are preserved."""
        data = {
            "name": "Updated Name",
            "period_type": budget.period_type,
            "start_date": str(budget.start_date),
            "end_date": str(budget.end_date),
        }
        serializer = BudgetWithItemsSerializer(
            budget, data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.name == "Updated Name"
        assert updated.items.count() == 1

    def test_computed_fields(self, budget, fake_request):
        serializer = BudgetWithItemsSerializer(
            budget, context={"request": fake_request}
        )
        data = serializer.data
        assert "remaining_amount" in data
        assert "progress_percentage" in data


class TestBudgetStatsSerializer:
    """Tests for BudgetStatsSerializer."""

    def test_serialization(self):
        data = {
            "total_budgets": 5,
            "active_budgets": 3,
            "total_planned": Decimal("10000.00"),
            "total_spent": Decimal("5000.00"),
            "total_remaining": Decimal("5000.00"),
            "overall_progress": Decimal("50.00"),
            "budgets_over_limit": 1,
            "budgets_near_limit": 2,
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 1, 31),
        }
        serializer = BudgetStatsSerializer(data)
        output = serializer.data
        assert output["total_budgets"] == 5
        assert output["total_planned"] == "10000.00"

    def test_null_period_start(self):
        data = {
            "total_budgets": 0,
            "active_budgets": 0,
            "total_planned": Decimal("0"),
            "total_spent": Decimal("0"),
            "total_remaining": Decimal("0"),
            "overall_progress": Decimal("0"),
            "budgets_over_limit": 0,
            "budgets_near_limit": 0,
            "period_start": None,
            "period_end": date(2026, 1, 31),
        }
        serializer = BudgetStatsSerializer(data)
        assert serializer.data["period_start"] is None


class TestCategoryBudgetSummarySerializer:
    """Tests for CategoryBudgetSummarySerializer."""

    def test_serialization(self):
        import uuid
        data = {
            "category_id": uuid.uuid4(),
            "category_name": "Groceries",
            "category_color": "#22c55e",
            "planned_amount": Decimal("500.00"),
            "spent_amount": Decimal("300.00"),
            "remaining_amount": Decimal("200.00"),
            "progress_percentage": Decimal("60.00"),
            "is_over_budget": False,
        }
        serializer = CategoryBudgetSummarySerializer(data)
        output = serializer.data
        assert output["category_name"] == "Groceries"
        assert output["is_over_budget"] is False

    def test_null_category_id(self):
        data = {
            "category_id": None,
            "category_name": "Uncategorized",
            "category_color": "#6366f1",
            "planned_amount": Decimal("100.00"),
            "spent_amount": Decimal("50.00"),
            "remaining_amount": Decimal("50.00"),
            "progress_percentage": Decimal("50.00"),
            "is_over_budget": False,
        }
        serializer = CategoryBudgetSummarySerializer(data)
        assert serializer.data["category_id"] is None
