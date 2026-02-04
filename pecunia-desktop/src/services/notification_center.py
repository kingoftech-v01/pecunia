"""
Notification Center for Pecunia Desktop.

Provides a centralized notification history and management system with:
- Persistent notification storage
- Read/unread status tracking
- Filtering and searching
- Notification grouping by date
- Clear all and mark as read functionality
"""

import json
import logging
import threading
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda *args: None

from services.notifications import (
    NotificationType,
    NotificationCategory,
    NotificationPriority,
    Notification,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

MAX_STORED_NOTIFICATIONS = 500
DEFAULT_RETENTION_DAYS = 30
NOTIFICATION_CENTER_DB_NAME = "notification_center.db"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NotificationItem:
    """
    Represents a notification item in the notification center.

    Extends the base Notification with additional fields for
    tracking read status and persistence.
    """
    id: str
    title: str
    message: str
    notification_type: str
    category: str
    priority: int
    timestamp: datetime
    is_read: bool = False
    is_archived: bool = False
    action_url: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_notification(cls, notification: Notification) -> "NotificationItem":
        """Create a NotificationItem from a Notification object."""
        return cls(
            id=notification.id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type.value,
            category=notification.category.value,
            priority=notification.priority.value,
            timestamp=notification.timestamp,
            data=notification.data,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "category": self.category,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat(),
            "is_read": self.is_read,
            "is_archived": self.is_archived,
            "action_url": self.action_url,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationItem":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            message=data.get("message", ""),
            notification_type=data.get("notification_type", "info"),
            category=data.get("category", "general"),
            priority=data.get("priority", 1),
            timestamp=timestamp,
            is_read=data.get("is_read", False),
            is_archived=data.get("is_archived", False),
            action_url=data.get("action_url"),
            data=data.get("data", {}),
        )


@dataclass
class NotificationFilter:
    """Filters for querying notifications."""
    categories: Optional[List[str]] = None
    types: Optional[List[str]] = None
    is_read: Optional[bool] = None
    is_archived: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_text: Optional[str] = None
    limit: int = 50
    offset: int = 0


class NotificationGroup(str, Enum):
    """Notification grouping options."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    OLDER = "older"


# =============================================================================
# Notification Center Signals
# =============================================================================

if QT_AVAILABLE:
    class NotificationCenterSignals(QObject):
        """Qt signals for the notification center."""
        notification_added = pyqtSignal(object)      # NotificationItem
        notification_read = pyqtSignal(str)          # notification_id
        notification_deleted = pyqtSignal(str)       # notification_id
        all_read = pyqtSignal()
        all_cleared = pyqtSignal()
        unread_count_changed = pyqtSignal(int)       # new count


# =============================================================================
# Notification Center Storage
# =============================================================================

class NotificationStorage:
    """
    SQLite-based storage for notification history.

    Provides persistent storage with efficient querying and
    automatic cleanup of old notifications.
    """

    def __init__(self, db_path: Path):
        """
        Initialize the notification storage.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        self._lock = threading.Lock()
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create the database schema if it doesn't exist."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        notification_type TEXT NOT NULL,
                        category TEXT NOT NULL,
                        priority INTEGER DEFAULT 1,
                        timestamp TEXT NOT NULL,
                        is_read INTEGER DEFAULT 0,
                        is_archived INTEGER DEFAULT 0,
                        action_url TEXT,
                        data TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_notifications_timestamp
                    ON notifications(timestamp DESC)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_notifications_is_read
                    ON notifications(is_read)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_notifications_category
                    ON notifications(category)
                """)

                conn.commit()
                conn.close()
                logger.debug("Notification storage database initialized")

            except Exception as e:
                logger.error(f"Failed to initialize notification database: {e}")

    def add(self, item: NotificationItem) -> bool:
        """
        Add a notification to storage.

        Args:
            item: The notification item to store.

        Returns:
            True if successful.
        """
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO notifications
                    (id, title, message, notification_type, category, priority,
                     timestamp, is_read, is_archived, action_url, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.id,
                    item.title,
                    item.message,
                    item.notification_type,
                    item.category,
                    item.priority,
                    item.timestamp.isoformat(),
                    1 if item.is_read else 0,
                    1 if item.is_archived else 0,
                    item.action_url,
                    json.dumps(item.data) if item.data else None,
                ))

                conn.commit()
                conn.close()
                return True

            except Exception as e:
                logger.error(f"Failed to add notification to storage: {e}")
                return False

    def get(self, notification_id: str) -> Optional[NotificationItem]:
        """
        Get a notification by ID.

        Args:
            notification_id: The notification ID.

        Returns:
            The notification item, or None if not found.
        """
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM notifications WHERE id = ?",
                    (notification_id,)
                )
                row = cursor.fetchone()
                conn.close()

                if row:
                    return self._row_to_item(row)
                return None

            except Exception as e:
                logger.error(f"Failed to get notification: {e}")
                return None

    def query(self, filter: NotificationFilter) -> List[NotificationItem]:
        """
        Query notifications with filters.

        Args:
            filter: Query filters.

        Returns:
            List of matching notification items.
        """
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = "SELECT * FROM notifications WHERE 1=1"
                params: List[Any] = []

                if filter.categories:
                    placeholders = ",".join("?" * len(filter.categories))
                    query += f" AND category IN ({placeholders})"
                    params.extend(filter.categories)

                if filter.types:
                    placeholders = ",".join("?" * len(filter.types))
                    query += f" AND notification_type IN ({placeholders})"
                    params.extend(filter.types)

                if filter.is_read is not None:
                    query += " AND is_read = ?"
                    params.append(1 if filter.is_read else 0)

                if filter.is_archived is not None:
                    query += " AND is_archived = ?"
                    params.append(1 if filter.is_archived else 0)

                if filter.start_date:
                    query += " AND timestamp >= ?"
                    params.append(filter.start_date.isoformat())

                if filter.end_date:
                    query += " AND timestamp <= ?"
                    params.append(filter.end_date.isoformat())

                if filter.search_text:
                    query += " AND (title LIKE ? OR message LIKE ?)"
                    search_pattern = f"%{filter.search_text}%"
                    params.extend([search_pattern, search_pattern])

                query += " ORDER BY timestamp DESC"
                query += f" LIMIT ? OFFSET ?"
                params.extend([filter.limit, filter.offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()

                return [self._row_to_item(row) for row in rows]

            except Exception as e:
                logger.error(f"Failed to query notifications: {e}")
                return []

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE notifications SET is_read = 1 WHERE id = ?",
                    (notification_id,)
                )
                conn.commit()
                affected = cursor.rowcount
                conn.close()

                return affected > 0

            except Exception as e:
                logger.error(f"Failed to mark notification as read: {e}")
                return False

    def mark_all_as_read(self) -> int:
        """Mark all notifications as read. Returns count of affected."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                cursor.execute("UPDATE notifications SET is_read = 1 WHERE is_read = 0")
                conn.commit()
                affected = cursor.rowcount
                conn.close()

                return affected

            except Exception as e:
                logger.error(f"Failed to mark all notifications as read: {e}")
                return 0

    def delete(self, notification_id: str) -> bool:
        """Delete a notification."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                cursor.execute(
                    "DELETE FROM notifications WHERE id = ?",
                    (notification_id,)
                )
                conn.commit()
                affected = cursor.rowcount
                conn.close()

                return affected > 0

            except Exception as e:
                logger.error(f"Failed to delete notification: {e}")
                return False

    def delete_all(self, archived_only: bool = False) -> int:
        """Delete all notifications. Returns count of deleted."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                if archived_only:
                    cursor.execute("DELETE FROM notifications WHERE is_archived = 1")
                else:
                    cursor.execute("DELETE FROM notifications")

                conn.commit()
                affected = cursor.rowcount
                conn.close()

                return affected

            except Exception as e:
                logger.error(f"Failed to delete all notifications: {e}")
                return 0

    def get_unread_count(self) -> int:
        """Get the count of unread notifications."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT COUNT(*) FROM notifications WHERE is_read = 0"
                )
                count = cursor.fetchone()[0]
                conn.close()

                return count

            except Exception as e:
                logger.error(f"Failed to get unread count: {e}")
                return 0

    def get_count(self, filter: Optional[NotificationFilter] = None) -> int:
        """Get total notification count with optional filter."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                query = "SELECT COUNT(*) FROM notifications WHERE 1=1"
                params: List[Any] = []

                if filter:
                    if filter.is_read is not None:
                        query += " AND is_read = ?"
                        params.append(1 if filter.is_read else 0)

                    if filter.is_archived is not None:
                        query += " AND is_archived = ?"
                        params.append(1 if filter.is_archived else 0)

                cursor.execute(query, params)
                count = cursor.fetchone()[0]
                conn.close()

                return count

            except Exception as e:
                logger.error(f"Failed to get notification count: {e}")
                return 0

    def cleanup_old(self, days: int = DEFAULT_RETENTION_DAYS) -> int:
        """Delete notifications older than specified days."""
        with self._lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()

                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(
                    "DELETE FROM notifications WHERE timestamp < ? AND is_read = 1",
                    (cutoff,)
                )
                conn.commit()
                affected = cursor.rowcount
                conn.close()

                logger.info(f"Cleaned up {affected} old notifications")
                return affected

            except Exception as e:
                logger.error(f"Failed to cleanup old notifications: {e}")
                return 0

    def _row_to_item(self, row: sqlite3.Row) -> NotificationItem:
        """Convert a database row to a NotificationItem."""
        data = {}
        if row["data"]:
            try:
                data = json.loads(row["data"])
            except json.JSONDecodeError:
                pass

        return NotificationItem(
            id=row["id"],
            title=row["title"],
            message=row["message"],
            notification_type=row["notification_type"],
            category=row["category"],
            priority=row["priority"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            is_read=bool(row["is_read"]),
            is_archived=bool(row["is_archived"]),
            action_url=row["action_url"],
            data=data,
        )


# =============================================================================
# Notification Center
# =============================================================================

class NotificationCenter:
    """
    Central notification management and history service.

    Provides:
    - Notification storage and retrieval
    - Read/unread status tracking
    - Filtering and grouping
    - Persistence across sessions
    - Do Not Disturb mode
    """

    _instance: Optional["NotificationCenter"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the notification center.

        Args:
            data_dir: Directory for storing notification database.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        # Determine data directory
        if data_dir is None:
            try:
                from config import get_data_dir
                data_dir = get_data_dir()
            except ImportError:
                data_dir = Path.home() / ".pecunia"
                data_dir.mkdir(parents=True, exist_ok=True)

        self._data_dir = data_dir
        self._db_path = data_dir / NOTIFICATION_CENTER_DB_NAME

        # Initialize storage
        self._storage = NotificationStorage(self._db_path)

        # Do Not Disturb settings
        self._dnd_enabled = False
        self._dnd_start_hour = 22
        self._dnd_end_hour = 7

        # Callbacks
        self._on_notification_added: List[Callable[[NotificationItem], None]] = []
        self._on_unread_count_changed: List[Callable[[int], None]] = []

        # Qt signals
        if QT_AVAILABLE:
            self._signals = NotificationCenterSignals()
        else:
            self._signals = None

        self._initialized = True
        logger.info("NotificationCenter initialized")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def signals(self) -> Optional[Any]:
        """Get the Qt signals object."""
        return self._signals

    @property
    def unread_count(self) -> int:
        """Get the number of unread notifications."""
        return self._storage.get_unread_count()

    @property
    def total_count(self) -> int:
        """Get the total number of notifications."""
        return self._storage.get_count()

    @property
    def dnd_enabled(self) -> bool:
        """Check if Do Not Disturb is enabled."""
        return self._dnd_enabled

    # =========================================================================
    # Notification Management
    # =========================================================================

    def add(self, notification: Notification) -> NotificationItem:
        """
        Add a notification to the center.

        Args:
            notification: The notification to add.

        Returns:
            The created NotificationItem.
        """
        item = NotificationItem.from_notification(notification)

        if self._storage.add(item):
            # Emit signals
            if self._signals:
                self._signals.notification_added.emit(item)
                self._signals.unread_count_changed.emit(self.unread_count)

            # Call callbacks
            for callback in self._on_notification_added:
                try:
                    callback(item)
                except Exception as e:
                    logger.error(f"Error in notification added callback: {e}")

            for callback in self._on_unread_count_changed:
                try:
                    callback(self.unread_count)
                except Exception as e:
                    logger.error(f"Error in unread count callback: {e}")

            logger.debug(f"Notification added to center: {item.id}")

        return item

    def add_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        category: str = "general",
        priority: int = 1,
        data: Optional[Dict[str, Any]] = None
    ) -> NotificationItem:
        """
        Add a notification directly by parameters.

        Args:
            title: Notification title.
            message: Notification message.
            notification_type: Type of notification.
            category: Notification category.
            priority: Priority level.
            data: Additional data.

        Returns:
            The created NotificationItem.
        """
        item = NotificationItem(
            id=datetime.now().strftime("%Y%m%d%H%M%S%f"),
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            priority=priority,
            timestamp=datetime.now(),
            data=data or {},
        )

        if self._storage.add(item):
            if self._signals:
                self._signals.notification_added.emit(item)
                self._signals.unread_count_changed.emit(self.unread_count)

        return item

    def get(self, notification_id: str) -> Optional[NotificationItem]:
        """Get a notification by ID."""
        return self._storage.get(notification_id)

    def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False
    ) -> List[NotificationItem]:
        """
        Get all notifications.

        Args:
            limit: Maximum number to return.
            offset: Pagination offset.
            unread_only: Only return unread notifications.

        Returns:
            List of notification items.
        """
        filter = NotificationFilter(
            limit=limit,
            offset=offset,
            is_read=False if unread_only else None,
            is_archived=False,
        )
        return self._storage.query(filter)

    def query(self, filter: NotificationFilter) -> List[NotificationItem]:
        """Query notifications with custom filter."""
        return self._storage.query(filter)

    def get_grouped(self) -> Dict[NotificationGroup, List[NotificationItem]]:
        """
        Get notifications grouped by time period.

        Returns:
            Dictionary of notification groups.
        """
        all_items = self.get_all(limit=200)
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        groups: Dict[NotificationGroup, List[NotificationItem]] = {
            NotificationGroup.TODAY: [],
            NotificationGroup.YESTERDAY: [],
            NotificationGroup.THIS_WEEK: [],
            NotificationGroup.THIS_MONTH: [],
            NotificationGroup.OLDER: [],
        }

        for item in all_items:
            if item.timestamp >= today_start:
                groups[NotificationGroup.TODAY].append(item)
            elif item.timestamp >= yesterday_start:
                groups[NotificationGroup.YESTERDAY].append(item)
            elif item.timestamp >= week_start:
                groups[NotificationGroup.THIS_WEEK].append(item)
            elif item.timestamp >= month_start:
                groups[NotificationGroup.THIS_MONTH].append(item)
            else:
                groups[NotificationGroup.OLDER].append(item)

        return groups

    def get_by_category(self, category: str) -> List[NotificationItem]:
        """Get notifications by category."""
        filter = NotificationFilter(
            categories=[category],
            is_archived=False,
        )
        return self._storage.query(filter)

    # =========================================================================
    # Read Status Management
    # =========================================================================

    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: The notification ID.

        Returns:
            True if successful.
        """
        if self._storage.mark_as_read(notification_id):
            if self._signals:
                self._signals.notification_read.emit(notification_id)
                self._signals.unread_count_changed.emit(self.unread_count)

            for callback in self._on_unread_count_changed:
                try:
                    callback(self.unread_count)
                except Exception as e:
                    logger.error(f"Error in unread count callback: {e}")

            return True
        return False

    def mark_all_as_read(self) -> int:
        """
        Mark all notifications as read.

        Returns:
            Number of notifications marked as read.
        """
        count = self._storage.mark_all_as_read()

        if count > 0:
            if self._signals:
                self._signals.all_read.emit()
                self._signals.unread_count_changed.emit(0)

            for callback in self._on_unread_count_changed:
                try:
                    callback(0)
                except Exception as e:
                    logger.error(f"Error in unread count callback: {e}")

        return count

    # =========================================================================
    # Deletion
    # =========================================================================

    def delete(self, notification_id: str) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: The notification ID.

        Returns:
            True if successful.
        """
        if self._storage.delete(notification_id):
            if self._signals:
                self._signals.notification_deleted.emit(notification_id)
                self._signals.unread_count_changed.emit(self.unread_count)

            return True
        return False

    def clear_all(self) -> int:
        """
        Clear all notifications.

        Returns:
            Number of notifications deleted.
        """
        count = self._storage.delete_all()

        if count > 0:
            if self._signals:
                self._signals.all_cleared.emit()
                self._signals.unread_count_changed.emit(0)

            for callback in self._on_unread_count_changed:
                try:
                    callback(0)
                except Exception as e:
                    logger.error(f"Error in unread count callback: {e}")

        logger.info(f"Cleared {count} notifications")
        return count

    def cleanup(self, days: int = DEFAULT_RETENTION_DAYS) -> int:
        """
        Clean up old notifications.

        Args:
            days: Delete read notifications older than this many days.

        Returns:
            Number of notifications deleted.
        """
        return self._storage.cleanup_old(days)

    # =========================================================================
    # Do Not Disturb
    # =========================================================================

    def set_dnd(
        self,
        enabled: bool,
        start_hour: Optional[int] = None,
        end_hour: Optional[int] = None
    ) -> None:
        """
        Set Do Not Disturb settings.

        Args:
            enabled: Whether DND is enabled.
            start_hour: DND start hour (0-23).
            end_hour: DND end hour (0-23).
        """
        self._dnd_enabled = enabled

        if start_hour is not None:
            self._dnd_start_hour = max(0, min(23, start_hour))

        if end_hour is not None:
            self._dnd_end_hour = max(0, min(23, end_hour))

        logger.debug(f"DND settings updated: enabled={enabled}, "
                     f"hours={self._dnd_start_hour}-{self._dnd_end_hour}")

    def is_dnd_active(self) -> bool:
        """
        Check if Do Not Disturb is currently active.

        Returns:
            True if DND is active right now.
        """
        if not self._dnd_enabled:
            return False

        current_hour = datetime.now().hour
        start = self._dnd_start_hour
        end = self._dnd_end_hour

        if start <= end:
            return start <= current_hour < end
        else:
            # DND spans midnight (e.g., 22:00 - 07:00)
            return current_hour >= start or current_hour < end

    # =========================================================================
    # Callbacks
    # =========================================================================

    def on_notification_added(
        self,
        callback: Callable[[NotificationItem], None]
    ) -> None:
        """Register a callback for when notifications are added."""
        self._on_notification_added.append(callback)

    def on_unread_count_changed(self, callback: Callable[[int], None]) -> None:
        """Register a callback for when unread count changes."""
        self._on_unread_count_changed.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a registered callback."""
        if callback in self._on_notification_added:
            self._on_notification_added.remove(callback)
        if callback in self._on_unread_count_changed:
            self._on_unread_count_changed.remove(callback)

    # =========================================================================
    # Export/Import
    # =========================================================================

    def export_to_json(self, path: Path) -> bool:
        """
        Export all notifications to a JSON file.

        Args:
            path: Path to save the JSON file.

        Returns:
            True if successful.
        """
        try:
            items = self.get_all(limit=MAX_STORED_NOTIFICATIONS)
            data = [item.to_dict() for item in items]

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(items)} notifications to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export notifications: {e}")
            return False

    def import_from_json(self, path: Path) -> int:
        """
        Import notifications from a JSON file.

        Args:
            path: Path to the JSON file.

        Returns:
            Number of notifications imported.
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            count = 0
            for item_data in data:
                item = NotificationItem.from_dict(item_data)
                if self._storage.add(item):
                    count += 1

            if self._signals:
                self._signals.unread_count_changed.emit(self.unread_count)

            logger.info(f"Imported {count} notifications from {path}")
            return count

        except Exception as e:
            logger.error(f"Failed to import notifications: {e}")
            return 0


# =============================================================================
# Global Instance Access
# =============================================================================

_notification_center: Optional[NotificationCenter] = None


def get_notification_center(data_dir: Optional[Path] = None) -> NotificationCenter:
    """Get the global notification center instance."""
    global _notification_center
    if _notification_center is None:
        _notification_center = NotificationCenter(data_dir)
    return _notification_center


__all__ = [
    # Data classes
    "NotificationItem",
    "NotificationFilter",

    # Enums
    "NotificationGroup",

    # Classes
    "NotificationStorage",
    "NotificationCenter",

    # Functions
    "get_notification_center",

    # Constants
    "MAX_STORED_NOTIFICATIONS",
    "DEFAULT_RETENTION_DAYS",
]
