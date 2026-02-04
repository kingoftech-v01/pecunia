"""
Dashboard API Views.

DRF ViewSets for dashboard data aggregation and insights.

This module provides API endpoints for dashboard widgets:

API Endpoints:
--------------
- GET /api/v1/dashboard/summary/     - Financial summary data
- GET /api/v1/dashboard/balance/     - Balance and trends
- GET /api/v1/dashboard/spending/    - Spending analytics
- GET /api/v1/dashboard/insights/    - AI-powered insights

Performance Notes:
------------------
- Uses database aggregation for efficient queries
- Implements caching for frequently accessed data
- Single queries with filters, no N+1 issues
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.cache import cache


class DashboardSummaryView(APIView):
    """
    API view for dashboard summary data.

    Provides aggregated financial data for the dashboard overview.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get comprehensive dashboard summary.

        Returns aggregated data including:
        - Total balance across all accounts
        - Monthly income and expenses
        - Budget utilization
        - Recent activity count
        """
        from apps.banking.models import BankAccount
        from apps.transactions.models import Transaction
        from apps.budgets.models import Budget

        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Cache key for user dashboard
        cache_key = f'dashboard_summary_{user.id}_{today}'
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        # Total balance from all bank accounts
        total_balance = BankAccount.objects.filter(
            user=user,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')

        # Monthly transactions
        monthly_transactions = Transaction.objects.filter(
            user=user,
            transaction_date__gte=month_start,
            transaction_date__lte=today
        )

        monthly_income = monthly_transactions.filter(
            type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        monthly_expenses = monthly_transactions.filter(
            type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Previous month comparison
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        prev_month_end = month_start - timedelta(days=1)

        prev_month_expenses = Transaction.objects.filter(
            user=user,
            transaction_date__gte=prev_month_start,
            transaction_date__lte=prev_month_end,
            type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Calculate expense trend
        expense_change = Decimal('0.00')
        if prev_month_expenses > 0:
            expense_change = ((monthly_expenses - prev_month_expenses) / prev_month_expenses) * 100

        # Active budgets
        active_budgets = Budget.objects.filter(
            user=user,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        )

        total_budget_planned = active_budgets.aggregate(
            total=Sum('total_planned_amount')
        )['total'] or Decimal('0.00')

        total_budget_spent = active_budgets.aggregate(
            total=Sum('total_spent_amount')
        )['total'] or Decimal('0.00')

        budget_utilization = Decimal('0.00')
        if total_budget_planned > 0:
            budget_utilization = (total_budget_spent / total_budget_planned) * 100

        # Transaction count this month
        transaction_count = monthly_transactions.count()

        data = {
            'total_balance': str(total_balance),
            'monthly_income': str(monthly_income),
            'monthly_expenses': str(monthly_expenses),
            'net_monthly': str(monthly_income - monthly_expenses),
            'expense_trend': str(expense_change.quantize(Decimal('0.01'))),
            'expense_trend_direction': 'up' if expense_change > 0 else 'down' if expense_change < 0 else 'neutral',
            'budget_planned': str(total_budget_planned),
            'budget_spent': str(total_budget_spent),
            'budget_utilization': str(budget_utilization.quantize(Decimal('0.01'))),
            'transaction_count': transaction_count,
            'active_budgets_count': active_budgets.count(),
            'period': {
                'start': str(month_start),
                'end': str(today),
            }
        }

        # Cache for 5 minutes
        cache.set(cache_key, data, 300)

        return Response(data)


class DashboardBalanceView(APIView):
    """
    API view for balance data and trends.

    Provides balance history and trend analysis.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get balance data with historical trends.

        Query Parameters:
        - period: 'week', 'month', 'quarter', 'year' (default: month)
        """
        from apps.banking.models import BankAccount
        from apps.transactions.models import Transaction

        user = request.user
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()

        # Determine date range
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:  # month
            start_date = today - timedelta(days=30)

        # Current balance by account type
        accounts = BankAccount.objects.filter(
            user=user,
            is_active=True
        ).values('account_type').annotate(
            total=Sum('current_balance'),
            count=Count('id')
        )

        account_balances = {
            acc['account_type']: {
                'balance': str(acc['total'] or Decimal('0.00')),
                'count': acc['count']
            }
            for acc in accounts
        }

        # Daily balance trend (simplified - shows net change per day)
        daily_transactions = Transaction.objects.filter(
            user=user,
            transaction_date__gte=start_date,
            transaction_date__lte=today
        ).values('transaction_date').annotate(
            income=Sum('amount', filter=Q(type='income')),
            expenses=Sum('amount', filter=Q(type='expense'))
        ).order_by('transaction_date')

        balance_trend = []
        for day in daily_transactions:
            income = day['income'] or Decimal('0.00')
            expenses = day['expenses'] or Decimal('0.00')
            balance_trend.append({
                'date': str(day['transaction_date']),
                'income': str(income),
                'expenses': str(expenses),
                'net': str(income - expenses)
            })

        # Total balance
        total_balance = BankAccount.objects.filter(
            user=user,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')

        data = {
            'total_balance': str(total_balance),
            'account_balances': account_balances,
            'balance_trend': balance_trend,
            'period': {
                'type': period,
                'start': str(start_date),
                'end': str(today)
            }
        }

        return Response(data)


class DashboardSpendingView(APIView):
    """
    API view for spending analytics.

    Provides detailed spending breakdown and patterns.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get spending analytics data.

        Query Parameters:
        - period: 'week', 'month', 'quarter', 'year' (default: month)
        """
        from apps.transactions.models import Transaction

        user = request.user
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()

        # Determine date range
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:  # month
            start_date = today.replace(day=1)

        # Spending by category
        spending_by_category = Transaction.objects.filter(
            user=user,
            transaction_date__gte=start_date,
            transaction_date__lte=today,
            type='expense'
        ).values(
            'category__id',
            'category__name',
            'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id'),
            avg=Avg('amount')
        ).order_by('-total')

        categories = []
        total_spending = Decimal('0.00')

        for cat in spending_by_category:
            amount = cat['total'] or Decimal('0.00')
            total_spending += amount
            categories.append({
                'id': str(cat['category__id']) if cat['category__id'] else None,
                'name': cat['category__name'] or 'Uncategorized',
                'color': cat['category__color'] or '#6366f1',
                'amount': str(amount),
                'count': cat['count'],
                'average': str((cat['avg'] or Decimal('0.00')).quantize(Decimal('0.01')))
            })

        # Add percentage to each category
        for cat in categories:
            if total_spending > 0:
                percentage = (Decimal(cat['amount']) / total_spending) * 100
                cat['percentage'] = str(percentage.quantize(Decimal('0.01')))
            else:
                cat['percentage'] = '0.00'

        # Top merchants
        top_merchants = Transaction.objects.filter(
            user=user,
            transaction_date__gte=start_date,
            transaction_date__lte=today,
            type='expense',
            merchant__isnull=False
        ).exclude(
            merchant=''
        ).values('merchant').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]

        merchants = [
            {
                'name': m['merchant'],
                'amount': str(m['total']),
                'count': m['count']
            }
            for m in top_merchants
        ]

        data = {
            'total_spending': str(total_spending),
            'categories': categories,
            'top_merchants': merchants,
            'period': {
                'type': period,
                'start': str(start_date),
                'end': str(today)
            }
        }

        return Response(data)


class DashboardInsightsView(APIView):
    """
    API view for AI-powered insights.

    Provides intelligent recommendations and alerts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get AI-generated insights for the user.

        Returns various types of insights:
        - Spending alerts
        - Budget warnings
        - Savings opportunities
        - Trend analysis
        """
        from apps.transactions.models import Transaction
        from apps.budgets.models import Budget
        from apps.ai.models import AIRecommendation

        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)

        insights = []

        # Check budget status
        over_budget_items = Budget.objects.filter(
            user=user,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today,
            total_spent_amount__gt=F('total_planned_amount')
        )

        for budget in over_budget_items[:3]:
            overspent = budget.total_spent_amount - budget.total_planned_amount
            insights.append({
                'type': 'warning',
                'category': 'budget',
                'title': f'Budget "{budget.name}" exceeded',
                'message': f'You have overspent by ${overspent:.2f}. Consider adjusting your spending.',
                'action': {
                    'label': 'View Budget',
                    'url': f'/budgets/{budget.id}/'
                },
                'priority': 'high'
            })

        # Near budget limit (80%+)
        near_limit_budgets = Budget.objects.filter(
            user=user,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today,
            total_spent_amount__gte=F('total_planned_amount') * Decimal('0.8'),
            total_spent_amount__lt=F('total_planned_amount')
        )

        for budget in near_limit_budgets[:2]:
            percentage = (budget.total_spent_amount / budget.total_planned_amount * 100)
            insights.append({
                'type': 'alert',
                'category': 'budget',
                'title': f'Budget "{budget.name}" at {percentage:.0f}%',
                'message': f'You are close to your budget limit. ${budget.remaining_amount:.2f} remaining.',
                'action': {
                    'label': 'Review Budget',
                    'url': f'/budgets/{budget.id}/'
                },
                'priority': 'medium'
            })

        # Unusual spending detection
        avg_daily_expense = Transaction.objects.filter(
            user=user,
            type='expense',
            transaction_date__gte=month_start - timedelta(days=30),
            transaction_date__lt=month_start
        ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')

        today_expenses = Transaction.objects.filter(
            user=user,
            type='expense',
            transaction_date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        if avg_daily_expense > 0 and today_expenses > (avg_daily_expense * 2):
            insights.append({
                'type': 'info',
                'category': 'spending',
                'title': 'Higher than usual spending today',
                'message': f'You spent ${today_expenses:.2f} today, which is higher than your daily average of ${avg_daily_expense:.2f}.',
                'action': {
                    'label': 'View Transactions',
                    'url': '/transactions/'
                },
                'priority': 'low'
            })

        # Get AI recommendations
        ai_recommendations = AIRecommendation.objects.filter(
            user=user,
            is_active=True,
            is_dismissed=False
        ).order_by('-created_at')[:3]

        for rec in ai_recommendations:
            insights.append({
                'type': 'suggestion',
                'category': 'ai',
                'title': rec.title,
                'message': rec.description,
                'action': {
                    'label': rec.action_label or 'Learn More',
                    'url': rec.action_url or '#'
                },
                'priority': rec.priority or 'medium',
                'id': str(rec.id)
            })

        # Positive insight - savings
        total_income = Transaction.objects.filter(
            user=user,
            type='income',
            transaction_date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        total_expenses = Transaction.objects.filter(
            user=user,
            type='expense',
            transaction_date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        if total_income > total_expenses and (total_income - total_expenses) > Decimal('100.00'):
            savings = total_income - total_expenses
            savings_rate = (savings / total_income * 100) if total_income > 0 else Decimal('0.00')
            insights.append({
                'type': 'success',
                'category': 'savings',
                'title': 'Great savings this month!',
                'message': f'You have saved ${savings:.2f} ({savings_rate:.0f}% of income) this month. Keep it up!',
                'action': None,
                'priority': 'low'
            })

        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        insights.sort(key=lambda x: priority_order.get(x['priority'], 1))

        data = {
            'insights': insights[:8],  # Limit to 8 insights
            'total_count': len(insights),
            'generated_at': str(timezone.now())
        }

        return Response(data)


class QuickActionsView(APIView):
    """
    API view for quick action shortcuts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get available quick actions for the user."""
        from apps.banking.models import BankAccount

        user = request.user

        # Check if user has connected bank accounts
        has_bank_accounts = BankAccount.objects.filter(
            user=user,
            is_active=True
        ).exists()

        actions = [
            {
                'id': 'add_transaction',
                'label': 'Add Transaction',
                'icon': 'plus-circle',
                'url': '/transactions/add/',
                'color': 'primary'
            },
            {
                'id': 'create_budget',
                'label': 'Create Budget',
                'icon': 'calculator',
                'url': '/budgets/create/',
                'color': 'accent'
            },
        ]

        if not has_bank_accounts:
            actions.insert(0, {
                'id': 'connect_bank',
                'label': 'Connect Bank',
                'icon': 'link',
                'url': '/banking/connect/',
                'color': 'success',
                'highlight': True
            })

        actions.extend([
            {
                'id': 'sync_accounts',
                'label': 'Sync Accounts',
                'icon': 'refresh',
                'url': '/banking/sync/',
                'color': 'secondary',
                'disabled': not has_bank_accounts
            },
            {
                'id': 'view_reports',
                'label': 'View Reports',
                'icon': 'chart-bar',
                'url': '/reports/',
                'color': 'secondary'
            },
            {
                'id': 'ai_analysis',
                'label': 'AI Analysis',
                'icon': 'sparkles',
                'url': '/ai/analysis/',
                'color': 'accent'
            }
        ])

        return Response({'actions': actions})
