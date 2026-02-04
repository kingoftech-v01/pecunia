"""
Form Layout Components Module

Layout components for organizing form elements with consistent styling.
Includes FormRow, FormSection, and FormButtons for standardized form layouts.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QSizePolicy, QSpacerItem,
    QToolButton, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from typing import Optional, List, Dict, Any, Tuple


class FormRow(QWidget):
    """
    Single form row with label, input widget, and optional error message.

    Features:
    - Label positioning (left, top, right)
    - Required field indicator
    - Error message display
    - Help text tooltip
    - Consistent spacing
    """

    def __init__(
        self,
        label: str,
        widget: QWidget,
        parent: Optional[QWidget] = None,
        required: bool = False,
        help_text: str = "",
        error_message: str = "",
        label_position: str = "left",  # "left", "top", "right"
        label_width: int = 120
    ):
        super().__init__(parent)
        self.setObjectName("formRow")

        self._label_text = label
        self._widget = widget
        self._required = required
        self._help_text = help_text
        self._error_message = error_message
        self._label_position = label_position
        self._label_width = label_width
        self._has_error = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the form row UI."""
        if self._label_position == "top":
            self._setup_vertical_layout()
        else:
            self._setup_horizontal_layout()

    def _setup_horizontal_layout(self):
        """Set up horizontal layout (label left or right)."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Row layout
        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)

        # Create label
        self.label = QLabel(self._label_text)
        self.label.setFont(QFont("Segoe UI", 10))
        self.label.setMinimumWidth(self._label_width)
        self.label.setMaximumWidth(self._label_width)

        if self._label_position == "left":
            self.label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

        # Required indicator
        if self._required:
            self.required_indicator = QLabel("*")
            self.required_indicator.setStyleSheet("color: #F44336;")
            self.required_indicator.setFont(QFont("Segoe UI", 10))

        # Help icon
        if self._help_text:
            self.help_btn = QToolButton()
            self.help_btn.setText("?")
            self.help_btn.setFont(QFont("Segoe UI", 8))
            self.help_btn.setFixedSize(16, 16)
            self.help_btn.setStyleSheet("""
                QToolButton {
                    color: #888;
                    background: #F0F0F0;
                    border: none;
                    border-radius: 8px;
                }
                QToolButton:hover {
                    background: #E0E0E0;
                }
            """)
            self.help_btn.setToolTip(self._help_text)

        # Arrange based on position
        if self._label_position == "right":
            row_layout.addWidget(self._widget, 1)
            row_layout.addWidget(self.label)
            if self._required:
                row_layout.addWidget(self.required_indicator)
            if self._help_text:
                row_layout.addWidget(self.help_btn)
        else:  # left (default)
            row_layout.addWidget(self.label)
            if self._required:
                row_layout.addWidget(self.required_indicator)
            row_layout.addWidget(self._widget, 1)
            if self._help_text:
                row_layout.addWidget(self.help_btn)

        main_layout.addLayout(row_layout)

        # Error message label
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setFont(QFont("Segoe UI", 9))
        self.error_label.setStyleSheet("color: #F44336; padding-left: 2px;")
        self.error_label.setVisible(False)

        if self._label_position == "left":
            # Align error with input widget
            error_layout = QHBoxLayout()
            error_layout.addSpacing(self._label_width + 12)  # Label width + spacing
            error_layout.addWidget(self.error_label)
            main_layout.addLayout(error_layout)
        else:
            main_layout.addWidget(self.error_label)

    def _setup_vertical_layout(self):
        """Set up vertical layout (label on top)."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Label row
        label_layout = QHBoxLayout()
        label_layout.setSpacing(4)

        self.label = QLabel(self._label_text)
        self.label.setFont(QFont("Segoe UI", 10))
        label_layout.addWidget(self.label)

        if self._required:
            self.required_indicator = QLabel("*")
            self.required_indicator.setStyleSheet("color: #F44336;")
            self.required_indicator.setFont(QFont("Segoe UI", 10))
            label_layout.addWidget(self.required_indicator)

        if self._help_text:
            self.help_btn = QToolButton()
            self.help_btn.setText("?")
            self.help_btn.setFont(QFont("Segoe UI", 8))
            self.help_btn.setFixedSize(16, 16)
            self.help_btn.setStyleSheet("""
                QToolButton {
                    color: #888;
                    background: #F0F0F0;
                    border: none;
                    border-radius: 8px;
                }
            """)
            self.help_btn.setToolTip(self._help_text)
            label_layout.addWidget(self.help_btn)

        label_layout.addStretch()
        main_layout.addLayout(label_layout)

        # Widget
        main_layout.addWidget(self._widget)

        # Error message
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setFont(QFont("Segoe UI", 9))
        self.error_label.setStyleSheet("color: #F44336;")
        self.error_label.setVisible(False)
        main_layout.addWidget(self.error_label)

    def show_error(self, message: str):
        """Show an error message."""
        self._has_error = True
        self._error_message = message
        self.error_label.setText(message)
        self.error_label.setVisible(True)

        # Add error styling to widget
        self._widget.setProperty("error", True)
        self._widget.style().unpolish(self._widget)
        self._widget.style().polish(self._widget)

    def clear_error(self):
        """Clear the error state."""
        self._has_error = False
        self._error_message = ""
        self.error_label.setVisible(False)

        # Remove error styling
        self._widget.setProperty("error", False)
        self._widget.style().unpolish(self._widget)
        self._widget.style().polish(self._widget)

    def has_error(self) -> bool:
        """Check if row has an error."""
        return self._has_error

    @property
    def widget(self) -> QWidget:
        """Get the input widget."""
        return self._widget

    def set_label(self, text: str):
        """Set the label text."""
        self._label_text = text
        self.label.setText(text)

    def set_required(self, required: bool):
        """Set required state."""
        self._required = required
        if hasattr(self, 'required_indicator'):
            self.required_indicator.setVisible(required)

    def setEnabled(self, enabled: bool):
        """Enable/disable the row."""
        super().setEnabled(enabled)
        self._widget.setEnabled(enabled)
        self.label.setEnabled(enabled)


class FormSection(QGroupBox):
    """
    Grouped form fields with title.

    Features:
    - Collapsible sections
    - Icon support
    - Description text
    - Nested sections
    """

    collapsed_changed = pyqtSignal(bool)

    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
        collapsible: bool = False,
        collapsed: bool = False,
        icon: Optional[QIcon] = None,
        description: str = ""
    ):
        super().__init__(title, parent)
        self.setObjectName("formSection")

        self._collapsible = collapsible
        self._collapsed = collapsed
        self._icon = icon
        self._description = description

        self._setup_ui()

        if collapsed:
            self._collapse(animated=False)

    def _setup_ui(self):
        """Set up the form section UI."""
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

        # Styling
        self.setStyleSheet("""
            QGroupBox#formSection {
                background-color: transparent;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox#formSection::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #333;
            }
        """)

        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 20, 16, 16)
        self._main_layout.setSpacing(12)

        # Description
        if self._description:
            self.description_label = QLabel(self._description)
            self.description_label.setFont(QFont("Segoe UI", 9))
            self.description_label.setStyleSheet("color: #666;")
            self.description_label.setWordWrap(True)
            self._main_layout.addWidget(self.description_label)

        # Content container (for collapse animation)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("sectionContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self._main_layout.addWidget(self.content_widget)

        # Make clickable if collapsible
        if self._collapsible:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        """Handle mouse press for collapsible sections."""
        if self._collapsible and event.button() == Qt.MouseButton.LeftButton:
            # Only toggle if clicked on title area
            if event.position().y() < 30:
                self.toggle_collapsed()
        super().mousePressEvent(event)

    def toggle_collapsed(self):
        """Toggle the collapsed state."""
        if self._collapsed:
            self._expand()
        else:
            self._collapse()

    def _collapse(self, animated: bool = True):
        """Collapse the section."""
        self._collapsed = True
        self.content_widget.setVisible(False)
        self.collapsed_changed.emit(True)

    def _expand(self, animated: bool = True):
        """Expand the section."""
        self._collapsed = False
        self.content_widget.setVisible(True)
        self.collapsed_changed.emit(False)

    def is_collapsed(self) -> bool:
        """Check if section is collapsed."""
        return self._collapsed

    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state."""
        if collapsed:
            self._collapse()
        else:
            self._expand()

    def add_widget(self, widget: QWidget):
        """Add a widget to the section."""
        self.content_layout.addWidget(widget)

    def add_row(self, row: FormRow):
        """Add a FormRow to the section."""
        self.content_layout.addWidget(row)

    def add_layout(self, layout):
        """Add a layout to the section."""
        self.content_layout.addLayout(layout)

    def add_spacing(self, spacing: int = 12):
        """Add vertical spacing."""
        self.content_layout.addSpacing(spacing)

    def add_separator(self):
        """Add a horizontal separator line."""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #E0E0E0;")
        separator.setFixedHeight(1)
        self.content_layout.addWidget(separator)

    def clear(self):
        """Remove all widgets from the section."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class FormButtons(QWidget):
    """
    Standard form button row (Save/Cancel/Apply/etc).

    Features:
    - Configurable buttons
    - Primary/secondary styling
    - Loading states
    - Keyboard shortcuts
    """

    # Signals for each button type
    ok_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    apply_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()

    # Button configurations
    BUTTON_CONFIGS = {
        'ok': {'text': 'OK', 'primary': True, 'signal': 'ok_clicked'},
        'save': {'text': 'Save', 'primary': True, 'signal': 'save_clicked'},
        'cancel': {'text': 'Cancel', 'primary': False, 'signal': 'cancel_clicked'},
        'apply': {'text': 'Apply', 'primary': False, 'signal': 'apply_clicked'},
        'reset': {'text': 'Reset', 'primary': False, 'signal': 'reset_clicked'},
        'delete': {'text': 'Delete', 'primary': False, 'danger': True, 'signal': 'delete_clicked'},
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        buttons: Optional[List[str]] = None,  # ['ok', 'cancel'] or custom
        alignment: str = "right",  # "left", "center", "right"
        spacing: int = 8,
        show_ok: bool = True,
        show_cancel: bool = True,
        show_apply: bool = False,
        ok_text: str = "OK",
        cancel_text: str = "Cancel",
        apply_text: str = "Apply"
    ):
        super().__init__(parent)
        self.setObjectName("formButtons")

        # Handle legacy parameters
        if buttons is None:
            buttons = []
            if show_ok:
                buttons.append('ok')
            if show_apply:
                buttons.append('apply')
            if show_cancel:
                buttons.append('cancel')

        self._buttons_config = buttons
        self._alignment = alignment
        self._spacing = spacing
        self._custom_texts = {
            'ok': ok_text,
            'cancel': cancel_text,
            'apply': apply_text,
        }
        self._button_widgets: Dict[str, QPushButton] = {}
        self._loading = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the form buttons UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(self._spacing)

        # Add stretch based on alignment
        if self._alignment in ["center", "right"]:
            layout.addStretch()

        # Create buttons in reverse order for right alignment
        button_list = list(self._buttons_config)
        if self._alignment == "right":
            button_list = list(reversed(button_list))

        for button_id in button_list:
            if button_id in self.BUTTON_CONFIGS:
                config = self.BUTTON_CONFIGS[button_id]
                btn = self._create_button(button_id, config)
                self._button_widgets[button_id] = btn
                layout.addWidget(btn)
            elif isinstance(button_id, dict):
                # Custom button configuration
                btn = self._create_custom_button(button_id)
                custom_id = button_id.get('id', f'custom_{len(self._button_widgets)}')
                self._button_widgets[custom_id] = btn
                layout.addWidget(btn)

        # Add stretch based on alignment
        if self._alignment in ["center", "left"]:
            layout.addStretch()

    def _create_button(self, button_id: str, config: Dict) -> QPushButton:
        """Create a standard button."""
        text = self._custom_texts.get(button_id, config['text'])
        btn = QPushButton(text)
        btn.setObjectName(f"{button_id}Button")
        btn.setFont(QFont("Segoe UI", 10))
        btn.setMinimumWidth(80)
        btn.setMinimumHeight(32)

        # Apply styling
        if config.get('primary'):
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            btn.setDefault(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: none;
                    border-radius: 4px;
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
        elif config.get('danger'):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #F44336;
                    border: 1px solid #F44336;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #FFEBEE;
                }
                QPushButton:pressed {
                    background-color: #FFCDD2;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #1976D2;
                    border: 1px solid #1976D2;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #E3F2FD;
                }
                QPushButton:pressed {
                    background-color: #BBDEFB;
                }
                QPushButton:disabled {
                    color: #BDBDBD;
                    border-color: #BDBDBD;
                }
            """)

        # Connect signal
        signal_name = config.get('signal')
        if signal_name and hasattr(self, signal_name):
            signal = getattr(self, signal_name)
            btn.clicked.connect(signal.emit)

        return btn

    def _create_custom_button(self, config: Dict) -> QPushButton:
        """Create a custom button from config."""
        btn = QPushButton(config.get('text', 'Button'))
        btn.setFont(QFont("Segoe UI", 10))
        btn.setMinimumWidth(80)
        btn.setMinimumHeight(32)

        if config.get('callback'):
            btn.clicked.connect(config['callback'])

        return btn

    def get_button(self, button_id: str) -> Optional[QPushButton]:
        """Get a button widget by ID."""
        return self._button_widgets.get(button_id)

    def set_button_enabled(self, button_id: str, enabled: bool):
        """Enable/disable a specific button."""
        btn = self._button_widgets.get(button_id)
        if btn:
            btn.setEnabled(enabled)

    def set_button_text(self, button_id: str, text: str):
        """Set text for a specific button."""
        btn = self._button_widgets.get(button_id)
        if btn:
            btn.setText(text)

    def set_button_visible(self, button_id: str, visible: bool):
        """Show/hide a specific button."""
        btn = self._button_widgets.get(button_id)
        if btn:
            btn.setVisible(visible)

    def set_loading(self, loading: bool, button_id: str = 'ok'):
        """Set loading state on a button."""
        self._loading = loading
        btn = self._button_widgets.get(button_id)

        if btn:
            if loading:
                self._original_text = btn.text()
                btn.setText("Loading...")
                btn.setEnabled(False)
            else:
                if hasattr(self, '_original_text'):
                    btn.setText(self._original_text)
                btn.setEnabled(True)

    def is_loading(self) -> bool:
        """Check if in loading state."""
        return self._loading

    # Legacy compatibility methods
    def set_ok_enabled(self, enabled: bool):
        """Enable/disable the OK button."""
        self.set_button_enabled('ok', enabled)

    def set_apply_enabled(self, enabled: bool):
        """Enable/disable the Apply button."""
        self.set_button_enabled('apply', enabled)

    def set_ok_text(self, text: str):
        """Set the OK button text."""
        self.set_button_text('ok', text)

    def set_cancel_text(self, text: str):
        """Set the Cancel button text."""
        self.set_button_text('cancel', text)


class FormGrid(QWidget):
    """
    Grid-based form layout for multi-column forms.

    Features:
    - Configurable columns
    - Responsive layout
    - Spanning cells
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        columns: int = 2,
        row_spacing: int = 12,
        column_spacing: int = 24
    ):
        super().__init__(parent)
        self.setObjectName("formGrid")

        self._columns = columns
        self._row_spacing = row_spacing
        self._column_spacing = column_spacing
        self._current_row = 0
        self._current_col = 0

        self._setup_ui()

    def _setup_ui(self):
        """Set up the form grid UI."""
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(self._column_spacing)
        self.grid_layout.setVerticalSpacing(self._row_spacing)

    def add_row(
        self,
        row: FormRow,
        column_span: int = 1
    ):
        """Add a FormRow to the grid."""
        self.grid_layout.addWidget(
            row,
            self._current_row,
            self._current_col,
            1,
            column_span
        )

        self._current_col += column_span
        if self._current_col >= self._columns:
            self._current_row += 1
            self._current_col = 0

    def add_widget(
        self,
        widget: QWidget,
        row: Optional[int] = None,
        column: Optional[int] = None,
        row_span: int = 1,
        column_span: int = 1
    ):
        """Add a widget at specific position or next available."""
        if row is not None and column is not None:
            self.grid_layout.addWidget(
                widget, row, column, row_span, column_span
            )
        else:
            self.grid_layout.addWidget(
                widget,
                self._current_row,
                self._current_col,
                row_span,
                column_span
            )
            self._current_col += column_span
            if self._current_col >= self._columns:
                self._current_row += 1
                self._current_col = 0

    def add_separator(self, column_span: Optional[int] = None):
        """Add a horizontal separator spanning columns."""
        if column_span is None:
            column_span = self._columns - self._current_col

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #E0E0E0;")
        separator.setFixedHeight(1)

        self.add_widget(separator, column_span=column_span)

    def next_row(self):
        """Move to the next row."""
        self._current_row += 1
        self._current_col = 0


class ScrollableForm(QScrollArea):
    """
    Scrollable container for long forms.

    Features:
    - Automatic scrolling
    - Smooth scroll animation
    - Focus follows scroll
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("scrollableForm")

        self._setup_ui()

    def _setup_ui(self):
        """Set up the scrollable form UI."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Content widget
        self.content = QWidget()
        self.content.setObjectName("scrollableFormContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 16, 0)  # Right margin for scrollbar
        self.content_layout.setSpacing(16)

        self.setWidget(self.content)

    def add_section(self, section: FormSection):
        """Add a form section."""
        self.content_layout.addWidget(section)

    def add_widget(self, widget: QWidget):
        """Add a widget."""
        self.content_layout.addWidget(widget)

    def add_spacing(self, spacing: int = 16):
        """Add vertical spacing."""
        self.content_layout.addSpacing(spacing)

    def add_stretch(self):
        """Add stretch at the end."""
        self.content_layout.addStretch()

    def scroll_to_widget(self, widget: QWidget):
        """Scroll to make a widget visible."""
        self.ensureWidgetVisible(widget)


class FormCard(QFrame):
    """
    Card-style container for forms.

    Features:
    - Elevated card appearance
    - Header with title
    - Optional icon
    - Shadow effect
    """

    def __init__(
        self,
        title: str = "",
        parent: Optional[QWidget] = None,
        icon: Optional[QIcon] = None,
        show_shadow: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("formCard")

        self._title = title
        self._icon = icon
        self._show_shadow = show_shadow

        self._setup_ui()

    def _setup_ui(self):
        """Set up the form card UI."""
        # Card styling
        shadow_style = "box-shadow: 0 2px 4px rgba(0,0,0,0.1);" if self._show_shadow else ""
        self.setStyleSheet(f"""
            QFrame#formCard {{
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                {shadow_style}
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header (if title provided)
        if self._title:
            self.header = QWidget()
            self.header.setObjectName("cardHeader")
            self.header.setStyleSheet("""
                QWidget#cardHeader {
                    background-color: #FAFAFA;
                    border-bottom: 1px solid #E0E0E0;
                    border-radius: 8px 8px 0 0;
                }
            """)

            header_layout = QHBoxLayout(self.header)
            header_layout.setContentsMargins(16, 12, 16, 12)

            if self._icon:
                icon_label = QLabel()
                icon_label.setPixmap(self._icon.pixmap(24, 24))
                header_layout.addWidget(icon_label)

            title_label = QLabel(self._title)
            title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            header_layout.addWidget(title_label)

            header_layout.addStretch()
            main_layout.addWidget(self.header)

        # Content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)
        main_layout.addWidget(self.content)

    def add_widget(self, widget: QWidget):
        """Add a widget to the card content."""
        self.content_layout.addWidget(widget)

    def add_section(self, section: FormSection):
        """Add a form section."""
        self.content_layout.addWidget(section)

    def add_buttons(self, buttons: FormButtons):
        """Add form buttons at the bottom."""
        self.content_layout.addWidget(buttons)

    def set_title(self, title: str):
        """Set the card title."""
        self._title = title
        if hasattr(self, 'header'):
            # Find and update title label
            for i in range(self.header.layout().count()):
                widget = self.header.layout().itemAt(i).widget()
                if isinstance(widget, QLabel) and widget != self.header.layout().itemAt(0).widget():
                    widget.setText(title)
                    break
