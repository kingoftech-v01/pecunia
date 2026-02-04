"""
Table Widgets Module

Reusable data table widgets with virtual scrolling, sorting, filtering,
pagination, custom delegates, context menus, and empty state handling.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QLabel, QComboBox,
    QLineEdit, QFrame, QMenu, QStyledItemDelegate, QStyleOptionViewItem,
    QStyle, QApplication, QTableView, QScrollBar, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QModelIndex, QRect, QSize, QAbstractTableModel,
    QTimer, QPoint, QItemSelectionModel
)
from PyQt6.QtGui import (
    QFont, QColor, QAction, QPainter, QPen, QBrush, QPalette,
    QKeyEvent, QWheelEvent, QMouseEvent, QKeySequence, QShortcut
)
from typing import Optional, List, Dict, Any, Callable, Tuple, Set
from decimal import Decimal
from datetime import datetime, date


# =============================================================================
# Virtual Table View - High Performance Table with Lazy Loading
# =============================================================================

class VirtualTableView(QTableView):
    """
    High-performance table view with virtual scrolling and lazy loading.

    Features:
    - Virtual scrolling for large datasets
    - Lazy loading of visible rows only
    - Efficient column resizing
    - Row selection with keyboard navigation
    - Multi-column sorting
    - Context menu support
    - Inline editing capability
    """

    # Signals
    row_selected = pyqtSignal(int, dict)  # row index, row data
    row_double_clicked = pyqtSignal(int, dict)
    rows_selected = pyqtSignal(list)  # list of row indices
    context_menu_requested = pyqtSignal(int, dict, QPoint)  # row, data, position
    edit_requested = pyqtSignal(int, dict)
    delete_requested = pyqtSignal(int, dict)
    selection_changed = pyqtSignal(list)  # list of selected row indices
    visible_rows_changed = pyqtSignal(int, int)  # first visible, last visible
    data_load_requested = pyqtSignal(int, int)  # start row, count

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("virtualTableView")

        # Configuration
        self._row_height = 36
        self._buffer_rows = 5  # Extra rows to load above/below visible area
        self._visible_start = 0
        self._visible_end = 0
        self._total_rows = 0
        self._loaded_range: Tuple[int, int] = (0, 0)

        # Column configuration
        self._column_widths: Dict[int, int] = {}
        self._resizable_columns: Set[int] = set()
        self._sortable_columns: Set[int] = set()
        self._current_sort: List[Tuple[int, Qt.SortOrder]] = []

        # Selection state
        self._selected_rows: Set[int] = set()
        self._anchor_row: int = -1

        # Setup
        self._setup_view()
        self._setup_keyboard_navigation()
        self._setup_scroll_handling()

    def _setup_view(self):
        """Configure the table view."""
        # Selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Appearance
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setWordWrap(False)

        # Performance optimizations
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        # Double click handling
        self.doubleClicked.connect(self._on_double_click)

    def _setup_keyboard_navigation(self):
        """Set up keyboard shortcuts and navigation."""
        # Select all shortcut
        select_all = QShortcut(QKeySequence.StandardKey.SelectAll, self)
        select_all.activated.connect(self.select_all_rows)

        # Delete shortcut
        delete_shortcut = QShortcut(QKeySequence.StandardKey.Delete, self)
        delete_shortcut.activated.connect(self._on_delete_pressed)

        # Enter/Return for edit
        enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        enter_shortcut.activated.connect(self._on_enter_pressed)

    def _setup_scroll_handling(self):
        """Set up scroll event handling for lazy loading."""
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._on_scroll_settled)

    def setModel(self, model: QAbstractTableModel):
        """Set the data model."""
        super().setModel(model)
        if model:
            self._total_rows = model.rowCount()
            model.rowsInserted.connect(self._on_rows_inserted)
            model.rowsRemoved.connect(self._on_rows_removed)
            model.dataChanged.connect(self._on_data_changed)
            model.modelReset.connect(self._on_model_reset)

    def _on_rows_inserted(self, parent: QModelIndex, first: int, last: int):
        """Handle rows inserted into model."""
        self._total_rows = self.model().rowCount() if self.model() else 0

    def _on_rows_removed(self, parent: QModelIndex, first: int, last: int):
        """Handle rows removed from model."""
        self._total_rows = self.model().rowCount() if self.model() else 0
        # Update selection if selected rows were removed
        self._selected_rows = {r for r in self._selected_rows
                              if r < self._total_rows}

    def _on_data_changed(self, topLeft: QModelIndex, bottomRight: QModelIndex,
                         roles: List[int] = None):
        """Handle data changes in model."""
        # Viewport update will be handled by Qt
        pass

    def _on_model_reset(self):
        """Handle model reset."""
        self._total_rows = self.model().rowCount() if self.model() else 0
        self._selected_rows.clear()
        self._anchor_row = -1
        self._update_visible_range()

    def scrollContentsBy(self, dx: int, dy: int):
        """Handle scroll events."""
        super().scrollContentsBy(dx, dy)
        # Debounce scroll handling
        self._scroll_timer.start(50)

    def _on_scroll_settled(self):
        """Called when scrolling has stopped."""
        self._update_visible_range()

    def _update_visible_range(self):
        """Update the range of visible rows and trigger lazy loading."""
        if not self.model():
            return

        viewport_rect = self.viewport().rect()
        first_visible = self.rowAt(0)
        last_visible = self.rowAt(viewport_rect.height())

        if first_visible < 0:
            first_visible = 0
        if last_visible < 0 or last_visible >= self._total_rows:
            last_visible = self._total_rows - 1

        # Add buffer rows
        load_start = max(0, first_visible - self._buffer_rows)
        load_end = min(self._total_rows - 1, last_visible + self._buffer_rows)

        if (load_start, load_end) != self._loaded_range:
            self._loaded_range = (load_start, load_end)
            self.visible_rows_changed.emit(first_visible, last_visible)
            self.data_load_requested.emit(load_start, load_end - load_start + 1)

        self._visible_start = first_visible
        self._visible_end = last_visible

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        self._update_visible_range()

    # =========================================================================
    # Column Management
    # =========================================================================

    def set_column_width(self, column: int, width: int):
        """Set the width of a specific column."""
        self._column_widths[column] = width
        self.setColumnWidth(column, width)

    def set_column_resizable(self, column: int, resizable: bool = True):
        """Set whether a column can be resized."""
        if resizable:
            self._resizable_columns.add(column)
            self.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Interactive)
        else:
            self._resizable_columns.discard(column)
            self.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Fixed)

    def set_column_stretch(self, column: int):
        """Set a column to stretch to fill available space."""
        self.horizontalHeader().setSectionResizeMode(
            column, QHeaderView.ResizeMode.Stretch)

    def set_column_resize_to_contents(self, column: int):
        """Set a column to resize based on content."""
        self.horizontalHeader().setSectionResizeMode(
            column, QHeaderView.ResizeMode.ResizeToContents)

    def auto_resize_columns(self):
        """Auto-resize all columns to fit content."""
        self.resizeColumnsToContents()

    # =========================================================================
    # Row Selection
    # =========================================================================

    def select_row(self, row: int, extend: bool = False):
        """Select a specific row."""
        if not self.model() or row < 0 or row >= self._total_rows:
            return

        if not extend:
            self._selected_rows.clear()

        self._selected_rows.add(row)
        self._anchor_row = row

        # Update visual selection
        selection_model = self.selectionModel()
        if selection_model:
            index = self.model().index(row, 0)
            if extend:
                selection_model.select(
                    index,
                    QItemSelectionModel.SelectionFlag.Select |
                    QItemSelectionModel.SelectionFlag.Rows)
            else:
                selection_model.select(
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect |
                    QItemSelectionModel.SelectionFlag.Rows)

        self.selection_changed.emit(list(self._selected_rows))

        # Emit row selected signal
        data = self._get_row_data(row)
        self.row_selected.emit(row, data)

    def select_rows(self, rows: List[int]):
        """Select multiple rows."""
        self._selected_rows.clear()

        selection_model = self.selectionModel()
        if selection_model:
            selection_model.clearSelection()

        for row in rows:
            if 0 <= row < self._total_rows:
                self._selected_rows.add(row)
                if selection_model:
                    index = self.model().index(row, 0)
                    selection_model.select(
                        index,
                        QItemSelectionModel.SelectionFlag.Select |
                        QItemSelectionModel.SelectionFlag.Rows)

        if rows:
            self._anchor_row = rows[-1]

        self.selection_changed.emit(list(self._selected_rows))
        self.rows_selected.emit(list(self._selected_rows))

    def select_range(self, start_row: int, end_row: int):
        """Select a range of rows."""
        if start_row > end_row:
            start_row, end_row = end_row, start_row

        rows = list(range(start_row, end_row + 1))
        self.select_rows(rows)

    def select_all_rows(self):
        """Select all rows."""
        if self.model():
            self.select_rows(list(range(self._total_rows)))

    def clear_selection(self):
        """Clear all selection."""
        self._selected_rows.clear()
        self._anchor_row = -1

        selection_model = self.selectionModel()
        if selection_model:
            selection_model.clearSelection()

        self.selection_changed.emit([])

    def get_selected_rows(self) -> List[int]:
        """Get list of selected row indices."""
        return sorted(self._selected_rows)

    def get_selected_data(self) -> List[Dict[str, Any]]:
        """Get data for all selected rows."""
        return [self._get_row_data(row) for row in sorted(self._selected_rows)]

    def _get_row_data(self, row: int) -> Dict[str, Any]:
        """Get data dictionary for a row."""
        if not self.model() or row < 0 or row >= self._total_rows:
            return {}

        model = self.model()
        data = {}

        for col in range(model.columnCount()):
            index = model.index(row, col)
            # Try to get header name for key
            header = model.headerData(col, Qt.Orientation.Horizontal,
                                       Qt.ItemDataRole.DisplayRole)
            key = str(header) if header else f"col_{col}"

            # Get display value and user data
            data[key] = index.data(Qt.ItemDataRole.DisplayRole)
            user_data = index.data(Qt.ItemDataRole.UserRole)
            if user_data is not None:
                data[f"{key}_data"] = user_data

        return data

    # =========================================================================
    # Keyboard Navigation
    # =========================================================================

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation."""
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Up:
            self._navigate_up(modifiers)
            event.accept()
        elif key == Qt.Key.Key_Down:
            self._navigate_down(modifiers)
            event.accept()
        elif key == Qt.Key.Key_Home:
            self._navigate_home(modifiers)
            event.accept()
        elif key == Qt.Key.Key_End:
            self._navigate_end(modifiers)
            event.accept()
        elif key == Qt.Key.Key_PageUp:
            self._navigate_page_up(modifiers)
            event.accept()
        elif key == Qt.Key.Key_PageDown:
            self._navigate_page_down(modifiers)
            event.accept()
        elif key == Qt.Key.Key_Space:
            self._toggle_current_selection()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _navigate_up(self, modifiers):
        """Navigate up one row."""
        current = self._anchor_row if self._anchor_row >= 0 else 0
        new_row = max(0, current - 1)

        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self.select_range(self._anchor_row, new_row)
        else:
            self.select_row(new_row)

        self.scrollTo(self.model().index(new_row, 0))

    def _navigate_down(self, modifiers):
        """Navigate down one row."""
        current = self._anchor_row if self._anchor_row >= 0 else -1
        new_row = min(self._total_rows - 1, current + 1)

        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Extend selection
            if self._anchor_row < 0:
                self._anchor_row = 0
            self.select_range(self._anchor_row, new_row)
        else:
            self.select_row(new_row)

        self.scrollTo(self.model().index(new_row, 0))

    def _navigate_home(self, modifiers):
        """Navigate to first row."""
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self.select_range(self._anchor_row, 0)
        else:
            self.select_row(0)
        self.scrollToTop()

    def _navigate_end(self, modifiers):
        """Navigate to last row."""
        last_row = self._total_rows - 1
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self.select_range(self._anchor_row, last_row)
        else:
            self.select_row(last_row)
        self.scrollToBottom()

    def _navigate_page_up(self, modifiers):
        """Navigate up one page."""
        visible_rows = (self._visible_end - self._visible_start)
        new_row = max(0, self._anchor_row - visible_rows)

        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self.select_range(self._anchor_row, new_row)
        else:
            self.select_row(new_row)

        self.scrollTo(self.model().index(new_row, 0))

    def _navigate_page_down(self, modifiers):
        """Navigate down one page."""
        visible_rows = (self._visible_end - self._visible_start)
        new_row = min(self._total_rows - 1, self._anchor_row + visible_rows)

        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self.select_range(self._anchor_row, new_row)
        else:
            self.select_row(new_row)

        self.scrollTo(self.model().index(new_row, 0))

    def _toggle_current_selection(self):
        """Toggle selection of current row."""
        if self._anchor_row >= 0:
            if self._anchor_row in self._selected_rows:
                self._selected_rows.discard(self._anchor_row)
            else:
                self._selected_rows.add(self._anchor_row)
            self.selection_changed.emit(list(self._selected_rows))

    def _on_delete_pressed(self):
        """Handle delete key press."""
        selected = self.get_selected_rows()
        if selected:
            for row in selected:
                data = self._get_row_data(row)
                self.delete_requested.emit(row, data)

    def _on_enter_pressed(self):
        """Handle enter key press."""
        if self._anchor_row >= 0:
            data = self._get_row_data(self._anchor_row)
            self.edit_requested.emit(self._anchor_row, data)

    # =========================================================================
    # Context Menu
    # =========================================================================

    def _on_context_menu(self, pos: QPoint):
        """Handle context menu request."""
        index = self.indexAt(pos)
        if index.isValid():
            row = index.row()
            data = self._get_row_data(row)

            # Select the row if not already selected
            if row not in self._selected_rows:
                self.select_row(row)

            self.context_menu_requested.emit(row, data, self.mapToGlobal(pos))

    def _on_double_click(self, index: QModelIndex):
        """Handle double click."""
        if index.isValid():
            row = index.row()
            data = self._get_row_data(row)
            self.row_double_clicked.emit(row, data)
            self.edit_requested.emit(row, data)

    # =========================================================================
    # Sorting
    # =========================================================================

    def set_sortable_column(self, column: int, sortable: bool = True):
        """Set whether a column is sortable."""
        if sortable:
            self._sortable_columns.add(column)
        else:
            self._sortable_columns.discard(column)

    def sort_by_column(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort by a specific column."""
        if column in self._sortable_columns:
            self.sortByColumn(column, order)
            self._current_sort = [(column, order)]

    def add_sort_column(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Add a column to multi-column sort."""
        if column in self._sortable_columns:
            # Remove existing sort for this column
            self._current_sort = [(c, o) for c, o in self._current_sort if c != column]
            self._current_sort.append((column, order))
            # Multi-column sort is handled by the model

    def clear_sort(self):
        """Clear all sorting."""
        self._current_sort.clear()
        self.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

    def get_sort_state(self) -> List[Tuple[int, Qt.SortOrder]]:
        """Get current sort state."""
        return self._current_sort.copy()


# =============================================================================
# Custom Delegates
# =============================================================================

class CurrencyDelegate(QStyledItemDelegate):
    """Delegate for displaying currency values with formatting and colors."""

    def __init__(self,
                 currency_symbol: str = "$",
                 positive_color: str = "#81C784",
                 negative_color: str = "#E57373",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.currency_symbol = currency_symbol
        self.positive_color = QColor(positive_color)
        self.negative_color = QColor(negative_color)

    def displayText(self, value: Any, locale) -> str:
        """Format the value as currency."""
        try:
            if value is None:
                return f"{self.currency_symbol}0.00"
            num_value = float(value)
            return f"{self.currency_symbol}{abs(num_value):,.2f}"
        except (ValueError, TypeError):
            return str(value)

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Initialize style options including color based on value."""
        super().initStyleOption(option, index)

        value = index.data(Qt.ItemDataRole.UserRole)
        try:
            if value is not None:
                num_value = float(value)
                if num_value >= 0:
                    option.palette.setColor(QPalette.ColorRole.Text, self.positive_color)
                else:
                    option.palette.setColor(QPalette.ColorRole.Text, self.negative_color)
        except (ValueError, TypeError):
            pass


class DateDelegate(QStyledItemDelegate):
    """Delegate for displaying formatted dates."""

    def __init__(self,
                 date_format: str = "%Y-%m-%d",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.date_format = date_format

    def displayText(self, value: Any, locale) -> str:
        """Format the value as a date."""
        try:
            if isinstance(value, (datetime, date)):
                return value.strftime(self.date_format)
            elif isinstance(value, str):
                # Try to parse common date formats
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime(self.date_format)
                    except ValueError:
                        continue
                return value
            return str(value) if value else ""
        except Exception:
            return str(value) if value else ""


class ProgressDelegate(QStyledItemDelegate):
    """Delegate for displaying progress bars with percentage."""

    def __init__(self,
                 bar_height: int = 16,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.bar_height = bar_height
        # Color thresholds: (percentage, color)
        self.colors = [
            (50, QColor("#4CAF50")),   # Green - under 50%
            (75, QColor("#FFC107")),   # Yellow - 50-75%
            (100, QColor("#FF9800")),  # Orange - 75-100%
            (float('inf'), QColor("#F44336"))  # Red - over 100%
        ]

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint the progress bar."""
        painter.save()

        value = index.data(Qt.ItemDataRole.UserRole)
        try:
            progress = float(value) if value is not None else 0
        except (ValueError, TypeError):
            progress = 0

        # Get the appropriate color
        color = self.colors[-1][1]
        for threshold, col in self.colors:
            if progress < threshold:
                color = col
                break

        # Calculate dimensions
        rect = option.rect
        padding = 4
        bar_rect = QRect(
            rect.left() + padding,
            rect.top() + (rect.height() - self.bar_height) // 2,
            rect.width() - 2 * padding,
            self.bar_height
        )

        # Draw background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E0E0E0"))
        painter.drawRoundedRect(bar_rect, 3, 3)

        # Draw progress fill
        if progress > 0:
            fill_width = int(bar_rect.width() * min(progress / 100, 1.0))
            fill_rect = QRect(bar_rect.left(), bar_rect.top(), fill_width, bar_rect.height())
            painter.setBrush(color)
            painter.drawRoundedRect(fill_rect, 3, 3)

        # Draw text
        painter.setPen(QColor("#333333"))
        text = f"{progress:.1f}%"
        painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return the preferred size for the progress bar."""
        return QSize(100, self.bar_height + 8)


class ColoredTextDelegate(QStyledItemDelegate):
    """Delegate for displaying text with conditional coloring."""

    def __init__(self,
                 color_map: Optional[Dict[str, str]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Default color map for transaction types
        self.color_map = color_map or {
            'income': '#81C784',
            'expense': '#E57373',
            'transfer': '#64B5F6'
        }

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Initialize style options including color based on value."""
        super().initStyleOption(option, index)

        value = index.data(Qt.ItemDataRole.DisplayRole)
        if value:
            value_lower = str(value).lower()
            if value_lower in self.color_map:
                option.palette.setColor(
                    QPalette.ColorRole.Text,
                    QColor(self.color_map[value_lower])
                )


class CategoryColorDelegate(QStyledItemDelegate):
    """Delegate for displaying category with color indicator."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint category with color dot."""
        painter.save()

        # Get color from user data (expects dict with 'color' key)
        data = index.data(Qt.ItemDataRole.UserRole)
        color = QColor("#888888")
        if isinstance(data, dict) and 'color' in data:
            color = QColor(data['color'])
        elif isinstance(data, str) and data.startswith('#'):
            color = QColor(data)

        # Draw selection background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Draw color dot
        dot_size = 10
        dot_x = option.rect.left() + 8
        dot_y = option.rect.top() + (option.rect.height() - dot_size) // 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

        # Draw text
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_rect = QRect(
            dot_x + dot_size + 8,
            option.rect.top(),
            option.rect.width() - dot_size - 24,
            option.rect.height()
        )

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

        painter.restore()


# =============================================================================
# Empty State Widget
# =============================================================================

class EmptyStateWidget(QFrame):
    """Widget displaying an empty state message."""

    action_clicked = pyqtSignal()

    def __init__(self,
                 message: str = "No data available",
                 icon: str = "",
                 action_text: str = "",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("emptyStateWidget")
        self._setup_ui(message, icon, action_text)

    def _setup_ui(self, message: str, icon: str, action_text: str):
        """Set up the empty state UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon (if provided)
        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI", 48))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("color: #9E9E9E;")
            layout.addWidget(icon_label)

        # Message
        message_label = QLabel(message)
        message_label.setFont(QFont("Segoe UI", 14))
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("color: #757575;")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # Action button (if provided)
        if action_text:
            action_btn = QPushButton(action_text)
            action_btn.setObjectName("primaryButton")
            action_btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(action_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_message(self, message: str):
        """Update the empty state message."""
        for child in self.children():
            if isinstance(child, QLabel):
                child.setText(message)
                break


# =============================================================================
# Pagination Widget
# =============================================================================

class TablePagination(QWidget):
    """Pagination controls for tables."""

    page_changed = pyqtSignal(int)
    page_size_changed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("tablePagination")
        self._current_page = 1
        self._total_pages = 1
        self._total_items = 0
        self._page_size = 25
        self._setup_ui()

    def _setup_ui(self):
        """Set up the pagination UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Items info
        self.info_label = QLabel("Showing 0 items")
        self.info_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.info_label)

        layout.addStretch()

        # Page size selector
        page_size_label = QLabel("Items per page:")
        page_size_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(page_size_label)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "25", "50", "100"])
        self.page_size_combo.setCurrentText("25")
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        layout.addWidget(self.page_size_combo)

        layout.addSpacing(20)

        # Navigation buttons
        self.first_btn = QPushButton("<<")
        self.first_btn.setObjectName("paginationButton")
        self.first_btn.setMaximumWidth(40)
        self.first_btn.setToolTip("First page")
        self.first_btn.clicked.connect(lambda: self.go_to_page(1))
        layout.addWidget(self.first_btn)

        self.prev_btn = QPushButton("<")
        self.prev_btn.setObjectName("paginationButton")
        self.prev_btn.setMaximumWidth(40)
        self.prev_btn.setToolTip("Previous page")
        self.prev_btn.clicked.connect(lambda: self.go_to_page(self._current_page - 1))
        layout.addWidget(self.prev_btn)

        # Page indicator
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setFont(QFont("Segoe UI", 10))
        self.page_label.setMinimumWidth(100)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)

        self.next_btn = QPushButton(">")
        self.next_btn.setObjectName("paginationButton")
        self.next_btn.setMaximumWidth(40)
        self.next_btn.setToolTip("Next page")
        self.next_btn.clicked.connect(lambda: self.go_to_page(self._current_page + 1))
        layout.addWidget(self.next_btn)

        self.last_btn = QPushButton(">>")
        self.last_btn.setObjectName("paginationButton")
        self.last_btn.setMaximumWidth(40)
        self.last_btn.setToolTip("Last page")
        self.last_btn.clicked.connect(lambda: self.go_to_page(self._total_pages))
        layout.addWidget(self.last_btn)

    def _on_page_size_changed(self, size_str: str):
        """Handle page size change."""
        self._page_size = int(size_str)
        self.page_size_changed.emit(self._page_size)

    def go_to_page(self, page: int):
        """Navigate to a specific page."""
        page = max(1, min(page, self._total_pages))
        if page != self._current_page:
            self._current_page = page
            self._update_ui()
            self.page_changed.emit(page)

    def set_total_items(self, total: int):
        """Set the total number of items."""
        self._total_items = total
        self._total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        self._current_page = min(self._current_page, self._total_pages)
        self._update_ui()

    def reset(self):
        """Reset pagination to first page."""
        self._current_page = 1
        self._update_ui()

    def _update_ui(self):
        """Update the pagination display."""
        start = (self._current_page - 1) * self._page_size + 1
        end = min(self._current_page * self._page_size, self._total_items)

        if self._total_items > 0:
            self.info_label.setText(f"Showing {start}-{end} of {self._total_items} items")
        else:
            self.info_label.setText("No items")

        self.page_label.setText(f"Page {self._current_page} of {self._total_pages}")

        # Enable/disable buttons
        self.first_btn.setEnabled(self._current_page > 1)
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)
        self.last_btn.setEnabled(self._current_page < self._total_pages)

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def page_size(self) -> int:
        return self._page_size


# =============================================================================
# Base Table Widget
# =============================================================================

class SortableTableWidget(QTableWidget):
    """Table widget with built-in sorting capabilities."""

    row_selected = pyqtSignal(int, dict)  # row index, row data
    row_double_clicked = pyqtSignal(int, dict)
    context_menu_requested = pyqtSignal(int, dict)  # row index, row data
    edit_requested = pyqtSignal(int, dict)
    delete_requested = pyqtSignal(int, dict)
    duplicate_requested = pyqtSignal(int, dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("sortableTable")
        self._column_formatters: Dict[int, Callable] = {}
        self._row_data: List[Dict[str, Any]] = []
        self._columns: List[Dict[str, Any]] = []
        self._enable_context_menu = True
        self._setup_table()

    def _setup_table(self):
        """Set up the table configuration."""
        # Selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Appearance
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        # Sorting
        self.setSortingEnabled(True)

        # Connect signals
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_double_click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def setup_columns(self, columns: List[Dict[str, Any]]):
        """
        Set up table columns.

        Each column dict should have:
        - 'key': Data key
        - 'header': Column header text
        - 'width': Optional width
        - 'resize_mode': Optional resize mode ('stretch', 'contents', 'fixed')
        - 'alignment': Optional alignment
        - 'formatter': Optional formatting function
        - 'delegate': Optional custom delegate instance
        - 'color_func': Optional function returning color based on value and row
        """
        self.setColumnCount(len(columns))
        headers = []

        for i, col in enumerate(columns):
            headers.append(col.get('header', col.get('key', '')))

            # Set width
            if 'width' in col:
                self.setColumnWidth(i, col['width'])

            # Set resize mode
            resize_mode = col.get('resize_mode', 'stretch' if i == len(columns) - 1 else 'contents')
            if resize_mode == 'stretch':
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            elif resize_mode == 'contents':
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            elif resize_mode == 'fixed':
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)

            # Store formatter
            if 'formatter' in col:
                self._column_formatters[i] = col['formatter']

            # Set delegate if provided
            if 'delegate' in col:
                self.setItemDelegateForColumn(i, col['delegate'])

        self.setHorizontalHeaderLabels(headers)
        self._columns = columns

    def load_data(self, data: List[Dict[str, Any]]):
        """Load data into the table."""
        self._row_data = data
        self.setSortingEnabled(False)
        self.setRowCount(0)

        for row_idx, row_data in enumerate(data):
            self.insertRow(row_idx)

            for col_idx, col in enumerate(self._columns):
                key = col.get('key', '')
                value = row_data.get(key, '')

                # Apply formatter if exists
                if col_idx in self._column_formatters:
                    display_value = self._column_formatters[col_idx](value)
                else:
                    display_value = str(value) if value is not None else ''

                item = QTableWidgetItem(display_value)

                # Store original value for sorting and delegate access
                item.setData(Qt.ItemDataRole.UserRole, value)

                # Apply alignment
                alignment = col.get('alignment', Qt.AlignmentFlag.AlignLeft)
                item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)

                # Apply color if specified
                if 'color_func' in col:
                    color = col['color_func'](value, row_data)
                    if color:
                        item.setForeground(QColor(color))

                self.setItem(row_idx, col_idx, item)

        self.setSortingEnabled(True)

    def set_context_menu_enabled(self, enabled: bool):
        """Enable or disable the context menu."""
        self._enable_context_menu = enabled

    def _on_selection_changed(self):
        """Handle row selection changes."""
        selected = self.selectedItems()
        if selected:
            row = selected[0].row()
            if row < len(self._row_data):
                self.row_selected.emit(row, self._row_data[row])

    def _on_double_click(self, item: QTableWidgetItem):
        """Handle double click on row."""
        row = item.row()
        if row < len(self._row_data):
            self.row_double_clicked.emit(row, self._row_data[row])

    def _on_context_menu(self, pos):
        """Handle context menu request."""
        if not self._enable_context_menu:
            return

        item = self.itemAt(pos)
        if item:
            row = item.row()
            if row < len(self._row_data):
                row_data = self._row_data[row]

                # Create context menu
                menu = QMenu(self)

                # Edit action
                edit_action = QAction("Edit", self)
                edit_action.triggered.connect(lambda: self.edit_requested.emit(row, row_data))
                menu.addAction(edit_action)

                # Duplicate action
                duplicate_action = QAction("Duplicate", self)
                duplicate_action.triggered.connect(lambda: self.duplicate_requested.emit(row, row_data))
                menu.addAction(duplicate_action)

                menu.addSeparator()

                # Delete action
                delete_action = QAction("Delete", self)
                delete_action.triggered.connect(lambda: self.delete_requested.emit(row, row_data))
                menu.addAction(delete_action)

                # Emit signal for custom handling
                self.context_menu_requested.emit(row, row_data)

                # Show menu
                menu.exec(self.mapToGlobal(pos))

    def get_selected_data(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected row data."""
        selected = self.selectedItems()
        if selected:
            row = selected[0].row()
            if row < len(self._row_data):
                return self._row_data[row]
        return None

    def get_selected_row(self) -> int:
        """Get the currently selected row index."""
        selected = self.selectedItems()
        if selected:
            return selected[0].row()
        return -1

    def refresh_row(self, row_idx: int, row_data: Dict[str, Any]):
        """Refresh a single row with new data."""
        if 0 <= row_idx < self.rowCount():
            self._row_data[row_idx] = row_data

            for col_idx, col in enumerate(self._columns):
                key = col.get('key', '')
                value = row_data.get(key, '')

                if col_idx in self._column_formatters:
                    display_value = self._column_formatters[col_idx](value)
                else:
                    display_value = str(value) if value is not None else ''

                item = self.item(row_idx, col_idx)
                if item:
                    item.setText(display_value)
                    item.setData(Qt.ItemDataRole.UserRole, value)

                    if 'color_func' in col:
                        color = col['color_func'](value, row_data)
                        if color:
                            item.setForeground(QColor(color))


# =============================================================================
# Data Table Widget with Search and Pagination
# =============================================================================

class DataTableWidget(QFrame):
    """Complete data table widget with search, pagination, and actions."""

    row_selected = pyqtSignal(dict)
    action_requested = pyqtSignal(str, dict)  # action name, row data
    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    duplicate_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("dataTableWidget")
        self._all_data: List[Dict[str, Any]] = []
        self._filtered_data: List[Dict[str, Any]] = []
        self._columns: List[Dict[str, Any]] = []
        self._empty_message = "No data available"
        self._empty_icon = ""
        self._empty_action_text = ""
        self._setup_ui()

    def _setup_ui(self):
        """Set up the data table UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self.toolbar = QHBoxLayout()
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setSpacing(10)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setObjectName("tableSearchInput")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self._on_search)
        self.toolbar.addWidget(self.search_input)

        self.toolbar.addStretch()

        # Action buttons placeholder
        self.action_buttons_layout = QHBoxLayout()
        self.toolbar.addLayout(self.action_buttons_layout)

        layout.addLayout(self.toolbar)

        # Table container (holds both table and empty state)
        self.table_container = QFrame()
        self.table_container_layout = QVBoxLayout(self.table_container)
        self.table_container_layout.setContentsMargins(0, 0, 0, 0)
        self.table_container_layout.setSpacing(0)

        # Table
        self.table = SortableTableWidget()
        self.table.row_selected.connect(lambda idx, data: self.row_selected.emit(data))
        self.table.row_double_clicked.connect(lambda idx, data: self.edit_requested.emit(data))
        self.table.edit_requested.connect(lambda idx, data: self.edit_requested.emit(data))
        self.table.delete_requested.connect(lambda idx, data: self.delete_requested.emit(data))
        self.table.duplicate_requested.connect(lambda idx, data: self.duplicate_requested.emit(data))
        self.table_container_layout.addWidget(self.table)

        # Empty state widget (hidden by default)
        self.empty_state = EmptyStateWidget(
            message=self._empty_message,
            icon=self._empty_icon,
            action_text=self._empty_action_text
        )
        self.empty_state.action_clicked.connect(lambda: self.action_requested.emit("add", {}))
        self.empty_state.hide()
        self.table_container_layout.addWidget(self.empty_state)

        layout.addWidget(self.table_container)

        # Pagination
        self.pagination = TablePagination()
        self.pagination.page_changed.connect(self._on_page_changed)
        self.pagination.page_size_changed.connect(self._on_page_size_changed)
        layout.addWidget(self.pagination)

    def set_empty_state(self, message: str, icon: str = "", action_text: str = ""):
        """Configure the empty state display."""
        self._empty_message = message
        self._empty_icon = icon
        self._empty_action_text = action_text

        # Recreate empty state widget
        self.empty_state.deleteLater()
        self.empty_state = EmptyStateWidget(
            message=message,
            icon=icon,
            action_text=action_text
        )
        self.empty_state.action_clicked.connect(lambda: self.action_requested.emit("add", {}))
        self.empty_state.hide()
        self.table_container_layout.addWidget(self.empty_state)

    def setup_columns(self, columns: List[Dict[str, Any]]):
        """Set up table columns."""
        self.table.setup_columns(columns)
        self._columns = columns

    def add_action_button(self, text: str, action_name: str, primary: bool = False):
        """Add an action button to the toolbar."""
        btn = QPushButton(text)
        btn.setObjectName("primaryButton" if primary else "secondaryButton")
        btn.clicked.connect(lambda: self._on_action(action_name))
        self.action_buttons_layout.addWidget(btn)
        return btn

    def _on_action(self, action_name: str):
        """Handle action button click."""
        selected = self.table.get_selected_data()
        self.action_requested.emit(action_name, selected or {})

    def load_data(self, data: List[Dict[str, Any]]):
        """Load data into the table."""
        self._all_data = data
        self._filtered_data = data
        self._update_empty_state()
        self._apply_pagination()

    def _update_empty_state(self):
        """Show or hide empty state based on data."""
        if len(self._filtered_data) == 0:
            self.table.hide()
            self.empty_state.show()
            self.pagination.hide()
        else:
            self.table.show()
            self.empty_state.hide()
            self.pagination.show()

    def _on_search(self, text: str):
        """Handle search text change."""
        if not text:
            self._filtered_data = self._all_data
        else:
            text_lower = text.lower()
            self._filtered_data = [
                row for row in self._all_data
                if any(
                    text_lower in str(row.get(col.get('key', ''), '')).lower()
                    for col in self._columns
                )
            ]

        self._update_empty_state()
        self.pagination.reset()
        self.pagination.set_total_items(len(self._filtered_data))
        self._apply_pagination()

    def _on_page_changed(self, page: int):
        """Handle page change."""
        self._apply_pagination()

    def _on_page_size_changed(self, size: int):
        """Handle page size change."""
        self.pagination.set_total_items(len(self._filtered_data))
        self._apply_pagination()

    def _apply_pagination(self):
        """Apply pagination to the filtered data."""
        page = self.pagination.current_page
        size = self.pagination.page_size

        start = (page - 1) * size
        end = start + size

        page_data = self._filtered_data[start:end]
        self.table.load_data(page_data)
        self.pagination.set_total_items(len(self._filtered_data))

    def refresh(self):
        """Refresh the table with current data."""
        self._apply_pagination()

    def clear(self):
        """Clear all data from the table."""
        self._all_data = []
        self._filtered_data = []
        self.table.setRowCount(0)
        self._update_empty_state()


# =============================================================================
# Specialized Table Widgets
# =============================================================================

class TransactionTableWidget(DataTableWidget):
    """Specialized table widget for transactions."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("transactionTableWidget")
        self._setup_transaction_columns()
        self._setup_transaction_actions()
        self.set_empty_state(
            message="No transactions yet",
            icon="",
            action_text="Add Transaction"
        )

    def _setup_transaction_columns(self):
        """Set up transaction-specific columns."""
        columns = [
            {
                'key': 'date',
                'header': 'Date',
                'width': 100,
                'formatter': lambda v: v.strftime('%Y-%m-%d') if isinstance(v, (datetime, date)) else str(v),
                'delegate': DateDelegate(parent=self)
            },
            {
                'key': 'description',
                'header': 'Description',
                'resize_mode': 'stretch'
            },
            {
                'key': 'category',
                'header': 'Category',
                'width': 120
            },
            {
                'key': 'type',
                'header': 'Type',
                'width': 80,
                'formatter': lambda v: v.capitalize() if v else '',
                'color_func': lambda v, row: '#81C784' if v == 'income' else '#E57373',
                'delegate': ColoredTextDelegate(parent=self)
            },
            {
                'key': 'amount',
                'header': 'Amount',
                'width': 100,
                'alignment': Qt.AlignmentFlag.AlignRight,
                'formatter': lambda v: f"${float(v):,.2f}" if v else '$0.00',
                'color_func': lambda v, row: '#81C784' if row.get('type') == 'income' else '#E57373'
            }
        ]
        self.setup_columns(columns)

    def _setup_transaction_actions(self):
        """Set up transaction action buttons."""
        self.add_action_button("+ Add Transaction", "add", primary=True)


class BudgetTableWidget(DataTableWidget):
    """Specialized table widget for budgets."""

    view_transactions_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetTableWidget")
        self._setup_budget_columns()
        self._setup_budget_actions()
        self.set_empty_state(
            message="No budgets created yet",
            icon="",
            action_text="Create Budget"
        )

    def _setup_budget_columns(self):
        """Set up budget-specific columns."""
        columns = [
            {
                'key': 'name',
                'header': 'Budget Name',
                'resize_mode': 'stretch'
            },
            {
                'key': 'category',
                'header': 'Category',
                'width': 120
            },
            {
                'key': 'period',
                'header': 'Period',
                'width': 80,
                'formatter': lambda v: v.capitalize() if v else ''
            },
            {
                'key': 'spent',
                'header': 'Spent',
                'width': 100,
                'alignment': Qt.AlignmentFlag.AlignRight,
                'formatter': lambda v: f"${float(v):,.2f}" if v else '$0.00'
            },
            {
                'key': 'limit',
                'header': 'Limit',
                'width': 100,
                'alignment': Qt.AlignmentFlag.AlignRight,
                'formatter': lambda v: f"${float(v):,.2f}" if v else '$0.00'
            },
            {
                'key': 'progress',
                'header': 'Progress',
                'width': 120,
                'resize_mode': 'fixed',
                'delegate': ProgressDelegate(parent=self)
            }
        ]
        self.setup_columns(columns)

    def _get_progress_color(self, value, row) -> str:
        """Get color based on budget progress."""
        try:
            progress = float(value) if value else 0
            if progress < 50:
                return '#4CAF50'  # Green
            elif progress < 75:
                return '#FFC107'  # Yellow
            elif progress < 100:
                return '#FF9800'  # Orange
            else:
                return '#F44336'  # Red
        except (ValueError, TypeError):
            return '#888888'

    def _setup_budget_actions(self):
        """Set up budget action buttons."""
        self.add_action_button("+ Create Budget", "add", primary=True)


class CategoryTableWidget(DataTableWidget):
    """Specialized table widget for categories."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("categoryTableWidget")
        self._setup_category_columns()
        self._setup_category_actions()
        self.set_empty_state(
            message="No categories created yet",
            icon="",
            action_text="Add Category"
        )

    def _setup_category_columns(self):
        """Set up category-specific columns."""
        columns = [
            {
                'key': 'name',
                'header': 'Category Name',
                'resize_mode': 'stretch',
                'delegate': CategoryColorDelegate(parent=self)
            },
            {
                'key': 'type',
                'header': 'Type',
                'width': 100,
                'formatter': lambda v: v.capitalize() if v else '',
                'color_func': lambda v, row: '#81C784' if v == 'income' else '#E57373'
            },
            {
                'key': 'parent',
                'header': 'Parent Category',
                'width': 150,
                'formatter': lambda v: v if v else '-'
            },
            {
                'key': 'transaction_count',
                'header': 'Transactions',
                'width': 100,
                'alignment': Qt.AlignmentFlag.AlignRight,
                'formatter': lambda v: str(v) if v is not None else '0'
            },
            {
                'key': 'total_amount',
                'header': 'Total Amount',
                'width': 120,
                'alignment': Qt.AlignmentFlag.AlignRight,
                'formatter': lambda v: f"${float(v):,.2f}" if v else '$0.00'
            }
        ]
        self.setup_columns(columns)

    def _setup_category_actions(self):
        """Set up category action buttons."""
        self.add_action_button("+ Add Category", "add", primary=True)


class AccountTableWidget(DataTableWidget):
    """Specialized table widget for accounts."""

    view_transactions_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("accountTableWidget")
        self._setup_account_columns()
        self._setup_account_actions()
        self.set_empty_state(
            message="No accounts added yet",
            icon="",
            action_text="Add Account"
        )

    def _setup_account_columns(self):
        """Set up account-specific columns."""
        columns = [
            {
                'key': 'name',
                'header': 'Account Name',
                'resize_mode': 'stretch'
            },
            {
                'key': 'type',
                'header': 'Type',
                'width': 100,
                'formatter': lambda v: v.replace('_', ' ').title() if v else ''
            },
            {
                'key': 'institution',
                'header': 'Institution',
                'width': 150,
                'formatter': lambda v: v if v else '-'
            },
            {
                'key': 'balance',
                'header': 'Balance',
                'width': 120,
                'alignment': Qt.AlignmentFlag.AlignRight,
                'formatter': lambda v: f"${float(v):,.2f}" if v else '$0.00',
                'color_func': lambda v, row: '#81C784' if v and float(v) >= 0 else '#E57373'
            },
            {
                'key': 'last_updated',
                'header': 'Last Updated',
                'width': 120,
                'formatter': lambda v: v.strftime('%Y-%m-%d') if isinstance(v, (datetime, date)) else str(v) if v else '-'
            }
        ]
        self.setup_columns(columns)

    def _setup_account_actions(self):
        """Set up account action buttons."""
        self.add_action_button("+ Add Account", "add", primary=True)
