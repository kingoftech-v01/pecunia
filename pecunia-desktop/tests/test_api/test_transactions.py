"""Tests for src/api/transactions.py — Transactions API client."""

from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

import pytest

from api.client import APIResponse, APIError
from api.transactions import (
    Transaction, TransactionSummary, TransactionCategory, TransactionFilter,
    PaginatedTransactions, TransactionsAPI, TransactionSortField, SortOrder,
    RecurringTransaction, RecurringTransactionCreate, RecurringTransactionsAPI,
    RecurrenceFrequency, CategoryCreate,
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
    return TransactionsAPI(mock_client)


@pytest.fixture
def recurring_api(mock_client):
    return RecurringTransactionsAPI(mock_client)


class TestTransaction:
    """Tests for Transaction dataclass."""

    def test_from_dict_full(self):
        data = {
            "id": "t1", "amount": "125.50", "description": "Groceries",
            "date": "2024-01-15", "type": "expense", "category": "food",
            "account_id": "a1", "merchant_name": "Store",
            "is_pending": True, "tags": ["weekly"],
        }
        txn = Transaction.from_dict(data)
        assert txn.id == "t1"
        assert txn.amount == Decimal("125.50")
        assert txn.description == "Groceries"
        assert txn.is_pending is True
        assert "weekly" in txn.tags

    def test_from_dict_minimal(self):
        txn = Transaction.from_dict({"id": "t2", "amount": 0, "description": "", "date": ""})
        assert txn.id == "t2"
        assert txn.amount == Decimal("0")
        assert txn.tags == []

    def test_to_dict(self):
        txn = Transaction(id="t1", amount=Decimal("50"), description="Test",
                          date="2024-01-01", type="expense")
        d = txn.to_dict()
        assert d["amount"] == Decimal("50")
        assert d["description"] == "Test"
        assert "id" not in d  # ID not in to_dict


class TestTransactionSummary:
    """Tests for TransactionSummary."""

    def test_from_dict(self):
        data = {
            "total_income": 5000, "total_expenses": 3000,
            "net_amount": 2000, "transaction_count": 42,
            "categories": {"food": 500, "rent": 1200},
        }
        summary = TransactionSummary.from_dict(data)
        assert summary.total_income == 5000.0
        assert summary.total_expenses == 3000.0
        assert summary.transaction_count == 42
        assert summary.categories["food"] == 500


class TestTransactionCategory:
    """Tests for TransactionCategory."""

    def test_from_dict(self):
        data = {"id": "c1", "name": "Food", "icon": "utensils", "is_income": False}
        cat = TransactionCategory.from_dict(data)
        assert cat.name == "Food"
        assert cat.is_income is False


class TestTransactionFilter:
    """Tests for TransactionFilter."""

    def test_empty_filter(self):
        f = TransactionFilter()
        assert f.to_params() == {}

    def test_full_filter(self):
        f = TransactionFilter(
            start_date="2024-01-01", end_date="2024-12-31",
            min_amount=10, max_amount=1000,
            type="expense", category="food",
            search="grocery", tags=["weekly", "food"],
            is_pending=False,
        )
        params = f.to_params()
        assert params["start_date"] == "2024-01-01"
        assert params["min_amount"] == 10
        assert "weekly" in params["tags"]
        assert params["is_pending"] == "false"

    def test_partial_filter(self):
        f = TransactionFilter(start_date="2024-01-01", type="income")
        params = f.to_params()
        assert "start_date" in params
        assert "type" in params
        assert "end_date" not in params


class TestPaginatedTransactions:
    """Tests for PaginatedTransactions."""

    def test_from_dict(self):
        data = {
            "items": [
                {"id": "t1", "amount": 100, "description": "A", "date": "2024-01-01", "type": "expense"},
                {"id": "t2", "amount": 200, "description": "B", "date": "2024-01-02", "type": "income"},
            ],
            "total": 50, "page": 1, "page_size": 25,
        }
        result = PaginatedTransactions.from_dict(data)
        assert len(result.items) == 2
        assert result.total == 50
        assert result.total_pages == 2

    def test_from_dict_single_page(self):
        data = {"items": [], "total": 0, "page_size": 50}
        result = PaginatedTransactions.from_dict(data)
        assert result.total_pages == 1


class TestTransactionsAPI:
    """Tests for TransactionsAPI methods."""

    async def test_list_transactions(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"items": [{"id": "t1", "amount": 100, "description": "A", "date": "2024-01-01", "type": "expense"}],
                  "total": 1, "page": 1, "page_size": 50},
        )
        result = await api.list()
        assert len(result.items) == 1
        assert result.items[0].id == "t1"

    async def test_list_with_filter(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"items": [], "total": 0, "page": 1, "page_size": 50},
        )
        f = TransactionFilter(start_date="2024-01-01")
        await api.list(filter=f)
        call_kwargs = mock_client.get.call_args
        assert "start_date" in call_kwargs[1]["params"]

    async def test_get_transaction(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "t1", "amount": 50, "description": "Test", "date": "2024-01-01", "type": "expense"},
        )
        txn = await api.get("t1")
        assert txn.id == "t1"

    async def test_get_transaction_not_found(self, api, mock_client):
        mock_client.get.return_value = APIResponse(success=False, status_code=404, data={})
        with pytest.raises(APIError):
            await api.get("nonexistent")

    async def test_create_transaction(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=201,
            data={"id": "new1", "amount": 100, "description": "New", "date": "2024-01-01", "type": "expense"},
        )
        txn = Transaction(id="", amount=Decimal("100"), description="New", date="2024-01-01", type="expense")
        created = await api.create(txn)
        assert created.id == "new1"

    async def test_update_transaction(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "t1", "amount": 200, "description": "Updated", "date": "2024-01-01", "type": "expense"},
        )
        updated = await api.update("t1", {"amount": 200})
        assert updated.amount == Decimal("200")

    async def test_delete_transaction(self, api, mock_client):
        mock_client.delete.return_value = APIResponse(success=True, status_code=200, data={})
        result = await api.delete("t1")
        assert result is True

    async def test_bulk_delete(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=200, data={"deleted_count": 3},
        )
        count = await api.bulk_delete(["t1", "t2", "t3"])
        assert count == 3

    async def test_get_summary(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"total_income": 5000, "total_expenses": 3000, "net_amount": 2000, "transaction_count": 10},
        )
        summary = await api.get_summary(start_date="2024-01-01")
        assert summary.total_income == 5000

    async def test_get_categories(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data=[{"id": "c1", "name": "Food"}, {"id": "c2", "name": "Transport"}],
        )
        cats = await api.get_categories()
        assert len(cats) == 2

    async def test_categorize(self, api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "t1", "amount": 50, "description": "Test", "date": "2024-01-01",
                  "type": "expense", "category": "food"},
        )
        txn = await api.categorize("t1", "food")
        assert txn.category == "food"

    async def test_search(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"items": [], "total": 0, "page": 1, "page_size": 50},
        )
        result = await api.search("grocery")
        assert result.total == 0

    async def test_import_transactions(self, api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=200,
            data={"imported": 5, "duplicates": 2},
        )
        result = await api.import_transactions(b"csv,data", "csv")
        assert result["imported"] == 5

    async def test_export_transactions(self, api, mock_client):
        import base64
        encoded = base64.b64encode(b"csv,content").decode()
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"file_data": encoded},
        )
        result = await api.export_transactions("csv")
        assert result == b"csv,content"

    async def test_get_by_date_range(self, api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"items": [{"id": "t1", "amount": 50, "description": "A", "date": "2024-01-01", "type": "expense"}],
                  "total": 1, "page": 1, "page_size": 100, "total_pages": 1},
        )
        txns = await api.get_by_date_range("2024-01-01", "2024-12-31")
        assert len(txns) == 1


class TestRecurringTransaction:
    """Tests for RecurringTransaction."""

    def test_from_dict(self):
        data = {"id": "r1", "amount": "100", "description": "Rent",
                "type": "expense", "frequency": "monthly", "start_date": "2024-01-01"}
        rt = RecurringTransaction.from_dict(data)
        assert rt.id == "r1"
        assert rt.amount == Decimal("100")
        assert rt.frequency == "monthly"

    def test_to_dict(self):
        rt = RecurringTransaction(id="r1", amount=Decimal("100"), description="Rent",
                                   type="expense", frequency="monthly", start_date="2024-01-01")
        d = rt.to_dict()
        assert d["frequency"] == "monthly"


class TestRecurringTransactionsAPI:
    """Tests for RecurringTransactionsAPI."""

    async def test_list_recurring(self, recurring_api, mock_client):
        mock_client.get.return_value = APIResponse(
            success=True, status_code=200,
            data={"items": [{"id": "r1", "amount": 100, "description": "Rent",
                             "type": "expense", "frequency": "monthly", "start_date": "2024-01-01"}]},
        )
        result = await recurring_api.list()
        assert len(result) == 1

    async def test_create_recurring(self, recurring_api, mock_client):
        mock_client.post.return_value = APIResponse(
            success=True, status_code=201,
            data={"id": "r2", "amount": 50, "description": "Sub",
                  "type": "expense", "frequency": "monthly", "start_date": "2024-01-01"},
        )
        create_data = RecurringTransactionCreate(
            amount=Decimal("50"), description="Sub",
            type="expense", frequency="monthly", start_date="2024-01-01",
        )
        result = await recurring_api.create(create_data)
        assert result.id == "r2"

    async def test_toggle_active(self, recurring_api, mock_client):
        mock_client.patch.return_value = APIResponse(
            success=True, status_code=200,
            data={"id": "r1", "amount": 100, "description": "Rent",
                  "type": "expense", "frequency": "monthly", "start_date": "2024-01-01",
                  "is_active": False},
        )
        result = await recurring_api.toggle_active("r1", False)
        assert result.is_active is False

    async def test_delete_recurring(self, recurring_api, mock_client):
        mock_client.delete.return_value = APIResponse(success=True, status_code=200, data={})
        result = await recurring_api.delete("r1")
        assert result is True


class TestCategoryCreate:
    """Tests for CategoryCreate."""

    def test_to_dict(self):
        cat = CategoryCreate(name="Custom", icon="star", color="#FF0000", is_income=True)
        d = cat.to_dict()
        assert d["name"] == "Custom"
        assert d["is_income"] is True
