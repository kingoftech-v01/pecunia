"""
Common reusable widgets for Pecunia Desktop.

Provides basic UI components including loading spinner, empty state,
error display, badges, and avatars.
"""

from typing import Optional
from enum import Enum

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QSize, pyqtProperty, QRectF, pyqtSignal
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QPixmap,
    QPainterPath, QBrush, QFontMetrics
)

from ..styles.theme import get_theme_manager, ThemeManager


class LoadingSpinner(QWidget):
    """
    Animated loading spinner widget.

    Displays a circular spinning animation to indicate loading state.
    Supports customizable size, color, and stroke width.

    Usage:
        spinner = LoadingSpinner()
        spinner.start()
        # ... loading complete
        spinner.stop()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        size: int = 40,
        color: Optional[str] = None,
        stroke_width: int = 4
    ):
        """
        Initialize the loading spinner.

        Args:
            parent: Parent widget
            size: Diameter of the spinner in pixels
            color: Color hex string (uses primary color if None)
            stroke_width: Width of the spinner stroke
        """
        super().__init__(parent)

        self._size = size
        self._stroke_width = stroke_width
        self._angle = 0
        self._is_spinning = False

        # Get color from theme if not provided
        theme = get_theme_manager()
        self._color = QColor(color if color else theme.current_palette.primary)

        # Setup timer for animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.setInterval(16)  # ~60 FPS

        # Set fixed size
        self.setFixedSize(size, size)

        # Connect to theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode):
        """Handle theme change."""
        if not hasattr(self, '_custom_color'):
            theme = get_theme_manager()
            self._color = QColor(theme.current_palette.primary)
            self.update()

    def set_color(self, color: str) -> None:
        """Set spinner color."""
        self._color = QColor(color)
        self._custom_color = True
        self.update()

    def start(self) -> None:
        """Start the spinning animation."""
        if not self._is_spinning:
            self._is_spinning = True
            self._timer.start()
            self.show()

    def stop(self) -> None:
        """Stop the spinning animation."""
        self._is_spinning = False
        self._timer.stop()

    def _rotate(self) -> None:
        """Rotate the spinner by one step."""
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        rect = self.rect()
        center = rect.center()
        radius = (min(rect.width(), rect.height()) - self._stroke_width) / 2

        # Create gradient effect for the arc
        painter.translate(center)
        painter.rotate(self._angle)

        # Draw arc segments with varying opacity
        pen = QPen(self._color)
        pen.setWidth(self._stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        arc_rect = QRectF(-radius, -radius, radius * 2, radius * 2)

        # Draw multiple segments with fading opacity
        for i in range(12):
            opacity = (i + 1) / 12.0
            color = QColor(self._color)
            color.setAlphaF(opacity)
            pen.setColor(color)
            painter.setPen(pen)

            start_angle = i * 30 * 16  # In 1/16th degrees
            span_angle = 25 * 16
            painter.drawArc(arc_rect, start_angle, span_angle)


class EmptyState(QWidget):
    """
    Empty state widget with icon and message.

    Displays a centered message with optional icon and action button
    when there is no content to show.

    Usage:
        empty = EmptyState(
            icon=":/icons/no-data.svg",
            title="No Transactions",
            message="Add your first transaction to get started.",
            action_text="Add Transaction",
            action_callback=self.add_transaction
        )
    """

    action_clicked = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None,
        title: str = "",
        message: str = "",
        action_text: Optional[str] = None,
        action_callback: Optional[callable] = None
    ):
        """
        Initialize empty state widget.

        Args:
            parent: Parent widget
            icon: Path to icon image
            title: Main title text
            message: Descriptive message
            action_text: Text for action button
            action_callback: Callback for action button click
        """
        super().__init__(parent)

        self._setup_ui(icon, title, message, action_text, action_callback)

    def _setup_ui(
        self,
        icon: Optional[str],
        title: str,
        message: str,
        action_text: Optional[str],
        action_callback: Optional[callable]
    ) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        theme = get_theme_manager()
        palette = theme.current_palette

        # Icon
        if icon:
            self._icon_label = QLabel()
            pixmap = QPixmap(icon)
            if not pixmap.isNull():
                self._icon_label.setPixmap(
                    pixmap.scaled(
                        64, 64,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._icon_label)
        else:
            # Default placeholder icon (circle with question mark)
            self._icon_label = QLabel()
            self._icon_label.setFixedSize(64, 64)
            self._icon_label.setStyleSheet(f"""
                background-color: {palette.background_alt};
                border-radius: 32px;
            """)
            self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Title
        if title:
            self._title_label = QLabel(title)
            self._title_label.setProperty("heading", True)
            self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._title_label.setStyleSheet(f"""
                font-size: 18px;
                font-weight: 600;
                color: {palette.text_primary};
            """)
            layout.addWidget(self._title_label)

        # Message
        if message:
            self._message_label = QLabel(message)
            self._message_label.setProperty("subheading", True)
            self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._message_label.setWordWrap(True)
            self._message_label.setMaximumWidth(400)
            self._message_label.setStyleSheet(f"""
                font-size: 14px;
                color: {palette.text_secondary};
            """)
            layout.addWidget(self._message_label)

        # Action button
        if action_text:
            layout.addSpacing(8)
            self._action_button = QPushButton(action_text)
            self._action_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_button.clicked.connect(self.action_clicked.emit)
            if action_callback:
                self._action_button.clicked.connect(action_callback)
            layout.addWidget(self._action_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_title(self, title: str) -> None:
        """Update the title text."""
        if hasattr(self, '_title_label'):
            self._title_label.setText(title)

    def set_message(self, message: str) -> None:
        """Update the message text."""
        if hasattr(self, '_message_label'):
            self._message_label.setText(message)


class ErrorWidget(QWidget):
    """
    Error display widget.

    Displays an error message with optional retry button.
    Supports different error types with appropriate styling.

    Usage:
        error = ErrorWidget(
            message="Failed to load data",
            error_type=ErrorType.NETWORK,
            retry_callback=self.reload_data
        )
    """

    class ErrorType(Enum):
        """Types of errors for styling."""
        GENERAL = "general"
        NETWORK = "network"
        AUTH = "auth"
        VALIDATION = "validation"

    retry_clicked = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "An error occurred",
        error_type: 'ErrorWidget.ErrorType' = None,
        retry_callback: Optional[callable] = None,
        show_retry: bool = True
    ):
        """
        Initialize error widget.

        Args:
            parent: Parent widget
            message: Error message to display
            error_type: Type of error for styling
            retry_callback: Callback for retry button
            show_retry: Whether to show retry button
        """
        super().__init__(parent)

        if error_type is None:
            error_type = self.ErrorType.GENERAL

        self._error_type = error_type
        self._setup_ui(message, retry_callback, show_retry)

    def _setup_ui(
        self,
        message: str,
        retry_callback: Optional[callable],
        show_retry: bool
    ) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        theme = get_theme_manager()
        palette = theme.current_palette

        # Container with error styling
        container = QFrame()
        container.setObjectName("errorContainer")
        container.setStyleSheet(f"""
            #errorContainer {{
                background-color: {palette.error}20;
                border: 1px solid {palette.error}40;
                border-radius: 8px;
                padding: 24px;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setSpacing(12)

        # Error icon (X in circle)
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            background-color: {palette.error};
            border-radius: 24px;
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)
        icon_label.setText("!")
        container_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Error message
        self._message_label = QLabel(message)
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setMaximumWidth(400)
        self._message_label.setStyleSheet(f"""
            color: {palette.error};
            font-size: 14px;
        """)
        container_layout.addWidget(self._message_label)

        # Retry button
        if show_retry:
            self._retry_button = QPushButton("Try Again")
            self._retry_button.setObjectName("secondaryButton")
            self._retry_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._retry_button.clicked.connect(self.retry_clicked.emit)
            if retry_callback:
                self._retry_button.clicked.connect(retry_callback)
            container_layout.addWidget(
                self._retry_button,
                alignment=Qt.AlignmentFlag.AlignCenter
            )

        layout.addWidget(container)

    def set_message(self, message: str) -> None:
        """Update the error message."""
        self._message_label.setText(message)


class Badge(QWidget):
    """
    Count badge widget.

    Displays a small badge with a number, typically used
    for notifications or unread counts.

    Usage:
        badge = Badge(count=5)
        badge.set_count(10)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        count: int = 0,
        max_count: int = 99,
        color: Optional[str] = None,
        text_color: Optional[str] = None
    ):
        """
        Initialize badge widget.

        Args:
            parent: Parent widget
            count: Initial count to display
            max_count: Maximum count before showing "+"
            color: Background color hex string
            text_color: Text color hex string
        """
        super().__init__(parent)

        self._count = count
        self._max_count = max_count

        theme = get_theme_manager()
        self._color = QColor(color if color else theme.current_palette.error)
        self._text_color = QColor(
            text_color if text_color else theme.current_palette.text_on_primary
        )

        self._min_size = 20
        self.setMinimumSize(self._min_size, self._min_size)
        self._update_size()

        # Connect to theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode) -> None:
        """Handle theme change."""
        if not hasattr(self, '_custom_color'):
            theme = get_theme_manager()
            self._color = QColor(theme.current_palette.error)
            self._text_color = QColor(theme.current_palette.text_on_primary)
            self.update()

    def _update_size(self) -> None:
        """Update widget size based on count."""
        text = self._get_display_text()

        font = QFont()
        font.setPixelSize(11)
        font.setBold(True)
        metrics = QFontMetrics(font)

        text_width = metrics.horizontalAdvance(text)
        width = max(self._min_size, text_width + 10)

        self.setFixedSize(width, self._min_size)

    def _get_display_text(self) -> str:
        """Get the text to display."""
        if self._count <= 0:
            return ""
        elif self._count > self._max_count:
            return f"{self._max_count}+"
        else:
            return str(self._count)

    def set_count(self, count: int) -> None:
        """Update the badge count."""
        self._count = count
        self._update_size()
        self.setVisible(count > 0)
        self.update()

    def get_count(self) -> int:
        """Get the current count."""
        return self._count

    count = property(get_count, set_count)

    def paintEvent(self, event) -> None:
        """Paint the badge."""
        if self._count <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        rect = self.rect()
        radius = rect.height() / 2

        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        # Draw text
        font = QFont()
        font.setPixelSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))

        text = self._get_display_text()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class Avatar(QWidget):
    """
    User avatar widget.

    Displays a user avatar image or initials fallback.
    Supports circular or rounded square shapes.

    Usage:
        avatar = Avatar(
            image_path="/path/to/avatar.png",
            name="John Doe",
            size=48
        )
    """

    clicked = pyqtSignal()

    class Shape(Enum):
        """Avatar shape options."""
        CIRCLE = "circle"
        ROUNDED = "rounded"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        image_path: Optional[str] = None,
        name: str = "",
        size: int = 40,
        shape: 'Avatar.Shape' = None,
        background_color: Optional[str] = None
    ):
        """
        Initialize avatar widget.

        Args:
            parent: Parent widget
            image_path: Path to avatar image
            name: User name for initials fallback
            size: Size in pixels
            shape: Circle or rounded square
            background_color: Background color for initials
        """
        super().__init__(parent)

        if shape is None:
            shape = self.Shape.CIRCLE

        self._image_path = image_path
        self._name = name
        self._size = size
        self._shape = shape
        self._pixmap: Optional[QPixmap] = None

        theme = get_theme_manager()
        self._bg_color = QColor(
            background_color if background_color else theme.current_palette.primary
        )
        self._text_color = QColor(theme.current_palette.text_on_primary)

        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Load image if provided
        if image_path:
            self.set_image(image_path)

        # Connect to theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode) -> None:
        """Handle theme change."""
        if not hasattr(self, '_custom_color'):
            theme = get_theme_manager()
            self._bg_color = QColor(theme.current_palette.primary)
            self._text_color = QColor(theme.current_palette.text_on_primary)
            self.update()

    def set_image(self, image_path: str) -> None:
        """Set the avatar image."""
        self._image_path = image_path
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self._pixmap = pixmap.scaled(
                self._size, self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self._pixmap = None
        self.update()

    def set_name(self, name: str) -> None:
        """Set the name for initials fallback."""
        self._name = name
        self.update()

    def _get_initials(self) -> str:
        """Get initials from name."""
        if not self._name:
            return "?"

        parts = self._name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1 and len(parts[0]) > 0:
            return parts[0][0].upper()
        else:
            return "?"

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        """Paint the avatar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Create clipping path for shape
        path = QPainterPath()
        if self._shape == self.Shape.CIRCLE:
            path.addEllipse(QRectF(rect))
        else:
            radius = self._size * 0.2
            path.addRoundedRect(QRectF(rect), radius, radius)

        painter.setClipPath(path)

        if self._pixmap:
            # Draw image
            # Center the image
            x = (rect.width() - self._pixmap.width()) // 2
            y = (rect.height() - self._pixmap.height()) // 2
            painter.drawPixmap(x, y, self._pixmap)
        else:
            # Draw background and initials
            painter.fillRect(rect, self._bg_color)

            font = QFont()
            font.setPixelSize(int(self._size * 0.4))
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(self._text_color))

            initials = self._get_initials()
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initials)


class AnimatedWidget(QWidget):
    """
    Base class for widgets with fade animations.

    Provides fade in/out animations for showing and hiding widgets.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize animated widget."""
        super().__init__(parent)

        # Setup opacity effect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        # Setup fade animation
        self._fade_animation = QPropertyAnimation(
            self._opacity_effect, b"opacity"
        )
        self._fade_animation.setDuration(200)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def fade_in(self, duration: int = 200) -> None:
        """Fade in the widget."""
        self._fade_animation.stop()
        self._fade_animation.setDuration(duration)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self.show()
        self._fade_animation.start()

    def fade_out(self, duration: int = 200, hide_after: bool = True) -> None:
        """Fade out the widget."""
        self._fade_animation.stop()
        self._fade_animation.setDuration(duration)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)

        if hide_after:
            self._fade_animation.finished.connect(self.hide)

        self._fade_animation.start()


class Separator(QFrame):
    """
    Horizontal or vertical separator line.

    Usage:
        separator = Separator(orientation=Qt.Orientation.Horizontal)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal
    ):
        """
        Initialize separator.

        Args:
            parent: Parent widget
            orientation: Horizontal or Vertical
        """
        super().__init__(parent)

        theme = get_theme_manager()

        if orientation == Qt.Orientation.Horizontal:
            self.setFrameShape(QFrame.Shape.HLine)
            self.setFixedHeight(1)
        else:
            self.setFrameShape(QFrame.Shape.VLine)
            self.setFixedWidth(1)

        self.setStyleSheet(f"""
            background-color: {theme.current_palette.divider};
        """)

        # Connect to theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode) -> None:
        """Handle theme change."""
        theme = get_theme_manager()
        self.setStyleSheet(f"""
            background-color: {theme.current_palette.divider};
        """)
