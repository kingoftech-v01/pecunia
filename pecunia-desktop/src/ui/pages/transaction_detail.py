"""
Transaction detail dialog for viewing and editing transaction information.

Provides TransactionDetailDialog with view/edit modes, attachments management,
and transaction history tracking.

Features:
- View mode with formatted display
- Edit mode with inline editing
- Attachments viewer and upload
- Transaction history timeline
- Split transaction support
- Related transactions display
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QTabWidget,
    QSizePolicy, QFileDialog, QMessageBox, QMenu, QToolButton,
    QListWidget, QListWidgetItem, QStackedWidget, QTextEdit,
    QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpacerItem
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QDate, QSize, QUrl, QMimeData, QTimer
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QPainter, QPen, QBrush,
    QPixmap, QDragEnterEvent, QDropEvent, QDesktopServices
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
class Attachment:
    """Transaction attachment data."""
    id: int
    filename: str
    file_type: str
    file_size: int
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    uploaded_at: Optional[datetime] = None


@dataclass
class HistoryEntry:
    """Transaction history entry."""
    id: int
    action: str  # created, updated, deleted, categorized, etc.
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    user_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    note: Optional[str] = None


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
    attachments: Optional[List[Attachment]] = None
    merchant: Optional[str] = None
    location: Optional[str] = None
    sync_status: SyncStatus = SyncStatus.SYNCED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    history: Optional[List[HistoryEntry]] = None


# =============================================================================
# Info Row Widget
# =============================================================================

class InfoRow(QWidget):
    """Widget for displaying a label-value pair."""

    def __init__(
        self,
        label: str,
        value: str = "",
        is_amount: bool = False,
        is_positive: Optional[bool] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._label = label
        self._is_amount = is_amount
        self._is_positive = is_positive
        self._setup_ui(value)

    def _setup_ui(self, value: str) -> None:
        """Set up the info row UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(16)

        # Label
        self._label_widget = QLabel(self._label)
        self._label_widget.setStyleSheet("color: #757575; font-size: 13px;")
        self._label_widget.setMinimumWidth(100)
        layout.addWidget(self._label_widget)

        # Value
        self._value_widget = QLabel(value)
        self._value_widget.setStyleSheet("font-size: 13px;")
        self._value_widget.setWordWrap(True)

        if self._is_amount and self._is_positive is not None:
            if self._is_positive:
                self._value_widget.setStyleSheet("font-size: 13px; color: #4CAF50; font-weight: bold;")
            else:
                self._value_widget.setStyleSheet("font-size: 13px; color: #F44336; font-weight: bold;")

        layout.addWidget(self._value_widget, 1)

    def set_value(self, value: str, is_positive: Optional[bool] = None) -> None:
        """Set the display value."""
        self._value_widget.setText(value)

        if self._is_amount and is_positive is not None:
            self._is_positive = is_positive
            if is_positive:
                self._value_widget.setStyleSheet("font-size: 13px; color: #4CAF50; font-weight: bold;")
            else:
                self._value_widget.setStyleSheet("font-size: 13px; color: #F44336; font-weight: bold;")


# =============================================================================
# Tag Chip Widget
# =============================================================================

class TagChip(QFrame):
    """Small tag display chip."""

    removed = pyqtSignal(str)

    def __init__(self, tag: str, removable: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._tag = tag
        self._removable = removable
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tag chip UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border: 1px solid #90CAF9;
                border-radius: 12px;
                padding: 2px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8 if not self._removable else 4, 2)
        layout.setSpacing(4)

        label = QLabel(self._tag)
        label.setStyleSheet("color: #1565C0; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(label)

        if self._removable:
            remove_btn = QToolButton()
            remove_btn.setText("\u00D7")
            remove_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    color: #1565C0;
                    font-size: 14px;
                    padding: 0;
                }
                QToolButton:hover {
                    color: #C62828;
                }
            """)
            remove_btn.setFixedSize(16, 16)
            remove_btn.clicked.connect(lambda: self.removed.emit(self._tag))
            layout.addWidget(remove_btn)

    @property
    def tag(self) -> str:
        return self._tag


# =============================================================================
# Attachment Item Widget
# =============================================================================

class AttachmentItem(QFrame):
    """Widget for displaying a single attachment."""

    view_requested = pyqtSignal(Attachment)
    download_requested = pyqtSignal(Attachment)
    delete_requested = pyqtSignal(Attachment)

    FILE_ICONS = {
        "pdf": "\U0001F4C4",
        "doc": "\U0001F4C3",
        "docx": "\U0001F4C3",
        "xls": "\U0001F4CA",
        "xlsx": "\U0001F4CA",
        "jpg": "\U0001F5BC",
        "jpeg": "\U0001F5BC",
        "png": "\U0001F5BC",
        "gif": "\U0001F5BC",
        "default": "\U0001F4CE"
    }

    def __init__(self, attachment: Attachment, editable: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._attachment = attachment
        self._editable = editable
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the attachment item UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #F5F5F5;
                border-color: #BDBDBD;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # File icon
        ext = self._attachment.file_type.lower().replace(".", "")
        icon = self.FILE_ICONS.get(ext, self.FILE_ICONS["default"])
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px; background: transparent; border: none;")
        layout.addWidget(icon_label)

        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(self._attachment.filename)
        name_label.setStyleSheet("font-weight: 500; background: transparent; border: none;")
        info_layout.addWidget(name_label)

        size_str = self._format_size(self._attachment.file_size)
        size_label = QLabel(size_str)
        size_label.setStyleSheet("color: #757575; font-size: 11px; background: transparent; border: none;")
        info_layout.addWidget(size_label)

        layout.addLayout(info_layout, 1)

        # Actions
        if self._editable:
            delete_btn = QToolButton()
            delete_btn.setText("\U0001F5D1")
            delete_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    font-size: 16px;
                }
                QToolButton:hover {
                    color: #C62828;
                }
            """)
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._attachment))
            layout.addWidget(delete_btn)

    def _format_size(self, size: int) -> str:
        """Format file size for display."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def mousePressEvent(self, event) -> None:
        """Handle click to view attachment."""
        self.view_requested.emit(self._attachment)
        super().mousePressEvent(event)


# =============================================================================
# Attachments Panel
# =============================================================================

class AttachmentsPanel(QFrame):
    """Panel for managing transaction attachments."""

    attachment_added = pyqtSignal(str)  # file path
    attachment_removed = pyqtSignal(Attachment)
    attachment_viewed = pyqtSignal(Attachment)

    def __init__(self, editable: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._editable = editable
        self._attachments: List[Attachment] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the attachments panel UI."""
        self.setAcceptDrops(self._editable)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Attachments")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        if self._editable:
            add_btn = QPushButton("+ Add File")
            add_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #1976D2;
                    border: 1px solid #1976D2;
                    border-radius: 4px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #E3F2FD;
                }
            """)
            add_btn.clicked.connect(self._on_add_clicked)
            header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Attachments list container
        self._list_container = QVBoxLayout()
        self._list_container.setSpacing(8)
        layout.addLayout(self._list_container)

        # Empty state / drop zone
        self._empty_label = QLabel("No attachments")
        self._empty_label.setStyleSheet("color: #757575; padding: 20px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_container.addWidget(self._empty_label)

        if self._editable:
            self._drop_zone = QFrame()
            self._drop_zone.setStyleSheet("""
                QFrame {
                    background-color: #FAFAFA;
                    border: 2px dashed #BDBDBD;
                    border-radius: 8px;
                    min-height: 80px;
                }
            """)
            drop_layout = QVBoxLayout(self._drop_zone)
            drop_label = QLabel("Drag & drop files here")
            drop_label.setStyleSheet("color: #757575;")
            drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            drop_layout.addWidget(drop_label)
            layout.addWidget(self._drop_zone)

    def _on_add_clicked(self) -> None:
        """Handle add attachment button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "All Files (*);;Images (*.png *.jpg *.jpeg *.gif);;Documents (*.pdf *.doc *.docx);;Spreadsheets (*.xls *.xlsx)"
        )
        if file_path:
            self.attachment_added.emit(file_path)

    def set_attachments(self, attachments: List[Attachment]) -> None:
        """Set the attachments list."""
        self._attachments = attachments

        # Clear existing items
        while self._list_container.count():
            item = self._list_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if attachments:
            for attachment in attachments:
                item = AttachmentItem(attachment, self._editable)
                item.view_requested.connect(self.attachment_viewed.emit)
                item.delete_requested.connect(self.attachment_removed.emit)
                self._list_container.addWidget(item)
        else:
            self._list_container.addWidget(self._empty_label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter for file drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drop_zone.setStyleSheet("""
                QFrame {
                    background-color: #E3F2FD;
                    border: 2px dashed #1976D2;
                    border-radius: 8px;
                    min-height: 80px;
                }
            """)

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave."""
        self._drop_zone.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
                min-height: 80px;
            }
        """)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle file drop."""
        self._drop_zone.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 2px dashed #BDBDBD;
                border-radius: 8px;
                min-height: 80px;
            }
        """)

        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.attachment_added.emit(url.toLocalFile())


# =============================================================================
# History Timeline
# =============================================================================

class HistoryTimeline(QWidget):
    """Timeline widget for transaction history."""

    ACTION_ICONS = {
        "created": "\U00002795",
        "updated": "\u270F",
        "deleted": "\U0001F5D1",
        "categorized": "\U0001F3F7",
        "split": "\u2702",
        "merged": "\U0001F517",
        "imported": "\U0001F4E5",
        "exported": "\U0001F4E4",
    }

    ACTION_COLORS = {
        "created": "#4CAF50",
        "updated": "#2196F3",
        "deleted": "#F44336",
        "categorized": "#9C27B0",
        "split": "#FF9800",
        "merged": "#00BCD4",
        "imported": "#607D8B",
        "exported": "#607D8B",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._history: List[HistoryEntry] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the history timeline UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        title = QLabel("History")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addSpacing(12)

        # Timeline container
        self._timeline_container = QVBoxLayout()
        self._timeline_container.setSpacing(0)
        layout.addLayout(self._timeline_container)

        # Empty state
        self._empty_label = QLabel("No history available")
        self._empty_label.setStyleSheet("color: #757575; padding: 20px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timeline_container.addWidget(self._empty_label)

        layout.addStretch()

    def set_history(self, history: List[HistoryEntry]) -> None:
        """Set the history entries."""
        self._history = history

        # Clear existing
        while self._timeline_container.count():
            item = self._timeline_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not history:
            self._timeline_container.addWidget(self._empty_label)
            return

        for i, entry in enumerate(sorted(history, key=lambda x: x.timestamp or datetime.min, reverse=True)):
            is_last = i == len(history) - 1
            item = self._create_history_item(entry, is_last)
            self._timeline_container.addWidget(item)

    def _create_history_item(self, entry: HistoryEntry, is_last: bool) -> QWidget:
        """Create a history timeline item."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Timeline line and dot
        timeline_widget = QWidget()
        timeline_widget.setFixedWidth(24)
        timeline_layout = QVBoxLayout(timeline_widget)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(0)

        # Dot
        color = self.ACTION_COLORS.get(entry.action, "#9E9E9E")
        dot = QLabel()
        dot.setFixedSize(12, 12)
        dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
        """)
        timeline_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignHCenter)

        # Line (unless last item)
        if not is_last:
            line = QFrame()
            line.setFrameShape(QFrame.Shape.VLine)
            line.setStyleSheet("background-color: #E0E0E0;")
            line.setFixedWidth(2)
            timeline_layout.addWidget(line, 1, Qt.AlignmentFlag.AlignHCenter)
        else:
            timeline_layout.addStretch()

        layout.addWidget(timeline_widget)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 16)

        # Action description
        icon = self.ACTION_ICONS.get(entry.action, "\u2022")
        action_text = entry.action.replace("_", " ").capitalize()

        if entry.field_changed:
            action_label = QLabel(f"{icon} {action_text}: {entry.field_changed}")
        else:
            action_label = QLabel(f"{icon} {action_text}")

        action_label.setStyleSheet("font-weight: 500;")
        content_layout.addWidget(action_label)

        # Changes detail
        if entry.old_value or entry.new_value:
            change_text = ""
            if entry.old_value and entry.new_value:
                change_text = f'"{entry.old_value}" -> "{entry.new_value}"'
            elif entry.new_value:
                change_text = f'Set to "{entry.new_value}"'
            elif entry.old_value:
                change_text = f'Removed "{entry.old_value}"'

            change_label = QLabel(change_text)
            change_label.setStyleSheet("color: #757575; font-size: 12px;")
            change_label.setWordWrap(True)
            content_layout.addWidget(change_label)

        # Note
        if entry.note:
            note_label = QLabel(entry.note)
            note_label.setStyleSheet("color: #757575; font-size: 12px; font-style: italic;")
            note_label.setWordWrap(True)
            content_layout.addWidget(note_label)

        # Timestamp and user
        meta_parts = []
        if entry.timestamp:
            meta_parts.append(entry.timestamp.strftime("%b %d, %Y at %I:%M %p"))
        if entry.user_name:
            meta_parts.append(f"by {entry.user_name}")

        if meta_parts:
            meta_label = QLabel(" ".join(meta_parts))
            meta_label.setStyleSheet("color: #9E9E9E; font-size: 11px;")
            content_layout.addWidget(meta_label)

        layout.addLayout(content_layout, 1)

        return container


# =============================================================================
# Related Transactions Widget
# =============================================================================

class RelatedTransactionsWidget(QWidget):
    """Widget for displaying related transactions."""

    transaction_clicked = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._transactions: List[Transaction] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the related transactions UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        title = QLabel("Related Transactions")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # List
        self._list_widget = QListWidget()
        self._list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EEEEEE;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
            }
        """)
        self._list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list_widget)

        # Empty state
        self._empty_label = QLabel("No related transactions found")
        self._empty_label.setStyleSheet("color: #757575; padding: 20px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

    def set_transactions(self, transactions: List[Transaction]) -> None:
        """Set the related transactions."""
        self._transactions = transactions
        self._list_widget.clear()

        if not transactions:
            self._list_widget.hide()
            self._empty_label.show()
            return

        self._list_widget.show()
        self._empty_label.hide()

        for txn in transactions:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, txn.id)

            # Format display text
            type_color = {
                TransactionType.INCOME: "#4CAF50",
                TransactionType.EXPENSE: "#F44336",
                TransactionType.TRANSFER: "#2196F3"
            }.get(txn.type, "#757575")

            amount_str = f"${txn.amount:,.2f}"
            if txn.type == TransactionType.EXPENSE:
                amount_str = f"-{amount_str}"

            text = f"{txn.date.strftime('%b %d')} - {txn.description}\n{txn.category} | {amount_str}"
            item.setText(text)

            self._list_widget.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item click."""
        txn_id = item.data(Qt.ItemDataRole.UserRole)
        if txn_id:
            self.transaction_clicked.emit(txn_id)


# =============================================================================
# Transaction Detail Dialog
# =============================================================================

class TransactionDetailDialog(QDialog):
    """
    Dialog for viewing and editing transaction details.

    Features:
    - View mode with formatted display
    - Edit mode with inline editing
    - Attachments management
    - Transaction history timeline
    - Related transactions

    Signals:
        saved(Transaction): Emitted when transaction is saved
        deleted(int): Emitted when transaction is deleted
        edit_requested(int): Emitted when edit button is clicked
    """

    saved = pyqtSignal(object)
    deleted = pyqtSignal(int)
    edit_requested = pyqtSignal(int)

    def __init__(
        self,
        transaction: Optional[Transaction] = None,
        editable: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._transaction = transaction
        self._editable = editable
        self._setup_ui()
        if transaction:
            self._load_transaction(transaction)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Transaction Details")
        self.setMinimumSize(700, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1976D2;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(8)

        # Title row
        title_row = QHBoxLayout()

        self._type_badge = QLabel()
        self._type_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        """)
        title_row.addWidget(self._type_badge)

        title_row.addStretch()

        close_btn = QPushButton("\u00D7")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                font-size: 24px;
                padding: 0;
            }
            QPushButton:hover {
                color: #FFCDD2;
            }
        """)
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.close)
        title_row.addWidget(close_btn)

        header_layout.addLayout(title_row)

        # Amount
        self._amount_label = QLabel()
        self._amount_label.setStyleSheet("color: white; font-size: 32px; font-weight: bold;")
        header_layout.addWidget(self._amount_label)

        # Description
        self._description_label = QLabel()
        self._description_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-size: 16px;")
        self._description_label.setWordWrap(True)
        header_layout.addWidget(self._description_label)

        layout.addWidget(header)

        # Content area with tabs
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # Tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #F5F5F5;
                padding: 8px 16px;
                border: 1px solid #E0E0E0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #1976D2;
            }
        """)

        # Details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(8)

        self._date_row = InfoRow("Date")
        details_layout.addWidget(self._date_row)

        self._category_row = InfoRow("Category")
        details_layout.addWidget(self._category_row)

        self._account_row = InfoRow("Account")
        details_layout.addWidget(self._account_row)

        self._merchant_row = InfoRow("Merchant")
        details_layout.addWidget(self._merchant_row)

        self._location_row = InfoRow("Location")
        details_layout.addWidget(self._location_row)

        # Tags
        tags_label = QLabel("Tags")
        tags_label.setStyleSheet("color: #757575; font-size: 13px; margin-top: 8px;")
        details_layout.addWidget(tags_label)

        self._tags_container = QHBoxLayout()
        self._tags_container.setSpacing(6)
        details_layout.addLayout(self._tags_container)

        # Notes
        notes_label = QLabel("Notes")
        notes_label.setStyleSheet("color: #757575; font-size: 13px; margin-top: 8px;")
        details_layout.addWidget(notes_label)

        self._notes_display = QLabel()
        self._notes_display.setStyleSheet("""
            background-color: #FAFAFA;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            padding: 12px;
        """)
        self._notes_display.setWordWrap(True)
        self._notes_display.setMinimumHeight(60)
        details_layout.addWidget(self._notes_display)

        # Sync status
        self._sync_status_row = InfoRow("Sync Status")
        details_layout.addWidget(self._sync_status_row)

        details_layout.addStretch()

        self._tab_widget.addTab(details_tab, "Details")

        # Attachments tab
        attachments_tab = QWidget()
        attachments_layout = QVBoxLayout(attachments_tab)
        attachments_layout.setContentsMargins(16, 16, 16, 16)

        self._attachments_panel = AttachmentsPanel(self._editable)
        attachments_layout.addWidget(self._attachments_panel)

        self._tab_widget.addTab(attachments_tab, "Attachments")

        # History tab
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(16, 16, 16, 16)

        self._history_timeline = HistoryTimeline()
        history_layout.addWidget(self._history_timeline)

        self._tab_widget.addTab(history_tab, "History")

        content_layout.addWidget(self._tab_widget)

        layout.addWidget(content, 1)

        # Footer with actions
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border-top: 1px solid #E0E0E0;
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)
        footer_layout.setSpacing(12)

        # Delete button
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #C62828;
                border: 1px solid #C62828;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #FFEBEE;
            }
        """)
        self._delete_btn.clicked.connect(self._on_delete)
        footer_layout.addWidget(self._delete_btn)

        footer_layout.addStretch()

        # Edit button
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setStyleSheet("""
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
        """)
        self._edit_btn.clicked.connect(self._on_edit)
        footer_layout.addWidget(self._edit_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        close_btn.clicked.connect(self.close)
        footer_layout.addWidget(close_btn)

        layout.addWidget(footer)

    def _load_transaction(self, txn: Transaction) -> None:
        """Load transaction data into the dialog."""
        self._transaction = txn

        # Header
        type_text = txn.type.value.upper()
        self._type_badge.setText(type_text)

        amount_str = f"${txn.amount:,.2f}"
        if txn.type == TransactionType.EXPENSE:
            amount_str = f"-{amount_str}"
        elif txn.type == TransactionType.INCOME:
            amount_str = f"+{amount_str}"
        self._amount_label.setText(amount_str)

        self._description_label.setText(txn.description)

        # Details
        self._date_row.set_value(txn.date.strftime("%B %d, %Y"))
        self._category_row.set_value(txn.category)
        self._account_row.set_value(txn.account)
        self._merchant_row.set_value(txn.merchant or "-")
        self._location_row.set_value(txn.location or "-")

        # Tags
        while self._tags_container.count():
            item = self._tags_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if txn.tags:
            for tag in txn.tags:
                chip = TagChip(tag)
                self._tags_container.addWidget(chip)
        else:
            no_tags = QLabel("No tags")
            no_tags.setStyleSheet("color: #757575;")
            self._tags_container.addWidget(no_tags)

        self._tags_container.addStretch()

        # Notes
        self._notes_display.setText(txn.notes or "No notes")

        # Sync status
        status_text = txn.sync_status.value.capitalize()
        status_colors = {
            SyncStatus.SYNCED: "#4CAF50",
            SyncStatus.PENDING: "#FF9800",
            SyncStatus.CONFLICT: "#F44336",
            SyncStatus.ERROR: "#F44336",
        }
        color = status_colors.get(txn.sync_status, "#757575")
        self._sync_status_row.set_value(f'<span style="color: {color};">{status_text}</span>')

        # Attachments
        self._attachments_panel.set_attachments(txn.attachments or [])

        # History
        self._history_timeline.set_history(txn.history or [])

    def _on_edit(self) -> None:
        """Handle edit button click."""
        if self._transaction and self._transaction.id:
            self.edit_requested.emit(self._transaction.id)
            self.close()

    def _on_delete(self) -> None:
        """Handle delete button click."""
        if not self._transaction or not self._transaction.id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this transaction?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.deleted.emit(self._transaction.id)
            self.close()

    def set_transaction(self, transaction: Transaction) -> None:
        """Set/update the transaction being displayed."""
        self._load_transaction(transaction)

    @property
    def transaction(self) -> Optional[Transaction]:
        """Get the current transaction."""
        return self._transaction
