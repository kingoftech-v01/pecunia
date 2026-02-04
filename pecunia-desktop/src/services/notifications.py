"""
Notification Service for Pecunia Desktop.

Provides a comprehensive notification system with:
- System tray notifications using plyer
- In-app toast notifications (QWidget overlay)
- Notification types: info, success, warning, error
- Budget alert notifications
- Sync status notifications
- Notification queue management
- Settings for notification preferences
"""

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Deque
from queue import Queue, Empty

# Qt imports with graceful fallback
try:
    from PyQt6.QtWidgets import (
        QWidget, QLabel, QVBoxLayout, QHBoxLayout,
        QPushButton, QGraphicsOpacityEffect, QApplication
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve,
        QPoint, pyqtSignal, QObject
    )
    from PyQt6.QtGui import QFont, QColor, QPalette
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QWidget = object
    QObject = object
    pyqtSignal = lambda *args: None

# Plyer for system notifications (cross-platform)
try:
    from plyer import notification as system_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    system_notification = None

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class NotificationType(str, Enum):
    """Type of notification determining its appearance and urgency."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationPriority(int, Enum):
    """Priority level for notification queue ordering."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class NotificationCategory(str, Enum):
    """Category for filtering and grouping notifications."""
    GENERAL = "general"
    BUDGET = "budget"
    TRANSACTION = "transaction"
    SYNC = "sync"
    SECURITY = "security"
    SYSTEM = "system"


# Default notification display durations (milliseconds)
DEFAULT_DURATIONS = {
    NotificationType.INFO: 4000,
    NotificationType.SUCCESS: 3000,
    NotificationType.WARNING: 5000,
    NotificationType.ERROR: 7000,
}

# Notification style colors
NOTIFICATION_COLORS = {
    NotificationType.INFO: {
        "background": "#3498db",
        "text": "#ffffff",
        "icon": "info"
    },
    NotificationType.SUCCESS: {
        "background": "#27ae60",
        "text": "#ffffff",
        "icon": "check"
    },
    NotificationType.WARNING: {
        "background": "#f39c12",
        "text": "#ffffff",
        "icon": "warning"
    },
    NotificationType.ERROR: {
        "background": "#e74c3c",
        "text": "#ffffff",
        "icon": "error"
    },
}

# Maximum notifications in history
MAX_NOTIFICATION_HISTORY = 100


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Notification:
    """Represents a notification to be displayed."""
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    category: NotificationCategory = NotificationCategory.GENERAL
    priority: NotificationPriority = NotificationPriority.NORMAL
    duration_ms: Optional[int] = None
    dismissible: bool = True
    action_text: Optional[str] = None
    action_callback: Optional[Callable[[], None]] = None
    icon_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    data: Dict[str, Any] = field(default_factory=dict)

    def get_duration(self) -> int:
        """Get the notification duration in milliseconds."""
        if self.duration_ms is not None:
            return self.duration_ms
        return DEFAULT_DURATIONS.get(self.notification_type, 4000)


@dataclass
class NotificationPreferences:
    """User preferences for notifications."""
    enabled: bool = True
    system_notifications_enabled: bool = True
    in_app_notifications_enabled: bool = True
    sound_enabled: bool = True

    # Category-specific settings
    budget_alerts: bool = True
    transaction_alerts: bool = True
    sync_alerts: bool = False
    security_alerts: bool = True

    # Budget alert thresholds
    budget_warning_threshold: int = 80  # Percentage
    budget_critical_threshold: int = 95  # Percentage

    # Do not disturb
    do_not_disturb: bool = False
    dnd_start_hour: int = 22  # 10 PM
    dnd_end_hour: int = 7     # 7 AM

    # Display settings
    max_visible_toasts: int = 3
    toast_position: str = "top-right"  # top-right, top-left, bottom-right, bottom-left


# =============================================================================
# Toast Notification Widget (In-App)
# =============================================================================

if QT_AVAILABLE:
    class ToastNotification(QWidget):
        """
        A toast notification widget that appears as an overlay.

        Displays notifications with animations for show/hide transitions.
        """

        closed = pyqtSignal(str)  # Emits notification ID when closed
        action_triggered = pyqtSignal(str)  # Emits notification ID when action clicked

        def __init__(
            self,
            notification: Notification,
            parent: Optional[QWidget] = None
        ):
            """
            Initialize the toast notification.

            Args:
                notification: The notification data to display.
                parent: Parent widget.
            """
            super().__init__(parent)
            self.notification = notification
            self._setup_ui()
            self._setup_animations()
            self._setup_timer()

        def _setup_ui(self) -> None:
            """Set up the toast UI components."""
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setFixedWidth(350)

            # Get colors for notification type
            colors = NOTIFICATION_COLORS.get(
                self.notification.notification_type,
                NOTIFICATION_COLORS[NotificationType.INFO]
            )

            # Main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)

            # Content container
            self.container = QWidget()
            self.container.setStyleSheet(f"""
                QWidget {{
                    background-color: {colors['background']};
                    border-radius: 8px;
                    padding: 12px;
                }}
                QLabel {{
                    color: {colors['text']};
                    background: transparent;
                }}
                QPushButton {{
                    color: {colors['text']};
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.3);
                }}
            """)

            container_layout = QVBoxLayout(self.container)
            container_layout.setSpacing(8)

            # Header with title and close button
            header_layout = QHBoxLayout()
            header_layout.setSpacing(8)

            # Title
            self.title_label = QLabel(self.notification.title)
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(11)
            self.title_label.setFont(title_font)
            header_layout.addWidget(self.title_label, 1)

            # Close button
            if self.notification.dismissible:
                close_btn = QPushButton("x")
                close_btn.setFixedSize(24, 24)
                close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                close_btn.clicked.connect(self._on_close)
                header_layout.addWidget(close_btn)

            container_layout.addLayout(header_layout)

            # Message
            self.message_label = QLabel(self.notification.message)
            self.message_label.setWordWrap(True)
            message_font = QFont()
            message_font.setPointSize(10)
            self.message_label.setFont(message_font)
            container_layout.addWidget(self.message_label)

            # Action button (if provided)
            if self.notification.action_text:
                action_btn = QPushButton(self.notification.action_text)
                action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                action_btn.clicked.connect(self._on_action)
                container_layout.addWidget(action_btn)

            main_layout.addWidget(self.container)

            # Apply opacity effect for animations
            self.opacity_effect = QGraphicsOpacityEffect(self)
            self.opacity_effect.setOpacity(0.0)
            self.setGraphicsEffect(self.opacity_effect)

        def _setup_animations(self) -> None:
            """Set up show/hide animations."""
            # Fade in animation
            self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_in.setDuration(200)
            self.fade_in.setStartValue(0.0)
            self.fade_in.setEndValue(1.0)
            self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

            # Fade out animation
            self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.fade_out.setDuration(200)
            self.fade_out.setStartValue(1.0)
            self.fade_out.setEndValue(0.0)
            self.fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
            self.fade_out.finished.connect(self._on_fade_out_complete)

        def _setup_timer(self) -> None:
            """Set up auto-close timer."""
            self.close_timer = QTimer(self)
            self.close_timer.setSingleShot(True)
            self.close_timer.timeout.connect(self.fade_out_and_close)

        def show_animated(self) -> None:
            """Show the toast with fade-in animation."""
            self.show()
            self.fade_in.start()
            duration = self.notification.get_duration()
            if duration > 0:
                self.close_timer.start(duration)

        def fade_out_and_close(self) -> None:
            """Start fade-out animation before closing."""
            self.close_timer.stop()
            self.fade_out.start()

        def _on_fade_out_complete(self) -> None:
            """Handle fade-out completion."""
            self.hide()
            self.closed.emit(self.notification.id)
            self.deleteLater()

        def _on_close(self) -> None:
            """Handle close button click."""
            self.fade_out_and_close()

        def _on_action(self) -> None:
            """Handle action button click."""
            self.action_triggered.emit(self.notification.id)
            if self.notification.action_callback:
                try:
                    self.notification.action_callback()
                except Exception as e:
                    logger.error(f"Error in notification action callback: {e}")
            self.fade_out_and_close()

        def enterEvent(self, event) -> None:
            """Pause auto-close timer on mouse enter."""
            self.close_timer.stop()
            super().enterEvent(event)

        def leaveEvent(self, event) -> None:
            """Resume auto-close timer on mouse leave."""
            duration = self.notification.get_duration()
            if duration > 0:
                self.close_timer.start(duration)
            super().leaveEvent(event)


# =============================================================================
# Notification Manager (Qt Signals Bridge)
# =============================================================================

if QT_AVAILABLE:
    class NotificationSignals(QObject):
        """Qt signals for cross-thread notification handling."""
        show_toast = pyqtSignal(object)  # Notification
        show_system = pyqtSignal(object)  # Notification
        remove_toast = pyqtSignal(str)    # notification_id


# =============================================================================
# Notification Service
# =============================================================================

class NotificationService:
    """
    Central service for managing all application notifications.

    Handles both system tray notifications and in-app toast notifications,
    with support for queuing, preferences, and notification history.
    """

    _instance: Optional["NotificationService"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        parent_widget: Optional[Any] = None,
        preferences: Optional[NotificationPreferences] = None
    ):
        """
        Initialize the notification service.

        Args:
            parent_widget: Parent widget for toast notifications.
            preferences: User notification preferences.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._parent_widget = parent_widget
        self._preferences = preferences or NotificationPreferences()

        # Notification queue and history
        self._queue: Queue[Notification] = Queue()
        self._history: Deque[Notification] = deque(maxlen=MAX_NOTIFICATION_HISTORY)

        # Active toasts
        self._active_toasts: Dict[str, Any] = {}  # notification_id -> ToastNotification

        # Callbacks
        self._on_notification: List[Callable[[Notification], None]] = []
        self._on_action: List[Callable[[str], None]] = []

        # Qt signals for thread-safe UI updates
        if QT_AVAILABLE:
            self._signals = NotificationSignals()
            self._signals.show_toast.connect(self._handle_show_toast)
            self._signals.show_system.connect(self._handle_show_system)
            self._signals.remove_toast.connect(self._handle_remove_toast)

        # Queue processing
        self._processing = False
        self._process_lock = threading.Lock()

        self._initialized = True
        logger.info("NotificationService initialized")

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_parent_widget(self, widget: Any) -> None:
        """Set the parent widget for toast notifications."""
        self._parent_widget = widget

    def set_preferences(self, preferences: NotificationPreferences) -> None:
        """Update notification preferences."""
        self._preferences = preferences
        logger.debug("Notification preferences updated")

    def get_preferences(self) -> NotificationPreferences:
        """Get current notification preferences."""
        return self._preferences

    def update_preference(self, key: str, value: Any) -> None:
        """Update a single preference value."""
        if hasattr(self._preferences, key):
            setattr(self._preferences, key, value)
            logger.debug(f"Notification preference '{key}' updated to {value}")

    # =========================================================================
    # Notification Methods
    # =========================================================================

    def notify(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        category: NotificationCategory = NotificationCategory.GENERAL,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        duration_ms: Optional[int] = None,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
        system_only: bool = False,
        toast_only: bool = False,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Show a notification.

        Args:
            title: Notification title.
            message: Notification message.
            notification_type: Type of notification (info, success, warning, error).
            category: Category for filtering.
            priority: Priority level.
            duration_ms: Custom duration in milliseconds.
            action_text: Optional action button text.
            action_callback: Callback when action is clicked.
            system_only: Only show system notification, not toast.
            toast_only: Only show toast notification, not system.
            data: Additional data to attach to notification.

        Returns:
            Notification ID if shown, None otherwise.
        """
        if not self._should_show_notification(category):
            return None

        notification = Notification(
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            priority=priority,
            duration_ms=duration_ms,
            action_text=action_text,
            action_callback=action_callback,
            data=data or {}
        )

        # Add to history
        self._history.append(notification)

        # Notify callbacks
        for callback in self._on_notification:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

        # Show notifications based on preferences and flags
        shown = False

        if not toast_only and self._preferences.system_notifications_enabled:
            self._show_system_notification(notification)
            shown = True

        if not system_only and self._preferences.in_app_notifications_enabled:
            self._queue_toast_notification(notification)
            shown = True

        return notification.id if shown else None

    def info(self, title: str, message: str, **kwargs) -> Optional[str]:
        """Show an info notification."""
        return self.notify(title, message, NotificationType.INFO, **kwargs)

    def success(self, title: str, message: str, **kwargs) -> Optional[str]:
        """Show a success notification."""
        return self.notify(title, message, NotificationType.SUCCESS, **kwargs)

    def warning(self, title: str, message: str, **kwargs) -> Optional[str]:
        """Show a warning notification."""
        return self.notify(title, message, NotificationType.WARNING, **kwargs)

    def error(self, title: str, message: str, **kwargs) -> Optional[str]:
        """Show an error notification."""
        return self.notify(title, message, NotificationType.ERROR, **kwargs)

    # =========================================================================
    # Specialized Notifications
    # =========================================================================

    def notify_budget_warning(
        self,
        budget_name: str,
        spent_amount: float,
        budget_amount: float,
        currency: str = "USD"
    ) -> Optional[str]:
        """
        Show a budget warning notification.

        Args:
            budget_name: Name of the budget category.
            spent_amount: Amount spent.
            budget_amount: Total budget amount.
            currency: Currency code.

        Returns:
            Notification ID if shown.
        """
        if not self._preferences.budget_alerts:
            return None

        percentage = (spent_amount / budget_amount * 100) if budget_amount > 0 else 0
        remaining = budget_amount - spent_amount

        if percentage >= self._preferences.budget_critical_threshold:
            notification_type = NotificationType.ERROR
            title = f"Budget Critical: {budget_name}"
            message = f"You've spent {percentage:.0f}% of your budget. Only {currency} {remaining:.2f} remaining."
        elif percentage >= self._preferences.budget_warning_threshold:
            notification_type = NotificationType.WARNING
            title = f"Budget Warning: {budget_name}"
            message = f"You've spent {percentage:.0f}% of your budget. {currency} {remaining:.2f} remaining."
        else:
            return None

        return self.notify(
            title=title,
            message=message,
            notification_type=notification_type,
            category=NotificationCategory.BUDGET,
            priority=NotificationPriority.HIGH,
            data={
                "budget_name": budget_name,
                "spent_amount": spent_amount,
                "budget_amount": budget_amount,
                "percentage": percentage
            }
        )

    def notify_budget_exceeded(
        self,
        budget_name: str,
        over_amount: float,
        currency: str = "USD"
    ) -> Optional[str]:
        """
        Show a budget exceeded notification.

        Args:
            budget_name: Name of the budget category.
            over_amount: Amount over budget.
            currency: Currency code.

        Returns:
            Notification ID if shown.
        """
        if not self._preferences.budget_alerts:
            return None

        return self.notify(
            title=f"Budget Exceeded: {budget_name}",
            message=f"You are {currency} {over_amount:.2f} over budget!",
            notification_type=NotificationType.ERROR,
            category=NotificationCategory.BUDGET,
            priority=NotificationPriority.URGENT,
            data={
                "budget_name": budget_name,
                "over_amount": over_amount
            }
        )

    def notify_sync_started(self) -> Optional[str]:
        """Show a sync started notification."""
        if not self._preferences.sync_alerts:
            return None

        return self.notify(
            title="Sync Started",
            message="Synchronizing your data...",
            notification_type=NotificationType.INFO,
            category=NotificationCategory.SYNC,
            priority=NotificationPriority.LOW,
            duration_ms=2000,
            toast_only=True
        )

    def notify_sync_completed(
        self,
        synced_count: int,
        failed_count: int = 0,
        duration_ms: int = 0
    ) -> Optional[str]:
        """
        Show a sync completed notification.

        Args:
            synced_count: Number of items synced.
            failed_count: Number of failed items.
            duration_ms: Sync duration in milliseconds.

        Returns:
            Notification ID if shown.
        """
        if not self._preferences.sync_alerts:
            return None

        if failed_count > 0:
            notification_type = NotificationType.WARNING
            title = "Sync Completed with Errors"
            message = f"Synced {synced_count} items. {failed_count} items failed."
        else:
            notification_type = NotificationType.SUCCESS
            title = "Sync Completed"
            message = f"Successfully synced {synced_count} items."

        if duration_ms > 0:
            duration_sec = duration_ms / 1000
            message += f" ({duration_sec:.1f}s)"

        return self.notify(
            title=title,
            message=message,
            notification_type=notification_type,
            category=NotificationCategory.SYNC,
            priority=NotificationPriority.LOW,
            data={
                "synced_count": synced_count,
                "failed_count": failed_count,
                "duration_ms": duration_ms
            }
        )

    def notify_sync_failed(self, error_message: str) -> Optional[str]:
        """
        Show a sync failed notification.

        Args:
            error_message: Error description.

        Returns:
            Notification ID if shown.
        """
        if not self._preferences.sync_alerts:
            return None

        return self.notify(
            title="Sync Failed",
            message=error_message,
            notification_type=NotificationType.ERROR,
            category=NotificationCategory.SYNC,
            priority=NotificationPriority.HIGH,
            data={"error": error_message}
        )

    def notify_sync_conflict(
        self,
        conflict_count: int,
        action_callback: Optional[Callable[[], None]] = None
    ) -> Optional[str]:
        """
        Show a sync conflict notification.

        Args:
            conflict_count: Number of conflicts detected.
            action_callback: Callback to resolve conflicts.

        Returns:
            Notification ID if shown.
        """
        return self.notify(
            title="Sync Conflicts Detected",
            message=f"{conflict_count} conflict(s) need your attention.",
            notification_type=NotificationType.WARNING,
            category=NotificationCategory.SYNC,
            priority=NotificationPriority.HIGH,
            action_text="Resolve",
            action_callback=action_callback,
            data={"conflict_count": conflict_count}
        )

    def notify_new_transaction(
        self,
        description: str,
        amount: float,
        currency: str = "USD"
    ) -> Optional[str]:
        """
        Show a new transaction notification.

        Args:
            description: Transaction description.
            amount: Transaction amount.
            currency: Currency code.

        Returns:
            Notification ID if shown.
        """
        if not self._preferences.transaction_alerts:
            return None

        sign = "-" if amount < 0 else "+"
        abs_amount = abs(amount)

        return self.notify(
            title="New Transaction",
            message=f"{description}: {sign}{currency} {abs_amount:.2f}",
            notification_type=NotificationType.INFO,
            category=NotificationCategory.TRANSACTION,
            priority=NotificationPriority.NORMAL,
            data={
                "description": description,
                "amount": amount
            }
        )

    def notify_security_alert(
        self,
        title: str,
        message: str,
        action_callback: Optional[Callable[[], None]] = None
    ) -> Optional[str]:
        """
        Show a security alert notification.

        Args:
            title: Alert title.
            message: Alert message.
            action_callback: Action callback.

        Returns:
            Notification ID if shown.
        """
        if not self._preferences.security_alerts:
            return None

        return self.notify(
            title=title,
            message=message,
            notification_type=NotificationType.ERROR,
            category=NotificationCategory.SECURITY,
            priority=NotificationPriority.URGENT,
            action_text="Review" if action_callback else None,
            action_callback=action_callback
        )

    # =========================================================================
    # Toast Management
    # =========================================================================

    def _queue_toast_notification(self, notification: Notification) -> None:
        """Add a notification to the toast queue."""
        self._queue.put(notification)
        self._process_queue()

    def _process_queue(self) -> None:
        """Process the notification queue."""
        with self._process_lock:
            if self._processing:
                return
            self._processing = True

        try:
            while (
                len(self._active_toasts) < self._preferences.max_visible_toasts and
                not self._queue.empty()
            ):
                try:
                    notification = self._queue.get_nowait()
                    if QT_AVAILABLE:
                        self._signals.show_toast.emit(notification)
                except Empty:
                    break
        finally:
            with self._process_lock:
                self._processing = False

    def _handle_show_toast(self, notification: Notification) -> None:
        """Handle showing a toast notification (Qt main thread)."""
        if not QT_AVAILABLE or self._parent_widget is None:
            logger.warning("Cannot show toast: Qt not available or no parent widget")
            return

        toast = ToastNotification(notification, self._parent_widget)
        toast.closed.connect(self._on_toast_closed)
        toast.action_triggered.connect(self._on_toast_action)

        # Position the toast
        self._position_toast(toast)

        self._active_toasts[notification.id] = toast
        toast.show_animated()

    def _position_toast(self, toast: "ToastNotification") -> None:
        """Position a toast notification based on preferences."""
        if not QT_AVAILABLE or self._parent_widget is None:
            return

        parent_rect = self._parent_widget.geometry()
        toast_width = toast.width()
        toast_height = toast.sizeHint().height()

        margin = 16
        offset = len(self._active_toasts) * (toast_height + margin)

        position = self._preferences.toast_position

        if position == "top-right":
            x = parent_rect.width() - toast_width - margin
            y = margin + offset
        elif position == "top-left":
            x = margin
            y = margin + offset
        elif position == "bottom-right":
            x = parent_rect.width() - toast_width - margin
            y = parent_rect.height() - toast_height - margin - offset
        elif position == "bottom-left":
            x = margin
            y = parent_rect.height() - toast_height - margin - offset
        else:
            x = parent_rect.width() - toast_width - margin
            y = margin + offset

        # Convert to global coordinates
        global_pos = self._parent_widget.mapToGlobal(QPoint(int(x), int(y)))
        toast.move(global_pos)

    def _on_toast_closed(self, notification_id: str) -> None:
        """Handle toast close event."""
        if QT_AVAILABLE:
            self._signals.remove_toast.emit(notification_id)
        self._process_queue()

    def _handle_remove_toast(self, notification_id: str) -> None:
        """Remove a toast from active toasts."""
        self._active_toasts.pop(notification_id, None)
        self._reposition_toasts()

    def _reposition_toasts(self) -> None:
        """Reposition all active toasts after one is removed."""
        if not QT_AVAILABLE or self._parent_widget is None:
            return

        for i, (_, toast) in enumerate(self._active_toasts.items()):
            parent_rect = self._parent_widget.geometry()
            toast_width = toast.width()
            toast_height = toast.sizeHint().height()

            margin = 16
            offset = i * (toast_height + margin)

            position = self._preferences.toast_position

            if position in ("top-right", "top-left"):
                y = margin + offset
            else:
                y = parent_rect.height() - toast_height - margin - offset

            if position in ("top-right", "bottom-right"):
                x = parent_rect.width() - toast_width - margin
            else:
                x = margin

            global_pos = self._parent_widget.mapToGlobal(QPoint(int(x), int(y)))
            toast.move(global_pos)

    def _on_toast_action(self, notification_id: str) -> None:
        """Handle toast action event."""
        for callback in self._on_action:
            try:
                callback(notification_id)
            except Exception as e:
                logger.error(f"Error in action callback: {e}")

    # =========================================================================
    # System Notifications
    # =========================================================================

    def _show_system_notification(self, notification: Notification) -> None:
        """Show a system tray notification."""
        if QT_AVAILABLE:
            self._signals.show_system.emit(notification)
        else:
            self._handle_show_system(notification)

    def _handle_show_system(self, notification: Notification) -> None:
        """Handle showing a system notification."""
        if not PLYER_AVAILABLE:
            logger.debug("Plyer not available, skipping system notification")
            return

        try:
            # Determine timeout (plyer uses seconds)
            timeout = notification.get_duration() // 1000

            system_notification.notify(
                title=notification.title,
                message=notification.message,
                app_name="Pecunia",
                app_icon=notification.icon_path,
                timeout=timeout
            )
            logger.debug(f"System notification shown: {notification.title}")
        except Exception as e:
            logger.error(f"Failed to show system notification: {e}")

    # =========================================================================
    # Preference Checks
    # =========================================================================

    def _should_show_notification(self, category: NotificationCategory) -> bool:
        """Check if a notification should be shown based on preferences."""
        if not self._preferences.enabled:
            return False

        if self._preferences.do_not_disturb and self._is_dnd_active():
            return False

        # Check category-specific settings
        category_settings = {
            NotificationCategory.BUDGET: self._preferences.budget_alerts,
            NotificationCategory.TRANSACTION: self._preferences.transaction_alerts,
            NotificationCategory.SYNC: self._preferences.sync_alerts,
            NotificationCategory.SECURITY: self._preferences.security_alerts,
        }

        return category_settings.get(category, True)

    def _is_dnd_active(self) -> bool:
        """Check if Do Not Disturb is currently active."""
        if not self._preferences.do_not_disturb:
            return False

        current_hour = datetime.now().hour
        start = self._preferences.dnd_start_hour
        end = self._preferences.dnd_end_hour

        if start <= end:
            return start <= current_hour < end
        else:
            # DND spans midnight (e.g., 22:00 - 07:00)
            return current_hour >= start or current_hour < end

    # =========================================================================
    # History and Callbacks
    # =========================================================================

    def get_history(self, limit: int = 50) -> List[Notification]:
        """
        Get notification history.

        Args:
            limit: Maximum number of notifications to return.

        Returns:
            List of recent notifications.
        """
        return list(self._history)[-limit:]

    def clear_history(self) -> None:
        """Clear notification history."""
        self._history.clear()
        logger.debug("Notification history cleared")

    def on_notification(self, callback: Callable[[Notification], None]) -> None:
        """Register a callback for all notifications."""
        self._on_notification.append(callback)

    def on_action(self, callback: Callable[[str], None]) -> None:
        """Register a callback for notification actions."""
        self._on_action.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a registered callback."""
        if callback in self._on_notification:
            self._on_notification.remove(callback)
        if callback in self._on_action:
            self._on_action.remove(callback)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def dismiss_all(self) -> None:
        """Dismiss all active toast notifications."""
        for toast in list(self._active_toasts.values()):
            if hasattr(toast, 'fade_out_and_close'):
                toast.fade_out_and_close()

    def dismiss(self, notification_id: str) -> bool:
        """
        Dismiss a specific notification.

        Args:
            notification_id: ID of the notification to dismiss.

        Returns:
            True if notification was found and dismissed.
        """
        if notification_id in self._active_toasts:
            toast = self._active_toasts[notification_id]
            if hasattr(toast, 'fade_out_and_close'):
                toast.fade_out_and_close()
            return True
        return False

    def get_active_count(self) -> int:
        """Get the number of active toast notifications."""
        return len(self._active_toasts)

    def get_queue_size(self) -> int:
        """Get the number of queued notifications."""
        return self._queue.qsize()


# =============================================================================
# Global Instance
# =============================================================================

_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def notify(
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    **kwargs
) -> Optional[str]:
    """Convenience function to show a notification."""
    return get_notification_service().notify(title, message, notification_type, **kwargs)


def notify_info(title: str, message: str, **kwargs) -> Optional[str]:
    """Convenience function to show an info notification."""
    return get_notification_service().info(title, message, **kwargs)


def notify_success(title: str, message: str, **kwargs) -> Optional[str]:
    """Convenience function to show a success notification."""
    return get_notification_service().success(title, message, **kwargs)


def notify_warning(title: str, message: str, **kwargs) -> Optional[str]:
    """Convenience function to show a warning notification."""
    return get_notification_service().warning(title, message, **kwargs)


def notify_error(title: str, message: str, **kwargs) -> Optional[str]:
    """Convenience function to show an error notification."""
    return get_notification_service().error(title, message, **kwargs)


def show_notification(
    title: str,
    message: str,
    notification_type: str = "info",
    **kwargs
) -> Optional[str]:
    """
    Show a notification with a string-based type.

    This is a convenience function that accepts notification type as a string.

    Args:
        title: Notification title.
        message: Notification message.
        notification_type: Type string (info, success, warning, error).
        **kwargs: Additional arguments passed to notify().

    Returns:
        Notification ID if shown, None otherwise.
    """
    type_map = {
        "info": NotificationType.INFO,
        "success": NotificationType.SUCCESS,
        "warning": NotificationType.WARNING,
        "error": NotificationType.ERROR,
    }
    nt = type_map.get(notification_type.lower(), NotificationType.INFO)
    return get_notification_service().notify(title, message, nt, **kwargs)


def show_system_notification(title: str, message: str, **kwargs) -> Optional[str]:
    """
    Show only a system tray notification (no in-app toast).

    Args:
        title: Notification title.
        message: Notification message.
        **kwargs: Additional arguments passed to notify().

    Returns:
        Notification ID if shown, None otherwise.
    """
    return get_notification_service().notify(
        title, message,
        system_only=True,
        **kwargs
    )


__all__ = [
    # Enums
    "NotificationType",
    "NotificationPriority",
    "NotificationCategory",

    # Data classes
    "Notification",
    "NotificationPreferences",

    # Widgets
    "ToastNotification",

    # Service
    "NotificationService",
    "get_notification_service",

    # Convenience functions
    "notify",
    "notify_info",
    "notify_success",
    "notify_warning",
    "notify_error",
    "show_notification",
    "show_system_notification",

    # Constants
    "QT_AVAILABLE",
    "PLYER_AVAILABLE",
]
