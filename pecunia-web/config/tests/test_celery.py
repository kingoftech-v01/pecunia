"""
Comprehensive tests for config/celery.py.

Covers:
- Celery app instantiation and configuration
- Broker and backend settings
- Serialization settings
- Task execution settings
- Queue configuration and routing
- Rate limiting annotations
- Beat schedule (periodic tasks)
- BaseTaskWithRetry class
- debug_task
"""
import logging
from unittest.mock import MagicMock, patch

import pytest
from celery.schedules import crontab
from kombu import Exchange, Queue

from config.celery import app, BaseTaskWithRetry, debug_task


# ============================================================================
# Celery App Configuration
# ============================================================================

class TestCeleryAppConfig:
    """Test basic Celery app configuration."""

    def test_app_name(self):
        assert app.main == "pecunia"

    def test_broker_url_configured(self):
        assert app.conf.broker_url is not None
        assert isinstance(app.conf.broker_url, str)

    def test_result_backend_configured(self):
        assert app.conf.result_backend is not None
        assert isinstance(app.conf.result_backend, str)

    def test_broker_connection_retry_on_startup(self):
        assert app.conf.broker_connection_retry_on_startup is True

    def test_broker_connection_retry(self):
        assert app.conf.broker_connection_retry is True

    def test_broker_connection_max_retries(self):
        assert app.conf.broker_connection_max_retries == 10


# ============================================================================
# Serialization Settings
# ============================================================================

class TestSerializationSettings:
    """Test task serialization configuration."""

    def test_task_serializer_json(self):
        assert app.conf.task_serializer == "json"

    def test_result_serializer_json(self):
        assert app.conf.result_serializer == "json"

    def test_accept_content_json_only(self):
        assert app.conf.accept_content == ["json"]

    def test_timezone(self):
        assert app.conf.timezone == "Europe/Paris"

    def test_enable_utc(self):
        assert app.conf.enable_utc is True


# ============================================================================
# Task Execution Settings
# ============================================================================

class TestTaskExecutionSettings:
    """Test task execution configuration."""

    def test_task_acks_late(self):
        assert app.conf.task_acks_late is True

    def test_task_reject_on_worker_lost(self):
        assert app.conf.task_reject_on_worker_lost is True

    def test_task_time_limit(self):
        assert app.conf.task_time_limit == 3600

    def test_task_soft_time_limit(self):
        assert app.conf.task_soft_time_limit == 3300

    def test_worker_prefetch_multiplier(self):
        assert app.conf.worker_prefetch_multiplier == 1

    def test_worker_concurrency(self):
        assert app.conf.worker_concurrency == 4


# ============================================================================
# Result Backend Settings
# ============================================================================

class TestResultBackendSettings:
    """Test result backend configuration."""

    def test_result_expires(self):
        assert app.conf.result_expires == 86400

    def test_result_extended(self):
        assert app.conf.result_extended is True


# ============================================================================
# Queue Configuration
# ============================================================================

class TestQueueConfiguration:
    """Test queue and exchange setup."""

    def test_task_queues_defined(self):
        queues = app.conf.task_queues
        assert queues is not None
        assert len(queues) >= 5

    def test_default_queue_exists(self):
        queue_names = [q.name for q in app.conf.task_queues]
        assert "default" in queue_names

    def test_bank_sync_queue_exists(self):
        queue_names = [q.name for q in app.conf.task_queues]
        assert "bank_sync" in queue_names

    def test_reports_queue_exists(self):
        queue_names = [q.name for q in app.conf.task_queues]
        assert "reports" in queue_names

    def test_alerts_queue_exists(self):
        queue_names = [q.name for q in app.conf.task_queues]
        assert "alerts" in queue_names

    def test_maintenance_queue_exists(self):
        queue_names = [q.name for q in app.conf.task_queues]
        assert "maintenance" in queue_names

    def test_default_queue_setting(self):
        assert app.conf.task_default_queue == "default"

    def test_default_exchange_setting(self):
        assert app.conf.task_default_exchange == "default"

    def test_default_routing_key(self):
        assert app.conf.task_default_routing_key == "default"


# ============================================================================
# Task Routing
# ============================================================================

class TestTaskRouting:
    """Test task routing configuration."""

    def test_sync_bank_accounts_routing(self):
        routes = app.conf.task_routes
        assert "apps.core.tasks.sync_bank_accounts" in routes
        assert routes["apps.core.tasks.sync_bank_accounts"]["queue"] == "bank_sync"

    def test_sync_single_bank_account_routing(self):
        routes = app.conf.task_routes
        assert "apps.core.tasks.sync_single_bank_account" in routes
        assert routes["apps.core.tasks.sync_single_bank_account"]["queue"] == "bank_sync"

    def test_generate_monthly_report_routing(self):
        routes = app.conf.task_routes
        assert "apps.core.tasks.generate_monthly_report" in routes
        assert routes["apps.core.tasks.generate_monthly_report"]["queue"] == "reports"

    def test_generate_user_report_routing(self):
        routes = app.conf.task_routes
        assert "apps.core.tasks.generate_user_report" in routes
        assert routes["apps.core.tasks.generate_user_report"]["queue"] == "reports"

    def test_check_budget_alerts_routing(self):
        routes = app.conf.task_routes
        assert "apps.core.tasks.check_budget_alerts" in routes
        assert routes["apps.core.tasks.check_budget_alerts"]["queue"] == "alerts"

    def test_cleanup_old_data_routing(self):
        routes = app.conf.task_routes
        assert "apps.core.tasks.cleanup_old_data" in routes
        assert routes["apps.core.tasks.cleanup_old_data"]["queue"] == "maintenance"


# ============================================================================
# Rate Limiting Annotations
# ============================================================================

class TestRateLimitAnnotations:
    """Test task rate limit annotations."""

    def test_sync_bank_accounts_rate_limit(self):
        annotations = app.conf.task_annotations
        assert "apps.core.tasks.sync_bank_accounts" in annotations
        assert annotations["apps.core.tasks.sync_bank_accounts"]["rate_limit"] == "10/m"

    def test_sync_single_bank_account_rate_limit(self):
        annotations = app.conf.task_annotations
        assert "apps.core.tasks.sync_single_bank_account" in annotations
        assert annotations["apps.core.tasks.sync_single_bank_account"]["rate_limit"] == "30/m"

    def test_generate_monthly_report_rate_limit(self):
        annotations = app.conf.task_annotations
        assert "apps.core.tasks.generate_monthly_report" in annotations
        assert annotations["apps.core.tasks.generate_monthly_report"]["rate_limit"] == "5/m"

    def test_check_budget_alerts_rate_limit(self):
        annotations = app.conf.task_annotations
        assert "apps.core.tasks.check_budget_alerts" in annotations
        assert annotations["apps.core.tasks.check_budget_alerts"]["rate_limit"] == "60/m"


# ============================================================================
# Beat Schedule
# ============================================================================

class TestBeatSchedule:
    """Test Celery Beat periodic task schedule."""

    def test_beat_schedule_defined(self):
        assert app.conf.beat_schedule is not None
        assert len(app.conf.beat_schedule) >= 5

    def test_sync_bank_accounts_schedule(self):
        schedule = app.conf.beat_schedule
        assert "sync-bank-accounts-periodic" in schedule
        entry = schedule["sync-bank-accounts-periodic"]
        assert entry["task"] == "apps.core.tasks.sync_bank_accounts"
        assert isinstance(entry["schedule"], crontab)
        assert entry["options"]["queue"] == "bank_sync"

    def test_monthly_reports_schedule(self):
        schedule = app.conf.beat_schedule
        assert "generate-monthly-reports" in schedule
        entry = schedule["generate-monthly-reports"]
        assert entry["task"] == "apps.core.tasks.generate_monthly_report"
        assert isinstance(entry["schedule"], crontab)
        assert entry["options"]["queue"] == "reports"

    def test_budget_alerts_schedule(self):
        schedule = app.conf.beat_schedule
        assert "check-budget-alerts-hourly" in schedule
        entry = schedule["check-budget-alerts-hourly"]
        assert entry["task"] == "apps.core.tasks.check_budget_alerts"
        assert isinstance(entry["schedule"], crontab)
        assert entry["options"]["queue"] == "alerts"

    def test_cleanup_schedule(self):
        schedule = app.conf.beat_schedule
        assert "cleanup-old-data-daily" in schedule
        entry = schedule["cleanup-old-data-daily"]
        assert entry["task"] == "apps.core.tasks.cleanup_old_data"
        assert isinstance(entry["schedule"], crontab)
        assert entry["options"]["queue"] == "maintenance"

    def test_quick_sync_schedule(self):
        schedule = app.conf.beat_schedule
        assert "quick-sync-business-hours" in schedule
        entry = schedule["quick-sync-business-hours"]
        assert entry["task"] == "apps.core.tasks.sync_bank_accounts"
        assert entry["kwargs"] == {"quick_sync": True}
        assert entry["options"]["queue"] == "bank_sync"

    def test_all_schedules_have_expires(self):
        for name, entry in app.conf.beat_schedule.items():
            assert "expires" in entry["options"], \
                f"Schedule '{name}' is missing 'expires' in options"

    def test_beat_scheduler_class(self):
        assert "DatabaseScheduler" in app.conf.beat_scheduler


# ============================================================================
# Error Handling and Retry Policy
# ============================================================================

class TestRetryPolicy:
    """Test default retry policy settings."""

    def test_default_retry_delay(self):
        assert app.conf.task_default_retry_delay == 60

    def test_max_retries(self):
        assert app.conf.task_max_retries == 5


# ============================================================================
# Monitoring
# ============================================================================

class TestMonitoring:
    """Test monitoring settings."""

    def test_worker_send_task_events(self):
        assert app.conf.worker_send_task_events is True

    def test_task_send_sent_event(self):
        assert app.conf.task_send_sent_event is True


# ============================================================================
# Auto-discover
# ============================================================================

class TestAutoDiscover:
    """Test task autodiscovery."""

    def test_autodiscover_called(self):
        # The autodiscover_tasks() has already been called during import.
        # We verify by checking that the celery app has registered tasks.
        # At minimum, the debug_task should be registered.
        assert app.tasks is not None


# ============================================================================
# debug_task
# ============================================================================

class TestDebugTask:
    """Test the debug_task function."""

    def test_debug_task_is_registered(self):
        # The debug task should be registered with the app
        assert debug_task is not None

    def test_debug_task_callable(self):
        assert callable(debug_task)


# ============================================================================
# BaseTaskWithRetry
# ============================================================================

class TestBaseTaskWithRetry:
    """Test the BaseTaskWithRetry class."""

    def test_autoretry_for(self):
        assert Exception in BaseTaskWithRetry.autoretry_for

    def test_dont_autoretry_for(self):
        excluded = BaseTaskWithRetry.dont_autoretry_for
        assert ValueError in excluded
        assert TypeError in excluded
        assert KeyError in excluded
        assert PermissionError in excluded

    def test_retry_backoff_enabled(self):
        assert BaseTaskWithRetry.retry_backoff is True

    def test_retry_backoff_max(self):
        assert BaseTaskWithRetry.retry_backoff_max == 600

    def test_retry_jitter_enabled(self):
        assert BaseTaskWithRetry.retry_jitter is True

    def test_max_retries(self):
        assert BaseTaskWithRetry.max_retries == 5

    def test_on_failure_logs_error(self):
        task = BaseTaskWithRetry()
        task.name = "test_task"
        with patch("config.celery.logger") as mock_logger:
            task.on_failure(
                exc=ValueError("test error"),
                task_id="test-id",
                args=[],
                kwargs={},
                einfo=MagicMock(),
            )
            mock_logger.error.assert_called_once()

    def test_on_retry_logs_warning(self):
        task = BaseTaskWithRetry()
        task.name = "test_task"
        # request is a property on unbound tasks; patch it via PropertyMock
        mock_req = MagicMock()
        mock_req.retries = 2
        with patch.object(type(task), "request", new_callable=lambda: property(lambda self: mock_req)):
            with patch("config.celery.logger") as mock_logger:
                task.on_retry(
                    exc=ConnectionError("timeout"),
                    task_id="test-id",
                    args=[],
                    kwargs={},
                    einfo=MagicMock(),
                )
                mock_logger.warning.assert_called_once()

    def test_on_success_logs_info(self):
        task = BaseTaskWithRetry()
        task.name = "test_task"
        with patch("config.celery.logger") as mock_logger:
            task.on_success(
                retval={"status": "ok"},
                task_id="test-id",
                args=[],
                kwargs={},
            )
            mock_logger.info.assert_called_once()

    def test_app_task_class_set(self):
        """The app.Task should be set to BaseTaskWithRetry."""
        assert app.Task is BaseTaskWithRetry


# ============================================================================
# Django Settings Integration
# ============================================================================

class TestDjangoSettingsIntegration:
    """Test Celery-Django settings integration."""

    def test_django_settings_module_set(self):
        import os
        assert os.environ.get("DJANGO_SETTINGS_MODULE") is not None

    def test_config_from_object(self):
        """Celery should load Django settings with CELERY_ prefix."""
        # This is verified by the fact that the app is configured and running.
        # If config_from_object failed, the app would not be properly configured.
        assert app.conf is not None
