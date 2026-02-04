"""
Conflict resolver for handling sync conflicts.

Provides strategies and utilities for detecting and resolving
data conflicts in offline-first synchronization.

Features:
- Detect conflicts between local and server versions
- Resolution strategies: server_wins, client_wins, merge, manual
- Merge logic for different entity types (transactions, budgets, etc.)
- User notification for manual conflicts
- Conflict history logging
"""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Tuple, Protocol
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of sync conflicts."""
    VERSION_MISMATCH = "version_mismatch"
    CONCURRENT_MODIFICATION = "concurrent_modification"
    DELETE_UPDATE = "delete_update"
    DUPLICATE_CREATE = "duplicate_create"
    SCHEMA_MISMATCH = "schema_mismatch"
    CONSTRAINT_VIOLATION = "constraint_violation"


class ResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    LOCAL_WINS = "local_wins"  # Alias for CLIENT_WINS
    REMOTE_WINS = "remote_wins"  # Alias for SERVER_WINS
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    CUSTOM = "custom"


@dataclass
class ConflictDetails:
    """Details about a detected conflict."""
    conflict_type: ConflictType
    entity_type: str
    entity_id: str
    local_data: Dict[str, Any]
    remote_data: Dict[str, Any]
    local_version: int
    remote_version: int
    local_updated_at: Optional[datetime] = None
    remote_updated_at: Optional[datetime] = None
    field_conflicts: List[str] = field(default_factory=list)
    suggested_strategy: ResolutionStrategy = ResolutionStrategy.MANUAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionResult:
    """Result of a conflict resolution."""
    success: bool
    resolved_data: Optional[Dict[str, Any]] = None
    strategy_used: Optional[ResolutionStrategy] = None
    changes_made: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class ConflictResolution:
    """
    Tracks the resolution of a conflict for audit and history purposes.

    This dataclass stores all information about how a conflict was resolved,
    including the strategy used, who resolved it, and any additional notes.
    """
    resolution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_id: str = ""
    entity_type: str = ""
    entity_id: str = ""
    strategy_used: ResolutionStrategy = ResolutionStrategy.MANUAL
    local_data: Dict[str, Any] = field(default_factory=dict)
    remote_data: Dict[str, Any] = field(default_factory=dict)
    resolved_data: Dict[str, Any] = field(default_factory=dict)
    resolved_by: str = "system"  # "system" or user identifier
    resolved_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    auto_resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "resolution_id": self.resolution_id,
            "conflict_id": self.conflict_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "strategy_used": self.strategy_used.value,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat(),
            "notes": self.notes,
            "auto_resolved": self.auto_resolved
        }


class ConflictNotificationHandler(Protocol):
    """Protocol for handling conflict notifications to users."""

    def notify_conflict_detected(self, conflict: ConflictDetails) -> None:
        """Notify user that a conflict was detected."""
        ...

    def notify_resolution_complete(self, resolution: ConflictResolution) -> None:
        """Notify user that a conflict was resolved."""
        ...

    def request_manual_resolution(
        self,
        conflict: ConflictDetails,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Request user to manually resolve a conflict."""
        ...


class DefaultNotificationHandler:
    """Default notification handler that logs to logger."""

    def notify_conflict_detected(self, conflict: ConflictDetails) -> None:
        """Log conflict detection."""
        logger.warning(
            f"Conflict detected for {conflict.entity_type} "
            f"(ID: {conflict.entity_id}): {conflict.conflict_type.value}"
        )

    def notify_resolution_complete(self, resolution: ConflictResolution) -> None:
        """Log conflict resolution."""
        logger.info(
            f"Conflict resolved for {resolution.entity_type} "
            f"(ID: {resolution.entity_id}) using {resolution.strategy_used.value}"
        )

    def request_manual_resolution(
        self,
        conflict: ConflictDetails,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Log manual resolution request."""
        logger.warning(
            f"Manual resolution required for {conflict.entity_type} "
            f"(ID: {conflict.entity_id})"
        )


@dataclass
class ConflictHistoryEntry:
    """Entry in the conflict history log."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict: Optional[ConflictDetails] = None
    resolution: Optional[ConflictResolution] = None
    logged_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "logged_at": self.logged_at.isoformat(),
            "conflict": {
                "entity_type": self.conflict.entity_type if self.conflict else None,
                "entity_id": self.conflict.entity_id if self.conflict else None,
                "conflict_type": self.conflict.conflict_type.value if self.conflict else None,
            },
            "resolution": self.resolution.to_dict() if self.resolution else None
        }


class ConflictResolver:
    """
    Handles detection and resolution of sync conflicts.

    Supports multiple resolution strategies and custom handlers
    for different conflict scenarios.
    """

    def __init__(
        self,
        default_strategy: ResolutionStrategy = ResolutionStrategy.LAST_WRITE_WINS
    ):
        """
        Initialize the conflict resolver.

        Args:
            default_strategy: Default strategy for resolving conflicts.
        """
        self._default_strategy = default_strategy
        self._custom_handlers: Dict[str, Callable] = {}
        self._field_priorities: Dict[str, str] = {}  # field -> 'local' or 'remote'
        self._merge_rules: Dict[str, Callable] = {}

        logger.debug(f"ConflictResolver initialized with strategy: {default_strategy.value}")

    @property
    def default_strategy(self) -> ResolutionStrategy:
        """Get the default resolution strategy."""
        return self._default_strategy

    @default_strategy.setter
    def default_strategy(self, strategy: ResolutionStrategy) -> None:
        """Set the default resolution strategy."""
        self._default_strategy = strategy
        logger.info(f"Default resolution strategy set to: {strategy.value}")

    def register_custom_handler(
        self,
        entity_type: str,
        handler: Callable[[ConflictDetails], ResolutionResult]
    ) -> None:
        """
        Register a custom conflict handler for an entity type.

        Args:
            entity_type: Type of entity (e.g., 'transaction', 'budget').
            handler: Custom handler function.
        """
        self._custom_handlers[entity_type] = handler
        logger.debug(f"Registered custom handler for: {entity_type}")

    def set_field_priority(self, field_name: str, priority: str) -> None:
        """
        Set priority for a specific field during merge.

        Args:
            field_name: Name of the field.
            priority: 'local' or 'remote'.
        """
        if priority not in ('local', 'remote'):
            raise ValueError("Priority must be 'local' or 'remote'")
        self._field_priorities[field_name] = priority

    def register_merge_rule(
        self,
        field_name: str,
        merge_func: Callable[[Any, Any], Any]
    ) -> None:
        """
        Register a custom merge rule for a field.

        Args:
            field_name: Name of the field.
            merge_func: Function that takes (local_value, remote_value) and returns merged value.
        """
        self._merge_rules[field_name] = merge_func
        logger.debug(f"Registered merge rule for field: {field_name}")

    def detect_conflict(
        self,
        entity_type: str,
        entity_id: str,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any]
    ) -> Optional[ConflictDetails]:
        """
        Detect if there's a conflict between local and remote data.

        Args:
            entity_type: Type of entity.
            entity_id: ID of the entity.
            local_data: Local version of the data.
            remote_data: Remote version of the data.

        Returns:
            ConflictDetails if conflict detected, None otherwise.
        """
        local_version = local_data.get('sync_version', 0)
        remote_version = remote_data.get('sync_version', 0)

        # No conflict if versions match
        if local_version == remote_version:
            return None

        # Detect conflict type
        conflict_type = self._determine_conflict_type(local_data, remote_data)

        # Find conflicting fields
        field_conflicts = self._find_field_conflicts(local_data, remote_data)

        if not field_conflicts and conflict_type != ConflictType.VERSION_MISMATCH:
            return None

        # Parse timestamps
        local_updated = self._parse_datetime(local_data.get('updated_at'))
        remote_updated = self._parse_datetime(remote_data.get('updated_at'))

        # Suggest resolution strategy
        suggested_strategy = self._suggest_strategy(
            conflict_type,
            local_updated,
            remote_updated,
            field_conflicts
        )

        conflict = ConflictDetails(
            conflict_type=conflict_type,
            entity_type=entity_type,
            entity_id=entity_id,
            local_data=local_data,
            remote_data=remote_data,
            local_version=local_version,
            remote_version=remote_version,
            local_updated_at=local_updated,
            remote_updated_at=remote_updated,
            field_conflicts=field_conflicts,
            suggested_strategy=suggested_strategy
        )

        logger.info(
            f"Conflict detected: {entity_type}:{entity_id} "
            f"(type={conflict_type.value}, fields={field_conflicts})"
        )
        return conflict

    def _determine_conflict_type(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any]
    ) -> ConflictType:
        """Determine the type of conflict."""
        local_deleted = local_data.get('deleted_at') is not None
        remote_deleted = remote_data.get('deleted_at') is not None

        if local_deleted != remote_deleted:
            return ConflictType.DELETE_UPDATE

        local_version = local_data.get('sync_version', 0)
        remote_version = remote_data.get('sync_version', 0)

        if local_version != remote_version:
            return ConflictType.VERSION_MISMATCH

        return ConflictType.CONCURRENT_MODIFICATION

    def _find_field_conflicts(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any]
    ) -> List[str]:
        """Find fields that have different values."""
        # Fields to ignore in conflict detection
        ignore_fields = {
            'sync_version', 'last_synced_at', 'is_dirty',
            'updated_at', 'created_at', 'id', 'remote_id'
        }

        conflicts = []
        all_keys = set(local_data.keys()) | set(remote_data.keys())

        for key in all_keys:
            if key in ignore_fields:
                continue

            local_value = local_data.get(key)
            remote_value = remote_data.get(key)

            if local_value != remote_value:
                conflicts.append(key)

        return conflicts

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse a datetime value."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None

    def _suggest_strategy(
        self,
        conflict_type: ConflictType,
        local_updated: Optional[datetime],
        remote_updated: Optional[datetime],
        field_conflicts: List[str]
    ) -> ResolutionStrategy:
        """Suggest a resolution strategy based on conflict details."""
        # Delete conflicts usually need manual resolution
        if conflict_type == ConflictType.DELETE_UPDATE:
            return ResolutionStrategy.MANUAL

        # Simple version conflicts can use last-write-wins
        if conflict_type == ConflictType.VERSION_MISMATCH:
            if local_updated and remote_updated:
                return ResolutionStrategy.LAST_WRITE_WINS
            return ResolutionStrategy.REMOTE_WINS

        # Few field conflicts might be mergeable
        if len(field_conflicts) <= 3:
            return ResolutionStrategy.MERGE

        return self._default_strategy

    def resolve(
        self,
        local_payload: Optional[str],
        conflict_data: Optional[str],
        strategy: Optional[ResolutionStrategy] = None
    ) -> str:
        """
        Resolve a conflict using the specified strategy.

        Args:
            local_payload: JSON string of local data.
            conflict_data: JSON string containing conflict details.
            strategy: Resolution strategy to use.

        Returns:
            JSON string of resolved data.
        """
        strategy = strategy or self._default_strategy

        local_data = json.loads(local_payload) if local_payload else {}
        conflict_info = json.loads(conflict_data) if conflict_data else {}
        remote_data = conflict_info.get('remote', {})

        if strategy == ResolutionStrategy.LOCAL_WINS:
            resolved = local_data
        elif strategy == ResolutionStrategy.REMOTE_WINS:
            resolved = remote_data
        elif strategy == ResolutionStrategy.LAST_WRITE_WINS:
            resolved = self._resolve_last_write_wins(local_data, remote_data)
        elif strategy == ResolutionStrategy.FIRST_WRITE_WINS:
            resolved = self._resolve_first_write_wins(local_data, remote_data)
        elif strategy == ResolutionStrategy.MERGE:
            resolved = self._resolve_merge(local_data, remote_data)
        else:
            resolved = local_data

        return json.dumps(resolved)

    def resolve_conflict(
        self,
        conflict: ConflictDetails,
        strategy: Optional[ResolutionStrategy] = None
    ) -> ResolutionResult:
        """
        Resolve a conflict and return detailed result.

        Args:
            conflict: Details of the conflict.
            strategy: Resolution strategy to use.

        Returns:
            ResolutionResult with resolved data and details.
        """
        strategy = strategy or conflict.suggested_strategy

        # Check for custom handler
        if conflict.entity_type in self._custom_handlers:
            try:
                return self._custom_handlers[conflict.entity_type](conflict)
            except Exception as e:
                logger.error(f"Custom handler failed: {e}")
                return ResolutionResult(
                    success=False,
                    error_message=f"Custom handler error: {e}"
                )

        try:
            if strategy == ResolutionStrategy.LOCAL_WINS:
                resolved, changes = self._apply_local_wins(conflict)
            elif strategy == ResolutionStrategy.REMOTE_WINS:
                resolved, changes = self._apply_remote_wins(conflict)
            elif strategy == ResolutionStrategy.LAST_WRITE_WINS:
                resolved, changes = self._apply_last_write_wins(conflict)
            elif strategy == ResolutionStrategy.FIRST_WRITE_WINS:
                resolved, changes = self._apply_first_write_wins(conflict)
            elif strategy == ResolutionStrategy.MERGE:
                resolved, changes = self._apply_merge(conflict)
            elif strategy == ResolutionStrategy.MANUAL:
                return ResolutionResult(
                    success=False,
                    error_message="Manual resolution required"
                )
            else:
                return ResolutionResult(
                    success=False,
                    error_message=f"Unknown strategy: {strategy}"
                )

            return ResolutionResult(
                success=True,
                resolved_data=resolved,
                strategy_used=strategy,
                changes_made=changes
            )

        except Exception as e:
            logger.error(f"Resolution failed: {e}")
            return ResolutionResult(
                success=False,
                error_message=str(e)
            )

    def _apply_local_wins(
        self,
        conflict: ConflictDetails
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Apply local-wins strategy."""
        resolved = conflict.local_data.copy()
        # Update version to be higher than remote
        resolved['sync_version'] = max(
            conflict.local_version,
            conflict.remote_version
        ) + 1
        changes = [f"Kept local value for: {', '.join(conflict.field_conflicts)}"]
        return resolved, changes

    def _apply_remote_wins(
        self,
        conflict: ConflictDetails
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Apply remote-wins strategy."""
        resolved = conflict.remote_data.copy()
        resolved['sync_version'] = conflict.remote_version
        changes = [f"Applied remote value for: {', '.join(conflict.field_conflicts)}"]
        return resolved, changes

    def _apply_last_write_wins(
        self,
        conflict: ConflictDetails
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Apply last-write-wins strategy."""
        local_time = conflict.local_updated_at or datetime.min
        remote_time = conflict.remote_updated_at or datetime.min

        if local_time >= remote_time:
            return self._apply_local_wins(conflict)
        else:
            return self._apply_remote_wins(conflict)

    def _apply_first_write_wins(
        self,
        conflict: ConflictDetails
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Apply first-write-wins strategy."""
        local_time = conflict.local_updated_at or datetime.max
        remote_time = conflict.remote_updated_at or datetime.max

        if local_time <= remote_time:
            return self._apply_local_wins(conflict)
        else:
            return self._apply_remote_wins(conflict)

    def _apply_merge(
        self,
        conflict: ConflictDetails
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Apply merge strategy."""
        resolved = conflict.local_data.copy()
        changes = []

        for field in conflict.field_conflicts:
            local_value = conflict.local_data.get(field)
            remote_value = conflict.remote_data.get(field)

            # Check for custom merge rule
            if field in self._merge_rules:
                merged_value = self._merge_rules[field](local_value, remote_value)
                resolved[field] = merged_value
                changes.append(f"Merged {field} using custom rule")

            # Check for field priority
            elif field in self._field_priorities:
                if self._field_priorities[field] == 'remote':
                    resolved[field] = remote_value
                    changes.append(f"Used remote value for {field} (priority)")
                else:
                    changes.append(f"Kept local value for {field} (priority)")

            # Default: use last-write-wins for individual field
            else:
                local_time = conflict.local_updated_at or datetime.min
                remote_time = conflict.remote_updated_at or datetime.min

                if remote_time > local_time:
                    resolved[field] = remote_value
                    changes.append(f"Used remote value for {field} (newer)")
                else:
                    changes.append(f"Kept local value for {field} (newer)")

        # Update version
        resolved['sync_version'] = max(
            conflict.local_version,
            conflict.remote_version
        ) + 1

        return resolved, changes

    def _resolve_last_write_wins(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve using last-write-wins."""
        local_time = self._parse_datetime(local_data.get('updated_at'))
        remote_time = self._parse_datetime(remote_data.get('updated_at'))

        if local_time and remote_time:
            return local_data if local_time >= remote_time else remote_data
        return local_data

    def _resolve_first_write_wins(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve using first-write-wins."""
        local_time = self._parse_datetime(local_data.get('updated_at'))
        remote_time = self._parse_datetime(remote_data.get('updated_at'))

        if local_time and remote_time:
            return local_data if local_time <= remote_time else remote_data
        return remote_data

    def _resolve_merge(
        self,
        local_data: Dict[str, Any],
        remote_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve using field-by-field merge."""
        resolved = local_data.copy()

        for key, remote_value in remote_data.items():
            if key in self._field_priorities:
                if self._field_priorities[key] == 'remote':
                    resolved[key] = remote_value
            elif key not in local_data:
                resolved[key] = remote_value

        return resolved

    def get_conflict_summary(self, conflict: ConflictDetails) -> str:
        """
        Generate a human-readable summary of a conflict.

        Args:
            conflict: The conflict to summarize.

        Returns:
            A formatted string describing the conflict.
        """
        lines = [
            f"Conflict Summary for {conflict.entity_type} (ID: {conflict.entity_id})",
            f"  Type: {conflict.conflict_type.value}",
            f"  Local Version: {conflict.local_version}",
            f"  Remote Version: {conflict.remote_version}",
        ]

        if conflict.local_updated_at:
            lines.append(f"  Local Updated: {conflict.local_updated_at.isoformat()}")
        if conflict.remote_updated_at:
            lines.append(f"  Remote Updated: {conflict.remote_updated_at.isoformat()}")

        if conflict.field_conflicts:
            lines.append("  Conflicting Fields:")
            for field in conflict.field_conflicts:
                local_val = conflict.local_data.get(field)
                remote_val = conflict.remote_data.get(field)
                lines.append(f"    - {field}: local={local_val}, remote={remote_val}")

        lines.append(f"  Suggested Strategy: {conflict.suggested_strategy.value}")

        return "\n".join(lines)


class AutoResolver:
    """
    Automatic conflict resolver with configurable rules.

    Applies resolution rules automatically without user intervention.
    """

    def __init__(self, conflict_resolver: ConflictResolver):
        """
        Initialize the auto resolver.

        Args:
            conflict_resolver: The underlying conflict resolver.
        """
        self._resolver = conflict_resolver
        self._rules: List[Tuple[Callable[[ConflictDetails], bool], ResolutionStrategy]] = []

    def add_rule(
        self,
        condition: Callable[[ConflictDetails], bool],
        strategy: ResolutionStrategy
    ) -> None:
        """
        Add an automatic resolution rule.

        Args:
            condition: Function that returns True if rule applies.
            strategy: Strategy to use when rule matches.
        """
        self._rules.append((condition, strategy))

    def auto_resolve(self, conflict: ConflictDetails) -> Optional[ResolutionResult]:
        """
        Attempt to automatically resolve a conflict.

        Args:
            conflict: The conflict to resolve.

        Returns:
            ResolutionResult if auto-resolved, None if manual resolution needed.
        """
        for condition, strategy in self._rules:
            try:
                if condition(conflict):
                    logger.info(
                        f"Auto-resolving {conflict.entity_type}:{conflict.entity_id} "
                        f"with strategy {strategy.value}"
                    )
                    return self._resolver.resolve_conflict(conflict, strategy)
            except Exception as e:
                logger.error(f"Error evaluating auto-resolve rule: {e}")

        return None
