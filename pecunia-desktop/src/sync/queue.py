"""
Sync operation queue for managing pending sync operations.

Provides a persistent queue with priority support, retry logic with exponential
backoff, and batch processing capabilities for offline-first synchronization.
Persists to database for crash recovery.
"""

import heapq
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Any, Callable
from enum import IntEnum

logger = logging.getLogger(__name__)


class OperationType(IntEnum):
    """Sync operation types with priority (lower number = higher priority)."""
    DELETE = 1      # Highest priority - deletions should propagate quickly
    UPDATE = 2      # Medium-high priority - updates are important
    CREATE = 3      # Medium priority - new items
    SYNC = 4        # Lower priority - general sync operations
    BULK = 5        # Lowest priority - bulk operations


class OperationStatus(IntEnum):
    """Status of a sync operation."""
    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
    RETRYING = 4


class OperationPriority(IntEnum):
    """Priority levels for sync operations."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 5
    LOW = 8
    BACKGROUND = 10


@dataclass
class SyncOperation:
    """
    Represents a single sync operation to be processed.

    Attributes:
        type: The type of operation (CREATE, UPDATE, DELETE, etc.)
        entity_type: The type of entity being synced (e.g., 'account', 'transaction')
        entity_id: The unique identifier of the entity
        data: The data payload for the operation
        created_at: Timestamp when the operation was created
        id: Unique database identifier (assigned on persistence)
        status: Current status of the operation
        retry_count: Number of retry attempts made
        last_error: Last error message if operation failed
        next_retry_at: Timestamp for next retry attempt
        priority: Priority level for the operation
    """
    type: OperationType
    entity_type: str
    entity_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None
    status: OperationStatus = OperationStatus.PENDING
    retry_count: int = 0
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    priority: int = field(default=OperationPriority.NORMAL)

    @property
    def key(self) -> str:
        """Get a unique key for this operation."""
        return f"{self.entity_type}:{self.entity_id}:{self.type.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to a dictionary for serialization."""
        return {
            'id': self.id,
            'type': int(self.type),
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'status': int(self.status),
            'retry_count': self.retry_count,
            'last_error': self.last_error,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'priority': self.priority
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncOperation':
        """Create a SyncOperation from a dictionary."""
        return cls(
            id=data.get('id'),
            type=OperationType(data['type']),
            entity_type=data['entity_type'],
            entity_id=data['entity_id'],
            data=data.get('data', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            status=OperationStatus(data.get('status', 0)),
            retry_count=data.get('retry_count', 0),
            last_error=data.get('last_error'),
            next_retry_at=datetime.fromisoformat(data['next_retry_at']) if data.get('next_retry_at') else None,
            priority=data.get('priority', OperationPriority.NORMAL)
        )

    def __lt__(self, other: 'SyncOperation') -> bool:
        """Compare operations for priority queue ordering."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at

    def __hash__(self) -> int:
        return hash(self.key)


@dataclass(order=True)
class QueuedOperation:
    """
    Represents a queued sync operation (legacy compatibility).

    Attributes are ordered for priority queue comparison:
    priority -> created_at -> entity_type -> operation
    """
    # Comparison fields (in order)
    priority: int = field(default=OperationPriority.NORMAL, compare=True)
    created_at: datetime = field(default_factory=datetime.utcnow, compare=True)

    # Non-comparison fields
    entity_type: str = field(default="", compare=False)
    entity_id: str = field(default="", compare=False)
    operation: OperationType = field(default=OperationType.UPDATE, compare=False)
    payload: Optional[str] = field(default=None, compare=False)
    record_id: Optional[str] = field(default=None, compare=False)
    metadata: Dict = field(default_factory=dict, compare=False)

    @property
    def key(self) -> str:
        """Get a unique key for this operation."""
        return f"{self.entity_type}:{self.entity_id}:{self.operation.name}"

    def __hash__(self) -> int:
        return hash(self.key)


class SyncQueue:
    """
    Thread-safe priority queue for sync operations with database persistence.

    Features:
    - Priority-based ordering
    - Deduplication of pending operations
    - Database persistence for crash recovery
    - Retry logic with exponential backoff
    - Batch retrieval for efficient processing
    - Statistics tracking
    """

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type INTEGER NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status INTEGER NOT NULL DEFAULT 0,
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            next_retry_at TEXT,
            priority INTEGER NOT NULL DEFAULT 5,
            UNIQUE(type, entity_type, entity_id)
        )
    """

    CREATE_INDEX_SQL = """
        CREATE INDEX IF NOT EXISTS idx_sync_queue_status_priority
        ON sync_queue(status, priority, created_at)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_retries: int = 5,
        base_backoff: float = 1.0,
        max_backoff: float = 300.0
    ):
        """
        Initialize the sync queue.

        Args:
            db_path: Path to SQLite database for persistence (None for in-memory only)
            max_retries: Maximum retry attempts before marking operation as failed
            base_backoff: Base backoff time in seconds (default: 1.0)
            max_backoff: Maximum backoff time in seconds (default: 300.0 = 5 minutes)
        """
        self.db_path = db_path
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff

        # In-memory heap for fast access
        self._heap: List[SyncOperation] = []
        self._pending_keys: Set[str] = set()
        self._lock = threading.RLock()

        # Statistics
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_deduplicated = 0
        self._total_retried = 0
        self._total_failed = 0

        # Initialize database if path provided
        if self.db_path:
            self._init_database()
            self._load_from_database()

        logger.debug("SyncQueue initialized")

    def _init_database(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.execute(self.CREATE_TABLE_SQL)
            conn.execute(self.CREATE_INDEX_SQL)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _load_from_database(self) -> None:
        """Load pending operations from database on startup (crash recovery)."""
        with self._lock:
            with self._get_connection() as conn:
                # Reset any in-progress operations to pending (crash recovery)
                conn.execute(
                    "UPDATE sync_queue SET status = ? WHERE status = ?",
                    (int(OperationStatus.PENDING), int(OperationStatus.IN_PROGRESS))
                )
                conn.commit()

                # Load all pending and retrying operations
                rows = conn.execute(
                    """
                    SELECT * FROM sync_queue
                    WHERE status IN (?, ?)
                    ORDER BY priority ASC, created_at ASC
                    """,
                    (int(OperationStatus.PENDING), int(OperationStatus.RETRYING))
                ).fetchall()

                for row in rows:
                    operation = self._row_to_operation(row)
                    heapq.heappush(self._heap, operation)
                    self._pending_keys.add(operation.key)

                if rows:
                    logger.info(f"Recovered {len(rows)} pending operations from database")

    def _row_to_operation(self, row: sqlite3.Row) -> SyncOperation:
        """Convert a database row to a SyncOperation."""
        return SyncOperation(
            id=row['id'],
            type=OperationType(row['type']),
            entity_type=row['entity_type'],
            entity_id=row['entity_id'],
            data=json.loads(row['data']),
            created_at=datetime.fromisoformat(row['created_at']),
            status=OperationStatus(row['status']),
            retry_count=row['retry_count'],
            last_error=row['last_error'],
            next_retry_at=datetime.fromisoformat(row['next_retry_at']) if row['next_retry_at'] else None,
            priority=row['priority']
        )

    def _persist_operation(self, operation: SyncOperation) -> SyncOperation:
        """Persist an operation to the database."""
        if not self.db_path:
            return operation

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sync_queue
                (type, entity_type, entity_id, data, created_at, status, retry_count,
                 last_error, next_retry_at, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(type, entity_type, entity_id) DO UPDATE SET
                    data = excluded.data,
                    created_at = excluded.created_at,
                    status = excluded.status,
                    retry_count = excluded.retry_count,
                    last_error = excluded.last_error,
                    next_retry_at = excluded.next_retry_at,
                    priority = excluded.priority
                """,
                (
                    int(operation.type),
                    operation.entity_type,
                    operation.entity_id,
                    json.dumps(operation.data),
                    operation.created_at.isoformat(),
                    int(operation.status),
                    operation.retry_count,
                    operation.last_error,
                    operation.next_retry_at.isoformat() if operation.next_retry_at else None,
                    operation.priority
                )
            )
            conn.commit()
            operation.id = cursor.lastrowid
        return operation

    def _update_operation_in_db(self, operation: SyncOperation) -> None:
        """Update an operation in the database."""
        if not self.db_path or operation.id is None:
            return

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sync_queue SET
                    status = ?,
                    retry_count = ?,
                    last_error = ?,
                    next_retry_at = ?
                WHERE id = ?
                """,
                (
                    int(operation.status),
                    operation.retry_count,
                    operation.last_error,
                    operation.next_retry_at.isoformat() if operation.next_retry_at else None,
                    operation.id
                )
            )
            conn.commit()

    def _remove_from_db(self, operation: SyncOperation) -> None:
        """Remove an operation from the database."""
        if not self.db_path or operation.id is None:
            return

        with self._get_connection() as conn:
            conn.execute("DELETE FROM sync_queue WHERE id = ?", (operation.id,))
            conn.commit()

    @property
    def size(self) -> int:
        """Get the current queue size."""
        with self._lock:
            return len(self._heap)

    @property
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        with self._lock:
            return len(self._heap) == 0

    def add(self, operation: SyncOperation, deduplicate: bool = True) -> bool:
        """
        Add an operation to the queue.

        Args:
            operation: The sync operation to add.
            deduplicate: Whether to skip if a similar operation is pending.

        Returns:
            True if the operation was added, False if deduplicated.
        """
        with self._lock:
            key = operation.key

            if deduplicate and key in self._pending_keys:
                self._total_deduplicated += 1
                logger.debug(f"Deduplicated operation: {key}")
                return False

            # Persist to database first for crash recovery
            operation = self._persist_operation(operation)

            heapq.heappush(self._heap, operation)
            self._pending_keys.add(key)
            self._total_enqueued += 1

            logger.debug(
                f"Added operation: {key} (priority={operation.priority}, "
                f"queue_size={len(self._heap)})"
            )
            return True

    def enqueue(self, operation: QueuedOperation, deduplicate: bool = True) -> bool:
        """
        Add a QueuedOperation to the queue (legacy compatibility).

        Args:
            operation: The operation to queue.
            deduplicate: Whether to skip if a similar operation is pending.

        Returns:
            True if the operation was added, False if deduplicated.
        """
        sync_op = SyncOperation(
            type=operation.operation if isinstance(operation.operation, OperationType)
                 else OperationType.UPDATE,
            entity_type=operation.entity_type,
            entity_id=operation.entity_id,
            data={'payload': operation.payload, 'record_id': operation.record_id, **operation.metadata},
            created_at=operation.created_at,
            priority=operation.priority
        )
        return self.add(sync_op, deduplicate)

    def get_next(self) -> Optional[SyncOperation]:
        """
        Get the next operation to process based on priority.

        Returns pending operations first, then retrying operations that are ready.

        Returns:
            The next operation to process, or None if queue is empty.
        """
        with self._lock:
            now = datetime.utcnow()

            # Find the first operation that is ready to process
            temp_heap = []
            result = None

            while self._heap:
                operation = heapq.heappop(self._heap)

                # Skip operations that are not ready for retry yet
                if operation.status == OperationStatus.RETRYING:
                    if operation.next_retry_at and operation.next_retry_at > now:
                        temp_heap.append(operation)
                        continue

                result = operation
                break

            # Put back operations we skipped
            for op in temp_heap:
                heapq.heappush(self._heap, op)

            if result:
                self._pending_keys.discard(result.key)
                self._total_dequeued += 1
                logger.debug(f"Retrieved operation: {result.key}")

            return result

    def dequeue(self) -> Optional[SyncOperation]:
        """
        Remove and return the highest priority operation.

        Returns:
            The next operation, or None if queue is empty.
        """
        return self.get_next()

    def peek(self) -> Optional[SyncOperation]:
        """
        Return the highest priority operation without removing it.

        Returns:
            The next operation, or None if queue is empty.
        """
        with self._lock:
            return self._heap[0] if self._heap else None

    def mark_in_progress(self, operation: SyncOperation) -> None:
        """
        Mark an operation as in progress.

        Args:
            operation: The operation to mark.
        """
        operation.status = OperationStatus.IN_PROGRESS
        self._update_operation_in_db(operation)
        logger.debug(f"Marked in-progress: {operation.key}")

    def mark_completed(self, operation: SyncOperation) -> None:
        """
        Mark an operation as completed and remove it from storage.

        Args:
            operation: The operation to mark as completed.
        """
        operation.status = OperationStatus.COMPLETED
        self._remove_from_db(operation)
        logger.info(f"Completed operation: {operation.key}")

    def mark_failed(self, operation: SyncOperation, error: str) -> bool:
        """
        Mark an operation as failed and schedule retry if possible.

        Uses exponential backoff to calculate the next retry time.
        If max retries exceeded, marks the operation as permanently failed.

        Args:
            operation: The operation that failed.
            error: Error message describing the failure.

        Returns:
            True if operation will be retried, False if max retries exceeded.
        """
        operation.retry_count += 1
        operation.last_error = error

        if operation.retry_count >= self.max_retries:
            operation.status = OperationStatus.FAILED
            self._total_failed += 1
            self._update_operation_in_db(operation)
            logger.error(
                f"Operation permanently failed after {operation.retry_count} retries: "
                f"{operation.key} - {error}"
            )
            return False

        # Calculate exponential backoff
        backoff = min(
            self.base_backoff * (2 ** (operation.retry_count - 1)),
            self.max_backoff
        )
        operation.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)
        operation.status = OperationStatus.RETRYING
        self._total_retried += 1

        # Re-add to heap for retry
        with self._lock:
            heapq.heappush(self._heap, operation)
            self._pending_keys.add(operation.key)

        self._update_operation_in_db(operation)
        logger.warning(
            f"Operation will retry in {backoff}s (attempt {operation.retry_count}/{self.max_retries}): "
            f"{operation.key} - {error}"
        )
        return True

    def remove_completed(self) -> int:
        """
        Remove all completed operations from the database.

        Returns:
            Number of operations removed.
        """
        if not self.db_path:
            return 0

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sync_queue WHERE status = ?",
                (int(OperationStatus.COMPLETED),)
            )
            conn.commit()
            count = cursor.rowcount
            if count > 0:
                logger.info(f"Removed {count} completed operations")
            return count

    def get_batch(self, max_size: int = 10) -> List[SyncOperation]:
        """
        Get a batch of operations for processing.

        Args:
            max_size: Maximum number of operations to return.

        Returns:
            List of operations (up to max_size).
        """
        batch = []
        for _ in range(max_size):
            operation = self.get_next()
            if operation is None:
                break
            batch.append(operation)

        if batch:
            logger.debug(f"Retrieved batch of {len(batch)} operations")
        return batch

    def process_queue(
        self,
        processor: Callable[[SyncOperation], bool],
        max_operations: Optional[int] = None
    ) -> tuple:
        """
        Process pending operations in the queue.

        Processes operations in priority order, calling the processor function
        for each operation. Handles success/failure and retry logic automatically.

        Args:
            processor: Function that processes an operation and returns True on success.
            max_operations: Maximum number of operations to process (None for unlimited).

        Returns:
            Tuple of (successful_count, failed_count).
        """
        successful = 0
        failed = 0
        processed = 0

        while max_operations is None or processed < max_operations:
            operation = self.get_next()
            if operation is None:
                break

            processed += 1
            self.mark_in_progress(operation)

            try:
                if processor(operation):
                    self.mark_completed(operation)
                    successful += 1
                else:
                    self.mark_failed(operation, "Processor returned False")
                    failed += 1
            except Exception as e:
                self.mark_failed(operation, str(e))
                failed += 1
                logger.exception(f"Error processing operation: {operation.key}")

        return successful, failed

    def remove(self, entity_type: str, entity_id: str) -> int:
        """
        Remove all operations for a specific entity.

        Args:
            entity_type: Type of entity.
            entity_id: ID of the entity.

        Returns:
            Number of operations removed.
        """
        with self._lock:
            original_size = len(self._heap)
            prefix = f"{entity_type}:{entity_id}:"

            # Find and remove matching operations
            removed_ops = [op for op in self._heap if op.key.startswith(prefix)]
            new_heap = [op for op in self._heap if not op.key.startswith(prefix)]

            # Remove from database
            for op in removed_ops:
                self._remove_from_db(op)

            # Rebuild heap
            heapq.heapify(new_heap)
            self._heap = new_heap
            self._pending_keys = {op.key for op in self._heap}

            removed = original_size - len(self._heap)
            if removed > 0:
                logger.debug(f"Removed {removed} operations for {entity_type}:{entity_id}")
            return removed

    def clear(self) -> int:
        """
        Clear all operations from the queue.

        Returns:
            Number of operations cleared.
        """
        with self._lock:
            count = len(self._heap)

            # Clear database
            if self.db_path:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM sync_queue")
                    conn.commit()

            self._heap.clear()
            self._pending_keys.clear()
            logger.info(f"Queue cleared: {count} operations removed")
            return count

    def contains(self, entity_type: str, entity_id: str) -> bool:
        """
        Check if the queue contains any operations for an entity.

        Args:
            entity_type: Type of entity.
            entity_id: ID of the entity.

        Returns:
            True if operations exist for the entity.
        """
        with self._lock:
            prefix = f"{entity_type}:{entity_id}:"
            return any(key.startswith(prefix) for key in self._pending_keys)

    def get_operations_for_entity(
        self,
        entity_type: str,
        entity_id: str
    ) -> List[SyncOperation]:
        """
        Get all pending operations for an entity.

        Args:
            entity_type: Type of entity.
            entity_id: ID of the entity.

        Returns:
            List of matching operations.
        """
        with self._lock:
            prefix = f"{entity_type}:{entity_id}:"
            return [op for op in self._heap if op.key.startswith(prefix)]

    def get_pending_count(self) -> int:
        """
        Get the number of pending operations in the queue.

        Returns:
            Count of pending and retrying operations.
        """
        with self._lock:
            return len([
                op for op in self._heap
                if op.status in (OperationStatus.PENDING, OperationStatus.RETRYING)
            ])

    def get_all_pending(self) -> List[SyncOperation]:
        """
        Get all pending operations in priority order.

        Returns:
            List of all pending and retrying operations.
        """
        with self._lock:
            pending = [
                op for op in self._heap
                if op.status in (OperationStatus.PENDING, OperationStatus.RETRYING)
            ]
            return sorted(pending)

    def reset_in_progress(self) -> int:
        """
        Reset all in-progress operations to pending status.

        This is useful for crash recovery to reprocess operations that were
        interrupted.

        Returns:
            Number of operations reset.
        """
        count = 0
        with self._lock:
            for op in self._heap:
                if op.status == OperationStatus.IN_PROGRESS:
                    op.status = OperationStatus.PENDING
                    self._update_operation_in_db(op)
                    count += 1

        if count > 0:
            logger.info(f"Reset {count} in-progress operations to pending")
        return count

    def update_priority(
        self,
        entity_type: str,
        entity_id: str,
        new_priority: int
    ) -> int:
        """
        Update priority for all operations of an entity.

        Args:
            entity_type: Type of entity.
            entity_id: ID of the entity.
            new_priority: New priority value.

        Returns:
            Number of operations updated.
        """
        with self._lock:
            prefix = f"{entity_type}:{entity_id}:"
            updated = 0

            for op in self._heap:
                if op.key.startswith(prefix):
                    op.priority = new_priority
                    updated += 1

            if updated > 0:
                # Rebuild heap with new priorities
                heapq.heapify(self._heap)
                logger.debug(
                    f"Updated priority to {new_priority} for {updated} "
                    f"operations of {entity_type}:{entity_id}"
                )
            return updated

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary containing queue statistics.
        """
        with self._lock:
            by_operation = {}
            by_entity_type = {}
            by_priority = {}
            by_status = {}

            for op in self._heap:
                op_type = op.type.name
                by_operation[op_type] = by_operation.get(op_type, 0) + 1
                by_entity_type[op.entity_type] = by_entity_type.get(op.entity_type, 0) + 1
                by_priority[op.priority] = by_priority.get(op.priority, 0) + 1
                status_name = op.status.name
                by_status[status_name] = by_status.get(status_name, 0) + 1

            return {
                "size": len(self._heap),
                "total_enqueued": self._total_enqueued,
                "total_dequeued": self._total_dequeued,
                "total_deduplicated": self._total_deduplicated,
                "total_retried": self._total_retried,
                "total_failed": self._total_failed,
                "by_operation": by_operation,
                "by_entity_type": by_entity_type,
                "by_priority": by_priority,
                "by_status": by_status
            }

    def __len__(self) -> int:
        """Return the queue size."""
        return self.size

    def __bool__(self) -> bool:
        """Return True if queue is not empty."""
        return not self.is_empty

    def __repr__(self) -> str:
        pending = self.get_pending_count()
        if self.db_path:
            return f"SyncQueue(db_path='{self.db_path}', pending={pending}, total={self.size})"
        return f"SyncQueue(size={self.size})"


class BatchQueue:
    """
    Queue that groups operations into batches by entity type.

    Useful for APIs that support batch operations.
    """

    def __init__(self, max_batch_size: int = 50):
        """
        Initialize the batch queue.

        Args:
            max_batch_size: Maximum operations per batch.
        """
        self._max_batch_size = max_batch_size
        self._batches: Dict[str, List[SyncOperation]] = {}
        self._lock = threading.RLock()

    def add(self, operation: SyncOperation) -> None:
        """Add an operation to the appropriate batch."""
        with self._lock:
            key = f"{operation.entity_type}:{operation.type.name}"
            if key not in self._batches:
                self._batches[key] = []
            self._batches[key].append(operation)

    def get_ready_batches(self) -> List[List[SyncOperation]]:
        """
        Get batches that are ready for processing.

        Returns:
            List of operation batches.
        """
        with self._lock:
            ready = []
            for key, operations in list(self._batches.items()):
                if len(operations) >= self._max_batch_size:
                    batch = operations[:self._max_batch_size]
                    self._batches[key] = operations[self._max_batch_size:]
                    ready.append(batch)
            return ready

    def flush_all(self) -> List[List[SyncOperation]]:
        """
        Flush all batches regardless of size.

        Returns:
            List of all operation batches.
        """
        with self._lock:
            all_batches = []
            for operations in self._batches.values():
                if operations:
                    all_batches.append(operations.copy())
            self._batches.clear()
            return all_batches

    def clear(self) -> None:
        """Clear all batches."""
        with self._lock:
            self._batches.clear()
