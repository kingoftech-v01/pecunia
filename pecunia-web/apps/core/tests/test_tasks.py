"""
Comprehensive tests for apps.core.tasks.

Covers:
- sync_bank_accounts, sync_single_bank_account
- generate_monthly_report, generate_user_report
- check_budget_alerts
- cleanup_old_data
- send_async_email, health_check
- Helper functions: _fetch_bank_data, _process_transactions, _compile_report_data,
  _save_report, _send_report_email, _check_user_budgets, _send_budget_notification,
  _cleanup_old_transactions, _cleanup_expired_sessions, _cleanup_old_notifications,
  _cleanup_old_audit_logs, _cleanup_old_reports, _cleanup_temp_files, _optimize_database
"""
import os
import tempfile
import time
from datetime import datetime, timedelta, date
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.core.tasks import (
    _fetch_bank_data,
    _process_transactions,
    _compile_report_data,
    _save_report,
    _send_report_email,
    _check_user_budgets,
    _send_budget_notification,
    _cleanup_old_transactions,
    _cleanup_expired_sessions,
    _cleanup_old_notifications,
    _cleanup_old_audit_logs,
    _cleanup_old_reports,
    _cleanup_temp_files,
    _optimize_database,
    health_check,
)

# Import the celery-decorated task objects
from apps.core import tasks as tasks_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_bound_task(task_fn, *args, **kwargs):
    """Call a bound Celery task's run method for testing.

    For bound tasks (bind=True), task.run() is the autoretry wrapper and
    task._orig_run() is the original function. Both are already bound to
    the task instance (self is provided automatically). We mock retry on
    the task object to prevent actual retries, then call run().
    """
    original_retry = task_fn.retry
    task_fn.retry = MagicMock(side_effect=Exception("retry called"))
    try:
        result = task_fn.run(*args, **kwargs)
        return result, task_fn
    finally:
        task_fn.retry = original_retry


# ============================================================================
# health_check
# ============================================================================

class TestHealthCheck:

    def test_returns_healthy(self):
        result = health_check()
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["worker"] == "celery"


# ============================================================================
# _fetch_bank_data
# ============================================================================

class TestFetchBankData:

    def test_returns_none(self):
        account = MagicMock()
        account.id = 1
        result = _fetch_bank_data(account)
        assert result is None


# ============================================================================
# _process_transactions
# ============================================================================

class TestProcessTransactions:

    def test_import_error_returns_zero(self):
        with patch.dict("sys.modules", {"apps.accounts.models": None}):
            result = _process_transactions(MagicMock(), [])
        assert result == 0

    @patch("apps.core.tasks.timezone")
    def test_creates_new_transactions(self, mock_tz):
        mock_tz.now.return_value.date.return_value = date.today()
        account = MagicMock()

        mock_tx_model = MagicMock()
        mock_tx_model.objects.filter.return_value.exists.return_value = False

        mock_module = MagicMock()
        mock_module.Transaction = mock_tx_model

        tx_data = [
            {"id": "tx_1", "amount": 100, "description": "Test", "date": date.today()},
            {"id": "tx_2", "amount": -50, "description": "Purchase"},
        ]

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}):
            result = _process_transactions(account, tx_data)
        assert result == 2
        assert mock_tx_model.objects.create.call_count == 2

    def test_skips_existing_transactions(self):
        account = MagicMock()
        mock_tx_model = MagicMock()
        mock_tx_model.objects.filter.return_value.exists.return_value = True
        mock_module = MagicMock()
        mock_module.Transaction = mock_tx_model

        tx_data = [{"id": "tx_existing", "amount": 100}]

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}):
            result = _process_transactions(account, tx_data)
        assert result == 0
        mock_tx_model.objects.create.assert_not_called()

    @patch("apps.core.tasks.timezone")
    def test_transaction_without_external_id(self, mock_tz):
        mock_tz.now.return_value.date.return_value = date.today()
        account = MagicMock()
        mock_tx_model = MagicMock()
        mock_module = MagicMock()
        mock_module.Transaction = mock_tx_model

        tx_data = [{"amount": 25, "description": "No ID"}]

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}):
            result = _process_transactions(account, tx_data)
        assert result == 1


# ============================================================================
# sync_bank_accounts
# ============================================================================

class TestSyncBankAccounts:

    def test_import_error_returns_skipped(self):
        with patch.dict("sys.modules", {"apps.accounts.models": None}):
            result, _ = _call_bound_task(
                tasks_module.sync_bank_accounts, user_id=1
            )
        assert result["status"] == "skipped"
        assert "not available" in result["message"]

    @patch("apps.core.tasks.sync_single_bank_account")
    def test_no_accounts_to_sync(self, mock_single_sync):
        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.return_value.select_related.return_value = []
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("django.contrib.auth.get_user_model"):
            result, _ = _call_bound_task(
                tasks_module.sync_bank_accounts, user_id=1
            )
        assert result["status"] == "no_accounts"

    @patch("apps.core.tasks.sync_single_bank_account")
    @patch("apps.core.tasks.group")
    def test_sync_accounts_success(self, mock_group, mock_single_sync):
        account1 = MagicMock(id=1)
        account2 = MagicMock(id=2)

        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.return_value.select_related.return_value = [
            account1, account2
        ]
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model

        mock_group_result = MagicMock()
        mock_group_result.get.return_value = [
            {"success": True, "transactions": 5, "balance_updated": True},
            {"success": True, "transactions": 3, "balance_updated": False},
        ]
        mock_group.return_value.apply_async.return_value = mock_group_result

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("django.contrib.auth.get_user_model"):
            result, _ = _call_bound_task(
                tasks_module.sync_bank_accounts, user_id=None, quick_sync=False
            )

        assert result["status"] == "completed"
        assert result["synced_accounts"] == 2
        assert result["new_transactions"] == 8
        assert result["updated_balances"] == 1

    @patch("apps.core.tasks.sync_single_bank_account")
    @patch("apps.core.tasks.group")
    def test_sync_with_errors(self, mock_group, mock_single_sync):
        account1 = MagicMock(id=1)

        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.return_value.select_related.return_value = [account1]
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model

        mock_group_result = MagicMock()
        mock_group_result.get.return_value = [
            {"success": False, "error": "API timeout"},
        ]
        mock_group.return_value.apply_async.return_value = mock_group_result

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("django.contrib.auth.get_user_model"):
            result, _ = _call_bound_task(tasks_module.sync_bank_accounts)
        assert len(result["errors"]) == 1

    @patch("apps.core.tasks.sync_single_bank_account")
    @patch("apps.core.tasks.group")
    def test_sync_group_timeout(self, mock_group, mock_single_sync):
        account1 = MagicMock(id=1)

        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.return_value.select_related.return_value = [account1]
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model

        mock_group_result = MagicMock()
        mock_group_result.get.side_effect = Exception("Timeout")
        mock_group.return_value.apply_async.return_value = mock_group_result

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("django.contrib.auth.get_user_model"):
            result, _ = _call_bound_task(tasks_module.sync_bank_accounts)
        assert len(result["errors"]) == 1
        assert "Timeout" in result["errors"][0]

    def test_soft_time_limit_exceeded(self):
        from celery.exceptions import SoftTimeLimitExceeded

        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.return_value.select_related.side_effect = (
            SoftTimeLimitExceeded()
        )
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("django.contrib.auth.get_user_model"):
            result, _ = _call_bound_task(tasks_module.sync_bank_accounts)
        assert result["status"] == "timeout"

    def test_general_exception_retries(self):
        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.side_effect = RuntimeError("DB connection failed")
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("django.contrib.auth.get_user_model"):
            with pytest.raises(Exception, match="retry called"):
                _call_bound_task(tasks_module.sync_bank_accounts)

    @patch("apps.core.tasks.sync_single_bank_account")
    @patch("apps.core.tasks.group")
    def test_quick_sync_filters(self, mock_group, mock_single_sync):
        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.return_value.filter.return_value.select_related.return_value = []
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("django.contrib.auth.get_user_model"):
            result, _ = _call_bound_task(
                tasks_module.sync_bank_accounts, quick_sync=True
            )
        assert result["status"] == "no_accounts"


# ============================================================================
# sync_single_bank_account
# ============================================================================

class TestSyncSingleBankAccount:

    def test_import_error(self):
        with patch.dict("sys.modules", {"apps.accounts.models": None}):
            result, _ = _call_bound_task(
                tasks_module.sync_single_bank_account, account_id=1
            )
        assert result["success"] is False
        assert result["error"] == "Models not available"

    @patch("apps.core.tasks._process_transactions", return_value=5)
    @patch("apps.core.tasks._fetch_bank_data")
    def test_successful_sync(self, mock_fetch, mock_process):
        mock_fetch.return_value = {
            "balance": "1000.50",
            "transactions": [{"id": "tx_1", "amount": 50}],
        }

        mock_account = MagicMock(id=1)
        mock_ba_model = MagicMock()
        mock_ba_model.objects.select_for_update.return_value.get.return_value = mock_account
        mock_tx_model = MagicMock()
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model
        mock_module.Transaction = mock_tx_model

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("apps.core.tasks.transaction") as mock_atomic:
            mock_atomic.atomic.return_value.__enter__ = MagicMock(return_value=None)
            mock_atomic.atomic.return_value.__exit__ = MagicMock(return_value=False)
            result, _ = _call_bound_task(
                tasks_module.sync_single_bank_account, account_id=1
            )

        assert result["success"] is True
        assert result["balance_updated"] is True
        assert result["transactions"] == 5

    @patch("apps.core.tasks._fetch_bank_data", return_value=None)
    def test_no_api_data(self, mock_fetch):
        mock_account = MagicMock(id=1)
        mock_ba_model = MagicMock()
        mock_ba_model.objects.select_for_update.return_value.get.return_value = mock_account
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model
        mock_module.Transaction = MagicMock()

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("apps.core.tasks.transaction") as mock_atomic:
            mock_atomic.atomic.return_value.__enter__ = MagicMock(return_value=None)
            mock_atomic.atomic.return_value.__exit__ = MagicMock(return_value=False)
            result, _ = _call_bound_task(
                tasks_module.sync_single_bank_account, account_id=1
            )
        assert result["balance_updated"] is False

    def test_exception_updates_account_error(self):
        mock_ba_model = MagicMock()
        mock_ba_model.objects.select_for_update.return_value.get.side_effect = (
            RuntimeError("DB error")
        )
        mock_module = MagicMock()
        mock_module.BankAccount = mock_ba_model
        mock_module.Transaction = MagicMock()

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}), \
             patch("apps.core.tasks.transaction") as mock_atomic:
            mock_atomic.atomic.return_value.__enter__ = MagicMock(return_value=None)
            mock_atomic.atomic.return_value.__exit__ = MagicMock(return_value=False)
            # The original function re-raises after updating account error.
            # Then the autoretry wrapper catches the exception and calls retry,
            # which we've mocked to raise Exception("retry called").
            with pytest.raises(Exception):
                _call_bound_task(
                    tasks_module.sync_single_bank_account, account_id=1
                )
        mock_ba_model.objects.filter.return_value.update.assert_called_once()


# ============================================================================
# generate_monthly_report
# ============================================================================

class TestGenerateMonthlyReport:

    @patch("apps.core.tasks.generate_user_report")
    def test_no_users(self, mock_gen_user):
        mock_user_model = MagicMock()
        mock_user_model.objects.filter.return_value.filter.return_value.select_related.return_value = []

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_monthly_report, month=1, year=2025
            )
        assert result["status"] == "no_users"

    @patch("apps.core.tasks.generate_user_report")
    def test_generates_for_users(self, mock_gen_user):
        user1, user2 = MagicMock(id=1), MagicMock(id=2)
        mock_user_model = MagicMock()
        mock_user_model.objects.filter.return_value.filter.return_value.select_related.return_value = [
            user1, user2
        ]

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_monthly_report, month=6, year=2025
            )
        assert result["status"] == "completed"
        assert result["reports_generated"] == 2
        assert mock_gen_user.delay.call_count == 2

    @patch("apps.core.tasks.generate_user_report")
    def test_specific_user(self, mock_gen_user):
        user1 = MagicMock(id=42)
        mock_user_model = MagicMock()
        # For specific user_id, the code does users_qs.filter(id=user_id)
        # then list(users_qs) without select_related
        mock_user_model.objects.filter.return_value.filter.return_value = [user1]

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_monthly_report,
                user_id=42, month=1, year=2025, send_email=False
            )
        assert result["reports_generated"] >= 0

    def test_defaults_to_previous_month(self):
        mock_user_model = MagicMock()
        mock_user_model.objects.filter.return_value.filter.return_value.select_related.return_value = []

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(tasks_module.generate_monthly_report)
        assert "month" in result
        assert "year" in result

    @patch("apps.core.tasks.generate_user_report")
    def test_queue_error_recorded(self, mock_gen_user):
        user1 = MagicMock(id=1)
        mock_gen_user.delay.side_effect = Exception("Queue full")
        mock_user_model = MagicMock()
        mock_user_model.objects.filter.return_value.filter.return_value.select_related.return_value = [
            user1
        ]

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_monthly_report, month=1, year=2025
            )
        assert len(result["errors"]) == 1
        assert result["errors"][0]["user_id"] == 1

    def test_exception_retries(self):
        with patch("django.contrib.auth.get_user_model", side_effect=RuntimeError("fail")):
            with pytest.raises(Exception, match="retry called"):
                _call_bound_task(
                    tasks_module.generate_monthly_report, month=1, year=2025
                )


# ============================================================================
# generate_user_report
# ============================================================================

class TestGenerateUserReport:

    @patch("apps.core.tasks._send_report_email", return_value=True)
    @patch("apps.core.tasks._save_report")
    @patch("apps.core.tasks._compile_report_data")
    def test_successful_generation(self, mock_compile, mock_save, mock_email):
        mock_compile.return_value = {"summary": {"total_income": "3000"}}

        mock_user = MagicMock(id=1, email="test@example.com")
        mock_user_model = MagicMock()
        mock_user_model.objects.get.return_value = mock_user

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_user_report,
                user_id=1, month=6, year=2025
            )

        assert result["success"] is True
        assert result["email_sent"] is True
        mock_save.assert_called_once()
        mock_email.assert_called_once()

    @patch("apps.core.tasks._compile_report_data", return_value={})
    def test_empty_report_data(self, mock_compile):
        mock_user = MagicMock(id=1, email="test@example.com")
        mock_user_model = MagicMock()
        mock_user_model.objects.get.return_value = mock_user

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_user_report,
                user_id=1, month=6, year=2025
            )
        assert result["success"] is False

    @patch("apps.core.tasks._save_report")
    @patch("apps.core.tasks._compile_report_data")
    def test_no_email_when_disabled(self, mock_compile, mock_save):
        mock_compile.return_value = {"data": "something"}
        mock_user = MagicMock(id=1, email="test@example.com")
        mock_user_model = MagicMock()
        mock_user_model.objects.get.return_value = mock_user

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_user_report,
                user_id=1, month=6, year=2025, send_email=False
            )
        assert result["success"] is True
        assert "email_sent" not in result

    @patch("apps.core.tasks._save_report")
    @patch("apps.core.tasks._compile_report_data")
    def test_no_email_when_no_user_email(self, mock_compile, mock_save):
        mock_compile.return_value = {"data": "something"}
        mock_user = MagicMock(id=1, email="")
        mock_user_model = MagicMock()
        mock_user_model.objects.get.return_value = mock_user

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(
                tasks_module.generate_user_report,
                user_id=1, month=6, year=2025, send_email=True
            )
        assert result["success"] is True
        assert "email_sent" not in result

    def test_user_not_found_raises(self):
        mock_user_model = MagicMock()
        mock_user_model.objects.get.side_effect = Exception("User not found")

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            with pytest.raises(Exception):
                _call_bound_task(
                    tasks_module.generate_user_report,
                    user_id=999, month=1, year=2025
                )


# ============================================================================
# _compile_report_data
# ============================================================================

class TestCompileReportData:

    def test_import_error_returns_empty(self):
        with patch.dict("sys.modules", {
            "apps.accounts.models": None,
            "apps.budgets.models": None,
        }):
            result = _compile_report_data(MagicMock(), date(2025, 1, 1), date(2025, 1, 31))
        assert result == {}

    def test_compiles_data(self):
        user = MagicMock()
        mock_accounts = MagicMock()
        mock_transactions = MagicMock()
        mock_transactions.filter.return_value.aggregate.side_effect = [
            {"total": Decimal("3000")},   # income
            {"total": Decimal("-1500")},   # expenses
        ]
        mock_transactions.values.return_value.annotate.return_value.order_by.return_value = []

        mock_ba_model = MagicMock()
        mock_ba_model.objects.filter.return_value = mock_accounts
        mock_accounts.values.return_value = []

        mock_tx_model = MagicMock()
        mock_tx_model.objects.filter.return_value = mock_transactions

        mock_budget_model = MagicMock()
        mock_budget_model.objects.filter.return_value = []

        mock_accounts_module = MagicMock()
        mock_accounts_module.Transaction = mock_tx_model
        mock_accounts_module.BankAccount = mock_ba_model

        mock_budgets_module = MagicMock()
        mock_budgets_module.Budget = mock_budget_model

        with patch.dict("sys.modules", {
            "apps.accounts.models": mock_accounts_module,
            "apps.budgets.models": mock_budgets_module,
        }):
            result = _compile_report_data(user, date(2025, 1, 1), date(2025, 1, 31))

        assert "summary" in result
        assert "period" in result
        assert result["summary"]["total_income"] == "3000"


# ============================================================================
# _save_report
# ============================================================================

class TestSaveReport:

    def test_import_error_handled(self):
        with patch.dict("sys.modules", {"apps.reports.models": None}):
            _save_report(MagicMock(), {"data": "test"}, date(2025, 1, 1))

    def test_saves_report(self):
        mock_report_model = MagicMock()
        mock_module = MagicMock()
        mock_module.MonthlyReport = mock_report_model

        with patch.dict("sys.modules", {"apps.reports.models": mock_module}):
            _save_report(MagicMock(), {"data": "test"}, date(2025, 6, 1))
        mock_report_model.objects.update_or_create.assert_called_once()


# ============================================================================
# _send_report_email
# ============================================================================

class TestSendReportEmail:

    @patch("apps.core.tasks.send_mail")
    @patch("apps.core.tasks.render_to_string", return_value="<html>report</html>")
    def test_successful_send(self, mock_render, mock_send_mail):
        user = MagicMock(id=1, email="test@example.com")
        result = _send_report_email(user, {"data": "report"}, 6, 2025)
        assert result is True
        mock_send_mail.assert_called_once()

    @patch("apps.core.tasks.send_mail", side_effect=Exception("SMTP error"))
    @patch("apps.core.tasks.render_to_string", return_value="<html>report</html>")
    def test_send_failure(self, mock_render, mock_send_mail):
        user = MagicMock(id=1, email="test@example.com")
        result = _send_report_email(user, {"data": "report"}, 6, 2025)
        assert result is False


# ============================================================================
# check_budget_alerts
# ============================================================================

class TestCheckBudgetAlerts:

    @patch("apps.core.tasks._check_user_budgets", return_value={"alerts": 1, "warnings": 2})
    def test_checks_users(self, mock_check):
        user1 = MagicMock(id=1)
        user2 = MagicMock(id=2)
        mock_user_model = MagicMock()
        mock_user_model.objects.filter.return_value.filter.return_value = [user1, user2]

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(tasks_module.check_budget_alerts)
        assert result["status"] == "completed"
        assert result["users_checked"] == 2
        assert result["alerts_sent"] == 2
        assert result["warnings_sent"] == 4

    @patch("apps.core.tasks._check_user_budgets", side_effect=Exception("DB error"))
    def test_user_error_recorded(self, mock_check):
        user1 = MagicMock(id=1)
        mock_user_model = MagicMock()
        mock_user_model.objects.filter.return_value.filter.return_value = [user1]

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model):
            result, _ = _call_bound_task(tasks_module.check_budget_alerts)
        assert len(result["errors"]) == 1

    def test_specific_user(self):
        user1 = MagicMock(id=42)
        mock_user_model = MagicMock()
        # check_budget_alerts does: users_qs = User.objects.filter(is_active=True)
        # then: users_qs = users_qs.filter(id=user_id) when user_id is provided
        mock_user_model.objects.filter.return_value.filter.return_value = [user1]

        with patch("django.contrib.auth.get_user_model", return_value=mock_user_model), \
             patch("apps.core.tasks._check_user_budgets",
                   return_value={"alerts": 0, "warnings": 0}):
            result, _ = _call_bound_task(
                tasks_module.check_budget_alerts, user_id=42
            )
        assert result["users_checked"] == 1

    def test_exception_retries(self):
        with patch("django.contrib.auth.get_user_model", side_effect=RuntimeError("fail")):
            with pytest.raises(Exception, match="retry called"):
                _call_bound_task(tasks_module.check_budget_alerts)


# ============================================================================
# _check_user_budgets
# ============================================================================

class TestCheckUserBudgets:

    def test_import_error_returns_empty(self):
        with patch.dict("sys.modules", {
            "apps.budgets.models": None,
            "apps.accounts.models": None,
        }):
            result = _check_user_budgets(MagicMock())
        assert result == {"alerts": 0, "warnings": 0}

    @patch("apps.core.tasks._send_budget_notification")
    def test_budget_exceeded(self, mock_notify):
        user = MagicMock()
        budget = MagicMock(category="Food", amount=Decimal("500"))

        mock_budget_model = MagicMock()
        mock_budget_model.objects.filter.return_value = [budget]
        mock_alert_model = MagicMock()
        mock_alert_model.objects.filter.return_value.exists.return_value = False

        mock_tx_model = MagicMock()
        mock_tx_model.objects.filter.return_value.aggregate.return_value = {
            "total": Decimal("-600")
        }

        mock_budgets_mod = MagicMock()
        mock_budgets_mod.Budget = mock_budget_model
        mock_budgets_mod.BudgetAlert = mock_alert_model

        mock_accounts_mod = MagicMock()
        mock_accounts_mod.Transaction = mock_tx_model

        with patch.dict("sys.modules", {
            "apps.budgets.models": mock_budgets_mod,
            "apps.accounts.models": mock_accounts_mod,
        }):
            result = _check_user_budgets(user)

        assert result["alerts"] == 1
        mock_alert_model.objects.create.assert_called_once()
        mock_notify.assert_called_once()

    @patch("apps.core.tasks._send_budget_notification")
    def test_budget_warning(self, mock_notify):
        user = MagicMock()
        budget = MagicMock(category="Transport", amount=Decimal("200"))

        mock_budget_model = MagicMock()
        mock_budget_model.objects.filter.return_value = [budget]
        mock_alert_model = MagicMock()
        mock_alert_model.objects.filter.return_value.exists.return_value = False

        mock_tx_model = MagicMock()
        mock_tx_model.objects.filter.return_value.aggregate.return_value = {
            "total": Decimal("-180")
        }

        mock_budgets_mod = MagicMock()
        mock_budgets_mod.Budget = mock_budget_model
        mock_budgets_mod.BudgetAlert = mock_alert_model

        mock_accounts_mod = MagicMock()
        mock_accounts_mod.Transaction = mock_tx_model

        with patch.dict("sys.modules", {
            "apps.budgets.models": mock_budgets_mod,
            "apps.accounts.models": mock_accounts_mod,
        }):
            result = _check_user_budgets(user)

        assert result["warnings"] == 1

    @patch("apps.core.tasks._send_budget_notification")
    def test_alert_already_sent_today(self, mock_notify):
        user = MagicMock()
        budget = MagicMock(category="Food", amount=Decimal("500"))

        mock_budget_model = MagicMock()
        mock_budget_model.objects.filter.return_value = [budget]
        mock_alert_model = MagicMock()
        mock_alert_model.objects.filter.return_value.exists.return_value = True

        mock_tx_model = MagicMock()
        mock_tx_model.objects.filter.return_value.aggregate.return_value = {
            "total": Decimal("-600")
        }

        mock_budgets_mod = MagicMock()
        mock_budgets_mod.Budget = mock_budget_model
        mock_budgets_mod.BudgetAlert = mock_alert_model

        mock_accounts_mod = MagicMock()
        mock_accounts_mod.Transaction = mock_tx_model

        with patch.dict("sys.modules", {
            "apps.budgets.models": mock_budgets_mod,
            "apps.accounts.models": mock_accounts_mod,
        }):
            result = _check_user_budgets(user)

        assert result["alerts"] == 0
        assert result["warnings"] == 0
        mock_notify.assert_not_called()

    @patch("apps.core.tasks._send_budget_notification")
    def test_under_threshold_no_alert(self, mock_notify):
        user = MagicMock()
        budget = MagicMock(category="Entertainment", amount=Decimal("300"))

        mock_budget_model = MagicMock()
        mock_budget_model.objects.filter.return_value = [budget]
        mock_alert_model = MagicMock()
        mock_alert_model.objects.filter.return_value.exists.return_value = False

        mock_tx_model = MagicMock()
        mock_tx_model.objects.filter.return_value.aggregate.return_value = {
            "total": Decimal("-150")
        }

        mock_budgets_mod = MagicMock()
        mock_budgets_mod.Budget = mock_budget_model
        mock_budgets_mod.BudgetAlert = mock_alert_model

        mock_accounts_mod = MagicMock()
        mock_accounts_mod.Transaction = mock_tx_model

        with patch.dict("sys.modules", {
            "apps.budgets.models": mock_budgets_mod,
            "apps.accounts.models": mock_accounts_mod,
        }):
            result = _check_user_budgets(user)

        assert result["alerts"] == 0
        assert result["warnings"] == 0


# ============================================================================
# _send_budget_notification
# ============================================================================

class TestSendBudgetNotification:

    @patch("apps.core.tasks.send_mail")
    @patch("apps.core.tasks.render_to_string", return_value="<html>alert</html>")
    def test_exceeded_notification(self, mock_render, mock_send_mail):
        user = MagicMock(email="test@example.com", id=1)
        budget = MagicMock(category="Food")
        _send_budget_notification(user, budget, Decimal("600"), 120.0, "exceeded")
        mock_send_mail.assert_called_once()

    @patch("apps.core.tasks.send_mail")
    @patch("apps.core.tasks.render_to_string", return_value="<html>warning</html>")
    def test_warning_notification(self, mock_render, mock_send_mail):
        user = MagicMock(email="test@example.com", id=1)
        budget = MagicMock(category="Transport")
        _send_budget_notification(user, budget, Decimal("180"), 90.0, "warning")
        mock_send_mail.assert_called_once()

    @patch("apps.core.tasks.render_to_string", side_effect=Exception("Template error"))
    def test_notification_failure_logged(self, mock_render):
        user = MagicMock(email="test@example.com", id=1)
        budget = MagicMock(category="Food")
        # Should not raise
        _send_budget_notification(user, budget, Decimal("600"), 120.0, "exceeded")


# ============================================================================
# cleanup_old_data
# ============================================================================

class TestCleanupOldData:

    @patch("apps.core.tasks._optimize_database")
    @patch("apps.core.tasks._cleanup_temp_files", return_value=0)
    @patch("apps.core.tasks._cleanup_old_reports", return_value=0)
    @patch("apps.core.tasks._cleanup_old_audit_logs", return_value=0)
    @patch("apps.core.tasks._cleanup_old_notifications", return_value=0)
    @patch("apps.core.tasks._cleanup_expired_sessions", return_value=5)
    @patch("apps.core.tasks._cleanup_old_transactions", return_value=10)
    def test_full_cleanup(self, mock_tx, mock_sess, mock_notif, mock_audit,
                          mock_reports, mock_temp, mock_optimize):
        result, _ = _call_bound_task(
            tasks_module.cleanup_old_data, days_to_keep=365, dry_run=False
        )
        assert result["status"] == "completed"
        assert result["deleted"]["transactions"] == 10
        assert result["deleted"]["sessions"] == 5
        mock_optimize.assert_called_once()

    @patch("apps.core.tasks._optimize_database")
    @patch("apps.core.tasks._cleanup_temp_files", return_value=3)
    @patch("apps.core.tasks._cleanup_old_reports", return_value=2)
    @patch("apps.core.tasks._cleanup_old_audit_logs", return_value=1)
    @patch("apps.core.tasks._cleanup_old_notifications", return_value=4)
    @patch("apps.core.tasks._cleanup_expired_sessions", return_value=0)
    @patch("apps.core.tasks._cleanup_old_transactions", return_value=0)
    def test_dry_run(self, mock_tx, mock_sess, mock_notif, mock_audit,
                     mock_reports, mock_temp, mock_optimize):
        result, _ = _call_bound_task(
            tasks_module.cleanup_old_data, dry_run=True
        )
        assert result["dry_run"] is True
        mock_optimize.assert_not_called()

    @patch("apps.core.tasks._cleanup_old_transactions", side_effect=RuntimeError("fail"))
    def test_exception_retries(self, mock_tx):
        with pytest.raises(Exception, match="retry called"):
            _call_bound_task(tasks_module.cleanup_old_data)


# ============================================================================
# _cleanup_old_transactions
# ============================================================================

class TestCleanupOldTransactions:

    def test_import_error(self):
        with patch.dict("sys.modules", {"apps.accounts.models": None}):
            assert _cleanup_old_transactions(timezone.now(), dry_run=False) == 0

    def test_dry_run(self):
        mock_tx_model = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 42
        mock_tx_model.objects.filter.return_value = mock_qs
        mock_module = MagicMock()
        mock_module.Transaction = mock_tx_model

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}):
            result = _cleanup_old_transactions(timezone.now(), dry_run=True)
        assert result == 42
        mock_qs.update.assert_not_called()

    def test_actual_cleanup(self):
        mock_tx_model = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 5
        mock_qs.__getitem__ = MagicMock(return_value=mock_qs)
        mock_tx_model.objects.filter.return_value = mock_qs
        mock_module = MagicMock()
        mock_module.Transaction = mock_tx_model

        with patch.dict("sys.modules", {"apps.accounts.models": mock_module}):
            result = _cleanup_old_transactions(timezone.now(), dry_run=False)
        assert result == 5


# ============================================================================
# _cleanup_expired_sessions
# ============================================================================

class TestCleanupExpiredSessions:

    @patch("django.contrib.sessions.models.Session")
    def test_dry_run(self, mock_session_cls):
        mock_qs = MagicMock()
        mock_qs.count.return_value = 10
        mock_session_cls.objects.filter.return_value = mock_qs
        result = _cleanup_expired_sessions(dry_run=True)
        assert result == 10
        mock_qs.delete.assert_not_called()

    @patch("django.contrib.sessions.models.Session")
    def test_actual_cleanup(self, mock_session_cls):
        mock_qs = MagicMock()
        mock_qs.count.return_value = 3
        mock_session_cls.objects.filter.return_value = mock_qs
        result = _cleanup_expired_sessions(dry_run=False)
        assert result == 3
        mock_qs.delete.assert_called_once()


# ============================================================================
# _cleanup_old_notifications
# ============================================================================

class TestCleanupOldNotifications:

    def test_import_error(self):
        with patch.dict("sys.modules", {"apps.notifications.models": None}):
            assert _cleanup_old_notifications(timezone.now(), dry_run=False) == 0

    def test_dry_run(self):
        mock_model = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 7
        mock_model.objects.filter.return_value = mock_qs
        mock_module = MagicMock()
        mock_module.Notification = mock_model

        with patch.dict("sys.modules", {"apps.notifications.models": mock_module}):
            result = _cleanup_old_notifications(timezone.now(), dry_run=True)
        assert result == 7
        mock_qs.delete.assert_not_called()


# ============================================================================
# _cleanup_old_audit_logs
# ============================================================================

class TestCleanupOldAuditLogs:

    def test_import_error(self):
        with patch.dict("sys.modules", {"apps.audit.models": None}):
            assert _cleanup_old_audit_logs(timezone.now(), dry_run=False) == 0

    def test_dry_run(self):
        mock_model = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 100
        mock_model.objects.filter.return_value = mock_qs
        mock_module = MagicMock()
        mock_module.AuditLog = mock_model

        with patch.dict("sys.modules", {"apps.audit.models": mock_module}):
            result = _cleanup_old_audit_logs(timezone.now(), dry_run=True)
        assert result == 100
        mock_qs.delete.assert_not_called()


# ============================================================================
# _cleanup_old_reports
# ============================================================================

class TestCleanupOldReports:

    def test_import_error(self):
        with patch.dict("sys.modules", {"apps.reports.models": None}):
            assert _cleanup_old_reports(timezone.now(), dry_run=False) == 0

    def test_dry_run(self):
        mock_model = MagicMock()
        mock_qs = MagicMock()
        mock_qs.count.return_value = 20
        mock_model.objects.filter.return_value = mock_qs
        mock_module = MagicMock()
        mock_module.MonthlyReport = mock_model

        with patch.dict("sys.modules", {"apps.reports.models": mock_module}):
            result = _cleanup_old_reports(timezone.now(), dry_run=True)
        assert result == 20
        mock_qs.delete.assert_not_called()


# ============================================================================
# _cleanup_temp_files
# ============================================================================

class TestCleanupTempFiles:

    @override_settings(MEDIA_ROOT="/nonexistent/path")
    def test_nonexistent_dir(self):
        result = _cleanup_temp_files(dry_run=False)
        assert result == 0

    def test_cleans_old_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = os.path.join(tmpdir, "temp")
            os.makedirs(temp_dir)

            old_file = os.path.join(temp_dir, "old.txt")
            with open(old_file, "w") as f:
                f.write("old")
            old_time = time.time() - 86400 * 2
            os.utime(old_file, (old_time, old_time))

            new_file = os.path.join(temp_dir, "new.txt")
            with open(new_file, "w") as f:
                f.write("new")

            with override_settings(MEDIA_ROOT=tmpdir):
                result = _cleanup_temp_files(dry_run=False)
            assert result == 1
            assert not os.path.exists(old_file)
            assert os.path.exists(new_file)

    def test_dry_run_does_not_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = os.path.join(tmpdir, "temp")
            os.makedirs(temp_dir)

            old_file = os.path.join(temp_dir, "old.txt")
            with open(old_file, "w") as f:
                f.write("old")
            old_time = time.time() - 86400 * 2
            os.utime(old_file, (old_time, old_time))

            with override_settings(MEDIA_ROOT=tmpdir):
                result = _cleanup_temp_files(dry_run=True)
            assert result == 1
            assert os.path.exists(old_file)

    def test_cleans_old_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = os.path.join(tmpdir, "temp")
            os.makedirs(temp_dir)

            old_dir = os.path.join(temp_dir, "old_dir")
            os.makedirs(old_dir)
            old_time = time.time() - 86400 * 2
            os.utime(old_dir, (old_time, old_time))

            with override_settings(MEDIA_ROOT=tmpdir):
                result = _cleanup_temp_files(dry_run=False)
            assert result == 1
            assert not os.path.exists(old_dir)


# ============================================================================
# _optimize_database
# ============================================================================

class TestOptimizeDatabase:
    """Test _optimize_database which imports connection locally via
    'from django.db import connection'. We patch django.db.connection."""

    @patch("apps.core.tasks.timezone")
    @patch("django.db.connection")
    def test_skips_during_business_hours(self, mock_conn, mock_tz):
        mock_tz.now.return_value.hour = 12
        _optimize_database()
        mock_conn.cursor.assert_not_called()

    @patch("apps.core.tasks.timezone")
    @patch("django.db.connection")
    def test_runs_outside_business_hours(self, mock_conn, mock_tz):
        mock_tz.now.return_value.hour = 3
        mock_conn.vendor = "postgresql"
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        _optimize_database()
        mock_cursor.execute.assert_called_with("VACUUM ANALYZE;")

    @patch("apps.core.tasks.timezone")
    @patch("django.db.connection")
    def test_non_postgresql_skipped(self, mock_conn, mock_tz):
        mock_tz.now.return_value.hour = 3
        mock_conn.vendor = "sqlite"
        _optimize_database()
        assert mock_conn.cursor.call_count == 0

    @patch("apps.core.tasks.timezone")
    @patch("django.db.connection")
    def test_exception_handled(self, mock_conn, mock_tz):
        mock_tz.now.return_value.hour = 3
        mock_conn.vendor = "postgresql"
        mock_conn.cursor.side_effect = Exception("Connection lost")
        _optimize_database()

    @patch("apps.core.tasks.timezone")
    @patch("django.db.connection")
    def test_boundary_hour_8(self, mock_conn, mock_tz):
        mock_tz.now.return_value.hour = 8
        _optimize_database()
        mock_conn.cursor.assert_not_called()

    @patch("apps.core.tasks.timezone")
    @patch("django.db.connection")
    def test_boundary_hour_20(self, mock_conn, mock_tz):
        mock_tz.now.return_value.hour = 20
        mock_conn.vendor = "postgresql"
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        _optimize_database()


# ============================================================================
# send_async_email
# ============================================================================

class TestSendAsyncEmail:

    @patch("apps.core.tasks.send_mail")
    def test_successful_send(self, mock_send_mail):
        result, _ = _call_bound_task(
            tasks_module.send_async_email,
            subject="Test",
            message="Hello",
            recipient_list=["test@example.com"],
        )
        assert result is True
        mock_send_mail.assert_called_once()

    @patch("apps.core.tasks.send_mail")
    def test_with_html_and_from_email(self, mock_send_mail):
        result, _ = _call_bound_task(
            tasks_module.send_async_email,
            subject="Test",
            message="Hello",
            recipient_list=["test@example.com"],
            html_message="<b>Hello</b>",
            from_email="custom@example.com",
        )
        assert result is True

    @patch("apps.core.tasks.send_mail", side_effect=Exception("SMTP Error"))
    def test_failure_raises(self, mock_send_mail):
        with pytest.raises(Exception):
            _call_bound_task(
                tasks_module.send_async_email,
                subject="Test",
                message="Hello",
                recipient_list=["test@example.com"],
            )
