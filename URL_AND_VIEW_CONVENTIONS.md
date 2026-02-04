# URL and View Conventions - Pecunia Finance Platform

**Version**: 2.0
**Last Updated**: 2026-01-29
**Status**: MANDATORY - All apps MUST follow this convention

---

## Table of Contents

1. [Overview](#1-overview)
2. [URL Structure](#2-url-structure)
3. [API Versioning](#3-api-versioning)
4. [ViewSet Conventions](#4-viewset-conventions)
5. [URL Patterns](#5-url-patterns)
6. [Response Format](#6-response-format)
7. [Filtering & Pagination](#7-filtering--pagination)
8. [Error Handling](#8-error-handling)
9. [Authentication](#9-authentication)
10. [Implementation Examples](#10-implementation-examples)
11. [Checklist](#11-checklist)

---

## 1. Overview

### Purpose

Pecunia uses a **REST API architecture** with Django REST Framework (DRF) as the backend. This document defines the standards for:

- URL structure and naming
- ViewSet organization
- Response formats
- Error handling
- Authentication patterns

### Scope

These conventions apply to:

- **pecunia-web**: Django REST API (primary backend)
- **pecunia-desktop**: API client implementation
- **pecunia-mobile**: API client implementation

### Related Documents

| Document | Purpose |
|----------|---------|
| [MASTER_CONVENTIONS.md](./MASTER_CONVENTIONS.md) | Overall coding standards |
| [SECURITY_GUIDELINES.md](./SECURITY_GUIDELINES.md) | Authentication & security |
| [SCALABILITY_GUIDELINES.md](./SCALABILITY_GUIDELINES.md) | Performance optimization |

---

## 2. URL Structure

### Base URL Format

```
Production:  https://api.pecunia.com/api/v1/
Staging:     https://staging-api.pecunia.com/api/v1/
Development: http://localhost:8000/api/v1/
```

### URL Pattern Convention

```
/api/v{version}/{app-name}/{resource-name}/
/api/v{version}/{app-name}/{resource-name}/{uuid}/
/api/v{version}/{app-name}/{resource-name}/{uuid}/{action}/
```

### Naming Rules

| Element | Convention | Example |
|---------|------------|---------|
| App name | kebab-case | `banking`, `transactions` |
| Resource name | kebab-case, plural | `transactions`, `bank-accounts` |
| UUID | Standard UUID format | `550e8400-e29b-41d4-a716-446655440000` |
| Action name | kebab-case, verb | `sync`, `archive`, `toggle-active` |

### URL Examples

```
# Transactions
GET    /api/v1/transactions/                     # List all transactions
POST   /api/v1/transactions/                     # Create transaction
GET    /api/v1/transactions/{uuid}/              # Get single transaction
PUT    /api/v1/transactions/{uuid}/              # Full update
PATCH  /api/v1/transactions/{uuid}/              # Partial update
DELETE /api/v1/transactions/{uuid}/              # Delete transaction
GET    /api/v1/transactions/stats/               # Get statistics
GET    /api/v1/transactions/by-category/         # Group by category

# Budgets
GET    /api/v1/budgets/                          # List budgets
POST   /api/v1/budgets/                          # Create budget
GET    /api/v1/budgets/{uuid}/                   # Get budget details
GET    /api/v1/budgets/{uuid}/progress/          # Get budget progress
GET    /api/v1/budgets/current/                  # Get active budgets
POST   /api/v1/budgets/{uuid}/recalculate/       # Recalculate totals

# Banking
GET    /api/v1/banking/connections/              # List bank connections
POST   /api/v1/banking/connections/              # Initiate connection
DELETE /api/v1/banking/connections/{uuid}/       # Disconnect
POST   /api/v1/banking/connections/{uuid}/sync/  # Trigger sync
GET    /api/v1/banking/accounts/                 # List bank accounts
GET    /api/v1/banking/accounts/summary/         # Balance summary

# Authentication
POST   /api/v1/auth/register/                    # Create account
POST   /api/v1/auth/login/                       # Obtain tokens
POST   /api/v1/auth/refresh/                     # Refresh token
POST   /api/v1/auth/logout/                      # Invalidate tokens
POST   /api/v1/auth/password-reset/              # Request reset
POST   /api/v1/auth/2fa/enable/                  # Enable 2FA
POST   /api/v1/auth/2fa/verify/                  # Verify 2FA code

# Sync (for desktop/mobile clients)
POST   /api/v1/sync/push/                        # Push local changes
GET    /api/v1/sync/pull/                        # Pull server changes
POST   /api/v1/sync/batch/                       # Batch sync operation
GET    /api/v1/sync/status/                      # Get sync status
```

---

## 3. API Versioning

### Version Strategy

- Version in URL path: `/api/v1/`, `/api/v2/`
- Breaking changes require new version
- Old versions supported minimum 12 months
- Deprecation header in responses

### Version Headers

```http
# Response headers for deprecated endpoints
Deprecation: true
Sunset: Sat, 01 Jan 2027 00:00:00 GMT
Link: </api/v2/transactions/>; rel="successor-version"
```

### Breaking vs Non-Breaking Changes

**Non-Breaking (same version)**:
- Adding new optional fields
- Adding new endpoints
- Adding new query parameters
- Fixing bugs

**Breaking (new version required)**:
- Removing or renaming fields
- Changing field types
- Removing endpoints
- Changing authentication
- Modifying response structure

---

## 4. ViewSet Conventions

### File Structure

```
apps/
├── transactions/
│   ├── __init__.py
│   ├── models.py           # Database models
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # ViewSets and APIViews
│   ├── urls.py             # URL routing
│   ├── filters.py          # Django-filter classes
│   ├── permissions.py      # Custom permissions
│   └── tasks.py            # Celery tasks
```

### ViewSet Template

```python
"""
Transactions API Views.

DRF ViewSets for transaction management with filtering, pagination, and statistics.

Endpoints:
----------
- GET    /api/v1/transactions/               - List (paginated, filterable)
- POST   /api/v1/transactions/               - Create new transaction
- GET    /api/v1/transactions/{uuid}/        - Retrieve single transaction
- PUT    /api/v1/transactions/{uuid}/        - Full update
- PATCH  /api/v1/transactions/{uuid}/        - Partial update
- DELETE /api/v1/transactions/{uuid}/        - Soft delete
- GET    /api/v1/transactions/stats/         - Statistics for period
- GET    /api/v1/transactions/by-category/   - Grouped by category

Filtering:
----------
Query parameters for list endpoint:

| Parameter    | Description                          | Example                |
|--------------|--------------------------------------|------------------------|
| type         | Filter by type                       | ?type=expense          |
| category     | Filter by category UUID              | ?category=abc-123      |
| date_from    | Start date (inclusive)               | ?date_from=2026-01-01  |
| date_to      | End date (inclusive)                 | ?date_to=2026-01-31    |
| search       | Search description/merchant          | ?search=grocery        |
| ordering     | Sort field (prefix - for desc)       | ?ordering=-amount      |

Performance:
-----------
- Uses select_related for category/bank_account
- Indexed on: user_id + transaction_date, user_id + type
- Statistics use database aggregation
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Transaction
from .serializers import (
    TransactionSerializer,
    TransactionListSerializer,
    TransactionCreateSerializer,
)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for transaction CRUD operations.

    Provides standard CRUD plus custom actions for statistics
    and category grouping.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'category', 'is_recurring']
    search_fields = ['description', 'merchant', 'reference']
    ordering_fields = ['transaction_date', 'amount', 'created_at']
    ordering = ['-transaction_date']
    lookup_field = 'pk'

    def get_queryset(self):
        """
        Return transactions for the current user.

        Optimizations:
        - select_related for foreign keys
        - Date range filtering via query params
        """
        return Transaction.objects.filter(
            user=self.request.user
        ).select_related('category', 'bank_account')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TransactionListSerializer
        if self.action == 'create':
            return TransactionCreateSerializer
        return TransactionSerializer

    def perform_create(self, serializer):
        """Set user on creation."""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get aggregated transaction statistics.

        Query Parameters:
            period: 'week', 'month', 'year', 'all' (default: month)

        Returns:
            {
                "total_income": 5000.00,
                "total_expenses": 3500.00,
                "net_balance": 1500.00,
                "transaction_count": 45,
                "period_start": "2026-01-01",
                "period_end": "2026-01-29"
            }
        """
        # Implementation...
        pass

    @action(detail=False, methods=['get'], url_path='by-category')
    def by_category(self, request):
        """
        Get transactions grouped by category.

        Returns spending breakdown by category for the period.
        """
        # Implementation...
        pass
```

### Serializer Convention

```python
"""
Transaction Serializers.

DRF serializers for transaction data transformation.

Serializer Types:
-----------------
- TransactionSerializer: Full detail (retrieve/update)
- TransactionListSerializer: Minimal fields (list view)
- TransactionCreateSerializer: Validated input (create)
"""
from rest_framework import serializers
from .models import Transaction, TransactionCategory


class TransactionCategorySerializer(serializers.ModelSerializer):
    """Nested serializer for category in transaction."""

    class Meta:
        model = TransactionCategory
        fields = ['id', 'name', 'color', 'icon']


class TransactionListSerializer(serializers.ModelSerializer):
    """
    Minimal transaction serializer for list views.

    Optimized for performance with fewer fields and
    minimal nested data.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'amount',
            'type',
            'description',
            'category_name',
            'transaction_date',
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """
    Full transaction serializer for detail views.

    Includes all fields and nested category data.
    """
    category = TransactionCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'amount',
            'type',
            'description',
            'category',
            'category_id',
            'bank_account',
            'transaction_date',
            'is_recurring',
            'tags',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Transaction serializer for creation.

    Validates input and handles category assignment.
    """

    class Meta:
        model = Transaction
        fields = [
            'amount',
            'type',
            'description',
            'category',
            'transaction_date',
            'is_recurring',
            'tags',
            'notes',
        ]

    def validate_amount(self, value):
        """Ensure amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value
```

---

## 5. URL Patterns

### urls.py Structure

```python
"""
Transactions URL Configuration.

API Endpoints:
- /api/v1/transactions/ - Transaction CRUD
- /api/v1/transactions/categories/ - Category management
- /api/v1/transactions/recurring/ - Recurring transactions

URL Namespaces:
- api:transactions:transaction-list
- api:transactions:transaction-detail
- api:transactions:transaction-stats
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# =============================================================================
# API Router Configuration
# =============================================================================

router = DefaultRouter()

# Main transaction ViewSet
router.register(
    r'',
    views.TransactionViewSet,
    basename='transaction'
)

# Category ViewSet
router.register(
    r'categories',
    views.TransactionCategoryViewSet,
    basename='category'
)

# Recurring transactions ViewSet
router.register(
    r'recurring',
    views.RecurringTransactionViewSet,
    basename='recurring'
)

# =============================================================================
# URL Patterns
# =============================================================================

app_name = 'transactions'

urlpatterns = [
    path('', include(router.urls)),
]
```

### Project-Level URL Configuration

```python
"""
Main URL Configuration for Pecunia API.

API Structure:
/api/v1/auth/          - Authentication
/api/v1/transactions/  - Transactions
/api/v1/budgets/       - Budgets
/api/v1/banking/       - Banking integration
/api/v1/sync/          - Synchronization
/api/v1/ai/            - AI features
/api/v1/subscriptions/ - Billing
"""
from django.urls import path, include

# =============================================================================
# API v1 URL Patterns
# =============================================================================

api_v1_patterns = [
    path('auth/', include('apps.accounts.urls', namespace='accounts')),
    path('transactions/', include('apps.transactions.urls', namespace='transactions')),
    path('budgets/', include('apps.budgets.urls', namespace='budgets')),
    path('banking/', include('apps.banking.urls', namespace='banking')),
    path('sync/', include('apps.sync.urls', namespace='sync')),
    path('ai/', include('apps.ai.urls', namespace='ai')),
    path('subscriptions/', include('apps.subscriptions.urls', namespace='subscriptions')),
]

# =============================================================================
# Main URL Patterns
# =============================================================================

urlpatterns = [
    # API endpoints
    path('api/v1/', include((api_v1_patterns, 'api'), namespace='v1')),

    # Health check (no auth required)
    path('health/', include('apps.core.health_urls')),
]
```

---

## 6. Response Format

### Success Response (Single Object)

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": "125.50",
    "type": "expense",
    "description": "Grocery shopping",
    "category": {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "name": "Groceries",
      "color": "#4CAF50"
    },
    "transaction_date": "2026-01-29",
    "created_at": "2026-01-29T14:30:00Z",
    "updated_at": "2026-01-29T14:30:00Z"
  }
}
```

### Success Response (Collection)

```json
{
  "count": 150,
  "next": "https://api.pecunia.com/api/v1/transactions/?page=2",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "amount": "125.50",
      "type": "expense",
      "description": "Grocery shopping",
      "transaction_date": "2026-01-29"
    }
  ]
}
```

### Success Response (Action)

```json
{
  "status": "success",
  "message": "Budget recalculated successfully",
  "data": {
    "planned_amount": "1000.00",
    "spent_amount": "750.00",
    "remaining_amount": "250.00"
  }
}
```

### Created Response (201)

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": "125.50",
    "type": "expense"
  },
  "message": "Transaction created successfully"
}
```

---

## 7. Filtering & Pagination

### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `page` | int | Page number (1-indexed) | `?page=2` |
| `page_size` | int | Items per page (max 100) | `?page_size=50` |
| `ordering` | string | Sort field(s), `-` for desc | `?ordering=-created_at` |
| `search` | string | Full-text search | `?search=grocery` |
| `{field}` | varies | Field-specific filter | `?type=expense` |
| `{field}__gte` | varies | Greater than or equal | `?amount__gte=100` |
| `{field}__lte` | varies | Less than or equal | `?amount__lte=500` |

### Date Range Filtering

```
# Transactions in January 2026
GET /api/v1/transactions/?date_from=2026-01-01&date_to=2026-01-31

# Transactions this month
GET /api/v1/transactions/?date_from=2026-01-01

# Transactions before specific date
GET /api/v1/transactions/?date_to=2026-01-15
```

### Sorting

```
# Sort by date descending (newest first)
GET /api/v1/transactions/?ordering=-transaction_date

# Sort by amount ascending
GET /api/v1/transactions/?ordering=amount

# Multiple sort fields
GET /api/v1/transactions/?ordering=-transaction_date,amount
```

### Pagination Settings

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
}
```

---

## 8. Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid transaction data",
    "details": {
      "amount": ["Amount must be positive."],
      "category": ["Category not found."]
    }
  }
}
```

### HTTP Status Codes

| Code | Name | Usage |
|------|------|-------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST creating resource |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Malformed request |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Sync conflict |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400/422 | Input validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | No token provided |
| `INVALID_TOKEN` | 401 | Token expired/invalid |
| `TOKEN_EXPIRED` | 401 | Access token expired |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `SUBSCRIPTION_REQUIRED` | 403 | Feature requires subscription |
| `RESOURCE_NOT_FOUND` | 404 | Resource doesn't exist |
| `SYNC_CONFLICT` | 409 | Data conflict during sync |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal error |

### Exception Handler

```python
# apps/core/exceptions.py
"""
Custom exception handling for Pecunia API.

Provides consistent error response format across all endpoints.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.

    Returns standardized error format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable message",
            "details": {...}  # Optional
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'error')
        error_message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)

        response.data = {
            'error': {
                'code': error_code.upper(),
                'message': error_message,
            }
        }

        # Add field-specific errors for validation
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            response.data['error']['details'] = exc.detail

    return response
```

---

## 9. Authentication

### Token Format

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Login Flow

```http
# 1. Login request
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secretpassword"
}

# 2. Response (without 2FA)
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "John Doe"
  }
}

# 3. Response (with 2FA required)
{
  "requires_2fa": true,
  "temp_token": "temporary-token-for-2fa"
}

# 4. 2FA verification
POST /api/v1/auth/2fa/verify/
{
  "temp_token": "temporary-token-for-2fa",
  "code": "123456"
}
```

### Token Refresh

```http
POST /api/v1/auth/refresh/
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

# Response
{
  "access_token": "new-access-token...",
  "expires_in": 900
}
```

### Token Lifetimes

| Token Type | Lifetime | Notes |
|------------|----------|-------|
| Access Token | 15 minutes | Short-lived for security |
| Refresh Token | 7 days | Rotated on each refresh |
| 2FA Temp Token | 5 minutes | One-time use |

---

## 10. Implementation Examples

### Complete ViewSet Example

```python
"""
Budget API Views.

Full example of ViewSet with custom actions, filtering, and pagination.
"""
from decimal import Decimal
from django.db.models import Sum, F
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Budget, BudgetItem
from .serializers import (
    BudgetSerializer,
    BudgetListSerializer,
    BudgetCreateSerializer,
    BudgetProgressSerializer,
)


class BudgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for budget CRUD operations.

    Endpoints:
    - GET    /api/v1/budgets/                  - List budgets
    - POST   /api/v1/budgets/                  - Create budget
    - GET    /api/v1/budgets/{uuid}/           - Get budget
    - PUT    /api/v1/budgets/{uuid}/           - Update budget
    - PATCH  /api/v1/budgets/{uuid}/           - Partial update
    - DELETE /api/v1/budgets/{uuid}/           - Delete budget
    - GET    /api/v1/budgets/current/          - Active budgets
    - GET    /api/v1/budgets/{uuid}/progress/  - Budget progress
    - POST   /api/v1/budgets/{uuid}/recalculate/ - Recalculate totals
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['period_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'end_date', 'total_planned_amount']
    ordering = ['-start_date']

    def get_queryset(self):
        """Return budgets for current user with optimized queries."""
        return Budget.objects.filter(
            user=self.request.user
        ).prefetch_related('items', 'items__category')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BudgetListSerializer
        if self.action == 'create':
            return BudgetCreateSerializer
        if self.action == 'progress':
            return BudgetProgressSerializer
        return BudgetSerializer

    def perform_create(self, serializer):
        """Set user on creation."""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get current active budgets.

        Returns budgets where today is within the budget period.
        """
        today = timezone.now().date()
        budgets = self.get_queryset().filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        )
        serializer = self.get_serializer(budgets, many=True)
        return Response({'data': serializer.data})

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Get detailed progress for a budget.

        Returns:
        - Current spending vs planned
        - Daily spending rate
        - Projected end-of-period spending
        - Per-category breakdown
        """
        budget = self.get_object()
        today = timezone.now().date()

        # Calculate days
        total_days = (budget.end_date - budget.start_date).days + 1
        days_elapsed = max((today - budget.start_date).days + 1, 0)
        days_remaining = max(total_days - days_elapsed, 0)

        # Calculate rates
        daily_budget = budget.total_planned_amount / total_days
        daily_spending = budget.total_spent_amount / days_elapsed if days_elapsed > 0 else Decimal('0')
        projected_spending = budget.total_spent_amount + (daily_spending * days_remaining)

        progress_data = {
            'budget': BudgetSerializer(budget).data,
            'progress': {
                'planned_amount': budget.total_planned_amount,
                'spent_amount': budget.total_spent_amount,
                'remaining_amount': budget.remaining_amount,
                'progress_percentage': budget.progress_percentage,
                'days_remaining': days_remaining,
                'daily_budget': daily_budget,
                'daily_spending_rate': daily_spending,
                'projected_spending': projected_spending,
                'is_on_track': budget.total_spent_amount <= (daily_budget * days_elapsed),
            }
        }

        return Response({'data': progress_data})

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate budget totals from items.

        Useful after bulk item updates.
        """
        budget = self.get_object()
        budget.recalculate_totals()

        serializer = self.get_serializer(budget)
        return Response({
            'status': 'success',
            'message': 'Budget recalculated successfully',
            'data': serializer.data
        })
```

### Client Implementation (Desktop)

```python
"""
Budget API Client for Pecunia Desktop.

Example of how to consume the Budget API from the desktop application.
"""
from typing import List, Optional
from datetime import date
from dataclasses import dataclass
from decimal import Decimal

from api.client import APIClient, APIResponse


@dataclass
class Budget:
    """Budget data model for desktop app."""
    id: str
    name: str
    total_planned_amount: Decimal
    total_spent_amount: Decimal
    start_date: date
    end_date: date
    is_active: bool

    @property
    def remaining_amount(self) -> Decimal:
        return self.total_planned_amount - self.total_spent_amount

    @property
    def progress_percentage(self) -> float:
        if self.total_planned_amount == 0:
            return 0.0
        return float(self.total_spent_amount / self.total_planned_amount * 100)


class BudgetAPI:
    """
    Budget API client.

    Usage:
        api = BudgetAPI(client)
        budgets = await api.list()
        budget = await api.get(budget_id)
        progress = await api.get_progress(budget_id)
    """

    def __init__(self, client: APIClient):
        self.client = client
        self.base_path = '/api/v1/budgets/'

    async def list(
        self,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> APIResponse:
        """
        List budgets with optional filtering.

        Args:
            is_active: Filter by active status
            page: Page number
            page_size: Items per page

        Returns:
            APIResponse with paginated budget list
        """
        params = {'page': page, 'page_size': page_size}
        if is_active is not None:
            params['is_active'] = is_active

        return await self.client.get(self.base_path, params=params)

    async def get(self, budget_id: str) -> APIResponse:
        """Get a single budget by ID."""
        return await self.client.get(f'{self.base_path}{budget_id}/')

    async def create(self, data: dict) -> APIResponse:
        """Create a new budget."""
        return await self.client.post(self.base_path, data=data)

    async def update(self, budget_id: str, data: dict) -> APIResponse:
        """Update a budget."""
        return await self.client.patch(f'{self.base_path}{budget_id}/', data=data)

    async def delete(self, budget_id: str) -> APIResponse:
        """Delete a budget."""
        return await self.client.delete(f'{self.base_path}{budget_id}/')

    async def get_current(self) -> APIResponse:
        """Get currently active budgets."""
        return await self.client.get(f'{self.base_path}current/')

    async def get_progress(self, budget_id: str) -> APIResponse:
        """Get detailed progress for a budget."""
        return await self.client.get(f'{self.base_path}{budget_id}/progress/')

    async def recalculate(self, budget_id: str) -> APIResponse:
        """Recalculate budget totals."""
        return await self.client.post(f'{self.base_path}{budget_id}/recalculate/')
```

---

## 11. Checklist

### When Creating a New API Endpoint

#### Models & Data
- [ ] Create models in `models.py`
- [ ] Add indexes for query optimization
- [ ] Create and run migrations
- [ ] Add model methods and properties

#### Serializers
- [ ] Create serializers in `serializers.py`
- [ ] Use different serializers for list/detail/create
- [ ] Add field validation
- [ ] Include nested serializers where needed

#### Views
- [ ] Create ViewSet or APIView in `views.py`
- [ ] Add comprehensive docstring with endpoints
- [ ] Configure permissions
- [ ] Configure filtering, search, ordering
- [ ] Add custom actions for non-CRUD operations
- [ ] Optimize queries (select_related, prefetch_related)

#### URLs
- [ ] Register in router or add path
- [ ] Follow URL naming conventions
- [ ] Set app_name for namespace

#### Documentation
- [ ] Document all endpoints in docstrings
- [ ] List query parameters
- [ ] Document response format
- [ ] Add examples

#### Testing
- [ ] Write unit tests for serializers
- [ ] Write integration tests for ViewSets
- [ ] Test edge cases and error handling
- [ ] Test permissions

---

## Summary

### Key Principles

| Principle | Description |
|-----------|-------------|
| **RESTful** | Follow REST conventions for URLs and methods |
| **Consistent** | Same patterns across all endpoints |
| **Documented** | Every endpoint has clear documentation |
| **Secure** | Authentication on all non-public endpoints |
| **Performant** | Optimize queries, use pagination |
| **Versioned** | API versions in URL path |

### Quick Reference

```
URL Pattern:    /api/v1/{app}/{resource}/
URL Style:      kebab-case, plural resources
Auth Header:    Authorization: Bearer <token>
Content Type:   application/json
Response:       { "data": {...} } or { "error": {...} }
Pagination:     ?page=1&page_size=20
Filtering:      ?field=value&field__gte=value
Ordering:       ?ordering=-created_at,name
```

---

**This convention is MANDATORY for all API development in Pecunia.**

*Last reviewed: 2026-01-29*
