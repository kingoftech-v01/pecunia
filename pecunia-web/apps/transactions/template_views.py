"""
Transactions Template Views (Frontend).

Django views for HTML pages with HTMX/Alpine.js support.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta

from .models import Transaction, TransactionCategory, RecurringTransaction
from .forms import (
    TransactionForm,
    TransactionCategoryForm,
    TransactionFilterForm,
    RecurringTransactionForm,
)


@login_required
def transaction_list(request):
    """
    List all transactions with filtering and pagination.

    Template: transactions/transaction_list.html
    URL: /transactions/
    """
    filter_form = TransactionFilterForm(request.user, request.GET)
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('category')

    # Apply filters
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        type_filter = filter_form.cleaned_data.get('type')
        category = filter_form.cleaned_data.get('category')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')

        if search:
            transactions = transactions.filter(
                Q(description__icontains=search) |
                Q(merchant__icontains=search)
            )
        if type_filter:
            transactions = transactions.filter(type=type_filter)
        if category:
            transactions = transactions.filter(category=category)
        if date_from:
            transactions = transactions.filter(transaction_date__gte=date_from)
        if date_to:
            transactions = transactions.filter(transaction_date__lte=date_to)

    # Calculate totals
    totals = transactions.aggregate(
        income=Sum('amount', filter=Q(type='income')),
        expenses=Sum('amount', filter=Q(type='expense'))
    )
    totals['income'] = totals['income'] or 0
    totals['expenses'] = totals['expenses'] or 0
    totals['balance'] = totals['income'] - totals['expenses']

    # Pagination
    paginator = Paginator(transactions, 20)
    page = request.GET.get('page', 1)
    transactions_page = paginator.get_page(page)

    context = {
        'transactions': transactions_page,
        'filter_form': filter_form,
        'totals': totals,
    }

    # HTMX support - return partial if HX request
    if request.headers.get('HX-Request'):
        return render(request, 'transactions/partials/transaction_table.html', context)

    return render(request, 'transactions/transaction_list.html', context)


@login_required
def transaction_detail(request, pk):
    """
    Transaction detail view.

    Template: transactions/transaction_detail.html
    URL: /transactions/<uuid>/
    """
    transaction = get_object_or_404(
        Transaction.objects.select_related('category', 'bank_account'),
        pk=pk,
        user=request.user
    )
    return render(request, 'transactions/transaction_detail.html', {
        'transaction': transaction
    })


@login_required
def transaction_create(request):
    """
    Create a new transaction.

    Template: transactions/transaction_form.html
    URL: /transactions/create/
    """
    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, 'Transaction created successfully!')

            if request.headers.get('HX-Request'):
                return render(request, 'transactions/partials/transaction_created.html', {
                    'transaction': transaction
                })
            return redirect('frontend:transactions:transaction_list')
    else:
        form = TransactionForm(request.user)

    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'action': 'Create'
    })


@login_required
def transaction_update(request, pk):
    """
    Update an existing transaction.

    Template: transactions/transaction_form.html
    URL: /transactions/<uuid>/edit/
    """
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully!')
            return redirect('frontend:transactions:transaction_detail', pk=pk)
    else:
        form = TransactionForm(request.user, instance=transaction)

    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'transaction': transaction,
        'action': 'Update'
    })


@login_required
def transaction_delete(request, pk):
    """
    Delete a transaction.

    URL: /transactions/<uuid>/delete/
    """
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully!')

        if request.headers.get('HX-Request'):
            return render(request, 'transactions/partials/transaction_deleted.html')
        return redirect('frontend:transactions:transaction_list')

    return render(request, 'transactions/transaction_confirm_delete.html', {
        'transaction': transaction
    })


@login_required
def category_list(request):
    """
    List all transaction categories.

    Template: transactions/category_list.html
    URL: /transactions/categories/
    """
    categories = TransactionCategory.objects.filter(
        user=request.user
    ).annotate(
        transaction_count=Sum('transactions__amount')
    )

    return render(request, 'transactions/category_list.html', {
        'categories': categories
    })


@login_required
def category_create(request):
    """
    Create a new category.

    Template: transactions/category_form.html
    URL: /transactions/categories/create/
    """
    if request.method == 'POST':
        form = TransactionCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, 'Category created successfully!')

            if request.headers.get('HX-Request'):
                return render(request, 'transactions/partials/category_option.html', {
                    'category': category
                })
            return redirect('frontend:transactions:category_list')
    else:
        form = TransactionCategoryForm()

    return render(request, 'transactions/category_form.html', {
        'form': form,
        'action': 'Create'
    })


@login_required
def recurring_list(request):
    """
    List recurring transactions.

    Template: transactions/recurring_list.html
    URL: /transactions/recurring/
    """
    recurring = RecurringTransaction.objects.filter(
        user=request.user
    ).select_related('category')

    return render(request, 'transactions/recurring_list.html', {
        'recurring_transactions': recurring
    })


@login_required
def recurring_create(request):
    """
    Create a new recurring transaction.

    Template: transactions/recurring_form.html
    URL: /transactions/recurring/create/
    """
    if request.method == 'POST':
        form = RecurringTransactionForm(request.user, request.POST)
        if form.is_valid():
            recurring = form.save(commit=False)
            recurring.user = request.user
            recurring.next_occurrence = recurring.start_date
            recurring.save()
            messages.success(request, 'Recurring transaction created!')
            return redirect('frontend:transactions:recurring_list')
    else:
        form = RecurringTransactionForm(request.user)

    return render(request, 'transactions/recurring_form.html', {
        'form': form,
        'action': 'Create'
    })
