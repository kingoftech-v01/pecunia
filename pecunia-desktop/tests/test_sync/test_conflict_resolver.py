"""Tests for src/sync/conflict_resolver.py — ConflictResolver and related classes."""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from sync.conflict_resolver import (
    ConflictType, ResolutionStrategy, ConflictDetails, ResolutionResult,
    ConflictResolution, ConflictHistoryEntry, ConflictResolver,
    AutoResolver, DefaultNotificationHandler,
)


class TestConflictType:
    """Tests for ConflictType enum."""

    def test_version_mismatch(self):
        assert ConflictType.VERSION_MISMATCH.value == "version_mismatch"

    def test_concurrent_modification(self):
        assert ConflictType.CONCURRENT_MODIFICATION.value == "concurrent_modification"

    def test_delete_update(self):
        assert ConflictType.DELETE_UPDATE.value == "delete_update"

    def test_duplicate_create(self):
        assert ConflictType.DUPLICATE_CREATE.value == "duplicate_create"

    def test_schema_mismatch(self):
        assert ConflictType.SCHEMA_MISMATCH.value == "schema_mismatch"

    def test_constraint_violation(self):
        assert ConflictType.CONSTRAINT_VIOLATION.value == "constraint_violation"

    def test_is_str_enum(self):
        assert isinstance(ConflictType.VERSION_MISMATCH, str)


class TestResolutionStrategy:
    """Tests for ResolutionStrategy enum."""

    def test_server_wins(self):
        assert ResolutionStrategy.SERVER_WINS.value == "server_wins"

    def test_client_wins(self):
        assert ResolutionStrategy.CLIENT_WINS.value == "client_wins"

    def test_local_wins_alias(self):
        assert ResolutionStrategy.LOCAL_WINS.value == "local_wins"

    def test_remote_wins_alias(self):
        assert ResolutionStrategy.REMOTE_WINS.value == "remote_wins"

    def test_last_write_wins(self):
        assert ResolutionStrategy.LAST_WRITE_WINS.value == "last_write_wins"

    def test_first_write_wins(self):
        assert ResolutionStrategy.FIRST_WRITE_WINS.value == "first_write_wins"

    def test_merge(self):
        assert ResolutionStrategy.MERGE.value == "merge"

    def test_manual(self):
        assert ResolutionStrategy.MANUAL.value == "manual"

    def test_custom(self):
        assert ResolutionStrategy.CUSTOM.value == "custom"


class TestConflictDetails:
    """Tests for ConflictDetails dataclass."""

    def _make_conflict(self, **kwargs):
        defaults = dict(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={"amount": 100, "sync_version": 1},
            remote_data={"amount": 200, "sync_version": 2},
            local_version=1,
            remote_version=2,
        )
        defaults.update(kwargs)
        return ConflictDetails(**defaults)

    def test_creation(self):
        conflict = self._make_conflict()
        assert conflict.entity_type == "transaction"
        assert conflict.entity_id == "t1"
        assert conflict.local_version == 1
        assert conflict.remote_version == 2

    def test_default_values(self):
        conflict = self._make_conflict()
        assert conflict.local_updated_at is None
        assert conflict.remote_updated_at is None
        assert conflict.field_conflicts == []
        assert conflict.suggested_strategy == ResolutionStrategy.MANUAL
        assert conflict.metadata == {}


class TestResolutionResult:
    """Tests for ResolutionResult dataclass."""

    def test_success(self):
        result = ResolutionResult(
            success=True,
            resolved_data={"amount": 200},
            strategy_used=ResolutionStrategy.SERVER_WINS,
            changes_made=["Applied server value for amount"],
        )
        assert result.success is True
        assert result.resolved_data == {"amount": 200}

    def test_failure(self):
        result = ResolutionResult(success=False, error_message="Manual required")
        assert result.success is False
        assert result.error_message == "Manual required"
        assert result.resolved_data is None


class TestConflictResolution:
    """Tests for ConflictResolution dataclass."""

    def test_creation(self):
        resolution = ConflictResolution(
            entity_type="transaction",
            entity_id="t1",
            strategy_used=ResolutionStrategy.MERGE,
        )
        assert resolution.entity_type == "transaction"
        assert resolution.resolved_by == "system"
        assert resolution.auto_resolved is False
        assert isinstance(resolution.resolution_id, str)

    def test_to_dict(self):
        resolution = ConflictResolution(
            entity_type="budget",
            entity_id="b1",
            strategy_used=ResolutionStrategy.SERVER_WINS,
        )
        d = resolution.to_dict()
        assert d["entity_type"] == "budget"
        assert d["strategy_used"] == "server_wins"
        assert "resolution_id" in d
        assert "resolved_at" in d


class TestConflictHistoryEntry:
    """Tests for ConflictHistoryEntry dataclass."""

    def test_creation(self):
        entry = ConflictHistoryEntry()
        assert isinstance(entry.entry_id, str)
        assert isinstance(entry.logged_at, datetime)

    def test_to_dict_no_conflict(self):
        entry = ConflictHistoryEntry()
        d = entry.to_dict()
        assert d["conflict"]["entity_type"] is None
        assert d["resolution"] is None

    def test_to_dict_with_conflict_and_resolution(self):
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={}, remote_data={},
            local_version=1, remote_version=2,
        )
        resolution = ConflictResolution(
            entity_type="transaction",
            entity_id="t1",
            strategy_used=ResolutionStrategy.MERGE,
        )
        entry = ConflictHistoryEntry(conflict=conflict, resolution=resolution)
        d = entry.to_dict()
        assert d["conflict"]["entity_type"] == "transaction"
        assert d["resolution"]["strategy_used"] == "merge"


class TestDefaultNotificationHandler:
    """Tests for DefaultNotificationHandler."""

    def test_notify_conflict_detected(self):
        handler = DefaultNotificationHandler()
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="t", entity_id="1",
            local_data={}, remote_data={},
            local_version=1, remote_version=2,
        )
        # Should not raise
        handler.notify_conflict_detected(conflict)

    def test_notify_resolution_complete(self):
        handler = DefaultNotificationHandler()
        resolution = ConflictResolution(
            entity_type="t", entity_id="1",
            strategy_used=ResolutionStrategy.MERGE,
        )
        handler.notify_resolution_complete(resolution)

    def test_request_manual_resolution(self):
        handler = DefaultNotificationHandler()
        conflict = ConflictDetails(
            conflict_type=ConflictType.DELETE_UPDATE,
            entity_type="t", entity_id="1",
            local_data={}, remote_data={},
            local_version=1, remote_version=2,
        )
        handler.request_manual_resolution(conflict, lambda x: None)


class TestConflictResolverInit:
    """Tests for ConflictResolver initialization."""

    def test_default_strategy(self):
        resolver = ConflictResolver()
        assert resolver.default_strategy == ResolutionStrategy.LAST_WRITE_WINS

    def test_custom_default_strategy(self):
        resolver = ConflictResolver(default_strategy=ResolutionStrategy.SERVER_WINS)
        assert resolver.default_strategy == ResolutionStrategy.SERVER_WINS

    def test_set_default_strategy(self):
        resolver = ConflictResolver()
        resolver.default_strategy = ResolutionStrategy.MERGE
        assert resolver.default_strategy == ResolutionStrategy.MERGE


class TestConflictResolverDetection:
    """Tests for ConflictResolver conflict detection."""

    def test_no_conflict_same_version(self):
        resolver = ConflictResolver()
        result = resolver.detect_conflict(
            "transaction", "t1",
            {"sync_version": 1, "amount": 100},
            {"sync_version": 1, "amount": 100},
        )
        assert result is None

    def test_detect_version_mismatch(self):
        resolver = ConflictResolver()
        result = resolver.detect_conflict(
            "transaction", "t1",
            {"sync_version": 1, "amount": 100},
            {"sync_version": 2, "amount": 200},
        )
        assert result is not None
        assert result.conflict_type == ConflictType.VERSION_MISMATCH
        assert result.local_version == 1
        assert result.remote_version == 2

    def test_detect_delete_update_conflict(self):
        resolver = ConflictResolver()
        result = resolver.detect_conflict(
            "transaction", "t1",
            {"sync_version": 1, "deleted_at": "2024-01-01"},
            {"sync_version": 2, "deleted_at": None, "amount": 100},
        )
        assert result is not None
        assert result.conflict_type == ConflictType.DELETE_UPDATE

    def test_detect_field_conflicts(self):
        resolver = ConflictResolver()
        result = resolver.detect_conflict(
            "transaction", "t1",
            {"sync_version": 1, "amount": 100, "description": "Old"},
            {"sync_version": 2, "amount": 200, "description": "New"},
        )
        assert result is not None
        assert "amount" in result.field_conflicts
        assert "description" in result.field_conflicts

    def test_ignored_fields_not_in_conflicts(self):
        resolver = ConflictResolver()
        result = resolver.detect_conflict(
            "transaction", "t1",
            {"sync_version": 1, "updated_at": "2024-01-01", "amount": 100},
            {"sync_version": 2, "updated_at": "2024-01-02", "amount": 200},
        )
        assert result is not None
        assert "updated_at" not in result.field_conflicts
        assert "sync_version" not in result.field_conflicts


class TestConflictResolverResolve:
    """Tests for ConflictResolver resolve method (JSON-based)."""

    def test_resolve_local_wins(self):
        resolver = ConflictResolver()
        local = json.dumps({"amount": 100})
        conflict = json.dumps({"remote": {"amount": 200}})
        result = resolver.resolve(local, conflict, ResolutionStrategy.LOCAL_WINS)
        data = json.loads(result)
        assert data["amount"] == 100

    def test_resolve_remote_wins(self):
        resolver = ConflictResolver()
        local = json.dumps({"amount": 100})
        conflict = json.dumps({"remote": {"amount": 200}})
        result = resolver.resolve(local, conflict, ResolutionStrategy.REMOTE_WINS)
        data = json.loads(result)
        assert data["amount"] == 200

    def test_resolve_last_write_wins_local_newer(self):
        resolver = ConflictResolver()
        local = json.dumps({"amount": 100, "updated_at": "2024-06-01T12:00:00"})
        conflict = json.dumps({"remote": {"amount": 200, "updated_at": "2024-01-01T12:00:00"}})
        result = resolver.resolve(local, conflict, ResolutionStrategy.LAST_WRITE_WINS)
        data = json.loads(result)
        assert data["amount"] == 100

    def test_resolve_last_write_wins_remote_newer(self):
        resolver = ConflictResolver()
        local = json.dumps({"amount": 100, "updated_at": "2024-01-01T12:00:00"})
        conflict = json.dumps({"remote": {"amount": 200, "updated_at": "2024-06-01T12:00:00"}})
        result = resolver.resolve(local, conflict, ResolutionStrategy.LAST_WRITE_WINS)
        data = json.loads(result)
        assert data["amount"] == 200

    def test_resolve_merge(self):
        resolver = ConflictResolver()
        local = json.dumps({"amount": 100, "description": "Local"})
        conflict = json.dumps({"remote": {"amount": 200, "extra_field": "value"}})
        result = resolver.resolve(local, conflict, ResolutionStrategy.MERGE)
        data = json.loads(result)
        # Merge should include extra remote fields not in local
        assert "extra_field" in data

    def test_resolve_default_strategy(self):
        resolver = ConflictResolver(default_strategy=ResolutionStrategy.LOCAL_WINS)
        local = json.dumps({"amount": 100})
        conflict = json.dumps({"remote": {"amount": 200}})
        result = resolver.resolve(local, conflict)
        data = json.loads(result)
        assert data["amount"] == 100

    def test_resolve_none_payloads(self):
        resolver = ConflictResolver()
        result = resolver.resolve(None, None, ResolutionStrategy.LOCAL_WINS)
        data = json.loads(result)
        assert data == {}


class TestConflictResolverResolveConflict:
    """Tests for ConflictResolver resolve_conflict method (ConflictDetails-based)."""

    def _make_conflict(self, **kwargs):
        defaults = dict(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={"amount": 100, "sync_version": 1},
            remote_data={"amount": 200, "sync_version": 2},
            local_version=1,
            remote_version=2,
            field_conflicts=["amount"],
            local_updated_at=datetime(2024, 6, 1),
            remote_updated_at=datetime(2024, 1, 1),
        )
        defaults.update(kwargs)
        return ConflictDetails(**defaults)

    def test_resolve_local_wins(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict()
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.LOCAL_WINS)
        assert result.success is True
        assert result.resolved_data["amount"] == 100
        assert result.resolved_data["sync_version"] == 3  # max(1,2) + 1

    def test_resolve_remote_wins(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict()
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.REMOTE_WINS)
        assert result.success is True
        assert result.resolved_data["amount"] == 200

    def test_resolve_last_write_wins_local_newer(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            local_updated_at=datetime(2024, 6, 1),
            remote_updated_at=datetime(2024, 1, 1),
        )
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.LAST_WRITE_WINS)
        assert result.success is True
        assert result.resolved_data["amount"] == 100

    def test_resolve_first_write_wins(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            local_updated_at=datetime(2024, 1, 1),
            remote_updated_at=datetime(2024, 6, 1),
        )
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.FIRST_WRITE_WINS)
        assert result.success is True
        assert result.resolved_data["amount"] == 100  # Local was first

    def test_resolve_merge(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            local_data={"amount": 100, "desc": "Local", "sync_version": 1},
            remote_data={"amount": 200, "desc": "Remote", "sync_version": 2},
            field_conflicts=["amount", "desc"],
        )
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.MERGE)
        assert result.success is True
        assert "sync_version" in result.resolved_data

    def test_resolve_manual_returns_error(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict()
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.MANUAL)
        assert result.success is False
        assert "Manual" in result.error_message

    def test_custom_handler(self):
        resolver = ConflictResolver()
        custom_result = ResolutionResult(
            success=True,
            resolved_data={"amount": 150},
            strategy_used=ResolutionStrategy.CUSTOM,
        )
        resolver.register_custom_handler("transaction", lambda c: custom_result)
        conflict = self._make_conflict()
        result = resolver.resolve_conflict(conflict)
        assert result.success is True
        assert result.resolved_data["amount"] == 150

    def test_custom_handler_error(self):
        resolver = ConflictResolver()
        resolver.register_custom_handler("transaction", lambda c: (_ for _ in ()).throw(RuntimeError("oops")))
        conflict = self._make_conflict()
        result = resolver.resolve_conflict(conflict)
        assert result.success is False


class TestConflictResolverFieldPriority:
    """Tests for field priority and merge rules."""

    def test_set_field_priority(self):
        resolver = ConflictResolver()
        resolver.set_field_priority("amount", "remote")
        assert resolver._field_priorities["amount"] == "remote"

    def test_set_field_priority_invalid(self):
        resolver = ConflictResolver()
        with pytest.raises(ValueError):
            resolver.set_field_priority("amount", "invalid")

    def test_register_merge_rule(self):
        resolver = ConflictResolver()
        resolver.register_merge_rule("amount", lambda l, r: max(l, r))
        assert "amount" in resolver._merge_rules

    def test_merge_uses_field_priority(self):
        resolver = ConflictResolver()
        resolver.set_field_priority("amount", "remote")
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={"amount": 100, "sync_version": 1},
            remote_data={"amount": 200, "sync_version": 2},
            local_version=1,
            remote_version=2,
            field_conflicts=["amount"],
            local_updated_at=datetime(2024, 6, 1),
            remote_updated_at=datetime(2024, 1, 1),
        )
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.MERGE)
        assert result.success is True
        assert result.resolved_data["amount"] == 200

    def test_merge_uses_custom_rule(self):
        resolver = ConflictResolver()
        resolver.register_merge_rule("amount", lambda l, r: l + r)
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={"amount": 100, "sync_version": 1},
            remote_data={"amount": 200, "sync_version": 2},
            local_version=1,
            remote_version=2,
            field_conflicts=["amount"],
        )
        result = resolver.resolve_conflict(conflict, ResolutionStrategy.MERGE)
        assert result.success is True
        assert result.resolved_data["amount"] == 300


class TestConflictSummary:
    """Tests for conflict summary generation."""

    def test_get_conflict_summary(self):
        resolver = ConflictResolver()
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={"amount": 100},
            remote_data={"amount": 200},
            local_version=1,
            remote_version=2,
            field_conflicts=["amount"],
            local_updated_at=datetime(2024, 1, 1),
            remote_updated_at=datetime(2024, 6, 1),
        )
        summary = resolver.get_conflict_summary(conflict)
        assert "transaction" in summary
        assert "t1" in summary
        assert "version_mismatch" in summary
        assert "amount" in summary
        assert "Local Version: 1" in summary
        assert "Remote Version: 2" in summary


class TestAutoResolver:
    """Tests for AutoResolver class."""

    def test_auto_resolve_matching_rule(self):
        resolver = ConflictResolver()
        auto = AutoResolver(resolver)
        auto.add_rule(
            lambda c: c.entity_type == "transaction",
            ResolutionStrategy.SERVER_WINS,
        )
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={"amount": 100, "sync_version": 1},
            remote_data={"amount": 200, "sync_version": 2},
            local_version=1,
            remote_version=2,
            field_conflicts=["amount"],
        )
        result = auto.auto_resolve(conflict)
        assert result is not None
        assert result.success is True

    def test_auto_resolve_no_matching_rule(self):
        resolver = ConflictResolver()
        auto = AutoResolver(resolver)
        auto.add_rule(
            lambda c: c.entity_type == "budget",
            ResolutionStrategy.SERVER_WINS,
        )
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="transaction",
            entity_id="t1",
            local_data={}, remote_data={},
            local_version=1, remote_version=2,
        )
        result = auto.auto_resolve(conflict)
        assert result is None

    def test_auto_resolve_rule_exception(self):
        resolver = ConflictResolver()
        auto = AutoResolver(resolver)
        auto.add_rule(lambda c: 1/0, ResolutionStrategy.SERVER_WINS)  # Will raise
        conflict = ConflictDetails(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="t", entity_id="1",
            local_data={}, remote_data={},
            local_version=1, remote_version=2,
        )
        result = auto.auto_resolve(conflict)
        assert result is None
