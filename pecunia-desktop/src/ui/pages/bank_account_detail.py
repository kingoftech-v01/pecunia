"""
Bank Account Detail Dialog Module

Dialog for viewing detailed information about a linked bank account,
including recent transactions, sync history, and account management options.
"""

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QMessageBox,
    QSizePolicy, QSpacerItem, QProgressBar, QMenu, QLineEdit,
    QComboBox, QDialogButtonBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDateTime, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class ConnectionStatus(Enum):
    """Bank connection status states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SYNCING = "syncing"
    REQUIRES_REAUTH = "requires_reauth"


@dataclass
class TransactionItem:
    """Represents a transaction from a linked account."""
    id: str
    date: datetime
    description: str
    amount: float
    category: Optional[str] = None
    pending: bool = False
    merchant_name: Optional[str] = None


@dataclass
class SyncHistoryItem:
    """Represents a sync operation in history."""
    id: str
    timestamp: datetime
    status: str  # "success", "error", "partial"
    transactions_added: int = 0
    transactions_modified: int = 0
    transactions_removed: int = 0
    error_message: Optional[str] = None


@dataclass
class AccountDetails:
    """Full details of a bank account."""
    id: str
    name: str
    official_name: Optional[str]
    institution_name: str
    institution_id: Optional[str]
    type: str
    subtype: Optional[str]
    mask: Optional[str]
    current_balance: float
    available_balance: Optional[float]
    limit: Optional[float]
    currency: str
    status: ConnectionStatus
    last_synced: Optional[datetime]
    created_at: Optional[datetime]
    plaid_account_id: Optional[str] = None


class AccountInfoWidget(QFrame):
    """Widget displaying account information."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._account: Optional[AccountDetails] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the account info widget UI."""
        self.setObjectName("accountInfoWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame#accountInfoWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header with institution
        header_layout = QHBoxLayout()

        # Institution icon
        self.inst_icon = QLabel()
        self.inst_icon.setFixedSize(48, 48)
        self.inst_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inst_icon.setStyleSheet("""
            background-color: #1976D2;
            border-radius: 24px;
            color: white;
            font-size: 20px;
            font-weight: bold;
        """)
        header_layout.addWidget(self.inst_icon)

        # Institution and account name
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)

        self.inst_name_label = QLabel("Bank Name")
        self.inst_name_label.setFont(QFont("Segoe UI", 10))
        self.inst_name_label.setStyleSheet("color: #666666;")
        name_layout.addWidget(self.inst_name_label)

        self.account_name_label = QLabel("Account Name")
        self.account_name_label.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        self.account_name_label.setStyleSheet("color: #333333;")
        name_layout.addWidget(self.account_name_label)

        header_layout.addLayout(name_layout, 1)

        # Status badge
        self.status_badge = QLabel("Connected")
        self.status_badge.setFont(QFont("Segoe UI", 9))
        self.status_badge.setStyleSheet("""
            background-color: #E8F5E9;
            color: #4CAF50;
            border-radius: 4px;
            padding: 4px 12px;
        """)
        header_layout.addWidget(self.status_badge)

        layout.addLayout(header_layout)

        # Balance section
        balance_frame = QFrame()
        balance_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        balance_layout = QGridLayout(balance_frame)
        balance_layout.setSpacing(16)

        # Current balance
        current_title = QLabel("Current Balance")
        current_title.setFont(QFont("Segoe UI", 10))
        current_title.setStyleSheet("color: #666666;")
        balance_layout.addWidget(current_title, 0, 0)

        self.current_balance_label = QLabel("$0.00")
        self.current_balance_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.current_balance_label.setStyleSheet("color: #333333;")
        balance_layout.addWidget(self.current_balance_label, 1, 0)

        # Available balance
        available_title = QLabel("Available Balance")
        available_title.setFont(QFont("Segoe UI", 10))
        available_title.setStyleSheet("color: #666666;")
        balance_layout.addWidget(available_title, 0, 1)

        self.available_balance_label = QLabel("$0.00")
        self.available_balance_label.setFont(QFont("Segoe UI", 18))
        self.available_balance_label.setStyleSheet("color: #666666;")
        balance_layout.addWidget(self.available_balance_label, 1, 1)

        # Credit limit (for credit accounts)
        limit_title = QLabel("Credit Limit")
        limit_title.setFont(QFont("Segoe UI", 10))
        limit_title.setStyleSheet("color: #666666;")
        balance_layout.addWidget(limit_title, 0, 2)

        self.limit_label = QLabel("-")
        self.limit_label.setFont(QFont("Segoe UI", 18))
        self.limit_label.setStyleSheet("color: #666666;")
        balance_layout.addWidget(self.limit_label, 1, 2)

        layout.addWidget(balance_frame)

        # Account details grid
        details_layout = QGridLayout()
        details_layout.setSpacing(12)
        details_layout.setColumnStretch(1, 1)
        details_layout.setColumnStretch(3, 1)

        # Account type
        self._add_detail_row(details_layout, 0, 0, "Account Type", "type_value")

        # Account number (masked)
        self._add_detail_row(details_layout, 0, 2, "Account Number", "mask_value")

        # Currency
        self._add_detail_row(details_layout, 1, 0, "Currency", "currency_value")

        # Last synced
        self._add_detail_row(details_layout, 1, 2, "Last Synced", "sync_value")

        # Linked since
        self._add_detail_row(details_layout, 2, 0, "Linked Since", "linked_value")

        layout.addLayout(details_layout)

    def _add_detail_row(
        self,
        layout: QGridLayout,
        row: int,
        col: int,
        label: str,
        value_name: str
    ):
        """Add a detail row to the grid."""
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Segoe UI", 9))
        label_widget.setStyleSheet("color: #888888;")
        layout.addWidget(label_widget, row, col)

        value_widget = QLabel("-")
        value_widget.setFont(QFont("Segoe UI", 10))
        value_widget.setStyleSheet("color: #333333;")
        value_widget.setObjectName(value_name)
        layout.addWidget(value_widget, row, col + 1)

        # Store reference
        setattr(self, f"{value_name}_label", value_widget)

    def set_account(self, account: AccountDetails):
        """Set the account to display."""
        self._account = account

        # Update institution
        self.inst_icon.setText(account.institution_name[0].upper())
        self.inst_name_label.setText(account.institution_name)

        # Update account name
        display_name = account.name
        if account.mask:
            display_name += f" (****{account.mask})"
        self.account_name_label.setText(display_name)

        # Update status
        self._update_status_badge(account.status)

        # Update balances
        currency_symbol = self._get_currency_symbol(account.currency)

        balance_color = "#4CAF50" if account.current_balance >= 0 else "#F44336"
        self.current_balance_label.setText(
            f"{currency_symbol}{abs(account.current_balance):,.2f}"
        )
        if account.current_balance < 0:
            self.current_balance_label.setText(f"-{self.current_balance_label.text()}")
        self.current_balance_label.setStyleSheet(f"color: {balance_color};")

        if account.available_balance is not None:
            self.available_balance_label.setText(
                f"{currency_symbol}{account.available_balance:,.2f}"
            )
        else:
            self.available_balance_label.setText("-")

        if account.limit is not None:
            self.limit_label.setText(f"{currency_symbol}{account.limit:,.2f}")
        else:
            self.limit_label.setText("-")

        # Update details
        account_type = f"{account.type.replace('_', ' ').title()}"
        if account.subtype:
            account_type += f" - {account.subtype.replace('_', ' ').title()}"
        self.type_value_label.setText(account_type)

        self.mask_value_label.setText(f"****{account.mask}" if account.mask else "-")
        self.currency_value_label.setText(account.currency)

        if account.last_synced:
            self.sync_value_label.setText(
                account.last_synced.strftime("%b %d, %Y at %I:%M %p")
            )
        else:
            self.sync_value_label.setText("Never")

        if account.created_at:
            self.linked_value_label.setText(
                account.created_at.strftime("%b %d, %Y")
            )
        else:
            self.linked_value_label.setText("-")

    def _update_status_badge(self, status: ConnectionStatus):
        """Update the status badge."""
        status_styles = {
            ConnectionStatus.CONNECTED: ("#E8F5E9", "#4CAF50", "Connected"),
            ConnectionStatus.DISCONNECTED: ("#FAFAFA", "#9E9E9E", "Disconnected"),
            ConnectionStatus.ERROR: ("#FFEBEE", "#F44336", "Error"),
            ConnectionStatus.SYNCING: ("#E3F2FD", "#2196F3", "Syncing..."),
            ConnectionStatus.REQUIRES_REAUTH: ("#FFF3E0", "#FF9800", "Reauth Required"),
        }
        bg_color, text_color, text = status_styles.get(
            status, ("#FAFAFA", "#9E9E9E", "Unknown")
        )
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            border-radius: 4px;
            padding: 4px 12px;
        """)

    def _get_currency_symbol(self, currency: str) -> str:
        """Get currency symbol."""
        symbols = {
            "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3",
            "CAD": "C$", "JPY": "\u00a5", "AUD": "A$"
        }
        return symbols.get(currency, currency)


class RecentTransactionsWidget(QFrame):
    """Widget displaying recent transactions from the account."""

    transaction_clicked = pyqtSignal(str)  # Emits transaction ID

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._transactions: List[TransactionItem] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the transactions widget UI."""
        self.setObjectName("recentTransactionsWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Recent Transactions")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #333333;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.count_label = QLabel("0 transactions")
        self.count_label.setFont(QFont("Segoe UI", 10))
        self.count_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(self.count_label)

        layout.addLayout(header_layout)

        # Transactions table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Description", "Category", "Amount"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #F0F0F0;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #333333;
            }
            QHeaderView::section {
                background-color: #FAFAFA;
                color: #666666;
                font-weight: 600;
                padding: 10px 12px;
                border: none;
                border-bottom: 2px solid #E0E0E0;
            }
        """)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 100)

        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)

        layout.addWidget(self.table)

        # Empty state
        self.empty_label = QLabel("No recent transactions")
        self.empty_label.setFont(QFont("Segoe UI", 11))
        self.empty_label.setStyleSheet("color: #999999;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def set_transactions(self, transactions: List[TransactionItem]):
        """Set the transactions to display."""
        self._transactions = transactions
        self._refresh_table()

    def _refresh_table(self):
        """Refresh the transactions table."""
        self.table.setRowCount(0)

        if not self._transactions:
            self.table.setVisible(False)
            self.empty_label.setVisible(True)
            self.count_label.setText("0 transactions")
            return

        self.table.setVisible(True)
        self.empty_label.setVisible(False)
        self.count_label.setText(f"{len(self._transactions)} transactions")

        for transaction in self._transactions:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Date
            date_item = QTableWidgetItem(transaction.date.strftime("%b %d"))
            date_item.setData(Qt.ItemDataRole.UserRole, transaction.id)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, date_item)

            # Description
            desc_text = transaction.description
            if transaction.pending:
                desc_text = f"(Pending) {desc_text}"
            desc_item = QTableWidgetItem(desc_text)
            if transaction.pending:
                desc_item.setForeground(QColor("#999999"))
            self.table.setItem(row, 1, desc_item)

            # Category
            category_text = transaction.category or "Uncategorized"
            category_item = QTableWidgetItem(category_text)
            category_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, category_item)

            # Amount
            amount_text = f"${abs(transaction.amount):,.2f}"
            if transaction.amount < 0:
                amount_text = f"-{amount_text}"
            amount_item = QTableWidgetItem(amount_text)
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            amount_color = QColor("#4CAF50") if transaction.amount >= 0 else QColor("#F44336")
            amount_item.setForeground(amount_color)
            self.table.setItem(row, 3, amount_item)

        self.table.resizeRowsToContents()

    def _on_row_double_clicked(self, row: int, col: int):
        """Handle row double-click."""
        item = self.table.item(row, 0)
        if item:
            transaction_id = item.data(Qt.ItemDataRole.UserRole)
            self.transaction_clicked.emit(transaction_id)


class SyncHistoryWidget(QFrame):
    """Widget displaying sync history."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._history: List[SyncHistoryItem] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the sync history widget UI."""
        self.setObjectName("syncHistoryWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Sync History")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #333333;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # History list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
        """)

        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(8, 8, 8, 8)
        self.history_layout.setSpacing(8)

        scroll_area.setWidget(self.history_container)
        layout.addWidget(scroll_area)

        # Empty state
        self.empty_label = QLabel("No sync history available")
        self.empty_label.setFont(QFont("Segoe UI", 11))
        self.empty_label.setStyleSheet("color: #999999;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_history(self, history: List[SyncHistoryItem]):
        """Set the sync history to display."""
        self._history = history
        self._refresh_list()

    def _refresh_list(self):
        """Refresh the history list."""
        # Clear existing items
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._history:
            self.history_layout.addWidget(self.empty_label)
            return

        for sync_item in self._history:
            item_widget = self._create_history_item(sync_item)
            self.history_layout.addWidget(item_widget)

        self.history_layout.addStretch()

    def _create_history_item(self, item: SyncHistoryItem) -> QFrame:
        """Create a widget for a sync history item."""
        frame = QFrame()
        frame.setObjectName("syncHistoryItem")
        frame.setStyleSheet("""
            QFrame#syncHistoryItem {
                background-color: #FAFAFA;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Status icon
        status_icon = QLabel()
        status_icon.setFixedSize(32, 32)
        status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if item.status == "success":
            status_icon.setText("\u2713")
            status_icon.setStyleSheet("""
                background-color: #E8F5E9;
                color: #4CAF50;
                border-radius: 16px;
                font-weight: bold;
            """)
        elif item.status == "error":
            status_icon.setText("\u2717")
            status_icon.setStyleSheet("""
                background-color: #FFEBEE;
                color: #F44336;
                border-radius: 16px;
                font-weight: bold;
            """)
        else:
            status_icon.setText("!")
            status_icon.setStyleSheet("""
                background-color: #FFF3E0;
                color: #FF9800;
                border-radius: 16px;
                font-weight: bold;
            """)
        layout.addWidget(status_icon)

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Time
        time_label = QLabel(item.timestamp.strftime("%b %d, %Y at %I:%M %p"))
        time_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        time_label.setStyleSheet("color: #333333;")
        info_layout.addWidget(time_label)

        # Details
        if item.status == "success":
            details_text = f"+{item.transactions_added} added"
            if item.transactions_modified > 0:
                details_text += f", {item.transactions_modified} modified"
            if item.transactions_removed > 0:
                details_text += f", {item.transactions_removed} removed"
        elif item.error_message:
            details_text = item.error_message
        else:
            details_text = "Partial sync completed"

        details_label = QLabel(details_text)
        details_label.setFont(QFont("Segoe UI", 9))
        details_label.setStyleSheet("color: #666666;")
        info_layout.addWidget(details_label)

        layout.addLayout(info_layout, 1)

        return frame


class BankAccountDetailDialog(QDialog):
    """
    Dialog for viewing detailed bank account information.

    Features:
    - Account information display
    - Recent transactions list
    - Sync history
    - Account management (rename, disconnect)
    - Manual sync trigger

    Signals:
        sync_requested: Request to sync this account
        disconnect_requested: Request to disconnect this account
        renamed: Account was renamed
    """

    sync_requested = pyqtSignal(str)  # Emits account ID
    disconnect_requested = pyqtSignal(str)  # Emits account ID
    renamed = pyqtSignal(str, str)  # Emits account ID, new name

    def __init__(
        self,
        account_id: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._account_id = account_id
        self._account: Optional[AccountDetails] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Account Details")
        self.setMinimumSize(700, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Account info section
        self.account_info = AccountInfoWidget()
        layout.addWidget(self.account_info)

        # Tab widget for transactions and history
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                border-top-left-radius: 0;
            }
            QTabBar::tab {
                background-color: #F0F0F0;
                color: #666666;
                padding: 10px 20px;
                border: 1px solid #E0E0E0;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #1976D2;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #E8E8E8;
            }
        """)

        # Transactions tab
        self.transactions_widget = RecentTransactionsWidget()
        tab_widget.addTab(self.transactions_widget, "Recent Transactions")

        # Sync history tab
        self.sync_history_widget = SyncHistoryWidget()
        tab_widget.addTab(self.sync_history_widget, "Sync History")

        layout.addWidget(tab_widget, 1)

        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Sync button
        sync_btn = QPushButton("Sync Now")
        sync_btn.setFont(QFont("Segoe UI", 10))
        sync_btn.setMinimumSize(120, 40)
        sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        sync_btn.clicked.connect(self._on_sync_clicked)
        buttons_layout.addWidget(sync_btn)

        # Rename button
        rename_btn = QPushButton("Rename")
        rename_btn.setFont(QFont("Segoe UI", 10))
        rename_btn.setMinimumSize(100, 40)
        rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rename_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1976D2;
                border: 1px solid #1976D2;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #E3F2FD;
            }
        """)
        rename_btn.clicked.connect(self._on_rename_clicked)
        buttons_layout.addWidget(rename_btn)

        buttons_layout.addStretch()

        # Disconnect button
        disconnect_btn = QPushButton("Disconnect Account")
        disconnect_btn.setFont(QFont("Segoe UI", 10))
        disconnect_btn.setMinimumSize(150, 40)
        disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        disconnect_btn.setObjectName("dangerButton")
        disconnect_btn.setStyleSheet("""
            QPushButton#dangerButton {
                background-color: transparent;
                color: #F44336;
                border: 1px solid #F44336;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton#dangerButton:hover {
                background-color: #FFEBEE;
            }
        """)
        disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        buttons_layout.addWidget(disconnect_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont("Segoe UI", 10))
        close_btn.setMinimumSize(100, 40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def set_account(self, account: AccountDetails):
        """Set the account details to display."""
        self._account = account
        self.account_info.set_account(account)
        self.setWindowTitle(f"Account Details - {account.name}")

    def set_transactions(self, transactions: List[TransactionItem]):
        """Set the recent transactions."""
        self.transactions_widget.set_transactions(transactions)

    def set_sync_history(self, history: List[SyncHistoryItem]):
        """Set the sync history."""
        self.sync_history_widget.set_history(history)

    def _on_sync_clicked(self):
        """Handle sync button click."""
        self.sync_requested.emit(self._account_id)

    def _on_rename_clicked(self):
        """Handle rename button click."""
        if not self._account:
            return

        # Create a simple rename dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Rename Account")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        label = QLabel("Enter a new name for this account:")
        label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(label)

        name_input = QLineEdit()
        name_input.setText(self._account.name)
        name_input.setFont(QFont("Segoe UI", 11))
        name_input.setMinimumHeight(40)
        name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #1976D2;
            }
        """)
        name_input.selectAll()
        layout.addWidget(name_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = name_input.text().strip()
            if new_name and new_name != self._account.name:
                self.renamed.emit(self._account_id, new_name)
                self._account.name = new_name
                self.account_info.set_account(self._account)

    def _on_disconnect_clicked(self):
        """Handle disconnect button click."""
        if not self._account:
            return

        reply = QMessageBox.warning(
            self,
            "Disconnect Account",
            f"Are you sure you want to disconnect {self._account.name}?\n\n"
            "This will remove the connection to your bank. "
            "Your transaction history will be preserved, but no new "
            "transactions will be imported.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.disconnect_requested.emit(self._account_id)
            self.accept()


# Convenience function for creating the dialog
def create_account_detail_dialog(
    account_id: str,
    parent: Optional[QWidget] = None
) -> BankAccountDetailDialog:
    """Create and return a new BankAccountDetailDialog instance."""
    return BankAccountDetailDialog(account_id, parent)


# Helper function to create mock data for testing
def create_mock_account_details(account_id: str) -> AccountDetails:
    """Create mock account details for testing."""
    return AccountDetails(
        id=account_id,
        name="Primary Checking",
        official_name="Personal Checking Account",
        institution_name="Chase Bank",
        institution_id="chase",
        type="checking",
        subtype="personal",
        mask="1234",
        current_balance=5432.10,
        available_balance=5200.00,
        limit=None,
        currency="USD",
        status=ConnectionStatus.CONNECTED,
        last_synced=datetime.now() - timedelta(hours=2),
        created_at=datetime.now() - timedelta(days=30),
    )


def create_mock_transactions() -> List[TransactionItem]:
    """Create mock transactions for testing."""
    return [
        TransactionItem(
            id="txn_001",
            date=datetime.now() - timedelta(days=1),
            description="Grocery Store",
            amount=-85.32,
            category="Groceries",
            pending=False,
        ),
        TransactionItem(
            id="txn_002",
            date=datetime.now() - timedelta(days=2),
            description="Direct Deposit - Payroll",
            amount=2500.00,
            category="Income",
            pending=False,
        ),
        TransactionItem(
            id="txn_003",
            date=datetime.now(),
            description="Coffee Shop",
            amount=-5.75,
            category="Food & Drink",
            pending=True,
        ),
        TransactionItem(
            id="txn_004",
            date=datetime.now() - timedelta(days=3),
            description="Electric Company",
            amount=-145.00,
            category="Utilities",
            pending=False,
        ),
    ]


def create_mock_sync_history() -> List[SyncHistoryItem]:
    """Create mock sync history for testing."""
    return [
        SyncHistoryItem(
            id="sync_001",
            timestamp=datetime.now() - timedelta(hours=2),
            status="success",
            transactions_added=3,
            transactions_modified=1,
            transactions_removed=0,
        ),
        SyncHistoryItem(
            id="sync_002",
            timestamp=datetime.now() - timedelta(days=1),
            status="success",
            transactions_added=5,
            transactions_modified=0,
            transactions_removed=0,
        ),
        SyncHistoryItem(
            id="sync_003",
            timestamp=datetime.now() - timedelta(days=2),
            status="error",
            error_message="Connection timeout - please try again",
        ),
    ]
