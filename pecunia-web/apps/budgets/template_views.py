"""
Budgets Template Views (Frontend).

Django views for HTML pages with HTMX/Alpine.js support.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Budget, BudgetItem
from .forms import (
    BudgetForm,
    BudgetItemForm,
    BudgetFilterForm,
    QuickBudgetForm,
)


@login_required
def budget_list(request):
    """
    List all budgets with filtering and pagination.

    Template: budgets/budget_list.html
    URL: /budgets/
    """
    filter_form = BudgetFilterForm(request.GET)
    budgets = Budget.objects.filter(
        user=request.user
    ).prefetch_related('items')

    # Apply filters
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        period_type = filter_form.cleaned_data.get('period_type')
        status_filter = filter_form.cleaned_data.get('status')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')

        if search:
            budgets = budgets.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        if period_type:
            budgets = budgets.filter(period_type=period_type)
        if status_filter:
            if status_filter == 'active':
                budgets = budgets.filter(is_active=True)
            elif status_filter == 'inactive':
                budgets = budgets.filter(is_active=False)
            elif status_filter == 'over_budget':
                budgets = budgets.filter(
                    total_spent_amount__gt=F('total_planned_amount')
                )
            elif status_filter == 'on_track':
                budgets = budgets.filter(
                    total_spent_amount__lte=F('total_planned_amount')
                )
        if date_from:
            budgets = budgets.filter(start_date__gte=date_from)
        if date_to:
            budgets = budgets.filter(end_date__lte=date_to)

    # Calculate totals
    totals = budgets.aggregate(
        planned=Sum('total_planned_amount'),
        spent=Sum('total_spent_amount')
    )
    totals['planned'] = totals['planned'] or Decimal('0.00')
    totals['spent'] = totals['spent'] or Decimal('0.00')
    totals['remaining'] = totals['planned'] - totals['spent']

    # Pagination
    paginator = Paginator(budgets, 10)
    page = request.GET.get('page', 1)
    budgets_page = paginator.get_page(page)

    context = {
        'budgets': budgets_page,
        'filter_form': filter_form,
        'totals': totals,
    }

    # HTMX support - return partial if HX request
    if request.headers.get('HX-Request'):
        return render(request, 'budgets/partials/budget_table.html', context)

    return render(request, 'budgets/budget_list.html', context)


@login_required
def budget_detail(request, pk):
    """
    Budget detail view with items.

    Template: budgets/budget_detail.html
    URL: /budgets/<uuid>/
    """
    budget = get_object_or_404(
        Budget.objects.prefetch_related('items', 'items__category'),
        pk=pk,
        user=request.user
    )

    # Calculate progress metrics
    today = timezone.now().date()
    total_days = (budget.end_date - budget.start_date).days + 1
    days_elapsed = min(
        max((today - budget.start_date).days + 1, 0),
        total_days
    )
    days_remaining = max(total_days - days_elapsed, 0)

    daily_budget = budget.total_planned_amount / total_days if total_days > 0 else Decimal('0.00')
    daily_spending = budget.total_spent_amount / days_elapsed if days_elapsed > 0 else Decimal('0.00')
    projected_spending = budget.total_spent_amount + (daily_spending * days_remaining)

    context = {
        'budget': budget,
        'items': budget.items.select_related('category').all(),
        'days_remaining': days_remaining,
        'daily_budget': daily_budget,
        'daily_spending': daily_spending,
        'projected_spending': projected_spending,
        'is_on_track': budget.total_spent_amount <= (daily_budget * days_elapsed),
    }

    # HTMX support
    if request.headers.get('HX-Request'):
        return render(request, 'budgets/partials/budget_detail_content.html', context)

    return render(request, 'budgets/budget_detail.html', context)


@login_required
def budget_create(request):
    """
    Create a new budget.

    Template: budgets/budget_form.html
    URL: /budgets/create/
    """
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(request, 'Budget created successfully!')

            if request.headers.get('HX-Request'):
                return render(request, 'budgets/partials/budget_created.html', {
                    'budget': budget
                })
            return redirect('frontend:budgets:budget_detail', pk=budget.pk)
    else:
        # Set default dates
        today = timezone.now().date()
        initial = {
            'start_date': today.replace(day=1),
            'end_date': (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
        }
        form = BudgetForm(initial=initial)

    return render(request, 'budgets/budget_form.html', {
        'form': form,
        'action': 'Create'
    })


@login_required
def budget_update(request, pk):
    """
    Update an existing budget.

    Template: budgets/budget_form.html
    URL: /budgets/<uuid>/edit/
    """
    budget = get_object_or_404(Budget, pk=pk, user=request.user)

    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated successfully!')

            if request.headers.get('HX-Request'):
                return render(request, 'budgets/partials/budget_updated.html', {
                    'budget': budget
                })
            return redirect('frontend:budgets:budget_detail', pk=pk)
    else:
        form = BudgetForm(instance=budget)

    return render(request, 'budgets/budget_form.html', {
        'form': form,
        'budget': budget,
        'action': 'Update'
    })


@login_required
def budget_delete(request, pk):
    """
    Delete a budget.

    Template: budgets/budget_confirm_delete.html
    URL: /budgets/<uuid>/delete/
    """
    budget = get_object_or_404(Budget, pk=pk, user=request.user)

    if request.method == 'POST':
        budget_name = budget.name
        budget.delete()
        messages.success(request, f'Budget "{budget_name}" deleted successfully!')

        if request.headers.get('HX-Request'):
            return render(request, 'budgets/partials/budget_deleted.html')
        return redirect('frontend:budgets:budget_list')

    return render(request, 'budgets/budget_confirm_delete.html', {
        'budget': budget
    })


@login_required
def budget_item_create(request, budget_pk):
    """
    Add an item to a budget.

    Template: budgets/budget_item_form.html
    URL: /budgets/<uuid>/items/create/
    """
    budget = get_object_or_404(Budget, pk=budget_pk, user=request.user)

    if request.method == 'POST':
        form = BudgetItemForm(request.user, request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.budget = budget
            item.save()
            messages.success(request, 'Budget item added successfully!')

            if request.headers.get('HX-Request'):
                return render(request, 'budgets/partials/budget_item_row.html', {
                    'item': item,
                    'budget': budget
                })
            return redirect('frontend:budgets:budget_detail', pk=budget_pk)
    else:
        form = BudgetItemForm(request.user)

    return render(request, 'budgets/budget_item_form.html', {
        'form': form,
        'budget': budget,
        'action': 'Add'
    })


@login_required
def budget_item_update(request, budget_pk, pk):
    """
    Update a budget item.

    Template: budgets/budget_item_form.html
    URL: /budgets/<uuid>/items/<uuid>/edit/
    """
    budget = get_object_or_404(Budget, pk=budget_pk, user=request.user)
    item = get_object_or_404(BudgetItem, pk=pk, budget=budget)

    if request.method == 'POST':
        form = BudgetItemForm(request.user, request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget item updated successfully!')

            if request.headers.get('HX-Request'):
                return render(request, 'budgets/partials/budget_item_row.html', {
                    'item': item,
                    'budget': budget
                })
            return redirect('frontend:budgets:budget_detail', pk=budget_pk)
    else:
        form = BudgetItemForm(request.user, instance=item)

    return render(request, 'budgets/budget_item_form.html', {
        'form': form,
        'budget': budget,
        'item': item,
        'action': 'Update'
    })


@login_required
def budget_item_delete(request, budget_pk, pk):
    """
    Delete a budget item.

    Template: budgets/budget_item_confirm_delete.html
    URL: /budgets/<uuid>/items/<uuid>/delete/
    """
    budget = get_object_or_404(Budget, pk=budget_pk, user=request.user)
    item = get_object_or_404(BudgetItem, pk=pk, budget=budget)

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Budget item deleted successfully!')

        if request.headers.get('HX-Request'):
            return render(request, 'budgets/partials/budget_item_deleted.html', {
                'budget': budget
            })
        return redirect('frontend:budgets:budget_detail', pk=budget_pk)

    return render(request, 'budgets/budget_item_confirm_delete.html', {
        'item': item,
        'budget': budget
    })


@login_required
def budget_dashboard(request):
    """
    Budget overview dashboard.

    Template: budgets/budget_dashboard.html
    URL: /budgets/dashboard/
    """
    today = timezone.now().date()

    # Get current active budgets
    current_budgets = Budget.objects.filter(
        user=request.user,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).prefetch_related('items', 'items__category')

    # Calculate overall stats
    stats = current_budgets.aggregate(
        total_planned=Sum('total_planned_amount'),
        total_spent=Sum('total_spent_amount')
    )
    stats['total_planned'] = stats['total_planned'] or Decimal('0.00')
    stats['total_spent'] = stats['total_spent'] or Decimal('0.00')
    stats['total_remaining'] = stats['total_planned'] - stats['total_spent']

    if stats['total_planned'] > 0:
        stats['overall_progress'] = (stats['total_spent'] / stats['total_planned']) * 100
    else:
        stats['overall_progress'] = Decimal('0.00')

    # Budget status counts
    stats['over_budget'] = current_budgets.filter(
        total_spent_amount__gt=F('total_planned_amount')
    ).count()
    stats['on_track'] = current_budgets.filter(
        total_spent_amount__lte=F('total_planned_amount')
    ).count()

    # Top spending categories (from budget items)
    top_categories = BudgetItem.objects.filter(
        budget__user=request.user,
        budget__is_active=True,
        budget__start_date__lte=today,
        budget__end_date__gte=today
    ).values(
        'category__name', 'category__color'
    ).annotate(
        total_spent=Sum('spent_amount'),
        total_planned=Sum('planned_amount')
    ).order_by('-total_spent')[:5]

    context = {
        'current_budgets': current_budgets,
        'stats': stats,
        'top_categories': top_categories,
    }

    return render(request, 'budgets/budget_dashboard.html', context)


@login_required
def quick_budget_create(request):
    """
    Quick budget creation with presets.

    Template: budgets/quick_budget_form.html
    URL: /budgets/quick-create/
    """
    if request.method == 'POST':
        form = QuickBudgetForm(request.POST)
        if form.is_valid():
            budget = Budget.objects.create(
                user=request.user,
                name=form.cleaned_data['name'],
                period_type=form.cleaned_data['period_type'],
                start_date=form.cleaned_data['start_date'],
                end_date=form.cleaned_data['end_date'],
                total_planned_amount=form.cleaned_data['total_amount'],
            )
            messages.success(request, 'Budget created successfully!')

            if request.headers.get('HX-Request'):
                return render(request, 'budgets/partials/budget_created.html', {
                    'budget': budget
                })
            return redirect('frontend:budgets:budget_detail', pk=budget.pk)
    else:
        form = QuickBudgetForm()

    return render(request, 'budgets/quick_budget_form.html', {
        'form': form
    })


@login_required
def budget_progress(request, pk):
    """
    Detailed budget progress view.

    Template: budgets/budget_progress.html
    URL: /budgets/<uuid>/progress/
    """
    budget = get_object_or_404(
        Budget.objects.prefetch_related('items', 'items__category'),
        pk=pk,
        user=request.user
    )

    today = timezone.now().date()
    total_days = (budget.end_date - budget.start_date).days + 1
    days_elapsed = min(max((today - budget.start_date).days + 1, 0), total_days)
    days_remaining = max(total_days - days_elapsed, 0)

    # Calculate projections
    daily_budget = budget.total_planned_amount / total_days if total_days > 0 else Decimal('0.00')
    daily_spending = budget.total_spent_amount / days_elapsed if days_elapsed > 0 else Decimal('0.00')
    projected_spending = budget.total_spent_amount + (daily_spending * days_remaining)

    # Build daily projection data for chart
    projection_data = []
    cumulative_budget = Decimal('0.00')
    for day in range(total_days + 1):
        current_date = budget.start_date + timedelta(days=day)
        cumulative_budget += daily_budget
        projection_data.append({
            'date': current_date.isoformat(),
            'budget': float(cumulative_budget),
            'projected': float(min(cumulative_budget, projected_spending)) if day <= days_elapsed else None
        })

    context = {
        'budget': budget,
        'items': budget.items.select_related('category').all(),
        'total_days': total_days,
        'days_elapsed': days_elapsed,
        'days_remaining': days_remaining,
        'daily_budget': daily_budget,
        'daily_spending': daily_spending,
        'projected_spending': projected_spending,
        'is_on_track': projected_spending <= budget.total_planned_amount,
        'projection_data': projection_data,
    }

    return render(request, 'budgets/budget_progress.html', context)
