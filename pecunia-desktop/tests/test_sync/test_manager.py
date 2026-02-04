"""Tests for src/sync/manager.py — SyncManager and related classes."""

import json
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock

import pytest

# Mock PyQt6 before importing the module
import sys
mock_qt_core = MagicMock()
mock_qt_core.QObject = object
mock_qt_core.pyqtSignal = lambda *args, **kwargs: MagicMock()
mock_qt_core.QTimer = MagicMock
mock_qt_core.QThread = MagicMock
sys.modules.setdefault("PyQt6", MagicMock())
sys.modules.setdefault("PyQt6.QtCore", mock_qt_core)

from sync.manager import (
    SyncState, SyncEntityType, SyncResult, SyncProgress,
    SyncConfig, SyncManager, ConflictError,
)
from sync.conflict_resolver import ResolutionStrategy


class TestSyncState:
    """Tests for SyncState enum."""

    def test_idle_value(self):
        assert SyncState.IDLE.value == "idle"

    def test_syncing_value(self):
        assert SyncState.SYNCING.value == "syncing"

    def test_paused_value(self):
        assert SyncState.PAUSED.value == "paused"

    def test_error_value(self):
        assert SyncState.ERROR.value == "error"

    def test_offline_value(self):
        assert SyncState.OFFLINE.value == "offline"

    def test_is_str_enum(self):
        assert isinstance(SyncState.IDLE, str)


class TestSyncEntityType:
    """Tests for SyncEntityType enum."""

    def test_transactions_value(self):
        assert SyncEntityType.TRANSACTIONS.value == "transactions"

    def test_budgets_value(self):
        assert SyncEntityType.BUDGETS.value == "budgets"

    def test_categories_value(self):
        assert SyncEntityType.CATEGORIES.value == "categories"

    def test_users_value(self):
        assert SyncEntityType.USERS.value == "users"

    def test_all_value(self):
        assert SyncEntityType.ALL.value == "all"


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_default_values(self):
        result = SyncResult(success=True)
        assert result.success is True
        assert result.synced_count == 0
        assert result.failed_count == 0
        assert result.conflict_count == 0
        assert result.errors == []
        assert result.duration_ms == 0
        assert result.entity_types_synced == []

    def test_with_values(self):
        result = SyncResult(
            success=False,
            synced_count=5,
            failed_count=2,
            conflict_count=1,
            errors=["err1"],
            duration_ms=1234,
            entity_types_synced=["transactions"],
        )
        assert result.synced_count == 5
        assert result.failed_count == 2
        assert result.conflict_count == 1
        assert result.errors == ["err1"]
        assert result.duration_ms == 1234


class TestSyncProgress:
    """Tests for SyncProgress dataclass."""

    def test_default_values(self):
        progress = SyncProgress()
        assert progress.current == 0
        assert progress.total == 0
        assert progress.entity_type == ""
        assert progress.operation == ""
        assert progress.message == ""

    def test_percentage_normal(self):
        progress = SyncProgress(current=50, total=200)
        assert progress.percentage == 25.0

    def test_percentage_zero_total(self):
        progress = SyncProgress(current=0, total=0)
        assert progress.percentage == 0.0

    def test_percentage_complete(self):
        progress = SyncProgress(current=100, total=100)
        assert progress.percentage == 100.0


class TestSyncConfig:
    """Tests for SyncConfig dataclass."""

    def test_default_values(self):
        config = SyncConfig()
        assert config.api_base_url == ""
        assert config.api_token is None
        assert config.auto_sync_interval_seconds == 300
        assert config.sync_timeout_seconds == 60
        assert config.batch_size == 50
        assert config.sync_on_startup is True
        assert config.sync_on_change is True
        assert config.sync_deletions is True
        assert config.sync_transactions is True
        assert config.sync_budgets is True
        assert config.sync_categories is True

    def test_custom_values(self):
        config = SyncConfig(
            api_base_url="https://api.example.com",
            api_token="tok123",
            batch_size=20,
            sync_on_startup=False,
        )
        assert config.api_base_url == "https://api.example.com"
        assert config.api_token == "tok123"
        assert config.batch_size == 20
        assert config.sync_on_startup is False

    def test_default_resolution_strategy(self):
        config = SyncConfig()
        assert config.default_resolution_strategy == ResolutionStrategy.LAST_WRITE_WINS


class TestSyncManagerInit:
    """Tests for SyncManager initialization."""

    def _make_manager(self, config=None):
        session_factory = MagicMock()
        manager = SyncManager.__new__(SyncManager)
        manager._session_factory = session_factory
        manager._config = config or SyncConfig()
        manager._state = SyncState.IDLE
        manager._queue = MagicMock()
        manager._conflict_resolver = MagicMock()
        manager._sync_timer = None
        manager._connectivity_timer = None
        manager._sync_task = None
        manager._stop_event = asyncio.Event()
        manager._is_online = True
        manager._last_connectivity_check = None
        manager._last_sync_at = None
        manager._total_synced = 0
        manager._total_failed = 0
        manager._enabled_entity_types = set()
        manager._update_enabled_entity_types = SyncManager._update_enabled_entity_types.__get__(manager)
        manager._update_enabled_entity_types()
        # Mock signals
        manager.state_changed = MagicMock()
        manager.sync_started = MagicMock()
        manager.sync_completed = MagicMock()
        manager.sync_progress = MagicMock()
        manager.sync_error = MagicMock()
        manager.conflict_detected = MagicMock()
        manager.connectivity_changed = MagicMock()
        manager.last_sync_updated = MagicMock()
        manager.pending_count_changed = MagicMock()
        return manager

    def test_initial_state(self):
        manager = self._make_manager()
        assert manager.state == SyncState.IDLE

    def test_is_online_default(self):
        manager = self._make_manager()
        assert manager.is_online is True

    def test_last_sync_at_initially_none(self):
        manager = self._make_manager()
        assert manager.last_sync_at is None

    def test_enabled_entity_types_defaults(self):
        manager = self._make_manager()
        assert SyncEntityType.TRANSACTIONS in manager.enabled_entity_types
        assert SyncEntityType.BUDGETS in manager.enabled_entity_types
        assert SyncEntityType.CATEGORIES in manager.enabled_entity_types

    def test_enabled_entity_types_returns_copy(self):
        manager = self._make_manager()
        types = manager.enabled_entity_types
        types.add(SyncEntityType.USERS)
        assert SyncEntityType.USERS not in manager.enabled_entity_types


class TestSyncManagerStateMethods:
    """Tests for SyncManager state management methods."""

    def _make_manager(self):
        manager = TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)
        return manager

    def test_set_state_emits_signal(self):
        manager = self._make_manager()
        manager._set_state(SyncState.SYNCING)
        assert manager._state == SyncState.SYNCING
        manager.state_changed.emit.assert_called_with("syncing")

    def test_set_state_no_emit_if_same(self):
        manager = self._make_manager()
        manager._state = SyncState.IDLE
        manager._set_state(SyncState.IDLE)
        manager.state_changed.emit.assert_not_called()

    def test_set_online_status_emits_signal(self):
        manager = self._make_manager()
        manager._is_online = True
        manager._set_online_status(False)
        assert manager._is_online is False
        manager.connectivity_changed.emit.assert_called_with(False)

    def test_set_online_status_no_emit_if_same(self):
        manager = self._make_manager()
        manager._is_online = True
        manager._set_online_status(True)
        manager.connectivity_changed.emit.assert_not_called()

    def test_going_offline_sets_state(self):
        manager = self._make_manager()
        manager._is_online = True
        manager._set_online_status(False)
        assert manager._state == SyncState.OFFLINE

    def test_going_online_from_offline_sets_idle(self):
        manager = self._make_manager()
        manager._state = SyncState.OFFLINE
        manager._is_online = False
        manager._set_online_status(True)
        assert manager._state == SyncState.IDLE


class TestSyncManagerConfig:
    """Tests for SyncManager configuration methods."""

    def _make_manager(self):
        return TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)

    def test_configure(self):
        manager = self._make_manager()
        new_config = SyncConfig(batch_size=20, sync_on_startup=False)
        manager.configure(new_config)
        assert manager._config.batch_size == 20
        assert manager._config.sync_on_startup is False

    def test_set_api_credentials(self):
        manager = self._make_manager()
        manager.set_api_credentials("https://api.example.com", "token123")
        assert manager._config.api_base_url == "https://api.example.com"
        assert manager._config.api_token == "token123"

    def test_set_sync_transactions(self):
        manager = self._make_manager()
        manager.set_sync_transactions(False)
        assert manager._config.sync_transactions is False
        assert SyncEntityType.TRANSACTIONS not in manager._enabled_entity_types

    def test_set_sync_budgets(self):
        manager = self._make_manager()
        manager.set_sync_budgets(False)
        assert SyncEntityType.BUDGETS not in manager._enabled_entity_types

    def test_set_sync_categories(self):
        manager = self._make_manager()
        manager.set_sync_categories(False)
        assert SyncEntityType.CATEGORIES not in manager._enabled_entity_types

    def test_set_selective_sync(self):
        manager = self._make_manager()
        manager.set_selective_sync(transactions=True, budgets=False, categories=False)
        assert SyncEntityType.TRANSACTIONS in manager._enabled_entity_types
        assert SyncEntityType.BUDGETS not in manager._enabled_entity_types
        assert SyncEntityType.CATEGORIES not in manager._enabled_entity_types


class TestSyncManagerConnectivity:
    """Tests for SyncManager connectivity checking."""

    def _make_manager(self):
        return TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)

    @patch("sync.manager.socket.create_connection")
    def test_check_connectivity_success(self, mock_conn):
        manager = self._make_manager()
        result = manager.check_connectivity()
        assert result is True
        assert manager._is_online is True

    @patch("sync.manager.socket.create_connection", side_effect=OSError)
    def test_check_connectivity_failure(self, mock_conn):
        manager = self._make_manager()
        result = manager.check_connectivity()
        assert result is False
        assert manager._is_online is False

    @patch("sync.manager.socket.create_connection")
    def test_check_api_connectivity_no_url(self, mock_conn):
        manager = self._make_manager()
        manager._config.api_base_url = ""
        result = manager.check_api_connectivity()
        assert result is False

    @patch("sync.manager.socket.create_connection")
    def test_check_api_connectivity_success(self, mock_conn):
        manager = self._make_manager()
        manager._config.api_base_url = "https://api.example.com"
        result = manager.check_api_connectivity()
        assert result is True


class TestSyncManagerQueueOperations:
    """Tests for SyncManager queue operations."""

    def _make_manager(self):
        manager = TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)
        manager._config.sync_on_change = False  # Prevent auto-sync
        mock_session = MagicMock()
        manager._session_factory = MagicMock(return_value=mock_session)
        return manager

    def test_queue_create(self):
        manager = self._make_manager()
        manager.queue_create("transaction", "t1", {"amount": 100})
        manager._queue.enqueue.assert_called_once()

    def test_queue_update(self):
        manager = self._make_manager()
        manager.queue_update("transaction", "t1", {"amount": 200})
        manager._queue.enqueue.assert_called_once()

    def test_queue_delete(self):
        manager = self._make_manager()
        manager.queue_delete("transaction", "t1")
        manager._queue.enqueue.assert_called_once()

    def test_queue_delete_disabled(self):
        manager = self._make_manager()
        manager._config.sync_deletions = False
        manager.queue_delete("transaction", "t1")
        manager._queue.enqueue.assert_not_called()

    def test_queue_create_disabled_entity_type(self):
        manager = self._make_manager()
        manager._enabled_entity_types.clear()
        manager.queue_create("transaction", "t1", {"amount": 100})
        manager._queue.enqueue.assert_not_called()

    def test_is_entity_type_enabled_known(self):
        manager = self._make_manager()
        assert manager._is_entity_type_enabled("transaction") is True
        assert manager._is_entity_type_enabled("transactions") is True
        assert manager._is_entity_type_enabled("budget") is True
        assert manager._is_entity_type_enabled("category") is True

    def test_is_entity_type_enabled_unknown(self):
        manager = self._make_manager()
        # Unknown types should return True (no mapping found, so not blocked)
        assert manager._is_entity_type_enabled("unknown_type") is True


class TestSyncManagerSyncNow:
    """Tests for SyncManager sync_now method."""

    def _make_manager(self):
        manager = TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)
        manager._config.sync_on_change = False
        manager._queue.is_empty = True
        manager._queue.size = 0
        manager._queue.get_batch = MagicMock(return_value=[])
        mock_session = MagicMock()
        manager._session_factory = MagicMock(return_value=mock_session)
        return manager

    async def test_sync_now_already_syncing(self):
        manager = self._make_manager()
        manager._state = SyncState.SYNCING
        result = await manager.sync_now()
        assert result.success is False
        assert "already in progress" in result.errors[0]

    async def test_sync_now_offline(self):
        manager = self._make_manager()
        manager._is_online = False
        result = await manager.sync_now()
        assert result.success is False
        assert "Offline" in result.errors[0]

    async def test_sync_now_success_empty_queue(self):
        manager = self._make_manager()
        manager._pull_changes = AsyncMock(return_value={"synced": 0, "conflicts": 0})
        manager._load_pending_records = AsyncMock()
        result = await manager.sync_now()
        assert result.success is True
        assert manager._state == SyncState.IDLE
        assert manager._last_sync_at is not None

    async def test_sync_now_emits_signals(self):
        manager = self._make_manager()
        manager._pull_changes = AsyncMock(return_value={"synced": 0, "conflicts": 0})
        manager._load_pending_records = AsyncMock()
        await manager.sync_now()
        manager.sync_started.emit.assert_called_once()
        manager.sync_completed.emit.assert_called_once()

    async def test_sync_now_handles_exception(self):
        manager = self._make_manager()
        manager._pull_changes = AsyncMock(side_effect=Exception("Network error"))
        manager._load_pending_records = AsyncMock()
        result = await manager.sync_now()
        assert result.success is False
        assert "Network error" in result.errors[0]
        assert manager._state == SyncState.ERROR


class TestSyncManagerControlMethods:
    """Tests for SyncManager control methods."""

    def _make_manager(self):
        return TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)

    def test_pause_from_idle(self):
        manager = self._make_manager()
        manager._sync_timer = MagicMock()
        manager.pause()
        assert manager._state == SyncState.PAUSED
        manager._sync_timer.stop.assert_called_once()

    def test_resume_from_paused(self):
        manager = self._make_manager()
        manager._state = SyncState.PAUSED
        manager._sync_timer = MagicMock()
        manager.resume()
        assert manager._state == SyncState.IDLE
        manager._sync_timer.start.assert_called_once()

    def test_resume_does_nothing_if_not_paused(self):
        manager = self._make_manager()
        manager._state = SyncState.IDLE
        manager.resume()
        assert manager._state == SyncState.IDLE

    def test_set_offline(self):
        manager = self._make_manager()
        manager.set_offline(True)
        assert manager._is_online is False

    def test_set_offline_false(self):
        manager = self._make_manager()
        manager._is_online = False
        manager._state = SyncState.OFFLINE
        manager.set_offline(False)
        assert manager._is_online is True

    def test_stop_stops_timers(self):
        manager = self._make_manager()
        manager._sync_timer = MagicMock()
        manager._connectivity_timer = MagicMock()
        manager.stop()
        manager._sync_timer.stop.assert_called_once()
        manager._connectivity_timer.stop.assert_called_once()
        assert manager._sync_timer is None
        assert manager._connectivity_timer is None

    def test_clear_queue(self):
        manager = self._make_manager()
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        manager._session_factory = MagicMock(return_value=mock_session)
        manager.clear_queue()
        manager._queue.clear.assert_called_once()


class TestSyncManagerStatus:
    """Tests for SyncManager status and statistics."""

    def _make_manager(self):
        manager = TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.all.return_value = []
        manager._session_factory = MagicMock(return_value=mock_session)
        return manager

    def test_get_pending_count(self):
        manager = self._make_manager()
        count = manager.get_pending_count()
        assert count == 3

    def test_get_conflict_count(self):
        manager = self._make_manager()
        count = manager.get_conflict_count()
        assert count == 3

    def test_get_sync_status(self):
        manager = self._make_manager()
        status = manager.get_sync_status()
        assert "state" in status
        assert "is_online" in status
        assert "pending_count" in status
        assert "conflict_count" in status
        assert status["state"] == "idle"
        assert status["is_online"] is True

    def test_get_statistics(self):
        manager = self._make_manager()
        stats = manager.get_statistics()
        assert "state" in stats
        assert "total_synced" in stats
        assert "total_failed" in stats
        assert "queue_size" in stats
        assert stats["total_synced"] == 0


class TestConflictError:
    """Tests for ConflictError exception."""

    def test_basic_creation(self):
        err = ConflictError("conflict detected", "version_mismatch", '{"field": "amount"}')
        assert str(err) == "conflict detected"
        assert err.conflict_type == "version_mismatch"
        assert err.remote_data == '{"field": "amount"}'
        assert err.remote_version is None

    def test_with_remote_version(self):
        err = ConflictError("conflict", "concurrent", '{}', remote_version=5)
        assert err.remote_version == 5

    def test_is_exception(self):
        err = ConflictError("test", "type", "data")
        assert isinstance(err, Exception)


class TestEntityTypesToStrings:
    """Tests for entity type string conversion."""

    def _make_manager(self):
        return TestSyncManagerInit._make_manager(TestSyncManagerInit(), None)

    def test_transactions(self):
        manager = self._make_manager()
        result = manager._entity_types_to_strings([SyncEntityType.TRANSACTIONS])
        assert "transaction" in result
        assert "transactions" in result

    def test_budgets(self):
        manager = self._make_manager()
        result = manager._entity_types_to_strings([SyncEntityType.BUDGETS])
        assert "budget" in result
        assert "budgets" in result

    def test_categories(self):
        manager = self._make_manager()
        result = manager._entity_types_to_strings([SyncEntityType.CATEGORIES])
        assert "category" in result
        assert "categories" in result

    def test_unknown_type_returns_empty(self):
        manager = self._make_manager()
        result = manager._entity_types_to_strings([SyncEntityType.ALL])
        assert result == []
