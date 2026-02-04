"""
Notification widgets for Pecunia Desktop.

Provides toast notifications, notification manager, and notification center.
"""

from typing import Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QRect, pyqtSignal, QObject, QParallelAnimationGroup
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QApplication,
    QGraphicsOpacityEffect, QSizePolicy
)
from PyQt6.QtGui import QFont, QCursor

from ..styles.theme import get_theme_manager


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class NotificationData:
    """Data class for notification information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    message: str = ""
    notification_type: NotificationType = NotificationType.INFO
    timestamp: datetime = field(default_factory=datetime.now)
    duration: int = 5000  # milliseconds
    dismissible: bool = True
    action_text: Optional[str] = None
    action_callback: Optional[Callable] = None
    read: bool = False


class ToastNotification(QFrame):
    """
    Toast notification widget with slide in/out animation.

    Displays a temporary notification that slides in from the edge
    of the screen and automatically dismisses after a timeout.

    Usage:
        toast = ToastNotification(
            title="Success",
            message="Transaction saved successfully.",
            notification_type=NotificationType.SUCCESS
        )
        toast.show()
    """

    closed = pyqtSignal(str)  # Emits notification ID
    action_clicked = pyqtSignal(str)  # Emits notification ID

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        notification_data: Optional[NotificationData] = None,
        title: str = "",
        message: str = "",
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        dismissible: bool = True,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None
    ):
        """
        Initialize toast notification.

        Args:
            parent: Parent widget
            notification_data: NotificationData object (overrides other params)
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            duration: Auto-dismiss duration in ms (0 for no auto-dismiss)
            dismissible: Whether notification can be dismissed
            action_text: Optional action button text
            action_callback: Optional action callback
        """
        super().__init__(parent)

        # Use notification data if provided
        if notification_data:
            self._data = notification_data
        else:
            self._data = NotificationData(
                title=title,
                message=message,
                notification_type=notification_type,
                duration=duration,
                dismissible=dismissible,
                action_text=action_text,
                action_callback=action_callback
            )

        self._setup_ui()
        self._setup_animations()

        # Auto-dismiss timer
        if self._data.duration > 0:
            self._dismiss_timer = QTimer(self)
            self._dismiss_timer.setSingleShot(True)
            self._dismiss_timer.timeout.connect(self.dismiss)

    def _get_type_color(self) -> str:
        """Get color based on notification type."""
        theme = get_theme_manager()
        palette = theme.current_palette

        colors = {
            NotificationType.INFO: palette.info,
            NotificationType.SUCCESS: palette.success,
            NotificationType.WARNING: palette.warning,
            NotificationType.ERROR: palette.error
        }
        return colors.get(self._data.notification_type, palette.info)

    def _get_type_icon(self) -> str:
        """Get icon based on notification type."""
        icons = {
            NotificationType.INFO: "i",
            NotificationType.SUCCESS: "\u2713",
            NotificationType.WARNING: "!",
            NotificationType.ERROR: "X"
        }
        return icons.get(self._data.notification_type, "i")

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        theme = get_theme_manager()
        palette = theme.current_palette
        type_color = self._get_type_color()

        self.setObjectName("toastNotification")
        self.setStyleSheet(f"""
            #toastNotification {{
                background-color: {palette.surface};
                border: 1px solid {palette.border};
                border-left: 4px solid {type_color};
                border-radius: 8px;
            }}
        """)
        self.setMinimumWidth(350)
        self.setMaximumWidth(400)

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel(self._get_type_icon())
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            background-color: {type_color}20;
            color: {type_color};
            border-radius: 16px;
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        # Title
        if self._data.title:
            title_label = QLabel(self._data.title)
            title_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 600;
                color: {palette.text_primary};
            """)
            content_layout.addWidget(title_label)

        # Message
        message_label = QLabel(self._data.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            font-size: 13px;
            color: {palette.text_secondary};
        """)
        content_layout.addWidget(message_label)

        # Action button
        if self._data.action_text:
            action_btn = QPushButton(self._data.action_text)
            action_btn.setFlat(True)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.setStyleSheet(f"""
                color: {type_color};
                font-weight: 500;
                padding: 4px 0;
                text-align: left;
            """)
            action_btn.clicked.connect(self._on_action)
            content_layout.addWidget(action_btn)

        layout.addLayout(content_layout, 1)

        # Close button
        if self._data.dismissible:
            close_btn = QPushButton("\u00d7")  # X symbol
            close_btn.setFixedSize(24, 24)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {palette.text_secondary};
                    border: none;
                    border-radius: 12px;
                    font-size: 18px;
                }}
                QPushButton:hover {{
                    background-color: {palette.hover};
                }}
            """)
            close_btn.clicked.connect(self.dismiss)
            layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        self.adjustSize()

    def _setup_animations(self) -> None:
        """Setup slide and fade animations."""
        # Opacity effect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        # Slide in animation
        self._slide_in_anim = QPropertyAnimation(self, b"pos")
        self._slide_in_anim.setDuration(300)
        self._slide_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade in animation
        self._fade_in_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in_anim.setDuration(200)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)

        # Combined show animation
        self._show_anim = QParallelAnimationGroup(self)
        self._show_anim.addAnimation(self._slide_in_anim)
        self._show_anim.addAnimation(self._fade_in_anim)

        # Slide out animation
        self._slide_out_anim = QPropertyAnimation(self, b"pos")
        self._slide_out_anim.setDuration(200)
        self._slide_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        # Fade out animation
        self._fade_out_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out_anim.setDuration(150)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)

        # Combined hide animation
        self._hide_anim = QParallelAnimationGroup(self)
        self._hide_anim.addAnimation(self._slide_out_anim)
        self._hide_anim.addAnimation(self._fade_out_anim)
        self._hide_anim.finished.connect(self._on_hide_finished)

    def _on_action(self) -> None:
        """Handle action button click."""
        self.action_clicked.emit(self._data.id)
        if self._data.action_callback:
            self._data.action_callback()
        self.dismiss()

    def _on_hide_finished(self) -> None:
        """Handle hide animation finished."""
        self.closed.emit(self._data.id)
        self.deleteLater()

    def show_animated(self, start_pos: QPoint, end_pos: QPoint) -> None:
        """Show with slide animation."""
        self._slide_in_anim.setStartValue(start_pos)
        self._slide_in_anim.setEndValue(end_pos)

        self.move(start_pos)
        self.show()
        self._show_anim.start()

        # Start dismiss timer
        if self._data.duration > 0:
            self._dismiss_timer.start(self._data.duration)

    def dismiss(self) -> None:
        """Dismiss the notification with animation."""
        if hasattr(self, '_dismiss_timer'):
            self._dismiss_timer.stop()

        current_pos = self.pos()
        end_pos = QPoint(current_pos.x() + 50, current_pos.y())

        self._slide_out_anim.setStartValue(current_pos)
        self._slide_out_anim.setEndValue(end_pos)

        self._hide_anim.start()

    @property
    def notification_id(self) -> str:
        """Get the notification ID."""
        return self._data.id

    def enterEvent(self, event) -> None:
        """Pause dismiss timer on hover."""
        if hasattr(self, '_dismiss_timer'):
            self._dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Resume dismiss timer on leave."""
        if hasattr(self, '_dismiss_timer') and self._data.duration > 0:
            self._dismiss_timer.start(self._data.duration)
        super().leaveEvent(event)


class NotificationManager(QObject):
    """
    Notification queue manager.

    Manages a queue of notifications and displays them in order.
    Handles positioning and stacking of multiple notifications.

    Usage:
        manager = NotificationManager(parent_widget)
        manager.show_notification(
            title="Success",
            message="Data saved.",
            notification_type=NotificationType.SUCCESS
        )
    """

    notification_added = pyqtSignal(NotificationData)
    notification_removed = pyqtSignal(str)

    _instance: Optional['NotificationManager'] = None

    def __new__(cls, parent: Optional[QWidget] = None):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize notification manager.

        Args:
            parent: Parent widget for positioning
        """
        if self._initialized:
            if parent:
                self._parent = parent
            return

        super().__init__(parent)
        self._parent = parent
        self._notifications: List[ToastNotification] = []
        self._notification_history: List[NotificationData] = []
        self._max_visible = 5
        self._spacing = 10
        self._margin = 20
        self._initialized = True

    def set_parent(self, parent: QWidget) -> None:
        """Set the parent widget for positioning."""
        self._parent = parent

    def show_notification(
        self,
        title: str = "",
        message: str = "",
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
        dismissible: bool = True,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None
    ) -> str:
        """
        Show a new notification.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            duration: Auto-dismiss duration
            dismissible: Whether can be dismissed
            action_text: Action button text
            action_callback: Action callback

        Returns:
            Notification ID
        """
        data = NotificationData(
            title=title,
            message=message,
            notification_type=notification_type,
            duration=duration,
            dismissible=dismissible,
            action_text=action_text,
            action_callback=action_callback
        )

        return self._show_notification_data(data)

    def _show_notification_data(self, data: NotificationData) -> str:
        """Show notification from data object."""
        # Add to history
        self._notification_history.append(data)
        self.notification_added.emit(data)

        # Create toast
        toast = ToastNotification(
            parent=self._parent,
            notification_data=data
        )
        toast.closed.connect(self._on_notification_closed)

        # Calculate position
        start_pos, end_pos = self._calculate_position(toast)

        # Add to list and show
        self._notifications.append(toast)
        toast.show_animated(start_pos, end_pos)

        # Remove oldest if too many
        if len(self._notifications) > self._max_visible:
            oldest = self._notifications[0]
            oldest.dismiss()

        return data.id

    def _calculate_position(self, toast: ToastNotification) -> tuple:
        """Calculate start and end positions for notification."""
        if self._parent:
            parent_rect = self._parent.geometry()
            # Position at top-right of parent
            x = parent_rect.right() - toast.width() - self._margin
            y = parent_rect.top() + self._margin
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_rect = screen.availableGeometry()
                x = screen_rect.right() - toast.width() - self._margin
                y = screen_rect.top() + self._margin
            else:
                x = 100
                y = 100

        # Stack below existing notifications
        for notif in self._notifications:
            if notif.isVisible():
                y += notif.height() + self._spacing

        start_pos = QPoint(x + 50, y)  # Start off-screen
        end_pos = QPoint(x, y)

        return start_pos, end_pos

    def _on_notification_closed(self, notification_id: str) -> None:
        """Handle notification closed."""
        # Remove from list
        self._notifications = [
            n for n in self._notifications
            if n.notification_id != notification_id
        ]

        self.notification_removed.emit(notification_id)

        # Reposition remaining notifications
        self._reposition_notifications()

    def _reposition_notifications(self) -> None:
        """Reposition all visible notifications."""
        if self._parent:
            parent_rect = self._parent.geometry()
            x = parent_rect.right() - self._margin
            y = parent_rect.top() + self._margin
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_rect = screen.availableGeometry()
                x = screen_rect.right() - self._margin
                y = screen_rect.top() + self._margin
            else:
                return

        for toast in self._notifications:
            if toast.isVisible():
                new_x = x - toast.width()

                # Animate to new position
                anim = QPropertyAnimation(toast, b"pos")
                anim.setDuration(200)
                anim.setStartValue(toast.pos())
                anim.setEndValue(QPoint(new_x, y))
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.start()

                y += toast.height() + self._spacing

    def dismiss_all(self) -> None:
        """Dismiss all visible notifications."""
        for toast in self._notifications[:]:
            toast.dismiss()

    def get_history(self) -> List[NotificationData]:
        """Get notification history."""
        return self._notification_history.copy()

    def clear_history(self) -> None:
        """Clear notification history."""
        self._notification_history.clear()

    def mark_as_read(self, notification_id: str) -> None:
        """Mark a notification as read."""
        for data in self._notification_history:
            if data.id == notification_id:
                data.read = True
                break

    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for d in self._notification_history if not d.read)


# Convenience functions
def notify(
    title: str = "",
    message: str = "",
    notification_type: NotificationType = NotificationType.INFO,
    duration: int = 5000
) -> str:
    """Show a notification using the global manager."""
    manager = NotificationManager()
    return manager.show_notification(
        title=title,
        message=message,
        notification_type=notification_type,
        duration=duration
    )


def notify_success(message: str, title: str = "Success") -> str:
    """Show a success notification."""
    return notify(title, message, NotificationType.SUCCESS)


def notify_error(message: str, title: str = "Error") -> str:
    """Show an error notification."""
    return notify(title, message, NotificationType.ERROR, duration=0)


def notify_warning(message: str, title: str = "Warning") -> str:
    """Show a warning notification."""
    return notify(title, message, NotificationType.WARNING)


def notify_info(message: str, title: str = "Info") -> str:
    """Show an info notification."""
    return notify(title, message, NotificationType.INFO)


class NotificationCenter(QWidget):
    """
    Notification center widget that lists all notifications.

    Displays a scrollable list of all past notifications with
    the ability to mark as read or clear all.

    Usage:
        center = NotificationCenter(parent)
        center.refresh()  # Load notifications from manager
    """

    notification_clicked = pyqtSignal(NotificationData)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize notification center.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._manager = NotificationManager()
        self._setup_ui()

        # Connect to manager signals
        self._manager.notification_added.connect(self._on_notification_added)
        self._manager.notification_removed.connect(self._on_notification_removed)

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        theme = get_theme_manager()
        palette = theme.current_palette

        self.setObjectName("notificationCenter")
        self.setStyleSheet(f"""
            #notificationCenter {{
                background-color: {palette.surface};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}
        """)
        self.setMinimumWidth(350)
        self.setMaximumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            background-color: {palette.background_alt};
            border-bottom: 1px solid {palette.border};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Notifications")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {palette.text_primary};
        """)
        header_layout.addWidget(title)

        # Unread badge
        self._badge = QLabel()
        self._badge.setFixedSize(24, 24)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(f"""
            background-color: {palette.error};
            color: white;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        """)
        self._badge.hide()
        header_layout.addWidget(self._badge)

        header_layout.addStretch()

        # Clear all button
        clear_btn = QPushButton("Clear All")
        clear_btn.setFlat(True)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            color: {palette.primary};
            font-weight: 500;
        """)
        clear_btn.clicked.connect(self._clear_all)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Scroll area for notifications
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet("border: none;")

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll, 1)

        # Empty state
        self._empty_label = QLabel("No notifications")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {palette.text_secondary};
            padding: 40px;
        """)
        self._list_layout.insertWidget(0, self._empty_label)

        self.refresh()

    def refresh(self) -> None:
        """Refresh the notification list."""
        # Clear existing items (except empty label and stretch)
        while self._list_layout.count() > 2:
            item = self._list_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Add notifications
        notifications = self._manager.get_history()

        if notifications:
            self._empty_label.hide()
            for data in reversed(notifications):  # Most recent first
                item = self._create_notification_item(data)
                self._list_layout.insertWidget(
                    self._list_layout.count() - 1, item
                )
        else:
            self._empty_label.show()

        # Update badge
        self._update_badge()

    def _create_notification_item(self, data: NotificationData) -> QFrame:
        """Create a notification list item."""
        theme = get_theme_manager()
        palette = theme.current_palette

        frame = QFrame()
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setProperty("notification_id", data.id)

        # Get type color
        type_colors = {
            NotificationType.INFO: palette.info,
            NotificationType.SUCCESS: palette.success,
            NotificationType.WARNING: palette.warning,
            NotificationType.ERROR: palette.error
        }
        type_color = type_colors.get(data.notification_type, palette.info)

        bg_color = palette.surface if data.read else palette.background_alt
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {palette.border};
                border-left: 3px solid {type_color};
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {palette.hover};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()

        if data.title:
            title = QLabel(data.title)
            title.setStyleSheet(f"""
                font-weight: 600;
                color: {palette.text_primary};
            """)
            header.addWidget(title)

        header.addStretch()

        # Time
        time_str = data.timestamp.strftime("%H:%M")
        time_label = QLabel(time_str)
        time_label.setStyleSheet(f"""
            font-size: 11px;
            color: {palette.text_secondary};
        """)
        header.addWidget(time_label)

        layout.addLayout(header)

        # Message
        message = QLabel(data.message)
        message.setWordWrap(True)
        message.setStyleSheet(f"""
            color: {palette.text_secondary};
            font-size: 13px;
        """)
        layout.addWidget(message)

        # Make clickable
        frame.mousePressEvent = lambda e: self._on_item_clicked(data)

        return frame

    def _on_item_clicked(self, data: NotificationData) -> None:
        """Handle notification item click."""
        self._manager.mark_as_read(data.id)
        self.notification_clicked.emit(data)
        self.refresh()

    def _on_notification_added(self, data: NotificationData) -> None:
        """Handle new notification added."""
        self.refresh()

    def _on_notification_removed(self, notification_id: str) -> None:
        """Handle notification removed."""
        # Just update badge, don't remove from history
        self._update_badge()

    def _update_badge(self) -> None:
        """Update the unread badge."""
        count = self._manager.get_unread_count()
        if count > 0:
            self._badge.setText(str(min(count, 99)))
            self._badge.show()
        else:
            self._badge.hide()

    def _clear_all(self) -> None:
        """Clear all notifications."""
        self._manager.clear_history()
        self.refresh()
