"""
Table Models Module

QAbstractTableModel implementations for transactions, budgets, and categories
with pagination support, multi-column sorting, and efficient data handling.
"""

from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel,
    pyqtSignal, QVariant, QDateTime, QDate
)
from PyQt6.QtGui import QColor, QFont, QIcon
from typing import Optional, List, Dict, Any, Callable, Tuple, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field


# =============================================================================
# Column Definition
# =============================================================================

class ColumnType(Enum):
    """Column data types for proper formatting and sorting."""
    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    DATETIME = "datetime"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    PROGRESS = "progress"
    ACTION = "action"


@dataclass
class ColumnDefinition:
    """Definition of a table column."""
    key: str
    header: str
    column_type: ColumnType = ColumnType.TEXT
    width: int = 100
    min_width: int = 50
    max_width: int = 500
    resizable: bool = True
    sortable: bool = True
    editable: bool = False
    visible: bool = True
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft
    formatter: Optional[Callable[[Any], str]] = None
    color_func: Optional[Callable[[Any, Dict], Optional[str]]] = None
    icon_func: Optional[Callable[[Any, Dict], Optional[QIcon]]] = None
    tooltip_func: Optional[Callable[[Any, Dict], Optional[str]]] = None


# =============================================================================
# Base Table Model
# =============================================================================

class BaseTableModel(QAbstractTableModel):
    """
    Base table model with pagination, sorting, and filtering support.

    Features:
    - Efficient data storage and retrieval
    - Multi-column sorting
    - Pagination support
    - Column visibility toggle
    - Custom formatters and colors
    """

    # Signals
    data_updated = pyqtSignal()
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Data storage
        self._data: List[Dict[str, Any]] = []
        self._filtered_data: List[Dict[str, Any]] = []
        self._display_data: List[Dict[str, Any]] = []

        # Column definitions
        self._columns: List[ColumnDefinition] = []
        self._visible_columns: List[int] = []

        # Pagination
        self._page = 1
        self._page_size = 25
        self._total_count = 0

        # Sorting
        self._sort_columns: List[Tuple[int, Qt.SortOrder]] = []

        # Filtering
        self._filters: Dict[str, Any] = {}
        self._search_text: str = ""
        self._search_columns: List[str] = []

        # Loading state
        self._is_loading = False

    # =========================================================================
    # QAbstractTableModel Implementation
    # =========================================================================

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows."""
        if parent.isValid():
            return 0
        return len(self._display_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of visible columns."""
        if parent.isValid():
            return 0
        return len(self._visible_columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col_idx = self._visible_columns[index.column()]

        if row < 0 or row >= len(self._display_data):
            return None

        column = self._columns[col_idx]
        row_data = self._display_data[row]
        value = row_data.get(column.key)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._format_display_value(value, column, row_data)

        elif role == Qt.ItemDataRole.UserRole:
            return value

        elif role == Qt.ItemDataRole.UserRole + 1:
            # Full row data
            return row_data

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return column.alignment | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ForegroundRole:
            if column.color_func:
                color = column.color_func(value, row_data)
                if color:
                    return QColor(color)
            return None

        elif role == Qt.ItemDataRole.DecorationRole:
            if column.icon_func:
                return column.icon_func(value, row_data)
            return None

        elif role == Qt.ItemDataRole.ToolTipRole:
            if column.tooltip_func:
                return column.tooltip_func(value, row_data)
            return None

        elif role == Qt.ItemDataRole.EditRole:
            return value

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Set data for the given index."""
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col_idx = self._visible_columns[index.column()]

        if row < 0 or row >= len(self._display_data):
            return False

        column = self._columns[col_idx]
        if not column.editable:
            return False

        self._display_data[row][column.key] = value
        self.dataChanged.emit(index, index, [role])
        return True

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data."""
        if orientation == Qt.Orientation.Horizontal:
            if section < 0 or section >= len(self._visible_columns):
                return None

            col_idx = self._visible_columns[section]
            column = self._columns[col_idx]

            if role == Qt.ItemDataRole.DisplayRole:
                return column.header

            elif role == Qt.ItemDataRole.TextAlignmentRole:
                return column.alignment | Qt.AlignmentFlag.AlignVCenter

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return item flags."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        col_idx = self._visible_columns[index.column()]
        column = self._columns[col_idx]

        if column.editable:
            flags |= Qt.ItemFlag.ItemIsEditable

        return flags

    # =========================================================================
    # Data Formatting
    # =========================================================================

    def _format_display_value(self, value: Any, column: ColumnDefinition,
                               row_data: Dict[str, Any]) -> str:
        """Format a value for display."""
        if value is None:
            return ""

        # Use custom formatter if provided
        if column.formatter:
            return column.formatter(value)

        # Format based on column type
        if column.column_type == ColumnType.CURRENCY:
            try:
                num_val = float(value)
                return f"${num_val:,.2f}"
            except (ValueError, TypeError):
                return str(value)

        elif column.column_type == ColumnType.NUMBER:
            try:
                num_val = float(value)
                if num_val == int(num_val):
                    return str(int(num_val))
                return f"{num_val:,.2f}"
            except (ValueError, TypeError):
                return str(value)

        elif column.column_type == ColumnType.PERCENTAGE:
            try:
                num_val = float(value)
                return f"{num_val:.1f}%"
            except (ValueError, TypeError):
                return str(value)

        elif column.column_type == ColumnType.DATE:
            if isinstance(value, (datetime, date)):
                return value.strftime("%Y-%m-%d")
            return str(value)

        elif column.column_type == ColumnType.DATETIME:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M")
            return str(value)

        elif column.column_type == ColumnType.BOOLEAN:
            return "Yes" if value else "No"

        return str(value)

    # =========================================================================
    # Column Management
    # =========================================================================

    def set_columns(self, columns: List[ColumnDefinition]):
        """Set column definitions."""
        self.beginResetModel()
        self._columns = columns
        self._visible_columns = [
            i for i, col in enumerate(columns) if col.visible
        ]
        self.endResetModel()

    def get_columns(self) -> List[ColumnDefinition]:
        """Get all column definitions."""
        return self._columns.copy()

    def set_column_visible(self, column_key: str, visible: bool):
        """Set column visibility."""
        for i, col in enumerate(self._columns):
            if col.key == column_key:
                col.visible = visible
                break

        self.beginResetModel()
        self._visible_columns = [
            i for i, col in enumerate(self._columns) if col.visible
        ]
        self.endResetModel()

    def get_visible_columns(self) -> List[ColumnDefinition]:
        """Get visible column definitions."""
        return [self._columns[i] for i in self._visible_columns]

    def get_column_index(self, key: str) -> int:
        """Get visual column index by key."""
        for i, col_idx in enumerate(self._visible_columns):
            if self._columns[col_idx].key == key:
                return i
        return -1

    # =========================================================================
    # Data Management
    # =========================================================================

    def set_data(self, data: List[Dict[str, Any]]):
        """Set the model data."""
        self.beginResetModel()
        self._data = data
        self._filtered_data = data.copy()
        self._total_count = len(data)
        self._apply_filters()
        self._apply_search()
        self._apply_sort()
        self._apply_pagination()
        self.endResetModel()
        self.data_updated.emit()

    def get_data(self) -> List[Dict[str, Any]]:
        """Get all data."""
        return self._data.copy()

    def get_row_data(self, row: int) -> Optional[Dict[str, Any]]:
        """Get data for a specific row."""
        if 0 <= row < len(self._display_data):
            return self._display_data[row].copy()
        return None

    def add_row(self, row_data: Dict[str, Any]):
        """Add a new row."""
        self._data.append(row_data)
        self._filtered_data.append(row_data)
        self._total_count += 1
        self._refresh_display()

    def update_row(self, row: int, row_data: Dict[str, Any]):
        """Update an existing row."""
        if 0 <= row < len(self._display_data):
            # Find the row in the original data
            old_data = self._display_data[row]
            for i, d in enumerate(self._data):
                if d is old_data:
                    self._data[i] = row_data
                    break

            self._display_data[row] = row_data
            self.dataChanged.emit(
                self.index(row, 0),
                self.index(row, self.columnCount() - 1)
            )

    def remove_row(self, row: int):
        """Remove a row."""
        if 0 <= row < len(self._display_data):
            row_data = self._display_data[row]

            self.beginRemoveRows(QModelIndex(), row, row)
            self._display_data.pop(row)

            # Remove from original data
            for i, d in enumerate(self._data):
                if d is row_data:
                    self._data.pop(i)
                    break

            # Remove from filtered data
            for i, d in enumerate(self._filtered_data):
                if d is row_data:
                    self._filtered_data.pop(i)
                    break

            self._total_count -= 1
            self.endRemoveRows()

    def clear(self):
        """Clear all data."""
        self.beginResetModel()
        self._data.clear()
        self._filtered_data.clear()
        self._display_data.clear()
        self._total_count = 0
        self.endResetModel()

    # =========================================================================
    # Sorting
    # =========================================================================

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort by a single column."""
        if column < 0 or column >= len(self._visible_columns):
            return

        col_idx = self._visible_columns[column]
        col_def = self._columns[col_idx]

        if not col_def.sortable:
            return

        self._sort_columns = [(column, order)]
        self._apply_sort()
        self._apply_pagination()
        self.layoutChanged.emit()

    def multi_sort(self, sort_spec: List[Tuple[int, Qt.SortOrder]]):
        """Sort by multiple columns."""
        self._sort_columns = []

        for column, order in sort_spec:
            if column < 0 or column >= len(self._visible_columns):
                continue

            col_idx = self._visible_columns[column]
            col_def = self._columns[col_idx]

            if col_def.sortable:
                self._sort_columns.append((column, order))

        self._apply_sort()
        self._apply_pagination()
        self.layoutChanged.emit()

    def _apply_sort(self):
        """Apply current sorting to filtered data."""
        if not self._sort_columns:
            return

        def sort_key(row: Dict[str, Any]) -> tuple:
            keys = []
            for column, order in self._sort_columns:
                col_idx = self._visible_columns[column]
                col_def = self._columns[col_idx]
                value = row.get(col_def.key)

                # Handle None values
                if value is None:
                    value = "" if col_def.column_type == ColumnType.TEXT else 0

                # Convert to sortable type
                if col_def.column_type in (ColumnType.CURRENCY, ColumnType.NUMBER,
                                            ColumnType.PERCENTAGE, ColumnType.PROGRESS):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = 0.0

                elif col_def.column_type in (ColumnType.DATE, ColumnType.DATETIME):
                    if isinstance(value, (datetime, date)):
                        value = value.isoformat()
                    elif isinstance(value, str):
                        pass  # Keep as string for comparison
                    else:
                        value = ""

                # Reverse for descending order
                if order == Qt.SortOrder.DescendingOrder:
                    if isinstance(value, (int, float)):
                        value = -value
                    elif isinstance(value, str):
                        # For strings, we'll handle this differently
                        pass

                keys.append(value)

            return tuple(keys)

        # Sort with reverse for descending if string
        reverse = (len(self._sort_columns) == 1 and
                   self._sort_columns[0][1] == Qt.SortOrder.DescendingOrder)

        self._filtered_data.sort(key=sort_key, reverse=False)

    def get_sort_state(self) -> List[Tuple[int, Qt.SortOrder]]:
        """Get current sort state."""
        return self._sort_columns.copy()

    def clear_sort(self):
        """Clear sorting."""
        self._sort_columns.clear()
        self._refresh_display()

    # =========================================================================
    # Filtering
    # =========================================================================

    def set_filter(self, key: str, value: Any):
        """Set a filter for a column."""
        if value is None or value == "":
            self._filters.pop(key, None)
        else:
            self._filters[key] = value
        self._refresh_display()

    def clear_filters(self):
        """Clear all filters."""
        self._filters.clear()
        self._refresh_display()

    def set_search(self, text: str, columns: Optional[List[str]] = None):
        """Set search text and columns."""
        self._search_text = text.lower()
        if columns:
            self._search_columns = columns
        else:
            # Search all text columns by default
            self._search_columns = [
                col.key for col in self._columns
                if col.column_type == ColumnType.TEXT
            ]
        self._refresh_display()

    def _apply_filters(self):
        """Apply current filters to data."""
        if not self._filters:
            self._filtered_data = self._data.copy()
            return

        self._filtered_data = []
        for row in self._data:
            match = True
            for key, value in self._filters.items():
                row_value = row.get(key)
                if isinstance(value, (list, tuple)):
                    if row_value not in value:
                        match = False
                        break
                elif row_value != value:
                    match = False
                    break

            if match:
                self._filtered_data.append(row)

    def _apply_search(self):
        """Apply search text to filtered data."""
        if not self._search_text:
            return

        search_results = []
        for row in self._filtered_data:
            for col_key in self._search_columns:
                value = row.get(col_key, "")
                if self._search_text in str(value).lower():
                    search_results.append(row)
                    break

        self._filtered_data = search_results

    def _refresh_display(self):
        """Refresh displayed data after filter/search/sort changes."""
        self.beginResetModel()
        self._apply_filters()
        self._apply_search()
        self._apply_sort()
        self._total_count = len(self._filtered_data)
        self._apply_pagination()
        self.endResetModel()
        self.data_updated.emit()

    # =========================================================================
    # Pagination
    # =========================================================================

    def set_page(self, page: int):
        """Set current page."""
        max_page = self.page_count()
        self._page = max(1, min(page, max_page))
        self._apply_pagination()
        self.layoutChanged.emit()

    def set_page_size(self, size: int):
        """Set page size."""
        self._page_size = max(1, size)
        self._page = 1  # Reset to first page
        self._apply_pagination()
        self.layoutChanged.emit()

    def _apply_pagination(self):
        """Apply pagination to filtered/sorted data."""
        start = (self._page - 1) * self._page_size
        end = start + self._page_size
        self._display_data = self._filtered_data[start:end]

    def page_count(self) -> int:
        """Get total number of pages."""
        if self._page_size <= 0:
            return 1
        return max(1, (self._total_count + self._page_size - 1) // self._page_size)

    def current_page(self) -> int:
        """Get current page number."""
        return self._page

    def page_size(self) -> int:
        """Get page size."""
        return self._page_size

    def total_count(self) -> int:
        """Get total number of items (after filtering)."""
        return self._total_count

    def displayed_range(self) -> Tuple[int, int]:
        """Get range of displayed items (1-indexed)."""
        if self._total_count == 0:
            return (0, 0)
        start = (self._page - 1) * self._page_size + 1
        end = min(self._page * self._page_size, self._total_count)
        return (start, end)


# =============================================================================
# Transaction Table Model
# =============================================================================

class TransactionTableModel(BaseTableModel):
    """Table model for financial transactions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_columns()

    def _setup_columns(self):
        """Set up transaction columns."""
        columns = [
            ColumnDefinition(
                key="id",
                header="ID",
                column_type=ColumnType.NUMBER,
                width=60,
                visible=False,
                sortable=True,
                editable=False
            ),
            ColumnDefinition(
                key="date",
                header="Date",
                column_type=ColumnType.DATE,
                width=100,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter
            ),
            ColumnDefinition(
                key="description",
                header="Description",
                column_type=ColumnType.TEXT,
                width=200,
                min_width=150,
                max_width=400,
                sortable=True,
                editable=True
            ),
            ColumnDefinition(
                key="category",
                header="Category",
                column_type=ColumnType.CATEGORY,
                width=120,
                sortable=True,
                editable=True
            ),
            ColumnDefinition(
                key="type",
                header="Type",
                column_type=ColumnType.TEXT,
                width=80,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignCenter,
                formatter=lambda v: v.capitalize() if v else "",
                color_func=self._get_type_color
            ),
            ColumnDefinition(
                key="amount",
                header="Amount",
                column_type=ColumnType.CURRENCY,
                width=100,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignRight,
                color_func=self._get_amount_color
            ),
            ColumnDefinition(
                key="account",
                header="Account",
                column_type=ColumnType.TEXT,
                width=120,
                sortable=True,
                editable=True
            ),
            ColumnDefinition(
                key="notes",
                header="Notes",
                column_type=ColumnType.TEXT,
                width=150,
                sortable=False,
                editable=True,
                visible=False
            )
        ]
        self.set_columns(columns)

    def _get_type_color(self, value: Any, row_data: Dict) -> Optional[str]:
        """Get color for transaction type."""
        if value == "income":
            return "#81C784"  # Green
        elif value == "expense":
            return "#E57373"  # Red
        elif value == "transfer":
            return "#64B5F6"  # Blue
        return None

    def _get_amount_color(self, value: Any, row_data: Dict) -> Optional[str]:
        """Get color for amount based on transaction type."""
        tx_type = row_data.get("type", "")
        if tx_type == "income":
            return "#81C784"  # Green
        elif tx_type == "expense":
            return "#E57373"  # Red
        return None

    def get_transactions_by_type(self, tx_type: str) -> List[Dict[str, Any]]:
        """Get transactions filtered by type."""
        return [row for row in self._data if row.get("type") == tx_type]

    def get_total_by_type(self, tx_type: str) -> float:
        """Get total amount for a transaction type."""
        total = 0.0
        for row in self._data:
            if row.get("type") == tx_type:
                try:
                    total += float(row.get("amount", 0))
                except (ValueError, TypeError):
                    pass
        return total


# =============================================================================
# Budget Table Model
# =============================================================================

class BudgetTableModel(BaseTableModel):
    """Table model for budgets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_columns()

    def _setup_columns(self):
        """Set up budget columns."""
        columns = [
            ColumnDefinition(
                key="id",
                header="ID",
                column_type=ColumnType.NUMBER,
                width=60,
                visible=False,
                sortable=True,
                editable=False
            ),
            ColumnDefinition(
                key="name",
                header="Budget Name",
                column_type=ColumnType.TEXT,
                width=180,
                min_width=120,
                sortable=True,
                editable=True
            ),
            ColumnDefinition(
                key="category",
                header="Category",
                column_type=ColumnType.CATEGORY,
                width=120,
                sortable=True,
                editable=True
            ),
            ColumnDefinition(
                key="period",
                header="Period",
                column_type=ColumnType.TEXT,
                width=80,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter,
                formatter=lambda v: v.capitalize() if v else ""
            ),
            ColumnDefinition(
                key="limit_amount",
                header="Limit",
                column_type=ColumnType.CURRENCY,
                width=100,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignRight
            ),
            ColumnDefinition(
                key="spent",
                header="Spent",
                column_type=ColumnType.CURRENCY,
                width=100,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignRight,
                color_func=self._get_spent_color
            ),
            ColumnDefinition(
                key="remaining",
                header="Remaining",
                column_type=ColumnType.CURRENCY,
                width=100,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignRight,
                color_func=self._get_remaining_color
            ),
            ColumnDefinition(
                key="progress",
                header="Progress",
                column_type=ColumnType.PROGRESS,
                width=120,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignCenter
            ),
            ColumnDefinition(
                key="start_date",
                header="Start Date",
                column_type=ColumnType.DATE,
                width=100,
                sortable=True,
                editable=True,
                visible=False
            ),
            ColumnDefinition(
                key="end_date",
                header="End Date",
                column_type=ColumnType.DATE,
                width=100,
                sortable=True,
                editable=True,
                visible=False
            )
        ]
        self.set_columns(columns)

    def _get_spent_color(self, value: Any, row_data: Dict) -> Optional[str]:
        """Get color for spent amount based on progress."""
        try:
            progress = float(row_data.get("progress", 0))
            if progress >= 100:
                return "#F44336"  # Red
            elif progress >= 75:
                return "#FF9800"  # Orange
            return None
        except (ValueError, TypeError):
            return None

    def _get_remaining_color(self, value: Any, row_data: Dict) -> Optional[str]:
        """Get color for remaining amount."""
        try:
            remaining = float(value) if value else 0
            if remaining < 0:
                return "#F44336"  # Red - Over budget
            elif remaining == 0:
                return "#FF9800"  # Orange - At limit
            return "#4CAF50"  # Green - Under budget
        except (ValueError, TypeError):
            return None

    def get_over_budget(self) -> List[Dict[str, Any]]:
        """Get budgets that are over limit."""
        over_budget = []
        for row in self._data:
            try:
                progress = float(row.get("progress", 0))
                if progress >= 100:
                    over_budget.append(row)
            except (ValueError, TypeError):
                pass
        return over_budget

    def get_near_limit(self, threshold: float = 75.0) -> List[Dict[str, Any]]:
        """Get budgets near their limit."""
        near_limit = []
        for row in self._data:
            try:
                progress = float(row.get("progress", 0))
                if threshold <= progress < 100:
                    near_limit.append(row)
            except (ValueError, TypeError):
                pass
        return near_limit


# =============================================================================
# Category Table Model
# =============================================================================

class CategoryTableModel(BaseTableModel):
    """Table model for categories."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_columns()

    def _setup_columns(self):
        """Set up category columns."""
        columns = [
            ColumnDefinition(
                key="id",
                header="ID",
                column_type=ColumnType.NUMBER,
                width=60,
                visible=False,
                sortable=True,
                editable=False
            ),
            ColumnDefinition(
                key="name",
                header="Category Name",
                column_type=ColumnType.TEXT,
                width=180,
                min_width=120,
                sortable=True,
                editable=True
            ),
            ColumnDefinition(
                key="color",
                header="Color",
                column_type=ColumnType.TEXT,
                width=80,
                sortable=False,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter
            ),
            ColumnDefinition(
                key="icon",
                header="Icon",
                column_type=ColumnType.TEXT,
                width=60,
                sortable=False,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter
            ),
            ColumnDefinition(
                key="type",
                header="Type",
                column_type=ColumnType.TEXT,
                width=80,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter,
                formatter=lambda v: v.capitalize() if v else "",
                color_func=self._get_type_color
            ),
            ColumnDefinition(
                key="parent_id",
                header="Parent",
                column_type=ColumnType.TEXT,
                width=120,
                sortable=True,
                editable=True,
                formatter=lambda v: v if v else "-"
            ),
            ColumnDefinition(
                key="transaction_count",
                header="Transactions",
                column_type=ColumnType.NUMBER,
                width=100,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignRight
            ),
            ColumnDefinition(
                key="total_amount",
                header="Total Amount",
                column_type=ColumnType.CURRENCY,
                width=120,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignRight
            )
        ]
        self.set_columns(columns)

    def _get_type_color(self, value: Any, row_data: Dict) -> Optional[str]:
        """Get color for category type."""
        if value == "income":
            return "#81C784"  # Green
        elif value == "expense":
            return "#E57373"  # Red
        return None

    def get_by_type(self, cat_type: str) -> List[Dict[str, Any]]:
        """Get categories by type."""
        return [row for row in self._data if row.get("type") == cat_type]

    def get_children(self, parent_id: Any) -> List[Dict[str, Any]]:
        """Get child categories."""
        return [row for row in self._data if row.get("parent_id") == parent_id]

    def get_root_categories(self) -> List[Dict[str, Any]]:
        """Get root categories (no parent)."""
        return [row for row in self._data
                if not row.get("parent_id")]


# =============================================================================
# Account Table Model
# =============================================================================

class AccountTableModel(BaseTableModel):
    """Table model for financial accounts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_columns()

    def _setup_columns(self):
        """Set up account columns."""
        columns = [
            ColumnDefinition(
                key="id",
                header="ID",
                column_type=ColumnType.NUMBER,
                width=60,
                visible=False,
                sortable=True,
                editable=False
            ),
            ColumnDefinition(
                key="name",
                header="Account Name",
                column_type=ColumnType.TEXT,
                width=180,
                min_width=120,
                sortable=True,
                editable=True
            ),
            ColumnDefinition(
                key="type",
                header="Type",
                column_type=ColumnType.TEXT,
                width=100,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter,
                formatter=lambda v: v.replace("_", " ").title() if v else ""
            ),
            ColumnDefinition(
                key="institution",
                header="Institution",
                column_type=ColumnType.TEXT,
                width=150,
                sortable=True,
                editable=True,
                formatter=lambda v: v if v else "-"
            ),
            ColumnDefinition(
                key="balance",
                header="Balance",
                column_type=ColumnType.CURRENCY,
                width=120,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignRight,
                color_func=self._get_balance_color
            ),
            ColumnDefinition(
                key="currency",
                header="Currency",
                column_type=ColumnType.TEXT,
                width=70,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter,
                visible=False
            ),
            ColumnDefinition(
                key="is_active",
                header="Active",
                column_type=ColumnType.BOOLEAN,
                width=70,
                sortable=True,
                editable=True,
                alignment=Qt.AlignmentFlag.AlignCenter
            ),
            ColumnDefinition(
                key="last_updated",
                header="Last Updated",
                column_type=ColumnType.DATETIME,
                width=140,
                sortable=True,
                editable=False,
                alignment=Qt.AlignmentFlag.AlignCenter
            )
        ]
        self.set_columns(columns)

    def _get_balance_color(self, value: Any, row_data: Dict) -> Optional[str]:
        """Get color for balance."""
        try:
            balance = float(value) if value else 0
            if balance < 0:
                return "#E57373"  # Red - Negative balance
            elif balance == 0:
                return "#9E9E9E"  # Gray - Zero balance
            return "#81C784"  # Green - Positive balance
        except (ValueError, TypeError):
            return None

    def get_total_balance(self) -> float:
        """Get total balance across all active accounts."""
        total = 0.0
        for row in self._data:
            if row.get("is_active", True):
                try:
                    total += float(row.get("balance", 0))
                except (ValueError, TypeError):
                    pass
        return total

    def get_by_type(self, account_type: str) -> List[Dict[str, Any]]:
        """Get accounts by type."""
        return [row for row in self._data if row.get("type") == account_type]

    def get_active_accounts(self) -> List[Dict[str, Any]]:
        """Get active accounts."""
        return [row for row in self._data if row.get("is_active", True)]


# =============================================================================
# Proxy Model for Advanced Filtering
# =============================================================================

class FilterSortProxyModel(QSortFilterProxyModel):
    """
    Proxy model providing advanced filtering and sorting capabilities.

    Features:
    - Multi-column filtering
    - Date range filtering
    - Amount range filtering
    - Text search across columns
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filters: Dict[str, Any] = {}
        self._date_range: Optional[Tuple[date, date]] = None
        self._amount_range: Optional[Tuple[float, float]] = None
        self._search_text: str = ""
        self._search_columns: List[str] = []

    def set_filter(self, column: str, value: Any):
        """Set a filter for a column."""
        if value is None or value == "":
            self._filters.pop(column, None)
        else:
            self._filters[column] = value
        self.invalidateFilter()

    def set_date_range(self, start_date: Optional[date], end_date: Optional[date]):
        """Set date range filter."""
        if start_date and end_date:
            self._date_range = (start_date, end_date)
        else:
            self._date_range = None
        self.invalidateFilter()

    def set_amount_range(self, min_amount: Optional[float], max_amount: Optional[float]):
        """Set amount range filter."""
        if min_amount is not None and max_amount is not None:
            self._amount_range = (min_amount, max_amount)
        else:
            self._amount_range = None
        self.invalidateFilter()

    def set_search(self, text: str, columns: Optional[List[str]] = None):
        """Set search text and columns."""
        self._search_text = text.lower()
        self._search_columns = columns or []
        self.invalidateFilter()

    def clear_filters(self):
        """Clear all filters."""
        self._filters.clear()
        self._date_range = None
        self._amount_range = None
        self._search_text = ""
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Determine if a row should be shown."""
        source_model = self.sourceModel()
        if not source_model:
            return True

        # Get row data
        row_data = {}
        for col in range(source_model.columnCount()):
            index = source_model.index(source_row, col)
            header = source_model.headerData(col, Qt.Orientation.Horizontal,
                                              Qt.ItemDataRole.DisplayRole)
            key = str(header) if header else f"col_{col}"
            row_data[key] = index.data(Qt.ItemDataRole.UserRole)

        # Apply column filters
        for key, value in self._filters.items():
            row_value = row_data.get(key)
            if isinstance(value, (list, tuple)):
                if row_value not in value:
                    return False
            elif row_value != value:
                return False

        # Apply date range filter
        if self._date_range:
            date_value = row_data.get("date") or row_data.get("Date")
            if date_value:
                if isinstance(date_value, str):
                    try:
                        date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                if isinstance(date_value, (datetime, date)):
                    if isinstance(date_value, datetime):
                        date_value = date_value.date()
                    if not (self._date_range[0] <= date_value <= self._date_range[1]):
                        return False

        # Apply amount range filter
        if self._amount_range:
            amount_value = row_data.get("amount") or row_data.get("Amount")
            if amount_value is not None:
                try:
                    amount_float = float(amount_value)
                    if not (self._amount_range[0] <= amount_float <= self._amount_range[1]):
                        return False
                except (ValueError, TypeError):
                    pass

        # Apply search filter
        if self._search_text:
            found = False
            search_keys = self._search_columns if self._search_columns else row_data.keys()
            for key in search_keys:
                value = row_data.get(key, "")
                if self._search_text in str(value).lower():
                    found = True
                    break
            if not found:
                return False

        return True
