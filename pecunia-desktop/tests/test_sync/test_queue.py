"""Tests for src/sync/queue.py — SyncQueue, BatchQueue and related classes."""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from sync.queue import (
    OperationType, OperationStatus, OperationPriority,
    SyncOperation, QueuedOperation, SyncQueue, BatchQueue,
)


class TestOperationType:
    """Tests for OperationType enum."""

    def test_delete_highest_priority(self):
        assert OperationType.DELETE == 1

    def test_update_priority(self):
        assert OperationType.UPDATE == 2

    def test_create_priority(self):
        assert OperationType.CREATE == 3

    def test_sync_priority(self):
        assert OperationType.SYNC == 4

    def test_bulk_lowest_priority(self):
        assert OperationType.BULK == 5

    def test_ordering(self):
        assert OperationType.DELETE < OperationType.UPDATE < OperationType.CREATE


class TestOperationStatus:
    """Tests for OperationStatus enum."""

    def test_pending(self):
        assert OperationStatus.PENDING == 0

    def test_in_progress(self):
        assert OperationStatus.IN_PROGRESS == 1

    def test_completed(self):
        assert OperationStatus.COMPLETED == 2

    def test_failed(self):
        assert OperationStatus.FAILED == 3

    def test_retrying(self):
        assert OperationStatus.RETRYING == 4


class TestOperationPriority:
    """Tests for OperationPriority enum."""

    def test_critical(self):
        assert OperationPriority.CRITICAL == 1

    def test_high(self):
        assert OperationPriority.HIGH == 2

    def test_normal(self):
        assert OperationPriority.NORMAL == 5

    def test_low(self):
        assert OperationPriority.LOW == 8

    def test_background(self):
        assert OperationPriority.BACKGROUND == 10


class TestSyncOperation:
    """Tests for SyncOperation dataclass."""

    def test_creation(self):
        op = SyncOperation(
            type=OperationType.CREATE,
            entity_type="transaction",
            entity_id="t1",
            data={"amount": 100},
        )
        assert op.type == OperationType.CREATE
        assert op.entity_type == "transaction"
        assert op.entity_id == "t1"
        assert op.data == {"amount": 100}

    def test_default_values(self):
        op = SyncOperation(
            type=OperationType.UPDATE,
            entity_type="budget",
            entity_id="b1",
        )
        assert op.status == OperationStatus.PENDING
        assert op.retry_count == 0
        assert op.last_error is None
        assert op.next_retry_at is None
        assert op.id is None
        assert op.priority == OperationPriority.NORMAL

    def test_key_property(self):
        op = SyncOperation(
            type=OperationType.DELETE,
            entity_type="transaction",
            entity_id="t1",
        )
        assert op.key == "transaction:t1:DELETE"

    def test_to_dict(self):
        op = SyncOperation(
            type=OperationType.CREATE,
            entity_type="account",
            entity_id="a1",
            data={"name": "Checking"},
        )
        d = op.to_dict()
        assert d["type"] == int(OperationType.CREATE)
        assert d["entity_type"] == "account"
        assert d["entity_id"] == "a1"
        assert d["data"] == {"name": "Checking"}
        assert d["status"] == int(OperationStatus.PENDING)

    def test_from_dict(self):
        data = {
            "type": 3,
            "entity_type": "transaction",
            "entity_id": "t1",
            "data": {"amount": 50},
            "created_at": "2024-01-01T12:00:00",
            "status": 0,
            "retry_count": 2,
            "priority": 5,
        }
        op = SyncOperation.from_dict(data)
        assert op.type == OperationType.CREATE
        assert op.entity_type == "transaction"
        assert op.retry_count == 2
        assert isinstance(op.created_at, datetime)

    def test_lt_by_priority(self):
        op1 = SyncOperation(type=OperationType.DELETE, entity_type="t", entity_id="1", priority=1)
        op2 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="2", priority=5)
        assert op1 < op2

    def test_lt_by_created_at(self):
        t1 = datetime(2024, 1, 1)
        t2 = datetime(2024, 1, 2)
        op1 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1", priority=5, created_at=t1)
        op2 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="2", priority=5, created_at=t2)
        assert op1 < op2

    def test_hash(self):
        op1 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        op2 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        assert hash(op1) == hash(op2)


class TestQueuedOperation:
    """Tests for QueuedOperation dataclass."""

    def test_creation(self):
        op = QueuedOperation(
            entity_type="transaction",
            entity_id="t1",
            operation=OperationType.UPDATE,
            payload='{"amount": 100}',
        )
        assert op.entity_type == "transaction"
        assert op.entity_id == "t1"

    def test_key_property(self):
        op = QueuedOperation(
            entity_type="budget",
            entity_id="b1",
            operation=OperationType.CREATE,
        )
        assert op.key == "budget:b1:CREATE"

    def test_ordering_by_priority(self):
        op1 = QueuedOperation(priority=1, entity_type="a", entity_id="1")
        op2 = QueuedOperation(priority=5, entity_type="b", entity_id="2")
        assert op1 < op2

    def test_hash(self):
        op = QueuedOperation(entity_type="t", entity_id="1", operation=OperationType.DELETE)
        assert isinstance(hash(op), int)


class TestSyncQueueInMemory:
    """Tests for SyncQueue in-memory operations (no persistence)."""

    def test_empty_queue(self):
        q = SyncQueue()
        assert q.size == 0
        assert q.is_empty is True
        assert len(q) == 0
        assert bool(q) is False

    def test_add_operation(self):
        q = SyncQueue()
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        result = q.add(op)
        assert result is True
        assert q.size == 1
        assert q.is_empty is False
        assert bool(q) is True

    def test_add_deduplicate(self):
        q = SyncQueue()
        op1 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        op2 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.add(op1)
        result = q.add(op2)
        assert result is False
        assert q.size == 1

    def test_add_no_deduplicate(self):
        q = SyncQueue()
        op1 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        op2 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.add(op1)
        result = q.add(op2, deduplicate=False)
        assert result is True
        assert q.size == 2

    def test_get_next(self):
        q = SyncQueue()
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.add(op)
        result = q.get_next()
        assert result is not None
        assert result.entity_id == "1"
        assert q.size == 0

    def test_get_next_empty(self):
        q = SyncQueue()
        assert q.get_next() is None

    def test_dequeue_alias(self):
        q = SyncQueue()
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.add(op)
        result = q.dequeue()
        assert result is not None
        assert result.entity_id == "1"

    def test_peek(self):
        q = SyncQueue()
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.add(op)
        result = q.peek()
        assert result is not None
        assert q.size == 1  # Not removed

    def test_peek_empty(self):
        q = SyncQueue()
        assert q.peek() is None

    def test_priority_ordering(self):
        q = SyncQueue()
        op_low = SyncOperation(type=OperationType.BULK, entity_type="t", entity_id="1", priority=10)
        op_high = SyncOperation(type=OperationType.DELETE, entity_type="t", entity_id="2", priority=1)
        q.add(op_low)
        q.add(op_high)
        first = q.get_next()
        assert first.entity_id == "2"  # Higher priority (lower number)

    def test_enqueue_queued_operation(self):
        q = SyncQueue()
        op = QueuedOperation(
            entity_type="transaction",
            entity_id="t1",
            operation=OperationType.UPDATE,
            payload='{"amount": 100}',
        )
        result = q.enqueue(op)
        assert result is True
        assert q.size == 1


class TestSyncQueueStatusOperations:
    """Tests for SyncQueue status management."""

    def test_mark_in_progress(self):
        q = SyncQueue()
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.mark_in_progress(op)
        assert op.status == OperationStatus.IN_PROGRESS

    def test_mark_completed(self):
        q = SyncQueue()
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.mark_completed(op)
        assert op.status == OperationStatus.COMPLETED

    def test_mark_failed_retry(self):
        q = SyncQueue(max_retries=5)
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        result = q.mark_failed(op, "Network error")
        assert result is True
        assert op.retry_count == 1
        assert op.status == OperationStatus.RETRYING
        assert op.last_error == "Network error"
        assert op.next_retry_at is not None

    def test_mark_failed_max_retries(self):
        q = SyncQueue(max_retries=2)
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1", retry_count=1)
        result = q.mark_failed(op, "Error")
        assert result is False
        assert op.status == OperationStatus.FAILED

    def test_exponential_backoff(self):
        q = SyncQueue(max_retries=5, base_backoff=1.0, max_backoff=300.0)
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        q.mark_failed(op, "err")
        first_retry = op.next_retry_at

        op2 = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="2", retry_count=2)
        q.mark_failed(op2, "err")
        # 3rd retry should have a longer backoff than 1st retry
        assert op2.next_retry_at > first_retry


class TestSyncQueueBatchAndSearch:
    """Tests for SyncQueue batch and search operations."""

    def test_get_batch(self):
        q = SyncQueue()
        for i in range(5):
            q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id=str(i)))
        batch = q.get_batch(3)
        assert len(batch) == 3
        assert q.size == 2

    def test_get_batch_smaller_than_queue(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        batch = q.get_batch(5)
        assert len(batch) == 1

    def test_process_queue(self):
        q = SyncQueue()
        for i in range(3):
            q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id=str(i)))
        processor = MagicMock(return_value=True)
        success, failed = q.process_queue(processor)
        assert success == 3
        assert failed == 0

    def test_process_queue_with_failure(self):
        q = SyncQueue(max_retries=1)
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        processor = MagicMock(return_value=False)
        success, failed = q.process_queue(processor)
        assert success == 0
        assert failed == 1

    def test_process_queue_with_exception(self):
        q = SyncQueue(max_retries=1)
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        processor = MagicMock(side_effect=RuntimeError("oops"))
        success, failed = q.process_queue(processor)
        assert success == 0
        assert failed == 1

    def test_process_queue_with_limit(self):
        q = SyncQueue()
        for i in range(5):
            q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id=str(i)))
        processor = MagicMock(return_value=True)
        success, failed = q.process_queue(processor, max_operations=2)
        assert success == 2

    def test_remove_entity(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        q.add(SyncOperation(type=OperationType.UPDATE, entity_type="t", entity_id="1"))
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="2"))
        removed = q.remove("t", "1")
        assert removed == 2
        assert q.size == 1

    def test_contains(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        assert q.contains("t", "1") is True
        assert q.contains("t", "2") is False

    def test_get_operations_for_entity(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="2"))
        ops = q.get_operations_for_entity("t", "1")
        assert len(ops) == 1

    def test_clear(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="2"))
        count = q.clear()
        assert count == 2
        assert q.size == 0


class TestSyncQueueStatistics:
    """Tests for SyncQueue statistics."""

    def test_get_statistics(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        q.add(SyncOperation(type=OperationType.DELETE, entity_type="b", entity_id="2"))
        stats = q.get_statistics()
        assert stats["size"] == 2
        assert stats["total_enqueued"] == 2
        assert "by_operation" in stats
        assert "by_entity_type" in stats

    def test_get_pending_count(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        assert q.get_pending_count() == 1

    def test_get_all_pending(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1", priority=5))
        q.add(SyncOperation(type=OperationType.DELETE, entity_type="t", entity_id="2", priority=1))
        pending = q.get_all_pending()
        assert len(pending) == 2
        assert pending[0].priority <= pending[1].priority

    def test_repr_in_memory(self):
        q = SyncQueue()
        assert "SyncQueue" in repr(q)

    def test_update_priority(self):
        q = SyncQueue()
        q.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1", priority=5))
        count = q.update_priority("t", "1", 1)
        assert count == 1


class TestSyncQueueWithPersistence:
    """Tests for SyncQueue with database persistence."""

    def test_init_with_db(self, tmp_path):
        db_path = str(tmp_path / "queue.db")
        q = SyncQueue(db_path=db_path)
        assert q.db_path == db_path
        assert q.size == 0

    def test_persist_and_recover(self, tmp_path):
        db_path = str(tmp_path / "queue.db")
        q1 = SyncQueue(db_path=db_path)
        q1.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1", data={"x": 1}))
        assert q1.size == 1

        # Simulate restart by creating a new queue with same db
        q2 = SyncQueue(db_path=db_path)
        assert q2.size == 1

    def test_remove_completed_from_db(self, tmp_path):
        db_path = str(tmp_path / "queue.db")
        q = SyncQueue(db_path=db_path)
        count = q.remove_completed()
        assert count == 0

    def test_repr_with_db(self, tmp_path):
        db_path = str(tmp_path / "queue.db")
        q = SyncQueue(db_path=db_path)
        assert db_path in repr(q)


class TestBatchQueue:
    """Tests for BatchQueue class."""

    def test_creation(self):
        bq = BatchQueue(max_batch_size=10)
        assert bq._max_batch_size == 10

    def test_add(self):
        bq = BatchQueue(max_batch_size=10)
        op = SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1")
        bq.add(op)
        assert len(bq._batches) == 1

    def test_get_ready_batches_not_ready(self):
        bq = BatchQueue(max_batch_size=5)
        bq.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        batches = bq.get_ready_batches()
        assert len(batches) == 0

    def test_get_ready_batches_ready(self):
        bq = BatchQueue(max_batch_size=2)
        bq.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        bq.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="2"))
        batches = bq.get_ready_batches()
        assert len(batches) == 1
        assert len(batches[0]) == 2

    def test_flush_all(self):
        bq = BatchQueue(max_batch_size=10)
        bq.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        bq.add(SyncOperation(type=OperationType.DELETE, entity_type="b", entity_id="2"))
        batches = bq.flush_all()
        assert len(batches) == 2  # Two different batch keys

    def test_clear(self):
        bq = BatchQueue(max_batch_size=10)
        bq.add(SyncOperation(type=OperationType.CREATE, entity_type="t", entity_id="1"))
        bq.clear()
        assert len(bq._batches) == 0
