"""
Tests for Sync models.

Tests SyncLog, SyncQueue, and SyncConflict models including all methods and properties.
"""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.sync.models import SyncLog, SyncQueue, SyncConflict


# =============================================================================
# SyncLog Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncLog:

    def test_create_sync_log(self, user):
        log = SyncLog.objects.create(
            user=user,
            direction='push',
            status='pending',
            device_id='device_123',
            device_name='iPhone 15',
        )
        assert log.pk is not None
        assert log.direction == 'push'
        assert log.status == 'pending'
        assert user.email in str(log)

    def test_mark_completed(self, user):
        log = SyncLog.objects.create(
            user=user,
            direction='pull',
            status='in_progress',
        )
        assert log.completed_at is None
        log.mark_completed()
        log.refresh_from_db()
        assert log.status == 'completed'
        assert log.completed_at is not None

    def test_mark_failed(self, user):
        log = SyncLog.objects.create(
            user=user,
            direction='push',
            status='in_progress',
        )
        log.mark_failed(
            error_message="Connection timeout",
            error_details={'code': 'TIMEOUT', 'retry': True},
        )
        log.refresh_from_db()
        assert log.status == 'failed'
        assert log.error_message == "Connection timeout"
        assert log.error_details == {'code': 'TIMEOUT', 'retry': True}
        assert log.completed_at is not None

    def test_duration_property(self, user):
        started = timezone.now()
        completed = started + timedelta(seconds=5)
        log = SyncLog.objects.create(
            user=user,
            direction='bidirectional',
            status='completed',
            started_at=started,
            completed_at=completed,
        )
        assert log.duration == pytest.approx(5.0, abs=0.1)

    def test_duration_none_when_not_completed(self, user):
        log = SyncLog.objects.create(
            user=user,
            direction='push',
            status='in_progress',
        )
        assert log.duration is None

    def test_ordering(self, user):
        log1 = SyncLog.objects.create(
            user=user, direction='push', status='pending',
        )
        log2 = SyncLog.objects.create(
            user=user, direction='pull', status='pending',
        )
        logs = list(SyncLog.objects.filter(user=user))
        # Ordering is -started_at, newest first
        assert logs[0] == log2

    def test_all_direction_choices(self, user):
        for direction, _ in SyncLog.DIRECTION_CHOICES:
            log = SyncLog.objects.create(
                user=user, direction=direction, status='pending',
            )
            assert log.direction == direction

    def test_all_status_choices(self, user):
        for status_val, _ in SyncLog.STATUS_CHOICES:
            log = SyncLog.objects.create(
                user=user, direction='push', status=status_val,
            )
            assert log.status == status_val

    def test_sync_statistics(self, user):
        log = SyncLog.objects.create(
            user=user,
            direction='bidirectional',
            status='completed',
            items_pushed=10,
            items_pulled=25,
            items_failed=2,
        )
        assert log.items_pushed == 10
        assert log.items_pulled == 25
        assert log.items_failed == 2

    def test_sync_metadata(self, user):
        log = SyncLog.objects.create(
            user=user,
            direction='push',
            status='pending',
            sync_metadata={'client_version': '1.0.0', 'platform': 'ios'},
        )
        assert log.sync_metadata == {'client_version': '1.0.0', 'platform': 'ios'}


# =============================================================================
# SyncQueue Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncQueue:

    def test_create_queue_item(self, user):
        item = SyncQueue.objects.create(
            user=user,
            operation='create',
            model_name='Transaction',
            object_id=str(uuid.uuid4()),
            payload={'amount': 100, 'description': 'Test'},
            client_timestamp=timezone.now(),
        )
        assert item.pk is not None
        assert item.operation == 'create'
        assert item.is_processed is False
        assert "create" in str(item)

    def test_mark_processed(self, user):
        item = SyncQueue.objects.create(
            user=user,
            operation='update',
            model_name='Transaction',
            object_id='obj_123',
            payload={'amount': 200},
            client_timestamp=timezone.now(),
        )
        item.mark_processed()
        item.refresh_from_db()
        assert item.is_processed is True
        assert item.processed_at is not None

    def test_increment_retry(self, user):
        item = SyncQueue.objects.create(
            user=user,
            operation='create',
            model_name='Transaction',
            object_id='obj_456',
            payload={},
            client_timestamp=timezone.now(),
        )
        assert item.retry_count == 0
        item.increment_retry("Connection error")
        item.refresh_from_db()
        assert item.retry_count == 1
        assert item.last_error == "Connection error"

    def test_can_retry_true(self, user):
        item = SyncQueue.objects.create(
            user=user,
            operation='create',
            model_name='Transaction',
            object_id='obj_789',
            payload={},
            client_timestamp=timezone.now(),
            retry_count=0,
            max_retries=3,
        )
        assert item.can_retry is True

    def test_can_retry_false(self, user):
        item = SyncQueue.objects.create(
            user=user,
            operation='create',
            model_name='Transaction',
            object_id='obj_max',
            payload={},
            client_timestamp=timezone.now(),
            retry_count=3,
            max_retries=3,
        )
        assert item.can_retry is False

    def test_can_retry_at_limit(self, user):
        item = SyncQueue.objects.create(
            user=user,
            operation='update',
            model_name='Transaction',
            object_id='obj_limit',
            payload={},
            client_timestamp=timezone.now(),
            retry_count=2,
            max_retries=3,
        )
        assert item.can_retry is True

    def test_ordering_by_priority(self, user):
        low = SyncQueue.objects.create(
            user=user, operation='create', model_name='T',
            object_id='1', payload={}, priority=1,
            client_timestamp=timezone.now(),
        )
        high = SyncQueue.objects.create(
            user=user, operation='create', model_name='T',
            object_id='2', payload={}, priority=4,
            client_timestamp=timezone.now(),
        )
        items = list(SyncQueue.objects.filter(user=user))
        assert items[0] == high  # Higher priority first (-priority ordering)

    def test_all_operations(self, user):
        for op, _ in SyncQueue.OPERATION_CHOICES:
            item = SyncQueue.objects.create(
                user=user, operation=op, model_name='T',
                object_id=str(uuid.uuid4()), payload={},
                client_timestamp=timezone.now(),
            )
            assert item.operation == op


# =============================================================================
# SyncConflict Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncConflict:

    def test_create_conflict(self, user):
        conflict = SyncConflict.objects.create(
            user=user,
            model_name='Transaction',
            object_id='obj_conflict',
            server_version={'amount': 100, 'description': 'Server version'},
            client_version={'amount': 150, 'description': 'Client version'},
        )
        assert conflict.pk is not None
        assert conflict.resolution_status == 'pending'
        assert conflict.resolved_at is None
        assert "pending" in str(conflict)

    def test_resolve_server_wins(self, user):
        conflict = SyncConflict.objects.create(
            user=user,
            model_name='Transaction',
            object_id='obj_sw',
            server_version={'amount': 100},
            client_version={'amount': 150},
        )
        conflict.resolve('server_wins', resolved_version={'amount': 100})
        conflict.refresh_from_db()
        assert conflict.resolution_status == 'server_wins'
        assert conflict.resolved_version == {'amount': 100}
        assert conflict.resolved_at is not None

    def test_resolve_client_wins(self, user):
        conflict = SyncConflict.objects.create(
            user=user,
            model_name='Transaction',
            object_id='obj_cw',
            server_version={'amount': 100},
            client_version={'amount': 150},
        )
        conflict.resolve('client_wins', resolved_version={'amount': 150})
        conflict.refresh_from_db()
        assert conflict.resolution_status == 'client_wins'
        assert conflict.resolved_version == {'amount': 150}

    def test_resolve_merged(self, user):
        conflict = SyncConflict.objects.create(
            user=user,
            model_name='Transaction',
            object_id='obj_merge',
            server_version={'amount': 100, 'description': 'Server'},
            client_version={'amount': 150, 'description': 'Client'},
        )
        merged = {'amount': 150, 'description': 'Server'}
        conflict.resolve('merged', resolved_version=merged)
        conflict.refresh_from_db()
        assert conflict.resolution_status == 'merged'
        assert conflict.resolved_version == merged

    def test_resolve_manual(self, user):
        conflict = SyncConflict.objects.create(
            user=user,
            model_name='Transaction',
            object_id='obj_manual',
            server_version={'amount': 100},
            client_version={'amount': 150},
        )
        conflict.resolve('manual', resolved_version={'amount': 125})
        conflict.refresh_from_db()
        assert conflict.resolution_status == 'manual'

    def test_ordering(self, user):
        c1 = SyncConflict.objects.create(
            user=user, model_name='T', object_id='1',
            server_version={}, client_version={},
        )
        c2 = SyncConflict.objects.create(
            user=user, model_name='T', object_id='2',
            server_version={}, client_version={},
        )
        conflicts = list(SyncConflict.objects.filter(user=user))
        assert conflicts[0] == c2  # Newest first

    def test_all_resolution_types(self, user):
        for res_type, _ in SyncConflict.RESOLUTION_CHOICES:
            conflict = SyncConflict.objects.create(
                user=user, model_name='T',
                object_id=str(uuid.uuid4()),
                server_version={}, client_version={},
                resolution_status=res_type,
            )
            assert conflict.resolution_status == res_type
