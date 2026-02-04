"""
Specialized Input Widgets Module

Custom input widgets for financial application forms.
Includes currency-formatted inputs, date pickers, tag inputs, and more.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QComboBox, QPushButton, QDoubleSpinBox, QDateEdit,
    QFrame, QCompleter, QToolButton, QCalendarWidget,
    QMenu, QWidgetAction, QListWidget, QListWidgetItem,
    QSizePolicy, QScrollArea, QApplication, QStyle
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QDate, QRegularExpression, QSize,
    QTimer, QEvent, QLocale, QStringListModel
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QPainter, QRegularExpressionValidator,
    QValidator, QPalette, QPixmap, QKeyEvent, QFocusEvent,
    QMouseEvent, QAction
)
from typing import Optional, List, Dict, Any, Callable, Tuple
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
import re

from .validators import AmountValidator, DateValidator


class AmountInput(QWidget):
    """
    Currency-formatted input widget.

    Features:
    - Configurable currency symbol and position
    - Decimal place control
    - Range validation
    - Thousand separators
    - Real-time formatting
    """

    value_changed = pyqtSignal(object)  # Decimal or float
    editing_finished = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        currency_symbol: str = "$",
        symbol_position: str = "prefix",  # "prefix" or "suffix"
        decimal_places: int = 2,
        minimum: float = 0.0,
        maximum: float = 999999999.99,
        show_symbol: bool = True,
        show_thousands_separator: bool = True,
        allow_negative: bool = False,
        placeholder: str = "0.00"
    ):
        super().__init__(parent)
        self.setObjectName("amountInput")

        self._currency_symbol = currency_symbol
        self._symbol_position = symbol_position
        self._decimal_places = decimal_places
        self._minimum = minimum
        self._maximum = maximum
        self._show_symbol = show_symbol
        self._show_thousands_separator = show_thousands_separator
        self._allow_negative = allow_negative
        self._placeholder = placeholder
        self._locale = QLocale.system()

        self._setup_ui()
        self._setup_validator()

    def _setup_ui(self):
        """Set up the amount input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Currency symbol prefix
        if self._show_symbol and self._symbol_position == "prefix":
            self.prefix_label = QLabel(self._currency_symbol)
            self.prefix_label.setFont(QFont("Segoe UI", 11))
            self.prefix_label.setStyleSheet("color: #666; padding-right: 2px;")
            layout.addWidget(self.prefix_label)

        # Main input field
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("amountLineEdit")
        self.line_edit.setPlaceholderText(self._placeholder)
        self.line_edit.setFont(QFont("Segoe UI", 11))
        self.line_edit.setMinimumHeight(32)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self.line_edit, 1)

        # Currency symbol suffix
        if self._show_symbol and self._symbol_position == "suffix":
            self.suffix_label = QLabel(self._currency_symbol)
            self.suffix_label.setFont(QFont("Segoe UI", 11))
            self.suffix_label.setStyleSheet("color: #666; padding-left: 2px;")
            layout.addWidget(self.suffix_label)

    def _setup_validator(self):
        """Set up the amount validator."""
        self._validator = AmountValidator(
            decimal_places=self._decimal_places,
            minimum=self._minimum,
            maximum=self._maximum,
            allow_negative=self._allow_negative
        )

    def _on_text_changed(self, text: str):
        """Handle text changes."""
        # Remove formatting for validation
        clean_text = self._clean_text(text)

        # Validate
        result = self._validator.validate_value(clean_text)

        if result.is_valid:
            try:
                value = Decimal(clean_text) if clean_text else Decimal(0)
                self.value_changed.emit(value)
            except InvalidOperation:
                pass

    def _on_editing_finished(self):
        """Handle editing finished - apply formatting."""
        text = self.line_edit.text()
        clean_text = self._clean_text(text)

        if clean_text:
            try:
                value = Decimal(clean_text)
                formatted = self._format_value(float(value))
                self.line_edit.blockSignals(True)
                self.line_edit.setText(formatted)
                self.line_edit.blockSignals(False)
            except (InvalidOperation, ValueError):
                pass

        self.editing_finished.emit()

    def _clean_text(self, text: str) -> str:
        """Remove formatting from text."""
        # Remove currency symbol
        text = text.replace(self._currency_symbol, "")
        # Remove thousand separators
        text = text.replace(",", "").replace(" ", "")
        return text.strip()

    def _format_value(self, value: float) -> str:
        """Format value with thousand separators."""
        if self._show_thousands_separator:
            return f"{value:,.{self._decimal_places}f}"
        return f"{value:.{self._decimal_places}f}"

    def value(self) -> Decimal:
        """Get the current value as Decimal."""
        text = self._clean_text(self.line_edit.text())
        try:
            return Decimal(text) if text else Decimal(0)
        except InvalidOperation:
            return Decimal(0)

    def set_value(self, value: float | Decimal | str):
        """Set the value."""
        try:
            float_value = float(value)
            formatted = self._format_value(float_value)
            self.line_edit.setText(formatted)
        except (ValueError, InvalidOperation):
            self.line_edit.setText("")

    def set_currency_symbol(self, symbol: str):
        """Set the currency symbol."""
        self._currency_symbol = symbol
        if self._show_symbol:
            if self._symbol_position == "prefix" and hasattr(self, 'prefix_label'):
                self.prefix_label.setText(symbol)
            elif self._symbol_position == "suffix" and hasattr(self, 'suffix_label'):
                self.suffix_label.setText(symbol)

    def set_range(self, minimum: float, maximum: float):
        """Set the valid range."""
        self._minimum = minimum
        self._maximum = maximum
        self._validator.set_range(minimum, maximum)

    def setReadOnly(self, readonly: bool):
        """Set read-only state."""
        self.line_edit.setReadOnly(readonly)

    def clear(self):
        """Clear the input."""
        self.line_edit.clear()

    def setFocus(self):
        """Set focus to the input."""
        self.line_edit.setFocus()

    def selectAll(self):
        """Select all text."""
        self.line_edit.selectAll()


class DateInput(QWidget):
    """
    Date input with calendar popup.

    Features:
    - Calendar popup
    - Today button
    - Keyboard navigation
    - Format customization
    - Date range constraints
    """

    date_changed = pyqtSignal(QDate)
    date_selected = pyqtSignal(QDate)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        date_format: str = "yyyy-MM-dd",
        show_today_button: bool = True,
        show_clear_button: bool = True,
        allow_empty: bool = False,
        placeholder: str = "Select date..."
    ):
        super().__init__(parent)
        self.setObjectName("dateInput")

        self._date_format = date_format
        self._show_today_button = show_today_button
        self._show_clear_button = show_clear_button
        self._allow_empty = allow_empty
        self._placeholder = placeholder
        self._minimum_date: Optional[QDate] = None
        self._maximum_date: Optional[QDate] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the date input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Date edit with calendar popup
        self.date_edit = QDateEdit()
        self.date_edit.setObjectName("dateEdit")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat(self._date_format)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFont(QFont("Segoe UI", 11))
        self.date_edit.setMinimumHeight(32)
        self.date_edit.dateChanged.connect(self._on_date_changed)

        # Style the calendar
        calendar = self.date_edit.calendarWidget()
        if calendar:
            calendar.setGridVisible(True)
            calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)

        layout.addWidget(self.date_edit, 1)

        # Today button
        if self._show_today_button:
            self.today_btn = QToolButton()
            self.today_btn.setObjectName("todayButton")
            self.today_btn.setText("Today")
            self.today_btn.setFont(QFont("Segoe UI", 9))
            self.today_btn.setMinimumHeight(32)
            self.today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.today_btn.clicked.connect(self._set_today)
            layout.addWidget(self.today_btn)

        # Clear button
        if self._show_clear_button and self._allow_empty:
            self.clear_btn = QToolButton()
            self.clear_btn.setObjectName("clearButton")
            self.clear_btn.setText("X")
            self.clear_btn.setFont(QFont("Segoe UI", 9))
            self.clear_btn.setFixedSize(24, 24)
            self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.clear_btn.clicked.connect(self._clear_date)
            layout.addWidget(self.clear_btn)

    def _on_date_changed(self, date: QDate):
        """Handle date change."""
        self.date_changed.emit(date)

    def _set_today(self):
        """Set the date to today."""
        self.date_edit.setDate(QDate.currentDate())
        self.date_selected.emit(QDate.currentDate())

    def _clear_date(self):
        """Clear the date (if allowed)."""
        if self._allow_empty:
            self.date_edit.setSpecialValueText(self._placeholder)
            self.date_edit.setDate(self.date_edit.minimumDate())

    def date(self) -> QDate:
        """Get the current date."""
        return self.date_edit.date()

    def set_date(self, date: QDate):
        """Set the date."""
        self.date_edit.setDate(date)

    def set_minimum_date(self, date: QDate):
        """Set the minimum selectable date."""
        self._minimum_date = date
        self.date_edit.setMinimumDate(date)

    def set_maximum_date(self, date: QDate):
        """Set the maximum selectable date."""
        self._maximum_date = date
        self.date_edit.setMaximumDate(date)

    def set_date_range(self, min_date: QDate, max_date: QDate):
        """Set the valid date range."""
        self._minimum_date = min_date
        self._maximum_date = max_date
        self.date_edit.setDateRange(min_date, max_date)

    def setReadOnly(self, readonly: bool):
        """Set read-only state."""
        self.date_edit.setReadOnly(readonly)

    def to_python_date(self) -> date:
        """Convert to Python date object."""
        qdate = self.date_edit.date()
        return date(qdate.year(), qdate.month(), qdate.day())


class DateRangeInput(QWidget):
    """
    Date range selection with start and end dates.

    Features:
    - Linked start/end date pickers
    - Preset ranges (This week, This month, etc.)
    - Auto-validation (end >= start)
    """

    range_changed = pyqtSignal(QDate, QDate)  # start, end

    # Preset range definitions
    PRESETS = {
        "Today": lambda: (QDate.currentDate(), QDate.currentDate()),
        "Yesterday": lambda: (
            QDate.currentDate().addDays(-1),
            QDate.currentDate().addDays(-1)
        ),
        "This Week": lambda: (
            QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek() + 1),
            QDate.currentDate()
        ),
        "Last Week": lambda: (
            QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek() - 6),
            QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek())
        ),
        "This Month": lambda: (
            QDate(QDate.currentDate().year(), QDate.currentDate().month(), 1),
            QDate.currentDate()
        ),
        "Last Month": lambda: (
            QDate(QDate.currentDate().year(), QDate.currentDate().month(), 1).addMonths(-1),
            QDate(QDate.currentDate().year(), QDate.currentDate().month(), 1).addDays(-1)
        ),
        "This Year": lambda: (
            QDate(QDate.currentDate().year(), 1, 1),
            QDate.currentDate()
        ),
        "Last 7 Days": lambda: (
            QDate.currentDate().addDays(-6),
            QDate.currentDate()
        ),
        "Last 30 Days": lambda: (
            QDate.currentDate().addDays(-29),
            QDate.currentDate()
        ),
        "Last 90 Days": lambda: (
            QDate.currentDate().addDays(-89),
            QDate.currentDate()
        ),
    }

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        date_format: str = "yyyy-MM-dd",
        show_presets: bool = True,
        show_labels: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("dateRangeInput")

        self._date_format = date_format
        self._show_presets = show_presets
        self._show_labels = show_labels

        self._setup_ui()

    def _setup_ui(self):
        """Set up the date range input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Start date
        if self._show_labels:
            start_label = QLabel("From:")
            start_label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(start_label)

        self.start_date = QDateEdit()
        self.start_date.setObjectName("startDateEdit")
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat(self._date_format)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setFont(QFont("Segoe UI", 11))
        self.start_date.setMinimumHeight(32)
        self.start_date.dateChanged.connect(self._on_start_changed)
        layout.addWidget(self.start_date)

        # Separator
        separator = QLabel("-")
        separator.setFont(QFont("Segoe UI", 11))
        layout.addWidget(separator)

        # End date
        if self._show_labels:
            end_label = QLabel("To:")
            end_label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(end_label)

        self.end_date = QDateEdit()
        self.end_date.setObjectName("endDateEdit")
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat(self._date_format)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setFont(QFont("Segoe UI", 11))
        self.end_date.setMinimumHeight(32)
        self.end_date.dateChanged.connect(self._on_end_changed)
        layout.addWidget(self.end_date)

        # Presets button
        if self._show_presets:
            self.presets_btn = QToolButton()
            self.presets_btn.setObjectName("presetsButton")
            self.presets_btn.setText("Presets")
            self.presets_btn.setFont(QFont("Segoe UI", 9))
            self.presets_btn.setMinimumHeight(32)
            self.presets_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self.presets_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # Create presets menu
            menu = QMenu(self)
            for preset_name in self.PRESETS:
                action = menu.addAction(preset_name)
                action.triggered.connect(
                    lambda checked, name=preset_name: self._apply_preset(name)
                )
            self.presets_btn.setMenu(menu)

            layout.addWidget(self.presets_btn)

    def _on_start_changed(self, date: QDate):
        """Handle start date change."""
        # Ensure end date is not before start date
        if self.end_date.date() < date:
            self.end_date.setDate(date)
        self.range_changed.emit(date, self.end_date.date())

    def _on_end_changed(self, date: QDate):
        """Handle end date change."""
        # Ensure start date is not after end date
        if self.start_date.date() > date:
            self.start_date.setDate(date)
        self.range_changed.emit(self.start_date.date(), date)

    def _apply_preset(self, preset_name: str):
        """Apply a preset date range."""
        if preset_name in self.PRESETS:
            start, end = self.PRESETS[preset_name]()
            self.start_date.setDate(start)
            self.end_date.setDate(end)

    def get_range(self) -> Tuple[QDate, QDate]:
        """Get the current date range."""
        return (self.start_date.date(), self.end_date.date())

    def set_range(self, start: QDate, end: QDate):
        """Set the date range."""
        self.start_date.setDate(start)
        self.end_date.setDate(end)

    def get_python_range(self) -> Tuple[date, date]:
        """Get the range as Python date objects."""
        start = self.start_date.date()
        end = self.end_date.date()
        return (
            date(start.year(), start.month(), start.day()),
            date(end.year(), end.month(), end.day())
        )

    def set_date_limits(self, minimum: Optional[QDate], maximum: Optional[QDate]):
        """Set overall date limits for both pickers."""
        if minimum:
            self.start_date.setMinimumDate(minimum)
            self.end_date.setMinimumDate(minimum)
        if maximum:
            self.start_date.setMaximumDate(maximum)
            self.end_date.setMaximumDate(maximum)


class CategorySelector(QComboBox):
    """
    Dropdown with category colors and icons.

    Features:
    - Color-coded categories
    - Icon support
    - Searchable
    - Custom item rendering
    """

    category_selected = pyqtSignal(str, dict)  # category name, category data

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        searchable: bool = True,
        show_colors: bool = True,
        placeholder: str = "Select category..."
    ):
        super().__init__(parent)
        self.setObjectName("categorySelector")

        self._categories: List[Dict[str, Any]] = []
        self._searchable = searchable
        self._show_colors = show_colors
        self._placeholder = placeholder

        self._setup_ui()

    def _setup_ui(self):
        """Set up the category selector UI."""
        self.setFont(QFont("Segoe UI", 11))
        self.setMinimumHeight(32)
        self.setMinimumWidth(150)

        # Make editable for search functionality
        if self._searchable:
            self.setEditable(True)
            self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self.lineEdit().setPlaceholderText(self._placeholder)

            # Set up completer
            self.completer().setCompletionMode(
                QCompleter.CompletionMode.PopupCompletion
            )
            self.completer().setCaseSensitivity(
                Qt.CaseSensitivity.CaseInsensitive
            )

        self.currentIndexChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self, index: int):
        """Handle selection change."""
        if 0 <= index < len(self._categories):
            category = self._categories[index]
            self.category_selected.emit(category.get('name', ''), category)

    def set_categories(self, categories: List[Dict[str, Any]]):
        """
        Set the available categories.

        Each category dict should have:
        - 'name': Category name (required)
        - 'color': Color code (optional)
        - 'icon': Icon path or QIcon (optional)
        - 'id': Category ID (optional)
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
                elif isinstance(icon, QIcon):
                    self.addItem(icon, name)
            elif self._show_colors:
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
            else:
                self.addItem(name)

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

    def set_current_category_by_id(self, category_id: Any):
        """Set the current category by ID."""
        for i, category in enumerate(self._categories):
            if category.get('id') == category_id:
                self.setCurrentIndex(i)
                break

    def add_category(self, category: Dict[str, Any]):
        """Add a single category."""
        self._categories.append(category)
        name = category.get('name', '')
        color = category.get('color', '#888888')

        if self._show_colors:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            self.addItem(QIcon(pixmap), name)
        else:
            self.addItem(name)

    def get_category_names(self) -> List[str]:
        """Get list of all category names."""
        return [cat.get('name', '') for cat in self._categories]


class TagInput(QWidget):
    """
    Multiple tag input widget.

    Features:
    - Add tags by typing and pressing Enter
    - Remove tags with X button or Backspace
    - Auto-complete suggestions
    - Tag limit support
    - Custom tag styling
    """

    tags_changed = pyqtSignal(list)  # List of tag strings
    tag_added = pyqtSignal(str)
    tag_removed = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Add tags...",
        max_tags: int = 10,
        allow_duplicates: bool = False,
        suggestions: Optional[List[str]] = None,
        tag_color: str = "#E3F2FD",
        tag_text_color: str = "#1976D2"
    ):
        super().__init__(parent)
        self.setObjectName("tagInput")

        self._placeholder = placeholder
        self._max_tags = max_tags
        self._allow_duplicates = allow_duplicates
        self._suggestions = suggestions or []
        self._tag_color = tag_color
        self._tag_text_color = tag_text_color
        self._tags: List[str] = []

        self._setup_ui()

    def _setup_ui(self):
        """Set up the tag input UI."""
        self.setMinimumHeight(40)

        # Main container
        self.container = QFrame()
        self.container.setObjectName("tagContainer")
        self.container.setStyleSheet("""
            QFrame#tagContainer {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px;
            }
            QFrame#tagContainer:focus-within {
                border: 2px solid #1976D2;
            }
        """)

        # Flow layout simulation using horizontal layout with wrapping
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.container)

        self.tags_layout = QHBoxLayout(self.container)
        self.tags_layout.setContentsMargins(4, 4, 4, 4)
        self.tags_layout.setSpacing(4)

        # Text input for new tags
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("tagLineEdit")
        self.line_edit.setPlaceholderText(self._placeholder)
        self.line_edit.setFont(QFont("Segoe UI", 10))
        self.line_edit.setFrame(False)
        self.line_edit.setMinimumWidth(100)
        self.line_edit.returnPressed.connect(self._add_current_tag)
        self.line_edit.installEventFilter(self)

        # Set up auto-complete
        if self._suggestions:
            completer = QCompleter(self._suggestions)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            self.line_edit.setCompleter(completer)

        self.tags_layout.addWidget(self.line_edit, 1)

    def eventFilter(self, obj, event):
        """Handle keyboard events for tag removal."""
        if obj == self.line_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Backspace:
                if not self.line_edit.text() and self._tags:
                    self.remove_tag(self._tags[-1])
                    return True
        return super().eventFilter(obj, event)

    def _add_current_tag(self):
        """Add the current input as a tag."""
        tag = self.line_edit.text().strip()
        if tag:
            if self.add_tag(tag):
                self.line_edit.clear()

    def add_tag(self, tag: str) -> bool:
        """
        Add a tag.

        Returns True if tag was added, False otherwise.
        """
        # Check limits
        if len(self._tags) >= self._max_tags:
            return False

        # Check duplicates
        if not self._allow_duplicates and tag.lower() in [t.lower() for t in self._tags]:
            return False

        self._tags.append(tag)
        self._create_tag_widget(tag)
        self.tag_added.emit(tag)
        self.tags_changed.emit(self._tags.copy())
        return True

    def _create_tag_widget(self, tag: str):
        """Create a visual tag widget."""
        tag_widget = QFrame()
        tag_widget.setObjectName("tagWidget")
        tag_widget.setStyleSheet(f"""
            QFrame#tagWidget {{
                background-color: {self._tag_color};
                border-radius: 12px;
                padding: 2px 8px;
            }}
        """)

        tag_layout = QHBoxLayout(tag_widget)
        tag_layout.setContentsMargins(8, 2, 4, 2)
        tag_layout.setSpacing(4)

        # Tag text
        label = QLabel(tag)
        label.setFont(QFont("Segoe UI", 9))
        label.setStyleSheet(f"color: {self._tag_text_color};")
        tag_layout.addWidget(label)

        # Remove button
        remove_btn = QToolButton()
        remove_btn.setText("x")
        remove_btn.setFont(QFont("Segoe UI", 8))
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet(f"""
            QToolButton {{
                color: {self._tag_text_color};
                background: transparent;
                border: none;
                border-radius: 8px;
            }}
            QToolButton:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
        """)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.remove_tag(tag))
        tag_layout.addWidget(remove_btn)

        # Store reference
        tag_widget.tag_text = tag

        # Insert before the line edit
        self.tags_layout.insertWidget(self.tags_layout.count() - 1, tag_widget)

    def remove_tag(self, tag: str):
        """Remove a tag."""
        if tag in self._tags:
            self._tags.remove(tag)

            # Find and remove the widget
            for i in range(self.tags_layout.count()):
                widget = self.tags_layout.itemAt(i).widget()
                if widget and hasattr(widget, 'tag_text') and widget.tag_text == tag:
                    widget.deleteLater()
                    break

            self.tag_removed.emit(tag)
            self.tags_changed.emit(self._tags.copy())

    def tags(self) -> List[str]:
        """Get all current tags."""
        return self._tags.copy()

    def set_tags(self, tags: List[str]):
        """Set tags, replacing existing ones."""
        self.clear()
        for tag in tags:
            self.add_tag(tag)

    def clear(self):
        """Clear all tags."""
        self._tags.clear()

        # Remove all tag widgets
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget() and item.widget() != self.line_edit:
                item.widget().deleteLater()

        self.tags_changed.emit([])

    def set_suggestions(self, suggestions: List[str]):
        """Update auto-complete suggestions."""
        self._suggestions = suggestions
        completer = QCompleter(suggestions)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.line_edit.setCompleter(completer)

    def setReadOnly(self, readonly: bool):
        """Set read-only state."""
        self.line_edit.setReadOnly(readonly)
        self.line_edit.setVisible(not readonly)


class SearchInput(QWidget):
    """
    Search input with icon and clear button.

    Features:
    - Search icon
    - Clear button (appears when text is entered)
    - Debounced search signal
    - Auto-complete support
    """

    text_changed = pyqtSignal(str)
    search_triggered = pyqtSignal(str)
    cleared = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Search...",
        debounce_ms: int = 300,
        show_clear_button: bool = True,
        show_search_icon: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("searchInput")

        self._placeholder = placeholder
        self._debounce_ms = debounce_ms
        self._show_clear_button = show_clear_button
        self._show_search_icon = show_search_icon

        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_search)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the search input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container frame
        self.container = QFrame()
        self.container.setObjectName("searchContainer")
        self.container.setStyleSheet("""
            QFrame#searchContainer {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QFrame#searchContainer:focus-within {
                border: 2px solid #1976D2;
            }
        """)

        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(8, 4, 8, 4)
        container_layout.setSpacing(8)

        # Search icon
        if self._show_search_icon:
            self.search_icon = QLabel()
            self.search_icon.setObjectName("searchIcon")
            # Use a simple text icon (can be replaced with actual icon)
            self.search_icon.setText("O")  # Placeholder for search icon
            self.search_icon.setFont(QFont("Segoe UI Symbol", 12))
            self.search_icon.setStyleSheet("color: #888;")
            container_layout.addWidget(self.search_icon)

        # Text input
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("searchLineEdit")
        self.line_edit.setPlaceholderText(self._placeholder)
        self.line_edit.setFont(QFont("Segoe UI", 11))
        self.line_edit.setFrame(False)
        self.line_edit.setMinimumHeight(28)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.returnPressed.connect(self._on_return_pressed)
        container_layout.addWidget(self.line_edit, 1)

        # Clear button
        if self._show_clear_button:
            self.clear_btn = QToolButton()
            self.clear_btn.setObjectName("clearButton")
            self.clear_btn.setText("X")
            self.clear_btn.setFont(QFont("Segoe UI", 9))
            self.clear_btn.setFixedSize(20, 20)
            self.clear_btn.setStyleSheet("""
                QToolButton {
                    color: #888;
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                }
                QToolButton:hover {
                    background-color: #E0E0E0;
                }
            """)
            self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.clear_btn.clicked.connect(self._on_clear)
            self.clear_btn.setVisible(False)
            container_layout.addWidget(self.clear_btn)

        layout.addWidget(self.container)

    def _on_text_changed(self, text: str):
        """Handle text changes with debouncing."""
        # Show/hide clear button
        if self._show_clear_button:
            self.clear_btn.setVisible(bool(text))

        # Emit immediate text change
        self.text_changed.emit(text)

        # Start debounce timer for search
        if self._debounce_ms > 0:
            self._debounce_timer.start(self._debounce_ms)
        else:
            self._emit_search()

    def _emit_search(self):
        """Emit the search signal."""
        self.search_triggered.emit(self.line_edit.text())

    def _on_return_pressed(self):
        """Handle Enter key - immediate search."""
        self._debounce_timer.stop()
        self.search_triggered.emit(self.line_edit.text())

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
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.line_edit.setCompleter(completer)

    def setPlaceholderText(self, text: str):
        """Set the placeholder text."""
        self._placeholder = text
        self.line_edit.setPlaceholderText(text)

    def setFocus(self):
        """Set focus to the input."""
        self.line_edit.setFocus()


class PasswordInput(QWidget):
    """
    Password input with visibility toggle.

    Features:
    - Show/hide password toggle
    - Strength indicator (optional)
    - Caps lock warning
    """

    text_changed = pyqtSignal(str)
    editing_finished = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placeholder: str = "Enter password...",
        show_toggle: bool = True,
        show_strength: bool = False
    ):
        super().__init__(parent)
        self.setObjectName("passwordInput")

        self._placeholder = placeholder
        self._show_toggle = show_toggle
        self._show_strength = show_strength
        self._password_visible = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the password input UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(0)

        # Container
        self.container = QFrame()
        self.container.setObjectName("passwordContainer")
        self.container.setStyleSheet("""
            QFrame#passwordContainer {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QFrame#passwordContainer:focus-within {
                border: 2px solid #1976D2;
            }
        """)

        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(8, 4, 4, 4)
        container_layout.setSpacing(4)

        # Password input
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("passwordLineEdit")
        self.line_edit.setPlaceholderText(self._placeholder)
        self.line_edit.setFont(QFont("Segoe UI", 11))
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.setFrame(False)
        self.line_edit.setMinimumHeight(28)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.editingFinished.connect(self.editing_finished.emit)
        container_layout.addWidget(self.line_edit, 1)

        # Visibility toggle
        if self._show_toggle:
            self.toggle_btn = QToolButton()
            self.toggle_btn.setObjectName("toggleButton")
            self.toggle_btn.setText("Show")
            self.toggle_btn.setFont(QFont("Segoe UI", 9))
            self.toggle_btn.setStyleSheet("""
                QToolButton {
                    color: #666;
                    background: transparent;
                    border: none;
                    padding: 4px 8px;
                }
                QToolButton:hover {
                    color: #1976D2;
                }
            """)
            self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle_btn.clicked.connect(self._toggle_visibility)
            container_layout.addWidget(self.toggle_btn)

        input_layout.addWidget(self.container)
        layout.addLayout(input_layout)

        # Strength indicator
        if self._show_strength:
            self.strength_bar = QFrame()
            self.strength_bar.setObjectName("strengthBar")
            self.strength_bar.setFixedHeight(4)
            self.strength_bar.setStyleSheet("background-color: #E0E0E0; border-radius: 2px;")
            layout.addWidget(self.strength_bar)

            self.strength_label = QLabel("")
            self.strength_label.setFont(QFont("Segoe UI", 9))
            self.strength_label.setStyleSheet("color: #666;")
            layout.addWidget(self.strength_label)

    def _on_text_changed(self, text: str):
        """Handle text change."""
        self.text_changed.emit(text)

        if self._show_strength:
            self._update_strength(text)

    def _toggle_visibility(self):
        """Toggle password visibility."""
        self._password_visible = not self._password_visible

        if self._password_visible:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Hide")
        else:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Show")

    def _update_strength(self, password: str):
        """Update strength indicator."""
        if not password:
            self.strength_bar.setStyleSheet("background-color: #E0E0E0; border-radius: 2px;")
            self.strength_label.setText("")
            return

        # Simple strength calculation
        score = 0
        if len(password) >= 8:
            score += 25
        if len(password) >= 12:
            score += 25
        if re.search(r'[A-Z]', password) and re.search(r'[a-z]', password):
            score += 25
        if re.search(r'\d', password) and re.search(r'[!@#$%^&*]', password):
            score += 25

        # Update display
        if score < 25:
            color = "#F44336"
            label = "Weak"
        elif score < 50:
            color = "#FF9800"
            label = "Fair"
        elif score < 75:
            color = "#FFC107"
            label = "Good"
        else:
            color = "#4CAF50"
            label = "Strong"

        self.strength_bar.setStyleSheet(
            f"background-color: {color}; border-radius: 2px;"
        )
        self.strength_label.setText(label)
        self.strength_label.setStyleSheet(f"color: {color};")

    def text(self) -> str:
        """Get the password text."""
        return self.line_edit.text()

    def set_text(self, text: str):
        """Set the password text."""
        self.line_edit.setText(text)

    def clear(self):
        """Clear the input."""
        self.line_edit.clear()

    def setFocus(self):
        """Set focus."""
        self.line_edit.setFocus()


class NumericInput(QWidget):
    """
    Numeric input with increment/decrement buttons.

    Features:
    - Spin buttons
    - Keyboard increment (up/down arrows)
    - Range validation
    - Step size configuration
    """

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        minimum: int = 0,
        maximum: int = 100,
        value: int = 0,
        step: int = 1,
        show_buttons: bool = True,
        prefix: str = "",
        suffix: str = ""
    ):
        super().__init__(parent)
        self.setObjectName("numericInput")

        self._minimum = minimum
        self._maximum = maximum
        self._value = value
        self._step = step
        self._show_buttons = show_buttons
        self._prefix = prefix
        self._suffix = suffix

        self._setup_ui()

    def _setup_ui(self):
        """Set up the numeric input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Decrement button
        if self._show_buttons:
            self.dec_btn = QToolButton()
            self.dec_btn.setText("-")
            self.dec_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            self.dec_btn.setFixedSize(32, 32)
            self.dec_btn.setStyleSheet("""
                QToolButton {
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px 0 0 4px;
                }
                QToolButton:hover {
                    background-color: #E0E0E0;
                }
                QToolButton:pressed {
                    background-color: #BDBDBD;
                }
            """)
            self.dec_btn.setAutoRepeat(True)
            self.dec_btn.setAutoRepeatDelay(500)
            self.dec_btn.setAutoRepeatInterval(100)
            self.dec_btn.clicked.connect(self._decrement)
            layout.addWidget(self.dec_btn)

        # Value display
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("numericLineEdit")
        self.line_edit.setFont(QFont("Segoe UI", 11))
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setMinimumHeight(32)
        self.line_edit.setText(self._format_value())
        self.line_edit.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self.line_edit, 1)

        # Increment button
        if self._show_buttons:
            self.inc_btn = QToolButton()
            self.inc_btn.setText("+")
            self.inc_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            self.inc_btn.setFixedSize(32, 32)
            self.inc_btn.setStyleSheet("""
                QToolButton {
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 0 4px 4px 0;
                }
                QToolButton:hover {
                    background-color: #E0E0E0;
                }
                QToolButton:pressed {
                    background-color: #BDBDBD;
                }
            """)
            self.inc_btn.setAutoRepeat(True)
            self.inc_btn.setAutoRepeatDelay(500)
            self.inc_btn.setAutoRepeatInterval(100)
            self.inc_btn.clicked.connect(self._increment)
            layout.addWidget(self.inc_btn)

    def _format_value(self) -> str:
        """Format the value for display."""
        return f"{self._prefix}{self._value}{self._suffix}"

    def _parse_value(self, text: str) -> int:
        """Parse value from display text."""
        # Remove prefix and suffix
        clean = text.replace(self._prefix, "").replace(self._suffix, "").strip()
        try:
            return int(clean)
        except ValueError:
            return self._value

    def _increment(self):
        """Increment the value."""
        new_value = min(self._value + self._step, self._maximum)
        if new_value != self._value:
            self._value = new_value
            self.line_edit.setText(self._format_value())
            self.value_changed.emit(self._value)

    def _decrement(self):
        """Decrement the value."""
        new_value = max(self._value - self._step, self._minimum)
        if new_value != self._value:
            self._value = new_value
            self.line_edit.setText(self._format_value())
            self.value_changed.emit(self._value)

    def _on_editing_finished(self):
        """Handle manual value entry."""
        parsed = self._parse_value(self.line_edit.text())
        clamped = max(self._minimum, min(parsed, self._maximum))

        if clamped != self._value:
            self._value = clamped
            self.value_changed.emit(self._value)

        self.line_edit.setText(self._format_value())

    def value(self) -> int:
        """Get the current value."""
        return self._value

    def set_value(self, value: int):
        """Set the value."""
        self._value = max(self._minimum, min(value, self._maximum))
        self.line_edit.setText(self._format_value())

    def set_range(self, minimum: int, maximum: int):
        """Set the valid range."""
        self._minimum = minimum
        self._maximum = maximum
        self._value = max(minimum, min(self._value, maximum))
        self.line_edit.setText(self._format_value())

    def setReadOnly(self, readonly: bool):
        """Set read-only state."""
        self.line_edit.setReadOnly(readonly)
        if self._show_buttons:
            self.inc_btn.setEnabled(not readonly)
            self.dec_btn.setEnabled(not readonly)
