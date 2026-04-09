# Scalability Guidelines - Pecunia

**Version**: 1.0
**Last Updated**: 2026-01-28
**Status**: MANDATORY - All platforms MUST follow these guidelines

---

## Table of Contents

1. [Performance Principles](#1-performance-principles)
2. [Database Optimization](#2-database-optimization)
3. [Query Optimization](#3-query-optimization)
4. [Caching Strategies](#4-caching-strategies)
5. [Pagination Standards](#5-pagination-standards)
6. [Async and Background Tasks](#6-async-and-background-tasks)
7. [Connection Pooling](#7-connection-pooling)
8. [API Performance Standards](#8-api-performance-standards)
9. [Monitoring and Observability](#9-monitoring-and-observability)
10. [Load Testing Requirements](#10-load-testing-requirements)
11. [Platform-Specific Optimizations](#11-platform-specific-optimizations)

---

## 1. Performance Principles

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Measure First** | Profile before optimizing |
| **80/20 Rule** | Focus on the 20% causing 80% of issues |
| **Simplicity** | Prefer simple solutions over complex ones |
| **Caching** | Cache aggressively, invalidate carefully |
| **Async** | Never block the main thread |

### Performance Budget

| Metric | Target | Maximum |
|--------|--------|---------|
| API Response Time (P50) | 100ms | 200ms |
| API Response Time (P99) | 500ms | 1000ms |
| Time to First Byte | 200ms | 500ms |
| Database Query Time | 50ms | 200ms |
| Cache Hit Ratio | 90% | - |

### Performance Hierarchy

```
                    +----------------------+
                    |     Application      |  ← Slowest to fix
                    +----------+-----------+
                               |
                    +----------v-----------+
                    |       Database       |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    |         I/O          |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    |       Network        |  ← Usually the bottleneck
                    +----------------------+
```

---

## 2. Database Optimization

### Index Strategy

**Required Indexes (All Platforms)**:

#### Transactions Table
```sql
-- Primary query patterns
CREATE INDEX ix_transactions_user_date ON transactions(user_id, transaction_date DESC);
CREATE INDEX ix_transactions_user_category ON transactions(user_id, category_id);
CREATE INDEX ix_transactions_user_type ON transactions(user_id, type);
CREATE INDEX ix_transactions_user_amount ON transactions(user_id, amount);

-- Sync operations
CREATE INDEX ix_transactions_sync_status ON transactions(is_synced) WHERE is_synced = FALSE;
CREATE INDEX ix_transactions_updated ON transactions(updated_at);

-- Search optimization
CREATE INDEX ix_transactions_description ON transactions USING gin(to_tsvector('english', description));
```

#### Budgets Table
```sql
CREATE INDEX ix_budgets_user_active ON budgets(user_id, is_active);
CREATE INDEX ix_budgets_user_period ON budgets(user_id, period_start, period_end);
CREATE INDEX ix_budgets_category ON budgets(category_id);
```

#### Django Model Definition

```python
# pecunia-web/apps/transactions/models.py
class Transaction(models.Model):
    # ... fields ...

    class Meta:
        indexes = [
            # Composite index for common query pattern
            models.Index(
                fields=['user', '-transaction_date'],
                name='ix_trans_user_date'
            ),
            # Partial index for unsynced records
            models.Index(
                fields=['is_synced'],
                name='ix_trans_unsynced',
                condition=Q(is_synced=False)
            ),
            # Index for category filtering
            models.Index(
                fields=['user', 'category'],
                name='ix_trans_user_category'
            ),
            # Index for type filtering
            models.Index(
                fields=['user', 'type'],
                name='ix_trans_user_type'
            ),
        ]
```

### Partitioning Strategy

For tables with millions of rows, implement time-based partitioning:

```sql
-- PostgreSQL native partitioning
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (transaction_date);

-- Create monthly partitions
CREATE TABLE transactions_2026_01
    PARTITION OF transactions
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE transactions_2026_02
    PARTITION OF transactions
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Automated partition creation (cron job)
-- Run monthly to create next month's partition
```

### Archive Strategy

```python
# pecunia-web/apps/transactions/management/commands/archive_old_transactions.py
"""
Archive transactions older than 2 years.

Run monthly via cron:
    0 2 1 * * python manage.py archive_old_transactions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.transactions.models import Transaction, TransactionArchive


class Command(BaseCommand):
    help = 'Archive transactions older than 2 years'

    def handle(self, *args, **options):
        cutoff_date = timezone.now().date() - timedelta(days=730)

        # Move to archive in batches
        batch_size = 10000
        total_archived = 0

        while True:
            old_transactions = Transaction.objects.filter(
                transaction_date__lt=cutoff_date
            )[:batch_size]

            if not old_transactions:
                break

            # Create archive records
            archives = [
                TransactionArchive(
                    original_id=t.id,
                    user_id=t.user_id,
                    data=t.to_archive_dict(),
                    transaction_date=t.transaction_date
                )
                for t in old_transactions
            ]
            TransactionArchive.objects.bulk_create(archives)

            # Delete originals
            Transaction.objects.filter(
                id__in=[t.id for t in old_transactions]
            ).delete()

            total_archived += len(old_transactions)
            self.stdout.write(f'Archived {total_archived} transactions...')

        self.stdout.write(
            self.style.SUCCESS(f'Archived {total_archived} transactions total')
        )
```

---

## 3. Query Optimization

### N+1 Query Prevention

**Problem**:
```python
# BAD - N+1 queries (1 + N additional queries)
transactions = Transaction.objects.filter(user=user)
for t in transactions:
    print(t.category.name)  # Each access = 1 query!
```

**Solution**:
```python
# GOOD - Single query with JOIN
transactions = Transaction.objects.filter(user=user).select_related('category')
for t in transactions:
    print(t.category.name)  # No additional query

# For reverse ForeignKey / ManyToMany - use prefetch_related
users = User.objects.prefetch_related('transactions').all()
for user in users:
    for transaction in user.transactions.all():  # No additional query
        print(transaction.amount)
```

### Select Only Required Fields

```python
# GOOD - Only fetch needed fields
Transaction.objects.filter(user=user).values('id', 'amount', 'transaction_date')

# Or with ORM model instances
Transaction.objects.filter(user=user).only('id', 'amount', 'transaction_date')

# Defer heavy fields
Transaction.objects.filter(user=user).defer('notes', 'metadata')
```

### Aggregation Optimization

```python
# GOOD - Database-level aggregation
from django.db.models import Sum, Count, Avg

stats = Transaction.objects.filter(
    user=user,
    transaction_date__gte=start_date
).aggregate(
    total_income=Sum('amount', filter=Q(type='income')),
    total_expense=Sum('amount', filter=Q(type='expense')),
    transaction_count=Count('id'),
    average_expense=Avg('amount', filter=Q(type='expense'))
)

# GOOD - Group by category
category_totals = Transaction.objects.filter(
    user=user
).values('category__name').annotate(
    total=Sum('amount'),
    count=Count('id')
).order_by('-total')
```

### Bulk Operations

```python
# BAD - Individual inserts (N queries)
for data in transaction_list:
    Transaction.objects.create(**data)

# GOOD - Bulk insert (1 query)
Transaction.objects.bulk_create([
    Transaction(**data) for data in transaction_list
], batch_size=1000)

# GOOD - Bulk update (1 query)
Transaction.objects.filter(
    id__in=transaction_ids
).update(is_synced=True)

# GOOD - Bulk update with different values
from django.db.models import Case, When

Transaction.objects.filter(
    id__in=category_updates.keys()
).update(
    category_id=Case(
        *[When(id=id, then=cat_id) for id, cat_id in category_updates.items()]
    )
)
```

### Query Analysis

**Django Debug Toolbar** (Development):
```python
# config/settings/development.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

**EXPLAIN ANALYZE** (PostgreSQL):
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT t.*, c.name as category_name
FROM transactions t
LEFT JOIN transaction_categories c ON t.category_id = c.id
WHERE t.user_id = 'uuid-here'
  AND t.transaction_date >= '2026-01-01'
ORDER BY t.transaction_date DESC
LIMIT 20;
```

**Query Logging**:
```python
# Log slow queries
LOGGING = {
    'handlers': {
        'slow_queries': {
            'class': 'logging.FileHandler',
            'filename': 'logs/slow_queries.log',
        }
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['slow_queries'],
            'level': 'DEBUG',
        }
    }
}
```

---

## 4. Caching Strategies

### Cache Hierarchy

```
+------------------+     +------------------+     +------------------+
|   L1: In-Memory  | --> |    L2: Redis     | --> |   L3: Database   |
|      (60s)       |     |    (5-60min)     |     |   (source)       |
+------------------+     +------------------+     +------------------+
```

### Django Cache Configuration

```python
# config/settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'pecunia',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'TIMEOUT': 86400,  # 24 hours
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 60,  # 1 minute
    }
}
```

### Cache Key Patterns

```python
# pecunia-web/apps/core/cache_keys.py
"""
Centralized cache key patterns.

Format: {prefix}:{entity}:{id}:{sub-resource}

Examples:
- user:123:dashboard:summary
- user:123:transactions:recent
- global:categories:list
"""

class CacheKeys:
    # User-specific keys
    USER_DASHBOARD = "user:{user_id}:dashboard:summary"
    USER_TRANSACTIONS_RECENT = "user:{user_id}:transactions:recent"
    USER_BUDGETS_ACTIVE = "user:{user_id}:budgets:active"
    USER_SPENDING_BY_CATEGORY = "user:{user_id}:spending:{category_id}"

    # Global keys
    CATEGORIES_LIST = "global:categories:list"
    EXCHANGE_RATES = "global:exchange_rates:{base_currency}"

    # Cache TTLs (seconds)
    TTL_SHORT = 60           # 1 minute
    TTL_MEDIUM = 300         # 5 minutes
    TTL_LONG = 3600          # 1 hour
    TTL_DAILY = 86400        # 24 hours

    @classmethod
    def user_dashboard(cls, user_id: str) -> str:
        return cls.USER_DASHBOARD.format(user_id=user_id)

    @classmethod
    def user_transactions_recent(cls, user_id: str) -> str:
        return cls.USER_TRANSACTIONS_RECENT.format(user_id=user_id)
```

### Cache Invalidation

```python
# pecunia-web/apps/transactions/signals.py
"""
Cache invalidation on model changes.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Transaction
from apps.core.cache_keys import CacheKeys


@receiver([post_save, post_delete], sender=Transaction)
def invalidate_transaction_cache(sender, instance, **kwargs):
    """
    Invalidate user caches when transactions change.

    Invalidates:
    - Dashboard summary
    - Recent transactions list
    - Spending by category (for affected category)
    """
    user_id = str(instance.user_id)

    cache_keys = [
        CacheKeys.user_dashboard(user_id),
        CacheKeys.user_transactions_recent(user_id),
    ]

    if instance.category_id:
        cache_keys.append(
            CacheKeys.USER_SPENDING_BY_CATEGORY.format(
                user_id=user_id,
                category_id=instance.category_id
            )
        )

    cache.delete_many(cache_keys)
```

### View-Level Caching

```python
# pecunia-web/apps/transactions/views.py
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


class TransactionViewSet(viewsets.ModelViewSet):

    @method_decorator(cache_page(60 * 5))  # 5 minutes
    @method_decorator(vary_on_headers('Authorization'))
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get transaction statistics.

        Cached for 5 minutes per user (varies on Authorization header).
        """
        # ... expensive calculation ...
        return Response(stats)
```

### Function-Level Caching

```python
# pecunia-web/apps/transactions/services.py
from django.core.cache import cache
from apps.core.cache_keys import CacheKeys


def get_dashboard_summary(user_id: str) -> dict:
    """
    Get user dashboard summary with caching.

    Cache TTL: 5 minutes
    """
    cache_key = CacheKeys.user_dashboard(user_id)

    # Try cache first
    summary = cache.get(cache_key)
    if summary is not None:
        return summary

    # Calculate summary
    summary = _calculate_dashboard_summary(user_id)

    # Store in cache
    cache.set(cache_key, summary, CacheKeys.TTL_MEDIUM)

    return summary


def _calculate_dashboard_summary(user_id: str) -> dict:
    """Calculate dashboard summary from database."""
    from .models import Transaction
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().date()
    month_start = today.replace(day=1)

    return Transaction.objects.filter(
        user_id=user_id,
        transaction_date__gte=month_start
    ).aggregate(
        total_income=Sum('amount', filter=Q(type='income')) or 0,
        total_expenses=Sum('amount', filter=Q(type='expense')) or 0,
        transaction_count=Count('id')
    )
```

### Desktop/Mobile Caching

```python
# pecunia-desktop/src/services/cache.py
"""
In-memory LRU cache for desktop application.
"""
from functools import lru_cache
from datetime import datetime, timedelta
from typing import TypeVar, Callable, Any

T = TypeVar('T')


class TTLCache:
    """
    Time-based cache with automatic expiration.
    """

    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get value if not expired."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if datetime.now() > expires_at:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value with TTL."""
        expires_at = datetime.now() + timedelta(seconds=ttl or self._default_ttl)
        self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


# Global cache instance
cache = TTLCache(default_ttl=300)


# Decorator for caching function results
def cached(ttl: int = 300):
    """
    Cache function results.

    Usage:
        @cached(ttl=60)
        def get_categories():
            return fetch_categories_from_api()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            result = cache.get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

---

## 5. Pagination Standards

### Offset-Based Pagination

**Use for**: Standard list views, admin panels

**Request**:
```
GET /api/v1/transactions?page=2&page_size=20
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "count": 1500,
    "page": 2,
    "page_size": 20,
    "total_pages": 75,
    "next": "/api/v1/transactions?page=3&page_size=20",
    "previous": "/api/v1/transactions?page=1&page_size=20"
  }
}
```

**Django Implementation**:
```python
# pecunia-web/apps/core/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for list endpoints.

    Query parameters:
    - page: Page number (1-indexed)
    - page_size: Items per page (default 20, max 100)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'pagination': {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'total_pages': self.page.paginator.num_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }
        })
```

### Cursor-Based Pagination

**Use for**: Real-time data, infinite scroll, large datasets

**Request**:
```
GET /api/v1/transactions?cursor=eyJpZCI6MTAwfQ&limit=20
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIwfQ",
    "previous_cursor": "eyJpZCI6MTAwfQ",
    "has_more": true
  }
}
```

**Django Implementation**:
```python
# pecunia-web/apps/core/pagination.py
from rest_framework.pagination import CursorPagination


class TransactionCursorPagination(CursorPagination):
    """
    Cursor-based pagination for transactions.

    Benefits:
    - Consistent results even when data changes
    - Efficient for large datasets
    - No offset performance degradation
    """
    page_size = 20
    ordering = '-transaction_date'
    cursor_query_param = 'cursor'

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'pagination': {
                'next_cursor': self.get_next_link(),
                'previous_cursor': self.get_previous_link(),
                'has_more': self.has_next
            }
        })
```

### Pagination Limits

| Endpoint | Default | Maximum | Reason |
|----------|---------|---------|--------|
| Transactions | 20 | 100 | Standard list |
| Budgets | 10 | 50 | Smaller dataset |
| Search Results | 20 | 50 | Performance |
| Export | 1000 | 10000 | Bulk operations |
| Admin List | 50 | 200 | Admin efficiency |

---

## 6. Async and Background Tasks

### Task Categories

| Priority | Queue | Examples | Timeout |
|----------|-------|----------|---------|
| Critical | `critical` | Password reset emails | 30s |
| High | `default` | Notifications, sync | 60s |
| Medium | `bank_sync` | Bank account sync | 5min |
| Low | `reports` | Monthly reports | 30min |
| Maintenance | `maintenance` | Data cleanup, archival | 1hr |

### Celery Configuration

```python
# config/celery.py
"""
Celery configuration for background tasks.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('pecunia')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Task routing
app.conf.task_routes = {
    'apps.accounts.tasks.*': {'queue': 'default'},
    'apps.banking.tasks.*': {'queue': 'bank_sync'},
    'apps.transactions.tasks.generate_*': {'queue': 'reports'},
    'apps.core.tasks.cleanup_*': {'queue': 'maintenance'},
}

# Rate limits
app.conf.task_annotations = {
    'apps.banking.tasks.sync_account': {'rate_limit': '10/m'},
    'apps.accounts.tasks.send_email': {'rate_limit': '100/m'},
}

# Scheduled tasks
app.conf.beat_schedule = {
    'process-recurring-transactions': {
        'task': 'apps.transactions.tasks.process_recurring',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'sync-all-bank-accounts': {
        'task': 'apps.banking.tasks.sync_all_accounts',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'cleanup-expired-sessions': {
        'task': 'apps.accounts.tasks.cleanup_sessions',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'archive-old-transactions': {
        'task': 'apps.transactions.tasks.archive_old',
        'schedule': crontab(day_of_month=1, hour=3, minute=0),  # Monthly
    },
}
```

### Task Definition Patterns

```python
# pecunia-web/apps/transactions/tasks.py
"""
Background tasks for transaction processing.
"""
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='apps.transactions.tasks.process_recurring',
    queue='default',
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def process_recurring_transactions(self):
    """
    Process all due recurring transactions.

    Runs daily at midnight.
    Creates transaction records for recurring patterns.

    Retry policy:
    - Max 3 retries
    - 60 second delay between retries
    - 5 minute soft timeout (cleanup chance)
    - 6 minute hard timeout
    """
    from .models import RecurringTransaction, Transaction
    from django.utils import timezone

    try:
        today = timezone.now().date()
        due_recurring = RecurringTransaction.objects.filter(
            is_active=True,
            next_occurrence__lte=today
        ).select_related('user', 'category')

        created_count = 0
        for recurring in due_recurring:
            try:
                Transaction.objects.create(
                    user=recurring.user,
                    amount=recurring.amount,
                    type=recurring.type,
                    category=recurring.category,
                    description=f"[Recurring] {recurring.description}",
                    transaction_date=recurring.next_occurrence,
                )
                recurring.update_next_occurrence()
                created_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to create recurring transaction {recurring.id}: {e}"
                )

        logger.info(f"Created {created_count} recurring transactions")
        return {'created': created_count}

    except SoftTimeLimitExceeded:
        logger.warning("Task timeout approaching, saving progress")
        raise
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise self.retry(exc=e)
```

### Desktop Async Patterns

```python
# pecunia-desktop/src/services/background.py
"""
Background task management for desktop application.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manage background tasks for desktop app.

    Uses:
    - asyncio for I/O-bound tasks (API calls, file operations)
    - ThreadPoolExecutor for CPU-bound tasks (calculations)
    """

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: dict[str, asyncio.Task] = {}

    async def run_async(
        self,
        task_id: str,
        coro: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Run coroutine as background task.

        Args:
            task_id: Unique identifier for task
            coro: Coroutine function to run
            *args, **kwargs: Arguments for coroutine

        Returns:
            Task result
        """
        task = asyncio.create_task(coro(*args, **kwargs))
        self._tasks[task_id] = task

        try:
            result = await task
            return result
        finally:
            self._tasks.pop(task_id, None)

    async def run_in_thread(
        self,
        task_id: str,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Run blocking function in thread pool.

        Use for CPU-bound operations that would block the event loop.
        """
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(
            self._executor,
            lambda: func(*args, **kwargs)
        )
        self._tasks[task_id] = task

        try:
            result = await task
            return result
        finally:
            self._tasks.pop(task_id, None)

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self._tasks.get(task_id)
        if task:
            task.cancel()
            return True
        return False

    def shutdown(self):
        """Shutdown executor and cancel all tasks."""
        for task in self._tasks.values():
            task.cancel()
        self._executor.shutdown(wait=False)
```

### Mobile WorkManager

```kotlin
// pecunia-mobile/app/src/main/java/com/pecunia/workers/SyncWorker.kt
package com.pecunia.workers

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

/**
 * Background worker for transaction synchronization.
 *
 * Features:
 * - Retry with exponential backoff
 * - Network constraint
 * - Battery optimization friendly
 */
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val syncRepository: SyncRepository
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return withContext(Dispatchers.IO) {
            try {
                syncRepository.syncAll()
                Result.success()
            } catch (e: Exception) {
                if (runAttemptCount < 3) {
                    Result.retry()
                } else {
                    Result.failure(
                        workDataOf("error" to e.message)
                    )
                }
            }
        }
    }

    companion object {
        private const val WORK_NAME = "sync_work"

        /**
         * Schedule periodic sync every 15 minutes.
         */
        fun schedulePeriodic(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build()

            val request = PeriodicWorkRequestBuilder<SyncWorker>(
                15, TimeUnit.MINUTES
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    WorkRequest.MIN_BACKOFF_MILLIS,
                    TimeUnit.MILLISECONDS
                )
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        }

        /**
         * Trigger immediate sync.
         */
        fun syncNow(context: Context) {
            val request = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()

            WorkManager.getInstance(context).enqueue(request)
        }
    }
}
```

---

## 7. Connection Pooling

### Database Connection Pooling

**Django (PostgreSQL)**:
```python
# config/settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),

        # Connection pooling
        'CONN_MAX_AGE': 60,  # Keep connections open for 60 seconds
        'CONN_HEALTH_CHECKS': True,  # Verify connection before use

        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 second query timeout
        }
    }
}

# For high-traffic applications, use pgBouncer or similar
# DATABASES['default']['HOST'] = 'pgbouncer-host'
```

**Desktop (SQLAlchemy)**:
```python
# pecunia-desktop/src/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker, scoped_session

def create_database_engine(db_path: str):
    """
    Create SQLAlchemy engine with connection pooling.

    Pool configuration:
    - pool_size: Base number of connections
    - max_overflow: Additional connections when pool exhausted
    - pool_timeout: Wait time for connection from pool
    - pool_recycle: Recycle connections after this many seconds
    """
    engine = create_engine(
        f'sqlite:///{db_path}',
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False,
    )

    # Configure SQLite for better concurrency
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
```

### HTTP Connection Pooling

**Desktop (aiohttp)**:
```python
# pecunia-desktop/src/api/client.py
import aiohttp
from contextlib import asynccontextmanager


class APIClient:
    """
    HTTP client with connection pooling.

    Connection pool settings:
    - limit: Maximum total connections
    - limit_per_host: Maximum connections per host
    - ttl_dns_cache: DNS cache TTL in seconds
    """

    def __init__(self, base_url: str):
        self._base_url = base_url
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,           # Total connection limit
                limit_per_host=20,   # Per-host limit
                ttl_dns_cache=300,   # 5 minute DNS cache
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            timeout = aiohttp.ClientTimeout(
                total=30,
                connect=10,
                sock_read=20,
            )

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )

        return self._session

    async def close(self):
        """Close the session and release connections."""
        if self._session and not self._session.closed:
            await self._session.close()
```

**Mobile (OkHttp)**:
```kotlin
// pecunia-mobile/di/NetworkModule.kt
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
            // Connection pool
            .connectionPool(
                ConnectionPool(
                    maxIdleConnections = 5,
                    keepAliveDuration = 5,
                    timeUnit = TimeUnit.MINUTES
                )
            )
            // Timeouts
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            // Retry
            .retryOnConnectionFailure(true)
            .build()
    }
}
```

---

## 8. API Performance Standards

### Response Time Targets

| Endpoint Type | P50 | P95 | P99 | Alert Threshold |
|---------------|-----|-----|-----|-----------------|
| Simple GET | 50ms | 150ms | 300ms | 500ms |
| List (paginated) | 100ms | 300ms | 500ms | 1s |
| Create/Update | 100ms | 300ms | 500ms | 1s |
| Complex Query | 200ms | 500ms | 1s | 2s |
| Report Generation | 1s | 5s | 10s | 30s |
| Bank Sync | 5s | 15s | 30s | 60s |

### Performance Headers

```python
# pecunia-web/apps/core/middleware.py
import time


class PerformanceHeadersMiddleware:
    """Add performance timing headers to responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()

        response = self.get_response(request)

        # Calculate processing time
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add timing header
        response['X-Response-Time'] = f"{duration_ms:.2f}ms"

        # Add server timing (for detailed breakdown)
        response['Server-Timing'] = f"total;dur={duration_ms:.2f}"

        return response
```

### Compression

```python
# config/settings/base.py
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',  # Enable gzip compression
    # ... other middleware
]

# For API responses, use DRF compression
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}
```

---

## 9. Monitoring and Observability

### Key Metrics to Track

| Category | Metric | Alert Threshold |
|----------|--------|-----------------|
| **Latency** | P99 response time | > 1s |
| **Throughput** | Requests/second | < 50% baseline |
| **Errors** | Error rate | > 1% |
| **Saturation** | CPU usage | > 80% |
| **Saturation** | Memory usage | > 85% |
| **Database** | Query time P99 | > 500ms |
| **Database** | Connection pool usage | > 80% |
| **Cache** | Hit ratio | < 80% |
| **Queue** | Task backlog | > 1000 |

### Logging Best Practices

```python
# pecunia-web/apps/core/logging.py
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def log_performance(operation_name: str):
    """
    Decorator to log function performance.

    Logs:
    - Function name
    - Execution time
    - Success/failure status
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"performance.{operation_name}",
                    extra={
                        'operation': operation_name,
                        'duration_ms': duration,
                        'status': 'success'
                    }
                )
                return result
            except Exception as e:
                duration = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"performance.{operation_name}",
                    extra={
                        'operation': operation_name,
                        'duration_ms': duration,
                        'status': 'error',
                        'error': str(e)
                    }
                )
                raise
        return wrapper
    return decorator
```

---

## 10. Load Testing Requirements

### Pre-Release Requirements

| Test | Requirement | Duration |
|------|-------------|----------|
| Sustained Load | 100 concurrent users | 10 minutes |
| Peak Load | 500 concurrent users | 2 minutes |
| Stress Test | Until failure | Until failure |
| Soak Test | 50 concurrent users | 4 hours |

### Load Test Scenarios

```python
# tests/load/locustfile.py
"""
Load testing with Locust.

Run: locust -f locustfile.py --host=https://api.pecunia.com
"""
from locust import HttpUser, task, between


class PecuniaUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login and get token."""
        response = self.client.post('/api/v1/accounts/login/', json={
            'email': 'loadtest@example.com',
            'password': 'testpassword123'
        })
        self.token = response.json()['access_token']
        self.headers = {'Authorization': f'Bearer {self.token}'}

    @task(10)
    def list_transactions(self):
        """Most common operation."""
        self.client.get(
            '/api/v1/transactions/',
            headers=self.headers
        )

    @task(5)
    def get_dashboard(self):
        """Dashboard summary."""
        self.client.get(
            '/api/v1/transactions/stats/',
            headers=self.headers
        )

    @task(2)
    def create_transaction(self):
        """Create new transaction."""
        self.client.post(
            '/api/v1/transactions/',
            headers=self.headers,
            json={
                'amount': 50.00,
                'type': 'expense',
                'description': 'Load test transaction'
            }
        )

    @task(1)
    def get_budgets(self):
        """List budgets."""
        self.client.get(
            '/api/v1/budgets/',
            headers=self.headers
        )
```

### Performance Baseline

Document baseline metrics after each release:

```markdown
## Performance Baseline - v1.0.0

**Date**: 2026-01-28
**Environment**: Production

| Endpoint | P50 | P95 | P99 | RPS |
|----------|-----|-----|-----|-----|
| GET /transactions | 45ms | 120ms | 250ms | 500 |
| POST /transactions | 65ms | 180ms | 350ms | 200 |
| GET /transactions/stats | 80ms | 200ms | 400ms | 300 |
| GET /budgets | 35ms | 90ms | 180ms | 400 |

**Database Metrics**:
- Average query time: 15ms
- Connection pool utilization: 40%

**Cache Metrics**:
- Hit ratio: 92%
- Average lookup time: 2ms
```

---

## 11. Platform-Specific Optimizations

### Web (Django)

```python
# Performance-optimized ViewSet
class TransactionViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        """Optimized queryset with select_related."""
        return Transaction.objects.filter(
            user=self.request.user
        ).select_related(
            'category',
            'bank_account'
        ).only(
            'id', 'amount', 'type', 'description',
            'transaction_date', 'category__name',
            'bank_account__name'
        )

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent transactions (cached)."""
        cache_key = f"user:{request.user.id}:transactions:recent"
        result = cache.get(cache_key)

        if result is None:
            result = list(
                self.get_queryset()
                .order_by('-transaction_date')[:10]
                .values('id', 'amount', 'type', 'description', 'transaction_date')
            )
            cache.set(cache_key, result, 300)

        return Response({'data': result})
```

### Desktop (Python)

```python
# Optimized database access
class TransactionRepository:
    """Repository with query optimization."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def get_recent(self, user_id: int, limit: int = 20) -> list[Transaction]:
        """Get recent transactions with optimized query."""
        with self._session_factory() as session:
            return session.query(Transaction).options(
                joinedload(Transaction.category)
            ).filter(
                Transaction.user_id == user_id
            ).order_by(
                Transaction.transaction_date.desc()
            ).limit(limit).all()

    def get_summary(self, user_id: int, start_date: date, end_date: date) -> dict:
        """Get summary using database aggregation."""
        with self._session_factory() as session:
            result = session.query(
                func.sum(case((Transaction.type == 'income', Transaction.amount), else_=0)).label('income'),
                func.sum(case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('expenses'),
                func.count(Transaction.id).label('count')
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date.between(start_date, end_date)
            ).first()

            return {
                'income': result.income or 0,
                'expenses': result.expenses or 0,
                'count': result.count or 0
            }
```

### Mobile (Kotlin)

```kotlin
// Optimized Room queries
@Dao
interface TransactionDao {

    /**
     * Get transactions with pagination.
     * Uses Room's built-in paging support.
     */
    @Query("""
        SELECT * FROM transactions
        WHERE user_id = :userId
        ORDER BY date DESC
    """)
    fun getTransactionsPaged(userId: String): PagingSource<Int, TransactionEntity>

    /**
     * Get summary using database aggregation.
     * More efficient than loading all records.
     */
    @Query("""
        SELECT
            SUM(CASE WHEN type = 'INCOME' THEN amount ELSE 0 END) as totalIncome,
            SUM(CASE WHEN type = 'EXPENSE' THEN amount ELSE 0 END) as totalExpenses,
            COUNT(*) as transactionCount
        FROM transactions
        WHERE user_id = :userId
        AND date BETWEEN :startDate AND :endDate
    """)
    suspend fun getSummary(
        userId: String,
        startDate: Long,
        endDate: Long
    ): TransactionSummary
}

// ViewModel with caching
@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val getTransactionsUseCase: GetTransactionsUseCase,
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {

    // Use StateFlow for efficient recomposition
    private val _transactions = MutableStateFlow<List<Transaction>>(emptyList())
    val transactions: StateFlow<List<Transaction>> = _transactions.asStateFlow()

    // Cache summary in SavedStateHandle to survive process death
    val summary: StateFlow<TransactionSummary?> = savedStateHandle
        .getStateFlow("summary", null)

    init {
        // Use viewModelScope for automatic cancellation
        viewModelScope.launch {
            getTransactionsUseCase.getRecent()
                .flowOn(Dispatchers.IO)
                .collect { _transactions.value = it }
        }
    }
}
```

---

**This document is MANDATORY for all Pecunia development.**

*Last performance review: 2026-01-28*
*Next scheduled review: 2026-04-28*
