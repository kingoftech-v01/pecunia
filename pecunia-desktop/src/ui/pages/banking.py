"""
Banking Page Module

Main banking page displaying linked bank accounts, balances, and sync controls.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QSizePolicy, QSpacerItem, QProgressBar, QMenu,
    QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QIcon, QCursor
from typing import Optional, Dict, Any, List, Callable
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class ConnectionStatus(Enum):
    """Bank connection status states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SYNCING = "syncing"
    REQUIRES_REAUTH = "requires_reauth"


class BankAccountCard(QFrame):
    """A card widget displaying a single bank account with balance."""

    clicked = pyqtSignal(str)  # Emits account ID
    sync_requested = pyqtSignal(str)  # Emits account ID
    disconnect_requested = pyqtSignal(str)  # Emits account ID

    def __init__(
        self,
        account_id: str,
        account_name: str,
        institution_name: str,
        account_type: str,
        balance: float,
        currency: str = "USD",
        mask: Optional[str] = None,
        status: ConnectionStatus = ConnectionStatus.CONNECTED,
        last_synced: Optional[datetime] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.account_id = account_id
        self._status = status
        self._balance = balance
        self._currency = currency
        self._setup_ui(
            account_name, institution_name, account_type,
            balance, currency, mask, status, last_synced
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(
        self,
        account_name: str,
        institution_name: str,
        account_type: str,
        balance: float,
        currency: str,
        mask: Optional[str],
        status: ConnectionStatus,
        last_synced: Optional[datetime]
    ):
        """Set up the account card UI."""
        self.setObjectName("bankAccountCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(280, 160)
        self.setMaximumHeight(180)

        status_color = self._get_status_color(status)

        self.setStyleSheet(f"""
            QFrame#bankAccountCard {{
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                border-left: 4px solid {status_color};
            }}
            QFrame#bankAccountCard:hover {{
                background-color: #FAFAFA;
                border-color: #BDBDBD;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header row: Institution and status
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Institution icon placeholder
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setStyleSheet(f"""
            background-color: {self._get_institution_color(institution_name)};
            border-radius: 16px;
            color: white;
            font-weight: bold;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText(institution_name[0].upper() if institution_name else "B")
        header_layout.addWidget(icon_label)

        # Institution name
        institution_label = QLabel(institution_name)
        institution_label.setFont(QFont("Segoe UI", 10))
        institution_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(institution_label)

        header_layout.addStretch()

        # Status indicator
        self.status_indicator = QLabel()
        self._update_status_indicator(status)
        header_layout.addWidget(self.status_indicator)

        # Menu button
        menu_btn = QPushButton()
        menu_btn.setFixedSize(24, 24)
        menu_btn.setText("...")
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #999999;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
                border-radius: 12px;
            }
        """)
        menu_btn.clicked.connect(self._show_context_menu)
        header_layout.addWidget(menu_btn)

        layout.addLayout(header_layout)

        # Account name and type
        name_layout = QHBoxLayout()
        display_name = f"{account_name}"
        if mask:
            display_name += f" (****{mask})"

        self.name_label = QLabel(display_name)
        self.name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.name_label.setStyleSheet("color: #333333;")
        name_layout.addWidget(self.name_label)

        type_label = QLabel(account_type.replace("_", " ").title())
        type_label.setFont(QFont("Segoe UI", 9))
        type_label.setStyleSheet("""
            color: #888888;
            background-color: #F0F0F0;
            border-radius: 4px;
            padding: 2px 8px;
        """)
        name_layout.addWidget(type_label)
        name_layout.addStretch()

        layout.addLayout(name_layout)

        # Balance
        balance_color = "#4CAF50" if balance >= 0 else "#F44336"
        currency_symbol = self._get_currency_symbol(currency)
        formatted_balance = f"{currency_symbol}{abs(balance):,.2f}"
        if balance < 0:
            formatted_balance = f"-{formatted_balance}"

        self.balance_label = QLabel(formatted_balance)
        self.balance_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.balance_label.setStyleSheet(f"color: {balance_color};")
        layout.addWidget(self.balance_label)

        # Last synced
        sync_text = "Never synced"
        if last_synced:
            sync_text = f"Last synced: {self._format_relative_time(last_synced)}"

        self.sync_label = QLabel(sync_text)
        self.sync_label.setFont(QFont("Segoe UI", 9))
        self.sync_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.sync_label)

        layout.addStretch()

    def _get_status_color(self, status: ConnectionStatus) -> str:
        """Get color for connection status."""
        colors = {
            ConnectionStatus.CONNECTED: "#4CAF50",
            ConnectionStatus.DISCONNECTED: "#9E9E9E",
            ConnectionStatus.ERROR: "#F44336",
            ConnectionStatus.SYNCING: "#2196F3",
            ConnectionStatus.REQUIRES_REAUTH: "#FF9800",
        }
        return colors.get(status, "#9E9E9E")

    def _get_institution_color(self, name: str) -> str:
        """Generate a consistent color for institution."""
        colors = [
            "#1976D2", "#388E3C", "#D32F2F", "#7B1FA2",
            "#C2185B", "#0097A7", "#FFA000", "#5D4037"
        ]
        hash_val = sum(ord(c) for c in name)
        return colors[hash_val % len(colors)]

    def _get_currency_symbol(self, currency: str) -> str:
        """Get currency symbol."""
        symbols = {
            "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3",
            "CAD": "C$", "JPY": "\u00a5", "AUD": "A$"
        }
        return symbols.get(currency, currency)

    def _format_relative_time(self, dt: datetime) -> str:
        """Format datetime as relative time string."""
        now = datetime.now()
        diff = now - dt

        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")

    def _update_status_indicator(self, status: ConnectionStatus):
        """Update the status indicator."""
        status_colors = {
            ConnectionStatus.CONNECTED: ("#4CAF50", "Connected"),
            ConnectionStatus.DISCONNECTED: ("#9E9E9E", "Disconnected"),
            ConnectionStatus.ERROR: ("#F44336", "Error"),
            ConnectionStatus.SYNCING: ("#2196F3", "Syncing..."),
            ConnectionStatus.REQUIRES_REAUTH: ("#FF9800", "Reauth needed"),
        }
        color, text = status_colors.get(status, ("#9E9E9E", "Unknown"))
        self.status_indicator.setText(text)
        self.status_indicator.setFont(QFont("Segoe UI", 9))
        self.status_indicator.setStyleSheet(f"""
            color: {color};
            background-color: {color}20;
            border-radius: 4px;
            padding: 2px 8px;
        """)

    def _show_context_menu(self):
        """Show context menu for account actions."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
            }
        """)

        sync_action = menu.addAction("Sync Now")
        sync_action.triggered.connect(lambda: self.sync_requested.emit(self.account_id))

        view_action = menu.addAction("View Details")
        view_action.triggered.connect(lambda: self.clicked.emit(self.account_id))

        menu.addSeparator()

        if self._status == ConnectionStatus.REQUIRES_REAUTH:
            reauth_action = menu.addAction("Reconnect Account")
            reauth_action.triggered.connect(lambda: self.clicked.emit(self.account_id))

        disconnect_action = menu.addAction("Disconnect")
        disconnect_action.triggered.connect(
            lambda: self.disconnect_requested.emit(self.account_id)
        )

        menu.exec(QCursor.pos())

    def update_balance(self, balance: float):
        """Update the displayed balance."""
        self._balance = balance
        balance_color = "#4CAF50" if balance >= 0 else "#F44336"
        currency_symbol = self._get_currency_symbol(self._currency)
        formatted_balance = f"{currency_symbol}{abs(balance):,.2f}"
        if balance < 0:
            formatted_balance = f"-{formatted_balance}"
        self.balance_label.setText(formatted_balance)
        self.balance_label.setStyleSheet(f"color: {balance_color};")

    def update_status(self, status: ConnectionStatus):
        """Update the connection status."""
        self._status = status
        self._update_status_indicator(status)
        self.setStyleSheet(self.styleSheet().replace(
            "border-left: 4px solid",
            f"border-left: 4px solid {self._get_status_color(status)}"
        ))

    def update_last_synced(self, last_synced: datetime):
        """Update the last synced time."""
        self.sync_label.setText(f"Last synced: {self._format_relative_time(last_synced)}")

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.account_id)
        super().mousePressEvent(event)


class TotalBalanceCard(QFrame):
    """Card displaying total aggregated balance across all accounts."""

    def __init__(
        self,
        total_balance: float = 0.0,
        total_assets: float = 0.0,
        total_liabilities: float = 0.0,
        currency: str = "USD",
        account_count: int = 0,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._currency = currency
        self._setup_ui(total_balance, total_assets, total_liabilities, account_count)

    def _setup_ui(
        self,
        total_balance: float,
        total_assets: float,
        total_liabilities: float,
        account_count: int
    ):
        """Set up the total balance card UI."""
        self.setObjectName("totalBalanceCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(140)
        self.setStyleSheet("""
            QFrame#totalBalanceCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1976D2, stop:1 #1565C0
                );
                border: none;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Total Net Worth")
        title_label.setFont(QFont("Segoe UI", 12))
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        accounts_label = QLabel(f"{account_count} accounts")
        accounts_label.setFont(QFont("Segoe UI", 10))
        accounts_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.7);
            background-color: rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 4px 12px;
        """)
        header_layout.addWidget(accounts_label)

        layout.addLayout(header_layout)

        # Total balance
        currency_symbol = self._get_currency_symbol(self._currency)
        formatted_total = f"{currency_symbol}{abs(total_balance):,.2f}"
        if total_balance < 0:
            formatted_total = f"-{formatted_total}"

        self.total_label = QLabel(formatted_total)
        self.total_label.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        self.total_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(self.total_label)

        # Assets and liabilities breakdown
        breakdown_layout = QHBoxLayout()
        breakdown_layout.setSpacing(24)

        # Assets
        assets_widget = QWidget()
        assets_layout = QVBoxLayout(assets_widget)
        assets_layout.setContentsMargins(0, 0, 0, 0)
        assets_layout.setSpacing(2)

        assets_title = QLabel("Assets")
        assets_title.setFont(QFont("Segoe UI", 9))
        assets_title.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        assets_layout.addWidget(assets_title)

        self.assets_label = QLabel(f"{currency_symbol}{total_assets:,.2f}")
        self.assets_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        self.assets_label.setStyleSheet("color: #A5D6A7;")
        assets_layout.addWidget(self.assets_label)

        breakdown_layout.addWidget(assets_widget)

        # Liabilities
        liabilities_widget = QWidget()
        liabilities_layout = QVBoxLayout(liabilities_widget)
        liabilities_layout.setContentsMargins(0, 0, 0, 0)
        liabilities_layout.setSpacing(2)

        liabilities_title = QLabel("Liabilities")
        liabilities_title.setFont(QFont("Segoe UI", 9))
        liabilities_title.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        liabilities_layout.addWidget(liabilities_title)

        self.liabilities_label = QLabel(f"-{currency_symbol}{abs(total_liabilities):,.2f}")
        self.liabilities_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        self.liabilities_label.setStyleSheet("color: #EF9A9A;")
        liabilities_layout.addWidget(self.liabilities_label)

        breakdown_layout.addWidget(liabilities_widget)
        breakdown_layout.addStretch()

        layout.addLayout(breakdown_layout)

    def _get_currency_symbol(self, currency: str) -> str:
        """Get currency symbol."""
        symbols = {
            "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3",
            "CAD": "C$", "JPY": "\u00a5", "AUD": "A$"
        }
        return symbols.get(currency, currency)

    def update_totals(
        self,
        total_balance: float,
        total_assets: float,
        total_liabilities: float,
        account_count: int
    ):
        """Update all displayed totals."""
        currency_symbol = self._get_currency_symbol(self._currency)

        formatted_total = f"{currency_symbol}{abs(total_balance):,.2f}"
        if total_balance < 0:
            formatted_total = f"-{formatted_total}"
        self.total_label.setText(formatted_total)

        self.assets_label.setText(f"{currency_symbol}{total_assets:,.2f}")
        self.liabilities_label.setText(f"-{currency_symbol}{abs(total_liabilities):,.2f}")


class EmptyStateWidget(QFrame):
    """Widget displayed when no bank accounts are connected."""

    add_bank_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the empty state UI."""
        self.setObjectName("emptyStateWidget")
        self.setStyleSheet("""
            QFrame#emptyStateWidget {
                background-color: #FAFAFA;
                border: 2px dashed #E0E0E0;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon_label = QLabel()
        icon_label.setText("\U0001F3E6")  # Bank emoji
        icon_label.setFont(QFont("Segoe UI Emoji", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel("No Bank Accounts Connected")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #333333;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Connect your bank accounts to automatically import\n"
            "transactions and track your finances in real-time."
        )
        desc_label.setFont(QFont("Segoe UI", 11))
        desc_label.setStyleSheet("color: #666666;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        layout.addSpacing(16)

        # Add bank button
        add_btn = QPushButton("Connect Your First Bank")
        add_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        add_btn.setMinimumSize(220, 48)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        add_btn.clicked.connect(self.add_bank_clicked.emit)
        layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class BankingPage(QWidget):
    """
    Main banking page displaying linked bank accounts and sync controls.

    Features:
    - List of connected bank accounts with balances
    - Total aggregated balance display
    - Sync status and controls
    - Add new bank connection button
    - Account detail access
    """

    # Signals
    add_bank_requested = pyqtSignal()
    account_selected = pyqtSignal(str)  # Emits account ID
    sync_requested = pyqtSignal(str)  # Emits account ID (or empty for all)
    disconnect_requested = pyqtSignal(str)  # Emits account ID

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._account_cards: Dict[str, BankAccountCard] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the main page UI."""
        self.setObjectName("bankingPage")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        title_label = QLabel("Banking")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1A1A1A;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Sync all button
        self.sync_all_btn = QPushButton("Sync All")
        self.sync_all_btn.setFont(QFont("Segoe UI", 10))
        self.sync_all_btn.setMinimumSize(100, 36)
        self.sync_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_all_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1976D2;
                border: 1px solid #1976D2;
                border-radius: 6px;
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
                border-color: #E0E0E0;
            }
        """)
        self.sync_all_btn.clicked.connect(lambda: self.sync_requested.emit(""))
        header_layout.addWidget(self.sync_all_btn)

        # Add bank button
        self.add_bank_btn = QPushButton("+ Add Bank")
        self.add_bank_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.add_bank_btn.setMinimumSize(120, 36)
        self.add_bank_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_bank_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.add_bank_btn.clicked.connect(self.add_bank_requested.emit)
        header_layout.addWidget(self.add_bank_btn)

        main_layout.addLayout(header_layout)

        # Stacked widget for empty/content states
        self.stacked_widget = QStackedWidget()

        # Empty state
        self.empty_state = EmptyStateWidget()
        self.empty_state.add_bank_clicked.connect(self.add_bank_requested.emit)
        self.stacked_widget.addWidget(self.empty_state)

        # Content state
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(24)

        # Total balance card
        self.total_card = TotalBalanceCard()
        content_layout.addWidget(self.total_card)

        # Accounts section header
        accounts_header = QHBoxLayout()

        accounts_title = QLabel("Connected Accounts")
        accounts_title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        accounts_title.setStyleSheet("color: #333333;")
        accounts_header.addWidget(accounts_title)

        accounts_header.addStretch()

        self.accounts_count_label = QLabel("0 accounts")
        self.accounts_count_label.setFont(QFont("Segoe UI", 10))
        self.accounts_count_label.setStyleSheet("color: #666666;")
        accounts_header.addWidget(self.accounts_count_label)

        content_layout.addLayout(accounts_header)

        # Scroll area for account cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        # Accounts grid container
        self.accounts_container = QWidget()
        self.accounts_grid = QGridLayout(self.accounts_container)
        self.accounts_grid.setContentsMargins(0, 0, 0, 0)
        self.accounts_grid.setSpacing(16)

        scroll_area.setWidget(self.accounts_container)
        content_layout.addWidget(scroll_area)

        self.stacked_widget.addWidget(self.content_widget)

        main_layout.addWidget(self.stacked_widget)

        # Initially show empty state
        self._update_view_state()

    def _update_view_state(self):
        """Update which view to show based on account count."""
        if len(self._accounts) == 0:
            self.stacked_widget.setCurrentWidget(self.empty_state)
            self.sync_all_btn.setEnabled(False)
        else:
            self.stacked_widget.setCurrentWidget(self.content_widget)
            self.sync_all_btn.setEnabled(True)

    def _update_totals(self):
        """Calculate and update total balances."""
        total_assets = 0.0
        total_liabilities = 0.0

        for account in self._accounts.values():
            balance = account.get("balance", 0.0)
            account_type = account.get("type", "").lower()

            # Credit cards and loans are liabilities
            if account_type in ["credit", "credit_card", "loan", "mortgage"]:
                total_liabilities += abs(balance)
            else:
                if balance >= 0:
                    total_assets += balance
                else:
                    total_liabilities += abs(balance)

        total_balance = total_assets - total_liabilities

        self.total_card.update_totals(
            total_balance,
            total_assets,
            total_liabilities,
            len(self._accounts)
        )

        self.accounts_count_label.setText(f"{len(self._accounts)} accounts")

    def _refresh_account_cards(self):
        """Rebuild the account cards grid."""
        # Clear existing cards
        while self.accounts_grid.count():
            item = self.accounts_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._account_cards.clear()

        # Add cards for each account
        row = 0
        col = 0
        max_cols = 3

        for account_id, account in self._accounts.items():
            card = BankAccountCard(
                account_id=account_id,
                account_name=account.get("name", "Unknown Account"),
                institution_name=account.get("institution_name", "Unknown Bank"),
                account_type=account.get("type", "checking"),
                balance=account.get("balance", 0.0),
                currency=account.get("currency", "USD"),
                mask=account.get("mask"),
                status=ConnectionStatus(
                    account.get("status", ConnectionStatus.CONNECTED.value)
                ),
                last_synced=account.get("last_synced")
            )

            card.clicked.connect(self.account_selected.emit)
            card.sync_requested.connect(self.sync_requested.emit)
            card.disconnect_requested.connect(self._on_disconnect_requested)

            self.accounts_grid.addWidget(card, row, col)
            self._account_cards[account_id] = card

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Add spacer to push cards to top-left
        spacer = QSpacerItem(
            20, 20,
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.accounts_grid.addItem(spacer, row + 1, max_cols)

    def _on_disconnect_requested(self, account_id: str):
        """Handle disconnect request with confirmation."""
        account = self._accounts.get(account_id, {})
        account_name = account.get("name", "this account")

        reply = QMessageBox.question(
            self,
            "Disconnect Account",
            f"Are you sure you want to disconnect {account_name}?\n\n"
            "This will remove the connection to your bank. "
            "Your transaction history will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.disconnect_requested.emit(account_id)

    # Public methods for updating data

    def set_accounts(self, accounts: List[Dict[str, Any]]):
        """
        Set the list of bank accounts to display.

        Args:
            accounts: List of account dictionaries with keys:
                - id: Account ID
                - name: Account name
                - institution_name: Bank name
                - type: Account type (checking, savings, credit, etc.)
                - balance: Current balance
                - currency: Currency code
                - mask: Last 4 digits (optional)
                - status: Connection status
                - last_synced: Last sync datetime (optional)
        """
        self._accounts = {acc["id"]: acc for acc in accounts}
        self._refresh_account_cards()
        self._update_totals()
        self._update_view_state()

    def add_account(self, account: Dict[str, Any]):
        """Add a single account to the display."""
        self._accounts[account["id"]] = account
        self._refresh_account_cards()
        self._update_totals()
        self._update_view_state()

    def remove_account(self, account_id: str):
        """Remove an account from the display."""
        if account_id in self._accounts:
            del self._accounts[account_id]
            self._refresh_account_cards()
            self._update_totals()
            self._update_view_state()

    def update_account(self, account_id: str, updates: Dict[str, Any]):
        """Update an existing account's data."""
        if account_id in self._accounts:
            self._accounts[account_id].update(updates)

            if account_id in self._account_cards:
                card = self._account_cards[account_id]

                if "balance" in updates:
                    card.update_balance(updates["balance"])

                if "status" in updates:
                    card.update_status(ConnectionStatus(updates["status"]))

                if "last_synced" in updates:
                    card.update_last_synced(updates["last_synced"])

            self._update_totals()

    def update_account_status(self, account_id: str, status: str):
        """Update an account's connection status."""
        self.update_account(account_id, {"status": status})

    def update_account_balance(self, account_id: str, balance: float):
        """Update an account's balance."""
        self.update_account(account_id, {"balance": balance})

    def set_syncing(self, account_id: str, is_syncing: bool):
        """Set an account's syncing state."""
        status = ConnectionStatus.SYNCING.value if is_syncing else ConnectionStatus.CONNECTED.value
        self.update_account_status(account_id, status)

    def set_all_syncing(self, is_syncing: bool):
        """Set syncing state for all accounts."""
        for account_id in self._accounts:
            self.set_syncing(account_id, is_syncing)
        self.sync_all_btn.setEnabled(not is_syncing)


# Convenience function for creating the page
def create_banking_page(parent: Optional[QWidget] = None) -> BankingPage:
    """Create and return a new BankingPage instance."""
    return BankingPage(parent)
