"""
Transaction Analytics Service.

Advanced analytics and metrics for financial transactions.
Provides spending analysis, income tracking, and trend predictions.
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from django.db.models import (
    Sum, Count, Avg, F, Q, Window, Case, When, Value,
    DecimalField, CharField
)
from django.db.models.functions import (
    TruncDay, TruncWeek, TruncMonth, TruncYear,
    ExtractMonth, ExtractYear, Coalesce
)
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

from .models import Transaction, TransactionCategory, RecurringTransaction


class AnalyticsPeriod:
    """
    Period helper for analytics date ranges.

    Provides consistent date range calculations across analytics methods.
    """

    PERIOD_CHOICES = ['week', 'month', 'quarter', 'year', 'all', 'custom']

    def __init__(
        self,
        period: str = 'month',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ):
        self.period = period
        self.custom_start = start_date
        self.custom_end = end_date
        self._today = timezone.now().date()

    @property
    def start_date(self) -> Optional[date]:
        """Calculate start date based on period."""
        if self.period == 'custom' and self.custom_start:
            return self.custom_start
        elif self.period == 'week':
            return self._today - timedelta(days=7)
        elif self.period == 'month':
            return self._today.replace(day=1)
        elif self.period == 'quarter':
            # (month-1)//3 gives quarter index 0-3; *3+1 converts back to month 1,4,7,10.
            quarter_start_month = ((self._today.month - 1) // 3) * 3 + 1
            return self._today.replace(month=quarter_start_month, day=1)
        elif self.period == 'year':
            return self._today.replace(month=1, day=1)
        elif self.period == 'all':
            return None
        return self._today.replace(day=1)

    @property
    def end_date(self) -> date:
        """Calculate end date based on period."""
        if self.period == 'custom' and self.custom_end:
            return self.custom_end
        return self._today

    @property
    def previous_start_date(self) -> Optional[date]:
        """Calculate start date for previous period (for comparison)."""
        if self.period == 'all' or not self.start_date:
            return None

        delta = self.end_date - self.start_date
        return self.start_date - delta - timedelta(days=1)

    @property
    def previous_end_date(self) -> Optional[date]:
        """Calculate end date for previous period."""
        if self.start_date:
            return self.start_date - timedelta(days=1)
        return None

    def get_cache_key_suffix(self) -> str:
        """Generate cache key suffix for this period."""
        if self.period == 'custom':
            return f"custom_{self.custom_start}_{self.custom_end}"
        return f"{self.period}_{self._today}"


class TransactionAnalytics:
    """
    Transaction analytics service.

    Provides comprehensive analytics for user transactions including:
    - Spending by category
    - Income vs expense comparison
    - Daily/monthly balance tracking
    - Merchant analysis
    - Recurring transaction insights
    """

    CACHE_TIMEOUT = 60 * 15  # 15 minutes

    def __init__(self, user):
        self.user = user
        self._base_queryset = Transaction.objects.filter(user=user)

    def _get_cache_key(self, method_name: str, period: AnalyticsPeriod) -> str:
        """Generate cache key for analytics results."""
        return f"analytics:{self.user.id}:{method_name}:{period.get_cache_key_suffix()}"

    def _apply_period_filter(self, queryset, period: AnalyticsPeriod):
        """Apply date range filter to queryset."""
        if period.start_date:
            queryset = queryset.filter(transaction_date__gte=period.start_date)
        if period.end_date:
            queryset = queryset.filter(transaction_date__lte=period.end_date)
        return queryset

    def get_spending_by_category(
        self,
        period: str = 'month',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
        include_uncategorized: bool = True
    ) -> Dict[str, Any]:
        """
        Get spending breakdown by category.

        Args:
            period: Time period ('week', 'month', 'quarter', 'year', 'all', 'custom')
            start_date: Start date for custom period
            end_date: End date for custom period
            limit: Maximum number of categories to return
            include_uncategorized: Include transactions without category

        Returns:
            Dict with categories, totals, and Chart.js compatible data
        """
        analytics_period = AnalyticsPeriod(period, start_date, end_date)
        cache_key = self._get_cache_key('spending_by_category', analytics_period)

        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        queryset = self._base_queryset.filter(type='expense')
        queryset = self._apply_period_filter(queryset, analytics_period)

        # Group by category
        category_spending = queryset.values(
            'category__id',
            'category__name',
            'category__color',
            'category__icon'
        ).annotate(
            total=Sum('amount'),
            count=Count('id'),
            avg_amount=Avg('amount')
        ).order_by('-total')

        categories = []
        total_spending = Decimal('0')

        for item in category_spending[:limit]:
            category_name = item['category__name'] or 'Non catégorisé'
            if not include_uncategorized and not item['category__name']:
                continue

            total = item['total'] or Decimal('0')
            total_spending += total

            categories.append({
                'id': str(item['category__id']) if item['category__id'] else None,
                'name': category_name,
                'color': item['category__color'] or '#9CA3AF',
                'icon': item['category__icon'] or 'tag',
                'total': float(total),
                'count': item['count'],
                'average': float(item['avg_amount'] or 0),
            })

        # Calculate percentages
        for cat in categories:
            if total_spending > 0:
                cat['percentage'] = round((Decimal(str(cat['total'])) / total_spending) * 100, 1)
            else:
                cat['percentage'] = 0

        # Chart.js format
        chart_data = {
            'labels': [c['name'] for c in categories],
            'datasets': [{
                'data': [c['total'] for c in categories],
                'backgroundColor': [c['color'] for c in categories],
                'borderWidth': 0,
            }]
        }

        result = {
            'categories': categories,
            'total_spending': float(total_spending),
            'period': {
                'start': str(analytics_period.start_date) if analytics_period.start_date else None,
                'end': str(analytics_period.end_date),
                'type': period,
            },
            'chart_data': chart_data,
        }

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def get_income_vs_expense(
        self,
        period: str = 'month',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: str = 'month'
    ) -> Dict[str, Any]:
        """
        Compare income vs expenses over time.

        Args:
            period: Time period for analysis
            start_date: Start date for custom period
            end_date: End date for custom period
            group_by: Grouping interval ('day', 'week', 'month')

        Returns:
            Dict with comparison data and Chart.js format
        """
        analytics_period = AnalyticsPeriod(period, start_date, end_date)
        cache_key = self._get_cache_key(f'income_vs_expense_{group_by}', analytics_period)

        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        queryset = self._apply_period_filter(self._base_queryset, analytics_period)

        # Select truncation function
        trunc_func = {
            'day': TruncDay,
            'week': TruncWeek,
            'month': TruncMonth,
        }.get(group_by, TruncMonth)

        # Aggregate by period and type
        aggregated = queryset.annotate(
            period_date=trunc_func('transaction_date')
        ).values('period_date', 'type').annotate(
            total=Sum('amount')
        ).order_by('period_date', 'type')

        # Organize data by period
        periods_data = defaultdict(lambda: {'income': Decimal('0'), 'expense': Decimal('0')})

        for item in aggregated:
            period_key = item['period_date'].strftime('%Y-%m-%d')
            if item['type'] == 'income':
                periods_data[period_key]['income'] = item['total']
            elif item['type'] == 'expense':
                periods_data[period_key]['expense'] = item['total']

        # Sort and format
        sorted_periods = sorted(periods_data.keys())

        data_points = []
        labels = []
        income_data = []
        expense_data = []
        balance_data = []

        total_income = Decimal('0')
        total_expense = Decimal('0')

        for period_key in sorted_periods:
            values = periods_data[period_key]
            income = values['income']
            expense = values['expense']
            balance = income - expense

            total_income += income
            total_expense += expense

            labels.append(period_key)
            income_data.append(float(income))
            expense_data.append(float(expense))
            balance_data.append(float(balance))

            data_points.append({
                'date': period_key,
                'income': float(income),
                'expense': float(expense),
                'balance': float(balance),
            })

        # Previous period comparison
        previous_comparison = None
        if analytics_period.previous_start_date:
            prev_queryset = self._base_queryset.filter(
                transaction_date__gte=analytics_period.previous_start_date,
                transaction_date__lte=analytics_period.previous_end_date
            )
            prev_totals = prev_queryset.values('type').annotate(total=Sum('amount'))
            prev_income = Decimal('0')
            prev_expense = Decimal('0')

            for item in prev_totals:
                if item['type'] == 'income':
                    prev_income = item['total'] or Decimal('0')
                elif item['type'] == 'expense':
                    prev_expense = item['total'] or Decimal('0')

            if prev_income > 0:
                income_change = ((total_income - prev_income) / prev_income) * 100
            else:
                income_change = Decimal('100') if total_income > 0 else Decimal('0')

            if prev_expense > 0:
                expense_change = ((total_expense - prev_expense) / prev_expense) * 100
            else:
                expense_change = Decimal('100') if total_expense > 0 else Decimal('0')

            previous_comparison = {
                'previous_income': float(prev_income),
                'previous_expense': float(prev_expense),
                'income_change_percent': float(income_change),
                'expense_change_percent': float(expense_change),
            }

        # Chart.js format
        chart_data = {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Revenus',
                    'data': income_data,
                    'backgroundColor': 'rgba(34, 197, 94, 0.5)',
                    'borderColor': 'rgb(34, 197, 94)',
                    'borderWidth': 2,
                },
                {
                    'label': 'Dépenses',
                    'data': expense_data,
                    'backgroundColor': 'rgba(239, 68, 68, 0.5)',
                    'borderColor': 'rgb(239, 68, 68)',
                    'borderWidth': 2,
                },
            ]
        }

        result = {
            'data_points': data_points,
            'summary': {
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'net_balance': float(total_income - total_expense),
                'savings_rate': float(
                    ((total_income - total_expense) / total_income * 100)
                    if total_income > 0 else 0
                ),
            },
            'comparison': previous_comparison,
            'period': {
                'start': str(analytics_period.start_date) if analytics_period.start_date else None,
                'end': str(analytics_period.end_date),
                'type': period,
                'group_by': group_by,
            },
            'chart_data': chart_data,
        }

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def get_daily_balance(
        self,
        period: str = 'month',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        initial_balance: Decimal = Decimal('0')
    ) -> Dict[str, Any]:
        """
        Calculate running daily balance over time.

        Args:
            period: Time period for analysis
            start_date: Start date for custom period
            end_date: End date for custom period
            initial_balance: Starting balance for the period

        Returns:
            Dict with daily balances and Chart.js format
        """
        analytics_period = AnalyticsPeriod(period, start_date, end_date)
        cache_key = self._get_cache_key('daily_balance', analytics_period)

        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        queryset = self._apply_period_filter(self._base_queryset, analytics_period)

        # Amounts stored positive; Case/When signs them in DB (avoids Python loop).
        daily_totals = queryset.annotate(
            signed_amount_calc=Case(
                When(type='expense', then=-F('amount')),  # Expenses reduce balance
                default=F('amount'),  # Income increases balance
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )
        ).values(
            'transaction_date'
        ).annotate(
            daily_total=Sum('signed_amount_calc'),
            income=Sum(Case(
                When(type='income', then='amount'),
                default=Value(0),
                output_field=DecimalField()
            )),
            expense=Sum(Case(
                When(type='expense', then='amount'),
                default=Value(0),
                output_field=DecimalField()
            )),
            transaction_count=Count('id')
        ).order_by('transaction_date')

        # Build daily balance series
        labels = []
        balance_data = []
        daily_details = []

        running_balance = initial_balance
        min_balance = initial_balance
        max_balance = initial_balance

        for day in daily_totals:
            date_str = day['transaction_date'].strftime('%Y-%m-%d')
            daily_change = day['daily_total'] or Decimal('0')
            running_balance += daily_change

            min_balance = min(min_balance, running_balance)
            max_balance = max(max_balance, running_balance)

            labels.append(date_str)
            balance_data.append(float(running_balance))

            daily_details.append({
                'date': date_str,
                'balance': float(running_balance),
                'change': float(daily_change),
                'income': float(day['income'] or 0),
                'expense': float(day['expense'] or 0),
                'transaction_count': day['transaction_count'],
            })

        # Chart.js format
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': 'Solde',
                'data': balance_data,
                'fill': True,
                'backgroundColor': 'rgba(99, 102, 241, 0.1)',
                'borderColor': 'rgb(99, 102, 241)',
                'borderWidth': 2,
                'tension': 0.4,
                'pointRadius': 2,
            }]
        }

        result = {
            'daily_balances': daily_details,
            'summary': {
                'initial_balance': float(initial_balance),
                'final_balance': float(running_balance),
                'min_balance': float(min_balance),
                'max_balance': float(max_balance),
                'total_change': float(running_balance - initial_balance),
            },
            'period': {
                'start': str(analytics_period.start_date) if analytics_period.start_date else None,
                'end': str(analytics_period.end_date),
                'type': period,
            },
            'chart_data': chart_data,
        }

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def get_top_merchants(
        self,
        period: str = 'month',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
        transaction_type: str = 'expense'
    ) -> Dict[str, Any]:
        """
        Get top merchants by transaction volume.

        Args:
            period: Time period for analysis
            start_date: Start date for custom period
            end_date: End date for custom period
            limit: Maximum number of merchants to return
            transaction_type: Filter by transaction type ('expense', 'income', 'all')

        Returns:
            Dict with top merchants and spending details
        """
        analytics_period = AnalyticsPeriod(period, start_date, end_date)
        cache_key = self._get_cache_key(f'top_merchants_{transaction_type}', analytics_period)

        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        queryset = self._apply_period_filter(self._base_queryset, analytics_period)
        queryset = queryset.exclude(merchant='')

        if transaction_type != 'all':
            queryset = queryset.filter(type=transaction_type)

        # Aggregate by merchant
        merchant_stats = queryset.values('merchant').annotate(
            total=Sum('amount'),
            count=Count('id'),
            avg_amount=Avg('amount'),
            last_transaction=Max('transaction_date'),
        ).order_by('-total')[:limit]

        merchants = []
        total_amount = Decimal('0')

        for item in merchant_stats:
            total = item['total'] or Decimal('0')
            total_amount += total

            merchants.append({
                'name': item['merchant'],
                'total': float(total),
                'count': item['count'],
                'average': float(item['avg_amount'] or 0),
                'last_transaction': str(item['last_transaction']),
            })

        # Calculate percentages
        for merchant in merchants:
            if total_amount > 0:
                merchant['percentage'] = round(
                    (Decimal(str(merchant['total'])) / total_amount) * 100, 1
                )
            else:
                merchant['percentage'] = 0

        # Chart.js format
        chart_data = {
            'labels': [m['name'] for m in merchants],
            'datasets': [{
                'label': 'Montant total',
                'data': [m['total'] for m in merchants],
                'backgroundColor': 'rgba(99, 102, 241, 0.7)',
                'borderColor': 'rgb(99, 102, 241)',
                'borderWidth': 1,
            }]
        }

        result = {
            'merchants': merchants,
            'total_amount': float(total_amount),
            'merchant_count': len(merchants),
            'period': {
                'start': str(analytics_period.start_date) if analytics_period.start_date else None,
                'end': str(analytics_period.end_date),
                'type': period,
            },
            'chart_data': chart_data,
        }

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def get_recurring_analysis(self) -> Dict[str, Any]:
        """
        Analyze recurring transactions for insights.

        Returns:
            Dict with recurring transaction analysis and projections
        """
        cache_key = f"analytics:{self.user.id}:recurring_analysis"

        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        recurring = RecurringTransaction.objects.filter(
            user=self.user,
            is_active=True
        ).select_related('category')

        monthly_income = Decimal('0')
        monthly_expense = Decimal('0')

        income_items = []
        expense_items = []
        upcoming = []

        today = timezone.now().date()
        next_30_days = today + timedelta(days=30)

        for rec in recurring:
            # Calculate monthly equivalent
            monthly_amount = self._calculate_monthly_equivalent(
                rec.amount, rec.frequency
            )

            item_data = {
                'id': str(rec.id),
                'name': rec.name,
                'amount': float(rec.amount),
                'monthly_equivalent': float(monthly_amount),
                'frequency': rec.frequency,
                'next_occurrence': str(rec.next_occurrence),
                'category': rec.category.name if rec.category else None,
                'category_color': rec.category.color if rec.category else '#9CA3AF',
            }

            if rec.type == 'income':
                monthly_income += monthly_amount
                income_items.append(item_data)
            else:
                monthly_expense += monthly_amount
                expense_items.append(item_data)

            # Check if due in next 30 days
            if rec.next_occurrence <= next_30_days:
                upcoming.append({
                    **item_data,
                    'type': rec.type,
                    'days_until': (rec.next_occurrence - today).days,
                })

        # Sort upcoming by date
        upcoming.sort(key=lambda x: x['days_until'])

        # Calculate projections
        yearly_income = monthly_income * 12
        yearly_expense = monthly_expense * 12

        result = {
            'recurring_income': {
                'items': income_items,
                'monthly_total': float(monthly_income),
                'yearly_total': float(yearly_income),
                'count': len(income_items),
            },
            'recurring_expense': {
                'items': expense_items,
                'monthly_total': float(monthly_expense),
                'yearly_total': float(yearly_expense),
                'count': len(expense_items),
            },
            'summary': {
                'monthly_net': float(monthly_income - monthly_expense),
                'yearly_net': float(yearly_income - yearly_expense),
                'total_recurring': len(income_items) + len(expense_items),
            },
            'upcoming': upcoming[:10],  # Next 10 upcoming
            'projections': {
                'next_month': {
                    'expected_income': float(monthly_income),
                    'expected_expense': float(monthly_expense),
                    'expected_net': float(monthly_income - monthly_expense),
                },
                'next_quarter': {
                    'expected_income': float(monthly_income * 3),
                    'expected_expense': float(monthly_expense * 3),
                    'expected_net': float((monthly_income - monthly_expense) * 3),
                },
                'next_year': {
                    'expected_income': float(yearly_income),
                    'expected_expense': float(yearly_expense),
                    'expected_net': float(yearly_income - yearly_expense),
                },
            },
        }

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def _calculate_monthly_equivalent(
        self,
        amount: Decimal,
        frequency: str
    ) -> Decimal:
        """Convert any frequency to monthly equivalent."""
        multipliers = {
            'daily': Decimal('30'),
            'weekly': Decimal('4.33'),
            'biweekly': Decimal('2.17'),
            'monthly': Decimal('1'),
            'quarterly': Decimal('0.33'),
            'yearly': Decimal('0.083'),
        }
        return amount * multipliers.get(frequency, Decimal('1'))

    def get_trends(
        self,
        period: str = 'year',
        metric: str = 'expense'
    ) -> Dict[str, Any]:
        """
        Calculate spending/income trends over time.

        Args:
            period: Time period for trend analysis
            metric: Metric to analyze ('expense', 'income', 'balance')

        Returns:
            Dict with trend analysis and predictions
        """
        analytics_period = AnalyticsPeriod(period)
        cache_key = self._get_cache_key(f'trends_{metric}', analytics_period)

        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        queryset = self._apply_period_filter(self._base_queryset, analytics_period)

        if metric in ['expense', 'income']:
            queryset = queryset.filter(type=metric)

        # Monthly aggregation
        monthly_data = queryset.annotate(
            month=TruncMonth('transaction_date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id'),
            avg_transaction=Avg('amount')
        ).order_by('month')

        months = []
        totals = []

        for item in monthly_data:
            months.append(item['month'].strftime('%Y-%m'))
            totals.append(float(item['total'] or 0))

        # Simple trend calculation (linear regression approximation)
        if len(totals) >= 2:
            n = len(totals)
            avg_total = sum(totals) / n

            # Calculate trend direction
            first_half_avg = sum(totals[:n//2]) / max(1, n//2)
            second_half_avg = sum(totals[n//2:]) / max(1, n - n//2)

            if first_half_avg > 0:
                trend_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
            else:
                trend_percent = 0

            trend_direction = 'up' if trend_percent > 5 else ('down' if trend_percent < -5 else 'stable')

            # Simple prediction (average of last 3 months)
            prediction = sum(totals[-3:]) / min(3, len(totals))
        else:
            trend_percent = 0
            trend_direction = 'stable'
            prediction = totals[0] if totals else 0

        # Chart.js format
        chart_data = {
            'labels': months,
            'datasets': [{
                'label': 'Revenus' if metric == 'income' else 'Dépenses',
                'data': totals,
                'fill': False,
                'borderColor': 'rgb(34, 197, 94)' if metric == 'income' else 'rgb(239, 68, 68)',
                'tension': 0.4,
            }]
        }

        result = {
            'monthly_data': [
                {'month': m, 'total': t}
                for m, t in zip(months, totals)
            ],
            'trend': {
                'direction': trend_direction,
                'change_percent': round(trend_percent, 1),
                'average': round(sum(totals) / max(1, len(totals)), 2),
            },
            'prediction': {
                'next_month': round(prediction, 2),
                'confidence': 'medium' if len(totals) >= 6 else 'low',
            },
            'period': {
                'start': str(analytics_period.start_date) if analytics_period.start_date else None,
                'end': str(analytics_period.end_date),
                'type': period,
                'metric': metric,
            },
            'chart_data': chart_data,
        }

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard summary.

        Returns aggregated data for dashboard display.
        """
        cache_key = f"analytics:{self.user.id}:dashboard_summary"

        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Current month totals
        current_month = self._base_queryset.filter(
            transaction_date__gte=month_start
        )

        income = current_month.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        expense = current_month.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # Previous month for comparison
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_month_end = month_start - timedelta(days=1)

        prev_month = self._base_queryset.filter(
            transaction_date__gte=prev_month_start,
            transaction_date__lte=prev_month_end
        )

        prev_income = prev_month.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        prev_expense = prev_month.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # Top category this month
        top_category = current_month.filter(
            type='expense',
            category__isnull=False
        ).values(
            'category__name', 'category__color'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total').first()

        result = {
            'current_month': {
                'income': float(income),
                'expense': float(expense),
                'balance': float(income - expense),
                'transaction_count': current_month.count(),
            },
            'comparison': {
                'income_change': float(
                    ((income - prev_income) / prev_income * 100)
                    if prev_income > 0 else 0
                ),
                'expense_change': float(
                    ((expense - prev_expense) / prev_expense * 100)
                    if prev_expense > 0 else 0
                ),
                'prev_income': float(prev_income),
                'prev_expense': float(prev_expense),
            },
            'top_category': {
                'name': top_category['category__name'] if top_category else None,
                'color': top_category['category__color'] if top_category else None,
                'total': float(top_category['total']) if top_category else 0,
            } if top_category else None,
            'savings_rate': float(
                ((income - expense) / income * 100) if income > 0 else 0
            ),
        }

        cache.set(cache_key, result, self.CACHE_TIMEOUT)
        return result

    def invalidate_cache(self):
        """Invalidate all cached analytics for this user."""
        # In production, use pattern-based cache deletion
        # This is a simplified version
        cache_patterns = [
            'spending_by_category',
            'income_vs_expense',
            'daily_balance',
            'top_merchants',
            'recurring_analysis',
            'trends',
            'dashboard_summary',
        ]

        for pattern in cache_patterns:
            # Delete common period variations
            for period in ['week', 'month', 'quarter', 'year']:
                cache_key = f"analytics:{self.user.id}:{pattern}:{period}"
                cache.delete(cache_key)


# Import Max for top_merchants
from django.db.models import Max


def get_spending_by_category(user, period: str = 'month') -> Dict[str, Any]:
    """
    Convenience function for spending by category analysis.

    Args:
        user: User instance
        period: Time period string

    Returns:
        Spending by category data
    """
    analytics = TransactionAnalytics(user)
    return analytics.get_spending_by_category(period=period)


def get_income_vs_expense(user, period: str = 'month') -> Dict[str, Any]:
    """
    Convenience function for income vs expense comparison.

    Args:
        user: User instance
        period: Time period string

    Returns:
        Income vs expense comparison data
    """
    analytics = TransactionAnalytics(user)
    return analytics.get_income_vs_expense(period=period)


def get_daily_balance(user, period: str = 'month') -> Dict[str, Any]:
    """
    Convenience function for daily balance analysis.

    Args:
        user: User instance
        period: Time period string

    Returns:
        Daily balance data
    """
    analytics = TransactionAnalytics(user)
    return analytics.get_daily_balance(period=period)


def get_top_merchants(user, period: str = 'month') -> Dict[str, Any]:
    """
    Convenience function for top merchants analysis.

    Args:
        user: User instance
        period: Time period string

    Returns:
        Top merchants data
    """
    analytics = TransactionAnalytics(user)
    return analytics.get_top_merchants(period=period)


def get_recurring_analysis(user) -> Dict[str, Any]:
    """
    Convenience function for recurring transactions analysis.

    Args:
        user: User instance

    Returns:
        Recurring transactions analysis data
    """
    analytics = TransactionAnalytics(user)
    return analytics.get_recurring_analysis()
