"""Tests for src/database/models/transaction.py — Transaction and TransactionCategory models."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from database.models.transaction import (
    Transaction, TransactionCategory, TransactionType,
)


class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_income_value(self):
        assert TransactionType.INCOME.value == "income"

    def test_expense_value(self):
        assert TransactionType.EXPENSE.value == "expense"

    def test_transfer_value(self):
        assert TransactionType.TRANSFER.value == "transfer"

    def test_is_str_enum(self):
        assert isinstance(TransactionType.INCOME, str)


class TestTransactionCategory:
    """Tests for TransactionCategory model."""

    def test_creation(self):
        cat = TransactionCategory(
            id=1, user_id=1, name="Food",
            type=TransactionType.EXPENSE,
        )
        assert cat.name == "Food"
        assert cat.type == TransactionType.EXPENSE

    def test_is_synced_false_when_no_server_id(self):
        cat = TransactionCategory(id=1, user_id=1, name="Test")
        assert cat.is_synced is False

    def test_is_synced_true_when_server_id_set(self):
        cat = TransactionCategory(id=1, user_id=1, name="Test", server_id=42)
        assert cat.is_synced is True

    def test_mark_as_synced(self):
        cat = TransactionCategory(id=1, user_id=1, name="Test")
        cat.mark_as_synced(99)
        assert cat.server_id == 99
        assert cat.is_synced is True

    def test_repr(self):
        cat = TransactionCategory(
            id=1, name="Food", type=TransactionType.EXPENSE,
        )
        repr_str = repr(cat)
        assert "Food" in repr_str
        assert "expense" in repr_str

    def test_with_icon_and_color(self):
        cat = TransactionCategory(
            id=1, user_id=1, name="Travel",
            type=TransactionType.EXPENSE,
            icon="plane", color="#0000FF",
        )
        assert cat.icon == "plane"
        assert cat.color == "#0000FF"


class TestTransaction:
    """Tests for Transaction model."""

    def test_creation_with_all_fields(self):
        txn = Transaction(
            id=1, user_id=1, category_id=1,
            amount=Decimal("125.50"), type=TransactionType.EXPENSE,
            description="Groceries", merchant="Store",
            transaction_date=datetime(2024, 1, 15),
        )
        assert txn.amount == Decimal("125.50")
        assert txn.type == TransactionType.EXPENSE
        assert txn.merchant == "Store"

    def test_default_is_synced_false(self):
        txn = Transaction(
            id=1, user_id=1,
            amount=Decimal("50"), type=TransactionType.INCOME,
        )
        assert txn.is_synced is False

    def test_mark_as_synced(self):
        txn = Transaction(
            id=1, user_id=1,
            amount=Decimal("50"), type=TransactionType.INCOME,
            is_synced=False,
        )
        txn.mark_as_synced(server_id=42)
        assert txn.server_id == 42
        assert txn.is_synced is True
        assert txn.updated_at is not None

    def test_mark_as_unsynced(self):
        txn = Transaction(
            id=1, user_id=1,
            amount=Decimal("50"), type=TransactionType.INCOME,
            is_synced=True, server_id=42,
        )
        txn.mark_as_unsynced()
        assert txn.is_synced is False
        assert txn.updated_at is not None

    def test_repr(self):
        txn = Transaction(
            id=1, amount=Decimal("100"),
            type=TransactionType.EXPENSE, is_synced=False,
        )
        repr_str = repr(txn)
        assert "100" in repr_str
        assert "expense" in repr_str

    def test_income_transaction(self):
        txn = Transaction(
            id=1, user_id=1,
            amount=Decimal("5000"), type=TransactionType.INCOME,
            description="Salary",
        )
        assert txn.type == TransactionType.INCOME
        assert txn.description == "Salary"

    def test_transfer_transaction(self):
        txn = Transaction(
            id=1, user_id=1,
            amount=Decimal("200"), type=TransactionType.TRANSFER,
        )
        assert txn.type == TransactionType.TRANSFER


class TestTransactionClassMethods:
    """Tests for Transaction class methods (mocked session)."""

    def test_get_by_server_id(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Transaction(id=1, server_id=42)

        result = Transaction.get_by_server_id(mock_session, 42)
        assert result is not None
        assert result.server_id == 42

    def test_get_unsynced(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [
            Transaction(id=1, is_synced=False),
            Transaction(id=2, is_synced=False),
        ]

        result = Transaction.get_unsynced(mock_session, user_id=1)
        assert len(result) == 2

    def test_get_synced(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [Transaction(id=1, is_synced=True)]

        result = Transaction.get_synced(mock_session, user_id=1)
        assert len(result) == 1

    def test_get_by_date_range(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = Transaction.get_by_date_range(
            mock_session, user_id=1,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )
        assert result == []

    def test_get_by_date_range_with_type(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = Transaction.get_by_date_range(
            mock_session, user_id=1,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            transaction_type=TransactionType.INCOME,
        )
        assert result == []

    def test_get_by_category(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = Transaction.get_by_category(mock_session, user_id=1, category_id=5)
        assert result == []

    def test_get_pending_sync_count(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5

        count = Transaction.get_pending_sync_count(mock_session, user_id=1)
        assert count == 5

    def test_get_all_for_user(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.limit.return_value = mock_query

        result = Transaction.get_all_for_user(mock_session, user_id=1)
        assert result == []

    def test_get_all_for_user_with_limit(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = Transaction.get_all_for_user(mock_session, user_id=1, limit=10)
        assert result == []

    def test_get_by_merchant(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = Transaction.get_by_merchant(mock_session, user_id=1, merchant="Store")
        assert result == []


class TestTransactionCategoryClassMethods:
    """Tests for TransactionCategory class methods."""

    def test_get_by_server_id(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = TransactionCategory(id=1, server_id=10)

        result = TransactionCategory.get_by_server_id(mock_session, 10)
        assert result.server_id == 10

    def test_get_unsynced(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = TransactionCategory.get_unsynced(mock_session, user_id=1)
        assert result == []

    def test_get_by_type(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = TransactionCategory.get_by_type(
            mock_session, user_id=1, category_type=TransactionType.EXPENSE,
        )
        assert result == []

    def test_get_all_for_user(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = TransactionCategory.get_all_for_user(mock_session, user_id=1)
        assert result == []
