"""
Settings Page Module

Application settings and user preferences page with tabbed interface.
Features:
- Account settings (email, password, 2FA)
- Appearance (theme with preview, language with immediate switch)
- Sync configuration
- Notifications management
- Subscription management
- Data export/import/backup
- About and licenses

Uses QSettings for persistence and includes unsaved changes warning.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QTabWidget,
    QLineEdit, QComboBox, QCheckBox, QSpinBox, QGroupBox,
    QFileDialog, QMessageBox, QRadioButton, QButtonGroup,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QFormLayout, QStackedWidget, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt6.QtGui import QFont, QCloseEvent, QKeySequence, QShortcut
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import copy

# Import section widgets
from .settings_sections import (
    AccountSection,
    AppearanceSection,
    SyncSection,
    NotificationsSection,
    SubscriptionSection,
    DataSection,
    AboutSection
)


# =============================================================================
# Category Management Dialog
# =============================================================================

class CategoryDialog(QDialog):
    """Dialog for adding/editing transaction categories."""

    def __init__(self, parent: Optional[QWidget] = None,
                 category_name: str = "", category_type: str = "expense"):
        super().__init__(parent)
        self.setWindowTitle("Category" if not category_name else "Edit Category")
        self.setMinimumWidth(300)
        self._setup_ui(category_name, category_type)

    def _setup_ui(self, category_name: str, category_type: str):
        """Set up the dialog UI."""
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Category name
        self.name_edit = QLineEdit()
        self.name_edit.setText(category_name)
        self.name_edit.setPlaceholderText("Enter category name")
        layout.addRow("Name:", self.name_edit)

        # Category type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["expense", "income"])
        if category_type:
            index = self.type_combo.findText(category_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        layout.addRow("Type:", self.type_combo)

        # Color picker placeholder
        self.color_combo = QComboBox()
        self.color_combo.addItems([
            "Red", "Orange", "Yellow", "Green", "Blue",
            "Purple", "Pink", "Gray", "Brown", "Teal"
        ])
        layout.addRow("Color:", self.color_combo)

        # Icon placeholder
        self.icon_combo = QComboBox()
        self.icon_combo.addItems([
            "Default", "Food", "Shopping", "Transport", "Bills",
            "Entertainment", "Health", "Education", "Travel", "Other"
        ])
        layout.addRow("Icon:", self.icon_combo)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_data(self) -> Dict[str, str]:
        """Get the category data."""
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "color": self.color_combo.currentText().lower(),
            "icon": self.icon_combo.currentText().lower()
        }


# =============================================================================
# Categories Tab
# =============================================================================

class CategoriesTab(QWidget):
    """Categories tab - manage transaction categories."""

    categories_changed = pyqtSignal(list)  # List of categories

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._categories: List[Dict[str, str]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the categories tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Expense Categories
        expense_group = QGroupBox("Expense Categories")
        expense_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        expense_layout = QVBoxLayout(expense_group)
        expense_layout.setContentsMargins(20, 20, 20, 20)
        expense_layout.setSpacing(10)

        self.expense_list = QListWidget()
        self.expense_list.setFont(QFont("Segoe UI", 10))
        self.expense_list.setMinimumHeight(150)
        self.expense_list.setAlternatingRowColors(True)
        expense_layout.addWidget(self.expense_list)

        expense_btn_layout = QHBoxLayout()
        add_expense_btn = QPushButton("Add Category")
        add_expense_btn.setObjectName("secondaryButton")
        add_expense_btn.clicked.connect(lambda: self._add_category("expense"))
        expense_btn_layout.addWidget(add_expense_btn)

        edit_expense_btn = QPushButton("Edit")
        edit_expense_btn.setObjectName("secondaryButton")
        edit_expense_btn.clicked.connect(lambda: self._edit_category("expense"))
        expense_btn_layout.addWidget(edit_expense_btn)

        delete_expense_btn = QPushButton("Delete")
        delete_expense_btn.setObjectName("secondaryButton")
        delete_expense_btn.clicked.connect(lambda: self._delete_category("expense"))
        expense_btn_layout.addWidget(delete_expense_btn)

        expense_btn_layout.addStretch()
        expense_layout.addLayout(expense_btn_layout)

        layout.addWidget(expense_group)

        # Income Categories
        income_group = QGroupBox("Income Categories")
        income_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        income_layout = QVBoxLayout(income_group)
        income_layout.setContentsMargins(20, 20, 20, 20)
        income_layout.setSpacing(10)

        self.income_list = QListWidget()
        self.income_list.setFont(QFont("Segoe UI", 10))
        self.income_list.setMinimumHeight(150)
        self.income_list.setAlternatingRowColors(True)
        income_layout.addWidget(self.income_list)

        income_btn_layout = QHBoxLayout()
        add_income_btn = QPushButton("Add Category")
        add_income_btn.setObjectName("secondaryButton")
        add_income_btn.clicked.connect(lambda: self._add_category("income"))
        income_btn_layout.addWidget(add_income_btn)

        edit_income_btn = QPushButton("Edit")
        edit_income_btn.setObjectName("secondaryButton")
        edit_income_btn.clicked.connect(lambda: self._edit_category("income"))
        income_btn_layout.addWidget(edit_income_btn)

        delete_income_btn = QPushButton("Delete")
        delete_income_btn.setObjectName("secondaryButton")
        delete_income_btn.clicked.connect(lambda: self._delete_category("income"))
        income_btn_layout.addWidget(delete_income_btn)

        income_btn_layout.addStretch()
        income_layout.addLayout(income_btn_layout)

        layout.addWidget(income_group)
        layout.addStretch()

    def _add_category(self, category_type: str):
        """Add a new category."""
        dialog = CategoryDialog(self, "", category_type)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data["name"]:
                # Check for duplicates
                for cat in self._categories:
                    if cat["name"].lower() == data["name"].lower() and cat["type"] == data["type"]:
                        QMessageBox.warning(
                            self, "Duplicate Category",
                            f"A {data['type']} category with this name already exists."
                        )
                        return

                self._categories.append(data)
                self._update_lists()
                self.categories_changed.emit(self._categories)

    def _edit_category(self, category_type: str):
        """Edit the selected category."""
        list_widget = self.expense_list if category_type == "expense" else self.income_list
        current_item = list_widget.currentItem()

        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a category to edit.")
            return

        old_name = current_item.text()

        # Find the category
        old_cat = None
        for cat in self._categories:
            if cat["name"] == old_name and cat["type"] == category_type:
                old_cat = cat
                break

        if not old_cat:
            return

        dialog = CategoryDialog(self, old_name, category_type)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data["name"]:
                # Update the category
                old_cat.update(data)
                self._update_lists()
                self.categories_changed.emit(self._categories)

    def _delete_category(self, category_type: str):
        """Delete the selected category."""
        list_widget = self.expense_list if category_type == "expense" else self.income_list
        current_item = list_widget.currentItem()

        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a category to delete.")
            return

        name = current_item.text()

        reply = QMessageBox.question(
            self,
            "Delete Category",
            f"Are you sure you want to delete the category '{name}'?\n\n"
            "Transactions using this category will be set to 'Uncategorized'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._categories = [
                cat for cat in self._categories
                if not (cat["name"] == name and cat["type"] == category_type)
            ]
            self._update_lists()
            self.categories_changed.emit(self._categories)

    def _update_lists(self):
        """Update the category lists."""
        self.expense_list.clear()
        self.income_list.clear()

        for cat in sorted(self._categories, key=lambda x: x["name"].lower()):
            item = QListWidgetItem(cat["name"])
            if cat["type"] == "expense":
                self.expense_list.addItem(item)
            else:
                self.income_list.addItem(item)

    def set_categories(self, categories: List[Dict[str, str]]):
        """Set the categories list."""
        self._categories = categories.copy() if categories else []
        self._update_lists()

    def get_categories(self) -> List[Dict[str, str]]:
        """Get the current categories."""
        return self._categories.copy()


# =============================================================================
# Regional Settings Tab
# =============================================================================

class RegionalTab(QWidget):
    """Regional settings tab - currency, date format, number format."""

    settings_changed = pyqtSignal(str, object)

    CURRENCIES = [
        ("USD", "US Dollar ($)"),
        ("EUR", "Euro (E)"),
        ("GBP", "British Pound (P)"),
        ("JPY", "Japanese Yen (Y)"),
        ("CAD", "Canadian Dollar (C$)"),
        ("AUD", "Australian Dollar (A$)"),
        ("CHF", "Swiss Franc (Fr.)"),
        ("CNY", "Chinese Yuan (Y)"),
        ("INR", "Indian Rupee (R)"),
        ("BRL", "Brazilian Real (R$)"),
        ("MXN", "Mexican Peso ($)"),
        ("KRW", "South Korean Won (W)"),
        ("RUB", "Russian Ruble (r)"),
        ("TRY", "Turkish Lira (TL)"),
        ("ZAR", "South African Rand (R)")
    ]

    DATE_FORMATS = [
        ("MM/DD/YYYY", "MM/DD/YYYY (US)"),
        ("DD/MM/YYYY", "DD/MM/YYYY (EU)"),
        ("YYYY-MM-DD", "YYYY-MM-DD (ISO)"),
        ("DD.MM.YYYY", "DD.MM.YYYY (DE)"),
        ("YYYY/MM/DD", "YYYY/MM/DD (JP)")
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the regional settings tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Currency Section
        currency_group = QGroupBox("Currency")
        currency_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        currency_layout = QFormLayout(currency_group)
        currency_layout.setContentsMargins(20, 20, 20, 20)
        currency_layout.setSpacing(15)

        self.currency_combo = QComboBox()
        for code, name in self.CURRENCIES:
            self.currency_combo.addItem(name, code)
        self.currency_combo.setMinimumWidth(200)
        self.currency_combo.currentIndexChanged.connect(self._on_currency_changed)
        currency_layout.addRow("Default Currency:", self.currency_combo)

        self.currency_position_combo = QComboBox()
        self.currency_position_combo.addItems(["Before amount ($100)", "After amount (100$)"])
        self.currency_position_combo.currentIndexChanged.connect(
            lambda i: self.settings_changed.emit("currency_position", "before" if i == 0 else "after")
        )
        currency_layout.addRow("Symbol Position:", self.currency_position_combo)

        layout.addWidget(currency_group)

        # Date & Time Section
        datetime_group = QGroupBox("Date & Time")
        datetime_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        datetime_layout = QFormLayout(datetime_group)
        datetime_layout.setContentsMargins(20, 20, 20, 20)
        datetime_layout.setSpacing(15)

        self.date_format_combo = QComboBox()
        for fmt, name in self.DATE_FORMATS:
            self.date_format_combo.addItem(name, fmt)
        self.date_format_combo.setMinimumWidth(200)
        self.date_format_combo.currentIndexChanged.connect(self._on_date_format_changed)
        datetime_layout.addRow("Date Format:", self.date_format_combo)

        self.time_format_combo = QComboBox()
        self.time_format_combo.addItems(["12-hour (1:30 PM)", "24-hour (13:30)"])
        self.time_format_combo.currentIndexChanged.connect(
            lambda i: self.settings_changed.emit("time_format", "12h" if i == 0 else "24h")
        )
        datetime_layout.addRow("Time Format:", self.time_format_combo)

        self.week_start_combo = QComboBox()
        self.week_start_combo.addItems(["Sunday", "Monday"])
        self.week_start_combo.currentIndexChanged.connect(
            lambda i: self.settings_changed.emit("first_day_of_week", "sunday" if i == 0 else "monday")
        )
        datetime_layout.addRow("First Day of Week:", self.week_start_combo)

        layout.addWidget(datetime_group)

        # Number Format Section
        number_group = QGroupBox("Number Format")
        number_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        number_layout = QFormLayout(number_group)
        number_layout.setContentsMargins(20, 20, 20, 20)
        number_layout.setSpacing(15)

        self.decimal_separator_combo = QComboBox()
        self.decimal_separator_combo.addItems(["Period (1,234.56)", "Comma (1.234,56)"])
        self.decimal_separator_combo.currentIndexChanged.connect(
            lambda i: self.settings_changed.emit("decimal_separator", "." if i == 0 else ",")
        )
        number_layout.addRow("Decimal Separator:", self.decimal_separator_combo)

        self.show_decimals_check = QCheckBox("Show decimal places")
        self.show_decimals_check.setChecked(True)
        self.show_decimals_check.toggled.connect(
            lambda v: self.settings_changed.emit("show_decimals", v)
        )
        number_layout.addRow(self.show_decimals_check)

        layout.addWidget(number_group)
        layout.addStretch()

    def _on_currency_changed(self, index: int):
        """Handle currency change."""
        currency_code = self.currency_combo.currentData()
        self.settings_changed.emit("currency", currency_code)

    def _on_date_format_changed(self, index: int):
        """Handle date format change."""
        date_format = self.date_format_combo.currentData()
        self.settings_changed.emit("date_format", date_format)

    def set_values(self, settings: Dict[str, Any]):
        """Set the current settings values."""
        # Currency
        currency = settings.get("currency", "USD")
        index = self.currency_combo.findData(currency)
        if index >= 0:
            self.currency_combo.setCurrentIndex(index)

        # Currency position
        pos = settings.get("currency_position", "before")
        self.currency_position_combo.setCurrentIndex(0 if pos == "before" else 1)

        # Date format
        date_fmt = settings.get("date_format", "MM/DD/YYYY")
        index = self.date_format_combo.findData(date_fmt)
        if index >= 0:
            self.date_format_combo.setCurrentIndex(index)

        # Time format
        time_fmt = settings.get("time_format", "12h")
        self.time_format_combo.setCurrentIndex(0 if time_fmt == "12h" else 1)

        # Week start
        week_start = settings.get("first_day_of_week", "sunday")
        self.week_start_combo.setCurrentIndex(0 if week_start == "sunday" else 1)

        # Decimal separator
        dec_sep = settings.get("decimal_separator", ".")
        self.decimal_separator_combo.setCurrentIndex(0 if dec_sep == "." else 1)

        # Show decimals
        self.show_decimals_check.setChecked(settings.get("show_decimals", True))

    def get_values(self) -> Dict[str, Any]:
        """Get the current settings values."""
        return {
            "currency": self.currency_combo.currentData(),
            "currency_position": "before" if self.currency_position_combo.currentIndex() == 0 else "after",
            "date_format": self.date_format_combo.currentData(),
            "time_format": "12h" if self.time_format_combo.currentIndex() == 0 else "24h",
            "first_day_of_week": "sunday" if self.week_start_combo.currentIndex() == 0 else "monday",
            "decimal_separator": "." if self.decimal_separator_combo.currentIndex() == 0 else ",",
            "show_decimals": self.show_decimals_check.isChecked()
        }


# =============================================================================
# Privacy & Security Tab
# =============================================================================

class PrivacyTab(QWidget):
    """Privacy and security settings tab."""

    settings_changed = pyqtSignal(str, object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the privacy tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Login Security Section
        login_group = QGroupBox("Login Security")
        login_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        login_layout = QVBoxLayout(login_group)
        login_layout.setContentsMargins(20, 20, 20, 20)
        login_layout.setSpacing(10)

        self.remember_login_check = QCheckBox("Remember me on this device")
        self.remember_login_check.setFont(QFont("Segoe UI", 10))
        self.remember_login_check.setChecked(True)
        self.remember_login_check.toggled.connect(
            lambda v: self.settings_changed.emit("remember_login", v)
        )
        login_layout.addWidget(self.remember_login_check)

        self.lock_on_minimize_check = QCheckBox("Lock app when minimized")
        self.lock_on_minimize_check.setFont(QFont("Segoe UI", 10))
        self.lock_on_minimize_check.toggled.connect(
            lambda v: self.settings_changed.emit("lock_on_minimize", v)
        )
        login_layout.addWidget(self.lock_on_minimize_check)

        # Lock timeout
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("Auto-lock after:")
        timeout_label.setFont(QFont("Segoe UI", 10))
        timeout_layout.addWidget(timeout_label)

        self.lock_timeout_spin = QSpinBox()
        self.lock_timeout_spin.setRange(1, 60)
        self.lock_timeout_spin.setValue(5)
        self.lock_timeout_spin.setSuffix(" minutes")
        self.lock_timeout_spin.valueChanged.connect(
            lambda v: self.settings_changed.emit("lock_timeout_minutes", v)
        )
        timeout_layout.addWidget(self.lock_timeout_spin)

        timeout_layout.addStretch()
        login_layout.addLayout(timeout_layout)

        layout.addWidget(login_group)

        # Privacy Section
        privacy_group = QGroupBox("Privacy")
        privacy_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        privacy_layout = QVBoxLayout(privacy_group)
        privacy_layout.setContentsMargins(20, 20, 20, 20)
        privacy_layout.setSpacing(10)

        self.hide_amounts_check = QCheckBox("Hide amounts in notifications")
        self.hide_amounts_check.setFont(QFont("Segoe UI", 10))
        self.hide_amounts_check.setToolTip("For privacy, hide monetary values in system notifications")
        self.hide_amounts_check.toggled.connect(
            lambda v: self.settings_changed.emit("hide_amounts_in_notifications", v)
        )
        privacy_layout.addWidget(self.hide_amounts_check)

        self.blur_sensitive_check = QCheckBox("Blur sensitive data when inactive")
        self.blur_sensitive_check.setFont(QFont("Segoe UI", 10))
        self.blur_sensitive_check.setToolTip("Blur account numbers and balances when app loses focus")
        self.blur_sensitive_check.toggled.connect(
            lambda v: self.settings_changed.emit("blur_sensitive", v)
        )
        privacy_layout.addWidget(self.blur_sensitive_check)

        layout.addWidget(privacy_group)

        # Data Collection Section
        data_group = QGroupBox("Data Collection")
        data_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(20, 20, 20, 20)
        data_layout.setSpacing(10)

        self.analytics_check = QCheckBox("Share anonymous usage analytics")
        self.analytics_check.setFont(QFont("Segoe UI", 10))
        self.analytics_check.setChecked(True)
        self.analytics_check.setToolTip("Help improve the app by sharing anonymous usage data")
        self.analytics_check.toggled.connect(
            lambda v: self.settings_changed.emit("analytics_enabled", v)
        )
        data_layout.addWidget(self.analytics_check)

        self.crash_reports_check = QCheckBox("Send crash reports")
        self.crash_reports_check.setFont(QFont("Segoe UI", 10))
        self.crash_reports_check.setChecked(True)
        self.crash_reports_check.setToolTip("Automatically send crash reports to help fix bugs")
        self.crash_reports_check.toggled.connect(
            lambda v: self.settings_changed.emit("crash_reports_enabled", v)
        )
        data_layout.addWidget(self.crash_reports_check)

        data_info = QLabel(
            "We never share your personal financial data with third parties. "
            "Analytics data is completely anonymous."
        )
        data_info.setFont(QFont("Segoe UI", 9))
        data_info.setStyleSheet("color: #666;")
        data_info.setWordWrap(True)
        data_layout.addWidget(data_info)

        layout.addWidget(data_group)
        layout.addStretch()

    def set_values(self, settings: Dict[str, Any]):
        """Set the current settings values."""
        self.remember_login_check.setChecked(settings.get("remember_login", True))
        self.lock_on_minimize_check.setChecked(settings.get("lock_on_minimize", False))
        self.lock_timeout_spin.setValue(settings.get("lock_timeout_minutes", 5))
        self.hide_amounts_check.setChecked(settings.get("hide_amounts_in_notifications", False))
        self.blur_sensitive_check.setChecked(settings.get("blur_sensitive", False))
        self.analytics_check.setChecked(settings.get("analytics_enabled", True))
        self.crash_reports_check.setChecked(settings.get("crash_reports_enabled", True))

    def get_values(self) -> Dict[str, Any]:
        """Get the current settings values."""
        return {
            "remember_login": self.remember_login_check.isChecked(),
            "lock_on_minimize": self.lock_on_minimize_check.isChecked(),
            "lock_timeout_minutes": self.lock_timeout_spin.value(),
            "hide_amounts_in_notifications": self.hide_amounts_check.isChecked(),
            "blur_sensitive": self.blur_sensitive_check.isChecked(),
            "analytics_enabled": self.analytics_check.isChecked(),
            "crash_reports_enabled": self.crash_reports_check.isChecked()
        }


# =============================================================================
# Main Settings Page
# =============================================================================

class SettingsPage(QWidget):
    """
    Settings page with tabbed interface for application configuration.

    Tabs:
    - Account: user info, email, password, 2FA
    - Appearance: theme (with preview), language (immediate switch)
    - Regional: currency, date format, number format
    - Sync: auto-sync, interval, data selection
    - Notifications: toggle all notification types
    - Subscription: plan info, upgrade options
    - Categories: manage transaction categories
    - Data: export, import, backup
    - Privacy: security and privacy settings
    - About: version, licenses, credits
    """

    # Signals
    settings_changed = pyqtSignal(str, object)
    theme_changed = pyqtSignal(str)
    theme_preview_requested = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    logout_requested = pyqtSignal()
    password_change_requested = pyqtSignal(str, str)
    email_change_requested = pyqtSignal(str, str)
    two_factor_toggle_requested = pyqtSignal(bool)
    delete_account_requested = pyqtSignal()
    sync_requested = pyqtSignal()
    categories_changed = pyqtSignal(list)
    export_requested = pyqtSignal(str, dict)
    import_requested = pyqtSignal(str)
    backup_requested = pyqtSignal()
    restore_requested = pyqtSignal(str)
    clear_data_requested = pyqtSignal()
    check_updates_requested = pyqtSignal()
    open_help_requested = pyqtSignal()
    upgrade_requested = pyqtSignal(str)
    save_requested = pyqtSignal(dict)
    cancel_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self._config: Dict[str, Any] = {}
        self._original_config: Dict[str, Any] = {}
        self._has_unsaved_changes = False
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        """Set up the settings page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Segoe UI", 10))
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.West)

        # Account Tab
        self.account_section = AccountSection()
        self._connect_account_signals()
        self.tab_widget.addTab(self.account_section, "Account")

        # Appearance Tab
        self.appearance_section = AppearanceSection()
        self._connect_appearance_signals()
        self.tab_widget.addTab(self.appearance_section, "Appearance")

        # Regional Tab
        self.regional_tab = RegionalTab()
        self.regional_tab.settings_changed.connect(self._on_setting_changed)
        self.tab_widget.addTab(self.regional_tab, "Regional")

        # Sync Tab
        self.sync_section = SyncSection()
        self._connect_sync_signals()
        self.tab_widget.addTab(self.sync_section, "Sync")

        # Notifications Tab
        self.notifications_section = NotificationsSection()
        self.notifications_section.settings_changed.connect(self._on_setting_changed)
        self.notifications_section.test_notification_requested.connect(
            self._on_test_notification
        )
        self.tab_widget.addTab(self.notifications_section, "Notifications")

        # Subscription Tab
        self.subscription_section = SubscriptionSection()
        self.subscription_section.upgrade_requested.connect(self.upgrade_requested.emit)
        self.subscription_section.manage_subscription_requested.connect(
            self._on_manage_subscription
        )
        self.tab_widget.addTab(self.subscription_section, "Subscription")

        # Categories Tab
        self.categories_tab = CategoriesTab()
        self.categories_tab.categories_changed.connect(self._on_categories_changed)
        self.tab_widget.addTab(self.categories_tab, "Categories")

        # Data Tab
        self.data_section = DataSection()
        self._connect_data_signals()
        self.tab_widget.addTab(self.data_section, "Data")

        # Privacy Tab
        self.privacy_tab = PrivacyTab()
        self.privacy_tab.settings_changed.connect(self._on_setting_changed)
        self.tab_widget.addTab(self.privacy_tab, "Privacy")

        # About Tab
        self.about_section = AboutSection()
        self.about_section.check_updates_requested.connect(self.check_updates_requested.emit)
        self.about_section.open_help_requested.connect(self.open_help_requested.emit)
        self.tab_widget.addTab(self.about_section, "About")

        layout.addWidget(self.tab_widget)

        # Footer with save/cancel buttons
        footer_layout = self._create_footer()
        layout.addLayout(footer_layout)

    def _create_header(self) -> QHBoxLayout:
        """Create the header section."""
        layout = QHBoxLayout()

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        layout.addStretch()

        # Unsaved changes indicator
        self.unsaved_indicator = QLabel("Unsaved changes")
        self.unsaved_indicator.setFont(QFont("Segoe UI", 10))
        self.unsaved_indicator.setStyleSheet("color: #FF9800; font-weight: bold;")
        self.unsaved_indicator.setVisible(False)
        layout.addWidget(self.unsaved_indicator)

        return layout

    def _create_footer(self) -> QHBoxLayout:
        """Create the footer with action buttons."""
        layout = QHBoxLayout()

        layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(cancel_btn)

        # Save button
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.setMinimumWidth(120)
        self.save_btn.clicked.connect(self._on_save)
        layout.addWidget(self.save_btn)

        return layout

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Ctrl+S to save
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self._on_save)

        # Escape to cancel
        cancel_shortcut = QShortcut(QKeySequence.StandardKey.Cancel, self)
        cancel_shortcut.activated.connect(self._on_cancel)

    def _connect_account_signals(self):
        """Connect account section signals."""
        self.account_section.logout_requested.connect(self.logout_requested.emit)
        self.account_section.password_change_requested.connect(self.password_change_requested.emit)
        self.account_section.email_change_requested.connect(self.email_change_requested.emit)
        self.account_section.two_factor_toggle_requested.connect(self.two_factor_toggle_requested.emit)
        self.account_section.delete_account_requested.connect(self.delete_account_requested.emit)

    def _connect_appearance_signals(self):
        """Connect appearance section signals."""
        self.appearance_section.theme_changed.connect(self.theme_changed.emit)
        self.appearance_section.theme_preview_requested.connect(self.theme_preview_requested.emit)
        self.appearance_section.language_changed.connect(self._on_language_changed)
        self.appearance_section.settings_changed.connect(self._on_setting_changed)

    def _connect_sync_signals(self):
        """Connect sync section signals."""
        self.sync_section.settings_changed.connect(self._on_setting_changed)
        self.sync_section.sync_requested.connect(self.sync_requested.emit)
        self.sync_section.sync_reset_requested.connect(self._on_sync_reset)

    def _connect_data_signals(self):
        """Connect data section signals."""
        self.data_section.export_requested.connect(self.export_requested.emit)
        self.data_section.import_requested.connect(self.import_requested.emit)
        self.data_section.backup_requested.connect(self.backup_requested.emit)
        self.data_section.restore_requested.connect(self.restore_requested.emit)
        self.data_section.clear_data_requested.connect(self.clear_data_requested.emit)

    def _on_setting_changed(self, key: str, value):
        """Handle individual setting changes."""
        self._config[key] = value
        self._mark_unsaved()
        self.settings_changed.emit(key, value)

    def _on_categories_changed(self, categories: List[Dict]):
        """Handle categories change."""
        self._config["categories"] = categories
        self._mark_unsaved()
        self.categories_changed.emit(categories)

    def _on_language_changed(self, lang_code: str):
        """Handle language change - immediate effect."""
        self._config["language"] = lang_code
        self._mark_unsaved()
        self.language_changed.emit(lang_code)

    def _on_test_notification(self):
        """Handle test notification request."""
        QMessageBox.information(
            self,
            "Test Notification",
            "This is a test notification.\n\n"
            "If notifications are working correctly, you should also "
            "see a system notification."
        )

    def _on_manage_subscription(self):
        """Handle manage subscription request."""
        QMessageBox.information(
            self,
            "Manage Subscription",
            "Subscription management will open in your browser."
        )

    def _on_sync_reset(self):
        """Handle sync reset request."""
        QMessageBox.information(
            self,
            "Sync Reset",
            "Sync state has been reset. A full re-sync will occur on next sync."
        )

    def _mark_unsaved(self):
        """Mark that there are unsaved changes."""
        if not self._has_unsaved_changes:
            self._has_unsaved_changes = True
            self.unsaved_indicator.setVisible(True)

    def _clear_unsaved(self):
        """Clear the unsaved changes marker."""
        self._has_unsaved_changes = False
        self.unsaved_indicator.setVisible(False)

    def _on_save(self):
        """Handle save button click."""
        # Validate settings before saving
        if not self._validate_settings():
            return

        # Collect all settings
        all_settings = self.get_all_settings()
        self._config.update(all_settings)
        self._original_config = copy.deepcopy(self._config)

        self._clear_unsaved()
        self.save_requested.emit(all_settings)

        QMessageBox.information(
            self,
            "Settings Saved",
            "Your settings have been saved successfully."
        )

    def _on_cancel(self):
        """Handle cancel button click."""
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Discard Changes",
                "You have unsaved changes. Are you sure you want to discard them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Restore original settings
        self.load_settings(self._original_config)
        self._clear_unsaved()
        self.cancel_requested.emit()

    def _validate_settings(self) -> bool:
        """Validate all settings before saving."""
        # Add validation logic here
        return True

    def check_unsaved_changes(self) -> bool:
        """
        Check for unsaved changes and prompt user.

        Returns:
            True if safe to proceed (no changes or user confirmed discard),
            False if operation should be cancelled.
        """
        if not self._has_unsaved_changes:
            return True

        reply = QMessageBox.warning(
            self,
            "Unsaved Changes",
            "You have unsaved changes in Settings.\n\n"
            "Do you want to save them before leaving?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )

        if reply == QMessageBox.StandardButton.Save:
            self._on_save()
            return True
        elif reply == QMessageBox.StandardButton.Discard:
            self._clear_unsaved()
            return True
        else:
            return False

    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the UI."""
        self._config = copy.deepcopy(settings)
        self._original_config = copy.deepcopy(settings)

        # Load into each section
        self.appearance_section.set_values(settings)
        self.regional_tab.set_values(settings)
        self.sync_section.set_values(settings)
        self.notifications_section.set_values(settings)
        self.privacy_tab.set_values(settings)

        # Load categories
        if "categories" in settings:
            self.categories_tab.set_categories(settings["categories"])

        # Load app version
        if "app_version" in settings:
            self.about_section.set_version(
                settings["app_version"],
                settings.get("build_number", "")
            )

        # Load subscription info
        if "subscription_plan" in settings:
            self.subscription_section.set_current_plan(
                settings["subscription_plan"],
                settings.get("subscription_renewal_date", "")
            )

        self._clear_unsaved()

    def set_user_info(self, username: str, email: str, member_since: str = "",
                      last_login: str = ""):
        """Set the user info for account section."""
        self.account_section.set_user_info(username, email, member_since, last_login)

    def set_two_factor_enabled(self, enabled: bool):
        """Set the two-factor authentication status."""
        self.account_section.set_two_factor_enabled(enabled)

    def set_last_sync(self, timestamp: Optional[str] = None):
        """Update the last sync time in sync section."""
        self.sync_section.set_last_sync(timestamp)

    def set_sync_status(self, status: str, is_error: bool = False):
        """Update the sync status in sync section."""
        self.sync_section.set_sync_status(status, is_error)

    def set_pending_changes(self, count: int):
        """Set the pending sync changes count."""
        self.sync_section.set_pending_changes(count)

    def set_update_status(self, status: str, has_update: bool = False):
        """Update the update status in about section."""
        self.about_section.set_update_status(status, has_update)

    def set_current_plan(self, plan_id: str, renewal_date: str = ""):
        """Set the current subscription plan."""
        self.subscription_section.set_current_plan(plan_id, renewal_date)

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings values."""
        settings = {}

        # Collect from all sections
        settings.update(self.appearance_section.get_values())
        settings.update(self.regional_tab.get_values())
        settings.update(self.sync_section.get_values())
        settings.update(self.notifications_section.get_values())
        settings.update(self.privacy_tab.get_values())

        # Get categories
        settings["categories"] = self.categories_tab.get_categories()

        return settings

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return copy.deepcopy(self._config)

    def save_to_qsettings(self, q_settings: QSettings) -> bool:
        """
        Save current settings to QSettings.

        Args:
            q_settings: QSettings instance

        Returns:
            True if save was successful, False otherwise
        """
        try:
            all_settings = self.get_all_settings()
            for key, value in all_settings.items():
                if isinstance(value, (list, dict)):
                    q_settings.setValue(key, json.dumps(value))
                else:
                    q_settings.setValue(key, value)
            q_settings.sync()
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings: {str(e)}"
            )
            return False

    def load_from_qsettings(self, q_settings: QSettings):
        """
        Load settings from QSettings.

        Args:
            q_settings: QSettings instance
        """
        settings = {}
        for key in q_settings.allKeys():
            value = q_settings.value(key)
            # Try to parse JSON for complex types
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            settings[key] = value

        self.load_settings(settings)

    def save_to_config_manager(self, config_manager) -> bool:
        """
        Save current settings to a config manager.

        Args:
            config_manager: Object with a save(dict) method

        Returns:
            True if save was successful, False otherwise
        """
        try:
            all_settings = self.get_all_settings()
            config_manager.save(all_settings)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings: {str(e)}"
            )
            return False
