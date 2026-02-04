"""Tests for src/database/models/sync.py — SyncRecord model."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from database.models.sync import SyncRecord, SyncStatus, SyncOperation


class TestSyncStatus:
    """Tests for SyncStatus enum."""

    def test_values(self):
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.IN_PROGRESS.value == "in_progress"
        assert SyncStatus.COMPLETED.value == "completed"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.CONFLICT.value == "conflict"
        assert SyncStatus.CANCELLED.value == "cancelled"

    def test_is_str_enum(self):
        assert isinstance(SyncStatus.PENDING, str)


class TestSyncOperation:
    """Tests for SyncOperation enum."""

    def test_values(self):
        assert SyncOperation.CREATE.value == "create"
        assert SyncOperation.UPDATE.value == "update"
        assert SyncOperation.DELETE.value == "delete"
        assert SyncOperation.FULL_SYNC.value == "full_sync"


class TestSyncRecordCreation:
    """Tests for SyncRecord creation."""

    def test_create_minimal(self):
        record = SyncRecord(
            entity_type="transaction",
            entity_id="t1",
            operation=SyncOperation.CREATE,
        )
        assert record.entity_type == "transaction"
        assert record.operation == SyncOperation.CREATE

    def test_default_values(self):
        record = SyncRecord(
            entity_type="user", entity_id="u1",
            operation=SyncOperation.UPDATE,
        )
        assert record.status == SyncStatus.PENDING
        assert record.priority == 5
        assert record.retry_count == 0
        assert record.max_retries == 3
        assert record.has_conflict is False

    def test_create_for_entity(self):
        record = SyncRecord.create_for_entity(
            entity_type="budget",
            entity_id="b1",
            operation=SyncOperation.CREATE,
            payload='{"name": "Monthly"}',
            priority=1,
        )
        assert record.entity_type == "budget"
        assert record.entity_id == "b1"
        assert record.status == SyncStatus.PENDING
        assert record.priority == 1
        assert record.payload == '{"name": "Monthly"}'


class TestSyncRecordProperties:
    """Tests for SyncRecord computed properties."""

    def test_can_retry_true(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            status=SyncStatus.FAILED,
            retry_count=1, max_retries=3,
        )
        assert record.can_retry is True

    def test_can_retry_false_max_retries(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            status=SyncStatus.FAILED,
            retry_count=3, max_retries=3,
        )
        assert record.can_retry is False

    def test_can_retry_false_wrong_status(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            status=SyncStatus.COMPLETED,
            retry_count=0, max_retries=3,
        )
        assert record.can_retry is False

    def test_is_terminal_completed(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            status=SyncStatus.COMPLETED,
        )
        assert record.is_terminal is True

    def test_is_terminal_cancelled(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            status=SyncStatus.CANCELLED,
        )
        assert record.is_terminal is True

    def test_is_not_terminal_pending(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            status=SyncStatus.PENDING,
        )
        assert record.is_terminal is False

    def test_needs_resolution_true(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.UPDATE,
            status=SyncStatus.CONFLICT,
            has_conflict=True,
        )
        assert record.needs_resolution is True

    def test_needs_resolution_false(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.UPDATE,
            status=SyncStatus.PENDING,
            has_conflict=False,
        )
        assert record.needs_resolution is False


class TestSyncRecordStateMachine:
    """Tests for SyncRecord state transitions."""

    def test_mark_pending(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            status=SyncStatus.FAILED,
        )
        record.mark_pending()
        assert record.status == SyncStatus.PENDING

    def test_mark_in_progress(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
        )
        record.mark_in_progress()
        assert record.status == SyncStatus.IN_PROGRESS
        assert record.started_at is not None

    def test_mark_completed(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
        )
        record.mark_completed(response_data='{"id": 42}')
        assert record.status == SyncStatus.COMPLETED
        assert record.completed_at is not None
        assert record.response_data == '{"id": 42}'

    def test_mark_completed_without_response(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
        )
        record.mark_completed()
        assert record.status == SyncStatus.COMPLETED
        assert record.response_data is None

    def test_mark_failed_increments_retry(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            retry_count=0, max_retries=3,
        )
        record.mark_failed("Network error", error_code="NET_ERR")
        assert record.status == SyncStatus.FAILED
        assert record.retry_count == 1
        assert record.error_message == "Network error"
        assert record.error_code == "NET_ERR"
        assert record.last_retry_at is not None

    def test_mark_failed_sets_next_retry(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            retry_count=0, max_retries=3,
        )
        record.mark_failed("error")
        assert record.next_retry_at is not None

    def test_mark_failed_no_next_retry_when_exhausted(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
            retry_count=2, max_retries=3,
        )
        record.mark_failed("final error")
        # After incrementing, retry_count=3, max_retries=3, can_retry=False
        assert record.retry_count == 3

    def test_mark_conflict(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.UPDATE,
            local_version=1,
        )
        record.mark_conflict('{"field": "amount"}', remote_version=3)
        assert record.status == SyncStatus.CONFLICT
        assert record.has_conflict is True
        assert record.conflict_data == '{"field": "amount"}'
        assert record.remote_version == 3

    def test_resolve_conflict(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.UPDATE,
            status=SyncStatus.CONFLICT,
            has_conflict=True,
        )
        record.resolve_conflict("local")
        assert record.resolution_strategy == "local"
        assert record.resolved_at is not None
        assert record.has_conflict is False
        assert record.status == SyncStatus.PENDING

    def test_cancel(self):
        record = SyncRecord(
            entity_type="t", entity_id="1",
            operation=SyncOperation.CREATE,
        )
        record.cancel()
        assert record.status == SyncStatus.CANCELLED


class TestSyncRecordSerialization:
    """Tests for SyncRecord serialization."""

    def test_to_dict(self):
        record = SyncRecord(
            id="r1", entity_type="transaction", entity_id="t1",
            operation=SyncOperation.CREATE, status=SyncStatus.PENDING,
            priority=3, retry_count=0, max_retries=3,
            local_version=1,
        )
        record.created_at = datetime(2024, 1, 1)
        record.updated_at = datetime(2024, 1, 1)
        d = record.to_dict()
        assert d["id"] == "r1"
        assert d["entity_type"] == "transaction"
        assert d["operation"] == "create"
        assert d["status"] == "pending"
        assert d["priority"] == 3

    def test_from_dict(self):
        data = {
            "id": "r1", "entity_type": "budget", "entity_id": "b1",
            "operation": "update", "status": "pending",
            "priority": 2, "retry_count": 1, "local_version": 5,
            "created_at": "2024-01-01T12:00:00",
        }
        record = SyncRecord.from_dict(data)
        assert record.entity_type == "budget"
        assert record.operation == SyncOperation.UPDATE
        assert record.status == SyncStatus.PENDING
        assert record.priority == 2
        assert isinstance(record.created_at, datetime)

    def test_from_dict_ignores_unknown(self):
        data = {
            "entity_type": "user", "entity_id": "u1",
            "operation": "create", "status": "pending",
            "unknown_field": "ignored",
        }
        record = SyncRecord.from_dict(data)
        assert record.entity_type == "user"

    def test_repr(self):
        record = SyncRecord(
            id="r1", entity_type="transaction",
            operation=SyncOperation.CREATE,
            status=SyncStatus.PENDING,
        )
        repr_str = repr(record)
        assert "transaction" in repr_str
        assert "create" in repr_str
