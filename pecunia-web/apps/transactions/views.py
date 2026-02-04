"""
Transactions API Views.

DRF ViewSets for transaction management with filtering, pagination, and statistics.

This module provides CRUD operations for financial transactions:

API Endpoints:
--------------
Transactions:
- GET    /api/v1/transactions/               - List (paginated, filterable)
- POST   /api/v1/transactions/               - Create new transaction
- GET    /api/v1/transactions/{uuid}/        - Retrieve single transaction
- PUT    /api/v1/transactions/{uuid}/        - Full update
- PATCH  /api/v1/transactions/{uuid}/        - Partial update
- DELETE /api/v1/transactions/{uuid}/        - Soft delete (is_deleted=True)
- GET    /api/v1/transactions/stats/         - Statistics for period
- GET    /api/v1/transactions/by_category/   - Grouped by category

Categories:
- GET    /api/v1/transactions/categories/    - List categories
- POST   /api/v1/transactions/categories/    - Create category
- PUT    /api/v1/transactions/categories/{uuid}/ - Update category

Recurring:
- GET    /api/v1/transactions/recurring/     - List recurring transactions
- POST   /api/v1/transactions/recurring/{id}/toggle_active/ - Toggle active

Filtering & Search:
-------------------
Query parameters for list endpoint:

| Parameter    | Description                          | Example                |
|--------------|--------------------------------------|------------------------|
| type         | Filter by type                       | ?type=expense          |
| category     | Filter by category UUID              | ?category=abc-123      |
| is_recurring | Filter recurring only                | ?is_recurring=true     |
| date_from    | Start date (inclusive)               | ?date_from=2026-01-01  |
| date_to      | End date (inclusive)                 | ?date_to=2026-01-31    |
| search       | Search description/merchant/ref      | ?search=grocery        |
| ordering     | Sort field (prefix - for desc)       | ?ordering=-amount      |

Pagination:
-----------
Default: 20 items per page, max 100
Response includes: count, next, previous, results

Statistics Endpoint:
-------------------
GET /api/v1/transactions/stats/?period=month

Periods: 'week', 'month', 'year', 'all'
Returns: total_income, total_expenses, net_balance, transaction_count

Performance Notes:
------------------
- List queries use select_related for category/bank_account
- Indexes on: user_id + transaction_date, user_id + type
- Stats queries use database aggregation (not Python loops)

See SCALABILITY_GUIDELINES.md for query optimization patterns.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import Transaction, TransactionCategory, RecurringTransaction
from .serializers import (
    TransactionSerializer,
    TransactionListSerializer,
    TransactionCategorySerializer,
    RecurringTransactionSerializer,
    TransactionStatsSerializer,
)


class TransactionCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for transaction category CRUD operations.

    Endpoints:
    - GET /api/v1/transactions/categories/ - List categories
    - POST /api/v1/transactions/categories/ - Create category
    - GET /api/v1/transactions/categories/{uuid}/ - Get category
    - PUT/PATCH /api/v1/transactions/categories/{uuid}/ - Update category
    - DELETE /api/v1/transactions/categories/{uuid}/ - Delete category
    """
    serializer_class = TransactionCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Return categories for the current user."""
        return TransactionCategory.objects.filter(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for transaction CRUD operations.

    Endpoints:
    - GET /api/v1/transactions/ - List transactions
    - POST /api/v1/transactions/ - Create transaction
    - GET /api/v1/transactions/{uuid}/ - Get transaction
    - PUT/PATCH /api/v1/transactions/{uuid}/ - Update transaction
    - DELETE /api/v1/transactions/{uuid}/ - Delete transaction
    - GET /api/v1/transactions/stats/ - Get transaction statistics
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'category', 'is_recurring']
    search_fields = ['description', 'merchant', 'reference']
    ordering_fields = ['transaction_date', 'amount', 'created_at']
    ordering = ['-transaction_date']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TransactionListSerializer
        return TransactionSerializer

    def get_queryset(self):
        """Return transactions for the current user."""
        queryset = Transaction.objects.filter(
            user=self.request.user
        ).select_related('category', 'bank_account')

        # Date range filter
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            queryset = queryset.filter(transaction_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(transaction_date__lte=date_to)

        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get aggregated transaction statistics for a time period.

        This endpoint provides summary statistics for the user's transactions,
        useful for dashboard displays and financial overview screens.

        Query Parameters:
        -----------------
        - period: Time range for statistics
            - 'week': Last 7 days
            - 'month': Current month (default)
            - 'year': Current year (from Jan 1)
            - 'all': All time (no date filter)

        Response:
        ---------
        {
            "total_income": 5000.00,      // Sum of income transactions
            "total_expenses": 3500.00,    // Sum of expense transactions
            "net_balance": 1500.00,       // income - expenses
            "transaction_count": 45,      // Total transactions in period
            "period_start": "2026-01-01", // Start of period (or "all")
            "period_end": "2026-01-28"    // End of period (today)
        }

        Performance Notes:
        ------------------
        - Uses database aggregation (SUM) for efficiency
        - Single query with filter, no N+1 issues
        - Consider caching for 'all' period on large datasets
        """
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
        elif period == 'all':
            start_date = None
        else:  # month
            start_date = today.replace(day=1)

        queryset = Transaction.objects.filter(user=request.user)
        if start_date:
            queryset = queryset.filter(transaction_date__gte=start_date)

        income = queryset.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0

        expenses = queryset.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0

        stats = {
            'total_income': income,
            'total_expenses': expenses,
            'net_balance': income - expenses,
            'transaction_count': queryset.count(),
            'period_start': start_date or 'all',
            'period_end': today,
        }

        serializer = TransactionStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get transactions grouped by category.

        Returns spending breakdown by category.
        """
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
        else:
            start_date = today.replace(day=1)

        queryset = Transaction.objects.filter(
            user=request.user,
            transaction_date__gte=start_date,
            type='expense'
        ).values(
            'category__id', 'category__name', 'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        return Response(list(queryset))


class RecurringTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for recurring transaction CRUD operations.

    Endpoints:
    - GET /api/v1/transactions/recurring/ - List recurring transactions
    - POST /api/v1/transactions/recurring/ - Create recurring transaction
    - GET /api/v1/transactions/recurring/{uuid}/ - Get recurring transaction
    - PUT/PATCH /api/v1/transactions/recurring/{uuid}/ - Update recurring transaction
    - DELETE /api/v1/transactions/recurring/{uuid}/ - Delete recurring transaction
    """
    serializer_class = RecurringTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'frequency', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['next_occurrence', 'amount', 'created_at']
    ordering = ['next_occurrence']

    def get_queryset(self):
        """Return recurring transactions for the current user."""
        return RecurringTransaction.objects.filter(
            user=self.request.user
        ).select_related('category')

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle the active status of a recurring transaction."""
        recurring = self.get_object()
        recurring.is_active = not recurring.is_active
        recurring.save()
        serializer = self.get_serializer(recurring)
        return Response(serializer.data)
