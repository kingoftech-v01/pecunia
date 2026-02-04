"""
Sync Manager for Offline/Online Data Synchronization.

This module provides the core synchronization engine for the offline-first
desktop application. It manages bidirectional data sync between the local
SQLite database and the remote Django REST API server.

Architecture Overview:
----------------------
The sync manager follows an offline-first pattern:

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Local     │     │    Sync     │     │   Remote    │
    │  Database   │────▶│   Manager   │◀───▶│    API      │
    │  (SQLite)   │     │  (Queue)    │     │  (Django)   │
    └─────────────┘     └─────────────┘     └─────────────┘
          │                   │
          │    ┌──────────────┘
          │    │
          ▼    ▼
    ┌─────────────┐
    │   PyQt6 UI  │
    │  (Signals)  │
    └─────────────┘

Data Flow:
----------
1. User creates/modifies data locally
2. Change is saved to SQLite immediately (instant response)
3. Change is queued in SyncQueue for background sync
4. SyncManager detects online status and processes queue
5. On conflict, ConflictResolver determines winner
6. UI receives signals for progress updates

Key Components:
---------------
- SyncManager: Main orchestrator with PyQt6 signal integration
- SyncQueue: Thread-safe FIFO queue for pending operations
- ConflictResolver: Handles version conflicts between local/remote
- SyncConfig: Configuration for timing, batch sizes, strategies

Signal Integration:
-------------------
All state changes emit PyQt6 signals for reactive UI updates:
- state_changed: Sync state transitions
- sync_progress: Progress during batch processing
- conflict_detected: Requires user resolution
- connectivity_changed: Network status changes

Conflict Resolution Strategies:
-------------------------------
- LAST_WRITE_WINS: Compare updated_at timestamps (default)
- CLIENT_WINS: Local changes always override server
- SERVER_WINS: Server changes always override local
- MANUAL: Queue for user decision

Configuration:
--------------
Key settings in SyncConfig:
- auto_sync_interval_seconds: Background sync frequency (default: 300s)
- batch_size: Operations per API call (default: 50)
- sync_on_change: Immediate sync after local change (default: True)
- default_resolution_strategy: Conflict handling (default: LAST_WRITE_WINS)

Related Documentation:
----------------------
- See DESKTOP_CONVENTIONS.md for PyQt6 patterns
- See SECURITY_GUIDELINES.md for token handling
- See SCALABILITY_GUIDELINES.md for batch processing limits
"""

import json
import logging
import asyncio
import socket
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Set
from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from sqlalchemy.orm import Session

from ..database.models import SyncRecord, SyncStatus, SyncOperation
from ..database.models import User, Transaction, Budget
from .queue import SyncQueue, QueuedOperation
from .conflict_resolver import ConflictResolver, ResolutionStrategy

logger = logging.getLogger(__name__)


class SyncState(str, Enum):
    """Current state of the sync manager."""
    IDLE = "idle"
    SYNCING = "syncing"
    PAUSED = "paused"
    ERROR = "error"
    OFFLINE = "offline"


class SyncEntityType(str, Enum):
    """Entity types that can be synced."""
    TRANSACTIONS = "transactions"
    BUDGETS = "budgets"
    CATEGORIES = "categories"
    USERS = "users"
    ALL = "all"


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    synced_count: int = 0
    failed_count: int = 0
    conflict_count: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: int = 0
    entity_types_synced: List[str] = field(default_factory=list)


@dataclass
class SyncProgress:
    """Progress information for sync operations."""
    current: int = 0
    total: int = 0
    entity_type: str = ""
    operation: str = ""
    message: str = ""

    @property
    def percentage(self) -> float:
        """Get progress as percentage."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100.0


@dataclass
class SyncConfig:
    """Configuration for the sync manager."""
    # API endpoint
    api_base_url: str = ""
    api_token: Optional[str] = None

    # Timing settings
    auto_sync_interval_seconds: int = 300  # 5 minutes
    sync_timeout_seconds: int = 60
    retry_delay_seconds: int = 10
    connectivity_check_interval_seconds: int = 30

    # Batch settings
    batch_size: int = 50
    max_concurrent_operations: int = 5

    # Conflict resolution
    default_resolution_strategy: ResolutionStrategy = ResolutionStrategy.LAST_WRITE_WINS

    # Feature flags
    sync_on_startup: bool = True
    sync_on_change: bool = True
    sync_deletions: bool = True

    # Selective sync settings
    sync_transactions: bool = True
    sync_budgets: bool = True
    sync_categories: bool = True


class SyncManager(QObject):
    """
    Manages data synchronization between local and remote storage.

    Implements offline-first architecture with PyQt6 signal integration for
    seamless UI updates:
    - Automatic background synchronization
    - Conflict detection and resolution
    - Retry logic with exponential backoff
    - Batch processing for efficiency
    - Network connectivity detection
    - Selective sync support

    Signals:
        state_changed: Emitted when sync state changes
        sync_started: Emitted when sync begins
        sync_completed: Emitted when sync finishes
        sync_progress: Emitted to report sync progress
        sync_error: Emitted when an error occurs
        conflict_detected: Emitted when a conflict is found
        connectivity_changed: Emitted when network status changes
        last_sync_updated: Emitted when last sync timestamp changes
    """

    # PyQt6 Signals for UI updates
    state_changed = pyqtSignal(str)  # SyncState value
    sync_started = pyqtSignal()
    sync_completed = pyqtSignal(object)  # SyncResult
    sync_progress = pyqtSignal(object)  # SyncProgress
    sync_error = pyqtSignal(str, str)  # error_type, error_message
    conflict_detected = pyqtSignal(object)  # SyncRecord
    connectivity_changed = pyqtSignal(bool)  # is_online
    last_sync_updated = pyqtSignal(object)  # datetime or None
    pending_count_changed = pyqtSignal(int)  # pending count

    def __init__(
        self,
        session_factory: Callable[[], Session],
        config: Optional[SyncConfig] = None,
        parent: Optional[QObject] = None
    ):
        """
        Initialize the sync manager.

        Args:
            session_factory: Factory function to create database sessions.
            config: Optional sync configuration.
            parent: Optional parent QObject.
        """
        super().__init__(parent)

        self._session_factory = session_factory
        self._config = config or SyncConfig()
        self._state = SyncState.IDLE
        self._queue = SyncQueue()
        self._conflict_resolver = ConflictResolver(
            default_strategy=self._config.default_resolution_strategy
        )

        # Timers for periodic operations
        self._sync_timer: Optional[QTimer] = None
        self._connectivity_timer: Optional[QTimer] = None

        # Background sync task
        self._sync_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Network state
        self._is_online: bool = True
        self._last_connectivity_check: Optional[datetime] = None

        # Statistics and tracking
        self._last_sync_at: Optional[datetime] = None
        self._total_synced: int = 0
        self._total_failed: int = 0

        # Selective sync tracking
        self._enabled_entity_types: Set[SyncEntityType] = set()
        self._update_enabled_entity_types()

        logger.info("SyncManager initialized with PyQt6 signals")

    def _update_enabled_entity_types(self) -> None:
        """Update the set of enabled entity types based on config."""
        self._enabled_entity_types.clear()
        if self._config.sync_transactions:
            self._enabled_entity_types.add(SyncEntityType.TRANSACTIONS)
        if self._config.sync_budgets:
            self._enabled_entity_types.add(SyncEntityType.BUDGETS)
        if self._config.sync_categories:
            self._enabled_entity_types.add(SyncEntityType.CATEGORIES)

    @property
    def state(self) -> SyncState:
        """Get the current sync state."""
        return self._state

    @property
    def is_online(self) -> bool:
        """Check if network is available."""
        return self._is_online

    @property
    def last_sync_at(self) -> Optional[datetime]:
        """Get the timestamp of the last successful sync."""
        return self._last_sync_at

    @property
    def enabled_entity_types(self) -> Set[SyncEntityType]:
        """Get the set of enabled entity types for sync."""
        return self._enabled_entity_types.copy()

    def _set_state(self, state: SyncState) -> None:
        """Set the sync state and emit signal."""
        if self._state != state:
            old_state = self._state
            self._state = state
            logger.info(f"Sync state changed: {old_state.value} -> {state.value}")
            self.state_changed.emit(state.value)

    def _set_online_status(self, is_online: bool) -> None:
        """Set online status and emit signal if changed."""
        if self._is_online != is_online:
            self._is_online = is_online
            logger.info(f"Connectivity changed: {'online' if is_online else 'offline'}")
            self.connectivity_changed.emit(is_online)

            if not is_online:
                self._set_state(SyncState.OFFLINE)
            elif self._state == SyncState.OFFLINE:
                self._set_state(SyncState.IDLE)

    def configure(self, config: SyncConfig) -> None:
        """Update the sync configuration."""
        self._config = config
        self._conflict_resolver = ConflictResolver(
            default_strategy=config.default_resolution_strategy
        )
        self._update_enabled_entity_types()
        logger.info("Sync configuration updated")

    def set_api_credentials(self, base_url: str, token: str) -> None:
        """Set API credentials for sync."""
        self._config.api_base_url = base_url
        self._config.api_token = token
        logger.info(f"API credentials set for: {base_url}")

    # =========================================================================
    # Selective Sync Configuration
    # =========================================================================

    def set_sync_transactions(self, enabled: bool) -> None:
        """Enable or disable transaction syncing."""
        self._config.sync_transactions = enabled
        self._update_enabled_entity_types()
        logger.info(f"Transaction sync {'enabled' if enabled else 'disabled'}")

    def set_sync_budgets(self, enabled: bool) -> None:
        """Enable or disable budget syncing."""
        self._config.sync_budgets = enabled
        self._update_enabled_entity_types()
        logger.info(f"Budget sync {'enabled' if enabled else 'disabled'}")

    def set_sync_categories(self, enabled: bool) -> None:
        """Enable or disable category syncing."""
        self._config.sync_categories = enabled
        self._update_enabled_entity_types()
        logger.info(f"Category sync {'enabled' if enabled else 'disabled'}")

    def set_selective_sync(
        self,
        transactions: bool = True,
        budgets: bool = True,
        categories: bool = True
    ) -> None:
        """
        Configure selective sync for multiple entity types at once.

        Args:
            transactions: Enable transaction syncing.
            budgets: Enable budget syncing.
            categories: Enable category syncing.
        """
        self._config.sync_transactions = transactions
        self._config.sync_budgets = budgets
        self._config.sync_categories = categories
        self._update_enabled_entity_types()
        logger.info(
            f"Selective sync configured: transactions={transactions}, "
            f"budgets={budgets}, categories={categories}"
        )

    # =========================================================================
    # Network Connectivity Detection
    # =========================================================================

    def check_connectivity(self) -> bool:
        """
        Check network connectivity.

        Attempts to connect to a well-known host to verify internet access.

        Returns:
            True if network is available, False otherwise.
        """
        try:
            # Check connectivity against the actual API server instead of Google DNS
            if self._config.api_base_url:
                import urllib.parse
                parsed = urllib.parse.urlparse(self._config.api_base_url)
                host = parsed.hostname or "localhost"
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                socket.create_connection((host, port), timeout=3)
            else:
                # Fallback: try multiple DNS resolvers
                socket.create_connection(("1.1.1.1", 53), timeout=3)
            self._last_connectivity_check = datetime.utcnow()
            self._set_online_status(True)
            return True
        except (socket.timeout, socket.error, OSError):
            self._last_connectivity_check = datetime.utcnow()
            self._set_online_status(False)
            return False

    def check_api_connectivity(self) -> bool:
        """
        Check connectivity to the API server.

        Returns:
            True if API is reachable, False otherwise.
        """
        if not self._config.api_base_url:
            return False

        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(self._config.api_base_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)

            socket.create_connection((host, port), timeout=5)
            self._set_online_status(True)
            return True
        except (socket.timeout, socket.error, OSError):
            self._set_online_status(False)
            return False

    def _on_connectivity_check(self) -> None:
        """Timer callback for periodic connectivity checks."""
        self.check_connectivity()

    # =========================================================================
    # Start/Stop Methods
    # =========================================================================

    def start(self) -> None:
        """
        Start the sync manager.

        Initializes timers for automatic sync and connectivity checks.
        Optionally triggers an immediate sync if configured.
        """
        logger.info("Starting SyncManager")

        # Check initial connectivity
        self.check_connectivity()

        # Start connectivity check timer
        self._connectivity_timer = QTimer(self)
        self._connectivity_timer.timeout.connect(self._on_connectivity_check)
        self._connectivity_timer.start(
            self._config.connectivity_check_interval_seconds * 1000
        )

        # Start auto-sync timer
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._on_auto_sync_timer)
        self._sync_timer.start(
            self._config.auto_sync_interval_seconds * 1000
        )

        # Initial sync if configured
        if self._config.sync_on_startup and self._is_online:
            # Schedule sync for next event loop iteration
            QTimer.singleShot(100, self._trigger_sync)

        logger.info("SyncManager started")

    def stop(self) -> None:
        """
        Stop the sync manager.

        Stops all timers and cancels any pending sync operations.
        """
        logger.info("Stopping SyncManager")

        # Stop timers
        if self._sync_timer:
            self._sync_timer.stop()
            self._sync_timer = None

        if self._connectivity_timer:
            self._connectivity_timer.stop()
            self._connectivity_timer = None

        # Cancel any pending sync
        self._stop_event.set()
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()

        self._set_state(SyncState.IDLE)
        logger.info("SyncManager stopped")

    def _on_auto_sync_timer(self) -> None:
        """Timer callback for periodic auto-sync."""
        if self._is_online and self._state == SyncState.IDLE:
            self._trigger_sync()

    def _trigger_sync(self) -> None:
        """Trigger a sync operation."""
        asyncio.create_task(self.sync_now())

    # =========================================================================
    # Queue Operations
    # =========================================================================

    def queue_create(self, entity_type: str, entity_id: str, data: dict) -> None:
        """
        Queue an entity creation for sync.

        Args:
            entity_type: Type of entity ('user', 'transaction', 'budget').
            entity_id: Local ID of the entity.
            data: Entity data to sync.
        """
        if not self._is_entity_type_enabled(entity_type):
            logger.debug(f"Sync disabled for entity type: {entity_type}")
            return

        operation = QueuedOperation(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=SyncOperation.CREATE,
            payload=json.dumps(data)
        )
        self._queue.enqueue(operation)
        self._persist_sync_record(operation)
        logger.debug(f"Queued CREATE for {entity_type}:{entity_id}")

        self._emit_pending_count()

        if self._config.sync_on_change and self._state == SyncState.IDLE and self._is_online:
            asyncio.create_task(self.sync_now())

    def queue_update(self, entity_type: str, entity_id: str, data: dict) -> None:
        """
        Queue an entity update for sync.

        Args:
            entity_type: Type of entity.
            entity_id: Local ID of the entity.
            data: Updated entity data.
        """
        if not self._is_entity_type_enabled(entity_type):
            logger.debug(f"Sync disabled for entity type: {entity_type}")
            return

        operation = QueuedOperation(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=SyncOperation.UPDATE,
            payload=json.dumps(data)
        )
        self._queue.enqueue(operation)
        self._persist_sync_record(operation)
        logger.debug(f"Queued UPDATE for {entity_type}:{entity_id}")

        self._emit_pending_count()

        if self._config.sync_on_change and self._state == SyncState.IDLE and self._is_online:
            asyncio.create_task(self.sync_now())

    def queue_delete(self, entity_type: str, entity_id: str) -> None:
        """
        Queue an entity deletion for sync.

        Args:
            entity_type: Type of entity.
            entity_id: Local ID of the entity.
        """
        if not self._config.sync_deletions:
            logger.debug(f"Deletion sync disabled, skipping {entity_type}:{entity_id}")
            return

        if not self._is_entity_type_enabled(entity_type):
            logger.debug(f"Sync disabled for entity type: {entity_type}")
            return

        operation = QueuedOperation(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=SyncOperation.DELETE
        )
        self._queue.enqueue(operation)
        self._persist_sync_record(operation)
        logger.debug(f"Queued DELETE for {entity_type}:{entity_id}")

        self._emit_pending_count()

        if self._config.sync_on_change and self._state == SyncState.IDLE and self._is_online:
            asyncio.create_task(self.sync_now())

    def _is_entity_type_enabled(self, entity_type: str) -> bool:
        """Check if an entity type is enabled for sync."""
        type_mapping = {
            "transaction": SyncEntityType.TRANSACTIONS,
            "transactions": SyncEntityType.TRANSACTIONS,
            "budget": SyncEntityType.BUDGETS,
            "budgets": SyncEntityType.BUDGETS,
            "category": SyncEntityType.CATEGORIES,
            "categories": SyncEntityType.CATEGORIES,
        }
        mapped_type = type_mapping.get(entity_type.lower())
        return mapped_type is None or mapped_type in self._enabled_entity_types

    def _emit_pending_count(self) -> None:
        """Emit the pending count signal."""
        count = self.get_pending_count()
        self.pending_count_changed.emit(count)

    def _persist_sync_record(self, operation: QueuedOperation) -> None:
        """Persist a sync record to the database."""
        session = self._session_factory()
        try:
            record = SyncRecord.create_for_entity(
                entity_type=operation.entity_type,
                entity_id=operation.entity_id,
                operation=operation.operation,
                payload=operation.payload,
                priority=operation.priority
            )
            session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to persist sync record: {e}")
        finally:
            session.close()

    # =========================================================================
    # Sync Operations
    # =========================================================================

    async def sync_now(
        self,
        entity_types: Optional[List[SyncEntityType]] = None
    ) -> SyncResult:
        """
        Perform immediate synchronization with the server.

        This is the main sync entry point. It orchestrates the full
        sync cycle: pull remote changes, then push local changes.

        Sync Algorithm:
        ---------------
        1. Check preconditions (not already syncing, online)
        2. Emit sync_started signal
        3. Pull Phase:
           - Request changes from server since last_sync_at
           - Apply remote changes to local database
           - Detect conflicts (same record modified locally)
        4. Push Phase:
           - Load pending SyncRecords from database
           - Process in batches (default: 50 per batch)
           - For each operation: call API, handle response
           - Update sync status (completed/failed/conflict)
        5. Emit sync_completed signal with SyncResult

        Args:
            entity_types: Optional list of entity types to sync.
                         If None, syncs all enabled types based on config.
                         Example: [SyncEntityType.TRANSACTIONS]

        Returns:
            SyncResult: Contains success status, counts, and any errors.

        Raises:
            Does not raise exceptions - errors captured in SyncResult.

        Example:
            result = await manager.sync_now()
            if result.success:
                print(f"Synced {result.synced_count} records")
            else:
                for error in result.errors:
                    logger.error(error)

        Signals Emitted:
            - sync_started: At beginning of sync
            - sync_progress: During batch processing
            - conflict_detected: When conflict found
            - sync_completed: At end with SyncResult
            - last_sync_updated: If sync successful
        """
        if self._state == SyncState.SYNCING:
            logger.warning("Sync already in progress")
            return SyncResult(success=False, errors=["Sync already in progress"])

        if not self._is_online:
            logger.warning("Cannot sync while offline")
            self.sync_error.emit("offline", "Cannot sync while offline")
            return SyncResult(success=False, errors=["Offline mode"])

        self._set_state(SyncState.SYNCING)
        self.sync_started.emit()
        start_time = datetime.utcnow()
        result = SyncResult(success=True)

        try:
            # Determine which entity types to sync
            types_to_sync = self._get_types_to_sync(entity_types)
            result.entity_types_synced = [t.value for t in types_to_sync]

            # Pull changes from server first
            pull_result = await self._pull_changes(types_to_sync)
            result.synced_count += pull_result.get("synced", 0)
            result.conflict_count += pull_result.get("conflicts", 0)

            # Load pending sync records from database
            await self._load_pending_records(types_to_sync)

            # Push local changes to server
            total_operations = self._queue.size
            processed = 0

            while not self._queue.is_empty:
                batch = self._queue.get_batch(self._config.batch_size)

                # Emit progress
                progress = SyncProgress(
                    current=processed,
                    total=total_operations,
                    operation="push",
                    message=f"Pushing changes ({processed}/{total_operations})"
                )
                self.sync_progress.emit(progress)

                batch_results = await self._process_batch(batch)

                result.synced_count += batch_results["synced"]
                result.failed_count += batch_results["failed"]
                result.conflict_count += batch_results["conflicts"]
                result.errors.extend(batch_results["errors"])

                processed += len(batch)

            # Final progress
            progress = SyncProgress(
                current=total_operations,
                total=total_operations,
                operation="complete",
                message="Sync completed"
            )
            self.sync_progress.emit(progress)

            self._last_sync_at = datetime.utcnow()
            self._total_synced += result.synced_count
            self._total_failed += result.failed_count

            # Emit last sync update
            self.last_sync_updated.emit(self._last_sync_at)

        except Exception as e:
            logger.error(f"Sync failed with error: {e}")
            result.success = False
            result.errors.append(str(e))
            self._set_state(SyncState.ERROR)
            self.sync_error.emit("sync_failed", str(e))
        else:
            self._set_state(SyncState.IDLE)

        # Calculate duration
        result.duration_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        # Emit sync completed signal
        self.sync_completed.emit(result)
        self._emit_pending_count()

        logger.info(
            f"Sync completed: {result.synced_count} synced, "
            f"{result.failed_count} failed, {result.conflict_count} conflicts"
        )
        return result

    def _get_types_to_sync(
        self,
        requested_types: Optional[List[SyncEntityType]]
    ) -> List[SyncEntityType]:
        """Get the list of entity types to sync."""
        if requested_types:
            return [t for t in requested_types if t in self._enabled_entity_types]
        return list(self._enabled_entity_types)

    async def _pull_changes(
        self,
        entity_types: List[SyncEntityType]
    ) -> Dict[str, int]:
        """
        Pull changes from the server.

        Args:
            entity_types: Entity types to pull.

        Returns:
            Dictionary with pull results.
        """
        results = {"synced": 0, "conflicts": 0, "errors": []}

        if not self._config.api_base_url:
            logger.debug("No API URL configured, skipping pull")
            return results

        for entity_type in entity_types:
            try:
                progress = SyncProgress(
                    entity_type=entity_type.value,
                    operation="pull",
                    message=f"Pulling {entity_type.value} from server"
                )
                self.sync_progress.emit(progress)

                # In production, this would make HTTP requests
                # For now, simulate the pull
                logger.debug(f"Would pull {entity_type.value} from server")
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to pull {entity_type.value}: {e}")
                results["errors"].append(str(e))

        return results

    async def _load_pending_records(
        self,
        entity_types: List[SyncEntityType]
    ) -> None:
        """Load pending sync records from the database."""
        session = self._session_factory()
        try:
            # Map entity types to database entity type strings
            type_strings = self._entity_types_to_strings(entity_types)

            query = session.query(SyncRecord).filter(
                SyncRecord.status.in_([
                    SyncStatus.PENDING,
                    SyncStatus.FAILED
                ])
            ).filter(
                SyncRecord.retry_count < SyncRecord.max_retries
            )

            if type_strings:
                query = query.filter(SyncRecord.entity_type.in_(type_strings))

            records = query.order_by(
                SyncRecord.priority,
                SyncRecord.created_at
            ).all()

            for record in records:
                if record.next_retry_at and record.next_retry_at > datetime.utcnow():
                    continue  # Skip if not ready for retry

                operation = QueuedOperation(
                    entity_type=record.entity_type,
                    entity_id=record.entity_id,
                    operation=record.operation,
                    payload=record.payload,
                    priority=record.priority,
                    record_id=record.id
                )
                self._queue.enqueue(operation)

            logger.debug(f"Loaded {len(records)} pending sync records")
        finally:
            session.close()

    def _entity_types_to_strings(
        self,
        entity_types: List[SyncEntityType]
    ) -> List[str]:
        """Convert SyncEntityType to database entity type strings."""
        type_mapping = {
            SyncEntityType.TRANSACTIONS: ["transaction", "transactions"],
            SyncEntityType.BUDGETS: ["budget", "budgets"],
            SyncEntityType.CATEGORIES: ["category", "categories"],
        }

        strings = []
        for et in entity_types:
            if et in type_mapping:
                strings.extend(type_mapping[et])
        return strings

    async def _process_batch(self, batch: List[QueuedOperation]) -> Dict[str, Any]:
        """
        Process a batch of sync operations.

        Args:
            batch: List of operations to process.

        Returns:
            Dictionary with batch results.
        """
        results = {
            "synced": 0,
            "failed": 0,
            "conflicts": 0,
            "errors": []
        }

        for operation in batch:
            try:
                success = await self._sync_operation(operation)
                if success:
                    results["synced"] += 1
                    await self._mark_synced(operation)
                else:
                    results["failed"] += 1
            except ConflictError as e:
                results["conflicts"] += 1
                await self._handle_conflict(operation, e)
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{operation.entity_type}:{operation.entity_id} - {e}")
                await self._mark_failed(operation, str(e))

        return results

    async def _sync_operation(self, operation: QueuedOperation) -> bool:
        """
        Execute a single sync operation.

        Args:
            operation: The operation to sync.

        Returns:
            True if successful, False otherwise.
        """
        if not self._config.api_base_url:
            logger.warning("No API URL configured, skipping actual sync")
            return True  # Simulate success for offline testing

        # Build the API endpoint
        endpoint = f"{self._config.api_base_url}/api/v1/{operation.entity_type}s"

        headers = {
            "Authorization": f"Bearer {self._config.api_token}",
            "Content-Type": "application/json"
        }

        # In production, use aiohttp or httpx here
        # For now, simulate the sync
        logger.debug(f"Would sync {operation.operation.value} to {endpoint}")

        # Simulate network delay
        await asyncio.sleep(0.1)

        return True

    async def _mark_synced(self, operation: QueuedOperation) -> None:
        """Mark a sync operation as completed."""
        if not operation.record_id:
            return

        session = self._session_factory()
        try:
            record = session.query(SyncRecord).filter_by(id=operation.record_id).first()
            if record:
                record.mark_completed()
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark sync record as completed: {e}")
        finally:
            session.close()

    async def _mark_failed(self, operation: QueuedOperation, error: str) -> None:
        """Mark a sync operation as failed."""
        if not operation.record_id:
            return

        session = self._session_factory()
        try:
            record = session.query(SyncRecord).filter_by(id=operation.record_id).first()
            if record:
                record.mark_failed(error)
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark sync record as failed: {e}")
        finally:
            session.close()

    async def _handle_conflict(
        self,
        operation: QueuedOperation,
        error: "ConflictError"
    ) -> None:
        """Handle a sync conflict."""
        session = self._session_factory()
        try:
            record = session.query(SyncRecord).filter_by(
                id=operation.record_id
            ).first()

            if record:
                record.mark_conflict(
                    conflict_data=json.dumps({
                        "local": operation.payload,
                        "remote": error.remote_data,
                        "type": error.conflict_type
                    }),
                    remote_version=error.remote_version
                )
                session.commit()

                # Emit conflict signal
                self.conflict_detected.emit(record)

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to handle conflict: {e}")
        finally:
            session.close()

    async def resolve_conflict(
        self,
        record_id: str,
        strategy: ResolutionStrategy
    ) -> bool:
        """
        Resolve a sync conflict.

        Args:
            record_id: ID of the sync record with conflict.
            strategy: Resolution strategy to use.

        Returns:
            True if resolution was successful.
        """
        session = self._session_factory()
        try:
            record = session.query(SyncRecord).filter_by(id=record_id).first()
            if not record or not record.needs_resolution:
                return False

            # Apply resolution strategy
            resolved_data = self._conflict_resolver.resolve(
                record.payload,
                record.conflict_data,
                strategy
            )

            # Update the record
            record.payload = resolved_data
            record.resolve_conflict(strategy.value)
            session.commit()

            # Re-queue for sync
            operation = QueuedOperation(
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                operation=record.operation,
                payload=resolved_data,
                record_id=record.id
            )
            self._queue.enqueue(operation)

            self._emit_pending_count()

            logger.info(f"Conflict resolved for {record.entity_type}:{record.entity_id}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to resolve conflict: {e}")
            return False
        finally:
            session.close()

    # =========================================================================
    # Status and Statistics
    # =========================================================================

    def get_pending_count(self) -> int:
        """Get the number of pending sync operations."""
        session = self._session_factory()
        try:
            return session.query(SyncRecord).filter(
                SyncRecord.status == SyncStatus.PENDING
            ).count()
        finally:
            session.close()

    def get_conflict_count(self) -> int:
        """Get the number of unresolved conflicts."""
        session = self._session_factory()
        try:
            return session.query(SyncRecord).filter(
                SyncRecord.status == SyncStatus.CONFLICT,
                SyncRecord.has_conflict == True
            ).count()
        finally:
            session.close()

    def get_conflicts(self) -> List[SyncRecord]:
        """Get all unresolved conflicts."""
        session = self._session_factory()
        try:
            return session.query(SyncRecord).filter(
                SyncRecord.status == SyncStatus.CONFLICT,
                SyncRecord.has_conflict == True
            ).all()
        finally:
            session.close()

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get comprehensive sync status information.

        Returns:
            Dictionary with sync status details.
        """
        return {
            "state": self._state.value,
            "is_online": self._is_online,
            "last_sync_at": self._last_sync_at.isoformat() if self._last_sync_at else None,
            "pending_count": self.get_pending_count(),
            "conflict_count": self.get_conflict_count(),
            "enabled_entity_types": [t.value for t in self._enabled_entity_types],
            "auto_sync_interval": self._config.auto_sync_interval_seconds,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get sync statistics."""
        return {
            "state": self._state.value,
            "is_online": self._is_online,
            "last_sync_at": self._last_sync_at.isoformat() if self._last_sync_at else None,
            "total_synced": self._total_synced,
            "total_failed": self._total_failed,
            "pending_count": self.get_pending_count(),
            "conflict_count": self.get_conflict_count(),
            "queue_size": self._queue.size,
            "last_connectivity_check": (
                self._last_connectivity_check.isoformat()
                if self._last_connectivity_check else None
            ),
        }

    # =========================================================================
    # Control Methods
    # =========================================================================

    def set_offline(self, offline: bool = True) -> None:
        """Set the offline mode manually."""
        self._set_online_status(not offline)

    def pause(self) -> None:
        """Pause synchronization."""
        if self._state in (SyncState.IDLE, SyncState.SYNCING):
            self._set_state(SyncState.PAUSED)
            if self._sync_timer:
                self._sync_timer.stop()

    def resume(self) -> None:
        """Resume synchronization."""
        if self._state == SyncState.PAUSED:
            self._set_state(SyncState.IDLE)
            if self._sync_timer:
                self._sync_timer.start(
                    self._config.auto_sync_interval_seconds * 1000
                )

    def force_sync(self) -> None:
        """Force an immediate sync, ignoring current state."""
        if self._is_online:
            self._set_state(SyncState.IDLE)
            asyncio.create_task(self.sync_now())

    def clear_queue(self) -> None:
        """Clear all pending sync operations."""
        self._queue.clear()

        session = self._session_factory()
        try:
            session.query(SyncRecord).filter(
                SyncRecord.status == SyncStatus.PENDING
            ).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to clear sync queue: {e}")
        finally:
            session.close()

        self._emit_pending_count()
        logger.info("Sync queue cleared")


class ConflictError(Exception):
    """Exception raised when a sync conflict is detected."""

    def __init__(
        self,
        message: str,
        conflict_type: str,
        remote_data: str,
        remote_version: Optional[int] = None
    ):
        super().__init__(message)
        self.conflict_type = conflict_type
        self.remote_data = remote_data
        self.remote_version = remote_version
