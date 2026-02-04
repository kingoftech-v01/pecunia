"""
Transactions API client for Pecunia Desktop.

Handles all transaction-related API operations including CRUD,
filtering, categorization, and import/export functionality.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import Endpoints, TransactionType
from .client import APIClient, APIResponse, APIError

logger = logging.getLogger(__name__)


class TransactionSortField(Enum):
    """Fields available for sorting transactions."""
    DATE = "date"
    AMOUNT = "amount"
    DESCRIPTION = "description"
    CATEGORY = "category"
    CREATED_AT = "created_at"


class SortOrder(Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class Transaction:
    """Represents a financial transaction."""
    id: str
    amount: Decimal
    description: str
    date: str
    type: str
    category: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    merchant_name: Optional[str] = None
    notes: Optional[str] = None
    is_pending: bool = False
    tags: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    plaid_transaction_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create Transaction from dictionary."""
        return cls(
            id=data.get('id', ''),
            amount=Decimal(str(data.get('amount', 0))),
            description=data.get('description', ''),
            date=data.get('date', ''),
            type=data.get('type', TransactionType.EXPENSE),
            category=data.get('category'),
            account_id=data.get('account_id'),
            account_name=data.get('account_name'),
            merchant_name=data.get('merchant_name'),
            notes=data.get('notes'),
            is_pending=data.get('is_pending', False),
            tags=data.get('tags', []),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            plaid_transaction_id=data.get('plaid_transaction_id'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            'amount': self.amount,
            'description': self.description,
            'date': self.date,
            'type': self.type,
            'category': self.category,
            'account_id': self.account_id,
            'merchant_name': self.merchant_name,
            'notes': self.notes,
            'is_pending': self.is_pending,
            'tags': self.tags,
        }


@dataclass
class TransactionSummary:
    """Summary statistics for transactions."""
    total_income: float = 0.0
    total_expenses: float = 0.0
    net_amount: Decimal = 0.0
    transaction_count: int = 0
    categories: Dict[str, float] = field(default_factory=dict)
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionSummary':
        """Create TransactionSummary from dictionary."""
        return cls(
            total_income=float(data.get('total_income', 0)),
            total_expenses=float(data.get('total_expenses', 0)),
            net_amount=float(data.get('net_amount', 0)),
            transaction_count=int(data.get('transaction_count', 0)),
            categories=data.get('categories', {}),
            period_start=data.get('period_start'),
            period_end=data.get('period_end'),
        )


@dataclass
class TransactionCategory:
    """Represents a transaction category."""
    id: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_income: bool = False
    is_system: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionCategory':
        """Create TransactionCategory from dictionary."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            icon=data.get('icon'),
            color=data.get('color'),
            parent_id=data.get('parent_id'),
            is_income=data.get('is_income', False),
            is_system=data.get('is_system', False),
        )


@dataclass
class PaginatedTransactions:
    """Paginated list of transactions."""
    items: List[Transaction]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaginatedTransactions':
        """Create PaginatedTransactions from dictionary."""
        items = [Transaction.from_dict(t) for t in data.get('items', [])]
        total = data.get('total', len(items))
        page_size = data.get('page_size', data.get('limit', 50))
        page = data.get('page', 1)
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@dataclass
class TransactionFilter:
    """Filter parameters for transaction queries."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    type: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    is_pending: Optional[bool] = None

    def to_params(self) -> Dict[str, Any]:
        """Convert to query parameters dictionary."""
        params = {}
        if self.start_date:
            params['start_date'] = self.start_date
        if self.end_date:
            params['end_date'] = self.end_date
        if self.min_amount is not None:
            params['min_amount'] = self.min_amount
        if self.max_amount is not None:
            params['max_amount'] = self.max_amount
        if self.type:
            params['type'] = self.type
        if self.category:
            params['category'] = self.category
        if self.account_id:
            params['account_id'] = self.account_id
        if self.search:
            params['search'] = self.search
        if self.tags:
            params['tags'] = ','.join(self.tags)
        if self.is_pending is not None:
            params['is_pending'] = str(self.is_pending).lower()
        return params


class TransactionsAPI:
    """
    API client for transaction operations.

    Provides methods for creating, reading, updating, and deleting
    transactions, as well as filtering, summarizing, and importing/exporting.
    """

    def __init__(self, api_client: APIClient):
        """
        Initialize the transactions API client.

        Args:
            api_client: The base API client instance.
        """
        self._client = api_client

    async def list(
        self,
        filter: Optional[TransactionFilter] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: TransactionSortField = TransactionSortField.DATE,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> PaginatedTransactions:
        """
        List transactions with optional filtering and pagination.

        Args:
            filter: Optional filter parameters.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            sort_by: Field to sort by.
            sort_order: Sort order (asc/desc).

        Returns:
            Paginated list of transactions.
        """
        params = {
            'page': page,
            'page_size': page_size,
            'sort_by': sort_by.value,
            'sort_order': sort_order.value,
        }

        if filter:
            params.update(filter.to_params())

        response = await self._client.get(Endpoints.TRANSACTIONS, params=params)

        if not response.is_ok:
            raise APIError("Failed to fetch transactions", response.status_code, response)

        return PaginatedTransactions.from_dict(response.data)

    async def get(self, transaction_id: str) -> Transaction:
        """
        Get a single transaction by ID.

        Args:
            transaction_id: The transaction ID.

        Returns:
            Transaction object.

        Raises:
            APIError: If transaction not found or request fails.
        """
        endpoint = Endpoints.TRANSACTIONS_BY_ID.format(id=transaction_id)
        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Transaction not found", response.status_code, response)

        return Transaction.from_dict(response.data)

    async def create(self, transaction: Transaction) -> Transaction:
        """
        Create a new transaction.

        Args:
            transaction: Transaction data to create.

        Returns:
            Created transaction with server-assigned ID.

        Raises:
            APIError: If creation fails.
        """
        response = await self._client.post(
            Endpoints.TRANSACTIONS,
            data=transaction.to_dict(),
        )

        if not response.is_ok:
            raise APIError("Failed to create transaction", response.status_code, response)

        return Transaction.from_dict(response.data)

    async def update(self, transaction_id: str, updates: Dict[str, Any]) -> Transaction:
        """
        Update an existing transaction.

        Args:
            transaction_id: The transaction ID to update.
            updates: Dictionary of fields to update.

        Returns:
            Updated transaction.

        Raises:
            APIError: If update fails.
        """
        endpoint = Endpoints.TRANSACTIONS_BY_ID.format(id=transaction_id)
        response = await self._client.patch(endpoint, data=updates)

        if not response.is_ok:
            raise APIError("Failed to update transaction", response.status_code, response)

        return Transaction.from_dict(response.data)

    async def delete(self, transaction_id: str) -> bool:
        """
        Delete a transaction.

        Args:
            transaction_id: The transaction ID to delete.

        Returns:
            True if deletion was successful.

        Raises:
            APIError: If deletion fails.
        """
        endpoint = Endpoints.TRANSACTIONS_BY_ID.format(id=transaction_id)
        response = await self._client.delete(endpoint)

        if not response.is_ok:
            raise APIError("Failed to delete transaction", response.status_code, response)

        return True

    async def bulk_delete(self, transaction_ids: List[str]) -> int:
        """
        Delete multiple transactions.

        Args:
            transaction_ids: List of transaction IDs to delete.

        Returns:
            Number of transactions deleted.
        """
        response = await self._client.post(
            f"{Endpoints.TRANSACTIONS}/bulk-delete",
            data={'ids': transaction_ids},
        )

        if not response.is_ok:
            raise APIError("Failed to delete transactions", response.status_code, response)

        return response.data.get('deleted_count', 0)

    async def get_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> TransactionSummary:
        """
        Get transaction summary/statistics.

        Args:
            start_date: Start date for summary period (ISO format).
            end_date: End date for summary period (ISO format).
            account_id: Optional account ID to filter by.

        Returns:
            TransactionSummary object.
        """
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if account_id:
            params['account_id'] = account_id

        response = await self._client.get(Endpoints.TRANSACTIONS_SUMMARY, params=params)

        if not response.is_ok:
            raise APIError("Failed to fetch summary", response.status_code, response)

        return TransactionSummary.from_dict(response.data)

    async def get_categories(self) -> List[TransactionCategory]:
        """
        Get all available transaction categories.

        Returns:
            List of TransactionCategory objects.
        """
        response = await self._client.get(Endpoints.TRANSACTIONS_CATEGORIES)

        if not response.is_ok:
            raise APIError("Failed to fetch categories", response.status_code, response)

        return [TransactionCategory.from_dict(c) for c in response.data]

    async def categorize(self, transaction_id: str, category: str) -> Transaction:
        """
        Set or update the category for a transaction.

        Args:
            transaction_id: The transaction ID.
            category: The category to assign.

        Returns:
            Updated transaction.
        """
        return await self.update(transaction_id, {'category': category})

    async def bulk_categorize(self, transaction_ids: List[str], category: str) -> int:
        """
        Set category for multiple transactions.

        Args:
            transaction_ids: List of transaction IDs.
            category: The category to assign.

        Returns:
            Number of transactions updated.
        """
        response = await self._client.post(
            f"{Endpoints.TRANSACTIONS}/bulk-categorize",
            data={'ids': transaction_ids, 'category': category},
        )

        if not response.is_ok:
            raise APIError("Failed to categorize transactions", response.status_code, response)

        return response.data.get('updated_count', 0)

    async def import_transactions(
        self,
        file_data: bytes,
        file_type: str = 'csv',
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import transactions from a file.

        Args:
            file_data: The file content as bytes.
            file_type: File type (csv, ofx, qfx).
            account_id: Optional account to import into.

        Returns:
            Import result with counts and any errors.
        """
        # Note: This would typically be a multipart form request
        # For simplicity, assuming base64 encoding
        import base64
        encoded_data = base64.b64encode(file_data).decode('utf-8')

        response = await self._client.post(
            Endpoints.TRANSACTIONS_IMPORT,
            data={
                'file_data': encoded_data,
                'file_type': file_type,
                'account_id': account_id,
            },
        )

        if not response.is_ok:
            raise APIError("Failed to import transactions", response.status_code, response)

        return response.data

    async def export_transactions(
        self,
        format: str = 'csv',
        filter: Optional[TransactionFilter] = None,
    ) -> bytes:
        """
        Export transactions to a file.

        Args:
            format: Export format (csv, json, xlsx).
            filter: Optional filter for transactions to export.

        Returns:
            File content as bytes.
        """
        params = {'format': format}
        if filter:
            params.update(filter.to_params())

        response = await self._client.get(Endpoints.TRANSACTIONS_EXPORT, params=params)

        if not response.is_ok:
            raise APIError("Failed to export transactions", response.status_code, response)

        # Response data should be base64 encoded file content
        if isinstance(response.data, dict) and 'file_data' in response.data:
            import base64
            return base64.b64decode(response.data['file_data'])

        return response.data if isinstance(response.data, bytes) else str(response.data).encode()

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedTransactions:
        """
        Search transactions by description, merchant, or notes.

        Args:
            query: Search query string.
            page: Page number.
            page_size: Items per page.

        Returns:
            Paginated search results.
        """
        filter = TransactionFilter(search=query)
        return await self.list(filter=filter, page=page, page_size=page_size)

    async def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        account_id: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Get all transactions within a date range.

        Args:
            start_date: Start date (ISO format).
            end_date: End date (ISO format).
            account_id: Optional account filter.

        Returns:
            List of transactions in the date range.
        """
        filter = TransactionFilter(
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
        )

        # Fetch all pages
        all_transactions = []
        page = 1
        while True:
            result = await self.list(filter=filter, page=page, page_size=100)
            all_transactions.extend(result.items)
            if page >= result.total_pages:
                break
            page += 1

        return all_transactions

    async def get_recurring(self) -> List[Transaction]:
        """
        Get identified recurring transactions.

        Returns:
            List of recurring transactions.
        """
        response = await self._client.get(f"{Endpoints.TRANSACTIONS}/recurring")

        if not response.is_ok:
            raise APIError("Failed to fetch recurring transactions", response.status_code, response)

        return [Transaction.from_dict(t) for t in response.data.get('items', response.data)]

    async def get_by_category(
        self,
        category_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedTransactions:
        """
        Get all transactions for a specific category.

        Args:
            category_id: The category ID to filter by.
            start_date: Optional start date filter (ISO format).
            end_date: Optional end date filter (ISO format).
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Paginated list of transactions in the category.
        """
        params = {
            'page': page,
            'page_size': page_size,
        }
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        endpoint = f"{Endpoints.TRANSACTIONS_CATEGORIES}/{category_id}/transactions"
        response = await self._client.get(endpoint, params=params)

        if not response.is_ok:
            raise APIError("Failed to fetch transactions by category", response.status_code, response)

        return PaginatedTransactions.from_dict(response.data)

    # =========================================================================
    # Category CRUD Operations
    # =========================================================================

    async def create_category(self, category: 'CategoryCreate') -> TransactionCategory:
        """
        Create a new transaction category.

        Args:
            category: Category data to create.

        Returns:
            Created category with server-assigned ID.

        Raises:
            APIError: If creation fails.
        """
        response = await self._client.post(
            Endpoints.TRANSACTIONS_CATEGORIES,
            data=category.to_dict(),
        )

        if not response.is_ok:
            raise APIError("Failed to create category", response.status_code, response)

        return TransactionCategory.from_dict(response.data)

    async def get_category(self, category_id: str) -> TransactionCategory:
        """
        Get a single category by ID.

        Args:
            category_id: The category ID.

        Returns:
            TransactionCategory object.

        Raises:
            APIError: If category not found or request fails.
        """
        endpoint = f"{Endpoints.TRANSACTIONS_CATEGORIES}/{category_id}"
        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Category not found", response.status_code, response)

        return TransactionCategory.from_dict(response.data)

    async def update_category(
        self,
        category_id: str,
        updates: Dict[str, Any],
    ) -> TransactionCategory:
        """
        Update an existing category.

        Args:
            category_id: The category ID to update.
            updates: Dictionary of fields to update.

        Returns:
            Updated category.

        Raises:
            APIError: If update fails.
        """
        endpoint = f"{Endpoints.TRANSACTIONS_CATEGORIES}/{category_id}"
        response = await self._client.patch(endpoint, data=updates)

        if not response.is_ok:
            raise APIError("Failed to update category", response.status_code, response)

        return TransactionCategory.from_dict(response.data)

    async def delete_category(
        self,
        category_id: str,
        reassign_to: Optional[str] = None,
    ) -> bool:
        """
        Delete a category.

        Args:
            category_id: The category ID to delete.
            reassign_to: Optional category ID to reassign transactions to.

        Returns:
            True if deletion was successful.

        Raises:
            APIError: If deletion fails.
        """
        endpoint = f"{Endpoints.TRANSACTIONS_CATEGORIES}/{category_id}"
        params = {}
        if reassign_to:
            params['reassign_to'] = reassign_to

        response = await self._client.delete(endpoint, params=params if params else None)

        if not response.is_ok:
            raise APIError("Failed to delete category", response.status_code, response)

        return True


# =============================================================================
# Recurring Transaction Models and API
# =============================================================================

class RecurrenceFrequency(Enum):
    """Frequency options for recurring transactions."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class RecurringTransaction:
    """Represents a recurring transaction template."""
    id: str
    amount: Decimal
    description: str
    type: str
    frequency: str
    start_date: str
    category: Optional[str] = None
    account_id: Optional[str] = None
    end_date: Optional[str] = None
    next_occurrence: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecurringTransaction':
        """Create RecurringTransaction from dictionary."""
        return cls(
            id=data.get('id', ''),
            amount=Decimal(str(data.get('amount', 0))),
            description=data.get('description', ''),
            type=data.get('type', TransactionType.EXPENSE),
            frequency=data.get('frequency', RecurrenceFrequency.MONTHLY.value),
            start_date=data.get('start_date', ''),
            category=data.get('category'),
            account_id=data.get('account_id'),
            end_date=data.get('end_date'),
            next_occurrence=data.get('next_occurrence'),
            notes=data.get('notes'),
            tags=data.get('tags', []),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            'amount': self.amount,
            'description': self.description,
            'type': self.type,
            'frequency': self.frequency,
            'start_date': self.start_date,
            'category': self.category,
            'account_id': self.account_id,
            'end_date': self.end_date,
            'notes': self.notes,
            'tags': self.tags,
            'is_active': self.is_active,
        }


@dataclass
class RecurringTransactionCreate:
    """Data for creating a new recurring transaction."""
    amount: Decimal
    description: str
    type: str
    frequency: str
    start_date: str
    category: Optional[str] = None
    account_id: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            'amount': self.amount,
            'description': self.description,
            'type': self.type,
            'frequency': self.frequency,
            'start_date': self.start_date,
            'category': self.category,
            'account_id': self.account_id,
            'end_date': self.end_date,
            'notes': self.notes,
            'tags': self.tags,
        }


@dataclass
class CategoryCreate:
    """Data for creating a new category."""
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_income: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            'name': self.name,
            'icon': self.icon,
            'color': self.color,
            'parent_id': self.parent_id,
            'is_income': self.is_income,
        }


class RecurringTransactionsAPI:
    """
    API client for recurring transaction operations.

    Provides methods for creating, reading, updating, and deleting
    recurring transaction templates.
    """

    def __init__(self, api_client: APIClient):
        """
        Initialize the recurring transactions API client.

        Args:
            api_client: The base API client instance.
        """
        self._client = api_client
        self._base_endpoint = f"{Endpoints.TRANSACTIONS}/recurring"

    async def list(
        self,
        is_active: Optional[bool] = None,
        type: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> List[RecurringTransaction]:
        """
        List all recurring transactions.

        Args:
            is_active: Optional filter by active status.
            type: Optional filter by transaction type.
            account_id: Optional filter by account.

        Returns:
            List of RecurringTransaction objects.
        """
        params = {}
        if is_active is not None:
            params['is_active'] = str(is_active).lower()
        if type:
            params['type'] = type
        if account_id:
            params['account_id'] = account_id

        response = await self._client.get(
            self._base_endpoint,
            params=params if params else None,
        )

        if not response.is_ok:
            raise APIError("Failed to fetch recurring transactions", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [RecurringTransaction.from_dict(rt) for rt in items]

    async def get(self, recurring_id: str) -> RecurringTransaction:
        """
        Get a single recurring transaction by ID.

        Args:
            recurring_id: The recurring transaction ID.

        Returns:
            RecurringTransaction object.

        Raises:
            APIError: If not found or request fails.
        """
        endpoint = f"{self._base_endpoint}/{recurring_id}"
        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Recurring transaction not found", response.status_code, response)

        return RecurringTransaction.from_dict(response.data)

    async def create(self, recurring: RecurringTransactionCreate) -> RecurringTransaction:
        """
        Create a new recurring transaction.

        Args:
            recurring: Recurring transaction data to create.

        Returns:
            Created recurring transaction with server-assigned ID.

        Raises:
            APIError: If creation fails.
        """
        response = await self._client.post(
            self._base_endpoint,
            data=recurring.to_dict(),
        )

        if not response.is_ok:
            raise APIError("Failed to create recurring transaction", response.status_code, response)

        return RecurringTransaction.from_dict(response.data)

    async def update(
        self,
        recurring_id: str,
        updates: Dict[str, Any],
    ) -> RecurringTransaction:
        """
        Update an existing recurring transaction.

        Args:
            recurring_id: The recurring transaction ID to update.
            updates: Dictionary of fields to update.

        Returns:
            Updated recurring transaction.

        Raises:
            APIError: If update fails.
        """
        endpoint = f"{self._base_endpoint}/{recurring_id}"
        response = await self._client.patch(endpoint, data=updates)

        if not response.is_ok:
            raise APIError("Failed to update recurring transaction", response.status_code, response)

        return RecurringTransaction.from_dict(response.data)

    async def delete(
        self,
        recurring_id: str,
        delete_generated: bool = False,
    ) -> bool:
        """
        Delete a recurring transaction.

        Args:
            recurring_id: The recurring transaction ID to delete.
            delete_generated: Whether to also delete generated transactions.

        Returns:
            True if deletion was successful.

        Raises:
            APIError: If deletion fails.
        """
        endpoint = f"{self._base_endpoint}/{recurring_id}"
        params = {}
        if delete_generated:
            params['delete_generated'] = 'true'

        response = await self._client.delete(
            endpoint,
            params=params if params else None,
        )

        if not response.is_ok:
            raise APIError("Failed to delete recurring transaction", response.status_code, response)

        return True

    async def toggle_active(
        self,
        recurring_id: str,
        is_active: bool,
    ) -> RecurringTransaction:
        """
        Toggle the active status of a recurring transaction.

        Args:
            recurring_id: The recurring transaction ID.
            is_active: New active status.

        Returns:
            Updated recurring transaction.
        """
        return await self.update(recurring_id, {'is_active': is_active})

    async def process_due(
        self,
        as_of_date: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Process all due recurring transactions and create actual transactions.

        Args:
            as_of_date: Date to check for due transactions (ISO format).
                       Defaults to today.

        Returns:
            List of newly created Transaction objects.
        """
        params = {}
        if as_of_date:
            params['as_of_date'] = as_of_date

        response = await self._client.post(
            f"{self._base_endpoint}/process",
            params=params if params else None,
        )

        if not response.is_ok:
            raise APIError("Failed to process recurring transactions", response.status_code, response)

        created = response.data.get('created_transactions', response.data.get('items', []))
        return [Transaction.from_dict(t) for t in created]

    async def get_upcoming(
        self,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming scheduled occurrences for all active recurring transactions.

        Args:
            days: Number of days to look ahead.

        Returns:
            List of upcoming occurrence details.
        """
        response = await self._client.get(
            f"{self._base_endpoint}/upcoming",
            params={'days': str(days)},
        )

        if not response.is_ok:
            raise APIError("Failed to fetch upcoming recurring transactions", response.status_code, response)

        return response.data.get('upcoming', response.data)
