"""
Pecunia Desktop - Application Class

Handles application lifecycle management, signal handlers, auto-updates,
system tray integration, and async event loop management.
"""

import sys
import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional, Any, Callable
from argparse import Namespace
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QMessageBox,
    QSplashScreen,
    QSystemTrayIcon,
    QMenu,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QThread,
    QObject,
    pyqtSignal,
    pyqtSlot,
    QUrl,
    QSettings,
)
from PyQt6.QtGui import QIcon, QPixmap, QAction, QFont, QDesktopServices

from constants import (
    APP_NAME,
    APP_VERSION,
    APP_AUTHOR,
    APP_ORGANIZATION,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)
from config import get_config_manager, get_config, get_data_dir, get_cache_dir
from exceptions import get_exception_handler, PecuniaError, NetworkError

logger = logging.getLogger(__name__)


# =============================================================================
# Async Worker Thread
# =============================================================================

class AsyncWorker(QThread):
    """
    Worker thread for running asyncio event loop.

    Runs an asyncio event loop in a separate thread to handle
    async operations without blocking the Qt event loop.
    """

    task_completed = pyqtSignal(object)  # Result of task
    task_error = pyqtSignal(Exception)   # Exception from task

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the asyncio event loop."""
        return self._loop

    def run(self) -> None:
        """Thread entry point - runs the asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._running = True

        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            self._running = False

    def stop(self) -> None:
        """Stop the asyncio event loop."""
        if self._loop and self._running:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self.wait(5000)  # Wait up to 5 seconds

    def run_coroutine(self, coro) -> None:
        """
        Schedule a coroutine to run in the event loop.

        Args:
            coro: Coroutine to run.
        """
        if self._loop and self._running:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            future.add_done_callback(self._on_future_done)

    def _on_future_done(self, future) -> None:
        """Handle completed future."""
        try:
            result = future.result()
            self.task_completed.emit(result)
        except Exception as e:
            self.task_error.emit(e)


# =============================================================================
# Update Checker
# =============================================================================

class UpdateChecker(QObject):
    """
    Checks for application updates.

    Periodically checks for new versions and notifies the user
    when updates are available.
    """

    update_available = pyqtSignal(str, str)  # (version, download_url)
    check_completed = pyqtSignal(bool)       # has_update
    check_failed = pyqtSignal(str)           # error_message

    UPDATE_CHECK_URL = "https://api.github.com/repos/pecunia/pecunia-desktop/releases/latest"
    CHECK_INTERVAL_HOURS = 24

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check_for_updates)
        self._last_check: Optional[datetime] = None
        self._async_worker: Optional[AsyncWorker] = None

    def set_async_worker(self, worker: AsyncWorker) -> None:
        """Set the async worker for network operations."""
        self._async_worker = worker

    def start_periodic_checks(self, interval_hours: int = CHECK_INTERVAL_HOURS) -> None:
        """Start periodic update checks."""
        interval_ms = interval_hours * 60 * 60 * 1000
        self._timer.start(interval_ms)
        logger.info(f"Started periodic update checks every {interval_hours} hours")

    def stop_periodic_checks(self) -> None:
        """Stop periodic update checks."""
        self._timer.stop()

    @pyqtSlot()
    def check_for_updates(self) -> None:
        """Check for available updates."""
        logger.debug("Checking for updates...")

        if self._async_worker:
            self._async_worker.run_coroutine(self._check_for_updates_async())
        else:
            # Synchronous fallback (not recommended)
            self._check_for_updates_sync()

    async def _check_for_updates_async(self) -> None:
        """Async implementation of update check."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.UPDATE_CHECK_URL,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        latest_version = data.get("tag_name", "").lstrip("v")
                        download_url = data.get("html_url", "")

                        if self._is_newer_version(latest_version):
                            logger.info(f"Update available: {latest_version}")
                            self.update_available.emit(latest_version, download_url)
                            self.check_completed.emit(True)
                        else:
                            logger.debug("No updates available")
                            self.check_completed.emit(False)
                    else:
                        self.check_failed.emit(f"HTTP {response.status}")

        except Exception as e:
            logger.warning(f"Update check failed: {e}")
            self.check_failed.emit(str(e))

        self._last_check = datetime.now()

    def _check_for_updates_sync(self) -> None:
        """Synchronous fallback for update check."""
        try:
            import urllib.request
            import json

            with urllib.request.urlopen(self.UPDATE_CHECK_URL, timeout=30) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")
                download_url = data.get("html_url", "")

                if self._is_newer_version(latest_version):
                    self.update_available.emit(latest_version, download_url)
                    self.check_completed.emit(True)
                else:
                    self.check_completed.emit(False)

        except Exception as e:
            logger.warning(f"Update check failed: {e}")
            self.check_failed.emit(str(e))

        self._last_check = datetime.now()

    def _is_newer_version(self, version: str) -> bool:
        """
        Compare version strings.

        Args:
            version: Version to compare against current.

        Returns:
            True if the given version is newer.
        """
        try:
            current_parts = [int(x) for x in APP_VERSION.split(".")]
            new_parts = [int(x) for x in version.split(".")]

            # Pad to equal length
            max_len = max(len(current_parts), len(new_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            new_parts.extend([0] * (max_len - len(new_parts)))

            return new_parts > current_parts

        except (ValueError, AttributeError):
            return False


# =============================================================================
# System Tray
# =============================================================================

class SystemTray(QObject):
    """
    System tray icon and menu management.

    Provides minimize-to-tray functionality and quick access menu.
    """

    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None

    def setup(self, icon_path: Optional[Path] = None) -> bool:
        """
        Set up the system tray icon.

        Args:
            icon_path: Path to tray icon image.

        Returns:
            True if system tray is available.
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available")
            return False

        self._tray_icon = QSystemTrayIcon(self.parent())

        # Set icon
        if icon_path and icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Create a simple default icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.darkGreen)
            self._tray_icon.setIcon(QIcon(pixmap))

        self._tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        # Create context menu
        self._create_menu()

        # Connect signals
        self._tray_icon.activated.connect(self._on_tray_activated)

        self._tray_icon.show()
        logger.info("System tray icon initialized")
        return True

    def _create_menu(self) -> None:
        """Create the tray context menu."""
        self._menu = QMenu()

        # Show/Hide action
        show_action = QAction("Show Window", self._menu)
        show_action.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(show_action)

        self._menu.addSeparator()

        # Settings action
        settings_action = QAction("Settings...", self._menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)

        self._tray_icon.setContextMenu(self._menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window_requested.emit()

    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 5000,
    ) -> None:
        """Show a tray notification message."""
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, icon, duration_ms)

    def hide(self) -> None:
        """Hide the tray icon."""
        if self._tray_icon:
            self._tray_icon.hide()


# =============================================================================
# Main Window
# =============================================================================

class MainWindow(QMainWindow):
    """
    Main application window.

    Provides the primary UI container with navigation sidebar,
    content area, and status bar.
    """

    close_to_tray = pyqtSignal()

    def __init__(self, minimize_to_tray: bool = False):
        super().__init__()
        self.config_manager = get_config_manager()
        self._minimize_to_tray = minimize_to_tray
        self._force_close = False
        self._setup_window()
        self._setup_ui()
        self._restore_geometry()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Set window icon if available
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "app_icon.png"
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

        # Content area with stacked widget for different views
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

        # Navigation items placeholder
        nav_placeholder = QLabel(
            "Navigation\n\n- Dashboard\n- Transactions\n- Budgets\n- Accounts\n- Settings"
        )
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
        dashboard_label = QLabel(
            "Dashboard View\n\nThis is where the main dashboard will be displayed."
        )
        dashboard_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dashboard_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        dashboard_layout.addWidget(dashboard_label)
        self.content_stack.addWidget(dashboard)

        # Transactions placeholder
        transactions = QWidget()
        transactions_layout = QVBoxLayout(transactions)
        transactions_label = QLabel(
            "Transactions View\n\nThis is where transactions will be listed."
        )
        transactions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transactions_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        transactions_layout.addWidget(transactions_label)
        self.content_stack.addWidget(transactions)

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
            self.config_manager.config.ui.window_maximized = True

    def set_minimize_to_tray(self, enabled: bool) -> None:
        """Enable or disable minimize-to-tray behavior."""
        self._minimize_to_tray = enabled

    def force_close(self) -> None:
        """Force close the window without minimize-to-tray."""
        self._force_close = True
        self.close()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self._save_geometry()
        self.config_manager.save()

        # Check if we should minimize to tray instead
        if self._minimize_to_tray and not self._force_close:
            event.ignore()
            self.hide()
            self.close_to_tray.emit()
            return

        # Mark first run as complete
        if self.config_manager.config.first_run:
            self.config_manager.config.first_run = False
            self.config_manager.save()

        logger.info("Main window closing")
        event.accept()


# =============================================================================
# Application Class
# =============================================================================

class Application(QObject):
    """
    Main application class.

    Handles application initialization, lifecycle management,
    signal handlers, and coordinates all major components.
    """

    shutdown_requested = pyqtSignal()

    def __init__(
        self,
        argv: list,
        args: Namespace,
        single_instance: Any = None,
    ):
        """
        Initialize the application.

        Args:
            argv: Command line arguments.
            args: Parsed arguments namespace.
            single_instance: SingleInstance object for activation callbacks.
        """
        super().__init__()
        self.argv = argv
        self.args = args
        self.single_instance = single_instance

        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
        self.async_worker: Optional[AsyncWorker] = None
        self.update_checker: Optional[UpdateChecker] = None
        self.system_tray: Optional[SystemTray] = None

        self._shutting_down = False

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code.
        """
        try:
            # Initialize Qt application
            self._setup_app()

            # Show splash screen
            splash = None
            if not self.args.no_splash:
                splash = self._show_splash_screen()

            # Initialize components
            self._init_async_worker()
            self._init_update_checker()
            self._init_system_tray()

            # Set up signal handlers
            self._setup_signal_handlers()

            # Set up single instance callback
            if self.single_instance:
                self.single_instance.set_activate_callback(self._activate_window)

            # Create main window
            self.main_window = MainWindow(
                minimize_to_tray=not self.args.no_tray
            )
            self._connect_main_window_signals()

            # Close splash and show main window
            if splash:
                splash.finish(self.main_window)

            if self.args.minimized and self.system_tray:
                # Start minimized to tray
                logger.info("Starting minimized to system tray")
            else:
                self.main_window.show()

            logger.info("Application started successfully")

            # Check for updates on startup
            if self.update_checker:
                QTimer.singleShot(5000, self.update_checker.check_for_updates)

            # Run the event loop
            exit_code = self.app.exec()

            # Cleanup
            self._cleanup()

            return exit_code

        except Exception as e:
            logger.exception(f"Fatal error during application run: {e}")
            if self.app:
                QMessageBox.critical(
                    None,
                    "Fatal Error",
                    f"An unexpected error occurred:\n\n{str(e)}\n\nThe application will now exit.",
                )
            return 1

    def _setup_app(self) -> None:
        """Set up the Qt application."""
        self.app = QApplication(self.argv)
        self.app.setApplicationName(APP_NAME)
        self.app.setApplicationVersion(APP_VERSION)
        self.app.setOrganizationName(APP_ORGANIZATION)

        # Set application-wide font
        font = self.app.font()
        font.setFamily("Segoe UI" if sys.platform == "win32" else "SF Pro Display")
        font.setPointSize(10)
        self.app.setFont(font)

        # Prevent app from quitting when last window closes (for tray mode)
        if not self.args.no_tray:
            self.app.setQuitOnLastWindowClosed(False)

        # Apply global stylesheet
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        """Apply the application stylesheet."""
        config = get_config()
        theme = config.ui.theme

        stylesheet = """
            QMainWindow {
                background-color: #f5f6fa;
            }

            QWidget {
                font-family: "Segoe UI", "SF Pro Display", sans-serif;
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
        """

        self.app.setStyleSheet(stylesheet)

    def _show_splash_screen(self) -> QSplashScreen:
        """Show splash screen during startup."""
        # Try to load splash image
        splash_path = Path(__file__).parent.parent / "resources" / "splash.png"

        if splash_path.exists():
            splash_pixmap = QPixmap(str(splash_path))
        else:
            # Create a simple splash screen
            splash_pixmap = QPixmap(400, 300)
            splash_pixmap.fill(Qt.GlobalColor.white)

        splash = QSplashScreen(splash_pixmap)
        splash.showMessage(
            f"{APP_NAME}\nv{APP_VERSION}\n\nLoading...",
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.darkGray,
        )
        splash.show()
        self.app.processEvents()

        return splash

    def _init_async_worker(self) -> None:
        """Initialize the async worker thread."""
        self.async_worker = AsyncWorker(self)
        self.async_worker.task_error.connect(self._on_async_error)
        self.async_worker.start()
        logger.debug("Async worker thread started")

    def _init_update_checker(self) -> None:
        """Initialize the update checker."""
        self.update_checker = UpdateChecker(self)

        if self.async_worker:
            self.update_checker.set_async_worker(self.async_worker)

        self.update_checker.update_available.connect(self._on_update_available)
        self.update_checker.start_periodic_checks()

    def _init_system_tray(self) -> None:
        """Initialize the system tray icon."""
        if self.args.no_tray:
            return

        self.system_tray = SystemTray(self)

        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "tray_icon.png"
        if not icon_path.exists():
            icon_path = Path(__file__).parent.parent / "resources" / "icons" / "app_icon.png"

        if self.system_tray.setup(icon_path if icon_path.exists() else None):
            self.system_tray.show_window_requested.connect(self._activate_window)
            self.system_tray.quit_requested.connect(self._quit)
            self.system_tray.settings_requested.connect(self._show_settings)

    def _setup_signal_handlers(self) -> None:
        """Set up OS signal handlers for graceful shutdown."""
        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Handle SIGTERM
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self._signal_handler)

        # Set up a timer to allow signal processing
        self._signal_timer = QTimer()
        self._signal_timer.start(500)
        self._signal_timer.timeout.connect(lambda: None)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle OS signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self._quit()

    def _connect_main_window_signals(self) -> None:
        """Connect main window signals."""
        if self.main_window:
            self.main_window.close_to_tray.connect(self._on_close_to_tray)

    @pyqtSlot()
    def _activate_window(self) -> None:
        """Activate and show the main window."""
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

            if self.main_window.isMinimized():
                self.main_window.showNormal()

            logger.debug("Main window activated")

    @pyqtSlot()
    def _on_close_to_tray(self) -> None:
        """Handle main window close-to-tray."""
        if self.system_tray:
            self.system_tray.show_message(
                APP_NAME,
                "Application minimized to tray. Double-click to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    @pyqtSlot(str, str)
    def _on_update_available(self, version: str, download_url: str) -> None:
        """Handle update available notification."""
        logger.info(f"Update available: {version}")

        if self.system_tray:
            self.system_tray.show_message(
                "Update Available",
                f"A new version ({version}) is available.",
                QSystemTrayIcon.MessageIcon.Information,
            )

        # Show update dialog if main window is visible
        if self.main_window and self.main_window.isVisible():
            reply = QMessageBox.question(
                self.main_window,
                "Update Available",
                f"A new version ({version}) is available.\n\n"
                "Would you like to download it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                from urllib.parse import urlparse
                parsed = urlparse(download_url)
                if parsed.scheme in ('https', 'http') and parsed.hostname:
                    QDesktopServices.openUrl(QUrl(download_url))
                else:
                    logger.warning(f"Blocked opening URL with invalid scheme or host: {parsed.scheme}")

    @pyqtSlot(Exception)
    def _on_async_error(self, error: Exception) -> None:
        """Handle async worker errors."""
        logger.error(f"Async task error: {error}")

    @pyqtSlot()
    def _show_settings(self) -> None:
        """Show the settings dialog."""
        if self.main_window:
            self._activate_window()
            # TODO: Navigate to settings view
            self.main_window.statusBar().showMessage("Settings view...")

    @pyqtSlot()
    def _quit(self) -> None:
        """Quit the application."""
        if self._shutting_down:
            return

        self._shutting_down = True
        logger.info("Application quit requested")

        # Force close main window
        if self.main_window:
            self.main_window.force_close()

        # Quit the application
        if self.app:
            self.app.quit()

    def _cleanup(self) -> None:
        """Clean up resources on exit."""
        logger.info("Cleaning up application resources")

        # Stop update checker
        if self.update_checker:
            self.update_checker.stop_periodic_checks()

        # Stop async worker
        if self.async_worker:
            self.async_worker.stop()

        # Hide system tray
        if self.system_tray:
            self.system_tray.hide()

        logger.info("Application shutdown complete")
