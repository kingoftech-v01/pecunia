"""Tests for Transaction serializers."""
import pytest
from decimal import Decimal
from datetime import date

from rest_framework.test import APIRequestFactory

from apps.transactions.models import Transaction, TransactionCategory
from apps.transactions.serializers import (
    TransactionSerializer,
    TransactionListSerializer,
    TransactionCategorySerializer,
    RecurringTransactionSerializer,
    TransactionStatsSerializer,
)


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
class TestTransactionCategorySerializer:
    """Tests for TransactionCategorySerializer."""

    def test_create_sets_user(self, fake_request, user):
        data = {"name": "Transport", "type": "expense"}
        serializer = TransactionCategorySerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        obj = serializer.save()
        assert obj.user == user

    def test_transaction_count_zero(self, category, fake_request):
        serializer = TransactionCategorySerializer(
            category, context={"request": fake_request}
        )
        assert serializer.data["transaction_count"] == 0

    def test_transaction_count_with_data(self, category, transaction, fake_request):
        serializer = TransactionCategorySerializer(
            category, context={"request": fake_request}
        )
        assert serializer.data["transaction_count"] == 1

    def test_read_only_fields(self, category, fake_request):
        serializer = TransactionCategorySerializer(
            category, context={"request": fake_request}
        )
        data = serializer.data
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_all_fields_present(self, category, fake_request):
        serializer = TransactionCategorySerializer(
            category, context={"request": fake_request}
        )
        data = serializer.data
        expected_fields = {
            "id", "name", "type", "icon", "color",
            "is_default", "transaction_count", "created_at", "updated_at",
        }
        assert set(data.keys()) == expected_fields


@pytest.mark.django_db
class TestTransactionSerializer:
    """Tests for TransactionSerializer."""

    def test_create_sets_user(self, fake_request, user, category):
        data = {
            "amount": "100.00",
            "type": "expense",
            "transaction_date": str(date.today()),
            "category": str(category.id),
        }
        serializer = TransactionSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        tx = serializer.save()
        assert tx.user == user

    def test_signed_amount_expense(self, transaction, fake_request):
        serializer = TransactionSerializer(
            transaction, context={"request": fake_request}
        )
        assert Decimal(serializer.data["signed_amount"]) == Decimal("-42.50")

    def test_signed_amount_income(self, income_transaction, fake_request):
        serializer = TransactionSerializer(
            income_transaction, context={"request": fake_request}
        )
        assert Decimal(serializer.data["signed_amount"]) == Decimal("3000.00")

    def test_category_name(self, transaction, fake_request):
        serializer = TransactionSerializer(
            transaction, context={"request": fake_request}
        )
        assert serializer.data["category_name"] == "Groceries"

    def test_category_name_null(self, user, fake_request):
        tx = Transaction.objects.create(
            user=user,
            amount=Decimal("10.00"),
            type="expense",
            transaction_date=date.today(),
        )
        serializer = TransactionSerializer(tx, context={"request": fake_request})
        # When category is None, DRF's nested source omits the key
        assert serializer.data.get("category_name") is None

    def test_validate_category_idor(self, category, fake_request_user2):
        """User2 cannot use user1's category."""
        data = {
            "amount": "100.00",
            "type": "expense",
            "transaction_date": str(date.today()),
            "category": str(category.id),
        }
        serializer = TransactionSerializer(
            data=data, context={"request": fake_request_user2}
        )
        assert not serializer.is_valid()
        assert "category" in serializer.errors

    def test_validate_category_own(self, category, fake_request):
        """User can use their own category."""
        data = {
            "amount": "100.00",
            "type": "expense",
            "transaction_date": str(date.today()),
            "category": str(category.id),
        }
        serializer = TransactionSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors

    def test_validate_category_null_is_ok(self, fake_request):
        """Null category should pass validation."""
        data = {
            "amount": "100.00",
            "type": "expense",
            "transaction_date": str(date.today()),
        }
        serializer = TransactionSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors

    def test_validate_bank_account_idor(
        self, user2, bank_account, fake_request_user2
    ):
        """User2 cannot use user1's bank account."""
        data = {
            "amount": "100.00",
            "type": "expense",
            "transaction_date": str(date.today()),
            "bank_account": str(bank_account.id),
        }
        serializer = TransactionSerializer(
            data=data, context={"request": fake_request_user2}
        )
        assert not serializer.is_valid()
        assert "bank_account" in serializer.errors

    def test_read_only_fields(self):
        serializer = TransactionSerializer()
        ro = serializer.Meta.read_only_fields
        assert "id" in ro
        assert "ai_category_suggestion" in ro
        assert "ai_confidence" in ro
        assert "created_at" in ro
        assert "updated_at" in ro


@pytest.mark.django_db
class TestTransactionListSerializer:
    """Tests for TransactionListSerializer."""

    def test_fields(self, transaction):
        serializer = TransactionListSerializer(transaction)
        data = serializer.data
        assert "id" in data
        assert "amount" in data
        assert "type" in data
        assert "description" in data
        assert "merchant" in data
        assert "category_name" in data
        assert "category_color" in data
        assert "transaction_date" in data
        # Full serializer fields should be absent
        assert "tags" not in data
        assert "signed_amount" not in data
        assert "notes" not in data

    def test_category_name_and_color(self, transaction):
        serializer = TransactionListSerializer(transaction)
        assert serializer.data["category_name"] == "Groceries"
        assert serializer.data["category_color"] == "#22c55e"

    def test_no_category(self, user):
        tx = Transaction.objects.create(
            user=user,
            amount=Decimal("10.00"),
            type="expense",
            transaction_date=date.today(),
        )
        serializer = TransactionListSerializer(tx)
        # When category is None, DRF's nested source omits the key
        assert serializer.data.get("category_name") is None
        assert serializer.data.get("category_color") is None


@pytest.mark.django_db
class TestRecurringTransactionSerializer:
    """Tests for RecurringTransactionSerializer."""

    def test_create_sets_user_and_next_occurrence(self, fake_request, category):
        data = {
            "name": "Rent",
            "amount": "1200.00",
            "type": "expense",
            "frequency": "monthly",
            "start_date": str(date.today()),
            "category": str(category.id),
        }
        serializer = RecurringTransactionSerializer(
            data=data, context={"request": fake_request}
        )
        assert serializer.is_valid(), serializer.errors
        rt = serializer.save()
        assert rt.user == fake_request.user
        assert rt.next_occurrence == date.today()

    def test_category_name(self, recurring_transaction):
        serializer = RecurringTransactionSerializer(recurring_transaction)
        assert serializer.data["category_name"] == "Groceries"

    def test_read_only_next_occurrence(self):
        assert "next_occurrence" in RecurringTransactionSerializer.Meta.read_only_fields

    def test_read_only_id(self):
        assert "id" in RecurringTransactionSerializer.Meta.read_only_fields


class TestTransactionStatsSerializer:
    """Tests for TransactionStatsSerializer."""

    def test_serialization(self):
        data = {
            "total_income": Decimal("5000.00"),
            "total_expenses": Decimal("3000.00"),
            "net_balance": Decimal("2000.00"),
            "transaction_count": 10,
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 1, 31),
        }
        serializer = TransactionStatsSerializer(data)
        output = serializer.data
        assert output["total_income"] == "5000.00"
        assert output["total_expenses"] == "3000.00"
        assert output["net_balance"] == "2000.00"
        assert output["transaction_count"] == 10
