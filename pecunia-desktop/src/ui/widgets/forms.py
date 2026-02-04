"""
Form Widgets Module

Reusable form widgets for input, validation, and user interaction.
Provides base form classes, validation support, and common form patterns.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QComboBox, QPushButton, QDoubleSpinBox, QDateEdit,
    QGroupBox, QFrame, QColorDialog, QCompleter, QSizePolicy,
    QGridLayout, QSpacerItem, QToolButton, QMessageBox,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QRegularExpression, QSize, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QPainter, QRegularExpressionValidator,
    QValidator, QPalette, QPixmap, QKeySequence, QShortcut
)
from typing import Optional, List, Dict, Any, Callable, Tuple, Union
from decimal import Decimal, InvalidOperation
from enum import Enum
import re

# Import validators and inputs for integration
from .validators import (
    BaseValidator, RequiredValidator, AmountValidator,
    DateValidator, EmailValidator, PasswordValidator,
    ValidationResult
)
from .form_layout import FormRow, FormSection, FormButtons, FormGrid


class CurrencyInput(QWidget):
    """
    Decimal input widget with currency symbol display.

    Provides formatted currency input with configurable symbol,
    decimal places, and range validation.
    """

    value_changed = pyqtSignal(Decimal)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        currency_symbol: str = "$",
        decimal_places: int = 2,
        minimum: float = 0.0,
        maximum: float = 999999999.99,
        show_symbol: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("currencyInput")
        self._currency_symbol = currency_symbol
        self._decimal_places = decimal_places
        self._show_symbol = show_symbol
        self._minimum = minimum
        self._maximum = maximum
        self._setup_ui()

    def _setup_ui(self):
        """Set up the currency input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Currency symbol label
        if self._show_symbol:
            self.symbol_label = QLabel(self._currency_symbol)
            self.symbol_label.setFont(QFont("Segoe UI", 11))
            self.symbol_label.setStyleSheet("color: #666;")
            layout.addWidget(self.symbol_label)

        # Spin box for decimal input
        self.spin_box = QDoubleSpinBox()
        self.spin_box.setObjectName("currencySpinBox")
        self.spin_box.setDecimals(self._decimal_places)
        self.spin_box.setMinimum(self._minimum)
        self.spin_box.setMaximum(self._maximum)
        self.spin_box.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_box.setFont(QFont("Segoe UI", 11))
        self.spin_box.setMinimumWidth(120)
        self.spin_box.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.spin_box, 1)

    def _on_value_changed(self, value: float):
        """Handle value changes."""
        decimal_value = Decimal(str(value)).quantize(
            Decimal(10) ** -self._decimal_places
        )
        self.value_changed.emit(decimal_value)

    def value(self) -> Decimal:
        """Get the current value as Decimal."""
        return Decimal(str(self.spin_box.value())).quantize(
            Decimal(10) ** -self._decimal_places
        )

    def set_value(self, value: float | Decimal | str):
        """Set the value."""
        try:
            self.spin_box.setValue(float(value))
        except (ValueError, InvalidOperation):
            self.spin_box.setValue(0.0)

    def set_currency_symbol(self, symbol: str):
        """Set the currency symbol."""
        self._currency_symbol = symbol
        if self._show_symbol:
            self.symbol_label.setText(symbol)

    def set_range(self, minimum: float, maximum: float):
        """Set the valid range."""
        self._minimum = minimum
        self._maximum = maximum
        self.spin_box.setMinimum(minimum)
        self.spin_box.setMaximum(maximum)

    def setReadOnly(self, readonly: bool):
        """Set read-only state."""
        self.spin_box.setReadOnly(readonly)


class DatePicker(QWidget):
    """
    Date selection widget with calendar popup.

    Provides easy date selection with configurable format,
    range constraints, and calendar display.
    """

    date_changed = pyqtSignal(QDate)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        date_format: str = "yyyy-MM-dd",
        show_today_button: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("datePicker")
        self._date_format = date_format
        self._show_today_button = show_today_button
        self._setup_ui()

    def _setup_ui(self):
        """Set up the date picker UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Date edit widget
        self.date_edit = QDateEdit()
        self.date_edit.setObjectName("dateEdit")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat(self._date_format)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFont(QFont("Segoe UI", 11))
        self.date_edit.dateChanged.connect(self.date_changed.emit)
        layout.addWidget(self.date_edit, 1)

        # Today button
        if self._show_today_button:
            self.today_btn = QToolButton()
            self.today_btn.setObjectName("todayButton")
            self.today_btn.setText("Today")
            self.today_btn.setFont(QFont("Segoe UI", 9))
            self.today_btn.clicked.connect(self._set_today)
            layout.addWidget(self.today_btn)

    def _set_today(self):
        """Set the date to today."""
        self.date_edit.setDate(QDate.currentDate())

    def date(self) -> QDate:
        """Get the current date."""
        return self.date_edit.date()

    def set_date(self, date: QDate):
        """Set the date."""
        self.date_edit.setDate(date)

    def set_minimum_date(self, date: QDate):
        """Set the minimum selectable date."""
        self.date_edit.setMinimumDate(date)

    def set_maximum_date(self, date: QDate):
        """Set the maximum selectable date."""
        self.date_edit.setMaximumDate(date)

    def set_date_range(self, min_date: QDate, max_date: QDate):
        """Set the valid date range."""
        self.date_edit.setDateRange(min_date, max_date)

    def setReadOnly(self, readonly: bool):
        """Set read-only state."""
        self.date_edit.setReadOnly(readonly)


class CategoryComboBox(QComboBox):
    """
    Dropdown with category colors and optional icons.

    Displays categories with visual indicators (color dots)
    and supports icons for each category.
    """

    category_changed = pyqtSignal(str, dict)  # category name, category data

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("categoryComboBox")
        self._categories: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the category combo box UI."""
        self.setFont(QFont("Segoe UI", 11))
        self.setMinimumHeight(32)
        self.currentIndexChanged.connect(self._on_index_changed)

    def _on_index_changed(self, index: int):
        """Handle selection change."""
        if 0 <= index < len(self._categories):
            category = self._categories[index]
            self.category_changed.emit(category.get('name', ''), category)

    def set_categories(self, categories: List[Dict[str, Any]]):
        """
        Set the available categories.

        Each category dict should have:
        - 'name': Category name (required)
        - 'color': Color code (optional)
        - 'icon': Icon path or QIcon (optional)
        """
        self._categories = categories
        self.clear()

        for category in categories:
            name = category.get('name', '')
            color = category.get('color', '#888888')
            icon = category.get('icon')

            if icon:
                if isinstance(icon, str):
                    self.addItem(QIcon(icon), name)
                else:
                    self.addItem(icon, name)
            else:
                # Create color dot icon
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QColor(color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(2, 2, 12, 12)
                painter.end()
                self.addItem(QIcon(pixmap), name)

    def current_category(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected category data."""
        index = self.currentIndex()
        if 0 <= index < len(self._categories):
            return self._categories[index]
        return None

    def set_current_category(self, name: str):
        """Set the current category by name."""
        for i, category in enumerate(self._categories):
            if category.get('name') == name:
                self.setCurrentIndex(i)
                break

    def add_category(self, category: Dict[str, Any]):
        """Add a single category."""
        self._categories.append(category)
        name = category.get('name', '')
        color = category.get('color', '#888888')

        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        self.addItem(QIcon(pixmap), name)


class SearchInput(QWidget):
    """
    Text input with search icon and clear button.

    Provides a search-style input with visual indicators
    and optional auto-complete functionality.
    """

    text_changed = pyqtSignal(str)
    search_submitted = pyqtSignal(str)
    cleared = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Search...",
        show_clear_button: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("searchInput")
        self._placeholder = placeholder
        self._show_clear_button = show_clear_button
        self._setup_ui()

    def _setup_ui(self):
        """Set up the search input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container frame for styling
        self.container = QFrame()
        self.container.setObjectName("searchContainer")
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(8, 4, 8, 4)
        container_layout.setSpacing(8)

        # Search icon label
        self.search_icon = QLabel()
        self.search_icon.setObjectName("searchIcon")
        self.search_icon.setText("\U0001F50D")  # Magnifying glass emoji
        self.search_icon.setFont(QFont("Segoe UI", 10))
        container_layout.addWidget(self.search_icon)

        # Text input
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("searchLineEdit")
        self.line_edit.setPlaceholderText(self._placeholder)
        self.line_edit.setFont(QFont("Segoe UI", 11))
        self.line_edit.setFrame(False)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.returnPressed.connect(self._on_return_pressed)
        container_layout.addWidget(self.line_edit, 1)

        # Clear button
        if self._show_clear_button:
            self.clear_btn = QToolButton()
            self.clear_btn.setObjectName("clearButton")
            self.clear_btn.setText("\u2715")  # X symbol
            self.clear_btn.setFont(QFont("Segoe UI", 9))
            self.clear_btn.setFixedSize(20, 20)
            self.clear_btn.clicked.connect(self._on_clear)
            self.clear_btn.setVisible(False)
            container_layout.addWidget(self.clear_btn)

        layout.addWidget(self.container)

    def _on_text_changed(self, text: str):
        """Handle text changes."""
        if self._show_clear_button:
            self.clear_btn.setVisible(bool(text))
        self.text_changed.emit(text)

    def _on_return_pressed(self):
        """Handle return/enter key."""
        self.search_submitted.emit(self.line_edit.text())

    def _on_clear(self):
        """Clear the search input."""
        self.line_edit.clear()
        self.cleared.emit()

    def text(self) -> str:
        """Get the current text."""
        return self.line_edit.text()

    def set_text(self, text: str):
        """Set the text."""
        self.line_edit.setText(text)

    def clear(self):
        """Clear the input."""
        self.line_edit.clear()

    def set_completer(self, items: List[str]):
        """Set auto-complete suggestions."""
        completer = QCompleter(items)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.line_edit.setCompleter(completer)

    def setPlaceholderText(self, text: str):
        """Set the placeholder text."""
        self._placeholder = text
        self.line_edit.setPlaceholderText(text)


class ColorPicker(QWidget):
    """
    Color selection widget for categories.

    Displays a color preview button that opens a color dialog
    when clicked, with preset colors and custom color support.
    """

    color_changed = pyqtSignal(str)  # hex color

    # Default preset colors for categories
    PRESET_COLORS = [
        '#4CAF50', '#2196F3', '#FF9800', '#E91E63',
        '#9C27B0', '#00BCD4', '#FFC107', '#795548',
        '#607D8B', '#F44336', '#3F51B5', '#009688',
        '#CDDC39', '#FF5722', '#673AB7', '#8BC34A'
    ]

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_color: str = "#4CAF50",
        show_presets: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("colorPicker")
        self._current_color = initial_color
        self._show_presets = show_presets
        self._setup_ui()

    def _setup_ui(self):
        """Set up the color picker UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Color preview button
        self.color_btn = QPushButton()
        self.color_btn.setObjectName("colorButton")
        self.color_btn.setFixedSize(32, 32)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.clicked.connect(self._open_color_dialog)
        self._update_button_color()
        layout.addWidget(self.color_btn)

        # Hex color display
        self.hex_label = QLabel(self._current_color)
        self.hex_label.setFont(QFont("Segoe UI Mono", 10))
        self.hex_label.setMinimumWidth(70)
        layout.addWidget(self.hex_label)

        # Preset colors
        if self._show_presets:
            layout.addSpacing(8)
            self.presets_frame = QFrame()
            presets_layout = QHBoxLayout(self.presets_frame)
            presets_layout.setContentsMargins(0, 0, 0, 0)
            presets_layout.setSpacing(4)

            for color in self.PRESET_COLORS[:8]:  # Show first 8 presets
                btn = QToolButton()
                btn.setFixedSize(20, 20)
                btn.setStyleSheet(
                    f"background-color: {color}; "
                    f"border: 1px solid #ccc; "
                    f"border-radius: 3px;"
                )
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, c=color: self._set_color(c))
                presets_layout.addWidget(btn)

            layout.addWidget(self.presets_frame)

        layout.addStretch()

    def _update_button_color(self):
        """Update the color button appearance."""
        self.color_btn.setStyleSheet(
            f"background-color: {self._current_color}; "
            f"border: 2px solid #ccc; "
            f"border-radius: 4px;"
        )

    def _open_color_dialog(self):
        """Open the color selection dialog."""
        color = QColorDialog.getColor(
            QColor(self._current_color),
            self,
            "Select Color"
        )
        if color.isValid():
            self._set_color(color.name())

    def _set_color(self, color: str):
        """Set the selected color."""
        self._current_color = color
        self._update_button_color()
        self.hex_label.setText(color)
        self.color_changed.emit(color)

    def color(self) -> str:
        """Get the current color as hex string."""
        return self._current_color

    def set_color(self, color: str):
        """Set the color."""
        self._set_color(color)


class ValidatedLineEdit(QWidget):
    """
    Input with validation and error display.

    Provides real-time validation feedback with customizable
    validators, error messages, and visual indicators.
    """

    text_changed = pyqtSignal(str)
    validation_changed = pyqtSignal(bool)  # is_valid

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "",
        validator: Optional[QValidator] = None,
        validation_func: Optional[Callable[[str], tuple[bool, str]]] = None,
        required: bool = False
    ):
        super().__init__(parent)
        self.setObjectName("validatedLineEdit")
        self._placeholder = placeholder
        self._validator = validator
        self._validation_func = validation_func
        self._required = required
        self._is_valid = True
        self._error_message = ""
        self._setup_ui()

    def _setup_ui(self):
        """Set up the validated input UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Input field
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("validatedInput")
        self.line_edit.setPlaceholderText(self._placeholder)
        self.line_edit.setFont(QFont("Segoe UI", 11))
        self.line_edit.setMinimumHeight(32)

        if self._validator:
            self.line_edit.setValidator(self._validator)

        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.editingFinished.connect(self._validate)
        layout.addWidget(self.line_edit)

        # Error message label
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setFont(QFont("Segoe UI", 9))
        self.error_label.setStyleSheet("color: #F44336; padding-left: 2px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

    def _on_text_changed(self, text: str):
        """Handle text changes."""
        self.text_changed.emit(text)
        # Clear error state while typing
        if self._error_message:
            self._clear_error()

    def _validate(self):
        """Validate the input."""
        text = self.line_edit.text()

        # Check required
        if self._required and not text.strip():
            self._show_error("This field is required")
            return

        # Check custom validation
        if self._validation_func and text:
            is_valid, message = self._validation_func(text)
            if not is_valid:
                self._show_error(message)
                return

        self._clear_error()

    def _show_error(self, message: str):
        """Show an error message."""
        self._is_valid = False
        self._error_message = message
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        self.line_edit.setStyleSheet(
            "border: 1px solid #F44336; border-radius: 4px;"
        )
        self.validation_changed.emit(False)

    def _clear_error(self):
        """Clear the error state."""
        self._is_valid = True
        self._error_message = ""
        self.error_label.setVisible(False)
        self.line_edit.setStyleSheet("")
        self.validation_changed.emit(True)

    def text(self) -> str:
        """Get the current text."""
        return self.line_edit.text()

    def set_text(self, text: str):
        """Set the text."""
        self.line_edit.setText(text)

    def is_valid(self) -> bool:
        """Check if the input is valid."""
        self._validate()
        return self._is_valid

    def set_validator(self, validator: QValidator):
        """Set a Qt validator."""
        self._validator = validator
        self.line_edit.setValidator(validator)

    def set_validation_func(self, func: Callable[[str], tuple[bool, str]]):
        """Set a custom validation function."""
        self._validation_func = func

    def set_required(self, required: bool):
        """Set whether the field is required."""
        self._required = required

    def setPlaceholderText(self, text: str):
        """Set the placeholder text."""
        self._placeholder = text
        self.line_edit.setPlaceholderText(text)

    def setReadOnly(self, readonly: bool):
        """Set read-only state."""
        self.line_edit.setReadOnly(readonly)

    def clear(self):
        """Clear the input."""
        self.line_edit.clear()
        self._clear_error()


class FormSection(QGroupBox):
    """
    Group box with title for organizing form fields.

    Provides a styled container for grouping related
    form fields with a descriptive title.
    """

    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
        collapsible: bool = False
    ):
        super().__init__(title, parent)
        self.setObjectName("formSection")
        self._collapsible = collapsible
        self._collapsed = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the form section UI."""
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 20, 16, 16)
        self._layout.setSpacing(12)

        # Content container for collapsible behavior
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self._layout.addWidget(self.content_widget)

        # Make clickable if collapsible
        if self._collapsible:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        """Handle mouse press for collapsible behavior."""
        if self._collapsible:
            self.toggle_collapsed()
        super().mousePressEvent(event)

    def toggle_collapsed(self):
        """Toggle the collapsed state."""
        self._collapsed = not self._collapsed
        self.content_widget.setVisible(not self._collapsed)

    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state."""
        self._collapsed = collapsed
        self.content_widget.setVisible(not collapsed)

    def add_widget(self, widget: QWidget):
        """Add a widget to the section."""
        self.content_layout.addWidget(widget)

    def add_row(self, label_text: str, widget: QWidget):
        """Add a label-widget row to the section."""
        row = QHBoxLayout()
        row.setSpacing(12)

        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 10))
        label.setMinimumWidth(120)
        row.addWidget(label)

        row.addWidget(widget, 1)

        self.content_layout.addLayout(row)

    def add_form_row(self, label_text: str, widget: QWidget, stretch: bool = True):
        """Add a form row with label above the widget."""
        container = QVBoxLayout()
        container.setSpacing(4)

        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 10))
        container.addWidget(label)

        if stretch:
            container.addWidget(widget)
        else:
            h_layout = QHBoxLayout()
            h_layout.addWidget(widget)
            h_layout.addStretch()
            container.addLayout(h_layout)

        self.content_layout.addLayout(container)

    def add_spacing(self, spacing: int = 12):
        """Add vertical spacing."""
        self.content_layout.addSpacing(spacing)


class FormButtons(QWidget):
    """
    OK/Cancel/Apply button row for forms.

    Provides a standardized button layout for form actions
    with configurable buttons and shortcuts.
    """

    ok_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    apply_clicked = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        show_ok: bool = True,
        show_cancel: bool = True,
        show_apply: bool = False,
        ok_text: str = "OK",
        cancel_text: str = "Cancel",
        apply_text: str = "Apply"
    ):
        super().__init__(parent)
        self.setObjectName("formButtons")
        self._show_ok = show_ok
        self._show_cancel = show_cancel
        self._show_apply = show_apply
        self._ok_text = ok_text
        self._cancel_text = cancel_text
        self._apply_text = apply_text
        self._setup_ui()

    def _setup_ui(self):
        """Set up the form buttons UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(8)

        layout.addStretch()

        # Cancel button
        if self._show_cancel:
            self.cancel_btn = QPushButton(self._cancel_text)
            self.cancel_btn.setObjectName("cancelButton")
            self.cancel_btn.setFont(QFont("Segoe UI", 10))
            self.cancel_btn.setMinimumWidth(80)
            self.cancel_btn.setMinimumHeight(32)
            self.cancel_btn.clicked.connect(self.cancel_clicked.emit)
            layout.addWidget(self.cancel_btn)

        # Apply button
        if self._show_apply:
            self.apply_btn = QPushButton(self._apply_text)
            self.apply_btn.setObjectName("applyButton")
            self.apply_btn.setFont(QFont("Segoe UI", 10))
            self.apply_btn.setMinimumWidth(80)
            self.apply_btn.setMinimumHeight(32)
            self.apply_btn.clicked.connect(self.apply_clicked.emit)
            layout.addWidget(self.apply_btn)

        # OK button
        if self._show_ok:
            self.ok_btn = QPushButton(self._ok_text)
            self.ok_btn.setObjectName("okButton")
            self.ok_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.ok_btn.setMinimumWidth(80)
            self.ok_btn.setMinimumHeight(32)
            self.ok_btn.setDefault(True)
            self.ok_btn.clicked.connect(self.ok_clicked.emit)
            layout.addWidget(self.ok_btn)

    def set_ok_enabled(self, enabled: bool):
        """Enable/disable the OK button."""
        if self._show_ok:
            self.ok_btn.setEnabled(enabled)

    def set_apply_enabled(self, enabled: bool):
        """Enable/disable the Apply button."""
        if self._show_apply:
            self.apply_btn.setEnabled(enabled)

    def set_ok_text(self, text: str):
        """Set the OK button text."""
        if self._show_ok:
            self.ok_btn.setText(text)

    def set_cancel_text(self, text: str):
        """Set the Cancel button text."""
        if self._show_cancel:
            self.cancel_btn.setText(text)


# Convenience aliases for backward compatibility
MoneySpinBox = CurrencyInput


class FormMode(Enum):
    """Form operation modes."""
    CREATE = "create"
    EDIT = "edit"
    VIEW = "view"


class FormWidget(QWidget):
    """
    Base form widget with comprehensive functionality.

    Provides a foundation for building forms with:
    - Field management and validation
    - Dirty state tracking
    - Submit/cancel/reset handling
    - Loading states
    - Error display
    - Tab navigation
    - Keyboard shortcuts

    Signals:
        submitted: Emitted when form is successfully submitted (dict)
        cancelled: Emitted when form is cancelled
        validation_failed: Emitted when validation fails (list of errors)
        dirty_changed: Emitted when dirty state changes (bool)
        field_changed: Emitted when any field value changes (field_name, value)
    """

    submitted = pyqtSignal(dict)
    cancelled = pyqtSignal()
    validation_failed = pyqtSignal(list)
    dirty_changed = pyqtSignal(bool)
    field_changed = pyqtSignal(str, object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        mode: FormMode = FormMode.CREATE,
        show_buttons: bool = True,
        scrollable: bool = False
    ):
        super().__init__(parent)
        self.setObjectName("formWidget")

        self._mode = mode
        self._show_buttons = show_buttons
        self._scrollable = scrollable
        self._fields: Dict[str, QWidget] = {}
        self._field_rows: Dict[str, FormRow] = {}
        self._validators: Dict[str, List[Callable]] = {}
        self._required_fields: List[str] = []
        self._initial_data: Dict[str, Any] = {}
        self._is_dirty = False
        self._is_loading = False
        self._errors: Dict[str, str] = {}

        self._setup_base_ui()
        self._setup_shortcuts()

    def _setup_base_ui(self):
        """Set up the base form UI."""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(16)

        # Scrollable container if needed
        if self._scrollable:
            self._scroll_area = QScrollArea()
            self._scroll_area.setWidgetResizable(True)
            self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            self._scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )

            self._scroll_content = QWidget()
            self._form_layout = QVBoxLayout(self._scroll_content)
            self._form_layout.setSpacing(12)
            self._form_layout.setContentsMargins(0, 0, 16, 0)

            self._scroll_area.setWidget(self._scroll_content)
            self._main_layout.addWidget(self._scroll_area, 1)
        else:
            # Form content area (to be filled by subclasses)
            self._form_layout = QVBoxLayout()
            self._form_layout.setSpacing(12)
            self._main_layout.addLayout(self._form_layout, 1)

        # Error summary (hidden by default)
        self._error_summary = QLabel()
        self._error_summary.setObjectName("errorSummary")
        self._error_summary.setFont(QFont("Segoe UI", 10))
        self._error_summary.setStyleSheet("""
            QLabel#errorSummary {
                color: #F44336;
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
                border-radius: 4px;
                padding: 8px 12px;
            }
        """)
        self._error_summary.setWordWrap(True)
        self._error_summary.setVisible(False)
        self._main_layout.addWidget(self._error_summary)

        # Spacer (only if not scrollable)
        if not self._scrollable:
            self._main_layout.addStretch()

        # Form buttons
        if self._show_buttons:
            self._buttons = FormButtons()
            self._buttons.ok_clicked.connect(self._on_submit)
            self._buttons.cancel_clicked.connect(self._on_cancel)
            self._main_layout.addWidget(self._buttons)

            # Update button text based on mode
            if self._mode == FormMode.CREATE:
                self._buttons.set_button_text('ok', 'Create')
            elif self._mode == FormMode.EDIT:
                self._buttons.set_button_text('ok', 'Save')

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Enter to submit (when not in multiline widget)
        # Escape to cancel
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.activated.connect(self._on_cancel)

    def _on_submit(self):
        """Handle form submission."""
        if self._is_loading:
            return

        # Clear previous errors
        self.clear_errors()

        # Validate
        if self.validate():
            data = self.get_data()
            self.submitted.emit(data)
        else:
            # Emit validation failed with error list
            errors = list(self._errors.values())
            self.validation_failed.emit(errors)

            # Show error summary if multiple errors
            if len(errors) > 1:
                self._show_error_summary(errors)

    def _on_cancel(self):
        """Handle form cancellation."""
        if self._is_dirty:
            # Could show confirmation dialog here
            pass
        self.cancelled.emit()

    def _show_error_summary(self, errors: List[str]):
        """Show error summary banner."""
        self._error_summary.setText(
            f"Please fix the following errors:\n" +
            "\n".join(f"  - {e}" for e in errors[:5])  # Show max 5 errors
        )
        self._error_summary.setVisible(True)

    def _on_field_changed(self, field_name: str, value: Any):
        """Handle field value change."""
        # Update dirty state
        if not self._is_dirty:
            if field_name in self._initial_data:
                if self._initial_data[field_name] != value:
                    self._is_dirty = True
                    self.dirty_changed.emit(True)
            else:
                self._is_dirty = True
                self.dirty_changed.emit(True)

        # Clear field error
        if field_name in self._errors:
            self.clear_field_error(field_name)

        # Emit change
        self.field_changed.emit(field_name, value)

    def add_field(
        self,
        name: str,
        widget: QWidget,
        label: str = "",
        required: bool = False,
        validators: Optional[List[Callable]] = None,
        help_text: str = ""
    ) -> FormRow:
        """
        Add a field to the form with optional FormRow wrapper.

        Args:
            name: Unique field identifier
            widget: Input widget
            label: Field label (if empty, no FormRow wrapper)
            required: Whether field is required
            validators: List of validation functions
            help_text: Help text to show

        Returns:
            FormRow wrapper (or None if no label)
        """
        self._fields[name] = widget

        if required:
            self._required_fields.append(name)

        if validators:
            self._validators[name] = validators

        # Create FormRow if label provided
        if label:
            row = FormRow(
                label=label,
                widget=widget,
                required=required,
                help_text=help_text
            )
            self._field_rows[name] = row
            self._form_layout.addWidget(row)
            return row
        else:
            self._form_layout.addWidget(widget)
            return None

    def add_section(self, section: FormSection):
        """Add a form section."""
        self._form_layout.addWidget(section)

    def add_widget(self, widget: QWidget):
        """Add any widget to the form layout."""
        self._form_layout.addWidget(widget)

    def add_spacing(self, spacing: int = 12):
        """Add vertical spacing."""
        self._form_layout.addSpacing(spacing)

    def get_field(self, name: str) -> Optional[QWidget]:
        """Get a field widget by name."""
        return self._fields.get(name)

    def get_field_row(self, name: str) -> Optional[FormRow]:
        """Get a field's FormRow wrapper by name."""
        return self._field_rows.get(name)

    def set_field_error(self, field_name: str, message: str):
        """Set error on a specific field."""
        self._errors[field_name] = message

        # Show on FormRow if exists
        if field_name in self._field_rows:
            self._field_rows[field_name].show_error(message)

        # Show on ValidatedLineEdit if applicable
        widget = self._fields.get(field_name)
        if isinstance(widget, ValidatedLineEdit):
            widget._show_error(message)

    def clear_field_error(self, field_name: str):
        """Clear error on a specific field."""
        if field_name in self._errors:
            del self._errors[field_name]

        if field_name in self._field_rows:
            self._field_rows[field_name].clear_error()

        widget = self._fields.get(field_name)
        if isinstance(widget, ValidatedLineEdit):
            widget._clear_error()

    def clear_errors(self):
        """Clear all field errors."""
        for field_name in list(self._errors.keys()):
            self.clear_field_error(field_name)
        self._error_summary.setVisible(False)

    def validate(self) -> bool:
        """
        Validate all form fields.

        Returns:
            True if all validations pass
        """
        is_valid = True

        for name, widget in self._fields.items():
            # Check required fields
            if name in self._required_fields:
                value = self._get_widget_value(widget)
                if value is None or (isinstance(value, str) and not value.strip()):
                    self.set_field_error(name, "This field is required")
                    is_valid = False
                    continue

            # Check ValidatedLineEdit widgets
            if isinstance(widget, ValidatedLineEdit):
                if not widget.is_valid():
                    is_valid = False
                    continue

            # Check custom validators
            if name in self._validators:
                value = self._get_widget_value(widget)
                for validator in self._validators[name]:
                    result = validator(value)
                    if isinstance(result, tuple):
                        valid, message = result
                        if not valid:
                            self.set_field_error(name, message)
                            is_valid = False
                            break
                    elif isinstance(result, ValidationResult):
                        if not result.is_valid:
                            self.set_field_error(name, result.message)
                            is_valid = False
                            break
                    elif not result:
                        self.set_field_error(name, "Invalid value")
                        is_valid = False
                        break

        return is_valid

    def _get_widget_value(self, widget: QWidget) -> Any:
        """Get value from a widget based on its type."""
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, ValidatedLineEdit):
            return widget.text()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QDateEdit):
            return widget.date()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, CurrencyInput):
            return widget.value()
        elif isinstance(widget, DatePicker):
            return widget.date()
        elif isinstance(widget, CategoryComboBox):
            return widget.current_category()
        elif hasattr(widget, 'value'):
            return widget.value()
        elif hasattr(widget, 'text'):
            return widget.text()
        return None

    def get_data(self) -> Dict[str, Any]:
        """
        Get form data as dictionary.

        Override in subclasses for custom data extraction.
        """
        data = {}
        for name, widget in self._fields.items():
            data[name] = self._get_widget_value(widget)
        return data

    def set_data(self, data: Dict[str, Any]):
        """
        Set form data from dictionary.

        Override in subclasses for custom data setting.
        """
        self._initial_data = data.copy()
        self._is_dirty = False

        for name, value in data.items():
            widget = self._fields.get(name)
            if widget:
                self._set_widget_value(widget, value)

    def _set_widget_value(self, widget: QWidget, value: Any):
        """Set value on a widget based on its type."""
        if isinstance(widget, QLineEdit):
            widget.setText(str(value) if value else "")
        elif isinstance(widget, ValidatedLineEdit):
            widget.set_text(str(value) if value else "")
        elif isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QDateEdit):
            if isinstance(value, QDate):
                widget.setDate(value)
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value) if value else 0)
        elif isinstance(widget, CurrencyInput):
            widget.set_value(value)
        elif isinstance(widget, DatePicker):
            if isinstance(value, QDate):
                widget.set_date(value)
        elif isinstance(widget, CategoryComboBox):
            if isinstance(value, str):
                widget.set_current_category(value)
        elif hasattr(widget, 'set_value'):
            widget.set_value(value)
        elif hasattr(widget, 'setText'):
            widget.setText(str(value) if value else "")

    def reset(self):
        """Reset form to initial values."""
        if self._initial_data:
            self.set_data(self._initial_data)
        else:
            for widget in self._fields.values():
                if isinstance(widget, (QLineEdit, ValidatedLineEdit)):
                    widget.clear() if hasattr(widget, 'clear') else widget.setText("")
                elif isinstance(widget, CurrencyInput):
                    widget.set_value(0)
                elif isinstance(widget, DatePicker):
                    widget.set_date(QDate.currentDate())
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(0)

        self.clear_errors()
        self._is_dirty = False
        self.dirty_changed.emit(False)

    def set_mode(self, mode: FormMode):
        """Set form mode."""
        self._mode = mode

        # Update button text
        if self._show_buttons:
            if mode == FormMode.CREATE:
                self._buttons.set_button_text('ok', 'Create')
            elif mode == FormMode.EDIT:
                self._buttons.set_button_text('ok', 'Save')
            elif mode == FormMode.VIEW:
                self._buttons.set_button_visible('ok', False)
                self._buttons.set_button_text('cancel', 'Close')

        # Make fields read-only in view mode
        if mode == FormMode.VIEW:
            self.set_read_only(True)

    def set_read_only(self, read_only: bool):
        """Set all fields to read-only."""
        for widget in self._fields.values():
            if hasattr(widget, 'setReadOnly'):
                widget.setReadOnly(read_only)
            elif hasattr(widget, 'setEnabled'):
                widget.setEnabled(not read_only)

    def set_loading(self, loading: bool):
        """Set loading state."""
        self._is_loading = loading

        if self._show_buttons:
            self._buttons.set_loading(loading)

        # Disable form during loading
        for widget in self._fields.values():
            widget.setEnabled(not loading)

    def is_dirty(self) -> bool:
        """Check if form has unsaved changes."""
        return self._is_dirty

    def is_valid(self) -> bool:
        """Check if form is currently valid without showing errors."""
        for name, widget in self._fields.items():
            if name in self._required_fields:
                value = self._get_widget_value(widget)
                if value is None or (isinstance(value, str) and not value.strip()):
                    return False
            if isinstance(widget, ValidatedLineEdit):
                if not widget._is_valid:
                    return False
        return True

    @property
    def mode(self) -> FormMode:
        """Get current form mode."""
        return self._mode

    @property
    def buttons(self) -> Optional[FormButtons]:
        """Get form buttons widget."""
        return self._buttons if self._show_buttons else None


class FormField(QWidget):
    """
    Single form field with label and input.

    Convenience widget for creating labeled form fields
    with optional validation indicators.
    """

    def __init__(
        self,
        label: str,
        widget: QWidget,
        parent: Optional[QWidget] = None,
        required: bool = False,
        help_text: str = ""
    ):
        super().__init__(parent)
        self.setObjectName("formField")
        self._label_text = label
        self._widget = widget
        self._required = required
        self._help_text = help_text
        self._setup_ui()

    def _setup_ui(self):
        """Set up the form field UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label row
        label_layout = QHBoxLayout()
        label_layout.setSpacing(4)

        self.label = QLabel(self._label_text)
        self.label.setFont(QFont("Segoe UI", 10))
        label_layout.addWidget(self.label)

        if self._required:
            required_label = QLabel("*")
            required_label.setStyleSheet("color: #F44336;")
            required_label.setFont(QFont("Segoe UI", 10))
            label_layout.addWidget(required_label)

        label_layout.addStretch()
        layout.addLayout(label_layout)

        # Input widget
        layout.addWidget(self._widget)

        # Help text
        if self._help_text:
            help_label = QLabel(self._help_text)
            help_label.setFont(QFont("Segoe UI", 9))
            help_label.setStyleSheet("color: #888;")
            help_label.setWordWrap(True)
            layout.addWidget(help_label)

    @property
    def widget(self) -> QWidget:
        """Get the input widget."""
        return self._widget


# Pre-built form classes for common use cases
class TransactionForm(FormWidget):
    """Form for creating/editing transactions."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_transaction_form()

    def _setup_transaction_form(self):
        """Set up the transaction form fields."""
        # Description
        self.description_input = ValidatedLineEdit(
            placeholder="Enter description",
            required=True
        )
        self._form_layout.addWidget(
            FormField("Description", self.description_input, required=True)
        )
        self.add_field("description", self.description_input)

        # Amount
        self.amount_input = CurrencyInput()
        self._form_layout.addWidget(
            FormField("Amount", self.amount_input, required=True)
        )
        self.add_field("amount", self.amount_input)

        # Date
        self.date_input = DatePicker()
        self._form_layout.addWidget(
            FormField("Date", self.date_input, required=True)
        )
        self.add_field("date", self.date_input)

        # Category
        self.category_input = CategoryComboBox()
        self._form_layout.addWidget(
            FormField("Category", self.category_input)
        )
        self.add_field("category", self.category_input)

    def get_data(self) -> Dict[str, Any]:
        """Get transaction form data."""
        category = self.category_input.current_category()
        return {
            "description": self.description_input.text(),
            "amount": self.amount_input.value(),
            "date": self.date_input.date().toPyDate(),
            "category": category.get("name") if category else ""
        }

    def set_data(self, data: Dict[str, Any]):
        """Set transaction form data."""
        self.description_input.set_text(data.get("description", ""))
        self.amount_input.set_value(data.get("amount", 0))
        if "date" in data:
            self.date_input.set_date(QDate(data["date"]))
        if "category" in data:
            self.category_input.set_current_category(data["category"])

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self.category_input.set_categories(categories)


class BudgetForm(FormWidget):
    """Form for creating/editing budgets."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_budget_form()

    def _setup_budget_form(self):
        """Set up the budget form fields."""
        # Name
        self.name_input = ValidatedLineEdit(
            placeholder="Enter budget name",
            required=True
        )
        self._form_layout.addWidget(
            FormField("Budget Name", self.name_input, required=True)
        )
        self.add_field("name", self.name_input)

        # Limit
        self.limit_input = CurrencyInput()
        self._form_layout.addWidget(
            FormField("Budget Limit", self.limit_input, required=True)
        )
        self.add_field("limit", self.limit_input)

        # Category
        self.category_input = CategoryComboBox()
        self._form_layout.addWidget(
            FormField("Category", self.category_input)
        )
        self.add_field("category", self.category_input)

        # Color
        self.color_input = ColorPicker()
        self._form_layout.addWidget(
            FormField("Color", self.color_input)
        )
        self.add_field("color", self.color_input)

    def get_data(self) -> Dict[str, Any]:
        """Get budget form data."""
        category = self.category_input.current_category()
        return {
            "name": self.name_input.text(),
            "limit": self.limit_input.value(),
            "category": category.get("name") if category else "",
            "color": self.color_input.color()
        }

    def set_data(self, data: Dict[str, Any]):
        """Set budget form data."""
        self.name_input.set_text(data.get("name", ""))
        self.limit_input.set_value(data.get("limit", 0))
        if "category" in data:
            self.category_input.set_current_category(data["category"])
        if "color" in data:
            self.color_input.set_color(data["color"])

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self.category_input.set_categories(categories)


class LoginForm(FormWidget):
    """Form for user login."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_login_form()

    def _setup_login_form(self):
        """Set up the login form fields."""
        # Email/Username
        self.email_input = ValidatedLineEdit(
            placeholder="Enter email or username",
            required=True
        )
        self._form_layout.addWidget(
            FormField("Email / Username", self.email_input, required=True)
        )
        self.add_field("email", self.email_input)

        # Password
        self.password_input = ValidatedLineEdit(
            placeholder="Enter password",
            required=True
        )
        self.password_input.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._form_layout.addWidget(
            FormField("Password", self.password_input, required=True)
        )
        self.add_field("password", self.password_input)

        # Update button text
        self._buttons.set_ok_text("Login")
        self._buttons.set_cancel_text("Forgot Password?")

    def get_data(self) -> Dict[str, Any]:
        """Get login form data."""
        return {
            "email": self.email_input.text(),
            "password": self.password_input.text()
        }


class RegisterForm(FormWidget):
    """Form for user registration."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_register_form()

    def _setup_register_form(self):
        """Set up the registration form fields."""
        # Name
        self.name_input = ValidatedLineEdit(
            placeholder="Enter your full name",
            required=True
        )
        self._form_layout.addWidget(
            FormField("Full Name", self.name_input, required=True)
        )
        self.add_field("name", self.name_input)

        # Email
        def validate_email(text: str) -> tuple[bool, str]:
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(pattern, text):
                return (True, "")
            return (False, "Please enter a valid email address")

        self.email_input = ValidatedLineEdit(
            placeholder="Enter email address",
            required=True,
            validation_func=validate_email
        )
        self._form_layout.addWidget(
            FormField("Email", self.email_input, required=True)
        )
        self.add_field("email", self.email_input)

        # Password
        def validate_password(text: str) -> tuple[bool, str]:
            if len(text) < 8:
                return (False, "Password must be at least 8 characters")
            return (True, "")

        self.password_input = ValidatedLineEdit(
            placeholder="Create a password",
            required=True,
            validation_func=validate_password
        )
        self.password_input.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._form_layout.addWidget(
            FormField(
                "Password",
                self.password_input,
                required=True,
                help_text="Must be at least 8 characters"
            )
        )
        self.add_field("password", self.password_input)

        # Confirm Password
        self.confirm_password_input = ValidatedLineEdit(
            placeholder="Confirm your password",
            required=True
        )
        self.confirm_password_input.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._form_layout.addWidget(
            FormField("Confirm Password", self.confirm_password_input, required=True)
        )
        self.add_field("confirm_password", self.confirm_password_input)

        # Update button text
        self._buttons.set_ok_text("Create Account")

    def validate(self) -> bool:
        """Validate registration form including password match."""
        if not super().validate():
            return False

        # Check password match
        if self.password_input.text() != self.confirm_password_input.text():
            self.confirm_password_input._show_error("Passwords do not match")
            return False

        return True

    def get_data(self) -> Dict[str, Any]:
        """Get registration form data."""
        return {
            "name": self.name_input.text(),
            "email": self.email_input.text(),
            "password": self.password_input.text()
        }
