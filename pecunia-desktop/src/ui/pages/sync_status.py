"""
Sync Status Widget Module

Widget for displaying real-time synchronization status, progress,
and error information for bank account data syncing.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QSizePolicy, QSpacerItem, QScrollArea,
    QStackedWidget, QMessageBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt6.QtGui import QFont, QColor
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto


class SyncState(Enum):
    """Synchronization state enumeration."""
    IDLE = auto()
    SYNCING = auto()
    SUCCESS = auto()
    ERROR = auto()
    PARTIAL = auto()
    OFFLINE = auto()


@dataclass
class SyncProgress:
    """Progress information for a sync operation."""
    current_step: int = 0
    total_steps: int = 0
    current_account: Optional[str] = None
    accounts_completed: int = 0
    total_accounts: int = 0
    transactions_added: int = 0
    transactions_modified: int = 0
    transactions_removed: int = 0
    message: str = ""
    percentage: float = 0.0


@dataclass
class SyncError:
    """Error information from a sync operation."""
    code: str
    message: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    is_recoverable: bool = True
    timestamp: datetime = field(default_factory=datetime.now)


class AnimatedProgressBar(QProgressBar):
    """Progress bar with smooth animations."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._animation: Optional[QPropertyAnimation] = None
        self._target_value = 0
        self._setup_ui()

    def _setup_ui(self):
        """Set up the progress bar UI."""
        self.setTextVisible(False)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setMinimumHeight(8)
        self.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #1976D2;
                border-radius: 4px;
            }
        """)

    def set_value_animated(self, value: int, duration: int = 300):
        """Set value with smooth animation."""
        if self._animation:
            self._animation.stop()

        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(duration)
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    def set_indeterminate(self, enabled: bool = True):
        """Set indeterminate (pulsing) mode."""
        if enabled:
            self.setRange(0, 0)
        else:
            self.setRange(0, 100)


class SyncStatusIndicator(QFrame):
    """Status indicator with icon and text."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._state = SyncState.IDLE
        self._setup_ui()

    def _setup_ui(self):
        """Set up the indicator UI."""
        self.setObjectName("syncStatusIndicator")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Status dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(10, 10)
        self.status_dot.setStyleSheet("""
            background-color: #9E9E9E;
            border-radius: 5px;
        """)
        layout.addWidget(self.status_dot)

        # Status text
        self.status_text = QLabel("Ready")
        self.status_text.setFont(QFont("Segoe UI", 10))
        self.status_text.setStyleSheet("color: #666666;")
        layout.addWidget(self.status_text)

        layout.addStretch()

    def set_state(self, state: SyncState, message: Optional[str] = None):
        """Set the current sync state."""
        self._state = state

        state_config = {
            SyncState.IDLE: ("#9E9E9E", "Ready", "#666666"),
            SyncState.SYNCING: ("#2196F3", "Syncing...", "#1976D2"),
            SyncState.SUCCESS: ("#4CAF50", "Synced", "#4CAF50"),
            SyncState.ERROR: ("#F44336", "Error", "#F44336"),
            SyncState.PARTIAL: ("#FF9800", "Partial Sync", "#FF9800"),
            SyncState.OFFLINE: ("#9E9E9E", "Offline", "#9E9E9E"),
        }

        dot_color, default_text, text_color = state_config.get(
            state, ("#9E9E9E", "Unknown", "#666666")
        )

        self.status_dot.setStyleSheet(f"""
            background-color: {dot_color};
            border-radius: 5px;
        """)

        display_text = message if message else default_text
        self.status_text.setText(display_text)
        self.status_text.setStyleSheet(f"color: {text_color};")

        # Add pulsing animation for syncing state
        if state == SyncState.SYNCING:
            self._start_pulse_animation()
        else:
            self._stop_pulse_animation()

    def _start_pulse_animation(self):
        """Start pulsing animation for syncing state."""
        # Could implement with QPropertyAnimation on opacity
        pass

    def _stop_pulse_animation(self):
        """Stop pulsing animation."""
        pass


class SyncErrorWidget(QFrame):
    """Widget displaying sync error information."""

    retry_requested = pyqtSignal()
    dismiss_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._error: Optional[SyncError] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the error widget UI."""
        self.setObjectName("syncErrorWidget")
        self.setStyleSheet("""
            QFrame#syncErrorWidget {
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        # Error icon
        icon_label = QLabel()
        icon_label.setText("\u26A0")  # Warning sign
        icon_label.setFont(QFont("Segoe UI", 16))
        icon_label.setStyleSheet("color: #F44336;")
        header_layout.addWidget(icon_label)

        # Title
        self.title_label = QLabel("Sync Error")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: #C62828;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Dismiss button
        dismiss_btn = QPushButton("\u2715")  # X mark
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #C62828;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FFCDD2;
                border-radius: 12px;
            }
        """)
        dismiss_btn.clicked.connect(self.dismiss_requested.emit)
        header_layout.addWidget(dismiss_btn)

        layout.addLayout(header_layout)

        # Error message
        self.message_label = QLabel("An error occurred during synchronization.")
        self.message_label.setFont(QFont("Segoe UI", 10))
        self.message_label.setStyleSheet("color: #B71C1C;")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        # Account info (if applicable)
        self.account_label = QLabel()
        self.account_label.setFont(QFont("Segoe UI", 9))
        self.account_label.setStyleSheet("color: #C62828;")
        self.account_label.setVisible(False)
        layout.addWidget(self.account_label)

        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setFont(QFont("Segoe UI", 9))
        self.retry_btn.setMinimumSize(80, 32)
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #E53935;
            }
        """)
        self.retry_btn.clicked.connect(self.retry_requested.emit)
        actions_layout.addWidget(self.retry_btn)

        actions_layout.addStretch()

        layout.addLayout(actions_layout)

    def set_error(self, error: SyncError):
        """Set the error to display."""
        self._error = error
        self.message_label.setText(error.message)

        if error.account_name:
            self.account_label.setText(f"Account: {error.account_name}")
            self.account_label.setVisible(True)
        else:
            self.account_label.setVisible(False)

        self.retry_btn.setVisible(error.is_recoverable)


class SyncDetailsWidget(QFrame):
    """Widget showing detailed sync progress information."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the details widget UI."""
        self.setObjectName("syncDetailsWidget")
        self.setStyleSheet("""
            QFrame#syncDetailsWidget {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Current account
        self.account_label = QLabel("Syncing...")
        self.account_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.account_label.setStyleSheet("color: #333333;")
        layout.addWidget(self.account_label)

        # Progress bar
        self.progress_bar = AnimatedProgressBar()
        layout.addWidget(self.progress_bar)

        # Stats grid
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(24)

        # Accounts progress
        accounts_widget = QWidget()
        accounts_layout = QVBoxLayout(accounts_widget)
        accounts_layout.setContentsMargins(0, 0, 0, 0)
        accounts_layout.setSpacing(2)

        accounts_title = QLabel("Accounts")
        accounts_title.setFont(QFont("Segoe UI", 9))
        accounts_title.setStyleSheet("color: #888888;")
        accounts_layout.addWidget(accounts_title)

        self.accounts_label = QLabel("0 / 0")
        self.accounts_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.accounts_label.setStyleSheet("color: #333333;")
        accounts_layout.addWidget(self.accounts_label)

        stats_layout.addWidget(accounts_widget)

        # Transactions added
        added_widget = QWidget()
        added_layout = QVBoxLayout(added_widget)
        added_layout.setContentsMargins(0, 0, 0, 0)
        added_layout.setSpacing(2)

        added_title = QLabel("Added")
        added_title.setFont(QFont("Segoe UI", 9))
        added_title.setStyleSheet("color: #888888;")
        added_layout.addWidget(added_title)

        self.added_label = QLabel("0")
        self.added_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.added_label.setStyleSheet("color: #4CAF50;")
        added_layout.addWidget(self.added_label)

        stats_layout.addWidget(added_widget)

        # Transactions modified
        modified_widget = QWidget()
        modified_layout = QVBoxLayout(modified_widget)
        modified_layout.setContentsMargins(0, 0, 0, 0)
        modified_layout.setSpacing(2)

        modified_title = QLabel("Modified")
        modified_title.setFont(QFont("Segoe UI", 9))
        modified_title.setStyleSheet("color: #888888;")
        modified_layout.addWidget(modified_title)

        self.modified_label = QLabel("0")
        self.modified_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.modified_label.setStyleSheet("color: #FF9800;")
        modified_layout.addWidget(self.modified_label)

        stats_layout.addWidget(modified_widget)

        stats_layout.addStretch()

        layout.addLayout(stats_layout)

    def update_progress(self, progress: SyncProgress):
        """Update the displayed progress."""
        if progress.current_account:
            self.account_label.setText(f"Syncing {progress.current_account}...")
        else:
            self.account_label.setText("Syncing...")

        # Update progress bar
        if progress.total_accounts > 0:
            percentage = int(
                (progress.accounts_completed / progress.total_accounts) * 100
            )
            self.progress_bar.set_value_animated(percentage)
        else:
            self.progress_bar.set_indeterminate(True)

        # Update stats
        self.accounts_label.setText(
            f"{progress.accounts_completed} / {progress.total_accounts}"
        )
        self.added_label.setText(str(progress.transactions_added))
        self.modified_label.setText(str(progress.transactions_modified))

    def reset(self):
        """Reset the widget to initial state."""
        self.account_label.setText("Ready to sync")
        self.progress_bar.setValue(0)
        self.accounts_label.setText("0 / 0")
        self.added_label.setText("0")
        self.modified_label.setText("0")


class SyncStatusWidget(QWidget):
    """
    Widget for displaying synchronization status and controls.

    Features:
    - Real-time sync progress indication
    - Last sync time display
    - Manual sync trigger button
    - Error display with retry option
    - Detailed progress during sync

    Signals:
        sync_requested: Request to start synchronization
        cancel_requested: Request to cancel current sync
        retry_requested: Request to retry after error
    """

    sync_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(
        self,
        compact: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._compact = compact
        self._state = SyncState.IDLE
        self._last_synced: Optional[datetime] = None
        self._current_progress: Optional[SyncProgress] = None
        self._current_error: Optional[SyncError] = None

        self._setup_ui()
        self._setup_timers()

    def _setup_ui(self):
        """Set up the widget UI."""
        self.setObjectName("syncStatusWidget")

        if self._compact:
            self._setup_compact_ui()
        else:
            self._setup_full_ui()

    def _setup_compact_ui(self):
        """Set up compact version of the widget."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Status indicator
        self.status_indicator = SyncStatusIndicator()
        layout.addWidget(self.status_indicator)

        # Last synced
        self.last_synced_label = QLabel("Never synced")
        self.last_synced_label.setFont(QFont("Segoe UI", 9))
        self.last_synced_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.last_synced_label)

        layout.addStretch()

        # Sync button
        self.sync_btn = QPushButton("Sync")
        self.sync_btn.setFont(QFont("Segoe UI", 9))
        self.sync_btn.setMinimumSize(70, 28)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        layout.addWidget(self.sync_btn)

    def _setup_full_ui(self):
        """Set up full version of the widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Header
        header_frame = QFrame()
        header_frame.setObjectName("syncHeader")
        header_frame.setStyleSheet("""
            QFrame#syncHeader {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(16)

        # Status indicator
        self.status_indicator = SyncStatusIndicator()
        header_layout.addWidget(self.status_indicator)

        header_layout.addStretch()

        # Last synced
        last_sync_layout = QVBoxLayout()
        last_sync_layout.setSpacing(2)

        last_sync_title = QLabel("Last Synced")
        last_sync_title.setFont(QFont("Segoe UI", 9))
        last_sync_title.setStyleSheet("color: #888888;")
        last_sync_layout.addWidget(last_sync_title)

        self.last_synced_label = QLabel("Never")
        self.last_synced_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.last_synced_label.setStyleSheet("color: #333333;")
        last_sync_layout.addWidget(self.last_synced_label)

        header_layout.addLayout(last_sync_layout)

        # Sync button
        self.sync_btn = QPushButton("Sync Now")
        self.sync_btn.setFont(QFont("Segoe UI", 10))
        self.sync_btn.setMinimumSize(100, 36)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        header_layout.addWidget(self.sync_btn)

        layout.addWidget(header_frame)

        # Stacked widget for different states
        self.content_stack = QStackedWidget()

        # Idle state (empty)
        idle_widget = QWidget()
        self.content_stack.addWidget(idle_widget)

        # Syncing state - progress details
        self.details_widget = SyncDetailsWidget()
        self.content_stack.addWidget(self.details_widget)

        # Error state
        self.error_widget = SyncErrorWidget()
        self.error_widget.retry_requested.connect(self._on_retry_clicked)
        self.error_widget.dismiss_requested.connect(self._dismiss_error)
        self.content_stack.addWidget(self.error_widget)

        layout.addWidget(self.content_stack)

        # Initially show idle state
        self.content_stack.setCurrentIndex(0)

    def _setup_timers(self):
        """Set up update timers."""
        # Timer for updating relative time display
        self.time_update_timer = QTimer(self)
        self.time_update_timer.timeout.connect(self._update_last_synced_display)
        self.time_update_timer.start(60000)  # Update every minute

    def _on_sync_clicked(self):
        """Handle sync button click."""
        if self._state == SyncState.SYNCING:
            self.cancel_requested.emit()
        else:
            self.sync_requested.emit()

    def _on_retry_clicked(self):
        """Handle retry button click."""
        self.retry_requested.emit()

    def _dismiss_error(self):
        """Dismiss error and return to idle state."""
        self._current_error = None
        self.set_state(SyncState.IDLE)

    def _update_last_synced_display(self):
        """Update the last synced time display."""
        if self._last_synced:
            self.last_synced_label.setText(
                self._format_relative_time(self._last_synced)
            )

    def _format_relative_time(self, dt: datetime) -> str:
        """Format datetime as relative time string."""
        now = datetime.now()
        diff = now - dt

        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")

    # Public methods

    def set_state(self, state: SyncState, message: Optional[str] = None):
        """
        Set the current sync state.

        Args:
            state: The new sync state
            message: Optional custom message to display
        """
        self._state = state
        self.status_indicator.set_state(state, message)

        # Update button
        if state == SyncState.SYNCING:
            self.sync_btn.setText("Cancel" if not self._compact else "...")
            self.sync_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
        else:
            self.sync_btn.setText("Sync Now" if not self._compact else "Sync")
            self.sync_btn.setEnabled(state != SyncState.OFFLINE)
            self.sync_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                }
            """)

        # Update content stack (full mode only)
        if not self._compact and hasattr(self, 'content_stack'):
            if state == SyncState.SYNCING:
                self.content_stack.setCurrentWidget(self.details_widget)
            elif state == SyncState.ERROR and self._current_error:
                self.content_stack.setCurrentWidget(self.error_widget)
            else:
                self.content_stack.setCurrentIndex(0)

    def set_last_synced(self, timestamp: datetime):
        """Set the last sync timestamp."""
        self._last_synced = timestamp
        self._update_last_synced_display()

    def update_progress(self, progress: SyncProgress):
        """
        Update sync progress.

        Args:
            progress: Current sync progress information
        """
        self._current_progress = progress

        if not self._compact and hasattr(self, 'details_widget'):
            self.details_widget.update_progress(progress)

        # Update status message
        if progress.message:
            self.status_indicator.set_state(SyncState.SYNCING, progress.message)

    def set_error(self, error: SyncError):
        """
        Display a sync error.

        Args:
            error: Error information to display
        """
        self._current_error = error

        if not self._compact and hasattr(self, 'error_widget'):
            self.error_widget.set_error(error)

        self.set_state(SyncState.ERROR, error.message)

    def start_sync(self):
        """Start sync operation (visual update)."""
        self.set_state(SyncState.SYNCING, "Starting sync...")

        if not self._compact and hasattr(self, 'details_widget'):
            self.details_widget.reset()

    def finish_sync(
        self,
        success: bool = True,
        transactions_added: int = 0,
        transactions_modified: int = 0
    ):
        """
        Finish sync operation.

        Args:
            success: Whether sync was successful
            transactions_added: Number of transactions added
            transactions_modified: Number of transactions modified
        """
        self._last_synced = datetime.now()
        self._update_last_synced_display()

        if success:
            total_changes = transactions_added + transactions_modified
            if total_changes > 0:
                message = f"{total_changes} transaction{'s' if total_changes != 1 else ''} updated"
            else:
                message = "Up to date"
            self.set_state(SyncState.SUCCESS, message)

            # Auto-reset to idle after delay
            QTimer.singleShot(3000, lambda: self.set_state(SyncState.IDLE))
        else:
            self.set_state(SyncState.ERROR)

    def set_offline(self, is_offline: bool):
        """Set offline state."""
        if is_offline:
            self.set_state(SyncState.OFFLINE, "No internet connection")
        else:
            self.set_state(SyncState.IDLE)

    def reset(self):
        """Reset the widget to initial state."""
        self._state = SyncState.IDLE
        self._current_progress = None
        self._current_error = None
        self.set_state(SyncState.IDLE)

        if not self._compact and hasattr(self, 'details_widget'):
            self.details_widget.reset()


class SyncStatusBar(QFrame):
    """
    Compact sync status bar for embedding in other widgets.

    A simplified version of SyncStatusWidget designed to be
    embedded in headers or toolbars.
    """

    sync_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._state = SyncState.IDLE
        self._last_synced: Optional[datetime] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the status bar UI."""
        self.setObjectName("syncStatusBar")
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QFrame#syncStatusBar {
                background-color: transparent;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        # Status dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet("""
            background-color: #9E9E9E;
            border-radius: 4px;
        """)
        layout.addWidget(self.status_dot)

        # Status text
        self.status_text = QLabel("Ready")
        self.status_text.setFont(QFont("Segoe UI", 9))
        self.status_text.setStyleSheet("color: #666666;")
        layout.addWidget(self.status_text)

        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(separator)

        # Last synced
        self.last_synced_label = QLabel("Never synced")
        self.last_synced_label.setFont(QFont("Segoe UI", 9))
        self.last_synced_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.last_synced_label)

        layout.addStretch()

        # Sync icon button
        self.sync_btn = QPushButton()
        self.sync_btn.setText("\u21BB")  # Refresh symbol
        self.sync_btn.setFixedSize(28, 28)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setToolTip("Sync now")
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #1976D2;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #E3F2FD;
                border-radius: 14px;
            }
            QPushButton:disabled {
                color: #BDBDBD;
            }
        """)
        self.sync_btn.clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_btn)

    def set_state(self, state: SyncState, message: Optional[str] = None):
        """Set the current sync state."""
        self._state = state

        state_config = {
            SyncState.IDLE: ("#9E9E9E", "Ready"),
            SyncState.SYNCING: ("#2196F3", "Syncing..."),
            SyncState.SUCCESS: ("#4CAF50", "Synced"),
            SyncState.ERROR: ("#F44336", "Sync error"),
            SyncState.PARTIAL: ("#FF9800", "Partial sync"),
            SyncState.OFFLINE: ("#9E9E9E", "Offline"),
        }

        dot_color, default_text = state_config.get(state, ("#9E9E9E", "Unknown"))

        self.status_dot.setStyleSheet(f"""
            background-color: {dot_color};
            border-radius: 4px;
        """)

        self.status_text.setText(message if message else default_text)
        self.sync_btn.setEnabled(state not in [SyncState.SYNCING, SyncState.OFFLINE])

    def set_last_synced(self, timestamp: datetime):
        """Set the last sync timestamp."""
        self._last_synced = timestamp
        self.last_synced_label.setText(self._format_relative_time(timestamp))

    def _format_relative_time(self, dt: datetime) -> str:
        """Format datetime as relative time string."""
        now = datetime.now()
        diff = now - dt

        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            return dt.strftime("%b %d")


# Convenience functions

def create_sync_status_widget(
    compact: bool = False,
    parent: Optional[QWidget] = None
) -> SyncStatusWidget:
    """Create and return a new SyncStatusWidget instance."""
    return SyncStatusWidget(compact=compact, parent=parent)


def create_sync_status_bar(parent: Optional[QWidget] = None) -> SyncStatusBar:
    """Create and return a new SyncStatusBar instance."""
    return SyncStatusBar(parent)
