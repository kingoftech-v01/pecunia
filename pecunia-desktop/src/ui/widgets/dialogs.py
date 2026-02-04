"""
Dialog widgets for Pecunia Desktop.

Provides common dialog components including confirmation, message,
input, and progress dialogs.
"""

from typing import Optional, Callable
from enum import Enum

from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QPoint
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QProgressBar, QWidget,
    QFrame, QGraphicsOpacityEffect, QApplication,
    QTextEdit, QSizePolicy
)
from PyQt6.QtGui import QFont, QKeyEvent

from ..styles.theme import get_theme_manager


class DialogType(Enum):
    """Types of message dialogs."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    QUESTION = "question"


class BaseDialog(QDialog):
    """
    Base dialog class with consistent styling and animations.

    Provides common functionality for all dialogs including
    fade animations and theme-aware styling.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        modal: bool = True,
        animate: bool = True
    ):
        """
        Initialize base dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            modal: Whether dialog is modal
            animate: Whether to use fade animations
        """
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(modal)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._animate = animate
        self._setup_base_ui()

        if animate:
            self._setup_animations()

    def _setup_base_ui(self) -> None:
        """Setup base UI structure."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container with shadow effect
        self._container = QFrame()
        self._container.setObjectName("dialogContainer")
        self._container.setStyleSheet(f"""
            #dialogContainer {{
                background-color: {palette.surface};
                border: 1px solid {palette.border};
                border-radius: 12px;
            }}
        """)

        main_layout.addWidget(self._container)

        # Container layout
        self._content_layout = QVBoxLayout(self._container)
        self._content_layout.setContentsMargins(24, 24, 24, 24)
        self._content_layout.setSpacing(16)

    def _setup_animations(self) -> None:
        """Setup fade animations."""
        self._opacity_effect = QGraphicsOpacityEffect(self._container)
        self._opacity_effect.setOpacity(0.0)
        self._container.setGraphicsEffect(self._opacity_effect)

        self._fade_in_anim = QPropertyAnimation(
            self._opacity_effect, b"opacity"
        )
        self._fade_in_anim.setDuration(150)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out_anim = QPropertyAnimation(
            self._opacity_effect, b"opacity"
        )
        self._fade_out_anim.setDuration(100)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out_anim.finished.connect(super().accept)

    def showEvent(self, event) -> None:
        """Handle show event with animation."""
        super().showEvent(event)
        if self._animate:
            self._fade_in_anim.start()

        # Center on parent or screen
        self._center_on_parent()

    def _center_on_parent(self) -> None:
        """Center dialog on parent window or screen."""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_rect = screen.availableGeometry()
                x = (screen_rect.width() - self.width()) // 2
                y = (screen_rect.height() - self.height()) // 2
                self.move(x, y)

    def accept(self) -> None:
        """Accept dialog with animation."""
        if self._animate:
            self._fade_out_anim.finished.disconnect()
            self._fade_out_anim.finished.connect(super().accept)
            self._fade_out_anim.start()
        else:
            super().accept()

    def reject(self) -> None:
        """Reject dialog with animation."""
        if self._animate:
            self._fade_out_anim.finished.disconnect()
            self._fade_out_anim.finished.connect(super().reject)
            self._fade_out_anim.start()
        else:
            super().reject()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class ConfirmDialog(BaseDialog):
    """
    Confirmation dialog with Yes/No buttons.

    Displays a message and asks for user confirmation.

    Usage:
        dialog = ConfirmDialog(
            title="Delete Transaction",
            message="Are you sure you want to delete this transaction?",
            confirm_text="Delete",
            cancel_text="Cancel",
            destructive=True
        )
        if dialog.exec():
            # User confirmed
            pass
    """

    confirmed = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Confirm",
        message: str = "",
        confirm_text: str = "Yes",
        cancel_text: str = "No",
        destructive: bool = False
    ):
        """
        Initialize confirmation dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            message: Confirmation message
            confirm_text: Text for confirm button
            cancel_text: Text for cancel button
            destructive: Whether action is destructive (uses red button)
        """
        super().__init__(parent, title)

        self._destructive = destructive
        self._setup_ui(title, message, confirm_text, cancel_text)

        self.setMinimumWidth(400)
        self.adjustSize()

    def _setup_ui(
        self,
        title: str,
        message: str,
        confirm_text: str,
        cancel_text: str
    ) -> None:
        """Setup dialog UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {palette.text_primary};
        """)
        self._content_layout.addWidget(title_label)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            font-size: 14px;
            color: {palette.text_secondary};
        """)
        self._content_layout.addWidget(message_label)

        # Spacer
        self._content_layout.addSpacing(8)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton(cancel_text)
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(cancel_btn)

        # Confirm button
        confirm_btn = QPushButton(confirm_text)
        if self._destructive:
            confirm_btn.setObjectName("dangerButton")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(self._on_confirm)
        confirm_btn.setDefault(True)
        button_layout.addWidget(confirm_btn)

        self._content_layout.addLayout(button_layout)

    def _on_confirm(self) -> None:
        """Handle confirm button click."""
        self.confirmed.emit()
        self.accept()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.cancelled.emit()
        self.reject()


class MessageDialog(BaseDialog):
    """
    Message dialog for info, warning, error, and success messages.

    Displays a message with an icon and OK button.

    Usage:
        dialog = MessageDialog(
            dialog_type=DialogType.ERROR,
            title="Error",
            message="Failed to save transaction."
        )
        dialog.exec()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        dialog_type: DialogType = DialogType.INFO,
        title: str = "",
        message: str = "",
        details: Optional[str] = None
    ):
        """
        Initialize message dialog.

        Args:
            parent: Parent widget
            dialog_type: Type of message (info, warning, error, success)
            title: Dialog title
            message: Main message
            details: Optional detailed text
        """
        super().__init__(parent, title)

        self._dialog_type = dialog_type
        self._setup_ui(title, message, details)

        self.setMinimumWidth(400)
        self.adjustSize()

    def _get_icon_color(self) -> str:
        """Get icon color based on dialog type."""
        theme = get_theme_manager()
        palette = theme.current_palette

        colors = {
            DialogType.INFO: palette.info,
            DialogType.WARNING: palette.warning,
            DialogType.ERROR: palette.error,
            DialogType.SUCCESS: palette.success,
            DialogType.QUESTION: palette.primary
        }
        return colors.get(self._dialog_type, palette.info)

    def _get_icon_symbol(self) -> str:
        """Get icon symbol based on dialog type."""
        symbols = {
            DialogType.INFO: "i",
            DialogType.WARNING: "!",
            DialogType.ERROR: "X",
            DialogType.SUCCESS: "\u2713",  # Checkmark
            DialogType.QUESTION: "?"
        }
        return symbols.get(self._dialog_type, "i")

    def _setup_ui(
        self,
        title: str,
        message: str,
        details: Optional[str]
    ) -> None:
        """Setup dialog UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Header with icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        # Icon
        icon_color = self._get_icon_color()
        icon_label = QLabel(self._get_icon_symbol())
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            background-color: {icon_color}20;
            color: {icon_color};
            border-radius: 24px;
            font-size: 24px;
            font-weight: bold;
        """)
        header_layout.addWidget(icon_label)

        # Title and message
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {palette.text_primary};
        """)
        text_layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            font-size: 14px;
            color: {palette.text_secondary};
        """)
        text_layout.addWidget(message_label)

        header_layout.addLayout(text_layout, 1)
        self._content_layout.addLayout(header_layout)

        # Details (expandable)
        if details:
            details_text = QTextEdit()
            details_text.setPlainText(details)
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(100)
            details_text.setStyleSheet(f"""
                background-color: {palette.background_alt};
                border: 1px solid {palette.border};
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 12px;
            """)
            self._content_layout.addWidget(details_text)

        # OK button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        ok_btn.setMinimumWidth(100)
        button_layout.addWidget(ok_btn)

        self._content_layout.addLayout(button_layout)


class InputDialog(BaseDialog):
    """
    Single input dialog.

    Displays a text input field with OK/Cancel buttons.

    Usage:
        dialog = InputDialog(
            title="Rename Account",
            label="Account name:",
            initial_value="My Account",
            placeholder="Enter account name"
        )
        if dialog.exec():
            new_name = dialog.get_value()
    """

    value_submitted = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Input",
        label: str = "",
        initial_value: str = "",
        placeholder: str = "",
        password_mode: bool = False,
        validator: Optional[Callable[[str], bool]] = None,
        error_message: str = "Invalid input"
    ):
        """
        Initialize input dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            label: Label for input field
            initial_value: Initial input value
            placeholder: Placeholder text
            password_mode: Whether to hide input
            validator: Optional validation function
            error_message: Error message for invalid input
        """
        super().__init__(parent, title)

        self._validator = validator
        self._error_message = error_message
        self._setup_ui(title, label, initial_value, placeholder, password_mode)

        self.setMinimumWidth(400)
        self.adjustSize()

    def _setup_ui(
        self,
        title: str,
        label: str,
        initial_value: str,
        placeholder: str,
        password_mode: bool
    ) -> None:
        """Setup dialog UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {palette.text_primary};
        """)
        self._content_layout.addWidget(title_label)

        # Label
        if label:
            input_label = QLabel(label)
            input_label.setStyleSheet(f"""
                font-size: 14px;
                color: {palette.text_secondary};
            """)
            self._content_layout.addWidget(input_label)

        # Input field
        self._input = QLineEdit()
        self._input.setText(initial_value)
        self._input.setPlaceholderText(placeholder)
        if password_mode:
            self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._on_submit)
        self._content_layout.addWidget(self._input)

        # Error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"""
            font-size: 12px;
            color: {palette.error};
        """)
        self._error_label.hide()
        self._content_layout.addWidget(self._error_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self._ok_btn = QPushButton("OK")
        self._ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ok_btn.clicked.connect(self._on_submit)
        self._ok_btn.setDefault(True)
        button_layout.addWidget(self._ok_btn)

        self._content_layout.addLayout(button_layout)

        # Focus input
        QTimer.singleShot(0, self._input.setFocus)

    def _on_text_changed(self, text: str) -> None:
        """Handle text change."""
        self._error_label.hide()
        if hasattr(self, '_input'):
            self._input.setProperty("error", False)
            self._input.style().polish(self._input)

    def _on_submit(self) -> None:
        """Handle submit."""
        value = self._input.text()

        if self._validator:
            if not self._validator(value):
                self._show_error(self._error_message)
                return

        self.value_submitted.emit(value)
        self.accept()

    def _show_error(self, message: str) -> None:
        """Show error message."""
        self._error_label.setText(message)
        self._error_label.show()
        self._input.setProperty("error", True)
        self._input.style().polish(self._input)
        self._input.setFocus()

    def get_value(self) -> str:
        """Get the input value."""
        return self._input.text()

    def set_value(self, value: str) -> None:
        """Set the input value."""
        self._input.setText(value)


class ProgressDialog(BaseDialog):
    """
    Progress dialog with cancel button.

    Displays a progress bar with optional cancel functionality.

    Usage:
        dialog = ProgressDialog(
            title="Importing Transactions",
            message="Please wait...",
            cancellable=True
        )
        dialog.show()

        # Update progress
        dialog.set_progress(50)
        dialog.set_message("Processing file...")

        # Complete
        dialog.set_progress(100)
        dialog.accept()
    """

    cancelled = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Processing",
        message: str = "Please wait...",
        cancellable: bool = True,
        indeterminate: bool = False,
        auto_close: bool = True
    ):
        """
        Initialize progress dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            message: Status message
            cancellable: Whether cancel button is shown
            indeterminate: Whether progress is indeterminate
            auto_close: Whether to close on completion
        """
        super().__init__(parent, title, modal=True, animate=False)

        self._cancellable = cancellable
        self._indeterminate = indeterminate
        self._auto_close = auto_close
        self._is_cancelled = False

        self._setup_ui(title, message)

        self.setMinimumWidth(400)
        self.adjustSize()

    def _setup_ui(self, title: str, message: str) -> None:
        """Setup dialog UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {palette.text_primary};
        """)
        self._content_layout.addWidget(title_label)

        # Message
        self._message_label = QLabel(message)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet(f"""
            font-size: 14px;
            color: {palette.text_secondary};
        """)
        self._content_layout.addWidget(self._message_label)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(0 if self._indeterminate else 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(not self._indeterminate)
        self._content_layout.addWidget(self._progress_bar)

        # Percentage label
        self._percentage_label = QLabel("0%")
        self._percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._percentage_label.setStyleSheet(f"""
            font-size: 12px;
            color: {palette.text_secondary};
        """)
        if self._indeterminate:
            self._percentage_label.hide()
        self._content_layout.addWidget(self._percentage_label)

        # Cancel button
        if self._cancellable:
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            self._cancel_btn = QPushButton("Cancel")
            self._cancel_btn.setObjectName("secondaryButton")
            self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._cancel_btn.clicked.connect(self._on_cancel)
            button_layout.addWidget(self._cancel_btn)

            self._content_layout.addLayout(button_layout)

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self._is_cancelled = True
        self.cancelled.emit()
        self.reject()

    def is_cancelled(self) -> bool:
        """Check if dialog was cancelled."""
        return self._is_cancelled

    def set_progress(self, value: int) -> None:
        """
        Set progress value (0-100).

        Args:
            value: Progress percentage
        """
        if self._indeterminate:
            self._progress_bar.setMaximum(100)
            self._percentage_label.show()
            self._indeterminate = False

        self._progress_bar.setValue(value)
        self._percentage_label.setText(f"{value}%")

        if value >= 100 and self._auto_close:
            QTimer.singleShot(500, self.accept)

    def set_message(self, message: str) -> None:
        """Update the status message."""
        self._message_label.setText(message)

    def set_indeterminate(self, indeterminate: bool) -> None:
        """Set indeterminate mode."""
        self._indeterminate = indeterminate
        if indeterminate:
            self._progress_bar.setMaximum(0)
            self._percentage_label.hide()
        else:
            self._progress_bar.setMaximum(100)
            self._percentage_label.show()

    def closeEvent(self, event) -> None:
        """Handle close event."""
        if self._cancellable:
            self._on_cancel()
        event.accept()


# Convenience functions

def show_info(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None
) -> None:
    """Show an info dialog."""
    dialog = MessageDialog(
        parent, DialogType.INFO, title, message, details
    )
    dialog.exec()


def show_warning(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None
) -> None:
    """Show a warning dialog."""
    dialog = MessageDialog(
        parent, DialogType.WARNING, title, message, details
    )
    dialog.exec()


def show_error(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None
) -> None:
    """Show an error dialog."""
    dialog = MessageDialog(
        parent, DialogType.ERROR, title, message, details
    )
    dialog.exec()


def show_success(
    parent: Optional[QWidget],
    title: str,
    message: str
) -> None:
    """Show a success dialog."""
    dialog = MessageDialog(
        parent, DialogType.SUCCESS, title, message
    )
    dialog.exec()


def confirm(
    parent: Optional[QWidget],
    title: str,
    message: str,
    confirm_text: str = "Yes",
    cancel_text: str = "No",
    destructive: bool = False
) -> bool:
    """
    Show a confirmation dialog and return result.

    Returns:
        True if confirmed, False otherwise
    """
    dialog = ConfirmDialog(
        parent, title, message, confirm_text, cancel_text, destructive
    )
    return dialog.exec() == QDialog.DialogCode.Accepted


def get_input(
    parent: Optional[QWidget],
    title: str,
    label: str,
    initial_value: str = "",
    placeholder: str = ""
) -> Optional[str]:
    """
    Show an input dialog and return the value.

    Returns:
        Input value if accepted, None otherwise
    """
    dialog = InputDialog(
        parent, title, label, initial_value, placeholder
    )
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_value()
    return None
