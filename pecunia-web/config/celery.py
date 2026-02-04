"""
Celery configuration for pecunia-web Django project.

This module configures Celery with Django integration, including:
- Redis as message broker and result backend
- Celery Beat for scheduled tasks
- Task routing and queues
- Retry policies with exponential backoff
"""

import os
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery application
app = Celery('pecunia')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# =============================================================================
# Broker and Backend Configuration
# =============================================================================

app.conf.broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.conf.result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# Redis connection settings
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 10

# =============================================================================
# Task Serialization
# =============================================================================

app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'Europe/Paris'
app.conf.enable_utc = True

# =============================================================================
# Task Execution Settings
# =============================================================================

app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.task_time_limit = 3600  # 1 hour hard limit
app.conf.task_soft_time_limit = 3300  # 55 minutes soft limit
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_concurrency = 4

# =============================================================================
# Result Backend Settings
# =============================================================================

app.conf.result_expires = 86400  # 24 hours
app.conf.result_extended = True

# =============================================================================
# Queue Configuration
# =============================================================================

default_exchange = Exchange('default', type='direct')
bank_exchange = Exchange('bank', type='direct')
reports_exchange = Exchange('reports', type='direct')
maintenance_exchange = Exchange('maintenance', type='direct')

app.conf.task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('bank_sync', bank_exchange, routing_key='bank.sync'),
    Queue('reports', reports_exchange, routing_key='reports.#'),
    Queue('alerts', default_exchange, routing_key='alerts'),
    Queue('maintenance', maintenance_exchange, routing_key='maintenance.#'),
)

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

# Task routing
app.conf.task_routes = {
    'apps.core.tasks.sync_bank_accounts': {
        'queue': 'bank_sync',
        'routing_key': 'bank.sync',
    },
    'apps.core.tasks.sync_single_bank_account': {
        'queue': 'bank_sync',
        'routing_key': 'bank.sync',
    },
    'apps.core.tasks.generate_monthly_report': {
        'queue': 'reports',
        'routing_key': 'reports.monthly',
    },
    'apps.core.tasks.generate_user_report': {
        'queue': 'reports',
        'routing_key': 'reports.user',
    },
    'apps.core.tasks.check_budget_alerts': {
        'queue': 'alerts',
        'routing_key': 'alerts',
    },
    'apps.core.tasks.cleanup_old_data': {
        'queue': 'maintenance',
        'routing_key': 'maintenance.cleanup',
    },
}

# =============================================================================
# Rate Limiting
# =============================================================================

app.conf.task_annotations = {
    'apps.core.tasks.sync_bank_accounts': {
        'rate_limit': '10/m',  # 10 per minute
    },
    'apps.core.tasks.sync_single_bank_account': {
        'rate_limit': '30/m',  # 30 per minute
    },
    'apps.core.tasks.generate_monthly_report': {
        'rate_limit': '5/m',  # 5 per minute
    },
    'apps.core.tasks.check_budget_alerts': {
        'rate_limit': '60/m',  # 60 per minute
    },
}

# =============================================================================
# Celery Beat Schedule (Periodic Tasks)
# =============================================================================

app.conf.beat_schedule = {
    # Bank account synchronization - every 6 hours
    'sync-bank-accounts-periodic': {
        'task': 'apps.core.tasks.sync_bank_accounts',
        'schedule': crontab(minute=0, hour='*/6'),
        'options': {
            'expires': 3600,
            'queue': 'bank_sync',
        },
    },

    # Monthly report generation - 1st of each month at 6:00 AM
    'generate-monthly-reports': {
        'task': 'apps.core.tasks.generate_monthly_report',
        'schedule': crontab(minute=0, hour=6, day_of_month=1),
        'options': {
            'expires': 86400,
            'queue': 'reports',
        },
    },

    # Budget alerts check - every hour
    'check-budget-alerts-hourly': {
        'task': 'apps.core.tasks.check_budget_alerts',
        'schedule': crontab(minute=0),
        'options': {
            'expires': 1800,
            'queue': 'alerts',
        },
    },

    # Cleanup old data - daily at 3:00 AM
    'cleanup-old-data-daily': {
        'task': 'apps.core.tasks.cleanup_old_data',
        'schedule': crontab(minute=0, hour=3),
        'options': {
            'expires': 7200,
            'queue': 'maintenance',
        },
    },

    # Quick sync during business hours - every 30 minutes between 8 AM and 8 PM
    'quick-sync-business-hours': {
        'task': 'apps.core.tasks.sync_bank_accounts',
        'schedule': crontab(minute='0,30', hour='8-20'),
        'kwargs': {'quick_sync': True},
        'options': {
            'expires': 1800,
            'queue': 'bank_sync',
        },
    },
}

# Beat scheduler database
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

# =============================================================================
# Error Handling and Retry Policy
# =============================================================================

app.conf.task_default_retry_delay = 60  # 1 minute
app.conf.task_max_retries = 5

# =============================================================================
# Monitoring
# =============================================================================

app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# =============================================================================
# Auto-discover tasks from installed Django apps
# =============================================================================

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')


# =============================================================================
# Task Base Class with Common Functionality
# =============================================================================

from celery import Task
import logging

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    """
    Base task class with automatic retry and exponential backoff.

    Features:
    - Exponential backoff retry
    - Comprehensive logging
    - Error tracking
    """

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max
    retry_jitter = True
    max_retries = 5

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            exc_info=einfo,
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'args': args,
                'kwargs': kwargs,
            }
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.warning(
            f"Task {self.name}[{task_id}] retrying: {exc}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'retry_count': self.request.retries,
            }
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(
            f"Task {self.name}[{task_id}] completed successfully",
            extra={
                'task_id': task_id,
                'task_name': self.name,
            }
        )
        super().on_success(retval, task_id, args, kwargs)


# Export the base task for use in other modules
app.Task = BaseTaskWithRetry
