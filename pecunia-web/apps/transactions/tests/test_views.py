"""Tests for Transaction API views."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.utils import timezone

from apps.transactions.models import Transaction, TransactionCategory, RecurringTransaction


TRANSACTIONS_URL = "/api/v1/transactions/"
CATEGORIES_URL = "/api/v1/transactions/categories/"
RECURRING_URL = "/api/v1/transactions/recurring/"


@pytest.mark.django_db
class TestTransactionCategoryViews:
    """Tests for TransactionCategoryViewSet."""

    def test_list_unauthenticated(self, api_client):
        response = api_client.get(CATEGORIES_URL)
        assert response.status_code == 401

    def test_list_categories(self, auth_client, category, income_category):
        response = auth_client.get(CATEGORIES_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_create_category(self, auth_client):
        data = {"name": "Transport", "type": "expense", "color": "#ff0000"}
        response = auth_client.post(CATEGORIES_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Transport"
        assert response.data["type"] == "expense"

    def test_retrieve_category(self, auth_client, category):
        response = auth_client.get(f"{CATEGORIES_URL}{category.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "Groceries"

    def test_update_category(self, auth_client, category):
        data = {"name": "Food", "type": "expense"}
        response = auth_client.put(f"{CATEGORIES_URL}{category.id}/", data, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "Food"

    def test_partial_update_category(self, auth_client, category):
        response = auth_client.patch(
            f"{CATEGORIES_URL}{category.id}/", {"name": "Food"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["name"] == "Food"

    def test_delete_category(self, auth_client, category):
        response = auth_client.delete(f"{CATEGORIES_URL}{category.id}/")
        assert response.status_code == 204

    def test_transaction_count_field(self, auth_client, category, transaction):
        response = auth_client.get(f"{CATEGORIES_URL}{category.id}/")
        assert response.data["transaction_count"] == 1

    def test_search_categories(self, auth_client, category, income_category):
        response = auth_client.get(f"{CATEGORIES_URL}?search=Groc")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Groceries"

    def test_ordering(self, auth_client, category, income_category):
        response = auth_client.get(f"{CATEGORIES_URL}?ordering=name")
        assert response.status_code == 200
        names = [c["name"] for c in response.data["results"]]
        assert names == sorted(names)

    def test_idor_list(self, auth_client2, category):
        """User2 should not see user1's categories."""
        response = auth_client2.get(CATEGORIES_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_idor_retrieve(self, auth_client2, category):
        """User2 should not access user1's category."""
        response = auth_client2.get(f"{CATEGORIES_URL}{category.id}/")
        assert response.status_code == 404

    def test_idor_update(self, auth_client2, category):
        response = auth_client2.patch(
            f"{CATEGORIES_URL}{category.id}/", {"name": "Hacked"}, format="json"
        )
        assert response.status_code == 404

    def test_idor_delete(self, auth_client2, category):
        response = auth_client2.delete(f"{CATEGORIES_URL}{category.id}/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestTransactionViews:
    """Tests for TransactionViewSet."""

    def test_list_unauthenticated(self, api_client):
        response = api_client.get(TRANSACTIONS_URL)
        assert response.status_code == 401

    def test_list_transactions(self, auth_client, transaction, income_transaction):
        response = auth_client.get(TRANSACTIONS_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_create_transaction(self, auth_client, category):
        data = {
            "amount": "100.00",
            "type": "expense",
            "description": "Test purchase",
            "transaction_date": str(timezone.now().date()),
            "category": str(category.id),
        }
        response = auth_client.post(TRANSACTIONS_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["amount"] == "100.00"
        assert response.data["type"] == "expense"

    def test_create_transaction_without_category(self, auth_client):
        data = {
            "amount": "50.00",
            "type": "expense",
            "transaction_date": str(timezone.now().date()),
        }
        response = auth_client.post(TRANSACTIONS_URL, data, format="json")
        assert response.status_code == 201

    def test_retrieve_transaction(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}{transaction.id}/")
        assert response.status_code == 200
        assert response.data["amount"] == "42.50"
        assert response.data["description"] == "Weekly groceries"

    def test_update_transaction(self, auth_client, transaction, category):
        data = {
            "amount": "50.00",
            "type": "expense",
            "transaction_date": str(timezone.now().date()),
            "category": str(category.id),
        }
        response = auth_client.put(f"{TRANSACTIONS_URL}{transaction.id}/", data, format="json")
        assert response.status_code == 200
        assert response.data["amount"] == "50.00"

    def test_partial_update(self, auth_client, transaction):
        response = auth_client.patch(
            f"{TRANSACTIONS_URL}{transaction.id}/", {"amount": "99.99"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["amount"] == "99.99"

    def test_delete_transaction(self, auth_client, transaction):
        response = auth_client.delete(f"{TRANSACTIONS_URL}{transaction.id}/")
        assert response.status_code == 204

    def test_date_from_filter(self, auth_client, transaction):
        today = timezone.now().date()
        response = auth_client.get(
            f"{TRANSACTIONS_URL}?date_from={today}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_date_to_filter(self, auth_client, transaction):
        today = timezone.now().date()
        response = auth_client.get(
            f"{TRANSACTIONS_URL}?date_to={today}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_date_range_filter(self, auth_client, transaction):
        today = timezone.now().date()
        response = auth_client.get(
            f"{TRANSACTIONS_URL}?date_from={today}&date_to={today}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_date_range_excludes(self, auth_client, transaction):
        tomorrow = timezone.now().date() + timedelta(days=1)
        response = auth_client.get(
            f"{TRANSACTIONS_URL}?date_from={tomorrow}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_type_filter(self, auth_client, transaction, income_transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}?type=expense")
        assert response.status_code == 200
        for tx in response.data["results"]:
            assert tx["type"] == "expense"

    def test_category_filter(self, auth_client, transaction, category):
        response = auth_client.get(f"{TRANSACTIONS_URL}?category={category.id}")
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_search_description(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}?search=groceries")
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_search_merchant(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}?search=Carrefour")
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_ordering_amount(self, auth_client, transaction, income_transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}?ordering=amount")
        assert response.status_code == 200
        amounts = [Decimal(tx["amount"]) for tx in response.data["results"]]
        assert amounts == sorted(amounts)

    def test_ordering_amount_desc(self, auth_client, transaction, income_transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}?ordering=-amount")
        assert response.status_code == 200
        amounts = [Decimal(tx["amount"]) for tx in response.data["results"]]
        assert amounts == sorted(amounts, reverse=True)

    def test_list_uses_list_serializer(self, auth_client, transaction):
        """List endpoint uses TransactionListSerializer with limited fields."""
        response = auth_client.get(TRANSACTIONS_URL)
        result = response.data["results"][0]
        assert "category_color" in result
        assert "category_name" in result
        # List serializer should NOT have these full fields
        assert "tags" not in result
        assert "signed_amount" not in result

    def test_detail_uses_full_serializer(self, auth_client, transaction):
        """Detail endpoint uses TransactionSerializer with all fields."""
        response = auth_client.get(f"{TRANSACTIONS_URL}{transaction.id}/")
        assert "signed_amount" in response.data
        assert "tags" in response.data
        assert "notes" in response.data
        assert "category_name" in response.data

    def test_stats_default_period(self, auth_client, transaction, income_transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}stats/")
        assert response.status_code == 200
        assert "total_income" in response.data
        assert "total_expenses" in response.data
        assert "net_balance" in response.data
        assert "transaction_count" in response.data

    def test_stats_month(self, auth_client, transaction, income_transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}stats/?period=month")
        assert response.status_code == 200
        assert Decimal(response.data["total_expenses"]) >= Decimal("42.50")
        assert Decimal(response.data["total_income"]) >= Decimal("3000.00")

    def test_stats_week(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}stats/?period=week")
        assert response.status_code == 200
        assert response.data["transaction_count"] >= 1

    def test_stats_year(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}stats/?period=year")
        assert response.status_code == 200

    def test_stats_all(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}stats/?period=all")
        assert response.status_code == 200
        assert response.data["transaction_count"] >= 1

    def test_stats_net_balance(self, auth_client, transaction, income_transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}stats/?period=month")
        assert response.status_code == 200
        income = Decimal(response.data["total_income"])
        expenses = Decimal(response.data["total_expenses"])
        net = Decimal(response.data["net_balance"])
        assert net == income - expenses

    def test_by_category(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}by_category/")
        assert response.status_code == 200
        assert isinstance(response.data, list)
        if response.data:
            item = response.data[0]
            assert "category__name" in item
            assert "total" in item
            assert "count" in item

    def test_by_category_week(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}by_category/?period=week")
        assert response.status_code == 200

    def test_by_category_year(self, auth_client, transaction):
        response = auth_client.get(f"{TRANSACTIONS_URL}by_category/?period=year")
        assert response.status_code == 200

    def test_idor_list(self, auth_client2, transaction):
        response = auth_client2.get(TRANSACTIONS_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_idor_retrieve(self, auth_client2, transaction):
        response = auth_client2.get(f"{TRANSACTIONS_URL}{transaction.id}/")
        assert response.status_code == 404

    def test_idor_update(self, auth_client2, transaction):
        response = auth_client2.patch(
            f"{TRANSACTIONS_URL}{transaction.id}/", {"amount": "999.99"}, format="json"
        )
        assert response.status_code == 404

    def test_idor_delete(self, auth_client2, transaction):
        response = auth_client2.delete(f"{TRANSACTIONS_URL}{transaction.id}/")
        assert response.status_code == 404

    def test_idor_stats_isolation(self, auth_client2, transaction):
        """User2 should get empty stats even if user1 has transactions."""
        response = auth_client2.get(f"{TRANSACTIONS_URL}stats/")
        assert response.status_code == 200
        assert response.data["transaction_count"] == 0


@pytest.mark.django_db
class TestRecurringTransactionViews:
    """Tests for RecurringTransactionViewSet."""

    def test_list_unauthenticated(self, api_client):
        response = api_client.get(RECURRING_URL)
        assert response.status_code == 401

    def test_list(self, auth_client, recurring_transaction):
        response = auth_client.get(RECURRING_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_create(self, auth_client, category):
        data = {
            "name": "Rent",
            "amount": "1200.00",
            "type": "expense",
            "frequency": "monthly",
            "start_date": str(timezone.now().date()),
            "category": str(category.id),
        }
        response = auth_client.post(RECURRING_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Rent"
        assert response.data["next_occurrence"] == str(timezone.now().date())

    def test_retrieve(self, auth_client, recurring_transaction):
        response = auth_client.get(f"{RECURRING_URL}{recurring_transaction.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "Netflix"

    def test_update(self, auth_client, recurring_transaction, category):
        data = {
            "name": "Disney+",
            "amount": "12.99",
            "type": "expense",
            "frequency": "monthly",
            "start_date": str(timezone.now().date()),
            "category": str(category.id),
        }
        response = auth_client.put(
            f"{RECURRING_URL}{recurring_transaction.id}/", data, format="json"
        )
        assert response.status_code == 200
        assert response.data["name"] == "Disney+"

    def test_partial_update(self, auth_client, recurring_transaction):
        response = auth_client.patch(
            f"{RECURRING_URL}{recurring_transaction.id}/",
            {"name": "Updated Netflix"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["name"] == "Updated Netflix"

    def test_delete(self, auth_client, recurring_transaction):
        response = auth_client.delete(f"{RECURRING_URL}{recurring_transaction.id}/")
        assert response.status_code == 204

    def test_toggle_active_off(self, auth_client, recurring_transaction):
        assert recurring_transaction.is_active is True
        response = auth_client.post(
            f"{RECURRING_URL}{recurring_transaction.id}/toggle_active/"
        )
        assert response.status_code == 200
        assert response.data["is_active"] is False

    def test_toggle_active_back_on(self, auth_client, recurring_transaction):
        auth_client.post(
            f"{RECURRING_URL}{recurring_transaction.id}/toggle_active/"
        )
        response = auth_client.post(
            f"{RECURRING_URL}{recurring_transaction.id}/toggle_active/"
        )
        assert response.data["is_active"] is True

    def test_filter_by_type(self, auth_client, recurring_transaction):
        response = auth_client.get(f"{RECURRING_URL}?type=expense")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_type_no_match(self, auth_client, recurring_transaction):
        response = auth_client.get(f"{RECURRING_URL}?type=income")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_filter_by_frequency(self, auth_client, recurring_transaction):
        response = auth_client.get(f"{RECURRING_URL}?frequency=monthly")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_active(self, auth_client, recurring_transaction):
        response = auth_client.get(f"{RECURRING_URL}?is_active=true")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_search(self, auth_client, recurring_transaction):
        response = auth_client.get(f"{RECURRING_URL}?search=Netflix")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_idor_list(self, auth_client2, recurring_transaction):
        response = auth_client2.get(RECURRING_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_idor_retrieve(self, auth_client2, recurring_transaction):
        response = auth_client2.get(f"{RECURRING_URL}{recurring_transaction.id}/")
        assert response.status_code == 404

    def test_idor_toggle(self, auth_client2, recurring_transaction):
        response = auth_client2.post(
            f"{RECURRING_URL}{recurring_transaction.id}/toggle_active/"
        )
        assert response.status_code == 404
