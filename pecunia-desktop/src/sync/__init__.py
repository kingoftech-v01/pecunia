"""
Sync module for Pecunia Desktop.

Provides offline-first data synchronization capabilities including
sync queue management and conflict resolution.
"""

from .manager import SyncManager, SyncState
from .queue import SyncQueue, QueuedOperation
from .conflict_resolver import ConflictResolver, ResolutionStrategy, ConflictType

__all__ = [
    "SyncManager",
    "SyncState",
    "SyncQueue",
    "QueuedOperation",
    "ConflictResolver",
    "ResolutionStrategy",
    "ConflictType",
]
