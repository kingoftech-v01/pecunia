# Desktop Platform Conventions - Pecunia Python/PyQt6

**Version**: 1.0
**Last Updated**: 2026-01-28
**Status**: MANDATORY for all desktop development

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [SQLAlchemy Models](#2-sqlalchemy-models)
3. [API Client Patterns](#3-api-client-patterns)
4. [PyQt6 UI Patterns](#4-pyqt6-ui-patterns)
5. [Sync Engine Patterns](#5-sync-engine-patterns)
6. [Configuration Management](#6-configuration-management)
7. [Error Handling](#7-error-handling)
8. [Logging Standards](#8-logging-standards)
9. [Testing Patterns](#9-testing-patterns)
10. [Packaging and Distribution](#10-packaging-and-distribution)

---

## 1. Project Structure

### Mandatory Directory Structure

```
pecunia-desktop/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   ├── constants.py            # Application constants
│   ├── exceptions.py           # Custom exceptions
│   ├── logger.py               # Logging configuration
│   │
│   ├── api/                    # API client layer
│   │   ├── __init__.py
│   │   ├── client.py          # Base HTTP client
│   │   ├── auth.py            # Authentication service
│   │   ├── transactions.py    # Transaction endpoints
│   │   ├── budgets.py         # Budget endpoints
│   │   └── banking.py         # Banking integration
│   │
│   ├── database/               # SQLAlchemy layer
│   │   ├── __init__.py
│   │   ├── connection.py      # Engine and session
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── base.py        # Base model class
│   │       ├── user.py
│   │       ├── transaction.py
│   │       └── budget.py
│   │
│   ├── sync/                   # Offline sync engine
│   │   ├── __init__.py
│   │   ├── manager.py         # Sync orchestration
│   │   ├── queue.py           # Operation queue
│   │   └── conflict_resolver.py
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── transaction_service.py
│   │   ├── budget_service.py
│   │   └── report_service.py
│   │
│   ├── ui/                     # PyQt6 UI layer
│   │   ├── __init__.py
│   │   ├── main_window.py     # Main application window
│   │   ├── styles.py          # QSS stylesheets
│   │   ├── theme.py           # Theme management
│   │   ├── pages/             # Full-page views
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py
│   │   │   ├── transactions.py
│   │   │   ├── budgets.py
│   │   │   └── settings.py
│   │   └── widgets/           # Reusable components
│   │       ├── __init__.py
│   │       ├── sidebar.py
│   │       ├── forms.py
│   │       └── tables.py
│   │
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── formatters.py
│       └── validators.py
│
├── resources/                  # Assets
│   ├── icons/
│   ├── images/
│   └── styles/
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_database/
│   ├── test_sync/
│   └── test_ui/
│
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

### Module Naming Conventions

| Module Type | Naming | Example |
|-------------|--------|---------|
| Files | snake_case | `transaction_service.py` |
| Classes | PascalCase | `TransactionService` |
| Functions | snake_case | `get_transactions()` |
| Constants | SCREAMING_SNAKE | `DEFAULT_PAGE_SIZE` |
| Private | `_prefix` | `_validate_amount()` |

---

## 2. SQLAlchemy Models

### Base Model Template

```python
"""
Base model with common fields and functionality.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class BaseModel(Base):
    """
    Abstract base model with common fields.

    All models should inherit from this class.

    Attributes:
        id: Auto-incrementing primary key (local).
        server_id: UUID from server (for sync).
        is_synced: Whether record is synced with server.
        sync_status: Current sync status.
        created_at: Local creation timestamp.
        updated_at: Last modification timestamp.
    """

    __abstract__ = True

    # Local primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Server sync fields
    server_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        unique=True,
        index=True
    )

    is_synced: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True
    )

    sync_status: Mapped[str] = mapped_column(
        String(20),
        default='pending'
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Version for optimistic locking
    version: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    def mark_synced(self, server_id: str) -> None:
        """Mark record as synced with server."""
        self.server_id = server_id
        self.is_synced = True
        self.sync_status = 'synced'
        self.updated_at = datetime.utcnow()

    def mark_dirty(self) -> None:
        """Mark record for re-sync."""
        self.is_synced = False
        self.sync_status = 'pending'
        self.version += 1
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'server_id': self.server_id,
            'is_synced': self.is_synced,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

### Entity Model Template

```python
"""
Transaction model for local database.
"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Boolean, Date, DateTime, Enum as SQLEnum,
    ForeignKey, Index, Integer, Numeric, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    INCOME = 'income'
    EXPENSE = 'expense'
    TRANSFER = 'transfer'


class Transaction(BaseModel):
    """
    Transaction model for local storage.

    Represents a financial transaction with support for:
    - Offline-first operation
    - Sync with server
    - Category classification
    - Recurring transactions

    Attributes:
        user_id: Owner user ID.
        amount: Transaction amount (positive).
        type: Income, expense, or transfer.
        category_id: Associated category.
        description: User description.
        transaction_date: Date of transaction.
        is_recurring: Whether this is recurring.
    """

    __tablename__ = 'transactions'

    # ==========================================================================
    # FOREIGN KEYS
    # ==========================================================================

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    category_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey('categories.id', ondelete='SET NULL'),
        nullable=True
    )

    bank_account_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey('bank_accounts.id', ondelete='SET NULL'),
        nullable=True
    )

    # ==========================================================================
    # BUSINESS FIELDS
    # ==========================================================================

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )

    type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType),
        nullable=False,
        index=True
    )

    description: Mapped[str] = mapped_column(
        String(500),
        default='',
        nullable=False
    )

    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )

    reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    notes: Mapped[str] = mapped_column(
        Text,
        default='',
        nullable=False
    )

    # ==========================================================================
    # STATUS FIELDS
    # ==========================================================================

    is_recurring: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_pending: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True
    )

    # ==========================================================================
    # METADATA
    # ==========================================================================

    tags: Mapped[str] = mapped_column(
        Text,
        default='',
        nullable=False
    )  # Comma-separated tags

    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================

    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="transactions"
    )

    # ==========================================================================
    # TABLE CONFIGURATION
    # ==========================================================================

    __table_args__ = (
        Index('ix_trans_user_date', 'user_id', 'transaction_date'),
        Index('ix_trans_user_type', 'user_id', 'type'),
        Index('ix_trans_user_category', 'user_id', 'category_id'),
        Index('ix_trans_unsynced', 'is_synced', postgresql_where=~is_synced),
    )

    # ==========================================================================
    # PROPERTIES
    # ==========================================================================

    @property
    def signed_amount(self) -> Decimal:
        """Return signed amount (negative for expenses)."""
        if self.type == TransactionType.EXPENSE:
            return -self.amount
        return self.amount

    @property
    def tag_list(self) -> List[str]:
        """Return tags as list."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @tag_list.setter
    def tag_list(self, tags: List[str]) -> None:
        """Set tags from list."""
        self.tags = ','.join(t.strip() for t in tags if t.strip())

    # ==========================================================================
    # METHODS
    # ==========================================================================

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        base = super().to_dict()
        base.update({
            'amount': str(self.amount),
            'type': self.type.value,
            'category_id': self.category_id,
            'description': self.description,
            'transaction_date': self.transaction_date.isoformat(),
            'is_recurring': self.is_recurring,
            'tags': self.tag_list,
        })
        return base

    def to_api_payload(self) -> dict:
        """Convert to API request payload."""
        return {
            'amount': str(self.amount),
            'type': self.type.value,
            'category_id': self.category_id,
            'description': self.description,
            'transaction_date': self.transaction_date.isoformat(),
            'is_recurring': self.is_recurring,
            'tags': self.tag_list,
        }

    @classmethod
    def from_api_response(cls, data: dict, user_id: int) -> "Transaction":
        """Create instance from API response."""
        return cls(
            server_id=data['id'],
            user_id=user_id,
            amount=Decimal(data['amount']),
            type=TransactionType(data['type']),
            category_id=data.get('category_id'),
            description=data.get('description', ''),
            transaction_date=date.fromisoformat(data['transaction_date']),
            is_recurring=data.get('is_recurring', False),
            tags=','.join(data.get('tags', [])),
            is_synced=True,
            sync_status='synced',
        )
```

---

## 3. API Client Patterns

### Base HTTP Client

```python
"""
Base API client with async HTTP operations.

Features:
- Connection pooling
- Automatic retry with exponential backoff
- Token refresh
- Error handling
"""
import asyncio
from typing import Any, Callable, Optional
from dataclasses import dataclass
import aiohttp
import logging

from ..exceptions import APIError, NetworkError, AuthenticationError
from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """API response wrapper."""
    status_code: int
    data: Any
    is_ok: bool

    @property
    def error_message(self) -> Optional[str]:
        """Extract error message from response."""
        if self.is_ok:
            return None
        if isinstance(self.data, dict):
            return self.data.get('error', {}).get('message', str(self.data))
        return str(self.data)


class APIClient:
    """
    Async HTTP client for API communication.

    Usage:
        client = APIClient(base_url="https://api.example.com")
        await client.connect()

        response = await client.get("/api/v1/transactions")
        if response.is_ok:
            transactions = response.data['data']

        await client.close()
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        self._token_provider: Optional[Callable[[], Optional[str]]] = None

    def set_token_provider(
        self,
        provider: Callable[[], Optional[str]]
    ) -> None:
        """Set function to provide access token."""
        self._token_provider = provider

    async def connect(self) -> None:
        """Initialize HTTP session with connection pooling."""
        if self._session is not None:
            return

        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=20,
            ttl_dns_cache=300,
            keepalive_timeout=30,
        )

        timeout = aiohttp.ClientTimeout(
            total=self._timeout,
            connect=10,
            sock_read=self._timeout,
        )

        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _get_headers(self) -> dict:
        """Build request headers with authentication."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        if self._token_provider:
            token = self._token_provider()
            if token:
                headers['Authorization'] = f'Bearer {token}'

        return headers

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> APIResponse:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API endpoint path
            data: Request body (for POST, PUT, PATCH)
            params: Query parameters

        Returns:
            APIResponse with status and data
        """
        if self._session is None:
            await self.connect()

        url = f"{self._base_url}{path}"
        headers = await self._get_headers()

        last_error = None
        for attempt in range(self._max_retries):
            try:
                async with self._session.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                ) as response:
                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = await response.text()

                    # Handle 401 - token expired
                    if response.status == 401:
                        raise AuthenticationError("Token expired or invalid")

                    return APIResponse(
                        status_code=response.status,
                        data=response_data,
                        is_ok=200 <= response.status < 300,
                    )

            except aiohttp.ClientError as e:
                last_error = NetworkError(f"Network error: {e}")
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self._max_retries}): {e}"
                )

                if attempt < self._max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)

        raise last_error or NetworkError("Request failed after retries")

    # Convenience methods
    async def get(
        self,
        path: str,
        params: Optional[dict] = None
    ) -> APIResponse:
        """Make GET request."""
        return await self._request('GET', path, params=params)

    async def post(
        self,
        path: str,
        data: Optional[dict] = None
    ) -> APIResponse:
        """Make POST request."""
        return await self._request('POST', path, data=data)

    async def put(
        self,
        path: str,
        data: Optional[dict] = None
    ) -> APIResponse:
        """Make PUT request."""
        return await self._request('PUT', path, data=data)

    async def patch(
        self,
        path: str,
        data: Optional[dict] = None
    ) -> APIResponse:
        """Make PATCH request."""
        return await self._request('PATCH', path, data=data)

    async def delete(self, path: str) -> APIResponse:
        """Make DELETE request."""
        return await self._request('DELETE', path)
```

### Domain API Client

```python
"""
Transaction API client.
"""
from typing import List, Optional
from dataclasses import dataclass
from datetime import date

from .client import APIClient, APIResponse
from ..exceptions import APIError


@dataclass
class TransactionFilters:
    """Filters for transaction queries."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    type: Optional[str] = None
    category_id: Optional[str] = None
    search: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to query parameters."""
        params = {}
        if self.date_from:
            params['date_from'] = self.date_from.isoformat()
        if self.date_to:
            params['date_to'] = self.date_to.isoformat()
        if self.type:
            params['type'] = self.type
        if self.category_id:
            params['category_id'] = self.category_id
        if self.search:
            params['search'] = self.search
        return params


class TransactionsAPI:
    """
    API client for transaction endpoints.

    Endpoints:
        GET    /api/v1/transactions/            List transactions
        POST   /api/v1/transactions/            Create transaction
        GET    /api/v1/transactions/{id}/       Get transaction
        PATCH  /api/v1/transactions/{id}/       Update transaction
        DELETE /api/v1/transactions/{id}/       Delete transaction
        GET    /api/v1/transactions/stats/      Get statistics
    """

    BASE_PATH = '/api/v1/transactions'

    def __init__(self, client: APIClient):
        self._client = client

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[TransactionFilters] = None,
    ) -> APIResponse:
        """
        List transactions with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            filters: Optional filters

        Returns:
            APIResponse with paginated transaction list
        """
        params = {'page': page, 'page_size': page_size}

        if filters:
            params.update(filters.to_dict())

        return await self._client.get(f'{self.BASE_PATH}/', params=params)

    async def get(self, transaction_id: str) -> APIResponse:
        """Get single transaction by ID."""
        return await self._client.get(f'{self.BASE_PATH}/{transaction_id}/')

    async def create(self, data: dict) -> APIResponse:
        """Create new transaction."""
        return await self._client.post(f'{self.BASE_PATH}/', data=data)

    async def update(
        self,
        transaction_id: str,
        data: dict
    ) -> APIResponse:
        """Update existing transaction."""
        return await self._client.patch(
            f'{self.BASE_PATH}/{transaction_id}/',
            data=data
        )

    async def delete(self, transaction_id: str) -> APIResponse:
        """Delete transaction."""
        return await self._client.delete(f'{self.BASE_PATH}/{transaction_id}/')

    async def stats(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> APIResponse:
        """Get transaction statistics."""
        params = {}
        if date_from:
            params['date_from'] = date_from.isoformat()
        if date_to:
            params['date_to'] = date_to.isoformat()

        return await self._client.get(f'{self.BASE_PATH}/stats/', params=params)
```

---

## 4. PyQt6 UI Patterns

### Main Window Structure

```python
"""
Main application window.
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon

from .sidebar import Sidebar
from .pages.dashboard import DashboardPage
from .pages.transactions import TransactionsPage
from .pages.budgets import BudgetsPage
from .pages.settings import SettingsPage
from ..config import config


class MainWindow(QMainWindow):
    """
    Main application window.

    Structure:
    - Sidebar (left): Navigation menu
    - Content (right): Page stack

    Signals:
        logout_requested: Emitted when user logs out
        sync_requested: Emitted when manual sync triggered
    """

    logout_requested = pyqtSignal()
    sync_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._restore_state()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.setWindowTitle(f"{config.APP_NAME} - {config.APP_VERSION}")
        self.setMinimumSize(QSize(1024, 768))

        # Set window icon
        icon_path = config.get_resource_path('icons/app_icon.png')
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
        """Initialize UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        layout.addWidget(self._sidebar)

        # Page stack
        self._pages = QStackedWidget()
        layout.addWidget(self._pages, stretch=1)

        # Add pages
        self._dashboard_page = DashboardPage()
        self._transactions_page = TransactionsPage()
        self._budgets_page = BudgetsPage()
        self._settings_page = SettingsPage()

        self._pages.addWidget(self._dashboard_page)
        self._pages.addWidget(self._transactions_page)
        self._pages.addWidget(self._budgets_page)
        self._pages.addWidget(self._settings_page)

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        # Sidebar navigation
        self._sidebar.page_selected.connect(self._on_page_selected)
        self._sidebar.logout_clicked.connect(self._on_logout)
        self._sidebar.sync_clicked.connect(self.sync_requested.emit)

        # Page signals
        self._transactions_page.transaction_created.connect(
            self._dashboard_page.refresh_data
        )

    def _restore_state(self) -> None:
        """Restore window state from config."""
        geometry = config.ui.window_geometry
        if geometry:
            self.restoreGeometry(geometry)

    @pyqtSlot(int)
    def _on_page_selected(self, index: int) -> None:
        """Handle page selection from sidebar."""
        self._pages.setCurrentIndex(index)

    @pyqtSlot()
    def _on_logout(self) -> None:
        """Handle logout request."""
        reply = QMessageBox.question(
            self,
            'Confirm Logout',
            'Are you sure you want to log out?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def closeEvent(self, event) -> None:
        """Save window state on close."""
        config.ui.window_geometry = self.saveGeometry()
        config.save()
        event.accept()
```

### Widget Template

```python
"""
Reusable widget template.
"""
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont

from ...database.models import Transaction


class TransactionListWidget(QWidget):
    """
    Widget displaying a list of transactions.

    Features:
    - Sortable columns
    - Selection handling
    - Pagination
    - Search/filter integration

    Signals:
        transaction_selected: Emitted when a transaction is clicked
            Args: transaction_id (int)
        refresh_requested: Emitted when refresh button clicked
        delete_requested: Emitted with selected transaction IDs
    """

    transaction_selected = pyqtSignal(int)  # transaction_id
    refresh_requested = pyqtSignal()
    delete_requested = pyqtSignal(list)  # transaction_ids

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._transactions: List[Transaction] = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Table
        self._table = self._create_table()
        layout.addWidget(self._table)

        # Footer (pagination)
        footer = self._create_footer()
        layout.addWidget(footer)

    def _create_header(self) -> QWidget:
        """Create header with title and actions."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Transactions")
        title.setFont(QFont('', 16, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addStretch()

        # Actions
        self._refresh_btn = QPushButton("Refresh")
        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setEnabled(False)

        layout.addWidget(self._refresh_btn)
        layout.addWidget(self._delete_btn)

        return header

    def _create_table(self) -> QTableWidget:
        """Create transaction table."""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Date", "Description", "Category", "Amount", "Type"
        ])

        # Configure headers
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        table.setColumnWidth(0, 100)  # Date
        table.setColumnWidth(2, 120)  # Category
        table.setColumnWidth(3, 100)  # Amount
        table.setColumnWidth(4, 80)   # Type

        # Selection mode
        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        table.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )

        return table

    def _create_footer(self) -> QWidget:
        """Create footer with pagination."""
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 8, 0, 0)

        self._page_label = QLabel("Page 1 of 1")
        layout.addWidget(self._page_label)

        layout.addStretch()

        self._prev_btn = QPushButton("Previous")
        self._next_btn = QPushButton("Next")
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)

        layout.addWidget(self._prev_btn)
        layout.addWidget(self._next_btn)

        return footer

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._refresh_btn.clicked.connect(self.refresh_requested.emit)
        self._delete_btn.clicked.connect(self._on_delete_clicked)

    @pyqtSlot()
    def _on_selection_changed(self) -> None:
        """Handle selection change."""
        has_selection = len(self._table.selectedItems()) > 0
        self._delete_btn.setEnabled(has_selection)

    @pyqtSlot(QTableWidgetItem)
    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        """Handle double-click on item."""
        row = item.row()
        if 0 <= row < len(self._transactions):
            transaction = self._transactions[row]
            self.transaction_selected.emit(transaction.id)

    @pyqtSlot()
    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        selected_rows = set(item.row() for item in self._table.selectedItems())
        transaction_ids = [
            self._transactions[row].id
            for row in selected_rows
            if 0 <= row < len(self._transactions)
        ]
        if transaction_ids:
            self.delete_requested.emit(transaction_ids)

    def set_transactions(self, transactions: List[Transaction]) -> None:
        """
        Update displayed transactions.

        Args:
            transactions: List of transactions to display
        """
        self._transactions = transactions
        self._table.setRowCount(len(transactions))

        for row, tx in enumerate(transactions):
            self._table.setItem(
                row, 0,
                QTableWidgetItem(tx.transaction_date.strftime('%Y-%m-%d'))
            )
            self._table.setItem(row, 1, QTableWidgetItem(tx.description))
            self._table.setItem(
                row, 2,
                QTableWidgetItem(tx.category.name if tx.category else '-')
            )

            # Format amount with color
            amount_item = QTableWidgetItem(f"${tx.amount:,.2f}")
            if tx.type.value == 'expense':
                amount_item.setForeground(Qt.GlobalColor.red)
            else:
                amount_item.setForeground(Qt.GlobalColor.green)
            self._table.setItem(row, 3, amount_item)

            self._table.setItem(row, 4, QTableWidgetItem(tx.type.value.title()))

    def set_pagination(
        self,
        current_page: int,
        total_pages: int
    ) -> None:
        """Update pagination display."""
        self._page_label.setText(f"Page {current_page} of {total_pages}")
        self._prev_btn.setEnabled(current_page > 1)
        self._next_btn.setEnabled(current_page < total_pages)

    def clear(self) -> None:
        """Clear all transactions."""
        self._transactions.clear()
        self._table.setRowCount(0)
```

---

## 5. Sync Engine Patterns

### Sync Manager

```python
"""
Offline-first sync manager.

Handles bidirectional synchronization between local database
and server API.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional
import logging

from ..database.connection import get_session
from ..database.models import Transaction, SyncRecord
from ..api.transactions import TransactionsAPI
from .queue import SyncQueue, QueuedOperation
from .conflict_resolver import ConflictResolver, ConflictResolution

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    """Sync operation status."""
    IDLE = 'idle'
    SYNCING = 'syncing'
    SUCCESS = 'success'
    ERROR = 'error'
    CONFLICT = 'conflict'


@dataclass
class SyncResult:
    """Result of sync operation."""
    status: SyncStatus
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SyncManager:
    """
    Manages offline-first data synchronization.

    Strategy:
    1. Queue local changes
    2. Push local changes to server
    3. Pull remote changes
    4. Resolve conflicts
    5. Update local database

    Usage:
        manager = SyncManager(api_client)
        result = await manager.sync_all()
    """

    def __init__(
        self,
        transactions_api: TransactionsAPI,
        conflict_resolver: Optional[ConflictResolver] = None,
    ):
        self._transactions_api = transactions_api
        self._conflict_resolver = conflict_resolver or ConflictResolver()
        self._queue = SyncQueue()
        self._status = SyncStatus.IDLE
        self._last_sync: Optional[datetime] = None

    @property
    def status(self) -> SyncStatus:
        """Current sync status."""
        return self._status

    @property
    def last_sync(self) -> Optional[datetime]:
        """Timestamp of last successful sync."""
        return self._last_sync

    def queue_operation(self, operation: QueuedOperation) -> None:
        """Add operation to sync queue."""
        self._queue.enqueue(operation)

    async def sync_all(self) -> SyncResult:
        """
        Perform full synchronization.

        Steps:
        1. Push all queued local changes
        2. Pull all remote changes since last sync
        3. Resolve any conflicts
        4. Update sync timestamps

        Returns:
            SyncResult with operation counts
        """
        if self._status == SyncStatus.SYNCING:
            logger.warning("Sync already in progress")
            return SyncResult(status=SyncStatus.ERROR, errors=["Sync in progress"])

        self._status = SyncStatus.SYNCING
        result = SyncResult(status=SyncStatus.SUCCESS)

        try:
            # Push local changes
            push_result = await self._push_changes()
            result.pushed = push_result.get('count', 0)
            result.errors.extend(push_result.get('errors', []))

            # Pull remote changes
            pull_result = await self._pull_changes()
            result.pulled = pull_result.get('count', 0)
            result.conflicts = pull_result.get('conflicts', 0)
            result.errors.extend(pull_result.get('errors', []))

            # Update last sync time
            self._last_sync = datetime.utcnow()

            if result.errors:
                result.status = SyncStatus.ERROR
            elif result.conflicts > 0:
                result.status = SyncStatus.CONFLICT

        except Exception as e:
            logger.exception("Sync failed")
            result.status = SyncStatus.ERROR
            result.errors.append(str(e))

        finally:
            self._status = SyncStatus.IDLE

        return result

    async def _push_changes(self) -> dict:
        """Push queued local changes to server."""
        result = {'count': 0, 'errors': []}

        operations = self._queue.get_batch(50)
        for op in operations:
            try:
                await self._process_operation(op)
                result['count'] += 1
            except Exception as e:
                logger.error(f"Failed to push operation: {e}")
                result['errors'].append(f"{op.entity_type}/{op.entity_id}: {e}")
                # Re-queue for retry
                self._queue.enqueue(op)

        return result

    async def _process_operation(self, op: QueuedOperation) -> None:
        """Process single sync operation."""
        if op.entity_type == 'transaction':
            await self._sync_transaction(op)
        elif op.entity_type == 'budget':
            await self._sync_budget(op)
        # Add more entity types as needed

    async def _sync_transaction(self, op: QueuedOperation) -> None:
        """Sync a single transaction."""
        with get_session() as session:
            transaction = session.query(Transaction).get(op.entity_id)
            if not transaction:
                return

            if op.operation == 'create':
                response = await self._transactions_api.create(
                    transaction.to_api_payload()
                )
                if response.is_ok:
                    transaction.mark_synced(response.data['id'])
                    session.commit()

            elif op.operation == 'update':
                if transaction.server_id:
                    response = await self._transactions_api.update(
                        transaction.server_id,
                        transaction.to_api_payload()
                    )
                    if response.is_ok:
                        transaction.is_synced = True
                        session.commit()

            elif op.operation == 'delete':
                if transaction.server_id:
                    await self._transactions_api.delete(transaction.server_id)

    async def _pull_changes(self) -> dict:
        """Pull remote changes from server."""
        result = {'count': 0, 'conflicts': 0, 'errors': []}

        # Get changes since last sync
        params = {}
        if self._last_sync:
            params['updated_after'] = self._last_sync.isoformat()

        response = await self._transactions_api.list(
            page_size=100,
            filters=params
        )

        if not response.is_ok:
            result['errors'].append(f"Pull failed: {response.error_message}")
            return result

        for remote_tx in response.data.get('data', []):
            try:
                conflict = await self._apply_remote_change(remote_tx)
                if conflict:
                    result['conflicts'] += 1
                else:
                    result['count'] += 1
            except Exception as e:
                result['errors'].append(f"Failed to apply {remote_tx['id']}: {e}")

        return result

    async def _apply_remote_change(self, remote_data: dict) -> bool:
        """
        Apply remote change to local database.

        Returns:
            True if conflict occurred, False otherwise
        """
        with get_session() as session:
            local_tx = session.query(Transaction).filter(
                Transaction.server_id == remote_data['id']
            ).first()

            if local_tx:
                # Check for conflict
                if not local_tx.is_synced:
                    # Local has unsaved changes - conflict!
                    resolution = self._conflict_resolver.resolve(
                        local_data=local_tx.to_dict(),
                        remote_data=remote_data
                    )

                    if resolution == ConflictResolution.KEEP_REMOTE:
                        self._update_from_remote(local_tx, remote_data)
                        session.commit()
                    elif resolution == ConflictResolution.KEEP_LOCAL:
                        # Keep local, mark for push
                        self._queue.enqueue(QueuedOperation(
                            entity_type='transaction',
                            entity_id=str(local_tx.id),
                            operation='update'
                        ))

                    return True

                # No conflict, update local
                self._update_from_remote(local_tx, remote_data)
                session.commit()

            else:
                # New remote record, create locally
                new_tx = Transaction.from_api_response(
                    remote_data,
                    user_id=self._get_current_user_id()
                )
                session.add(new_tx)
                session.commit()

        return False

    def _update_from_remote(
        self,
        local: Transaction,
        remote: dict
    ) -> None:
        """Update local record with remote data."""
        local.amount = remote['amount']
        local.type = remote['type']
        local.description = remote.get('description', '')
        local.is_synced = True
        local.sync_status = 'synced'
```

---

## 6. Configuration Management

```python
"""
Configuration management using pydantic.
"""
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import json


class APIConfig(BaseModel):
    """API connection configuration."""
    base_url: str = "http://localhost:8000"
    timeout: int = 30
    verify_ssl: bool = True


class UIConfig(BaseModel):
    """UI configuration."""
    theme: str = "light"
    language: str = "en"
    currency: str = "EUR"
    window_geometry: Optional[bytes] = None


class SyncConfig(BaseModel):
    """Sync configuration."""
    auto_sync_enabled: bool = True
    auto_sync_interval: int = 900  # 15 minutes
    sync_on_startup: bool = True


class AppConfig(BaseSettings):
    """Application configuration."""

    # Constants
    APP_NAME: str = "Pecunia"
    APP_VERSION: str = "1.0.0"

    # Sub-configurations
    api: APIConfig = APIConfig()
    ui: UIConfig = UIConfig()
    sync: SyncConfig = SyncConfig()

    # Paths
    _config_dir: Optional[Path] = None
    _config_file: Optional[Path] = None

    class Config:
        env_prefix = "PECUNIA_"

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get platform-specific config directory."""
        import sys

        if sys.platform == 'win32':
            base = Path.home() / 'AppData' / 'Roaming'
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library' / 'Application Support'
        else:
            base = Path.home() / '.config'

        config_dir = base / 'Pecunia'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @classmethod
    def load(cls) -> 'AppConfig':
        """Load configuration from file."""
        config_file = cls.get_config_dir() / 'config.json'

        if config_file.exists():
            data = json.loads(config_file.read_text())
            return cls(**data)

        return cls()

    def save(self) -> None:
        """Save configuration to file."""
        config_file = self.get_config_dir() / 'config.json'

        data = self.model_dump(exclude={'_config_dir', '_config_file'})
        config_file.write_text(json.dumps(data, indent=2, default=str))

    def get_resource_path(self, resource: str) -> Path:
        """Get path to resource file."""
        # Development: relative to source
        dev_path = Path(__file__).parent.parent.parent / 'resources' / resource

        if dev_path.exists():
            return dev_path

        # Production: relative to executable
        import sys
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent / 'resources' / resource

        return dev_path


# Global config instance
config = AppConfig.load()
```

---

## 7. Error Handling

```python
"""
Custom exceptions for the application.
"""


class PecuniaError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NetworkError(PecuniaError):
    """Network-related errors."""

    def __init__(self, message: str = "Network error"):
        super().__init__(message, "NETWORK_ERROR")


class APIError(PecuniaError):
    """API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_data: dict = None
    ):
        super().__init__(message, "API_ERROR")
        self.status_code = status_code
        self.response_data = response_data or {}


class AuthenticationError(PecuniaError):
    """Authentication failures."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")


class ValidationError(PecuniaError):
    """Data validation errors."""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class SyncError(PecuniaError):
    """Synchronization errors."""

    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "SYNC_ERROR")
        self.operation = operation


class DatabaseError(PecuniaError):
    """Database-related errors."""

    def __init__(self, message: str):
        super().__init__(message, "DATABASE_ERROR")
```

---

## 8. Logging Standards

```python
"""
Logging configuration.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from .config import config


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure application logging.

    Creates:
    - Console handler (INFO+)
    - File handler (DEBUG+)
    - Security file handler (WARNING+)
    """
    # Create logs directory
    log_dir = config.get_config_dir() / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(console_handler)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(file_handler)

    # Security log
    security_handler = RotatingFileHandler(
        log_dir / 'security.log',
        maxBytes=10_000_000,
        backupCount=10
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))

    security_logger = logging.getLogger('pecunia.security')
    security_logger.addHandler(security_handler)
```

---

## 9. Testing Patterns

```python
"""
Test fixtures and utilities.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models.base import Base


@pytest.fixture
def db_engine():
    """Create in-memory test database."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_api_client():
    """Create mock API client."""
    client = Mock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def sample_transaction(db_session):
    """Create sample transaction."""
    from src.database.models import Transaction, TransactionType
    from datetime import date
    from decimal import Decimal

    tx = Transaction(
        user_id=1,
        amount=Decimal('100.00'),
        type=TransactionType.EXPENSE,
        description='Test transaction',
        transaction_date=date.today(),
    )
    db_session.add(tx)
    db_session.commit()
    return tx
```

---

## 10. Packaging and Distribution

### PyInstaller Configuration

```python
# build.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'PyQt6.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pecunia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pecunia',
)
```

### Build Script

```bash
#!/bin/bash
# build.sh - Build desktop application

set -e

echo "Building Pecunia Desktop..."

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Run tests
pytest tests/ -v

# Build executable
pyinstaller build.spec --clean

echo "Build complete: dist/Pecunia/"
```

---

**This document is MANDATORY for all desktop development in Pecunia.**

*Last reviewed: 2026-01-28*
