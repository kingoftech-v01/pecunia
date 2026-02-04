"""
Transaction management page with PyQt6.

Provides TransactionsPage with QTableView and custom model for viewing/filtering
transactions with virtual scrolling, multi-select, bulk actions, and keyboard shortcuts.

Features:
- QTableView with custom QAbstractTableModel for virtual scrolling
- Filter panel with date range, type, category, search filters
- Search bar with real-time filtering
- Toolbar with actions (add, export, import, delete)
- Multi-select with bulk actions
- Keyboard shortcuts for common operations
- Category quick filter chips
- Sortable columns with indicators
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableView, QHeaderView, QPushButton, QLineEdit,
    QComboBox, QDateEdit, QLabel, QFrame, QSizePolicy,
    QAbstractItemView, QMenu, QToolBar, QSpacerItem,
    QMessageBox, QCheckBox, QScrollArea, QApplication,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QDate, QSize, QModelIndex,
    QAbstractTableModel, QSortFilterProxyModel, QTimer,
    QItemSelectionModel, QRect, QPoint
)
from PyQt6.QtGui import (
    QAction, QColor, QFont, QKeySequence, QShortcut,
    QPainter, QPen, QBrush, QPalette, QIcon
)


class TransactionType(Enum):
    """Transaction type enumeration."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class SyncStatus(Enum):
    """Transaction sync status."""
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass
class Transaction:
    """Transaction data model."""
    id: Optional[int]
    date: date
    type: TransactionType
    category: str
    description: str
    amount: Decimal
    account: str
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    merchant: Optional[str] = None
    sync_status: SyncStatus = SyncStatus.SYNCED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TransactionFilter:
    """Filter criteria for transactions."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    transaction_type: Optional[TransactionType] = None
    category: Optional[str] = None
    categories: Optional[Set[str]] = None
    search_text: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    account: Optional[str] = None
    tags: Optional[List[str]] = None
    sync_status: Optional[SyncStatus] = None


# =============================================================================
# Custom Delegates
# =============================================================================

class AmountDelegate(QStyledItemDelegate):
    """Delegate for displaying currency amounts with colors."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.positive_color = QColor("#4CAF50")
        self.negative_color = QColor("#F44336")
        self.transfer_color = QColor("#2196F3")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint the amount with appropriate color."""
        painter.save()

        # Get data
        amount = index.data(Qt.ItemDataRole.UserRole)
        txn_type = index.data(Qt.ItemDataRole.UserRole + 1)
        display_text = index.data(Qt.ItemDataRole.DisplayRole)

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#E3F2FD"))

        # Set text color based on transaction type
        if txn_type == TransactionType.INCOME.value:
            color = self.positive_color
        elif txn_type == TransactionType.EXPENSE.value:
            color = self.negative_color
        else:
            color = self.transfer_color

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(color)

        # Draw text right-aligned
        text_rect = option.rect.adjusted(4, 0, -8, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, display_text)

        painter.restore()


class TypeDelegate(QStyledItemDelegate):
    """Delegate for displaying transaction type with colored badge."""

    TYPE_COLORS = {
        TransactionType.INCOME.value: ("#E8F5E9", "#4CAF50"),
        TransactionType.EXPENSE.value: ("#FFEBEE", "#F44336"),
        TransactionType.TRANSFER.value: ("#E3F2FD", "#2196F3"),
    }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint the type badge."""
        painter.save()

        txn_type = index.data(Qt.ItemDataRole.DisplayRole)
        bg_color, text_color = self.TYPE_COLORS.get(
            txn_type.lower() if txn_type else "",
            ("#F5F5F5", "#757575")
        )

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Draw badge
        badge_rect = QRect(
            option.rect.left() + 8,
            option.rect.top() + (option.rect.height() - 24) // 2,
            option.rect.width() - 16,
            24
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg_color))
        painter.drawRoundedRect(badge_rect, 4, 4)

        # Draw text
        painter.setPen(QColor(text_color))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, txn_type.capitalize() if txn_type else "")

        painter.restore()


class CategoryDelegate(QStyledItemDelegate):
    """Delegate for displaying category with color dot."""

    # Category color mapping
    CATEGORY_COLORS = {
        "groceries": "#4CAF50",
        "dining": "#FF9800",
        "transport": "#2196F3",
        "utilities": "#9C27B0",
        "entertainment": "#E91E63",
        "shopping": "#00BCD4",
        "health": "#F44336",
        "salary": "#4CAF50",
        "investment": "#3F51B5",
        "default": "#9E9E9E"
    }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint category with color indicator."""
        painter.save()

        category = index.data(Qt.ItemDataRole.DisplayRole) or ""
        color_key = category.lower().replace(" ", "_")
        color = self.CATEGORY_COLORS.get(color_key, self.CATEGORY_COLORS["default"])

        # Draw selection/hover background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#E3F2FD"))

        # Draw color dot
        dot_size = 10
        dot_x = option.rect.left() + 8
        dot_y = option.rect.top() + (option.rect.height() - dot_size) // 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

        # Draw text
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        text_rect = QRect(
            dot_x + dot_size + 8,
            option.rect.top(),
            option.rect.width() - dot_size - 24,
            option.rect.height()
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, category)

        painter.restore()


# =============================================================================
# Transaction Table Model
# =============================================================================

class TransactionTableModel(QAbstractTableModel):
    """
    Custom table model for transactions with virtual scrolling support.

    Provides efficient data access for large transaction lists by
    only loading visible data on demand.
    """

    COLUMNS = [
        ("", "checkbox", 40),
        ("Date", "date", 100),
        ("Type", "type", 90),
        ("Category", "category", 130),
        ("Description", "description", 250),
        ("Amount", "amount", 110),
        ("Account", "account", 120),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._transactions: List[Transaction] = []
        self._selected_ids: Set[int] = set()
        self._sort_column = 1  # Date
        self._sort_order = Qt.SortOrder.DescendingOrder

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows."""
        if parent.isValid():
            return 0
        return len(self._transactions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._transactions):
            return None

        txn = self._transactions[row]
        col_name = self.COLUMNS[col][1]

        if role == Qt.ItemDataRole.DisplayRole:
            if col_name == "checkbox":
                return None
            elif col_name == "date":
                return txn.date.strftime("%Y-%m-%d")
            elif col_name == "type":
                return txn.type.value
            elif col_name == "category":
                return txn.category
            elif col_name == "description":
                return txn.description
            elif col_name == "amount":
                if txn.type == TransactionType.EXPENSE:
                    return f"-${txn.amount:,.2f}"
                return f"${txn.amount:,.2f}"
            elif col_name == "account":
                return txn.account

        elif role == Qt.ItemDataRole.UserRole:
            # Store raw data for sorting and delegates
            if col_name == "amount":
                return float(txn.amount)
            elif col_name == "date":
                return txn.date
            elif col_name == "checkbox":
                return txn.id in self._selected_ids
            return None

        elif role == Qt.ItemDataRole.UserRole + 1:
            # Transaction type for amount coloring
            if col_name == "amount":
                return txn.type.value
            return None

        elif role == Qt.ItemDataRole.UserRole + 2:
            # Full transaction object
            return txn

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_name == "description" and txn.notes:
                return txn.notes
            return None

        elif role == Qt.ItemDataRole.CheckStateRole:
            if col_name == "checkbox":
                return Qt.CheckState.Checked if txn.id in self._selected_ids else Qt.CheckState.Unchecked
            return None

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_name == "amount":
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Set data for the given index."""
        if not index.isValid():
            return False

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._transactions):
            return False

        txn = self._transactions[row]
        col_name = self.COLUMNS[col][1]

        if role == Qt.ItemDataRole.CheckStateRole and col_name == "checkbox":
            if value == Qt.CheckState.Checked:
                self._selected_ids.add(txn.id)
            else:
                self._selected_ids.discard(txn.id)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        col_name = self.COLUMNS[index.column()][1]
        if col_name == "checkbox":
            flags |= Qt.ItemFlag.ItemIsUserCheckable

        return flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                header = self.COLUMNS[section][0]
                # Add sort indicator
                if section == self._sort_column and section > 0:
                    arrow = " \u25B2" if self._sort_order == Qt.SortOrder.AscendingOrder else " \u25BC"
                    return header + arrow
                return header
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort the data by the given column."""
        if column == 0:  # Checkbox column
            return

        self._sort_column = column
        self._sort_order = order

        col_name = self.COLUMNS[column][1]

        sort_key_map = {
            "date": lambda t: t.date,
            "type": lambda t: t.type.value,
            "category": lambda t: t.category.lower(),
            "description": lambda t: t.description.lower(),
            "amount": lambda t: t.amount,
            "account": lambda t: t.account.lower(),
        }

        if col_name in sort_key_map:
            self.layoutAboutToBeChanged.emit()
            self._transactions.sort(
                key=sort_key_map[col_name],
                reverse=(order == Qt.SortOrder.DescendingOrder)
            )
            self.layoutChanged.emit()

    def set_transactions(self, transactions: List[Transaction]):
        """Set the transaction list."""
        self.beginResetModel()
        self._transactions = transactions
        self.endResetModel()

    def get_transaction(self, row: int) -> Optional[Transaction]:
        """Get transaction at row."""
        if 0 <= row < len(self._transactions):
            return self._transactions[row]
        return None

    def get_transaction_by_id(self, txn_id: int) -> Optional[Transaction]:
        """Get transaction by ID."""
        for txn in self._transactions:
            if txn.id == txn_id:
                return txn
        return None

    def get_selected_ids(self) -> List[int]:
        """Get list of selected transaction IDs."""
        return list(self._selected_ids)

    def set_selected_ids(self, ids: Set[int]):
        """Set selected transaction IDs."""
        self._selected_ids = ids
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, 0),
            [Qt.ItemDataRole.CheckStateRole]
        )

    def clear_selection(self):
        """Clear all selections."""
        self._selected_ids.clear()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, 0),
            [Qt.ItemDataRole.CheckStateRole]
        )

    def select_all(self):
        """Select all transactions."""
        self._selected_ids = {t.id for t in self._transactions if t.id is not None}
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, 0),
            [Qt.ItemDataRole.CheckStateRole]
        )

    def select_range(self, start_row: int, end_row: int):
        """Select a range of transactions."""
        for row in range(start_row, end_row + 1):
            if 0 <= row < len(self._transactions):
                txn = self._transactions[row]
                if txn.id is not None:
                    self._selected_ids.add(txn.id)

        self.dataChanged.emit(
            self.index(start_row, 0),
            self.index(end_row, 0),
            [Qt.ItemDataRole.CheckStateRole]
        )


# =============================================================================
# Filter Proxy Model
# =============================================================================

class TransactionFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering transactions."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._filter = TransactionFilter()
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_filter(self, filter_obj: TransactionFilter):
        """Set the filter criteria."""
        self._filter = filter_obj
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Determine if row passes filter."""
        model = self.sourceModel()
        if not isinstance(model, TransactionTableModel):
            return True

        txn = model.get_transaction(source_row)
        if not txn:
            return False

        f = self._filter

        # Date range filter
        if f.start_date and txn.date < f.start_date:
            return False
        if f.end_date and txn.date > f.end_date:
            return False

        # Type filter
        if f.transaction_type and txn.type != f.transaction_type:
            return False

        # Category filter (single)
        if f.category and txn.category.lower() != f.category.lower():
            return False

        # Categories filter (multiple)
        if f.categories and txn.category not in f.categories:
            return False

        # Account filter
        if f.account and txn.account.lower() != f.account.lower():
            return False

        # Amount range
        if f.min_amount is not None and txn.amount < f.min_amount:
            return False
        if f.max_amount is not None and txn.amount > f.max_amount:
            return False

        # Search text
        if f.search_text:
            search_lower = f.search_text.lower()
            searchable = [
                txn.description.lower(),
                txn.category.lower(),
                txn.account.lower(),
                txn.merchant.lower() if txn.merchant else "",
                txn.notes.lower() if txn.notes else "",
            ]
            if txn.tags:
                searchable.extend([t.lower() for t in txn.tags])

            if not any(search_lower in s for s in searchable):
                return False

        # Tags filter
        if f.tags:
            if not txn.tags or not any(t in txn.tags for t in f.tags):
                return False

        # Sync status
        if f.sync_status and txn.sync_status != f.sync_status:
            return False

        return True


# =============================================================================
# Category Chip Widget
# =============================================================================

class CategoryChip(QPushButton):
    """Quick filter chip for categories."""

    toggled_filter = pyqtSignal(str, bool)

    def __init__(self, category: str, color: str = "#9E9E9E", parent: Optional[QWidget] = None):
        super().__init__(category, parent)
        self._category = category
        self._color = color
        self._active = False
        self.setCheckable(True)
        self.setMinimumHeight(28)
        self.setMaximumHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self.clicked.connect(self._on_clicked)

    def _update_style(self) -> None:
        """Update chip appearance based on state."""
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._color};
                    color: white;
                    border: none;
                    border-radius: 14px;
                    padding: 4px 14px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {self._color};
                    opacity: 0.9;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #F5F5F5;
                    color: #424242;
                    border: 1px solid #E0E0E0;
                    border-radius: 14px;
                    padding: 4px 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #EEEEEE;
                    border-color: {self._color};
                }}
            """)

    def _on_clicked(self) -> None:
        """Handle chip click."""
        self._active = not self._active
        self._update_style()
        self.toggled_filter.emit(self._category, self._active)

    @property
    def category(self) -> str:
        return self._category

    @property
    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        """Set chip active state without emitting signal."""
        self._active = active
        self.setChecked(active)
        self._update_style()


# =============================================================================
# Pagination Widget
# =============================================================================

class PaginationWidget(QWidget):
    """Pagination controls widget."""

    page_changed = pyqtSignal(int)
    page_size_changed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_page = 1
        self._total_pages = 1
        self._page_size = 50
        self._total_items = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up pagination UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)

        # Items per page
        layout.addWidget(QLabel("Show:"))
        self._page_size_combo = QComboBox()
        self._page_size_combo.addItems(["25", "50", "100", "250", "500"])
        self._page_size_combo.setCurrentText(str(self._page_size))
        self._page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        self._page_size_combo.setMaximumWidth(80)
        layout.addWidget(self._page_size_combo)
        layout.addWidget(QLabel("items"))

        layout.addStretch()

        # Page info
        self._info_label = QLabel()
        self._info_label.setStyleSheet("color: #757575;")
        layout.addWidget(self._info_label)

        layout.addSpacing(16)

        # Navigation buttons
        btn_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 32px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:disabled {
                color: #BDBDBD;
                border-color: #EEEEEE;
            }
        """

        self._first_btn = QPushButton("\u00AB")
        self._first_btn.setToolTip("First page (Ctrl+Home)")
        self._first_btn.setStyleSheet(btn_style)
        self._first_btn.clicked.connect(self._go_first)
        layout.addWidget(self._first_btn)

        self._prev_btn = QPushButton("\u2039")
        self._prev_btn.setToolTip("Previous page (Page Up)")
        self._prev_btn.setStyleSheet(btn_style)
        self._prev_btn.clicked.connect(self._go_prev)
        layout.addWidget(self._prev_btn)

        self._page_label = QLabel()
        self._page_label.setMinimumWidth(80)
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._page_label)

        self._next_btn = QPushButton("\u203A")
        self._next_btn.setToolTip("Next page (Page Down)")
        self._next_btn.setStyleSheet(btn_style)
        self._next_btn.clicked.connect(self._go_next)
        layout.addWidget(self._next_btn)

        self._last_btn = QPushButton("\u00BB")
        self._last_btn.setToolTip("Last page (Ctrl+End)")
        self._last_btn.setStyleSheet(btn_style)
        self._last_btn.clicked.connect(self._go_last)
        layout.addWidget(self._last_btn)

        self._update_display()

    def _update_display(self) -> None:
        """Update pagination display."""
        self._page_label.setText(f"{self._current_page} / {self._total_pages}")

        start = (self._current_page - 1) * self._page_size + 1
        end = min(self._current_page * self._page_size, self._total_items)
        if self._total_items > 0:
            self._info_label.setText(f"Showing {start:,}-{end:,} of {self._total_items:,}")
        else:
            self._info_label.setText("No transactions")

        self._first_btn.setEnabled(self._current_page > 1)
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < self._total_pages)
        self._last_btn.setEnabled(self._current_page < self._total_pages)

    def _on_page_size_changed(self, text: str) -> None:
        """Handle page size change."""
        self._page_size = int(text)
        self._current_page = 1
        self._calculate_total_pages()
        self._update_display()
        self.page_size_changed.emit(self._page_size)

    def _go_first(self) -> None:
        if self._current_page != 1:
            self._current_page = 1
            self._update_display()
            self.page_changed.emit(self._current_page)

    def _go_prev(self) -> None:
        if self._current_page > 1:
            self._current_page -= 1
            self._update_display()
            self.page_changed.emit(self._current_page)

    def _go_next(self) -> None:
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._update_display()
            self.page_changed.emit(self._current_page)

    def _go_last(self) -> None:
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._update_display()
            self.page_changed.emit(self._current_page)

    def _calculate_total_pages(self) -> None:
        """Calculate total pages based on items and page size."""
        self._total_pages = max(1, (self._total_items + self._page_size - 1) // self._page_size)

    def set_total_items(self, total: int) -> None:
        """Set total number of items."""
        self._total_items = total
        self._calculate_total_pages()
        if self._current_page > self._total_pages:
            self._current_page = max(1, self._total_pages)
        self._update_display()

    def reset(self) -> None:
        """Reset pagination to first page."""
        self._current_page = 1
        self._update_display()

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def page_size(self) -> int:
        return self._page_size


# =============================================================================
# Filter Panel
# =============================================================================

class FilterPanel(QFrame):
    """Collapsible filter panel for transactions."""

    filter_changed = pyqtSignal(TransactionFilter)
    filter_cleared = pyqtSignal()

    # Category colors for chips
    CATEGORY_COLORS = {
        "Groceries": "#4CAF50",
        "Dining": "#FF9800",
        "Transport": "#2196F3",
        "Utilities": "#9C27B0",
        "Entertainment": "#E91E63",
        "Shopping": "#00BCD4",
        "Health": "#F44336",
        "Salary": "#66BB6A",
        "Investment": "#3F51B5",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("filterPanel")
        self._active_categories: Set[str] = set()
        self._category_chips: List[CategoryChip] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up filter panel UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            #filterPanel {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 12)

        # Filter title
        title_layout = QHBoxLayout()
        title_label = QLabel("Filters")
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1976D2;
                border: none;
                padding: 4px 8px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self._clear_btn.clicked.connect(self._clear_filters)
        title_layout.addWidget(self._clear_btn)

        layout.addLayout(title_layout)

        # First row: Date range and type
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Date range
        date_group = QHBoxLayout()
        date_group.setSpacing(8)
        date_group.addWidget(QLabel("Date:"))

        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setDate(QDate.currentDate().addMonths(-1))
        self._start_date.setDisplayFormat("MMM dd, yyyy")
        self._start_date.setMaximumWidth(130)
        self._start_date.dateChanged.connect(self._on_filter_changed)
        date_group.addWidget(self._start_date)

        date_group.addWidget(QLabel("to"))

        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setDate(QDate.currentDate())
        self._end_date.setDisplayFormat("MMM dd, yyyy")
        self._end_date.setMaximumWidth(130)
        self._end_date.dateChanged.connect(self._on_filter_changed)
        date_group.addWidget(self._end_date)

        row1.addLayout(date_group)

        # Quick date buttons
        quick_dates = QHBoxLayout()
        quick_dates.setSpacing(4)

        for label, days in [("7D", 7), ("30D", 30), ("90D", 90), ("YTD", -1), ("All", -2)]:
            btn = QPushButton(label)
            btn.setMaximumWidth(50)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #F5F5F5;
                }
            """)
            btn.clicked.connect(lambda checked, d=days: self._set_quick_date(d))
            quick_dates.addWidget(btn)

        row1.addLayout(quick_dates)
        row1.addStretch()

        # Type filter
        type_group = QHBoxLayout()
        type_group.setSpacing(8)
        type_group.addWidget(QLabel("Type:"))

        self._type_combo = QComboBox()
        self._type_combo.addItem("All Types", None)
        self._type_combo.addItem("Income", TransactionType.INCOME)
        self._type_combo.addItem("Expense", TransactionType.EXPENSE)
        self._type_combo.addItem("Transfer", TransactionType.TRANSFER)
        self._type_combo.setMinimumWidth(120)
        self._type_combo.currentIndexChanged.connect(self._on_filter_changed)
        type_group.addWidget(self._type_combo)

        row1.addLayout(type_group)

        layout.addLayout(row1)

        # Category chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)
        chips_label = QLabel("Categories:")
        chips_label.setStyleSheet("color: #757575;")
        chips_layout.addWidget(chips_label)

        self._chips_container = QHBoxLayout()
        self._chips_container.setSpacing(6)
        chips_layout.addLayout(self._chips_container)
        chips_layout.addStretch()

        layout.addLayout(chips_layout)

    def _set_quick_date(self, days: int) -> None:
        """Set quick date range."""
        today = QDate.currentDate()

        if days == -1:  # YTD
            self._start_date.setDate(QDate(today.year(), 1, 1))
            self._end_date.setDate(today)
        elif days == -2:  # All time
            self._start_date.setDate(QDate(2000, 1, 1))
            self._end_date.setDate(today)
        else:
            self._start_date.setDate(today.addDays(-days))
            self._end_date.setDate(today)

        self._on_filter_changed()

    def _on_filter_changed(self) -> None:
        """Emit filter changed signal."""
        self.filter_changed.emit(self.get_filter())

    def _on_category_toggled(self, category: str, active: bool) -> None:
        """Handle category chip toggle."""
        if active:
            self._active_categories.add(category)
        else:
            self._active_categories.discard(category)
        self._on_filter_changed()

    def _clear_filters(self) -> None:
        """Clear all filters."""
        self._start_date.setDate(QDate.currentDate().addMonths(-1))
        self._end_date.setDate(QDate.currentDate())
        self._type_combo.setCurrentIndex(0)

        self._active_categories.clear()
        for chip in self._category_chips:
            chip.set_active(False)

        self.filter_cleared.emit()
        self._on_filter_changed()

    def get_filter(self) -> TransactionFilter:
        """Get current filter settings."""
        filter_obj = TransactionFilter()

        # Date range
        start_qdate = self._start_date.date()
        end_qdate = self._end_date.date()
        filter_obj.start_date = date(start_qdate.year(), start_qdate.month(), start_qdate.day())
        filter_obj.end_date = date(end_qdate.year(), end_qdate.month(), end_qdate.day())

        # Type
        type_data = self._type_combo.currentData()
        if type_data is not None:
            filter_obj.transaction_type = type_data

        # Categories
        if self._active_categories:
            filter_obj.categories = self._active_categories.copy()

        return filter_obj

    def set_categories(self, categories: List[str]) -> None:
        """Set available categories for chips."""
        # Clear existing chips
        while self._chips_container.count():
            item = self._chips_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._category_chips.clear()

        # Add new chips
        for category in sorted(categories)[:10]:  # Limit to 10 chips
            color = self.CATEGORY_COLORS.get(category, "#9E9E9E")
            chip = CategoryChip(category, color)
            chip.toggled_filter.connect(self._on_category_toggled)
            if category in self._active_categories:
                chip.set_active(True)
            self._chips_container.addWidget(chip)
            self._category_chips.append(chip)


# =============================================================================
# Summary Bar Widget
# =============================================================================

class SummaryBar(QFrame):
    """Summary statistics bar for filtered transactions."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("summaryBar")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up summary bar UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            #summaryBar {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(32)

        # Total transactions
        self._count_label = QLabel("0 transactions")
        self._count_label.setStyleSheet("color: #757575; font-size: 12px;")
        layout.addWidget(self._count_label)

        layout.addStretch()

        # Income total
        income_container = QHBoxLayout()
        income_container.setSpacing(6)
        income_icon = QLabel("\u2191")  # Up arrow
        income_icon.setStyleSheet("color: #4CAF50; font-size: 16px;")
        income_container.addWidget(income_icon)
        self._income_label = QLabel("$0.00")
        self._income_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        income_container.addWidget(self._income_label)
        income_text = QLabel("Income")
        income_text.setStyleSheet("color: #757575; font-size: 11px;")
        income_container.addWidget(income_text)
        layout.addLayout(income_container)

        # Expense total
        expense_container = QHBoxLayout()
        expense_container.setSpacing(6)
        expense_icon = QLabel("\u2193")  # Down arrow
        expense_icon.setStyleSheet("color: #F44336; font-size: 16px;")
        expense_container.addWidget(expense_icon)
        self._expense_label = QLabel("$0.00")
        self._expense_label.setStyleSheet("color: #F44336; font-weight: bold;")
        expense_container.addWidget(self._expense_label)
        expense_text = QLabel("Expenses")
        expense_text.setStyleSheet("color: #757575; font-size: 11px;")
        expense_container.addWidget(expense_text)
        layout.addLayout(expense_container)

        # Net total
        net_container = QHBoxLayout()
        net_container.setSpacing(6)
        self._net_icon = QLabel("=")
        self._net_icon.setStyleSheet("color: #1976D2; font-size: 16px;")
        net_container.addWidget(self._net_icon)
        self._net_label = QLabel("$0.00")
        self._net_label.setStyleSheet("color: #1976D2; font-weight: bold;")
        net_container.addWidget(self._net_label)
        net_text = QLabel("Net")
        net_text.setStyleSheet("color: #757575; font-size: 11px;")
        net_container.addWidget(net_text)
        layout.addLayout(net_container)

    def update_summary(self, transactions: List[Transaction]) -> None:
        """Update summary with transaction data."""
        count = len(transactions)
        total_income = Decimal('0')
        total_expense = Decimal('0')

        for txn in transactions:
            if txn.type == TransactionType.INCOME:
                total_income += txn.amount
            elif txn.type == TransactionType.EXPENSE:
                total_expense += txn.amount

        net = total_income - total_expense

        # Update labels
        self._count_label.setText(f"{count:,} transaction{'s' if count != 1 else ''}")
        self._income_label.setText(f"${total_income:,.2f}")
        self._expense_label.setText(f"${total_expense:,.2f}")

        if net >= 0:
            self._net_label.setText(f"+${net:,.2f}")
            self._net_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self._net_label.setText(f"-${abs(net):,.2f}")
            self._net_label.setStyleSheet("color: #F44336; font-weight: bold;")


# =============================================================================
# Bulk Actions Bar
# =============================================================================

class BulkActionsBar(QFrame):
    """Bulk actions bar for selected transactions."""

    delete_requested = pyqtSignal(list)
    export_requested = pyqtSignal(list)
    categorize_requested = pyqtSignal(list)
    select_all_requested = pyqtSignal()
    deselect_all_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("bulkActionsBar")
        self._selected_count = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up bulk actions bar UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            #bulkActionsBar {
                background-color: #E3F2FD;
                border: 1px solid #90CAF9;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(16)

        # Selection info
        self._selection_label = QLabel("0 selected")
        self._selection_label.setStyleSheet("font-weight: bold; color: #1565C0;")
        layout.addWidget(self._selection_label)

        layout.addStretch()

        # Select/Deselect all
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1976D2;
                border: none;
                padding: 4px 8px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self._select_all_btn.clicked.connect(self.select_all_requested.emit)
        layout.addWidget(self._select_all_btn)

        self._deselect_btn = QPushButton("Deselect")
        self._deselect_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1976D2;
                border: none;
                padding: 4px 8px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self._deselect_btn.clicked.connect(self.deselect_all_requested.emit)
        layout.addWidget(self._deselect_btn)

        layout.addSpacing(16)

        # Action buttons
        btn_style = """
            QPushButton {
                background-color: white;
                border: 1px solid #90CAF9;
                border-radius: 4px;
                padding: 6px 12px;
                color: #1565C0;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """

        self._categorize_btn = QPushButton("Categorize")
        self._categorize_btn.setStyleSheet(btn_style)
        self._categorize_btn.clicked.connect(lambda: self.categorize_requested.emit([]))
        layout.addWidget(self._categorize_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setStyleSheet(btn_style)
        self._export_btn.clicked.connect(lambda: self.export_requested.emit([]))
        layout.addWidget(self._export_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
                border-radius: 4px;
                padding: 6px 12px;
                color: #C62828;
            }
            QPushButton:hover {
                background-color: #FFCDD2;
            }
        """)
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit([]))
        layout.addWidget(self._delete_btn)

    def update_selection(self, count: int) -> None:
        """Update selection count display."""
        self._selected_count = count
        self._selection_label.setText(f"{count:,} selected")
        self.setVisible(count > 0)


# =============================================================================
# Transactions Page
# =============================================================================

class TransactionsPage(QWidget):
    """
    Main transactions page with QTableView, filters, search, and bulk actions.

    Features:
    - QTableView with custom model for virtual scrolling
    - Filter panel with date range, type, category
    - Search bar with real-time filtering
    - Toolbar actions (add, import, export)
    - Multi-select with bulk actions
    - Keyboard shortcuts

    Signals:
        transaction_selected(int): Emitted when a transaction is selected
        edit_requested(int): Emitted when edit is requested
        create_requested(): Emitted when create new is requested
        import_requested(): Emitted when import is requested
        export_requested(list): Emitted with IDs to export
        data_changed(): Emitted when data is modified
    """

    transaction_selected = pyqtSignal(int)
    edit_requested = pyqtSignal(int)
    create_requested = pyqtSignal()
    import_requested = pyqtSignal()
    export_requested = pyqtSignal(list)
    data_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("transactionsPage")
        self._transactions: List[Transaction] = []
        self._last_clicked_row = -1
        self._setup_ui()
        self._setup_model()
        self._setup_shortcuts()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Header with title and toolbar
        header_layout = QHBoxLayout()

        title = QLabel("Transactions")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Search bar
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search transactions... (Ctrl+F)")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setMinimumWidth(250)
        self._search_input.setMaximumWidth(350)
        self._search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 20px;
                padding: 8px 16px;
                background-color: #F5F5F5;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
                background-color: white;
            }
        """)
        header_layout.addWidget(self._search_input)

        header_layout.addSpacing(16)

        # Toolbar buttons
        btn_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """

        self._import_btn = QPushButton("Import")
        self._import_btn.setStyleSheet(btn_style)
        self._import_btn.setToolTip("Import transactions from file (Ctrl+I)")
        self._import_btn.clicked.connect(self.import_requested.emit)
        header_layout.addWidget(self._import_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setStyleSheet(btn_style)
        self._export_btn.setToolTip("Export transactions to CSV (Ctrl+E)")
        self._export_btn.clicked.connect(self._on_export)
        header_layout.addWidget(self._export_btn)

        self._add_btn = QPushButton("+ Add Transaction")
        self._add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        self._add_btn.setToolTip("Add new transaction (Ctrl+N)")
        self._add_btn.clicked.connect(self.create_requested.emit)
        header_layout.addWidget(self._add_btn)

        layout.addLayout(header_layout)

        # Filter panel
        self._filter_panel = FilterPanel()
        layout.addWidget(self._filter_panel)

        # Bulk actions bar (hidden by default)
        self._bulk_actions_bar = BulkActionsBar()
        self._bulk_actions_bar.hide()
        layout.addWidget(self._bulk_actions_bar)

        # Table view
        self._table_view = QTableView()
        self._table_view.setObjectName("transactionsTable")
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table_view.setSortingEnabled(True)
        self._table_view.setShowGrid(False)
        self._table_view.setWordWrap(False)
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.verticalHeader().setDefaultSectionSize(44)
        self._table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Enable hover
        self._table_view.setMouseTracking(True)

        # Set stylesheet
        self._table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
            }
            QTableView::item {
                padding: 8px;
                border-bottom: 1px solid #F5F5F5;
            }
            QTableView::item:selected {
                background-color: #E3F2FD;
                color: #212121;
            }
            QTableView::item:hover {
                background-color: #F5F5F5;
            }
            QHeaderView::section {
                background-color: #FAFAFA;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #E0E0E0;
                font-weight: 600;
            }
            QHeaderView::section:hover {
                background-color: #F5F5F5;
            }
        """)

        layout.addWidget(self._table_view)

        # Summary and pagination
        footer_layout = QHBoxLayout()

        self._summary_bar = SummaryBar()
        footer_layout.addWidget(self._summary_bar, 1)

        footer_layout.addSpacing(16)

        self._pagination = PaginationWidget()
        footer_layout.addWidget(self._pagination)

        layout.addLayout(footer_layout)

    def _setup_model(self) -> None:
        """Set up the table model and proxy."""
        self._model = TransactionTableModel(self)
        self._proxy_model = TransactionFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)

        self._table_view.setModel(self._proxy_model)

        # Set up column widths and delegates
        header = self._table_view.horizontalHeader()
        for i, (_, col_name, width) in enumerate(TransactionTableModel.COLUMNS):
            if col_name == "description":
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                self._table_view.setColumnWidth(i, width)

            # Set delegates
            if col_name == "amount":
                self._table_view.setItemDelegateForColumn(i, AmountDelegate(self))
            elif col_name == "type":
                self._table_view.setItemDelegateForColumn(i, TypeDelegate(self))
            elif col_name == "category":
                self._table_view.setItemDelegateForColumn(i, CategoryDelegate(self))

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self._focus_search)

        # New transaction
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self.create_requested.emit)

        # Import
        import_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        import_shortcut.activated.connect(self.import_requested.emit)

        # Export
        export_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        export_shortcut.activated.connect(self._on_export)

        # Delete
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self._delete_selected)

        # Select all
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(self._select_all)

        # Edit
        edit_shortcut = QShortcut(QKeySequence("Enter"), self)
        edit_shortcut.activated.connect(self._edit_current)

        # Escape - clear selection
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._clear_selection)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Search
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_search)
        self._search_input.textChanged.connect(lambda: self._search_timer.start(300))

        # Filter panel
        self._filter_panel.filter_changed.connect(self._apply_filter)
        self._filter_panel.filter_cleared.connect(self._on_filter_cleared)

        # Table interactions
        self._table_view.doubleClicked.connect(self._on_double_click)
        self._table_view.customContextMenuRequested.connect(self._show_context_menu)
        self._table_view.clicked.connect(self._on_row_clicked)

        # Selection changes
        self._table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Bulk actions
        self._bulk_actions_bar.select_all_requested.connect(self._select_all)
        self._bulk_actions_bar.deselect_all_requested.connect(self._clear_selection)
        self._bulk_actions_bar.delete_requested.connect(lambda _: self._delete_selected())
        self._bulk_actions_bar.export_requested.connect(lambda _: self._export_selected())

        # Pagination
        self._pagination.page_changed.connect(self._on_page_changed)
        self._pagination.page_size_changed.connect(self._on_page_size_changed)

    def _focus_search(self) -> None:
        """Focus the search input."""
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _apply_search(self) -> None:
        """Apply search filter."""
        current_filter = self._filter_panel.get_filter()
        current_filter.search_text = self._search_input.text().strip() or None
        self._proxy_model.set_filter(current_filter)
        self._update_summary()
        self._pagination.set_total_items(self._proxy_model.rowCount())

    def _apply_filter(self, filter_obj: TransactionFilter) -> None:
        """Apply filter to transactions."""
        # Merge with search text
        filter_obj.search_text = self._search_input.text().strip() or None
        self._proxy_model.set_filter(filter_obj)
        self._update_summary()
        self._pagination.set_total_items(self._proxy_model.rowCount())
        self._pagination.reset()

    def _on_filter_cleared(self) -> None:
        """Handle filter cleared."""
        self._search_input.clear()
        self._apply_search()

    def _on_row_clicked(self, index: QModelIndex) -> None:
        """Handle row click with shift-click support."""
        modifiers = QApplication.keyboardModifiers()
        row = index.row()

        if modifiers & Qt.KeyboardModifier.ShiftModifier and self._last_clicked_row >= 0:
            # Shift-click: select range
            start_row = min(self._last_clicked_row, row)
            end_row = max(self._last_clicked_row, row)
            self._model.select_range(start_row, end_row)
        elif index.column() == 0:
            # Checkbox column - toggle handled by model
            pass
        else:
            self._last_clicked_row = row

        self._update_bulk_actions_bar()

    def _on_selection_changed(self) -> None:
        """Handle selection changes."""
        selected_rows = self._table_view.selectionModel().selectedRows()
        self._update_bulk_actions_bar()

    def _on_double_click(self, index: QModelIndex) -> None:
        """Handle double-click to edit."""
        if index.column() == 0:  # Checkbox column
            return

        source_index = self._proxy_model.mapToSource(index)
        txn = self._model.get_transaction(source_index.row())
        if txn and txn.id:
            self.edit_requested.emit(txn.id)

    def _edit_current(self) -> None:
        """Edit currently selected transaction."""
        indexes = self._table_view.selectionModel().selectedRows()
        if indexes:
            source_index = self._proxy_model.mapToSource(indexes[0])
            txn = self._model.get_transaction(source_index.row())
            if txn and txn.id:
                self.edit_requested.emit(txn.id)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu for transaction."""
        index = self._table_view.indexAt(position)
        if not index.isValid():
            return

        source_index = self._proxy_model.mapToSource(index)
        txn = self._model.get_transaction(source_index.row())
        if not txn:
            return

        menu = QMenu(self)

        # View action
        view_action = QAction("View Details", self)
        view_action.triggered.connect(lambda: self.transaction_selected.emit(txn.id))
        menu.addAction(view_action)

        # Edit action
        edit_action = QAction("Edit", self)
        edit_action.setShortcut(QKeySequence("Enter"))
        edit_action.triggered.connect(lambda: self.edit_requested.emit(txn.id))
        menu.addAction(edit_action)

        menu.addSeparator()

        # Duplicate action
        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(lambda: self._duplicate_transaction(txn))
        menu.addAction(duplicate_action)

        menu.addSeparator()

        # Delete action
        delete_action = QAction("Delete", self)
        delete_action.setShortcut(QKeySequence("Delete"))
        delete_action.triggered.connect(lambda: self._delete_single(txn.id))
        menu.addAction(delete_action)

        menu.exec(self._table_view.viewport().mapToGlobal(position))

    def _select_all(self) -> None:
        """Select all visible transactions."""
        self._model.select_all()
        self._update_bulk_actions_bar()

    def _clear_selection(self) -> None:
        """Clear all selections."""
        self._model.clear_selection()
        self._table_view.clearSelection()
        self._update_bulk_actions_bar()

    def _update_bulk_actions_bar(self) -> None:
        """Update bulk actions bar based on selection."""
        count = len(self._model.get_selected_ids())
        self._bulk_actions_bar.update_selection(count)

    def _delete_selected(self) -> None:
        """Delete selected transactions."""
        selected_ids = self._model.get_selected_ids()
        if not selected_ids:
            return

        count = len(selected_ids)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {count} transaction{'s' if count != 1 else ''}?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._transactions = [t for t in self._transactions if t.id not in selected_ids]
            self._model.set_transactions(self._transactions)
            self._model.clear_selection()
            self._update_summary()
            self._update_bulk_actions_bar()
            self._pagination.set_total_items(len(self._transactions))
            self.data_changed.emit()

    def _delete_single(self, txn_id: int) -> None:
        """Delete a single transaction."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this transaction?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._transactions = [t for t in self._transactions if t.id != txn_id]
            self._model.set_transactions(self._transactions)
            self._update_summary()
            self._pagination.set_total_items(len(self._transactions))
            self.data_changed.emit()

    def _duplicate_transaction(self, txn: Transaction) -> None:
        """Duplicate a transaction for editing."""
        # Signal with negative ID to indicate duplicate
        self.edit_requested.emit(-txn.id)

    def _export_selected(self) -> None:
        """Export selected transactions."""
        selected_ids = self._model.get_selected_ids()
        if selected_ids:
            self.export_requested.emit(selected_ids)

    def _on_export(self) -> None:
        """Handle export button click."""
        selected_ids = self._model.get_selected_ids()

        if selected_ids:
            reply = QMessageBox.question(
                self,
                "Export Transactions",
                f"You have {len(selected_ids)} transactions selected.\n\n"
                "Export selected transactions only?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.export_requested.emit(selected_ids)
            else:
                # Export all filtered
                all_ids = [t.id for t in self._transactions if t.id is not None]
                self.export_requested.emit(all_ids)
        else:
            # Export all filtered
            all_ids = [t.id for t in self._transactions if t.id is not None]
            self.export_requested.emit(all_ids)

    def _on_page_changed(self, page: int) -> None:
        """Handle page change."""
        # Scroll to top
        self._table_view.scrollToTop()

    def _on_page_size_changed(self, size: int) -> None:
        """Handle page size change."""
        self._table_view.scrollToTop()

    def _update_summary(self) -> None:
        """Update summary bar with filtered transactions."""
        # Get filtered transactions
        filtered = []
        for row in range(self._proxy_model.rowCount()):
            source_index = self._proxy_model.mapToSource(self._proxy_model.index(row, 0))
            txn = self._model.get_transaction(source_index.row())
            if txn:
                filtered.append(txn)

        self._summary_bar.update_summary(filtered)

    def set_transactions(self, transactions: List[Transaction]) -> None:
        """Set the transaction list."""
        self._transactions = transactions
        self._model.set_transactions(transactions)
        self._model.clear_selection()

        # Extract categories for filter chips
        categories = sorted(set(t.category for t in transactions))
        self._filter_panel.set_categories(categories)

        # Apply current filter
        self._apply_filter(self._filter_panel.get_filter())

        # Update pagination
        self._pagination.set_total_items(self._proxy_model.rowCount())
        self._pagination.reset()

    def get_transaction_by_id(self, txn_id: int) -> Optional[Transaction]:
        """Get a transaction by ID."""
        return self._model.get_transaction_by_id(txn_id)

    def get_selected_ids(self) -> List[int]:
        """Get list of selected transaction IDs."""
        return self._model.get_selected_ids()

    def refresh(self) -> None:
        """Refresh the current view."""
        self._apply_filter(self._filter_panel.get_filter())


# Backwards compatibility alias
TransactionListPage = TransactionsPage
