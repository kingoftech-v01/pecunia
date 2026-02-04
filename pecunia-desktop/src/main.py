"""
Pecunia Desktop - Main Application Entry Point

A professional-grade PyQt6-based desktop application for personal finance management.
This module handles application startup, single instance enforcement, high DPI support,
async event loop integration with qasync, system tray, splash screen, and auto-updates.
"""

from __future__ import annotations

import os
import sys
import ctypes
import argparse
import logging
import signal
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, NoReturn, TYPE_CHECKING

# =============================================================================
# High DPI Configuration (must be set before QApplication creation)
# =============================================================================

# Enable high DPI scaling via environment variables
os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '1')
os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
os.environ.setdefault('QT_SCALE_FACTOR_ROUNDING_POLICY', 'PassThrough')

# Add src directory to path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
    QSplashScreen,
    QSystemTrayIcon,
    QMenu,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QProgressBar,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QSharedMemory,
    QLockFile,
    QObject,
    QEvent,
    pyqtSignal,
)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QFont,
    QAction,
    QLinearGradient,
)

# Third-party async integration
try:
    import qasync
    QASYNC_AVAILABLE = True
except ImportError:
    qasync = None
    QASYNC_AVAILABLE = False

try:
    import asyncio
except ImportError:
    asyncio = None

from constants import APP_NAME, APP_VERSION, APP_ORGANIZATION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from config import get_config_manager, get_config, get_data_dir, get_cache_dir

if TYPE_CHECKING:
    from config import ConfigManager, AppSettings

logger = logging.getLogger(__name__)


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging(
    level: int = logging.INFO,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_debug_file: bool = False,
    enable_error_file: bool = True,
    colored_console: bool = True,
    structured_logs: bool = False,
) -> logging.Logger:
    """
    Configure comprehensive application logging.

    Args:
        level: Base logging level.
        enable_console: Enable console output.
        enable_file: Enable main log file.
        enable_debug_file: Enable separate debug log file.
        enable_error_file: Enable separate error log file.
        colored_console: Enable colored console output (Windows).
        structured_logs: Enable JSON structured logging.

    Returns:
        The root logger instance.
    """
    log_dir = get_data_dir() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped log files
    timestamp = datetime.now().strftime('%Y%m%d')
    main_log = log_dir / f'pecunia_{timestamp}.log'
    error_log = log_dir / f'pecunia_errors_{timestamp}.log'
    debug_log = log_dir / f'pecunia_debug_{timestamp}.log'

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)-8s | %(name)s | %(message)s'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all, filter at handlers
    root_logger.handlers.clear()

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Main file handler with rotation
    if enable_file:
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                main_log,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8',
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler: {e}")

    # Error file handler
    if enable_error_file:
        try:
            from logging.handlers import RotatingFileHandler
            error_handler = RotatingFileHandler(
                error_log,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding='utf-8',
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            root_logger.addHandler(error_handler)
        except Exception:
            pass

    # Debug file handler
    if enable_debug_file:
        try:
            from logging.handlers import RotatingFileHandler
            debug_handler = RotatingFileHandler(
                debug_log,
                maxBytes=20 * 1024 * 1024,  # 20 MB
                backupCount=2,
                encoding='utf-8',
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(file_formatter)
            root_logger.addHandler(debug_handler)
        except Exception:
            pass

    # Reduce noise from third-party libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    return root_logger


def shutdown_logging() -> None:
    """Shutdown logging and flush all handlers."""
    logging.shutdown()


# =============================================================================
# Global Exception Handler
# =============================================================================

class GlobalExceptionHandler(QObject):
    """
    Handles uncaught exceptions in both main thread and Qt event loop.

    Provides user-friendly error dialogs and comprehensive logging.
    """

    exception_caught = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._original_excepthook = sys.excepthook
        self.exception_caught.connect(self._show_error_dialog)

    def install(self) -> None:
        """Install the global exception handler."""
        sys.excepthook = self._handle_exception

    def uninstall(self) -> None:
        """Restore the original exception handler."""
        sys.excepthook = self._original_excepthook

    def _handle_exception(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb,
    ) -> None:
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupt to exit gracefully
            self._original_excepthook(exc_type, exc_value, exc_tb)
            return

        # Format the exception
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Uncaught exception:\n{error_msg}")

        # Emit signal for UI handling (thread-safe)
        self.exception_caught.emit(
            exc_type.__name__,
            str(exc_value) or "An unexpected error occurred"
        )

    def _show_error_dialog(self, error_type: str, error_message: str) -> None:
        """Show error dialog to user."""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle(f"{APP_NAME} - Error")
            msg_box.setText(f"An unexpected error occurred: {error_type}")
            msg_box.setInformativeText(error_message)
            msg_box.setDetailedText(
                f"Please check the log file for more details.\n\n"
                f"Log location: {get_data_dir() / 'logs'}"
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception:
            pass


def get_exception_handler() -> GlobalExceptionHandler:
    """Get the global exception handler instance."""
    global _exception_handler
    if '_exception_handler' not in globals() or _exception_handler is None:
        _exception_handler = GlobalExceptionHandler()
    return _exception_handler

_exception_handler: Optional[GlobalExceptionHandler] = None


# =============================================================================
# Single Instance Management
# =============================================================================

class SingleInstance:
    """
    Ensures only one instance of the application runs at a time.

    Uses a combination of shared memory and local socket server
    for reliable cross-platform single instance detection.
    """

    def __init__(self, app_id: str):
        """
        Initialize the single instance checker.

        Args:
            app_id: Unique identifier for the application.
        """
        self._app_id = app_id
        self._shared_memory = QSharedMemory(app_id)
        self._lock_file: Optional[QLockFile] = None
        self._server: Optional[QLocalServer] = None
        self._is_primary = False
        self.activate_window_callback = None

    @property
    def is_primary(self) -> bool:
        """Check if this is the primary instance."""
        return self._is_primary

    def try_lock(self) -> bool:
        """
        Attempt to acquire the single instance lock.

        Returns:
            True if this is the primary instance, False otherwise.
        """
        # Try shared memory approach first
        if self._shared_memory.attach():
            # Another instance exists
            self._shared_memory.detach()
            return False

        # Try to create shared memory segment
        if self._shared_memory.create(1):
            self._is_primary = True
            self._start_server()
            return True

        # Shared memory failed, try lock file fallback
        return self._try_lock_file()

    def _try_lock_file(self) -> bool:
        """Try to acquire lock using a lock file."""
        lock_path = get_data_dir() / f"{self._app_id}.lock"
        self._lock_file = QLockFile(str(lock_path))

        if self._lock_file.tryLock(100):  # 100ms timeout
            self._is_primary = True
            self._start_server()
            return True

        return False

    def _start_server(self) -> None:
        """Start local server to receive messages from other instances."""
        # Remove any stale server
        QLocalServer.removeServer(self._app_id)

        self._server = QLocalServer()
        if self._server.listen(self._app_id):
            self._server.newConnection.connect(self._on_new_connection)
            logger.debug(f"Local server started: {self._app_id}")

    def _on_new_connection(self) -> None:
        """Handle new connection from another instance."""
        if self._server:
            socket = self._server.nextPendingConnection()
            if socket:
                socket.waitForReadyRead(1000)
                data = socket.readAll().data().decode("utf-8")
                logger.info(f"Received message from other instance: {data}")
                socket.disconnectFromServer()

                # Activate main window
                if self.activate_window_callback:
                    self.activate_window_callback()

    def send_message(self, message: str = "activate") -> bool:
        """
        Send a message to the primary instance.

        Args:
            message: Message to send.

        Returns:
            True if message was sent successfully.
        """
        socket = QLocalSocket()
        socket.connectToServer(self._app_id)

        if socket.waitForConnected(1000):
            socket.write(message.encode("utf-8"))
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return True

        return False

    def release(self) -> None:
        """Release the single instance lock."""
        if self._server:
            self._server.close()
            self._server = None

        if self._shared_memory.isAttached():
            self._shared_memory.detach()

        if self._lock_file:
            self._lock_file.unlock()
            self._lock_file = None

        self._is_primary = False

    def set_activate_callback(self, callback) -> None:
        """Set callback for when another instance requests activation."""
        self.activate_window_callback = callback


# =============================================================================
# Splash Screen
# =============================================================================

class SplashScreen(QSplashScreen):
    """
    Professional splash screen with progress indicator.

    Displays application branding and loading status during startup.
    """

    def __init__(self):
        # Create splash pixmap
        pixmap = self._create_splash_pixmap()
        super().__init__(pixmap)

        self.setWindowFlags(
            Qt.WindowType.SplashScreen |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        # Progress tracking
        self._progress = 0
        self._status_message = "Initializing..."

    def _create_splash_pixmap(self) -> QPixmap:
        """Create the splash screen pixmap."""
        width, height = 500, 350
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor('#1a252f'))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw gradient background
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor('#2c3e50'))
        gradient.setColorAt(1, QColor('#1a252f'))
        painter.fillRect(0, 0, width, height, gradient)

        # Draw app name
        title_font = QFont('Segoe UI', 36, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(0, 80, width, 60, Qt.AlignmentFlag.AlignCenter, APP_NAME)

        # Draw version
        version_font = QFont('Segoe UI', 14)
        painter.setFont(version_font)
        painter.setPen(QColor('#95a5a6'))
        painter.drawText(0, 130, width, 30, Qt.AlignmentFlag.AlignCenter, f"Version {APP_VERSION}")

        # Draw tagline
        tagline_font = QFont('Segoe UI', 12)
        painter.setFont(tagline_font)
        painter.setPen(QColor('#7f8c8d'))
        painter.drawText(0, 170, width, 30, Qt.AlignmentFlag.AlignCenter, "Personal Finance Management")

        # Draw loading bar background
        bar_y = height - 60
        bar_height = 6
        bar_margin = 50
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#34495e'))
        painter.drawRoundedRect(bar_margin, bar_y, width - 2*bar_margin, bar_height, 3, 3)

        # Draw copyright
        copyright_font = QFont('Segoe UI', 9)
        painter.setFont(copyright_font)
        painter.setPen(QColor('#5a6c7d'))
        painter.drawText(
            0, height - 30, width, 25,
            Qt.AlignmentFlag.AlignCenter,
            f"(C) {datetime.now().year} {APP_ORGANIZATION}. All rights reserved."
        )

        painter.end()
        return pixmap

    def set_progress(self, value: int, message: str = "") -> None:
        """
        Update progress and status message.

        Args:
            value: Progress percentage (0-100).
            message: Status message to display.
        """
        self._progress = max(0, min(100, value))
        if message:
            self._status_message = message

        self.showMessage(
            self._status_message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            QColor('#bdc3c7')
        )
        QApplication.processEvents()

    def increment_progress(self, amount: int = 10, message: str = "") -> None:
        """Increment progress by specified amount."""
        self.set_progress(self._progress + amount, message)


# =============================================================================
# Update Checker
# =============================================================================

class UpdateChecker(QObject):
    """
    Background update checker with async support.

    Checks for application updates from the configured update server.
    """

    update_available = pyqtSignal(str, str)  # version, download_url
    check_complete = pyqtSignal(bool)  # has_update
    check_failed = pyqtSignal(str)  # error_message

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._current_version = APP_VERSION
        self._checking = False

    async def check_for_updates_async(self) -> Optional[dict]:
        """
        Check for updates asynchronously.

        Returns:
            Update info dict if available, None otherwise.
        """
        if self._checking or asyncio is None:
            return None

        self._checking = True

        try:
            config = get_config()
            update_url = config.update_url

            # Use aiohttp if available
            try:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    params = {
                        'current_version': self._current_version,
                        'platform': sys.platform,
                    }
                    async with session.get(
                        f"{update_url}/check",
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._process_update_response(data)
                        else:
                            logger.warning(f"Update check returned status {response.status}")
                            return None

            except ImportError:
                # Fallback to urllib
                import urllib.request
                import json

                params = f"?current_version={self._current_version}&platform={sys.platform}"
                req = urllib.request.Request(
                    f"{update_url}/check{params}",
                    headers={'User-Agent': f'{APP_NAME}/{APP_VERSION}'}
                )

                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode())
                    return self._process_update_response(data)

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            self.check_failed.emit(str(e))
            return None
        finally:
            self._checking = False

    def _process_update_response(self, data: dict) -> Optional[dict]:
        """Process update response from server."""
        if data.get('update_available'):
            new_version = data.get('version', 'unknown')
            download_url = data.get('download_url', '')

            logger.info(f"Update available: v{new_version}")
            self.update_available.emit(new_version, download_url)
            self.check_complete.emit(True)

            return {
                'version': new_version,
                'download_url': download_url,
                'release_notes': data.get('release_notes', ''),
                'mandatory': data.get('mandatory', False),
            }
        else:
            logger.debug("No updates available")
            self.check_complete.emit(False)
            return None

    def check_for_updates_sync(self) -> None:
        """Trigger update check synchronously (runs in timer callback)."""
        if asyncio is None:
            return

        try:
            loop = asyncio.get_event_loop()
            if QASYNC_AVAILABLE and loop.is_running():
                asyncio.create_task(self.check_for_updates_async())
            else:
                # Use asyncio.run for synchronous execution
                asyncio.run(self.check_for_updates_async())
        except Exception as e:
            logger.error(f"Failed to initiate update check: {e}")
            self.check_failed.emit(str(e))


# =============================================================================
# System Tray Manager
# =============================================================================

class SystemTrayManager(QObject):
    """
    Manages system tray icon and menu.

    Provides quick access to common actions and notifications.
    """

    show_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    sync_requested = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._tray_menu: Optional[QMenu] = None
        self._initialized = False

    def initialize(self, app: QApplication) -> bool:
        """
        Initialize the system tray icon.

        Args:
            app: The QApplication instance.

        Returns:
            True if system tray is available and initialized.
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this platform")
            return False

        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self._create_tray_icon(), parent=app)
        self._tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        # Create context menu
        self._create_tray_menu()

        # Connect signals
        self._tray_icon.activated.connect(self._on_tray_activated)

        # Show tray icon
        self._tray_icon.show()
        self._initialized = True

        logger.debug("System tray initialized")
        return True

    def _create_tray_icon(self) -> QIcon:
        """Create the tray icon."""
        # Check for custom icon file
        icon_path = Path(__file__).parent.parent / 'resources' / 'icons' / 'tray_icon.png'
        if icon_path.exists():
            return QIcon(str(icon_path))

        # Create a simple default icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor('#3498db'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 28, 28)

        # Draw $ symbol
        painter.setPen(QColor('#ffffff'))
        font = QFont('Segoe UI', 18, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, 0, 32, 32, Qt.AlignmentFlag.AlignCenter, "$")
        painter.end()

        return QIcon(pixmap)

    def _create_tray_menu(self) -> None:
        """Create the tray context menu."""
        self._tray_menu = QMenu()

        # Show/Hide action
        show_action = QAction(f"Show {APP_NAME}", self._tray_menu)
        show_action.triggered.connect(self.show_requested.emit)
        self._tray_menu.addAction(show_action)

        self._tray_menu.addSeparator()

        # Quick actions
        sync_action = QAction("Sync Now", self._tray_menu)
        sync_action.triggered.connect(self.sync_requested.emit)
        self._tray_menu.addAction(sync_action)

        self._tray_menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self._tray_menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(self._tray_menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - show on Windows
            if sys.platform == 'win32':
                self.show_requested.emit()

    def show_notification(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 5000,
    ) -> None:
        """
        Show a system tray notification.

        Args:
            title: Notification title.
            message: Notification message.
            icon: Icon type to display.
            duration_ms: Duration to show notification.
        """
        if self._tray_icon and self._initialized:
            self._tray_icon.showMessage(title, message, icon, duration_ms)

    def cleanup(self) -> None:
        """Clean up tray resources."""
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None
        self._initialized = False


# =============================================================================
# Main Window
# =============================================================================

class MainWindow(QMainWindow):
    """
    Main application window.

    Provides the primary UI container with navigation sidebar,
    content area, and status bar.
    """

    closing = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config_manager = get_config_manager()
        self._setup_window()
        self._setup_ui()
        self._restore_geometry()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Set window icon if available
        icon_path = Path(__file__).parent.parent / 'resources' / 'icons' / 'app_icon.png'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
        """Set up the main user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)

        # Content area
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, 1)

        # Add placeholder views
        self._add_placeholder_views()

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_sidebar(self) -> QWidget:
        """Create the navigation sidebar."""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("""
            QWidget#sidebar {
                background-color: #2c3e50;
                color: white;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)

        # App title
        title_label = QLabel(APP_NAME)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                background-color: #1a252f;
            }
        """)
        layout.addWidget(title_label)

        # Navigation placeholder
        nav_placeholder = QLabel("Navigation\n\n- Dashboard\n- Transactions\n- Budgets\n- Accounts\n- Settings")
        nav_placeholder.setStyleSheet("color: #bdc3c7; padding: 20px;")
        layout.addWidget(nav_placeholder)

        layout.addStretch()

        # User info placeholder
        user_label = QLabel("Not logged in")
        user_label.setStyleSheet("color: #95a5a6; padding: 20px;")
        layout.addWidget(user_label)

        return sidebar

    def _add_placeholder_views(self) -> None:
        """Add placeholder views to the content stack."""
        # Dashboard placeholder
        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_label = QLabel("Dashboard View\n\nThis is where the main dashboard will be displayed.")
        dashboard_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dashboard_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        dashboard_layout.addWidget(dashboard_label)
        self.content_stack.addWidget(dashboard)

    def _restore_geometry(self) -> None:
        """Restore window geometry from configuration."""
        ui_config = self.config_manager.ui

        if ui_config.window_x is not None and ui_config.window_y is not None:
            self.move(ui_config.window_x, ui_config.window_y)

        self.resize(ui_config.window_width, ui_config.window_height)

        if ui_config.window_maximized:
            self.showMaximized()

    def _save_geometry(self) -> None:
        """Save window geometry to configuration."""
        if not self.isMaximized():
            geometry = self.geometry()
            self.config_manager.update_window_geometry(
                x=geometry.x(),
                y=geometry.y(),
                width=geometry.width(),
                height=geometry.height(),
                maximized=False,
            )
        else:
            self.config_manager.settings.ui.window_maximized = True

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self._save_geometry()
        self.config_manager.save()

        if self.config_manager.settings.first_run:
            self.config_manager.settings.first_run = False
            self.config_manager.save()

        logger.info("Application closing")
        self.closing.emit()
        event.accept()


# =============================================================================
# Application Class
# =============================================================================

class Application:
    """
    Main application class.

    Handles application initialization, event loop integration,
    and lifecycle management.
    """

    def __init__(
        self,
        argv: list[str],
        args: argparse.Namespace,
        single_instance: SingleInstance,
    ):
        """
        Initialize the application.

        Args:
            argv: Command line arguments.
            args: Parsed argument namespace.
            single_instance: Single instance manager.
        """
        self.argv = argv
        self.args = args
        self.single_instance = single_instance

        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
        self.splash: Optional[SplashScreen] = None
        self.tray_manager: Optional[SystemTrayManager] = None
        self.update_checker: Optional[UpdateChecker] = None

        self._async_loop = None
        self._async_timer: Optional[QTimer] = None
        self._exit_code: int = 0

    def _setup_high_dpi(self) -> None:
        """Configure high DPI scaling."""
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except AttributeError:
            pass  # Older PyQt6 versions

    def _setup_app(self) -> None:
        """Set up the Qt application."""
        self._setup_high_dpi()

        self.app = QApplication(self.argv)
        self.app.setApplicationName(APP_NAME)
        self.app.setApplicationVersion(APP_VERSION)
        self.app.setOrganizationName(APP_ORGANIZATION)
        self.app.setOrganizationDomain("pecunia.com")

        # Prevent quit when last window closes if tray is active
        self.app.setQuitOnLastWindowClosed(False)

        # Set application font
        font = self.app.font()
        if sys.platform == 'win32':
            font.setFamily("Segoe UI")
        elif sys.platform == 'darwin':
            font.setFamily("SF Pro Display")
        else:
            font.setFamily("Ubuntu")
        font.setPointSize(10)
        self.app.setFont(font)

        # Apply stylesheet
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        """Apply the application stylesheet."""
        stylesheet = """
            QMainWindow {
                background-color: #f5f6fa;
            }
            QWidget {
                font-family: "Segoe UI", "SF Pro Display", "Ubuntu", sans-serif;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #3498db;
            }
            QTableWidget {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                background-color: white;
                gridline-color: #ecf0f1;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f5f6fa;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
            QStatusBar {
                background-color: #ecf0f1;
                color: #7f8c8d;
            }
        """
        self.app.setStyleSheet(stylesheet)

    def _setup_async_loop(self) -> None:
        """Set up asyncio event loop integration with Qt."""
        if asyncio is None:
            logger.warning("asyncio not available")
            return

        if QASYNC_AVAILABLE:
            # Use qasync for proper integration
            self._async_loop = qasync.QEventLoop(self.app)
            asyncio.set_event_loop(self._async_loop)
            logger.debug("Using qasync for async integration")
        else:
            # Fallback: manual event loop processing
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)

            # Create a timer to process asyncio events
            self._async_timer = QTimer()
            self._async_timer.timeout.connect(self._process_async_events)
            self._async_timer.start(10)  # Process every 10ms

            logger.debug("Using fallback async integration (qasync not available)")

    def _process_async_events(self) -> None:
        """Process pending asyncio events (fallback mode)."""
        if self._async_loop:
            try:
                self._async_loop.stop()
                self._async_loop.run_forever()
            except Exception:
                pass

    def _setup_signal_handlers(self) -> None:
        """Set up OS signal handlers for graceful shutdown."""
        if sys.platform != 'win32':
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, self._signal_handler)
        else:
            signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle OS signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self._initiate_shutdown()

    def _initiate_shutdown(self) -> None:
        """Initiate graceful application shutdown."""
        if self.main_window:
            self.main_window.close()
        if self.app:
            self.app.quit()

    def _setup_tray(self) -> None:
        """Set up system tray."""
        if self.args.no_tray:
            logger.debug("System tray disabled via command line")
            return

        self.tray_manager = SystemTrayManager(self.app)
        if self.tray_manager.initialize(self.app):
            self.tray_manager.show_requested.connect(self._on_show_requested)
            self.tray_manager.quit_requested.connect(self._initiate_shutdown)
            self.tray_manager.sync_requested.connect(self._on_sync_requested)

    def _on_show_requested(self) -> None:
        """Handle show window request from tray."""
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

    def _on_sync_requested(self) -> None:
        """Handle sync request from tray."""
        logger.debug("Manual sync triggered from tray")
        # TODO: Implement sync service call

    async def _check_for_updates(self) -> None:
        """Check for application updates."""
        config = get_config()
        if not config.check_updates_on_startup:
            return

        self.update_checker = UpdateChecker(self.app)
        self.update_checker.update_available.connect(self._on_update_available)

        try:
            result = await self.update_checker.check_for_updates_async()
            if result:
                logger.info(f"Update check complete: {result}")
        except Exception as e:
            logger.warning(f"Update check failed: {e}")

    def _on_update_available(self, version: str, download_url: str) -> None:
        """Handle update available notification."""
        if self.tray_manager:
            self.tray_manager.show_notification(
                "Update Available",
                f"{APP_NAME} v{version} is available. Click to download.",
                QSystemTrayIcon.MessageIcon.Information,
            )

        if self.main_window and self.main_window.isVisible():
            reply = QMessageBox.question(
                self.main_window,
                "Update Available",
                f"A new version of {APP_NAME} (v{version}) is available.\n\n"
                "Would you like to download it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                import webbrowser
                webbrowser.open(download_url)

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code.
        """
        try:
            # Initialize Qt application
            self._setup_app()
            logger.debug("Qt application initialized")

            # Show splash screen
            if not self.args.no_splash:
                self.splash = SplashScreen()
                self.splash.show()
                self.splash.set_progress(10, "Loading configuration...")

            # Load configuration
            config_manager = get_config_manager()
            if self.splash:
                self.splash.set_progress(25, "Configuration loaded")
            logger.info("Configuration loaded")

            # Setup async event loop
            self._setup_async_loop()
            if self.splash:
                self.splash.set_progress(40, "Initializing services...")

            # Setup signal handlers
            self._setup_signal_handlers()
            if self.splash:
                self.splash.set_progress(50, "Setting up system tray...")

            # Setup system tray
            self._setup_tray()
            if self.splash:
                self.splash.set_progress(65, "Creating main window...")

            # Set up single instance callback
            self.single_instance.set_activate_callback(self._on_show_requested)

            # Create main window
            self.main_window = MainWindow()
            self.main_window.closing.connect(self._on_main_window_closing)
            if self.splash:
                self.splash.set_progress(85, "Checking for updates...")

            # Schedule update check
            if asyncio and QASYNC_AVAILABLE:
                asyncio.ensure_future(self._check_for_updates())
            else:
                QTimer.singleShot(2000, self._schedule_update_check)

            if self.splash:
                self.splash.set_progress(100, "Ready!")

            # Finish startup
            QTimer.singleShot(500, self._finish_startup)

            logger.info("Application initialized successfully")

            # Run the event loop
            if QASYNC_AVAILABLE and self._async_loop:
                with self._async_loop:
                    self._exit_code = self._async_loop.run_forever()
            else:
                self._exit_code = self.app.exec()

            # Cleanup
            self._cleanup()

            return self._exit_code

        except Exception as e:
            logger.exception(f"Fatal error during startup: {e}")

            if self.app:
                QMessageBox.critical(
                    None,
                    "Fatal Error",
                    f"An unexpected error occurred during startup:\n\n{str(e)}\n\n"
                    f"Check the logs at: {get_data_dir() / 'logs'}"
                )
            return 1

    def _schedule_update_check(self) -> None:
        """Schedule update check (fallback for non-qasync mode)."""
        if self.update_checker:
            self.update_checker.check_for_updates_sync()

    def _finish_startup(self) -> None:
        """Finish startup and show main window."""
        if self.splash:
            self.splash.finish(self.main_window)

        if not self.args.minimized:
            if self.main_window:
                self.main_window.show()
                self.main_window.raise_()
        else:
            logger.debug("Starting minimized to tray")

    def _on_main_window_closing(self) -> None:
        """Handle main window closing."""
        if self.tray_manager and self.tray_manager._initialized:
            logger.debug("Main window closed, running in system tray")
        else:
            self._initiate_shutdown()

    def _cleanup(self) -> None:
        """Clean up resources on exit."""
        logger.debug("Cleaning up resources...")

        if self.tray_manager:
            self.tray_manager.cleanup()

        if self._async_loop and not QASYNC_AVAILABLE:
            try:
                self._async_loop.close()
            except Exception:
                pass

        logger.info("Application shutdown complete")


# =============================================================================
# Command Line Arguments
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog=APP_NAME.lower(),
        description=f"{APP_NAME} - Personal Finance Management",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} v{APP_VERSION}",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Skip splash screen",
    )

    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="Reset configuration to defaults",
    )

    parser.add_argument(
        "--portable",
        action="store_true",
        help="Run in portable mode (store data in application directory)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set log level",
    )

    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Disable system tray icon",
    )

    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Start minimized to system tray",
    )

    return parser.parse_args()


# =============================================================================
# Platform-Specific Setup
# =============================================================================

def setup_windows() -> None:
    """Perform Windows-specific setup."""
    if sys.platform != "win32":
        return

    try:
        # Set application ID for taskbar grouping
        app_id = f"{APP_ORGANIZATION}.{APP_NAME}.Desktop.{APP_VERSION}"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

        # Enable DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        # Enable virtual terminal processing for colored console output
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            mode.value |= 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(handle, mode)
        except Exception:
            pass

    except Exception as e:
        print(f"Warning: Windows setup failed: {e}")


def setup_macos() -> None:
    """Perform macOS-specific setup."""
    if sys.platform != "darwin":
        return
    # macOS-specific setup would go here


def setup_linux() -> None:
    """Perform Linux-specific setup."""
    if sys.platform not in ("linux", "linux2"):
        return

    try:
        os.makedirs(get_data_dir(), exist_ok=True)
    except Exception as e:
        print(f"Warning: Linux setup failed: {e}")


def setup_platform() -> None:
    """Perform platform-specific setup."""
    setup_windows()
    setup_macos()
    setup_linux()


# =============================================================================
# Pre-flight Checks
# =============================================================================

def check_python_version() -> bool:
    """Check if Python version meets requirements."""
    min_version = (3, 10)
    current = sys.version_info[:2]

    if current < min_version:
        print(
            f"Error: Python {min_version[0]}.{min_version[1]}+ required, "
            f"found {current[0]}.{current[1]}"
        )
        return False

    return True


def check_dependencies() -> bool:
    """Check if required dependencies are available."""
    missing = []

    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        missing.append("PyQt6")

    try:
        import aiohttp
    except ImportError:
        missing.append("aiohttp")

    if missing:
        print(f"Error: Missing required dependencies: {', '.join(missing)}")
        print("Please install them with: pip install " + " ".join(missing))
        return False

    return True


def run_preflight_checks() -> bool:
    """Run all pre-flight checks."""
    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
    ]

    for name, check_func in checks:
        try:
            if not check_func():
                return False
        except Exception as e:
            print(f"Error during {name} check: {e}")
            return False

    return True


# =============================================================================
# Main Entry Point
# =============================================================================

def show_error_and_exit(title: str, message: str, exit_code: int = 1) -> NoReturn:
    """Show an error message and exit."""
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        print(f"Error: {title}\n{message}", file=sys.stderr)

    sys.exit(exit_code)


def main() -> int:
    """
    Application entry point.

    Returns:
        Exit code.
    """
    # Parse command line arguments first
    args = parse_arguments()

    # Run pre-flight checks
    if not run_preflight_checks():
        return 1

    # Platform-specific setup
    setup_platform()

    # Set up logging early
    log_level = logging.DEBUG if args.debug else getattr(logging, args.log_level)
    setup_logging(
        level=log_level,
        enable_console=True,
        enable_file=True,
        enable_debug_file=args.debug,
        enable_error_file=True,
        colored_console=True,
        structured_logs=False,
    )

    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.debug(f"Arguments: {args}")
    logger.debug(f"Python: {sys.version}")
    logger.debug(f"Platform: {sys.platform}")
    logger.debug(f"qasync available: {QASYNC_AVAILABLE}")

    # Install global exception handler
    exception_handler = get_exception_handler()
    exception_handler.install()

    # Check for single instance
    single_instance = SingleInstance(f"{APP_ORGANIZATION}.{APP_NAME}")

    if not single_instance.try_lock():
        logger.info("Another instance is already running")

        # Try to activate the existing instance
        if single_instance.send_message("activate"):
            logger.info("Sent activation message to existing instance")
        else:
            logger.warning("Failed to communicate with existing instance")

        return 0

    try:
        # Load configuration
        config_manager = get_config_manager()

        if args.reset_config:
            logger.info("Resetting configuration to defaults")
            config_manager.reset()
            config_manager.save()
        else:
            config_manager.load()

        # Create and run the application
        application = Application(
            argv=sys.argv,
            args=args,
            single_instance=single_instance,
        )

        exit_code = application.run()

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        show_error_and_exit(
            "Unexpected Error",
            f"An unexpected error occurred:\n\n{e}\n\nPlease check the logs for details.",
        )
        exit_code = 1

    finally:
        # Cleanup
        single_instance.release()
        exception_handler.uninstall()
        shutdown_logging()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
