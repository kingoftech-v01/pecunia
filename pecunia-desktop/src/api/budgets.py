"""
Budgets API client for Pecunia Desktop.

Handles all budget-related API operations including CRUD,
progress tracking, budget items management, and reporting.
"""

import logging
from datetime import date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import Endpoints, BudgetPeriod
from .client import APIClient, APIResponse, APIError

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class BudgetStatus(Enum):
    """Budget status based on spending."""
    ON_TRACK = "on_track"
    WARNING = "warning"  # 80-99% spent
    EXCEEDED = "exceeded"  # 100%+ spent
    INACTIVE = "inactive"


class BudgetItemType(Enum):
    """Type of budget item."""
    CATEGORY = "category"
    SUBCATEGORY = "subcategory"
    CUSTOM = "custom"


# =============================================================================
# REQUEST/RESPONSE DATACLASSES
# =============================================================================

@dataclass
class Budget:
    """Represents a budget."""
    id: str
    name: str
    amount: float
    period: str
    category: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = True
    rollover: bool = False
    notify_at_percent: int = 80
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Budget':
        """Create Budget from dictionary."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            amount=float(data.get('amount', 0)),
            period=data.get('period', BudgetPeriod.MONTHLY.value),
            category=data.get('category'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            is_active=data.get('is_active', True),
            rollover=data.get('rollover', False),
            notify_at_percent=data.get('notify_at_percent', 80),
            description=data.get('description'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            'name': self.name,
            'amount': self.amount,
            'period': self.period,
            'category': self.category,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'is_active': self.is_active,
            'rollover': self.rollover,
            'notify_at_percent': self.notify_at_percent,
            'description': self.description,
        }


@dataclass
class BudgetItem:
    """Represents a budget line item."""
    id: str
    budget_id: str
    name: str
    amount: float
    category: Optional[str] = None
    item_type: str = BudgetItemType.CATEGORY.value
    description: Optional[str] = None
    order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetItem':
        """Create BudgetItem from dictionary."""
        return cls(
            id=data.get('id', ''),
            budget_id=data.get('budget_id', ''),
            name=data.get('name', ''),
            amount=float(data.get('amount', 0)),
            category=data.get('category'),
            item_type=data.get('item_type', BudgetItemType.CATEGORY.value),
            description=data.get('description'),
            order=int(data.get('order', 0)),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            'budget_id': self.budget_id,
            'name': self.name,
            'amount': self.amount,
            'category': self.category,
            'item_type': self.item_type,
            'description': self.description,
            'order': self.order,
        }


@dataclass
class BudgetWithItems:
    """Budget with its associated items."""
    budget: Budget
    items: List[BudgetItem] = field(default_factory=list)
    total_allocated: float = 0.0
    unallocated_amount: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetWithItems':
        """Create BudgetWithItems from dictionary."""
        budget = Budget.from_dict(data.get('budget', data))
        items = [BudgetItem.from_dict(item) for item in data.get('items', [])]
        total_allocated = sum(item.amount for item in items)

        return cls(
            budget=budget,
            items=items,
            total_allocated=data.get('total_allocated', total_allocated),
            unallocated_amount=data.get('unallocated_amount', budget.amount - total_allocated),
        )


@dataclass
class BudgetProgress:
    """Progress tracking for a budget."""
    budget_id: str
    budget_name: str
    budget_amount: float
    spent_amount: float
    remaining_amount: float
    percent_used: float
    status: str
    period_start: str
    period_end: str
    transaction_count: int = 0
    daily_average: float = 0.0
    projected_spending: float = 0.0
    days_remaining: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetProgress':
        """Create BudgetProgress from dictionary."""
        budget_amount = float(data.get('budget_amount', 0))
        spent_amount = float(data.get('spent_amount', 0))
        remaining = budget_amount - spent_amount

        return cls(
            budget_id=data.get('budget_id', ''),
            budget_name=data.get('budget_name', ''),
            budget_amount=budget_amount,
            spent_amount=spent_amount,
            remaining_amount=data.get('remaining_amount', remaining),
            percent_used=float(data.get('percent_used', 0)),
            status=data.get('status', BudgetStatus.ON_TRACK.value),
            period_start=data.get('period_start', ''),
            period_end=data.get('period_end', ''),
            transaction_count=int(data.get('transaction_count', 0)),
            daily_average=float(data.get('daily_average', 0)),
            projected_spending=float(data.get('projected_spending', 0)),
            days_remaining=int(data.get('days_remaining', 0)),
        )

    @property
    def is_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        return self.percent_used >= 100

    @property
    def is_warning(self) -> bool:
        """Check if budget is at warning level."""
        return 80 <= self.percent_used < 100


@dataclass
class BudgetAlert:
    """Budget alert notification."""
    id: str
    budget_id: str
    budget_name: str
    alert_type: str  # 'warning', 'exceeded', 'approaching'
    message: str
    percent_used: float
    created_at: str
    is_read: bool = False
    dismissed: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetAlert':
        """Create BudgetAlert from dictionary."""
        return cls(
            id=data.get('id', ''),
            budget_id=data.get('budget_id', ''),
            budget_name=data.get('budget_name', ''),
            alert_type=data.get('alert_type', 'warning'),
            message=data.get('message', ''),
            percent_used=float(data.get('percent_used', 0)),
            created_at=data.get('created_at', ''),
            is_read=data.get('is_read', False),
            dismissed=data.get('dismissed', False),
        )


@dataclass
class BudgetSummary:
    """Summary of all budgets."""
    total_budgeted: float
    total_spent: float
    total_remaining: float
    budget_count: int
    on_track_count: int
    warning_count: int
    exceeded_count: int
    budgets: List[BudgetProgress] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetSummary':
        """Create BudgetSummary from dictionary."""
        return cls(
            total_budgeted=float(data.get('total_budgeted', 0)),
            total_spent=float(data.get('total_spent', 0)),
            total_remaining=float(data.get('total_remaining', 0)),
            budget_count=int(data.get('budget_count', 0)),
            on_track_count=int(data.get('on_track_count', 0)),
            warning_count=int(data.get('warning_count', 0)),
            exceeded_count=int(data.get('exceeded_count', 0)),
            budgets=[BudgetProgress.from_dict(b) for b in data.get('budgets', [])],
        )


@dataclass
class BudgetFilter:
    """Filter parameters for budget queries."""
    active_only: bool = True
    category: Optional[str] = None
    period: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search: Optional[str] = None

    def to_params(self) -> Dict[str, Any]:
        """Convert to query parameters dictionary."""
        params = {}
        if self.active_only:
            params['active_only'] = 'true'
        if self.category:
            params['category'] = self.category
        if self.period:
            params['period'] = self.period
        if self.start_date:
            params['start_date'] = self.start_date
        if self.end_date:
            params['end_date'] = self.end_date
        if self.min_amount is not None:
            params['min_amount'] = self.min_amount
        if self.max_amount is not None:
            params['max_amount'] = self.max_amount
        if self.search:
            params['search'] = self.search
        return params


@dataclass
class BudgetItemProgress:
    """Progress tracking for a budget item."""
    item_id: str
    item_name: str
    budgeted_amount: float
    spent_amount: float
    remaining_amount: float
    percent_used: float
    category: Optional[str] = None
    transaction_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetItemProgress':
        """Create BudgetItemProgress from dictionary."""
        budgeted = float(data.get('budgeted_amount', 0))
        spent = float(data.get('spent_amount', 0))

        return cls(
            item_id=data.get('item_id', ''),
            item_name=data.get('item_name', ''),
            budgeted_amount=budgeted,
            spent_amount=spent,
            remaining_amount=data.get('remaining_amount', budgeted - spent),
            percent_used=float(data.get('percent_used', 0)),
            category=data.get('category'),
            transaction_count=int(data.get('transaction_count', 0)),
        )


@dataclass
class BudgetVsActualReport:
    """Budget vs actual comparison report."""
    budget_id: str
    budget_name: str
    period_start: str
    period_end: str
    total_budgeted: float
    total_actual: float
    variance: float
    variance_percent: float
    items: List[BudgetItemProgress] = field(default_factory=list)
    category_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)
    trends: Dict[str, List[float]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetVsActualReport':
        """Create BudgetVsActualReport from dictionary."""
        total_budgeted = float(data.get('total_budgeted', 0))
        total_actual = float(data.get('total_actual', 0))
        variance = total_budgeted - total_actual

        return cls(
            budget_id=data.get('budget_id', ''),
            budget_name=data.get('budget_name', ''),
            period_start=data.get('period_start', ''),
            period_end=data.get('period_end', ''),
            total_budgeted=total_budgeted,
            total_actual=total_actual,
            variance=data.get('variance', variance),
            variance_percent=float(data.get('variance_percent', 0)),
            items=[BudgetItemProgress.from_dict(item) for item in data.get('items', [])],
            category_breakdown=data.get('category_breakdown', {}),
            trends=data.get('trends', {}),
        )

    @property
    def is_under_budget(self) -> bool:
        """Check if actual spending is under budget."""
        return self.total_actual <= self.total_budgeted

    @property
    def is_over_budget(self) -> bool:
        """Check if actual spending exceeds budget."""
        return self.total_actual > self.total_budgeted


@dataclass
class PaginatedBudgets:
    """Paginated list of budgets."""
    items: List[Budget]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaginatedBudgets':
        """Create PaginatedBudgets from dictionary."""
        items = [Budget.from_dict(b) for b in data.get('items', [])]
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


# =============================================================================
# API CLIENT
# =============================================================================

class BudgetsAPI:
    """
    API client for budget operations.

    Provides methods for creating, reading, updating, and deleting
    budgets and budget items, as well as tracking progress, managing
    alerts, and generating reports.
    """

    def __init__(self, api_client: APIClient):
        """
        Initialize the budgets API client.

        Args:
            api_client: The base API client instance.
        """
        self._client = api_client

    # -------------------------------------------------------------------------
    # Budget CRUD Operations
    # -------------------------------------------------------------------------

    async def list(
        self,
        filter: Optional[BudgetFilter] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedBudgets:
        """
        List all budgets with optional filtering and pagination.

        Args:
            filter: Optional filter parameters.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Paginated list of budgets.
        """
        params = {
            'page': page,
            'page_size': page_size,
        }

        if filter:
            params.update(filter.to_params())

        response = await self._client.get(Endpoints.BUDGETS, params=params)

        if not response.is_ok:
            raise APIError("Failed to fetch budgets", response.status_code, response)

        # Handle both paginated and non-paginated responses
        if isinstance(response.data, dict) and 'items' in response.data:
            return PaginatedBudgets.from_dict(response.data)

        # Legacy format: list of budgets
        items = response.data if isinstance(response.data, list) else []
        return PaginatedBudgets(
            items=[Budget.from_dict(b) for b in items],
            total=len(items),
            page=1,
            page_size=len(items),
            total_pages=1,
        )

    async def get(self, budget_id: str, include_items: bool = False) -> BudgetWithItems:
        """
        Get a single budget by ID with optional items.

        Args:
            budget_id: The budget ID.
            include_items: Whether to include budget items.

        Returns:
            BudgetWithItems object containing budget and optional items.

        Raises:
            APIError: If budget not found.
        """
        endpoint = Endpoints.BUDGETS_BY_ID.format(id=budget_id)
        params = {'include_items': 'true'} if include_items else {}

        response = await self._client.get(endpoint, params=params)

        if not response.is_ok:
            raise APIError("Budget not found", response.status_code, response)

        return BudgetWithItems.from_dict(response.data)

    async def create(self, budget: Budget) -> Budget:
        """
        Create a new budget.

        Args:
            budget: Budget data to create.

        Returns:
            Created budget with server-assigned ID.

        Raises:
            APIError: If creation fails.
        """
        response = await self._client.post(
            Endpoints.BUDGETS,
            data=budget.to_dict(),
        )

        if not response.is_ok:
            raise APIError("Failed to create budget", response.status_code, response)

        return Budget.from_dict(response.data)

    async def update(self, budget_id: str, updates: Dict[str, Any]) -> Budget:
        """
        Update an existing budget.

        Args:
            budget_id: The budget ID to update.
            updates: Dictionary of fields to update.

        Returns:
            Updated budget.

        Raises:
            APIError: If update fails.
        """
        endpoint = Endpoints.BUDGETS_BY_ID.format(id=budget_id)
        response = await self._client.patch(endpoint, data=updates)

        if not response.is_ok:
            raise APIError("Failed to update budget", response.status_code, response)

        return Budget.from_dict(response.data)

    async def delete(self, budget_id: str) -> bool:
        """
        Delete a budget.

        Args:
            budget_id: The budget ID to delete.

        Returns:
            True if deletion was successful.

        Raises:
            APIError: If deletion fails.
        """
        endpoint = Endpoints.BUDGETS_BY_ID.format(id=budget_id)
        response = await self._client.delete(endpoint)

        if not response.is_ok:
            raise APIError("Failed to delete budget", response.status_code, response)

        return True

    # -------------------------------------------------------------------------
    # Budget Progress & Status
    # -------------------------------------------------------------------------

    async def get_progress(self, budget_id: str) -> BudgetProgress:
        """
        Get progress/status for a specific budget.

        Args:
            budget_id: The budget ID.

        Returns:
            BudgetProgress object with current spending info.
        """
        endpoint = Endpoints.BUDGETS_PROGRESS.format(id=budget_id)
        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Failed to fetch budget progress", response.status_code, response)

        return BudgetProgress.from_dict(response.data)

    async def get_all_progress(self) -> List[BudgetProgress]:
        """
        Get progress for all active budgets.

        Returns:
            List of BudgetProgress objects.
        """
        response = await self._client.get(f"{Endpoints.BUDGETS}/progress")

        if not response.is_ok:
            raise APIError("Failed to fetch budget progress", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [BudgetProgress.from_dict(p) for p in items]

    async def get_summary(self) -> BudgetSummary:
        """
        Get summary of all budgets.

        Returns:
            BudgetSummary with aggregated information.
        """
        response = await self._client.get(f"{Endpoints.BUDGETS}/summary")

        if not response.is_ok:
            raise APIError("Failed to fetch budget summary", response.status_code, response)

        return BudgetSummary.from_dict(response.data)

    # -------------------------------------------------------------------------
    # Budget Items CRUD
    # -------------------------------------------------------------------------

    async def list_items(self, budget_id: str) -> List[BudgetItem]:
        """
        List all items for a budget.

        Args:
            budget_id: The budget ID.

        Returns:
            List of BudgetItem objects.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/items"
        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Failed to fetch budget items", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [BudgetItem.from_dict(item) for item in items]

    async def get_item(self, budget_id: str, item_id: str) -> BudgetItem:
        """
        Get a single budget item.

        Args:
            budget_id: The budget ID.
            item_id: The item ID.

        Returns:
            BudgetItem object.

        Raises:
            APIError: If item not found.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/items/{item_id}"
        response = await self._client.get(endpoint)

        if not response.is_ok:
            raise APIError("Budget item not found", response.status_code, response)

        return BudgetItem.from_dict(response.data)

    async def create_item(self, budget_id: str, item: BudgetItem) -> BudgetItem:
        """
        Create a new budget item.

        Args:
            budget_id: The budget ID.
            item: BudgetItem data to create.

        Returns:
            Created budget item with server-assigned ID.

        Raises:
            APIError: If creation fails.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/items"
        data = item.to_dict()
        data['budget_id'] = budget_id

        response = await self._client.post(endpoint, data=data)

        if not response.is_ok:
            raise APIError("Failed to create budget item", response.status_code, response)

        return BudgetItem.from_dict(response.data)

    async def update_item(
        self,
        budget_id: str,
        item_id: str,
        updates: Dict[str, Any],
    ) -> BudgetItem:
        """
        Update an existing budget item.

        Args:
            budget_id: The budget ID.
            item_id: The item ID to update.
            updates: Dictionary of fields to update.

        Returns:
            Updated budget item.

        Raises:
            APIError: If update fails.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/items/{item_id}"
        response = await self._client.patch(endpoint, data=updates)

        if not response.is_ok:
            raise APIError("Failed to update budget item", response.status_code, response)

        return BudgetItem.from_dict(response.data)

    async def delete_item(self, budget_id: str, item_id: str) -> bool:
        """
        Delete a budget item.

        Args:
            budget_id: The budget ID.
            item_id: The item ID to delete.

        Returns:
            True if deletion was successful.

        Raises:
            APIError: If deletion fails.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/items/{item_id}"
        response = await self._client.delete(endpoint)

        if not response.is_ok:
            raise APIError("Failed to delete budget item", response.status_code, response)

        return True

    async def bulk_update_items(
        self,
        budget_id: str,
        items: List[Dict[str, Any]],
    ) -> List[BudgetItem]:
        """
        Bulk update multiple budget items.

        Args:
            budget_id: The budget ID.
            items: List of item updates with 'id' and fields to update.

        Returns:
            List of updated budget items.

        Raises:
            APIError: If update fails.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/items/bulk-update"
        response = await self._client.post(endpoint, data={'items': items})

        if not response.is_ok:
            raise APIError("Failed to bulk update budget items", response.status_code, response)

        updated = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [BudgetItem.from_dict(item) for item in updated]

    async def reorder_items(
        self,
        budget_id: str,
        item_ids: List[str],
    ) -> List[BudgetItem]:
        """
        Reorder budget items.

        Args:
            budget_id: The budget ID.
            item_ids: List of item IDs in desired order.

        Returns:
            List of reordered budget items.

        Raises:
            APIError: If reorder fails.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/items/reorder"
        response = await self._client.post(endpoint, data={'item_ids': item_ids})

        if not response.is_ok:
            raise APIError("Failed to reorder budget items", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [BudgetItem.from_dict(item) for item in items]

    # -------------------------------------------------------------------------
    # Budget vs Actual Report
    # -------------------------------------------------------------------------

    async def get_budget_vs_actual(
        self,
        budget_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> BudgetVsActualReport:
        """
        Get budget vs actual comparison report for a specific budget.

        Args:
            budget_id: The budget ID.
            start_date: Optional start date filter (ISO format).
            end_date: Optional end date filter (ISO format).

        Returns:
            BudgetVsActualReport with comparison data.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/report"
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        response = await self._client.get(endpoint, params=params)

        if not response.is_ok:
            raise APIError("Failed to fetch budget vs actual report", response.status_code, response)

        return BudgetVsActualReport.from_dict(response.data)

    async def get_all_budgets_vs_actual(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[BudgetVsActualReport]:
        """
        Get budget vs actual reports for all active budgets.

        Args:
            start_date: Optional start date filter (ISO format).
            end_date: Optional end date filter (ISO format).

        Returns:
            List of BudgetVsActualReport objects.
        """
        endpoint = f"{Endpoints.BUDGETS}/reports/vs-actual"
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        response = await self._client.get(endpoint, params=params)

        if not response.is_ok:
            raise APIError("Failed to fetch budget vs actual reports", response.status_code, response)

        items = response.data.get('reports', response.data) if isinstance(response.data, dict) else response.data
        return [BudgetVsActualReport.from_dict(r) for r in items]

    # -------------------------------------------------------------------------
    # Budget Alerts
    # -------------------------------------------------------------------------

    async def get_alerts(
        self,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[BudgetAlert]:
        """
        Get budget alerts.

        Args:
            unread_only: Whether to only return unread alerts.
            limit: Maximum number of alerts to return.

        Returns:
            List of BudgetAlert objects.
        """
        params = {'limit': limit}
        if unread_only:
            params['unread_only'] = 'true'

        response = await self._client.get(Endpoints.BUDGETS_ALERTS, params=params)

        if not response.is_ok:
            raise APIError("Failed to fetch alerts", response.status_code, response)

        items = response.data.get('items', response.data) if isinstance(response.data, dict) else response.data
        return [BudgetAlert.from_dict(a) for a in items]

    async def mark_alert_read(self, alert_id: str) -> bool:
        """
        Mark an alert as read.

        Args:
            alert_id: The alert ID.

        Returns:
            True if successful.
        """
        response = await self._client.patch(
            f"{Endpoints.BUDGETS_ALERTS}/{alert_id}",
            data={'is_read': True},
        )

        if not response.is_ok:
            raise APIError("Failed to update alert", response.status_code, response)

        return True

    async def dismiss_alert(self, alert_id: str) -> bool:
        """
        Dismiss an alert.

        Args:
            alert_id: The alert ID.

        Returns:
            True if successful.
        """
        response = await self._client.patch(
            f"{Endpoints.BUDGETS_ALERTS}/{alert_id}",
            data={'dismissed': True},
        )

        if not response.is_ok:
            raise APIError("Failed to dismiss alert", response.status_code, response)

        return True

    async def mark_all_alerts_read(self) -> int:
        """
        Mark all alerts as read.

        Returns:
            Number of alerts marked as read.
        """
        response = await self._client.post(f"{Endpoints.BUDGETS_ALERTS}/mark-all-read")

        if not response.is_ok:
            raise APIError("Failed to mark alerts as read", response.status_code, response)

        return response.data.get('updated_count', 0)

    # -------------------------------------------------------------------------
    # Budget Utility Methods
    # -------------------------------------------------------------------------

    async def activate(self, budget_id: str) -> Budget:
        """
        Activate a budget.

        Args:
            budget_id: The budget ID.

        Returns:
            Updated budget.
        """
        return await self.update(budget_id, {'is_active': True})

    async def deactivate(self, budget_id: str) -> Budget:
        """
        Deactivate a budget.

        Args:
            budget_id: The budget ID.

        Returns:
            Updated budget.
        """
        return await self.update(budget_id, {'is_active': False})

    async def duplicate(self, budget_id: str, new_name: Optional[str] = None) -> Budget:
        """
        Duplicate an existing budget.

        Args:
            budget_id: The budget ID to duplicate.
            new_name: Optional new name for the duplicated budget.

        Returns:
            Newly created budget.
        """
        response = await self._client.post(
            f"{Endpoints.BUDGETS}/{budget_id}/duplicate",
            data={'name': new_name} if new_name else None,
        )

        if not response.is_ok:
            raise APIError("Failed to duplicate budget", response.status_code, response)

        return Budget.from_dict(response.data)

    async def get_by_category(self, category: str) -> List[Budget]:
        """
        Get all budgets for a specific category.

        Args:
            category: The category name.

        Returns:
            List of budgets for the category.
        """
        filter = BudgetFilter(active_only=False, category=category)
        result = await self.list(filter=filter)
        return result.items

    async def check_budget_impact(
        self,
        amount: float,
        category: str,
    ) -> Dict[str, Any]:
        """
        Check how a transaction amount would impact category budgets.

        Args:
            amount: Transaction amount.
            category: Transaction category.

        Returns:
            Dictionary with budget impact information.
        """
        response = await self._client.post(
            f"{Endpoints.BUDGETS}/check-impact",
            data={'amount': amount, 'category': category},
        )

        if not response.is_ok:
            raise APIError("Failed to check budget impact", response.status_code, response)

        return response.data

    async def get_spending_by_period(
        self,
        budget_id: str,
        periods: int = 6,
    ) -> Dict[str, Any]:
        """
        Get spending history for a budget over multiple periods.

        Args:
            budget_id: The budget ID.
            periods: Number of past periods to include.

        Returns:
            Dictionary with period-by-period spending data.
        """
        endpoint = f"{Endpoints.BUDGETS}/{budget_id}/spending-history"
        response = await self._client.get(endpoint, params={'periods': periods})

        if not response.is_ok:
            raise APIError("Failed to fetch spending history", response.status_code, response)

        return response.data

    async def copy_to_next_period(self, budget_id: str) -> Budget:
        """
        Copy a budget to the next period.

        Args:
            budget_id: The budget ID to copy.

        Returns:
            Newly created budget for the next period.
        """
        response = await self._client.post(
            f"{Endpoints.BUDGETS}/{budget_id}/copy-next-period"
        )

        if not response.is_ok:
            raise APIError("Failed to copy budget to next period", response.status_code, response)

        return Budget.from_dict(response.data)
