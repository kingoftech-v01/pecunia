"""
Dashboard Template Views.

Django views that render HTML templates for the dashboard.
Supports HTMX for dynamic partial updates and lazy loading.

Views:
------
- dashboard_home: Main dashboard page
- get_balance_data: HTMX widget for balance card
- get_recent_transactions: HTMX widget for recent transactions
- get_budget_overview: HTMX widget for budget overview
- get_ai_insights: HTMX widget for AI insights
- get_quick_actions: HTMX widget for quick actions
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


@login_required
def dashboard_home(request):
    """
    Main dashboard view.

    Renders the dashboard skeleton with HTMX placeholders
    that load widgets asynchronously for better perceived performance.
    """
    context = {
        'page_title': 'Dashboard',
        'user': request.user,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def get_balance_data(request):
    """
    HTMX endpoint for balance card widget.

    Returns partial HTML with:
    - Total balance across all accounts
    - Monthly income and expenses
    - Trend indicators
    """
    from apps.banking.models import BankAccount
    from apps.transactions.models import Transaction

    user = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)

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

    # Previous month for comparison
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
    prev_month_end = month_start - timedelta(days=1)

    prev_month_expenses = Transaction.objects.filter(
        user=user,
        transaction_date__gte=prev_month_start,
        transaction_date__lte=prev_month_end,
        type='expense'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    prev_month_income = Transaction.objects.filter(
        user=user,
        transaction_date__gte=prev_month_start,
        transaction_date__lte=prev_month_end,
        type='income'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Calculate trends
    expense_change = Decimal('0.00')
    if prev_month_expenses > 0:
        expense_change = ((monthly_expenses - prev_month_expenses) / prev_month_expenses) * 100

    income_change = Decimal('0.00')
    if prev_month_income > 0:
        income_change = ((monthly_income - prev_month_income) / prev_month_income) * 100

    context = {
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'net_monthly': monthly_income - monthly_expenses,
        'expense_change': expense_change,
        'expense_trend': 'up' if expense_change > 0 else 'down' if expense_change < 0 else 'neutral',
        'income_change': income_change,
        'income_trend': 'up' if income_change > 0 else 'down' if income_change < 0 else 'neutral',
    }

    return render(request, 'dashboard/widgets/balance_card.html', context)


@login_required
def get_recent_transactions(request):
    """
    HTMX endpoint for recent transactions widget.

    Returns partial HTML with:
    - 5 most recent transactions
    - Quick view of amount, category, date
    - Link to view all transactions
    """
    from apps.transactions.models import Transaction

    user = request.user

    recent_transactions = Transaction.objects.filter(
        user=user
    ).select_related('category').order_by('-transaction_date', '-created_at')[:5]

    context = {
        'transactions': recent_transactions,
        'has_transactions': recent_transactions.exists(),
    }

    return render(request, 'dashboard/widgets/recent_transactions.html', context)


@login_required
def get_budget_overview(request):
    """
    HTMX endpoint for budget overview widget.

    Returns partial HTML with:
    - Active budget summary
    - Overall progress percentage
    - Top spending categories
    """
    from apps.budgets.models import Budget, BudgetItem

    user = request.user
    today = timezone.now().date()

    # Get active budgets
    active_budgets = Budget.objects.filter(
        user=user,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).prefetch_related('items', 'items__category')

    # Calculate totals
    total_planned = active_budgets.aggregate(
        total=Sum('total_planned_amount')
    )['total'] or Decimal('0.00')

    total_spent = active_budgets.aggregate(
        total=Sum('total_spent_amount')
    )['total'] or Decimal('0.00')

    total_remaining = total_planned - total_spent

    overall_progress = Decimal('0.00')
    if total_planned > 0:
        overall_progress = (total_spent / total_planned) * 100

    # Top spending categories from budget items
    top_categories = BudgetItem.objects.filter(
        budget__in=active_budgets
    ).values(
        'category__id',
        'category__name',
        'category__color'
    ).annotate(
        planned=Sum('planned_amount'),
        spent=Sum('spent_amount')
    ).order_by('-spent')[:5]

    categories = []
    for cat in top_categories:
        planned = cat['planned'] or Decimal('0.00')
        spent = cat['spent'] or Decimal('0.00')
        progress = (spent / planned * 100) if planned > 0 else Decimal('0.00')
        categories.append({
            'name': cat['category__name'] or 'Uncategorized',
            'color': cat['category__color'] or '#6366f1',
            'planned': planned,
            'spent': spent,
            'remaining': planned - spent,
            'progress': progress,
            'is_over': spent > planned
        })

    # Budget health status
    budgets_over = active_budgets.filter(
        total_spent_amount__gt=F('total_planned_amount')
    ).count()

    budgets_near = active_budgets.filter(
        total_spent_amount__gte=F('total_planned_amount') * Decimal('0.8'),
        total_spent_amount__lt=F('total_planned_amount')
    ).count()

    context = {
        'has_budgets': active_budgets.exists(),
        'budget_count': active_budgets.count(),
        'total_planned': total_planned,
        'total_spent': total_spent,
        'total_remaining': total_remaining,
        'overall_progress': overall_progress,
        'top_categories': categories,
        'budgets_over': budgets_over,
        'budgets_near': budgets_near,
        'health_status': 'danger' if budgets_over > 0 else 'warning' if budgets_near > 0 else 'good',
    }

    return render(request, 'dashboard/widgets/budget_overview.html', context)


@login_required
def get_ai_insights(request):
    """
    HTMX endpoint for AI insights widget.

    Returns partial HTML with:
    - Latest AI recommendations
    - Quick action buttons
    - Dismiss functionality
    """
    from apps.budgets.models import Budget
    from apps.transactions.models import Transaction

    user = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)

    insights = []

    # Budget warnings
    over_budget = Budget.objects.filter(
        user=user,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
        total_spent_amount__gt=F('total_planned_amount')
    ).first()

    if over_budget:
        overspent = over_budget.total_spent_amount - over_budget.total_planned_amount
        insights.append({
            'type': 'warning',
            'icon': 'exclamation-triangle',
            'title': f'Budget "{over_budget.name}" exceeded',
            'message': f'Over by ${overspent:.2f}',
            'action_url': f'/budgets/{over_budget.id}/',
            'action_label': 'Review'
        })

    # Near budget limit
    near_limit = Budget.objects.filter(
        user=user,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
        total_spent_amount__gte=F('total_planned_amount') * Decimal('0.8'),
        total_spent_amount__lt=F('total_planned_amount')
    ).first()

    if near_limit:
        remaining = near_limit.total_planned_amount - near_limit.total_spent_amount
        insights.append({
            'type': 'alert',
            'icon': 'bell',
            'title': f'Budget "{near_limit.name}" nearly exhausted',
            'message': f'${remaining:.2f} remaining',
            'action_url': f'/budgets/{near_limit.id}/',
            'action_label': 'View'
        })

    # Spending pattern insight
    avg_daily = Transaction.objects.filter(
        user=user,
        type='expense',
        transaction_date__gte=month_start - timedelta(days=30),
        transaction_date__lt=month_start
    ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')

    this_month_avg = Transaction.objects.filter(
        user=user,
        type='expense',
        transaction_date__gte=month_start
    ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')

    if avg_daily > 0 and this_month_avg > avg_daily * Decimal('1.2'):
        insights.append({
            'type': 'info',
            'icon': 'trending-up',
            'title': 'Spending trend detected',
            'message': 'Your average transaction is higher this month',
            'action_url': '/transactions/',
            'action_label': 'Analyze'
        })

    # Positive savings insight
    monthly_income = Transaction.objects.filter(
        user=user,
        type='income',
        transaction_date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    monthly_expenses = Transaction.objects.filter(
        user=user,
        type='expense',
        transaction_date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    if monthly_income > monthly_expenses:
        savings = monthly_income - monthly_expenses
        if savings >= Decimal('100.00'):
            insights.append({
                'type': 'success',
                'icon': 'check-circle',
                'title': 'Great savings!',
                'message': f'You\'ve saved ${savings:.2f} this month',
                'action_url': None,
                'action_label': None
            })

    # Try to get AI recommendations if available
    try:
        from apps.ai.models import AIRecommendation
        ai_recs = AIRecommendation.objects.filter(
            user=user,
            is_active=True,
            is_dismissed=False
        ).order_by('-created_at')[:2]

        for rec in ai_recs:
            insights.append({
                'type': 'suggestion',
                'icon': 'lightbulb',
                'title': rec.title,
                'message': rec.description[:100] + '...' if len(rec.description) > 100 else rec.description,
                'action_url': rec.action_url or '/ai/',
                'action_label': rec.action_label or 'Learn More',
                'rec_id': str(rec.id)
            })
    except Exception:
        pass

    context = {
        'insights': insights[:5],  # Limit to 5 insights
        'has_insights': len(insights) > 0,
    }

    return render(request, 'dashboard/widgets/ai_insights.html', context)


@login_required
def get_spending_chart_data(request):
    """
    HTMX endpoint for spending chart data.

    Returns JSON data for Chart.js visualization.
    """
    from django.http import JsonResponse
    from apps.transactions.models import Transaction

    user = request.user
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Spending by category
    spending = Transaction.objects.filter(
        user=user,
        transaction_date__gte=month_start,
        type='expense'
    ).values(
        'category__name',
        'category__color'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total')[:8]

    labels = []
    data = []
    colors = []

    for item in spending:
        labels.append(item['category__name'] or 'Uncategorized')
        data.append(float(item['total']))
        colors.append(item['category__color'] or '#6366f1')

    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': colors,
            'borderWidth': 0
        }]
    })


@login_required
def get_balance_chart_data(request):
    """
    HTMX endpoint for balance trend chart data.

    Returns JSON data for Chart.js line chart.
    """
    from django.http import JsonResponse
    from apps.transactions.models import Transaction

    user = request.user
    today = timezone.now().date()
    start_date = today - timedelta(days=30)

    # Daily income and expenses
    daily_data = Transaction.objects.filter(
        user=user,
        transaction_date__gte=start_date
    ).values('transaction_date').annotate(
        income=Sum('amount', filter=Q(type='income')),
        expenses=Sum('amount', filter=Q(type='expense'))
    ).order_by('transaction_date')

    labels = []
    income_data = []
    expense_data = []

    for day in daily_data:
        labels.append(day['transaction_date'].strftime('%b %d'))
        income_data.append(float(day['income'] or 0))
        expense_data.append(float(day['expenses'] or 0))

    return JsonResponse({
        'labels': labels,
        'datasets': [
            {
                'label': 'Income',
                'data': income_data,
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'fill': True,
                'tension': 0.4
            },
            {
                'label': 'Expenses',
                'data': expense_data,
                'borderColor': '#ef4444',
                'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                'fill': True,
                'tension': 0.4
            }
        ]
    })
