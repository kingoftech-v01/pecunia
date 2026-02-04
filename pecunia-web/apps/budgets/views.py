"""
Budgets API Views.

DRF ViewSets for budget management.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Budget, BudgetItem
from .serializers import (
    BudgetSerializer,
    BudgetListSerializer,
    BudgetWithItemsSerializer,
    BudgetItemSerializer,
    BudgetStatsSerializer,
    BudgetProgressSerializer,
    CategoryBudgetSummarySerializer,
)


class BudgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for budget CRUD operations.

    Endpoints:
    - GET /api/v1/budgets/ - List budgets
    - POST /api/v1/budgets/ - Create budget
    - GET /api/v1/budgets/{uuid}/ - Get budget
    - PUT/PATCH /api/v1/budgets/{uuid}/ - Update budget
    - DELETE /api/v1/budgets/{uuid}/ - Delete budget
    - GET /api/v1/budgets/stats/ - Get budget statistics
    - GET /api/v1/budgets/current/ - Get current active budgets
    - GET /api/v1/budgets/{uuid}/progress/ - Get budget progress details
    - POST /api/v1/budgets/{uuid}/recalculate/ - Recalculate budget totals
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['period_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'end_date', 'total_planned_amount', 'created_at']
    ordering = ['-start_date']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BudgetListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return BudgetWithItemsSerializer
        return BudgetSerializer

    def get_queryset(self):
        """Return budgets for the current user."""
        queryset = Budget.objects.filter(
            user=self.request.user
        ).prefetch_related('items', 'items__category')

        # Date range filter
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(end_date__lte=date_to)

        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter == 'over_budget':
            queryset = queryset.filter(
                total_spent_amount__gt=F('total_planned_amount')
            )
        elif status_filter == 'on_track':
            queryset = queryset.filter(
                total_spent_amount__lte=F('total_planned_amount')
            )

        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get budget statistics for a period.

        Query params:
        - period: 'week', 'month', 'year', 'all' (default: month)
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

        queryset = Budget.objects.filter(user=request.user)
        if start_date:
            queryset = queryset.filter(
                Q(start_date__gte=start_date) | Q(end_date__gte=start_date)
            )

        totals = queryset.aggregate(
            total_planned=Sum('total_planned_amount'),
            total_spent=Sum('total_spent_amount')
        )

        total_planned = totals['total_planned'] or Decimal('0.00')
        total_spent = totals['total_spent'] or Decimal('0.00')
        total_remaining = total_planned - total_spent

        overall_progress = Decimal('0.00')
        if total_planned > 0:
            overall_progress = (total_spent / total_planned) * 100

        # Count budgets by status
        budgets_over = queryset.filter(
            total_spent_amount__gt=F('total_planned_amount')
        ).count()

        # Near limit: within 20% of limit
        budgets_near = queryset.filter(
            total_spent_amount__gte=F('total_planned_amount') * Decimal('0.8'),
            total_spent_amount__lte=F('total_planned_amount')
        ).count()

        stats = {
            'total_budgets': queryset.count(),
            'active_budgets': queryset.filter(is_active=True).count(),
            'total_planned': total_planned,
            'total_spent': total_spent,
            'total_remaining': total_remaining,
            'overall_progress': overall_progress,
            'budgets_over_limit': budgets_over,
            'budgets_near_limit': budgets_near,
            'period_start': start_date,
            'period_end': today,
        }

        serializer = BudgetStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get current active budgets.

        Returns budgets that include today's date.
        """
        today = timezone.now().date()
        queryset = Budget.objects.filter(
            user=request.user,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).prefetch_related('items', 'items__category')

        serializer = BudgetSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Get detailed progress for a specific budget.

        Includes daily spending rate and projections.
        """
        budget = self.get_object()
        today = timezone.now().date()

        # Calculate days in budget period
        total_days = (budget.end_date - budget.start_date).days + 1
        days_elapsed = min(
            max((today - budget.start_date).days + 1, 0),
            total_days
        )
        days_remaining = max(total_days - days_elapsed, 0)

        # Calculate daily metrics
        daily_budget = budget.total_planned_amount / total_days if total_days > 0 else Decimal('0.00')
        daily_spending_rate = budget.total_spent_amount / days_elapsed if days_elapsed > 0 else Decimal('0.00')

        # Project spending to end of period
        projected_spending = budget.total_spent_amount + (daily_spending_rate * days_remaining)

        # Determine if on track
        expected_spent = daily_budget * days_elapsed
        is_on_track = budget.total_spent_amount <= expected_spent

        progress_data = {
            'budget_id': budget.id,
            'budget_name': budget.name,
            'period_type': budget.period_type,
            'planned_amount': budget.total_planned_amount,
            'spent_amount': budget.total_spent_amount,
            'remaining_amount': budget.remaining_amount,
            'progress_percentage': budget.progress_percentage,
            'days_remaining': days_remaining,
            'daily_budget': daily_budget,
            'daily_spending_rate': daily_spending_rate,
            'projected_spending': projected_spending,
            'is_on_track': is_on_track,
            'items': BudgetItemSerializer(budget.items.all(), many=True).data,
        }

        serializer = BudgetProgressSerializer(progress_data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate budget totals from items.

        Useful after bulk updates to items.
        """
        budget = self.get_object()
        budget.recalculate_totals()
        serializer = self.get_serializer(budget)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get budget allocation by category.

        Returns spending breakdown by category across all active budgets.
        """
        today = timezone.now().date()

        # Get current budget items grouped by category
        items = BudgetItem.objects.filter(
            budget__user=request.user,
            budget__is_active=True,
            budget__start_date__lte=today,
            budget__end_date__gte=today
        ).values(
            'category__id', 'category__name', 'category__color'
        ).annotate(
            planned_amount=Sum('planned_amount'),
            spent_amount=Sum('spent_amount')
        ).order_by('-planned_amount')

        result = []
        for item in items:
            planned = item['planned_amount'] or Decimal('0.00')
            spent = item['spent_amount'] or Decimal('0.00')
            remaining = planned - spent
            progress = (spent / planned * 100) if planned > 0 else Decimal('0.00')

            result.append({
                'category_id': item['category__id'],
                'category_name': item['category__name'] or 'Uncategorized',
                'category_color': item['category__color'] or '#6366f1',
                'planned_amount': planned,
                'spent_amount': spent,
                'remaining_amount': remaining,
                'progress_percentage': progress,
                'is_over_budget': spent > planned,
            })

        serializer = CategoryBudgetSummarySerializer(result, many=True)
        return Response(serializer.data)


class BudgetItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for budget item CRUD operations.

    Endpoints:
    - GET /api/v1/budgets/items/ - List all budget items
    - POST /api/v1/budgets/items/ - Create budget item
    - GET /api/v1/budgets/items/{uuid}/ - Get budget item
    - PUT/PATCH /api/v1/budgets/items/{uuid}/ - Update budget item
    - DELETE /api/v1/budgets/items/{uuid}/ - Delete budget item
    - POST /api/v1/budgets/items/{uuid}/update-spent/ - Update spent amount
    """
    serializer_class = BudgetItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['budget', 'category', 'is_active']
    ordering_fields = ['planned_amount', 'spent_amount', 'created_at']
    ordering = ['-planned_amount']

    def get_queryset(self):
        """Return budget items for the current user's budgets."""
        return BudgetItem.objects.filter(
            budget__user=self.request.user
        ).select_related('budget', 'category')

    @action(detail=True, methods=['post'], url_path='update-spent')
    def update_spent(self, request, pk=None):
        """
        Update the spent amount for a budget item.

        Request body:
        - amount: The new spent amount or amount to add
        - mode: 'set' (default) or 'add'
        """
        item = self.get_object()
        amount = request.data.get('amount')
        mode = request.data.get('mode', 'set')

        if amount is None:
            return Response(
                {'detail': 'Amount is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response(
                {'detail': 'Invalid amount value.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if mode == 'add':
            item.spent_amount += amount
        else:
            item.spent_amount = amount

        item.save()
        serializer = self.get_serializer(item)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        Bulk update spent amounts for multiple budget items.

        Request body:
        - items: List of {id, spent_amount} objects
        """
        items_data = request.data.get('items', [])

        if not items_data:
            return Response(
                {'detail': 'Items list is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_items = []
        for item_data in items_data:
            try:
                item = BudgetItem.objects.get(
                    id=item_data['id'],
                    budget__user=request.user
                )
                item.spent_amount = Decimal(str(item_data['spent_amount']))
                item.save()
                updated_items.append(item)
            except (BudgetItem.DoesNotExist, KeyError, ValueError):
                continue

        serializer = self.get_serializer(updated_items, many=True)
        return Response(serializer.data)
