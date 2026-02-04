"""
Bank Connection Wizard Module

Multi-step wizard for connecting bank accounts via OAuth/Plaid integration.
"""

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QLineEdit, QListWidget,
    QListWidgetItem, QCheckBox, QProgressBar, QScrollArea,
    QSizePolicy, QSpacerItem, QMessageBox, QStackedWidget,
    QGroupBox, QGridLayout, QAbstractItemView
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QUrl, QSize, QThread, pyqtSlot
)
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QDesktopServices
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum, auto
import webbrowser


class WizardStep(Enum):
    """Wizard step identifiers."""
    SEARCH_INSTITUTION = auto()
    OAUTH_CONNECT = auto()
    SELECT_ACCOUNTS = auto()
    CONFIRMATION = auto()


@dataclass
class InstitutionInfo:
    """Information about a financial institution."""
    id: str
    name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    url: Optional[str] = None
    supports_oauth: bool = True


@dataclass
class AccountInfo:
    """Information about a discovered bank account."""
    id: str
    name: str
    official_name: Optional[str]
    type: str
    subtype: Optional[str]
    mask: Optional[str]
    balance: Optional[float]
    currency: str = "USD"


class InstitutionSearchWidget(QFrame):
    """Widget for searching and selecting a financial institution."""

    institution_selected = pyqtSignal(object)  # Emits InstitutionInfo

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._institutions: List[InstitutionInfo] = []
        self._selected_institution: Optional[InstitutionInfo] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the search widget UI."""
        self.setObjectName("institutionSearchWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Search input
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for your bank...")
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.setMinimumHeight(48)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1976D2;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)

        # Results list
        self.results_list = QListWidget()
        self.results_list.setObjectName("institutionList")
        self.results_list.setMinimumHeight(300)
        self.results_list.setStyleSheet("""
            QListWidget#institutionList {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                outline: none;
            }
            QListWidget#institutionList::item {
                padding: 12px 16px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget#institutionList::item:hover {
                background-color: #F5F5F5;
            }
            QListWidget#institutionList::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
        """)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.results_list)

        # Popular banks section
        popular_label = QLabel("Popular Banks")
        popular_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        popular_label.setStyleSheet("color: #666666;")
        layout.addWidget(popular_label)

        self.popular_grid = QGridLayout()
        self.popular_grid.setSpacing(12)
        layout.addLayout(self.popular_grid)

        # Add placeholder popular banks
        self._add_popular_banks()

    def _add_popular_banks(self):
        """Add popular bank buttons."""
        popular_banks = [
            ("Chase", "#117ACA"),
            ("Bank of America", "#012169"),
            ("Wells Fargo", "#D71E28"),
            ("Citi", "#003B70"),
            ("Capital One", "#D03027"),
            ("US Bank", "#0C2340"),
        ]

        row = 0
        col = 0
        max_cols = 3

        for name, color in popular_banks:
            btn = QPushButton(name)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setMinimumSize(140, 48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    color: {color};
                    border: 1px solid {color};
                    border-radius: 8px;
                    padding: 12px 16px;
                }}
                QPushButton:hover {{
                    background-color: {color}15;
                }}
                QPushButton:pressed {{
                    background-color: {color}25;
                }}
            """)
            btn.clicked.connect(lambda checked, n=name: self._on_popular_clicked(n))
            self.popular_grid.addWidget(btn, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _on_search_changed(self, text: str):
        """Handle search text changes."""
        # This would typically trigger an API search
        # For now, filter the loaded institutions
        self._filter_institutions(text)

    def _filter_institutions(self, query: str):
        """Filter institutions based on search query."""
        self.results_list.clear()
        query_lower = query.lower()

        for inst in self._institutions:
            if query_lower in inst.name.lower():
                item = QListWidgetItem(inst.name)
                item.setData(Qt.ItemDataRole.UserRole, inst)
                item.setSizeHint(QSize(0, 48))
                self.results_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle institution item click."""
        institution = item.data(Qt.ItemDataRole.UserRole)
        self._selected_institution = institution

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle institution item double-click."""
        institution = item.data(Qt.ItemDataRole.UserRole)
        self._selected_institution = institution
        self.institution_selected.emit(institution)

    def _on_popular_clicked(self, name: str):
        """Handle popular bank button click."""
        # Find the institution by name
        for inst in self._institutions:
            if inst.name.lower() == name.lower():
                self._selected_institution = inst
                self.institution_selected.emit(inst)
                return

        # If not found, create a placeholder
        inst = InstitutionInfo(
            id=name.lower().replace(" ", "_"),
            name=name
        )
        self._selected_institution = inst
        self.institution_selected.emit(inst)

    def set_institutions(self, institutions: List[InstitutionInfo]):
        """Set the list of available institutions."""
        self._institutions = institutions
        self._filter_institutions(self.search_input.text())

    def get_selected_institution(self) -> Optional[InstitutionInfo]:
        """Get the currently selected institution."""
        return self._selected_institution

    def select_institution(self):
        """Emit selected institution signal."""
        if self._selected_institution:
            self.institution_selected.emit(self._selected_institution)


class OAuthConnectWidget(QFrame):
    """Widget for OAuth authentication flow."""

    auth_started = pyqtSignal()
    auth_completed = pyqtSignal(str)  # Emits public token
    auth_failed = pyqtSignal(str)  # Emits error message
    auth_cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._institution: Optional[InstitutionInfo] = None
        self._link_token: Optional[str] = None
        self._is_connecting = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the OAuth widget UI."""
        self.setObjectName("oauthConnectWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Institution info
        self.institution_frame = QFrame()
        self.institution_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        inst_layout = QVBoxLayout(self.institution_frame)
        inst_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst_layout.setSpacing(12)

        # Institution icon placeholder
        self.inst_icon = QLabel()
        self.inst_icon.setFixedSize(64, 64)
        self.inst_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inst_icon.setStyleSheet("""
            background-color: #1976D2;
            border-radius: 32px;
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)
        inst_layout.addWidget(self.inst_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self.inst_name = QLabel("Bank Name")
        self.inst_name.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        self.inst_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst_layout.addWidget(self.inst_name)

        layout.addWidget(self.institution_frame)

        # Instructions
        instructions = QLabel(
            "Click the button below to securely connect to your bank.\n"
            "You will be redirected to your bank's website to log in."
        )
        instructions.setFont(QFont("Segoe UI", 11))
        instructions.setStyleSheet("color: #666666;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Connect button
        self.connect_btn = QPushButton("Connect to Bank")
        self.connect_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.connect_btn.setMinimumSize(200, 52)
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 28px;
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
        self.connect_btn.clicked.connect(self._start_oauth)
        layout.addWidget(self.connect_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress indicator (hidden by default)
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setMinimumWidth(300)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #1976D2;
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Connecting...")
        self.progress_label.setFont(QFont("Segoe UI", 10))
        self.progress_label.setStyleSheet("color: #666666;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(self.progress_frame)

        # Security notice
        security_frame = QFrame()
        security_frame.setStyleSheet("""
            QFrame {
                background-color: #E8F5E9;
                border: 1px solid #C8E6C9;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        security_layout = QHBoxLayout(security_frame)

        security_icon = QLabel()
        security_icon.setText("\U0001F512")  # Lock emoji
        security_icon.setFont(QFont("Segoe UI Emoji", 16))
        security_layout.addWidget(security_icon)

        security_text = QLabel(
            "Your credentials are encrypted and never stored on our servers.\n"
            "We use bank-level security to protect your data."
        )
        security_text.setFont(QFont("Segoe UI", 9))
        security_text.setStyleSheet("color: #2E7D32;")
        security_text.setWordWrap(True)
        security_layout.addWidget(security_text, 1)

        layout.addWidget(security_frame)

        layout.addStretch()

    def set_institution(self, institution: InstitutionInfo):
        """Set the institution to connect to."""
        self._institution = institution
        self.inst_name.setText(institution.name)
        self.inst_icon.setText(institution.name[0].upper() if institution.name else "B")

        if institution.primary_color:
            self.inst_icon.setStyleSheet(f"""
                background-color: {institution.primary_color};
                border-radius: 32px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            """)

    def set_link_token(self, link_token: str):
        """Set the Plaid link token for OAuth."""
        self._link_token = link_token

    def _start_oauth(self):
        """Start the OAuth authentication flow."""
        if self._is_connecting:
            return

        self._is_connecting = True
        self.connect_btn.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.progress_label.setText("Opening bank login...")

        self.auth_started.emit()

        # In a real implementation, this would:
        # 1. Open Plaid Link in a QWebEngineView or system browser
        # 2. Handle the OAuth callback
        # For this demo, we'll simulate with a timer

        QTimer.singleShot(2000, self._simulate_auth_complete)

    def _simulate_auth_complete(self):
        """Simulate OAuth completion (for demo purposes)."""
        self.progress_label.setText("Authentication successful!")
        self._is_connecting = False

        # Emit success with a mock public token
        QTimer.singleShot(1000, lambda: self.auth_completed.emit("public-token-mock-12345"))

    def reset(self):
        """Reset the widget state."""
        self._is_connecting = False
        self.connect_btn.setEnabled(True)
        self.progress_frame.setVisible(False)


class AccountSelectionWidget(QFrame):
    """Widget for selecting which accounts to link."""

    accounts_selected = pyqtSignal(list)  # Emits list of account IDs

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._accounts: List[AccountInfo] = []
        self._selected_ids: set = set()
        self._setup_ui()

    def _setup_ui(self):
        """Set up the account selection widget UI."""
        self.setObjectName("accountSelectionWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Select Accounts to Link")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #333333;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Select all checkbox
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.setFont(QFont("Segoe UI", 10))
        self.select_all_cb.stateChanged.connect(self._on_select_all_changed)
        header_layout.addWidget(self.select_all_cb)

        layout.addLayout(header_layout)

        # Accounts list
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

        self.accounts_container = QWidget()
        self.accounts_layout = QVBoxLayout(self.accounts_container)
        self.accounts_layout.setContentsMargins(8, 8, 8, 8)
        self.accounts_layout.setSpacing(8)

        scroll_area.setWidget(self.accounts_container)
        layout.addWidget(scroll_area)

        # Selected count
        self.selected_label = QLabel("0 accounts selected")
        self.selected_label.setFont(QFont("Segoe UI", 10))
        self.selected_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.selected_label)

    def _create_account_item(self, account: AccountInfo) -> QFrame:
        """Create a widget for an account item."""
        frame = QFrame()
        frame.setObjectName("accountItem")
        frame.setStyleSheet("""
            QFrame#accountItem {
                background-color: #FAFAFA;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
            }
            QFrame#accountItem:hover {
                background-color: #F0F0F0;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Checkbox
        cb = QCheckBox()
        cb.setProperty("account_id", account.id)
        cb.stateChanged.connect(lambda state, aid=account.id: self._on_account_toggled(aid, state))
        layout.addWidget(cb)

        # Account info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        name_label = QLabel(account.name)
        name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        name_label.setStyleSheet("color: #333333;")
        info_layout.addWidget(name_label)

        details_text = account.type.replace("_", " ").title()
        if account.mask:
            details_text += f" ****{account.mask}"

        details_label = QLabel(details_text)
        details_label.setFont(QFont("Segoe UI", 9))
        details_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(details_label)

        layout.addLayout(info_layout, 1)

        # Balance
        if account.balance is not None:
            currency_symbol = "$" if account.currency == "USD" else account.currency
            balance_text = f"{currency_symbol}{account.balance:,.2f}"

            balance_label = QLabel(balance_text)
            balance_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            balance_color = "#4CAF50" if account.balance >= 0 else "#F44336"
            balance_label.setStyleSheet(f"color: {balance_color};")
            layout.addWidget(balance_label)

        return frame

    def _on_account_toggled(self, account_id: str, state: int):
        """Handle account checkbox toggle."""
        if state == Qt.CheckState.Checked.value:
            self._selected_ids.add(account_id)
        else:
            self._selected_ids.discard(account_id)

        self._update_selected_label()
        self._update_select_all_state()

    def _on_select_all_changed(self, state: int):
        """Handle select all checkbox change."""
        is_checked = state == Qt.CheckState.Checked.value

        # Find all checkboxes and update them
        for i in range(self.accounts_layout.count()):
            item = self.accounts_layout.itemAt(i)
            if item and item.widget():
                frame = item.widget()
                for child in frame.findChildren(QCheckBox):
                    child.setChecked(is_checked)

    def _update_selected_label(self):
        """Update the selected accounts count label."""
        count = len(self._selected_ids)
        self.selected_label.setText(f"{count} account{'s' if count != 1 else ''} selected")

    def _update_select_all_state(self):
        """Update select all checkbox state based on individual selections."""
        if len(self._selected_ids) == 0:
            self.select_all_cb.setCheckState(Qt.CheckState.Unchecked)
        elif len(self._selected_ids) == len(self._accounts):
            self.select_all_cb.setCheckState(Qt.CheckState.Checked)
        else:
            self.select_all_cb.setCheckState(Qt.CheckState.PartiallyChecked)

    def set_accounts(self, accounts: List[AccountInfo]):
        """Set the list of available accounts."""
        self._accounts = accounts
        self._selected_ids.clear()

        # Clear existing items
        while self.accounts_layout.count():
            item = self.accounts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add account items
        for account in accounts:
            item_widget = self._create_account_item(account)
            self.accounts_layout.addWidget(item_widget)

            # Auto-select all accounts by default
            self._selected_ids.add(account.id)
            for cb in item_widget.findChildren(QCheckBox):
                cb.setChecked(True)

        self.accounts_layout.addStretch()
        self._update_selected_label()
        self.select_all_cb.setChecked(True)

    def get_selected_accounts(self) -> List[str]:
        """Get list of selected account IDs."""
        return list(self._selected_ids)


class ConfirmationWidget(QFrame):
    """Widget displaying connection confirmation."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the confirmation widget UI."""
        self.setObjectName("confirmationWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success icon
        success_icon = QLabel()
        success_icon.setText("\u2713")  # Checkmark
        success_icon.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        success_icon.setStyleSheet("""
            color: #4CAF50;
            background-color: #E8F5E9;
            border-radius: 40px;
            padding: 20px;
        """)
        success_icon.setFixedSize(80, 80)
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(success_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        # Title
        title = QLabel("Accounts Connected Successfully!")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #333333;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Summary frame
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        summary_layout = QVBoxLayout(self.summary_frame)
        summary_layout.setSpacing(8)

        self.institution_label = QLabel("Bank: -")
        self.institution_label.setFont(QFont("Segoe UI", 11))
        summary_layout.addWidget(self.institution_label)

        self.accounts_label = QLabel("Accounts linked: 0")
        self.accounts_label.setFont(QFont("Segoe UI", 11))
        summary_layout.addWidget(self.accounts_label)

        self.sync_label = QLabel("Initial sync will begin shortly...")
        self.sync_label.setFont(QFont("Segoe UI", 10))
        self.sync_label.setStyleSheet("color: #666666;")
        summary_layout.addWidget(self.sync_label)

        layout.addWidget(self.summary_frame)

        # Next steps
        next_steps = QLabel(
            "Your accounts will sync automatically every day.\n"
            "You can manually sync at any time from the Banking page."
        )
        next_steps.setFont(QFont("Segoe UI", 10))
        next_steps.setStyleSheet("color: #666666;")
        next_steps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        next_steps.setWordWrap(True)
        layout.addWidget(next_steps)

        layout.addStretch()

    def set_summary(
        self,
        institution_name: str,
        account_count: int,
        total_balance: Optional[float] = None
    ):
        """Set the confirmation summary."""
        self.institution_label.setText(f"Bank: {institution_name}")
        self.accounts_label.setText(f"Accounts linked: {account_count}")

        if total_balance is not None:
            self.sync_label.setText(
                f"Total balance: ${total_balance:,.2f}\n"
                "Initial sync will begin shortly..."
            )


# Wizard Pages

class SearchInstitutionPage(QWizardPage):
    """Wizard page for searching and selecting an institution."""

    def __init__(self, parent: Optional[QWizard] = None):
        super().__init__(parent)
        self.setTitle("Select Your Bank")
        self.setSubTitle("Search for your financial institution to begin the connection process.")

        self._selected_institution: Optional[InstitutionInfo] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)

        self.search_widget = InstitutionSearchWidget()
        self.search_widget.institution_selected.connect(self._on_institution_selected)
        layout.addWidget(self.search_widget)

    def _on_institution_selected(self, institution: InstitutionInfo):
        """Handle institution selection."""
        self._selected_institution = institution
        self.completeChanged.emit()

        # Auto-advance to next page
        wizard = self.wizard()
        if wizard:
            wizard.next()

    def set_institutions(self, institutions: List[InstitutionInfo]):
        """Set available institutions."""
        self.search_widget.set_institutions(institutions)

    def get_selected_institution(self) -> Optional[InstitutionInfo]:
        """Get the selected institution."""
        return self._selected_institution

    def isComplete(self) -> bool:
        """Check if the page is complete."""
        return self._selected_institution is not None


class OAuthPage(QWizardPage):
    """Wizard page for OAuth authentication."""

    auth_completed = pyqtSignal(str)  # Emits public token

    def __init__(self, parent: Optional[QWizard] = None):
        super().__init__(parent)
        self.setTitle("Connect to Your Bank")
        self.setSubTitle("Securely authenticate with your bank to link your accounts.")

        self._public_token: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)

        self.oauth_widget = OAuthConnectWidget()
        self.oauth_widget.auth_completed.connect(self._on_auth_completed)
        self.oauth_widget.auth_failed.connect(self._on_auth_failed)
        layout.addWidget(self.oauth_widget)

    def set_institution(self, institution: InstitutionInfo):
        """Set the institution for authentication."""
        self.oauth_widget.set_institution(institution)

    def set_link_token(self, link_token: str):
        """Set the Plaid link token."""
        self.oauth_widget.set_link_token(link_token)

    def _on_auth_completed(self, public_token: str):
        """Handle successful authentication."""
        self._public_token = public_token
        self.auth_completed.emit(public_token)
        self.completeChanged.emit()

        # Auto-advance to next page
        wizard = self.wizard()
        if wizard:
            wizard.next()

    def _on_auth_failed(self, error: str):
        """Handle authentication failure."""
        QMessageBox.warning(
            self,
            "Connection Failed",
            f"Unable to connect to your bank:\n{error}\n\nPlease try again."
        )

    def get_public_token(self) -> Optional[str]:
        """Get the public token from auth."""
        return self._public_token

    def isComplete(self) -> bool:
        """Check if the page is complete."""
        return self._public_token is not None

    def initializePage(self):
        """Initialize the page when shown."""
        self._public_token = None
        self.oauth_widget.reset()


class SelectAccountsPage(QWizardPage):
    """Wizard page for selecting accounts to link."""

    def __init__(self, parent: Optional[QWizard] = None):
        super().__init__(parent)
        self.setTitle("Select Accounts")
        self.setSubTitle("Choose which accounts you want to link to Pecunia.")

        self._setup_ui()

    def _setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)

        self.selection_widget = AccountSelectionWidget()
        layout.addWidget(self.selection_widget)

    def set_accounts(self, accounts: List[AccountInfo]):
        """Set available accounts."""
        self.selection_widget.set_accounts(accounts)

    def get_selected_accounts(self) -> List[str]:
        """Get selected account IDs."""
        return self.selection_widget.get_selected_accounts()

    def isComplete(self) -> bool:
        """Check if at least one account is selected."""
        return len(self.selection_widget.get_selected_accounts()) > 0


class ConfirmationPage(QWizardPage):
    """Wizard page for confirmation."""

    def __init__(self, parent: Optional[QWizard] = None):
        super().__init__(parent)
        self.setTitle("Connection Complete")
        self.setSubTitle("")
        self.setFinalPage(True)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)

        self.confirmation_widget = ConfirmationWidget()
        layout.addWidget(self.confirmation_widget)

    def set_summary(
        self,
        institution_name: str,
        account_count: int,
        total_balance: Optional[float] = None
    ):
        """Set the confirmation summary."""
        self.confirmation_widget.set_summary(institution_name, account_count, total_balance)


class BankConnectWizard(QWizard):
    """
    Multi-step wizard for connecting bank accounts.

    Steps:
    1. Search and select financial institution
    2. OAuth authentication in browser
    3. Select accounts to link
    4. Confirmation

    Signals:
        connection_completed: Emitted when accounts are successfully connected
        connection_cancelled: Emitted when wizard is cancelled
    """

    connection_completed = pyqtSignal(dict)  # Emits connection result
    connection_cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._institutions: List[InstitutionInfo] = []
        self._selected_institution: Optional[InstitutionInfo] = None
        self._public_token: Optional[str] = None
        self._accounts: List[AccountInfo] = []
        self._selected_account_ids: List[str] = []

        self._setup_ui()
        self._setup_pages()

    def _setup_ui(self):
        """Set up the wizard UI."""
        self.setWindowTitle("Connect Bank Account")
        self.setMinimumSize(600, 700)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        # Style the wizard
        self.setStyleSheet("""
            QWizard {
                background-color: #FFFFFF;
            }
            QWizard QLabel#qt_wizard_title_label {
                font-size: 20px;
                font-weight: bold;
                color: #333333;
            }
            QWizard QLabel#qt_wizard_subTitleLabel {
                font-size: 12px;
                color: #666666;
            }
            QPushButton {
                min-width: 100px;
                min-height: 36px;
            }
        """)

        # Configure buttons
        self.setButtonText(QWizard.WizardButton.NextButton, "Continue")
        self.setButtonText(QWizard.WizardButton.BackButton, "Back")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Done")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Cancel")

    def _setup_pages(self):
        """Set up wizard pages."""
        # Page 1: Search Institution
        self.search_page = SearchInstitutionPage(self)
        self.addPage(self.search_page)

        # Page 2: OAuth Connect
        self.oauth_page = OAuthPage(self)
        self.oauth_page.auth_completed.connect(self._on_auth_completed)
        self.addPage(self.oauth_page)

        # Page 3: Select Accounts
        self.accounts_page = SelectAccountsPage(self)
        self.addPage(self.accounts_page)

        # Page 4: Confirmation
        self.confirmation_page = ConfirmationPage(self)
        self.addPage(self.confirmation_page)

        # Connect page change signal
        self.currentIdChanged.connect(self._on_page_changed)

    def _on_page_changed(self, page_id: int):
        """Handle page changes."""
        if page_id == 1:  # OAuth page
            institution = self.search_page.get_selected_institution()
            if institution:
                self._selected_institution = institution
                self.oauth_page.set_institution(institution)

        elif page_id == 2:  # Accounts page
            # In a real implementation, fetch accounts from API
            # For demo, create mock accounts
            self._load_mock_accounts()

        elif page_id == 3:  # Confirmation page
            self._selected_account_ids = self.accounts_page.get_selected_accounts()
            if self._selected_institution:
                self.confirmation_page.set_summary(
                    self._selected_institution.name,
                    len(self._selected_account_ids)
                )

    def _on_auth_completed(self, public_token: str):
        """Handle OAuth completion."""
        self._public_token = public_token

    def _load_mock_accounts(self):
        """Load mock accounts for demo."""
        mock_accounts = [
            AccountInfo(
                id="acc_001",
                name="Checking Account",
                official_name="Personal Checking",
                type="checking",
                subtype="checking",
                mask="1234",
                balance=5432.10,
                currency="USD"
            ),
            AccountInfo(
                id="acc_002",
                name="Savings Account",
                official_name="High Yield Savings",
                type="savings",
                subtype="savings",
                mask="5678",
                balance=12500.00,
                currency="USD"
            ),
            AccountInfo(
                id="acc_003",
                name="Credit Card",
                official_name="Rewards Credit Card",
                type="credit",
                subtype="credit card",
                mask="9012",
                balance=-1234.56,
                currency="USD"
            ),
        ]
        self._accounts = mock_accounts
        self.accounts_page.set_accounts(mock_accounts)

    def set_institutions(self, institutions: List[InstitutionInfo]):
        """Set available institutions for search."""
        self._institutions = institutions
        self.search_page.set_institutions(institutions)

    def set_link_token(self, link_token: str):
        """Set the Plaid link token."""
        self.oauth_page.set_link_token(link_token)

    def accept(self):
        """Handle wizard completion."""
        result = {
            "institution": self._selected_institution,
            "public_token": self._public_token,
            "selected_accounts": self._selected_account_ids,
        }
        self.connection_completed.emit(result)
        super().accept()

    def reject(self):
        """Handle wizard cancellation."""
        self.connection_cancelled.emit()
        super().reject()


# Convenience function for creating the wizard
def create_bank_connect_wizard(parent: Optional[QWidget] = None) -> BankConnectWizard:
    """Create and return a new BankConnectWizard instance."""
    wizard = BankConnectWizard(parent)

    # Pre-populate with some mock institutions
    mock_institutions = [
        InstitutionInfo(id="chase", name="Chase", primary_color="#117ACA"),
        InstitutionInfo(id="bofa", name="Bank of America", primary_color="#012169"),
        InstitutionInfo(id="wells", name="Wells Fargo", primary_color="#D71E28"),
        InstitutionInfo(id="citi", name="Citi", primary_color="#003B70"),
        InstitutionInfo(id="capital_one", name="Capital One", primary_color="#D03027"),
        InstitutionInfo(id="usbank", name="US Bank", primary_color="#0C2340"),
        InstitutionInfo(id="pnc", name="PNC Bank", primary_color="#FF6600"),
        InstitutionInfo(id="td", name="TD Bank", primary_color="#34A853"),
    ]
    wizard.set_institutions(mock_institutions)

    return wizard
