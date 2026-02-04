"""
Table Header Module

Custom header implementations for tables with sorting indicators,
filter dropdowns, and column visibility toggles.
"""

from PyQt6.QtWidgets import (
    QHeaderView, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMenu, QWidgetAction,
    QCheckBox, QFrame, QDateEdit, QSpinBox, QDoubleSpinBox,
    QStyleOptionHeader, QStyle, QApplication, QToolButton
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QRect, QPoint, QSize, QDate, QModelIndex
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
    QMouseEvent, QPainterPath, QPolygon, QCursor, QIcon, QPixmap
)
from typing import Optional, List, Dict, Any, Tuple, Set
from datetime import date, datetime
from enum import Enum


# =============================================================================
# Sort Direction Enum
# =============================================================================

class SortDirection(Enum):
    """Sort direction enumeration."""
    NONE = 0
    ASCENDING = 1
    DESCENDING = 2


# =============================================================================
# Sortable Header View
# =============================================================================

class SortableHeader(QHeaderView):
    """
    Custom header view with enhanced sorting and filtering capabilities.

    Features:
    - Multi-column sorting with visual indicators
    - Click to sort (cycles through: none -> asc -> desc -> none)
    - Shift+click for multi-column sort
    - Filter dropdown menus per column
    - Column visibility toggle via context menu
    - Resizable columns with visual feedback
    """

    # Signals
    sort_changed = pyqtSignal(list)  # List of (column, SortDirection)
    filter_changed = pyqtSignal(int, object)  # column, filter value
    column_visibility_changed = pyqtSignal(int, bool)  # column, visible
    column_resized = pyqtSignal(int, int, int)  # column, old_size, new_size

    def __init__(self, orientation: Qt.Orientation = Qt.Orientation.Horizontal,
                 parent: Optional[QWidget] = None):
        super().__init__(orientation, parent)

        # Sorting state
        self._sort_columns: List[Tuple[int, SortDirection]] = []
        self._sortable_columns: Set[int] = set()
        self._max_sort_columns = 3  # Maximum columns for multi-sort

        # Filter state
        self._filterable_columns: Set[int] = set()
        self._column_filters: Dict[int, Any] = {}
        self._filter_widgets: Dict[int, QWidget] = {}

        # Column visibility
        self._hidden_columns: Set[int] = set()
        self._can_hide_columns: Set[int] = set()

        # Visual settings
        self._sort_indicator_size = 10
        self._filter_icon_size = 12
        self._header_padding = 8

        # Colors
        self._sort_indicator_color = QColor("#2196F3")
        self._filter_active_color = QColor("#4CAF50")
        self._hover_color = QColor("#E3F2FD")

        # Hover tracking
        self._hover_section = -1
        self._hover_sort = False
        self._hover_filter = False

        # Setup
        self._setup_header()

    def _setup_header(self):
        """Configure the header."""
        self.setSectionsClickable(True)
        self.setSectionsMovable(True)
        self.setHighlightSections(True)
        self.setStretchLastSection(True)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Connect section click
        self.sectionClicked.connect(self._on_section_clicked)

        # Connect resize
        self.sectionResized.connect(self._on_section_resized)

    # =========================================================================
    # Column Configuration
    # =========================================================================

    def set_column_sortable(self, column: int, sortable: bool = True):
        """Set whether a column is sortable."""
        if sortable:
            self._sortable_columns.add(column)
        else:
            self._sortable_columns.discard(column)
            # Remove from sort if present
            self._sort_columns = [(c, d) for c, d in self._sort_columns if c != column]

    def set_column_filterable(self, column: int, filterable: bool = True):
        """Set whether a column has a filter dropdown."""
        if filterable:
            self._filterable_columns.add(column)
        else:
            self._filterable_columns.discard(column)
            self._column_filters.pop(column, None)

    def set_column_hideable(self, column: int, hideable: bool = True):
        """Set whether a column can be hidden."""
        if hideable:
            self._can_hide_columns.add(column)
        else:
            self._can_hide_columns.discard(column)

    def set_all_columns_sortable(self, sortable: bool = True):
        """Set all columns sortable."""
        if sortable:
            for i in range(self.count()):
                self._sortable_columns.add(i)
        else:
            self._sortable_columns.clear()

    def set_all_columns_filterable(self, filterable: bool = True):
        """Set all columns filterable."""
        if filterable:
            for i in range(self.count()):
                self._filterable_columns.add(i)
        else:
            self._filterable_columns.clear()
            self._column_filters.clear()

    # =========================================================================
    # Sorting
    # =========================================================================

    def _on_section_clicked(self, logical_index: int):
        """Handle header section click."""
        if logical_index not in self._sortable_columns:
            return

        modifiers = QApplication.keyboardModifiers()
        multi_sort = modifiers & Qt.KeyboardModifier.ShiftModifier

        # Find current sort state for this column
        current_direction = SortDirection.NONE
        current_priority = -1
        for i, (col, direction) in enumerate(self._sort_columns):
            if col == logical_index:
                current_direction = direction
                current_priority = i
                break

        # Cycle through sort directions
        if current_direction == SortDirection.NONE:
            new_direction = SortDirection.ASCENDING
        elif current_direction == SortDirection.ASCENDING:
            new_direction = SortDirection.DESCENDING
        else:
            new_direction = SortDirection.NONE

        # Update sort columns
        if multi_sort:
            # Multi-column sort mode
            if current_priority >= 0:
                # Update existing sort
                if new_direction == SortDirection.NONE:
                    self._sort_columns.pop(current_priority)
                else:
                    self._sort_columns[current_priority] = (logical_index, new_direction)
            elif new_direction != SortDirection.NONE:
                # Add new sort column
                if len(self._sort_columns) < self._max_sort_columns:
                    self._sort_columns.append((logical_index, new_direction))
        else:
            # Single column sort mode
            if new_direction == SortDirection.NONE:
                self._sort_columns.clear()
            else:
                self._sort_columns = [(logical_index, new_direction)]

        # Emit signal
        self.sort_changed.emit(self._sort_columns)

        # Update visual
        self.viewport().update()

    def get_sort_state(self) -> List[Tuple[int, SortDirection]]:
        """Get current sort state."""
        return self._sort_columns.copy()

    def set_sort_state(self, sort_columns: List[Tuple[int, SortDirection]]):
        """Set sort state programmatically."""
        self._sort_columns = [(c, d) for c, d in sort_columns
                               if c in self._sortable_columns]
        self.sort_changed.emit(self._sort_columns)
        self.viewport().update()

    def clear_sort(self):
        """Clear all sorting."""
        self._sort_columns.clear()
        self.sort_changed.emit([])
        self.viewport().update()

    # =========================================================================
    # Filtering
    # =========================================================================

    def set_filter(self, column: int, value: Any):
        """Set filter value for a column."""
        if value is None or value == "":
            self._column_filters.pop(column, None)
        else:
            self._column_filters[column] = value
        self.filter_changed.emit(column, value)
        self.viewport().update()

    def get_filter(self, column: int) -> Any:
        """Get filter value for a column."""
        return self._column_filters.get(column)

    def clear_filter(self, column: int):
        """Clear filter for a column."""
        self._column_filters.pop(column, None)
        self.filter_changed.emit(column, None)
        self.viewport().update()

    def clear_all_filters(self):
        """Clear all filters."""
        columns = list(self._column_filters.keys())
        self._column_filters.clear()
        for col in columns:
            self.filter_changed.emit(col, None)
        self.viewport().update()

    def has_active_filter(self, column: int) -> bool:
        """Check if column has an active filter."""
        return column in self._column_filters

    # =========================================================================
    # Column Visibility
    # =========================================================================

    def hide_column(self, column: int):
        """Hide a column."""
        if column in self._can_hide_columns:
            self._hidden_columns.add(column)
            self.hideSection(column)
            self.column_visibility_changed.emit(column, False)

    def show_column(self, column: int):
        """Show a column."""
        self._hidden_columns.discard(column)
        self.showSection(column)
        self.column_visibility_changed.emit(column, True)

    def toggle_column_visibility(self, column: int):
        """Toggle column visibility."""
        if column in self._hidden_columns:
            self.show_column(column)
        else:
            self.hide_column(column)

    def is_column_hidden(self, column: int) -> bool:
        """Check if column is hidden."""
        return column in self._hidden_columns

    def get_visible_columns(self) -> List[int]:
        """Get list of visible column indices."""
        return [i for i in range(self.count()) if i not in self._hidden_columns]

    # =========================================================================
    # Painting
    # =========================================================================

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int):
        """Paint a header section with sort indicator and filter icon."""
        painter.save()

        # Get section data
        model = self.model()
        if not model:
            super().paintSection(painter, rect, logical_index)
            painter.restore()
            return

        # Draw background
        if logical_index == self._hover_section:
            painter.fillRect(rect, self._hover_color)
        else:
            painter.fillRect(rect, self.palette().button().color())

        # Get header text
        text = model.headerData(logical_index, self.orientation(),
                                 Qt.ItemDataRole.DisplayRole)
        text = str(text) if text else ""

        # Calculate available width for text
        text_rect = rect.adjusted(self._header_padding, 0, -self._header_padding, 0)

        # Reserve space for sort indicator
        sort_direction = SortDirection.NONE
        sort_priority = -1
        for i, (col, direction) in enumerate(self._sort_columns):
            if col == logical_index:
                sort_direction = direction
                sort_priority = i
                break

        if sort_direction != SortDirection.NONE:
            text_rect.setRight(text_rect.right() - self._sort_indicator_size - 4)

        # Reserve space for filter icon
        has_filter = logical_index in self._filterable_columns
        if has_filter:
            text_rect.setRight(text_rect.right() - self._filter_icon_size - 4)

        # Draw text
        painter.setPen(self.palette().text().color())
        font = painter.font()
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(text_rect,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         text)

        # Draw sort indicator
        if sort_direction != SortDirection.NONE:
            self._draw_sort_indicator(painter, rect, sort_direction, sort_priority)

        # Draw filter icon
        if has_filter:
            is_active = logical_index in self._column_filters
            self._draw_filter_icon(painter, rect, is_active)

        # Draw separator line
        painter.setPen(QPen(QColor("#E0E0E0"), 1))
        painter.drawLine(rect.right() - 1, rect.top() + 4,
                         rect.right() - 1, rect.bottom() - 4)

        painter.restore()

    def _draw_sort_indicator(self, painter: QPainter, rect: QRect,
                              direction: SortDirection, priority: int):
        """Draw sort direction indicator."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate position (right side, before filter icon if present)
        size = self._sort_indicator_size
        x = rect.right() - self._header_padding - size
        y = rect.top() + (rect.height() - size) // 2

        # Adjust for filter icon if column is filterable
        if self._filterable_columns:
            x -= self._filter_icon_size + 4

        # Set color based on priority
        if priority == 0:
            color = self._sort_indicator_color
        else:
            color = self._sort_indicator_color.lighter(130)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        # Draw arrow
        if direction == SortDirection.ASCENDING:
            # Up arrow
            points = [
                QPoint(x + size // 2, y),
                QPoint(x, y + size),
                QPoint(x + size, y + size)
            ]
        else:
            # Down arrow
            points = [
                QPoint(x, y),
                QPoint(x + size, y),
                QPoint(x + size // 2, y + size)
            ]

        painter.drawPolygon(QPolygon(points))

        # Draw priority number for multi-sort
        if priority > 0 or len(self._sort_columns) > 1:
            painter.setPen(Qt.GlobalColor.white)
            font = painter.font()
            font.setPointSize(7)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            num_rect = QRect(x - 2, y - 2, size + 4, size + 4)
            painter.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, str(priority + 1))

        painter.restore()

    def _draw_filter_icon(self, painter: QPainter, rect: QRect, is_active: bool):
        """Draw filter icon."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate position (right side)
        size = self._filter_icon_size
        x = rect.right() - self._header_padding - size
        y = rect.top() + (rect.height() - size) // 2

        # Set color
        if is_active:
            color = self._filter_active_color
        else:
            color = QColor("#9E9E9E")

        painter.setPen(QPen(color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw funnel shape
        path = QPainterPath()
        path.moveTo(x, y + 2)
        path.lineTo(x + size, y + 2)
        path.lineTo(x + size * 0.6, y + size * 0.5)
        path.lineTo(x + size * 0.6, y + size)
        path.lineTo(x + size * 0.4, y + size)
        path.lineTo(x + size * 0.4, y + size * 0.5)
        path.closeSubpath()

        if is_active:
            painter.setBrush(color.lighter(150))

        painter.drawPath(path)

        painter.restore()

    # =========================================================================
    # Mouse Events
    # =========================================================================

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for hover effects."""
        pos = event.pos()
        section = self.logicalIndexAt(pos)

        if section != self._hover_section:
            self._hover_section = section
            self.viewport().update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover_section = -1
        self.viewport().update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double click for auto-resize."""
        pos = event.pos()
        section = self.logicalIndexAt(pos)

        # Check if near section edge
        section_start = self.sectionViewportPosition(section)
        section_width = self.sectionSize(section)

        if abs(pos.x() - (section_start + section_width)) < 5:
            # Near right edge - auto resize
            self.resizeSection(section, self.sectionSizeHint(section))
        else:
            super().mouseDoubleClickEvent(event)

    # =========================================================================
    # Context Menu
    # =========================================================================

    def _show_context_menu(self, pos: QPoint):
        """Show column context menu."""
        section = self.logicalIndexAt(pos)
        if section < 0:
            return

        menu = QMenu(self)

        # Sort options
        if section in self._sortable_columns:
            sort_asc = menu.addAction("Sort Ascending")
            sort_asc.triggered.connect(
                lambda: self._set_single_sort(section, SortDirection.ASCENDING))

            sort_desc = menu.addAction("Sort Descending")
            sort_desc.triggered.connect(
                lambda: self._set_single_sort(section, SortDirection.DESCENDING))

            if self._sort_columns:
                clear_sort = menu.addAction("Clear Sort")
                clear_sort.triggered.connect(self.clear_sort)

            menu.addSeparator()

        # Filter options
        if section in self._filterable_columns:
            if section in self._column_filters:
                clear_filter = menu.addAction("Clear Filter")
                clear_filter.triggered.connect(lambda: self.clear_filter(section))
            else:
                # Add filter submenu/action
                filter_action = menu.addAction("Filter...")
                filter_action.triggered.connect(lambda: self._show_filter_dialog(section))

            menu.addSeparator()

        # Column visibility
        visibility_menu = menu.addMenu("Columns")
        model = self.model()
        if model:
            for i in range(self.count()):
                header = model.headerData(i, self.orientation(),
                                           Qt.ItemDataRole.DisplayRole)
                action = visibility_menu.addAction(str(header) if header else f"Column {i}")
                action.setCheckable(True)
                action.setChecked(i not in self._hidden_columns)

                if i in self._can_hide_columns:
                    action.triggered.connect(
                        lambda checked, col=i: self.show_column(col) if checked else self.hide_column(col))
                else:
                    action.setEnabled(False)

        # Show all columns option
        if self._hidden_columns:
            visibility_menu.addSeparator()
            show_all = visibility_menu.addAction("Show All Columns")
            show_all.triggered.connect(self._show_all_columns)

        menu.exec(self.mapToGlobal(pos))

    def _set_single_sort(self, column: int, direction: SortDirection):
        """Set single column sort."""
        self._sort_columns = [(column, direction)]
        self.sort_changed.emit(self._sort_columns)
        self.viewport().update()

    def _show_filter_dialog(self, column: int):
        """Show filter dialog for column."""
        # This would show a filter input dialog
        # For now, emit signal to let parent handle it
        pass

    def _show_all_columns(self):
        """Show all hidden columns."""
        for col in list(self._hidden_columns):
            self.show_column(col)

    # =========================================================================
    # Resize Handling
    # =========================================================================

    def _on_section_resized(self, logical_index: int, old_size: int, new_size: int):
        """Handle section resize."""
        self.column_resized.emit(logical_index, old_size, new_size)


# =============================================================================
# Filter Header Widget
# =============================================================================

class FilterHeaderWidget(QFrame):
    """
    A header widget with embedded filter controls.

    Features:
    - Text filter input
    - Dropdown filter for categories
    - Date range filter
    - Number range filter
    - Clear all filters button
    """

    filter_changed = pyqtSignal(str, object)  # column_key, value

    def __init__(self, columns: List[Dict[str, Any]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("filterHeaderWidget")

        self._columns = columns or []
        self._filters: Dict[str, QWidget] = {}
        self._filter_values: Dict[str, Any] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Set up the filter header UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Create filter widgets for each column
        for col in self._columns:
            if not col.get("filterable", True):
                continue

            key = col.get("key", "")
            col_type = col.get("type", "text")
            label = col.get("header", key)

            # Container for this filter
            container = QFrame()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(2)

            # Label
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet("color: #757575;")
            container_layout.addWidget(lbl)

            # Filter widget based on type
            if col_type == "text":
                widget = QLineEdit()
                widget.setPlaceholderText("Filter...")
                widget.textChanged.connect(
                    lambda text, k=key: self._on_filter_changed(k, text))
            elif col_type == "select":
                widget = QComboBox()
                widget.addItem("All", None)
                for option in col.get("options", []):
                    widget.addItem(str(option), option)
                widget.currentIndexChanged.connect(
                    lambda idx, w=widget, k=key: self._on_filter_changed(k, w.currentData()))
            elif col_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setSpecialValueText("Any")
                widget.dateChanged.connect(
                    lambda d, k=key: self._on_filter_changed(k, d.toPyDate() if d.isValid() else None))
            elif col_type == "number":
                widget = QDoubleSpinBox()
                widget.setSpecialValueText("Any")
                widget.setMinimum(-999999999)
                widget.setMaximum(999999999)
                widget.valueChanged.connect(
                    lambda val, k=key: self._on_filter_changed(k, val if val != 0 else None))
            else:
                widget = QLineEdit()
                widget.textChanged.connect(
                    lambda text, k=key: self._on_filter_changed(k, text))

            widget.setMinimumWidth(100)
            container_layout.addWidget(widget)

            self._filters[key] = widget
            layout.addWidget(container)

        layout.addStretch()

        # Clear all button
        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self.clear_all_filters)
        layout.addWidget(clear_btn)

    def _on_filter_changed(self, key: str, value: Any):
        """Handle filter value change."""
        if value is None or value == "":
            self._filter_values.pop(key, None)
        else:
            self._filter_values[key] = value
        self.filter_changed.emit(key, value)

    def get_filter(self, key: str) -> Any:
        """Get filter value for a column."""
        return self._filter_values.get(key)

    def get_all_filters(self) -> Dict[str, Any]:
        """Get all active filters."""
        return self._filter_values.copy()

    def set_filter(self, key: str, value: Any):
        """Set filter value programmatically."""
        if key in self._filters:
            widget = self._filters[key]
            if isinstance(widget, QLineEdit):
                widget.setText(str(value) if value else "")
            elif isinstance(widget, QComboBox):
                idx = widget.findData(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif isinstance(widget, QDateEdit):
                if isinstance(value, (date, datetime)):
                    widget.setDate(QDate(value.year, value.month, value.day))
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.setValue(value if value else 0)

    def clear_filter(self, key: str):
        """Clear a specific filter."""
        if key in self._filters:
            widget = self._filters[key]
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate())
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.setValue(0)

    def clear_all_filters(self):
        """Clear all filters."""
        for key in list(self._filters.keys()):
            self.clear_filter(key)


# =============================================================================
# Column Visibility Menu
# =============================================================================

class ColumnVisibilityMenu(QMenu):
    """
    A menu for toggling column visibility.

    Features:
    - Checkbox for each column
    - Show all / Hide all options
    - Drag to reorder columns
    """

    visibility_changed = pyqtSignal(str, bool)  # column_key, visible
    order_changed = pyqtSignal(list)  # list of column keys in new order

    def __init__(self, columns: List[Dict[str, Any]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__("Columns", parent)

        self._columns = columns or []
        self._checkboxes: Dict[str, QCheckBox] = {}

        self._setup_menu()

    def _setup_menu(self):
        """Set up the menu items."""
        for col in self._columns:
            key = col.get("key", "")
            header = col.get("header", key)
            visible = col.get("visible", True)
            can_hide = col.get("hideable", True)

            action = QWidgetAction(self)
            checkbox = QCheckBox(header)
            checkbox.setChecked(visible)
            checkbox.setEnabled(can_hide)
            checkbox.stateChanged.connect(
                lambda state, k=key: self.visibility_changed.emit(k, state == Qt.CheckState.Checked.value))

            action.setDefaultWidget(checkbox)
            self.addAction(action)
            self._checkboxes[key] = checkbox

        self.addSeparator()

        # Show all
        show_all = self.addAction("Show All")
        show_all.triggered.connect(self._show_all)

        # Hide all (except non-hideable)
        hide_all = self.addAction("Hide All")
        hide_all.triggered.connect(self._hide_all)

    def _show_all(self):
        """Show all columns."""
        for key, checkbox in self._checkboxes.items():
            if checkbox.isEnabled():
                checkbox.setChecked(True)

    def _hide_all(self):
        """Hide all hideable columns."""
        for key, checkbox in self._checkboxes.items():
            if checkbox.isEnabled():
                checkbox.setChecked(False)

    def set_column_visible(self, key: str, visible: bool):
        """Set column visibility programmatically."""
        if key in self._checkboxes:
            self._checkboxes[key].setChecked(visible)

    def update_columns(self, columns: List[Dict[str, Any]]):
        """Update column definitions."""
        self._columns = columns
        self.clear()
        self._checkboxes.clear()
        self._setup_menu()


# =============================================================================
# Quick Filter Toolbar
# =============================================================================

class QuickFilterToolbar(QFrame):
    """
    A toolbar with quick filter buttons for common filter operations.

    Features:
    - Preset filter buttons (Today, This Week, This Month, etc.)
    - Toggle buttons for transaction types
    - Search input
    """

    filter_preset_selected = pyqtSignal(str)  # preset name
    type_filter_changed = pyqtSignal(list)  # list of selected types
    search_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("quickFilterToolbar")

        self._selected_types: Set[str] = {"income", "expense", "transfer"}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the toolbar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Date presets
        date_presets = [
            ("Today", "today"),
            ("This Week", "week"),
            ("This Month", "month"),
            ("This Year", "year"),
            ("All Time", "all")
        ]

        for label, preset in date_presets:
            btn = QPushButton(label)
            btn.setObjectName("filterPresetButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, p=preset: self._on_preset_clicked(p))
            layout.addWidget(btn)

        layout.addSpacing(16)

        # Type toggles
        type_colors = {
            "income": "#81C784",
            "expense": "#E57373",
            "transfer": "#64B5F6"
        }

        for type_name, color in type_colors.items():
            btn = QPushButton(type_name.capitalize())
            btn.setObjectName("filterTypeButton")
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setStyleSheet(f"""
                QPushButton[checked="true"] {{
                    background-color: {color};
                    color: white;
                }}
            """)
            btn.toggled.connect(lambda checked, t=type_name: self._on_type_toggled(t, checked))
            layout.addWidget(btn)

        layout.addStretch()

        # Search input
        search = QLineEdit()
        search.setPlaceholderText("Search transactions...")
        search.setObjectName("quickSearchInput")
        search.setMaximumWidth(250)
        search.textChanged.connect(self.search_changed.emit)
        layout.addWidget(search)

    def _on_preset_clicked(self, preset: str):
        """Handle preset button click."""
        self.filter_preset_selected.emit(preset)

    def _on_type_toggled(self, type_name: str, checked: bool):
        """Handle type toggle."""
        if checked:
            self._selected_types.add(type_name)
        else:
            self._selected_types.discard(type_name)
        self.type_filter_changed.emit(list(self._selected_types))

    def get_selected_types(self) -> List[str]:
        """Get list of selected types."""
        return list(self._selected_types)

    def set_selected_types(self, types: List[str]):
        """Set selected types."""
        self._selected_types = set(types)
        # Update button states
        for child in self.children():
            if isinstance(child, QPushButton) and child.objectName() == "filterTypeButton":
                type_name = child.text().lower()
                child.setChecked(type_name in self._selected_types)
