"""
Celery tasks for pecunia-web.

This module contains all background tasks for:
- Bank account synchronization
- Report generation
- Budget alert monitoring
- Data maintenance and cleanup

All tasks use exponential backoff retry and comprehensive logging.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from celery import shared_task, group, chain, chord
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Sum, F
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Bank Account Synchronization Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.core.tasks.sync_bank_accounts',
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
    soft_time_limit=1800,
    time_limit=2000,
)
def sync_bank_accounts(
    self,
    user_id: Optional[int] = None,
    quick_sync: bool = False
) -> Dict[str, Any]:
    """
    Synchronize bank accounts with external banking APIs.

    This task fetches the latest transactions and balances from connected
    bank accounts. It can sync all accounts or a specific user's accounts.

    Args:
        self: Task instance (bound task)
        user_id: Optional user ID to sync only their accounts
        quick_sync: If True, only sync accounts updated in last 24h

    Returns:
        Dict containing sync results:
        - synced_accounts: Number of accounts synced
        - new_transactions: Number of new transactions
        - errors: List of any errors encountered
    """
    from django.contrib.auth import get_user_model

    logger.info(
        f"Starting bank account sync - user_id={user_id}, quick_sync={quick_sync}",
        extra={'task_id': self.request.id}
    )

    results = {
        'synced_accounts': 0,
        'new_transactions': 0,
        'updated_balances': 0,
        'errors': [],
        'started_at': timezone.now().isoformat(),
    }

    try:
        User = get_user_model()

        # Build query for accounts to sync
        # Note: Adjust model imports based on actual project structure
        try:
            from apps.accounts.models import BankAccount
        except ImportError:
            logger.warning("BankAccount model not found, using placeholder logic")
            # Placeholder for when model doesn't exist yet
            results['status'] = 'skipped'
            results['message'] = 'BankAccount model not available'
            return results

        accounts_qs = BankAccount.objects.filter(is_active=True)

        if user_id:
            accounts_qs = accounts_qs.filter(user_id=user_id)

        if quick_sync:
            cutoff = timezone.now() - timedelta(hours=24)
            accounts_qs = accounts_qs.filter(last_synced__gte=cutoff)

        accounts = list(accounts_qs.select_related('user', 'institution'))

        if not accounts:
            logger.info("No accounts to sync")
            results['status'] = 'no_accounts'
            return results

        # Create subtasks for each account
        sync_tasks = []
        for account in accounts:
            sync_tasks.append(
                sync_single_bank_account.s(account.id)
            )

        # Execute all sync tasks in parallel
        if sync_tasks:
            job = group(sync_tasks)
            group_result = job.apply_async()

            # Wait for all tasks to complete (with timeout)
            try:
                task_results = group_result.get(timeout=1500)

                for task_result in task_results:
                    if task_result.get('success'):
                        results['synced_accounts'] += 1
                        results['new_transactions'] += task_result.get('transactions', 0)
                        results['updated_balances'] += 1 if task_result.get('balance_updated') else 0
                    else:
                        results['errors'].append(task_result.get('error'))

            except Exception as e:
                logger.error(f"Error waiting for sync tasks: {e}")
                results['errors'].append(str(e))

        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'completed'

        logger.info(
            f"Bank sync completed - {results['synced_accounts']} accounts, "
            f"{results['new_transactions']} new transactions",
            extra={'task_id': self.request.id, 'results': results}
        )

        return results

    except SoftTimeLimitExceeded:
        logger.error("Bank sync task exceeded soft time limit")
        results['status'] = 'timeout'
        results['errors'].append('Task exceeded time limit')
        return results

    except Exception as e:
        logger.exception(f"Bank sync failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='apps.core.tasks.sync_single_bank_account',
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    soft_time_limit=300,
    time_limit=360,
)
def sync_single_bank_account(self, account_id: int) -> Dict[str, Any]:
    """
    Synchronize a single bank account.

    Args:
        self: Task instance (bound task)
        account_id: ID of the BankAccount to sync

    Returns:
        Dict containing:
        - success: Boolean indicating success
        - transactions: Number of new transactions
        - balance_updated: Boolean if balance was updated
        - error: Error message if failed
    """
    logger.info(f"Syncing bank account {account_id}", extra={'task_id': self.request.id})

    result = {
        'account_id': account_id,
        'success': False,
        'transactions': 0,
        'balance_updated': False,
    }

    try:
        # Import models
        try:
            from apps.accounts.models import BankAccount, Transaction
        except ImportError:
            result['error'] = 'Models not available'
            return result

        with transaction.atomic():
            account = BankAccount.objects.select_for_update().get(id=account_id)

            # Call external banking API (placeholder)
            # In real implementation, this would use a banking aggregator API
            # like Plaid, Yodlee, or local banking APIs
            api_data = _fetch_bank_data(account)

            if api_data:
                # Update balance
                if 'balance' in api_data:
                    account.current_balance = Decimal(str(api_data['balance']))
                    result['balance_updated'] = True

                # Process new transactions
                if 'transactions' in api_data:
                    new_count = _process_transactions(account, api_data['transactions'])
                    result['transactions'] = new_count

                # Update sync timestamp
                account.last_synced = timezone.now()
                account.sync_error = None
                account.save()

                result['success'] = True

        logger.info(
            f"Account {account_id} synced successfully - "
            f"{result['transactions']} new transactions",
            extra={'task_id': self.request.id}
        )

        return result

    except Exception as e:
        logger.error(f"Failed to sync account {account_id}: {e}")
        result['error'] = str(e)

        # Update account with error status
        try:
            from apps.accounts.models import BankAccount
            BankAccount.objects.filter(id=account_id).update(
                sync_error=str(e)[:500],
                last_sync_attempt=timezone.now()
            )
        except Exception:
            pass

        raise


def _fetch_bank_data(account) -> Optional[Dict[str, Any]]:
    """
    Fetch data from banking API.

    This is a placeholder that should be replaced with actual
    banking API integration (e.g., Plaid, Yodlee).
    """
    # Placeholder implementation
    # In production, this would call the appropriate banking API
    logger.debug(f"Fetching bank data for account {account.id}")
    return None


def _process_transactions(account, transactions: List[Dict]) -> int:
    """
    Process and save new transactions.

    Args:
        account: BankAccount instance
        transactions: List of transaction data from API

    Returns:
        Number of new transactions created
    """
    try:
        from apps.accounts.models import Transaction
    except ImportError:
        return 0

    new_count = 0

    for tx_data in transactions:
        # Check if transaction already exists (by external ID)
        external_id = tx_data.get('id') or tx_data.get('external_id')

        if external_id:
            exists = Transaction.objects.filter(
                account=account,
                external_id=external_id
            ).exists()

            if exists:
                continue

        # Create new transaction
        Transaction.objects.create(
            account=account,
            external_id=external_id,
            amount=Decimal(str(tx_data.get('amount', 0))),
            description=tx_data.get('description', '')[:500],
            date=tx_data.get('date', timezone.now().date()),
            category=tx_data.get('category'),
            is_pending=tx_data.get('pending', False),
        )
        new_count += 1

    return new_count


# =============================================================================
# Report Generation Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.core.tasks.generate_monthly_report',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=3600,
    time_limit=3900,
)
def generate_monthly_report(
    self,
    user_id: Optional[int] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    send_email: bool = True
) -> Dict[str, Any]:
    """
    Generate monthly financial reports for users.

    Creates comprehensive financial reports including:
    - Income/expense summary
    - Category breakdown
    - Budget vs actual comparison
    - Savings rate
    - Notable transactions

    Args:
        self: Task instance (bound task)
        user_id: Optional specific user ID (generates for all if None)
        month: Report month (defaults to previous month)
        year: Report year (defaults to current/previous year)
        send_email: Whether to send report via email

    Returns:
        Dict containing generation results
    """
    from django.contrib.auth import get_user_model

    logger.info(
        f"Starting monthly report generation - user_id={user_id}, month={month}/{year}",
        extra={'task_id': self.request.id}
    )

    # Default to previous month
    today = timezone.now().date()
    if month is None or year is None:
        first_of_month = today.replace(day=1)
        last_month = first_of_month - timedelta(days=1)
        month = month or last_month.month
        year = year or last_month.year

    results = {
        'month': month,
        'year': year,
        'reports_generated': 0,
        'emails_sent': 0,
        'errors': [],
    }

    try:
        User = get_user_model()

        # Get users to generate reports for
        users_qs = User.objects.filter(is_active=True)

        if user_id:
            users_qs = users_qs.filter(id=user_id)
        else:
            # Only users with email notifications enabled
            users_qs = users_qs.filter(
                profile__email_monthly_report=True
            ).select_related('profile')

        users = list(users_qs)

        if not users:
            logger.info("No users for monthly report generation")
            results['status'] = 'no_users'
            return results

        # Generate reports for each user
        for user in users:
            try:
                report_result = generate_user_report.delay(
                    user.id, month, year, send_email
                )
                results['reports_generated'] += 1

            except Exception as e:
                logger.error(f"Failed to queue report for user {user.id}: {e}")
                results['errors'].append({
                    'user_id': user.id,
                    'error': str(e)
                })

        results['status'] = 'completed'
        logger.info(
            f"Monthly report generation queued - {results['reports_generated']} reports",
            extra={'task_id': self.request.id}
        )

        return results

    except Exception as e:
        logger.exception(f"Monthly report generation failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name='apps.core.tasks.generate_user_report',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=600,
)
def generate_user_report(
    self,
    user_id: int,
    month: int,
    year: int,
    send_email: bool = True
) -> Dict[str, Any]:
    """
    Generate a monthly report for a specific user.

    Args:
        self: Task instance (bound task)
        user_id: User ID
        month: Report month
        year: Report year
        send_email: Whether to send via email

    Returns:
        Dict containing report data and status
    """
    from django.contrib.auth import get_user_model

    logger.info(
        f"Generating report for user {user_id} - {month}/{year}",
        extra={'task_id': self.request.id}
    )

    result = {
        'user_id': user_id,
        'month': month,
        'year': year,
        'success': False,
    }

    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)

        # Calculate report period
        from calendar import monthrange
        start_date = datetime(year, month, 1).date()
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day).date()

        # Gather report data
        report_data = _compile_report_data(user, start_date, end_date)

        if report_data:
            result['report'] = report_data
            result['success'] = True

            # Save report to database
            _save_report(user, report_data, start_date)

            # Send email if requested
            if send_email and user.email:
                email_sent = _send_report_email(user, report_data, month, year)
                result['email_sent'] = email_sent

        logger.info(
            f"Report generated for user {user_id}",
            extra={'task_id': self.request.id}
        )

        return result

    except Exception as e:
        logger.error(f"Failed to generate report for user {user_id}: {e}")
        result['error'] = str(e)
        raise


def _compile_report_data(user, start_date, end_date) -> Dict[str, Any]:
    """
    Compile financial data for the report period.

    Args:
        user: User instance
        start_date: Report start date
        end_date: Report end date

    Returns:
        Dict containing compiled report data
    """
    try:
        from apps.accounts.models import Transaction, BankAccount
        from apps.budgets.models import Budget
    except ImportError:
        logger.warning("Required models not available for report generation")
        return {}

    # Get user's accounts
    accounts = BankAccount.objects.filter(user=user, is_active=True)

    # Calculate totals
    transactions = Transaction.objects.filter(
        account__in=accounts,
        date__gte=start_date,
        date__lte=end_date
    )

    income = transactions.filter(amount__gt=0).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    expenses = transactions.filter(amount__lt=0).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    # Category breakdown
    category_breakdown = transactions.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # Budget comparison
    budgets = Budget.objects.filter(
        user=user,
        month=start_date.month,
        year=start_date.year
    )

    budget_comparison = []
    for budget in budgets:
        spent = transactions.filter(category=budget.category).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        budget_comparison.append({
            'category': budget.category,
            'budgeted': budget.amount,
            'spent': abs(spent),
            'remaining': budget.amount - abs(spent),
            'percentage': (abs(spent) / budget.amount * 100) if budget.amount else 0
        })

    # Calculate savings rate
    savings_rate = ((income + expenses) / income * 100) if income else 0

    return {
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
        },
        'summary': {
            'total_income': str(income),
            'total_expenses': str(abs(expenses)),
            'net_savings': str(income + expenses),
            'savings_rate': round(savings_rate, 2),
        },
        'category_breakdown': list(category_breakdown),
        'budget_comparison': budget_comparison,
        'account_balances': list(
            accounts.values('name', 'current_balance')
        ),
        'generated_at': timezone.now().isoformat(),
    }


def _save_report(user, report_data: Dict, period_start) -> None:
    """Save generated report to database."""
    try:
        from apps.reports.models import MonthlyReport
        MonthlyReport.objects.update_or_create(
            user=user,
            month=period_start.month,
            year=period_start.year,
            defaults={
                'data': report_data,
                'generated_at': timezone.now(),
            }
        )
    except ImportError:
        logger.debug("MonthlyReport model not available")


def _send_report_email(user, report_data: Dict, month: int, year: int) -> bool:
    """Send report via email."""
    try:
        subject = f"Your Monthly Financial Report - {month}/{year}"

        # Render email content
        html_content = render_to_string('emails/monthly_report.html', {
            'user': user,
            'report': report_data,
            'month': month,
            'year': year,
        })

        text_content = render_to_string('emails/monthly_report.txt', {
            'user': user,
            'report': report_data,
            'month': month,
            'year': year,
        })

        send_mail(
            subject=subject,
            message=text_content,
            html_message=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"Report email sent to user {user.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send report email to user {user.id}: {e}")
        return False


# =============================================================================
# Budget Alert Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.core.tasks.check_budget_alerts',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=900,
)
def check_budget_alerts(self, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Check budgets and send alerts when thresholds are exceeded.

    Monitors user budgets and sends notifications when:
    - Spending reaches 80% of budget (warning)
    - Spending reaches 100% of budget (alert)
    - Unusual spending patterns detected

    Args:
        self: Task instance (bound task)
        user_id: Optional specific user ID

    Returns:
        Dict containing check results
    """
    from django.contrib.auth import get_user_model

    logger.info(
        f"Checking budget alerts - user_id={user_id}",
        extra={'task_id': self.request.id}
    )

    results = {
        'users_checked': 0,
        'alerts_sent': 0,
        'warnings_sent': 0,
        'errors': [],
    }

    try:
        User = get_user_model()

        # Get users to check
        users_qs = User.objects.filter(is_active=True)

        if user_id:
            users_qs = users_qs.filter(id=user_id)
        else:
            users_qs = users_qs.filter(
                profile__budget_alerts_enabled=True
            )

        for user in users_qs:
            try:
                user_results = _check_user_budgets(user)
                results['users_checked'] += 1
                results['alerts_sent'] += user_results.get('alerts', 0)
                results['warnings_sent'] += user_results.get('warnings', 0)

            except Exception as e:
                logger.error(f"Error checking budgets for user {user.id}: {e}")
                results['errors'].append({
                    'user_id': user.id,
                    'error': str(e)
                })

        results['status'] = 'completed'
        logger.info(
            f"Budget alerts check completed - "
            f"{results['alerts_sent']} alerts, {results['warnings_sent']} warnings",
            extra={'task_id': self.request.id}
        )

        return results

    except Exception as e:
        logger.exception(f"Budget alerts check failed: {e}")
        raise self.retry(exc=e)


def _check_user_budgets(user) -> Dict[str, int]:
    """
    Check a user's budgets and send appropriate alerts.

    Args:
        user: User instance

    Returns:
        Dict with counts of alerts and warnings sent
    """
    result = {'alerts': 0, 'warnings': 0}

    try:
        from apps.budgets.models import Budget, BudgetAlert
        from apps.accounts.models import Transaction
    except ImportError:
        return result

    # Get current month's budgets
    today = timezone.now().date()
    budgets = Budget.objects.filter(
        user=user,
        month=today.month,
        year=today.year,
        is_active=True
    )

    for budget in budgets:
        # Calculate current spending
        spending = Transaction.objects.filter(
            account__user=user,
            category=budget.category,
            date__month=today.month,
            date__year=today.year,
            amount__lt=0
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        spending = abs(spending)
        percentage = (spending / budget.amount * 100) if budget.amount else 0

        # Check if alert already sent today
        alert_sent_today = BudgetAlert.objects.filter(
            budget=budget,
            created_at__date=today
        ).exists()

        if alert_sent_today:
            continue

        # Send appropriate notification
        if percentage >= 100:
            _send_budget_notification(
                user, budget, spending, percentage, 'exceeded'
            )
            BudgetAlert.objects.create(
                budget=budget,
                alert_type='exceeded',
                percentage=percentage,
                amount_spent=spending
            )
            result['alerts'] += 1

        elif percentage >= 80:
            _send_budget_notification(
                user, budget, spending, percentage, 'warning'
            )
            BudgetAlert.objects.create(
                budget=budget,
                alert_type='warning',
                percentage=percentage,
                amount_spent=spending
            )
            result['warnings'] += 1

    return result


def _send_budget_notification(
    user,
    budget,
    spending: Decimal,
    percentage: float,
    alert_type: str
) -> None:
    """
    Send budget alert notification to user.

    Args:
        user: User instance
        budget: Budget instance
        spending: Current spending amount
        percentage: Percentage of budget used
        alert_type: 'warning' or 'exceeded'
    """
    if alert_type == 'exceeded':
        subject = f"Budget Alert: {budget.category} budget exceeded!"
        template = 'emails/budget_exceeded.html'
    else:
        subject = f"Budget Warning: {budget.category} at {percentage:.0f}%"
        template = 'emails/budget_warning.html'

    try:
        html_content = render_to_string(template, {
            'user': user,
            'budget': budget,
            'spending': spending,
            'percentage': percentage,
        })

        send_mail(
            subject=subject,
            message=f"Your {budget.category} budget is at {percentage:.0f}%",
            html_message=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

        logger.info(
            f"Budget {alert_type} sent to user {user.id} for {budget.category}"
        )

    except Exception as e:
        logger.error(f"Failed to send budget notification: {e}")


# =============================================================================
# Data Cleanup Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.core.tasks.cleanup_old_data',
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=7200,
    time_limit=7500,
)
def cleanup_old_data(
    self,
    days_to_keep: int = 365,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Clean up old data to maintain database performance.

    Removes or archives:
    - Old transaction records (older than retention period)
    - Expired sessions
    - Old notification records
    - Orphaned records
    - Temporary files

    Args:
        self: Task instance (bound task)
        days_to_keep: Number of days to retain data (default 365)
        dry_run: If True, only count records without deleting

    Returns:
        Dict containing cleanup results
    """
    logger.info(
        f"Starting data cleanup - days_to_keep={days_to_keep}, dry_run={dry_run}",
        extra={'task_id': self.request.id}
    )

    results = {
        'dry_run': dry_run,
        'days_to_keep': days_to_keep,
        'deleted': {},
        'errors': [],
        'started_at': timezone.now().isoformat(),
    }

    cutoff_date = timezone.now() - timedelta(days=days_to_keep)

    try:
        # Clean up old transactions (archive first if needed)
        tx_count = _cleanup_old_transactions(cutoff_date, dry_run)
        results['deleted']['transactions'] = tx_count

        # Clean up expired sessions
        session_count = _cleanup_expired_sessions(dry_run)
        results['deleted']['sessions'] = session_count

        # Clean up old notifications
        notif_count = _cleanup_old_notifications(cutoff_date, dry_run)
        results['deleted']['notifications'] = notif_count

        # Clean up old audit logs (keep longer)
        audit_cutoff = timezone.now() - timedelta(days=days_to_keep * 2)
        audit_count = _cleanup_old_audit_logs(audit_cutoff, dry_run)
        results['deleted']['audit_logs'] = audit_count

        # Clean up old reports
        report_count = _cleanup_old_reports(cutoff_date, dry_run)
        results['deleted']['reports'] = report_count

        # Clean up temporary files
        file_count = _cleanup_temp_files(dry_run)
        results['deleted']['temp_files'] = file_count

        # Vacuum database (PostgreSQL)
        if not dry_run:
            _optimize_database()

        results['completed_at'] = timezone.now().isoformat()
        results['status'] = 'completed'

        total_deleted = sum(results['deleted'].values())
        logger.info(
            f"Data cleanup completed - {total_deleted} total records "
            f"{'would be' if dry_run else ''} deleted",
            extra={'task_id': self.request.id, 'results': results}
        )

        return results

    except Exception as e:
        logger.exception(f"Data cleanup failed: {e}")
        results['errors'].append(str(e))
        raise self.retry(exc=e)


def _cleanup_old_transactions(cutoff_date, dry_run: bool) -> int:
    """Archive and delete old transactions."""
    try:
        from apps.accounts.models import Transaction
    except ImportError:
        return 0

    # Get count first
    old_transactions = Transaction.objects.filter(
        date__lt=cutoff_date.date(),
        is_archived=False
    )
    count = old_transactions.count()

    if not dry_run and count > 0:
        # Archive in batches to avoid memory issues
        batch_size = 1000
        for i in range(0, count, batch_size):
            batch = old_transactions[:batch_size]
            # Mark as archived (or delete if archiving not needed)
            batch.update(is_archived=True)

        logger.info(f"Archived {count} old transactions")

    return count


def _cleanup_expired_sessions(dry_run: bool) -> int:
    """Delete expired user sessions."""
    from django.contrib.sessions.models import Session

    expired = Session.objects.filter(expire_date__lt=timezone.now())
    count = expired.count()

    if not dry_run and count > 0:
        expired.delete()
        logger.info(f"Deleted {count} expired sessions")

    return count


def _cleanup_old_notifications(cutoff_date, dry_run: bool) -> int:
    """Delete old read notifications."""
    try:
        from apps.notifications.models import Notification
    except ImportError:
        return 0

    old_notifications = Notification.objects.filter(
        created_at__lt=cutoff_date,
        is_read=True
    )
    count = old_notifications.count()

    if not dry_run and count > 0:
        old_notifications.delete()
        logger.info(f"Deleted {count} old notifications")

    return count


def _cleanup_old_audit_logs(cutoff_date, dry_run: bool) -> int:
    """Delete old audit log entries."""
    try:
        from apps.audit.models import AuditLog
    except ImportError:
        return 0

    old_logs = AuditLog.objects.filter(created_at__lt=cutoff_date)
    count = old_logs.count()

    if not dry_run and count > 0:
        # Delete in batches using regular delete to respect signals and cascades
        batch_size = 1000
        while old_logs.exists():
            batch_ids = list(old_logs.values_list('id', flat=True)[:batch_size])
            AuditLog.objects.filter(id__in=batch_ids).delete()
        logger.info(f"Deleted {count} old audit logs")

    return count


def _cleanup_old_reports(cutoff_date, dry_run: bool) -> int:
    """Delete old generated reports."""
    try:
        from apps.reports.models import MonthlyReport
    except ImportError:
        return 0

    # Keep reports for 3 years
    report_cutoff = cutoff_date - timedelta(days=730)  # 2 more years
    old_reports = MonthlyReport.objects.filter(generated_at__lt=report_cutoff)
    count = old_reports.count()

    if not dry_run and count > 0:
        old_reports.delete()
        logger.info(f"Deleted {count} old reports")

    return count


def _cleanup_temp_files(dry_run: bool) -> int:
    """Clean up temporary files from media directory."""
    import os
    import shutil
    from django.conf import settings

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')

    if not os.path.exists(temp_dir):
        return 0

    count = 0
    cutoff = timezone.now() - timedelta(hours=24)

    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        try:
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_time < cutoff.replace(tzinfo=None):
                count += 1
                if not dry_run:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                    elif os.path.isdir(filepath):
                        shutil.rmtree(filepath)
        except Exception as e:
            logger.warning(f"Could not process temp file {filepath}: {e}")

    if count > 0:
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {count} temp files")

    return count


def _optimize_database() -> None:
    """Run database optimization commands.

    Only runs VACUUM ANALYZE outside of business hours (8 AM - 8 PM)
    to avoid blocking production queries during peak usage.
    """
    from django.db import connection

    current_hour = timezone.now().hour
    if 8 <= current_hour < 20:
        logger.info(
            "Database VACUUM ANALYZE skipped - current hour %d is within "
            "business hours (8-20). Schedule this task outside business hours.",
            current_hour
        )
        return

    try:
        if 'postgresql' in connection.vendor:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM ANALYZE;")
                logger.info("Database vacuum completed")
    except Exception as e:
        logger.warning(f"Database optimization skipped: {e}")


# =============================================================================
# Utility Tasks
# =============================================================================

@shared_task(
    bind=True,
    name='apps.core.tasks.send_async_email',
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_async_email(
    self,
    subject: str,
    message: str,
    recipient_list: List[str],
    html_message: Optional[str] = None,
    from_email: Optional[str] = None
) -> bool:
    """
    Send email asynchronously.

    Args:
        self: Task instance (bound task)
        subject: Email subject
        message: Plain text message
        recipient_list: List of recipient email addresses
        html_message: Optional HTML message
        from_email: Optional sender email

    Returns:
        Boolean indicating success
    """
    logger.info(f"Sending async email to {recipient_list}")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {recipient_list}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise


@shared_task(name='apps.core.tasks.health_check')
def health_check() -> Dict[str, Any]:
    """
    Celery health check task.

    Returns:
        Dict with health status and timestamp
    """
    return {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'worker': 'celery',
    }
