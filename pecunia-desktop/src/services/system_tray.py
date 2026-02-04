"""
System Tray Service for Pecunia Desktop.

Provides system tray integration with:
- Tray icon with notification badge
- Context menu (Open, Sync, Settings, Quit)
- Click to show/hide application
- Balloon/toast notifications
- Minimize to tray functionality
"""

import logging
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

# Qt imports with graceful fallback
try:
    from PyQt6.QtWidgets import (
        QApplication, QMenu, QSystemTrayIcon, QWidget
    )
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
    TRAY_ICON_AVAILABLE = True
except ImportError:
    TRAY_ICON_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda *args: None

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class TrayIconState(str, Enum):
    """States for the tray icon appearance."""
    NORMAL = "normal"
    SYNCING = "syncing"
    ERROR = "error"
    NOTIFICATION = "notification"


class TrayMenuAction(str, Enum):
    """Menu actions available in the tray context menu."""
    OPEN = "open"
    SYNC = "sync"
    SETTINGS = "settings"
    ABOUT = "about"
    QUIT = "quit"


# Default tray icon colors
TRAY_ICON_COLORS = {
    TrayIconState.NORMAL: "#2563EB",      # Blue
    TrayIconState.SYNCING: "#F59E0B",     # Amber
    TrayIconState.ERROR: "#EF4444",       # Red
    TrayIconState.NOTIFICATION: "#10B981",  # Green
}

# Badge colors
BADGE_BACKGROUND_COLOR = "#EF4444"  # Red
BADGE_TEXT_COLOR = "#FFFFFF"        # White


# =============================================================================
# System Tray Icon Widget
# =============================================================================

if TRAY_ICON_AVAILABLE:
    class SystemTrayIcon(QSystemTrayIcon):
        """
        Custom system tray icon with notification badge support.

        Features:
        - Dynamic icon state (normal, syncing, error, notification)
        - Notification badge with count
        - Context menu with common actions
        - Click to show/activate main window
        """

        # Signals
        open_requested = pyqtSignal()
        sync_requested = pyqtSignal()
        settings_requested = pyqtSignal()
        about_requested = pyqtSignal()
        quit_requested = pyqtSignal()
        activated_signal = pyqtSignal(str)  # activation reason as string

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            icon_path: Optional[str] = None,
            tooltip: str = "Pecunia"
        ):
            """
            Initialize the system tray icon.

            Args:
                parent: Parent widget.
                icon_path: Path to the tray icon image.
                tooltip: Tooltip text for the tray icon.
            """
            super().__init__(parent)

            self._icon_path = icon_path
            self._tooltip = tooltip
            self._state = TrayIconState.NORMAL
            self._badge_count = 0
            self._base_icon: Optional[QIcon] = None
            self._main_window: Optional[QWidget] = None

            # Menu actions storage
            self._menu_actions: Dict[TrayMenuAction, QAction] = {}

            self._setup_icon()
            self._setup_menu()
            self._connect_signals()

            logger.debug("SystemTrayIcon initialized")

        def _setup_icon(self) -> None:
            """Set up the tray icon."""
            if self._icon_path and Path(self._icon_path).exists():
                self._base_icon = QIcon(self._icon_path)
            else:
                # Create a default icon
                self._base_icon = self._create_default_icon()

            self.setIcon(self._base_icon)
            self.setToolTip(self._tooltip)

        def _create_default_icon(self, color: str = TRAY_ICON_COLORS[TrayIconState.NORMAL]) -> QIcon:
            """
            Create a default application icon.

            Args:
                color: Hex color for the icon.

            Returns:
                QIcon instance.
            """
            size = 64
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw a rounded rectangle with the app color
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(4, 4, size - 8, size - 8, 12, 12)

            # Draw a dollar sign or "F" for Finance
            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Arial", 32, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "$")

            painter.end()
            return QIcon(pixmap)

        def _setup_menu(self) -> None:
            """Set up the context menu."""
            menu = QMenu()

            # Open action
            open_action = menu.addAction("Open Pecunia")
            open_action.triggered.connect(self._on_open)
            self._menu_actions[TrayMenuAction.OPEN] = open_action

            menu.addSeparator()

            # Sync action
            sync_action = menu.addAction("Sync Now")
            sync_action.triggered.connect(self._on_sync)
            self._menu_actions[TrayMenuAction.SYNC] = sync_action

            # Settings action
            settings_action = menu.addAction("Settings")
            settings_action.triggered.connect(self._on_settings)
            self._menu_actions[TrayMenuAction.SETTINGS] = settings_action

            menu.addSeparator()

            # About action
            about_action = menu.addAction("About")
            about_action.triggered.connect(self._on_about)
            self._menu_actions[TrayMenuAction.ABOUT] = about_action

            menu.addSeparator()

            # Quit action
            quit_action = menu.addAction("Quit")
            quit_action.triggered.connect(self._on_quit)
            self._menu_actions[TrayMenuAction.QUIT] = quit_action

            self.setContextMenu(menu)

        def _connect_signals(self) -> None:
            """Connect internal signals."""
            self.activated.connect(self._on_activated)

        def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
            """Handle tray icon activation."""
            reason_map = {
                QSystemTrayIcon.ActivationReason.Trigger: "click",
                QSystemTrayIcon.ActivationReason.DoubleClick: "double_click",
                QSystemTrayIcon.ActivationReason.MiddleClick: "middle_click",
                QSystemTrayIcon.ActivationReason.Context: "context",
            }

            reason_str = reason_map.get(reason, "unknown")
            self.activated_signal.emit(reason_str)

            # On single or double click, show the main window
            if reason in (
                QSystemTrayIcon.ActivationReason.Trigger,
                QSystemTrayIcon.ActivationReason.DoubleClick
            ):
                self._show_main_window()

        def _show_main_window(self) -> None:
            """Show and activate the main window."""
            if self._main_window:
                self._main_window.showNormal()
                self._main_window.activateWindow()
                self._main_window.raise_()
            self.open_requested.emit()

        def _on_open(self) -> None:
            """Handle open action."""
            self._show_main_window()

        def _on_sync(self) -> None:
            """Handle sync action."""
            self.sync_requested.emit()
            logger.debug("Sync requested from tray")

        def _on_settings(self) -> None:
            """Handle settings action."""
            self.settings_requested.emit()
            logger.debug("Settings requested from tray")

        def _on_about(self) -> None:
            """Handle about action."""
            self.about_requested.emit()
            logger.debug("About requested from tray")

        def _on_quit(self) -> None:
            """Handle quit action."""
            self.quit_requested.emit()
            logger.debug("Quit requested from tray")

        # =====================================================================
        # Public Methods
        # =====================================================================

        def set_main_window(self, window: QWidget) -> None:
            """
            Set the main window reference.

            Args:
                window: The main application window.
            """
            self._main_window = window

        def set_state(self, state: TrayIconState) -> None:
            """
            Set the tray icon state.

            Args:
                state: The new icon state.
            """
            self._state = state
            self._update_icon()
            logger.debug(f"Tray icon state changed to: {state.value}")

        def set_badge_count(self, count: int) -> None:
            """
            Set the notification badge count.

            Args:
                count: Number to display on badge (0 to hide).
            """
            self._badge_count = max(0, count)
            self._update_icon()

        def increment_badge(self) -> None:
            """Increment the badge count by 1."""
            self._badge_count += 1
            self._update_icon()

        def clear_badge(self) -> None:
            """Clear the notification badge."""
            self._badge_count = 0
            self._update_icon()

        def _update_icon(self) -> None:
            """Update the tray icon based on state and badge."""
            color = TRAY_ICON_COLORS.get(self._state, TRAY_ICON_COLORS[TrayIconState.NORMAL])

            if self._icon_path and Path(self._icon_path).exists():
                base_pixmap = QPixmap(self._icon_path)
            else:
                # Create default icon with current state color
                icon = self._create_default_icon(color)
                base_pixmap = icon.pixmap(64, 64)

            # Add badge if count > 0
            if self._badge_count > 0:
                final_pixmap = self._add_badge_to_pixmap(base_pixmap, self._badge_count)
            else:
                final_pixmap = base_pixmap

            self.setIcon(QIcon(final_pixmap))

        def _add_badge_to_pixmap(self, pixmap: QPixmap, count: int) -> QPixmap:
            """
            Add a notification badge to a pixmap.

            Args:
                pixmap: Base pixmap.
                count: Badge count to display.

            Returns:
                Pixmap with badge overlay.
            """
            result = QPixmap(pixmap)
            painter = QPainter(result)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            size = pixmap.width()
            badge_size = size // 3
            badge_x = size - badge_size
            badge_y = 0

            # Draw badge background
            painter.setBrush(QColor(BADGE_BACKGROUND_COLOR))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(badge_x, badge_y, badge_size, badge_size)

            # Draw badge text
            painter.setPen(QColor(BADGE_TEXT_COLOR))
            font = QFont("Arial", badge_size // 2 - 2, QFont.Weight.Bold)
            painter.setFont(font)

            badge_text = str(count) if count < 100 else "99+"
            from PyQt6.QtCore import QRect
            badge_rect = QRect(badge_x, badge_y, badge_size, badge_size)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

            painter.end()
            return result

        def set_tooltip(self, text: str) -> None:
            """
            Set the tray icon tooltip.

            Args:
                text: Tooltip text.
            """
            self._tooltip = text
            self.setToolTip(text)

        def show_message(
            self,
            title: str,
            message: str,
            icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
            duration_ms: int = 5000
        ) -> None:
            """
            Show a balloon/notification message.

            Args:
                title: Message title.
                message: Message body.
                icon_type: Icon to display.
                duration_ms: Duration in milliseconds.
            """
            self.showMessage(title, message, icon_type, duration_ms)

        def show_info_message(self, title: str, message: str, duration_ms: int = 5000) -> None:
            """Show an info message."""
            self.show_message(title, message, QSystemTrayIcon.MessageIcon.Information, duration_ms)

        def show_warning_message(self, title: str, message: str, duration_ms: int = 7000) -> None:
            """Show a warning message."""
            self.show_message(title, message, QSystemTrayIcon.MessageIcon.Warning, duration_ms)

        def show_error_message(self, title: str, message: str, duration_ms: int = 10000) -> None:
            """Show an error message."""
            self.show_message(title, message, QSystemTrayIcon.MessageIcon.Critical, duration_ms)

        def enable_action(self, action: TrayMenuAction, enabled: bool = True) -> None:
            """
            Enable or disable a menu action.

            Args:
                action: The action to modify.
                enabled: Whether to enable the action.
            """
            if action in self._menu_actions:
                self._menu_actions[action].setEnabled(enabled)

        def set_action_text(self, action: TrayMenuAction, text: str) -> None:
            """
            Set the text for a menu action.

            Args:
                action: The action to modify.
                text: New text for the action.
            """
            if action in self._menu_actions:
                self._menu_actions[action].setText(text)

        def start_syncing_animation(self) -> None:
            """Start the syncing state animation."""
            self.set_state(TrayIconState.SYNCING)
            self.set_action_text(TrayMenuAction.SYNC, "Syncing...")
            self.enable_action(TrayMenuAction.SYNC, False)

        def stop_syncing_animation(self, success: bool = True) -> None:
            """
            Stop the syncing animation.

            Args:
                success: Whether sync was successful.
            """
            if success:
                self.set_state(TrayIconState.NORMAL)
            else:
                self.set_state(TrayIconState.ERROR)

            self.set_action_text(TrayMenuAction.SYNC, "Sync Now")
            self.enable_action(TrayMenuAction.SYNC, True)


# =============================================================================
# System Tray Service (Singleton)
# =============================================================================

class SystemTrayService:
    """
    Singleton service for managing the system tray icon.

    Provides a centralized interface for:
    - Tray icon management
    - Badge updates
    - Menu customization
    - Notification messages
    """

    _instance: Optional["SystemTrayService"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the system tray service."""
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._tray_icon: Optional[Any] = None  # SystemTrayIcon
        self._main_window: Optional[Any] = None
        self._icon_path: Optional[str] = None
        self._callbacks: Dict[str, List[Callable]] = {
            "open": [],
            "sync": [],
            "settings": [],
            "about": [],
            "quit": [],
            "activated": [],
        }

        self._initialized = True
        logger.info("SystemTrayService initialized")

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(
        self,
        parent: Optional[Any] = None,
        main_window: Optional[Any] = None,
        icon_path: Optional[str] = None,
        tooltip: str = "Pecunia"
    ) -> bool:
        """
        Initialize and show the system tray icon.

        Args:
            parent: Parent widget.
            main_window: Main application window.
            icon_path: Path to tray icon.
            tooltip: Tray icon tooltip.

        Returns:
            True if initialization was successful.
        """
        if not TRAY_ICON_AVAILABLE:
            logger.warning("System tray not available (PyQt6 not installed)")
            return False

        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available on this platform")
            return False

        try:
            self._main_window = main_window
            self._icon_path = icon_path

            self._tray_icon = SystemTrayIcon(parent, icon_path, tooltip)
            self._tray_icon.set_main_window(main_window)

            # Connect signals to callbacks
            self._tray_icon.open_requested.connect(self._emit_callback("open"))
            self._tray_icon.sync_requested.connect(self._emit_callback("sync"))
            self._tray_icon.settings_requested.connect(self._emit_callback("settings"))
            self._tray_icon.about_requested.connect(self._emit_callback("about"))
            self._tray_icon.quit_requested.connect(self._emit_callback("quit"))
            self._tray_icon.activated_signal.connect(self._on_activated)

            self._tray_icon.show()
            logger.info("System tray icon initialized and visible")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize system tray: {e}")
            return False

    def _emit_callback(self, event_type: str) -> Callable:
        """Create a callback emitter for a specific event type."""
        def callback():
            for cb in self._callbacks.get(event_type, []):
                try:
                    cb()
                except Exception as e:
                    logger.error(f"Error in tray callback '{event_type}': {e}")
        return callback

    def _on_activated(self, reason: str) -> None:
        """Handle tray icon activation."""
        for cb in self._callbacks.get("activated", []):
            try:
                cb(reason)
            except Exception as e:
                logger.error(f"Error in tray activation callback: {e}")

    # =========================================================================
    # Callback Registration
    # =========================================================================

    def on_open(self, callback: Callable[[], None]) -> None:
        """Register a callback for the open action."""
        self._callbacks["open"].append(callback)

    def on_sync(self, callback: Callable[[], None]) -> None:
        """Register a callback for the sync action."""
        self._callbacks["sync"].append(callback)

    def on_settings(self, callback: Callable[[], None]) -> None:
        """Register a callback for the settings action."""
        self._callbacks["settings"].append(callback)

    def on_about(self, callback: Callable[[], None]) -> None:
        """Register a callback for the about action."""
        self._callbacks["about"].append(callback)

    def on_quit(self, callback: Callable[[], None]) -> None:
        """Register a callback for the quit action."""
        self._callbacks["quit"].append(callback)

    def on_activated(self, callback: Callable[[str], None]) -> None:
        """Register a callback for tray activation (receives reason string)."""
        self._callbacks["activated"].append(callback)

    def remove_callback(self, event_type: str, callback: Callable) -> None:
        """Remove a registered callback."""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    # =========================================================================
    # Tray Icon Methods
    # =========================================================================

    @property
    def is_available(self) -> bool:
        """Check if the system tray is available."""
        return TRAY_ICON_AVAILABLE and self._tray_icon is not None

    def set_badge_count(self, count: int) -> None:
        """Set the notification badge count."""
        if self._tray_icon:
            self._tray_icon.set_badge_count(count)

    def increment_badge(self) -> None:
        """Increment the badge count."""
        if self._tray_icon:
            self._tray_icon.increment_badge()

    def clear_badge(self) -> None:
        """Clear the notification badge."""
        if self._tray_icon:
            self._tray_icon.clear_badge()

    def set_state(self, state: TrayIconState) -> None:
        """Set the tray icon state."""
        if self._tray_icon:
            self._tray_icon.set_state(state)

    def set_tooltip(self, text: str) -> None:
        """Set the tray icon tooltip."""
        if self._tray_icon:
            self._tray_icon.set_tooltip(text)

    def show_message(
        self,
        title: str,
        message: str,
        message_type: str = "info",
        duration_ms: int = 5000
    ) -> None:
        """
        Show a tray notification message.

        Args:
            title: Message title.
            message: Message body.
            message_type: Type of message (info, warning, error).
            duration_ms: Duration in milliseconds.
        """
        if not self._tray_icon:
            return

        if message_type == "warning":
            self._tray_icon.show_warning_message(title, message, duration_ms)
        elif message_type == "error":
            self._tray_icon.show_error_message(title, message, duration_ms)
        else:
            self._tray_icon.show_info_message(title, message, duration_ms)

    def start_sync_animation(self) -> None:
        """Start the syncing animation."""
        if self._tray_icon:
            self._tray_icon.start_syncing_animation()

    def stop_sync_animation(self, success: bool = True) -> None:
        """Stop the syncing animation."""
        if self._tray_icon:
            self._tray_icon.stop_syncing_animation(success)

    def show(self) -> None:
        """Show the tray icon."""
        if self._tray_icon:
            self._tray_icon.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        if self._tray_icon:
            self._tray_icon.hide()

    def shutdown(self) -> None:
        """Shutdown the system tray service."""
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None
        logger.info("SystemTrayService shut down")


# =============================================================================
# Global Instance Access
# =============================================================================

_system_tray_service: Optional[SystemTrayService] = None


def get_system_tray_service() -> SystemTrayService:
    """Get the global system tray service instance."""
    global _system_tray_service
    if _system_tray_service is None:
        _system_tray_service = SystemTrayService()
    return _system_tray_service


__all__ = [
    # Enums
    "TrayIconState",
    "TrayMenuAction",

    # Classes
    "SystemTrayIcon",
    "SystemTrayService",

    # Functions
    "get_system_tray_service",

    # Constants
    "TRAY_ICON_AVAILABLE",
]
