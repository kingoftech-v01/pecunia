"""
Sync tracking model for the Pecunia Desktop application.

Provides sync state management for offline-first architecture.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, Integer, Index, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped

from . import Base


class SyncStatus(str, Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    CANCELLED = "cancelled"


class SyncOperation(str, Enum):
    """Type of sync operation."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    FULL_SYNC = "full_sync"


class SyncRecord(Base):
    """
    Sync record model for tracking synchronization state.

    Tracks individual sync operations and their status for
    offline-first data synchronization.
    """

    __tablename__ = "sync_records"

    # Primary key
    id: Mapped[str] = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Entity information
    entity_type: Mapped[str] = Column(String(50), nullable=False)  # 'user', 'transaction', 'budget'
    entity_id: Mapped[str] = Column(String(36), nullable=False)

    # Operation details
    operation: Mapped[SyncOperation] = Column(
        SQLEnum(SyncOperation),
        nullable=False
    )
    status: Mapped[SyncStatus] = Column(
        SQLEnum(SyncStatus),
        nullable=False,
        default=SyncStatus.PENDING
    )

    # Priority (lower = higher priority)
    priority: Mapped[int] = Column(Integer, default=5, nullable=False)

    # Retry tracking
    retry_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = Column(Integer, default=3, nullable=False)
    last_retry_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Payload - serialized data to sync (JSON string)
    payload: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Remote response data (JSON string)
    response_data: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Error information
    error_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = Column(String(50), nullable=True)

    # Conflict resolution
    has_conflict: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    conflict_data: Mapped[Optional[str]] = Column(Text, nullable=True)  # JSON string
    resolution_strategy: Mapped[Optional[str]] = Column(String(50), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Version tracking for conflict detection
    local_version: Mapped[int] = Column(Integer, default=0, nullable=False)
    remote_version: Mapped[Optional[int]] = Column(Integer, nullable=True)

    # Batch processing
    batch_id: Mapped[Optional[str]] = Column(String(36), nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('ix_sync_entity', 'entity_type', 'entity_id'),
        Index('ix_sync_status', 'status', 'priority'),
        Index('ix_sync_pending', 'status', 'next_retry_at'),
        Index('ix_sync_conflicts', 'has_conflict', 'status'),
        Index('ix_sync_batch', 'batch_id', 'status'),
    )

    def __repr__(self) -> str:
        return (
            f"<SyncRecord(id={self.id}, entity_type={self.entity_type}, "
            f"operation={self.operation.value}, status={self.status.value})>"
        )

    @property
    def can_retry(self) -> bool:
        """Check if the operation can be retried."""
        return self.retry_count < self.max_retries and self.status == SyncStatus.FAILED

    @property
    def is_terminal(self) -> bool:
        """Check if the sync is in a terminal state."""
        return self.status in (SyncStatus.COMPLETED, SyncStatus.CANCELLED)

    @property
    def needs_resolution(self) -> bool:
        """Check if the record needs conflict resolution."""
        return self.has_conflict and self.status == SyncStatus.CONFLICT

    def mark_pending(self) -> None:
        """Mark the sync record as pending."""
        self.status = SyncStatus.PENDING
        self.updated_at = datetime.utcnow()

    def mark_in_progress(self) -> None:
        """Mark the sync record as in progress."""
        self.status = SyncStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_completed(self, response_data: Optional[str] = None) -> None:
        """
        Mark the sync record as completed.

        Args:
            response_data: Optional JSON response from server.
        """
        self.status = SyncStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if response_data:
            self.response_data = response_data

    def mark_failed(self, error_message: str, error_code: Optional[str] = None) -> None:
        """
        Mark the sync record as failed.

        Args:
            error_message: Description of the error.
            error_code: Optional error code.
        """
        self.status = SyncStatus.FAILED
        self.error_message = error_message
        self.error_code = error_code
        self.retry_count += 1
        self.last_retry_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Calculate next retry time with exponential backoff
        if self.can_retry:
            from datetime import timedelta
            backoff_seconds = min(300, 2 ** self.retry_count * 10)  # Max 5 minutes
            self.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)

    def mark_conflict(
        self,
        conflict_data: str,
        remote_version: Optional[int] = None
    ) -> None:
        """
        Mark the sync record as having a conflict.

        Args:
            conflict_data: JSON string describing the conflict.
            remote_version: Remote version that caused the conflict.
        """
        self.status = SyncStatus.CONFLICT
        self.has_conflict = True
        self.conflict_data = conflict_data
        if remote_version is not None:
            self.remote_version = remote_version
        self.updated_at = datetime.utcnow()

    def resolve_conflict(self, resolution_strategy: str) -> None:
        """
        Mark the conflict as resolved.

        Args:
            resolution_strategy: Strategy used to resolve ('local', 'remote', 'merge').
        """
        self.resolution_strategy = resolution_strategy
        self.resolved_at = datetime.utcnow()
        self.has_conflict = False
        self.status = SyncStatus.PENDING  # Re-queue for sync
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel the sync operation."""
        self.status = SyncStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert the sync record to a dictionary for serialization."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "operation": self.operation.value,
            "status": self.status.value,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "payload": self.payload,
            "response_data": self.response_data,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "has_conflict": self.has_conflict,
            "conflict_data": self.conflict_data,
            "resolution_strategy": self.resolution_strategy,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "local_version": self.local_version,
            "remote_version": self.remote_version,
            "batch_id": self.batch_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncRecord":
        """Create a SyncRecord instance from a dictionary."""
        record = cls()
        for key, value in data.items():
            if hasattr(record, key):
                if key == 'operation' and isinstance(value, str):
                    value = SyncOperation(value)
                elif key == 'status' and isinstance(value, str):
                    value = SyncStatus(value)
                elif key.endswith('_at') and value and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(record, key, value)
        return record

    @classmethod
    def create_for_entity(
        cls,
        entity_type: str,
        entity_id: str,
        operation: SyncOperation,
        payload: Optional[str] = None,
        priority: int = 5
    ) -> "SyncRecord":
        """
        Create a new sync record for an entity.

        Args:
            entity_type: Type of entity ('user', 'transaction', 'budget').
            entity_id: ID of the entity.
            operation: Type of sync operation.
            payload: Optional JSON payload.
            priority: Priority (lower = higher priority).

        Returns:
            A new SyncRecord instance.
        """
        return cls(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=payload,
            priority=priority,
            status=SyncStatus.PENDING
        )
