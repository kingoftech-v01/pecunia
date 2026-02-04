"""
Transaction form dialog for creating and editing transactions.

Provides TransactionFormDialog with full form functionality including
category autocomplete, date picker, and amount input validation.

Features:
- Create/edit transaction form
- Category autocomplete with recent suggestions
- Date picker with quick date buttons
- Currency input with formatting
- Tag input with autocomplete
- Split transaction support
- Form validation with error display
- Keyboard navigation
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QLineEdit,
    QComboBox, QDateEdit, QDoubleSpinBox, QTextEdit,
    QCompleter, QMessageBox, QSizePolicy, QToolButton,
    QStackedWidget, QSpinBox, QCheckBox, QTabWidget
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QDate, QSize, QStringListModel,
    QTimer, QRegularExpression
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QKeySequence, QShortcut,
    QRegularExpressionValidator, QFocusEvent
)


class TransactionType(Enum):
    """Transaction type enumeration."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


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
    merchant: Optional[str] = None
    to_account: Optional[str] = None  # For transfers


@dataclass
class SplitLine:
    """Split transaction line item."""
    category: str
    amount: Decimal
    description: Optional[str] = None


# =============================================================================
# Form Field Widgets
# =============================================================================

class FormField(QWidget):
    """Base form field with label and validation."""

    def __init__(
        self,
        label: str,
        required: bool = False,
        help_text: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._label_text = label
        self._required = required
        self._help_text = help_text
        self._error_message = ""
        self._setup_base_ui()

    def _setup_base_ui(self) -> None:
        """Set up the base field UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        # Label row
        label_layout = QHBoxLayout()
        label_layout.setSpacing(4)

        self._label = QLabel(self._label_text)
        self._label.setStyleSheet("font-size: 13px; font-weight: 500;")
        label_layout.addWidget(self._label)

        if self._required:
            required_mark = QLabel("*")
            required_mark.setStyleSheet("color: #F44336; font-weight: bold;")
            label_layout.addWidget(required_mark)

        label_layout.addStretch()
        layout.addLayout(label_layout)

        # Input widget placeholder (set by subclasses)
        self._input_container = QVBoxLayout()
        self._input_container.setSpacing(2)
        layout.addLayout(self._input_container)

        # Error message
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #F44336; font-size: 11px;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        # Help text
        if self._help_text:
            help_label = QLabel(self._help_text)
            help_label.setStyleSheet("color: #757575; font-size: 11px;")
            help_label.setWordWrap(True)
            layout.addWidget(help_label)

    def set_error(self, message: str) -> None:
        """Show an error message."""
        self._error_message = message
        self._error_label.setText(message)
        self._error_label.show()

    def clear_error(self) -> None:
        """Clear the error message."""
        self._error_message = ""
        self._error_label.hide()

    @property
    def has_error(self) -> bool:
        return bool(self._error_message)


class TextInputField(FormField):
    """Text input field with validation."""

    text_changed = pyqtSignal(str)

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        required: bool = False,
        max_length: int = 200,
        help_text: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(label, required, help_text, parent)
        self._placeholder = placeholder
        self._max_length = max_length
        self._setup_input()

    def _setup_input(self) -> None:
        """Set up the text input."""
        self._input = QLineEdit()
        self._input.setPlaceholderText(self._placeholder)
        self._input.setMaxLength(self._max_length)
        self._input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
            }
            QLineEdit[error="true"] {
                border: 1px solid #F44336;
            }
        """)
        self._input.textChanged.connect(self._on_text_changed)
        self._input_container.addWidget(self._input)

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes."""
        self.clear_error()
        self.text_changed.emit(text)

    def text(self) -> str:
        return self._input.text()

    def set_text(self, text: str) -> None:
        self._input.setText(text)

    def clear(self) -> None:
        self._input.clear()

    def setFocus(self) -> None:
        self._input.setFocus()


class CategoryInputField(FormField):
    """Category input with autocomplete and color indicator."""

    category_changed = pyqtSignal(str)

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

    def __init__(
        self,
        label: str = "Category",
        required: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(label, required, "", parent)
        self._categories: List[str] = []
        self._recent_categories: List[str] = []
        self._setup_input()

    def _setup_input(self) -> None:
        """Set up the category input."""
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        # Color indicator
        self._color_indicator = QLabel()
        self._color_indicator.setFixedSize(16, 16)
        self._color_indicator.setStyleSheet("""
            background-color: #9E9E9E;
            border-radius: 8px;
        """)
        input_layout.addWidget(self._color_indicator)

        # Input
        self._input = QComboBox()
        self._input.setEditable(True)
        self._input.setStyleSheet("""
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #1976D2;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                selection-background-color: #E3F2FD;
            }
        """)
        self._input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._input.currentTextChanged.connect(self._on_category_changed)
        input_layout.addWidget(self._input, 1)

        self._input_container.addLayout(input_layout)

        # Recent categories chips
        self._recent_layout = QHBoxLayout()
        self._recent_layout.setSpacing(6)
        self._recent_label = QLabel("Recent:")
        self._recent_label.setStyleSheet("color: #757575; font-size: 11px;")
        self._recent_layout.addWidget(self._recent_label)
        self._recent_chips_layout = QHBoxLayout()
        self._recent_chips_layout.setSpacing(4)
        self._recent_layout.addLayout(self._recent_chips_layout)
        self._recent_layout.addStretch()
        self._input_container.addLayout(self._recent_layout)
        self._recent_label.hide()

    def _on_category_changed(self, text: str) -> None:
        """Handle category change."""
        self.clear_error()

        # Update color indicator
        color = self.CATEGORY_COLORS.get(text, "#9E9E9E")
        self._color_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 8px;
        """)

        self.category_changed.emit(text)

    def set_categories(self, categories: List[str]) -> None:
        """Set available categories."""
        self._categories = categories
        current = self._input.currentText()
        self._input.clear()
        self._input.addItems(categories)
        if current:
            self._input.setCurrentText(current)

    def set_recent_categories(self, categories: List[str]) -> None:
        """Set recent categories for quick selection."""
        self._recent_categories = categories[:5]

        # Clear existing chips
        while self._recent_chips_layout.count():
            item = self._recent_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if categories:
            self._recent_label.show()
            for cat in self._recent_categories:
                chip = QPushButton(cat)
                chip.setStyleSheet("""
                    QPushButton {
                        background-color: #F5F5F5;
                        border: 1px solid #E0E0E0;
                        border-radius: 12px;
                        padding: 2px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #E0E0E0;
                    }
                """)
                chip.setCursor(Qt.CursorShape.PointingHandCursor)
                chip.clicked.connect(lambda checked, c=cat: self._input.setCurrentText(c))
                self._recent_chips_layout.addWidget(chip)
        else:
            self._recent_label.hide()

    def category(self) -> str:
        return self._input.currentText()

    def set_category(self, category: str) -> None:
        self._input.setCurrentText(category)

    def clear(self) -> None:
        self._input.setCurrentIndex(-1)
        self._input.clearEditText()


class AmountInputField(FormField):
    """Currency amount input with formatting."""

    amount_changed = pyqtSignal(Decimal)

    def __init__(
        self,
        label: str = "Amount",
        currency_symbol: str = "$",
        required: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(label, required, "", parent)
        self._currency_symbol = currency_symbol
        self._setup_input()

    def _setup_input(self) -> None:
        """Set up the amount input."""
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        # Currency symbol
        symbol_label = QLabel(self._currency_symbol)
        symbol_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #757575;")
        input_layout.addWidget(symbol_label)

        # Spin box
        self._input = QDoubleSpinBox()
        self._input.setRange(0.01, 999999999.99)
        self._input.setDecimals(2)
        self._input.setSingleStep(10.00)
        self._input.setGroupSeparatorShown(True)
        self._input.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #1976D2;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0;
                border: none;
            }
        """)
        self._input.valueChanged.connect(self._on_value_changed)
        input_layout.addWidget(self._input, 1)

        self._input_container.addLayout(input_layout)

        # Quick amount buttons
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)
        quick_label = QLabel("Quick:")
        quick_label.setStyleSheet("color: #757575; font-size: 11px;")
        quick_layout.addWidget(quick_label)

        for amount in [10, 25, 50, 100, 250]:
            btn = QPushButton(f"${amount}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #E0E0E0;
                }
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, a=amount: self._input.setValue(a))
            quick_layout.addWidget(btn)

        quick_layout.addStretch()
        self._input_container.addLayout(quick_layout)

    def _on_value_changed(self, value: float) -> None:
        """Handle value change."""
        self.clear_error()
        self.amount_changed.emit(Decimal(str(value)))

    def amount(self) -> Decimal:
        return Decimal(str(self._input.value()))

    def set_amount(self, amount: Decimal) -> None:
        self._input.setValue(float(amount))

    def clear(self) -> None:
        self._input.setValue(0.00)

    def setFocus(self) -> None:
        self._input.setFocus()


class DateInputField(FormField):
    """Date input with calendar and quick date buttons."""

    date_changed = pyqtSignal(QDate)

    def __init__(
        self,
        label: str = "Date",
        required: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(label, required, "", parent)
        self._setup_input()

    def _setup_input(self) -> None:
        """Set up the date input."""
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        # Date edit
        self._input = QDateEdit()
        self._input.setCalendarPopup(True)
        self._input.setDate(QDate.currentDate())
        self._input.setDisplayFormat("MMMM d, yyyy")
        self._input.setStyleSheet("""
            QDateEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QDateEdit:focus {
                border: 2px solid #1976D2;
            }
            QDateEdit::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self._input.dateChanged.connect(self._on_date_changed)
        input_layout.addWidget(self._input, 1)

        self._input_container.addLayout(input_layout)

        # Quick date buttons
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)

        today_btn = QPushButton("Today")
        today_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: #1976D2;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        today_btn.clicked.connect(lambda: self._input.setDate(QDate.currentDate()))
        quick_layout.addWidget(today_btn)

        yesterday_btn = QPushButton("Yesterday")
        yesterday_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        yesterday_btn.clicked.connect(lambda: self._input.setDate(QDate.currentDate().addDays(-1)))
        quick_layout.addWidget(yesterday_btn)

        quick_layout.addStretch()
        self._input_container.addLayout(quick_layout)

    def _on_date_changed(self, date: QDate) -> None:
        """Handle date change."""
        self.clear_error()
        self.date_changed.emit(date)

    def date(self) -> QDate:
        return self._input.date()

    def set_date(self, date: QDate) -> None:
        self._input.setDate(date)

    def clear(self) -> None:
        self._input.setDate(QDate.currentDate())


class AccountInputField(FormField):
    """Account selection dropdown."""

    account_changed = pyqtSignal(str)

    def __init__(
        self,
        label: str = "Account",
        required: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(label, required, "", parent)
        self._accounts: List[str] = []
        self._setup_input()

    def _setup_input(self) -> None:
        """Set up the account input."""
        self._input = QComboBox()
        self._input.setEditable(True)
        self._input.setStyleSheet("""
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #1976D2;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self._input.currentTextChanged.connect(self._on_account_changed)
        self._input_container.addWidget(self._input)

    def _on_account_changed(self, text: str) -> None:
        """Handle account change."""
        self.clear_error()
        self.account_changed.emit(text)

    def set_accounts(self, accounts: List[str]) -> None:
        """Set available accounts."""
        self._accounts = accounts
        current = self._input.currentText()
        self._input.clear()
        self._input.addItems(accounts)
        if current:
            self._input.setCurrentText(current)

    def account(self) -> str:
        return self._input.currentText()

    def set_account(self, account: str) -> None:
        self._input.setCurrentText(account)

    def clear(self) -> None:
        self._input.setCurrentIndex(0)


class TagsInputField(FormField):
    """Tags input with autocomplete and chips display."""

    tags_changed = pyqtSignal(list)

    def __init__(
        self,
        label: str = "Tags",
        parent: Optional[QWidget] = None
    ):
        super().__init__(label, False, "Press Enter to add a tag", parent)
        self._tags: List[str] = []
        self._available_tags: List[str] = []
        self._setup_input()

    def _setup_input(self) -> None:
        """Set up the tags input."""
        # Input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Add tags...")
        self._input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
            }
        """)
        self._input.returnPressed.connect(self._add_current_tag)
        self._input_container.addWidget(self._input)

        # Tags chips container
        self._chips_container = QHBoxLayout()
        self._chips_container.setSpacing(6)
        self._input_container.addLayout(self._chips_container)

    def _add_current_tag(self) -> None:
        """Add the current input as a tag."""
        tag = self._input.text().strip()
        if tag and tag not in self._tags:
            self._tags.append(tag)
            self._update_chips()
            self.tags_changed.emit(self._tags)
        self._input.clear()

    def _remove_tag(self, tag: str) -> None:
        """Remove a tag."""
        if tag in self._tags:
            self._tags.remove(tag)
            self._update_chips()
            self.tags_changed.emit(self._tags)

    def _update_chips(self) -> None:
        """Update the tags chips display."""
        # Clear existing chips
        while self._chips_container.count():
            item = self._chips_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add chips for each tag
        for tag in self._tags:
            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background-color: #E3F2FD;
                    border: 1px solid #90CAF9;
                    border-radius: 12px;
                }
            """)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(8, 2, 4, 2)
            chip_layout.setSpacing(4)

            label = QLabel(tag)
            label.setStyleSheet("color: #1565C0; font-size: 12px; background: transparent; border: none;")
            chip_layout.addWidget(label)

            remove_btn = QToolButton()
            remove_btn.setText("\u00D7")
            remove_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    color: #1565C0;
                    font-size: 14px;
                }
                QToolButton:hover {
                    color: #C62828;
                }
            """)
            remove_btn.setFixedSize(16, 16)
            remove_btn.clicked.connect(lambda checked, t=tag: self._remove_tag(t))
            chip_layout.addWidget(remove_btn)

            self._chips_container.addWidget(chip)

        self._chips_container.addStretch()

    def set_available_tags(self, tags: List[str]) -> None:
        """Set available tags for autocomplete."""
        self._available_tags = tags
        completer = QCompleter(tags)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._input.setCompleter(completer)

    def tags(self) -> List[str]:
        return self._tags.copy()

    def set_tags(self, tags: List[str]) -> None:
        self._tags = tags.copy() if tags else []
        self._update_chips()

    def clear(self) -> None:
        self._tags = []
        self._update_chips()
        self._input.clear()


class NotesInputField(FormField):
    """Multi-line notes input."""

    notes_changed = pyqtSignal(str)

    def __init__(
        self,
        label: str = "Notes",
        parent: Optional[QWidget] = None
    ):
        super().__init__(label, False, "", parent)
        self._setup_input()

    def _setup_input(self) -> None:
        """Set up the notes input."""
        self._input = QTextEdit()
        self._input.setPlaceholderText("Add notes (optional)...")
        self._input.setMaximumHeight(100)
        self._input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 2px solid #1976D2;
            }
        """)
        self._input.textChanged.connect(lambda: self.notes_changed.emit(self._input.toPlainText()))
        self._input_container.addWidget(self._input)

    def notes(self) -> str:
        return self._input.toPlainText()

    def set_notes(self, notes: str) -> None:
        self._input.setPlainText(notes or "")

    def clear(self) -> None:
        self._input.clear()


# =============================================================================
# Transaction Type Selector
# =============================================================================

class TypeSelector(QWidget):
    """Transaction type selector with visual buttons."""

    type_changed = pyqtSignal(TransactionType)

    TYPE_CONFIG = {
        TransactionType.EXPENSE: {
            "label": "Expense",
            "icon": "\u2193",
            "color": "#F44336",
            "bg": "#FFEBEE",
        },
        TransactionType.INCOME: {
            "label": "Income",
            "icon": "\u2191",
            "color": "#4CAF50",
            "bg": "#E8F5E9",
        },
        TransactionType.TRANSFER: {
            "label": "Transfer",
            "icon": "\u2194",
            "color": "#2196F3",
            "bg": "#E3F2FD",
        },
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_type = TransactionType.EXPENSE
        self._buttons: Dict[TransactionType, QPushButton] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the type selector UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for txn_type, config in self.TYPE_CONFIG.items():
            btn = QPushButton(f"{config['icon']} {config['label']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=txn_type: self._on_type_clicked(t))
            self._buttons[txn_type] = btn
            layout.addWidget(btn)

        self._update_styles()

    def _on_type_clicked(self, txn_type: TransactionType) -> None:
        """Handle type button click."""
        self._current_type = txn_type
        self._update_styles()
        self.type_changed.emit(txn_type)

    def _update_styles(self) -> None:
        """Update button styles based on selection."""
        for txn_type, btn in self._buttons.items():
            config = self.TYPE_CONFIG[txn_type]
            if txn_type == self._current_type:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {config['bg']};
                        color: {config['color']};
                        border: 2px solid {config['color']};
                        border-radius: 8px;
                        padding: 12px 24px;
                        font-weight: bold;
                        font-size: 14px;
                    }}
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F5F5F5;
                        color: #757575;
                        border: 1px solid #E0E0E0;
                        border-radius: 8px;
                        padding: 12px 24px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #EEEEEE;
                        border-color: #BDBDBD;
                    }
                """)

    def transaction_type(self) -> TransactionType:
        return self._current_type

    def set_transaction_type(self, txn_type: TransactionType) -> None:
        self._current_type = txn_type
        self._update_styles()


# =============================================================================
# Transaction Form Dialog
# =============================================================================

class TransactionFormDialog(QDialog):
    """
    Dialog for creating and editing transactions.

    Features:
    - Transaction type selector
    - Category autocomplete
    - Date picker with quick buttons
    - Amount input with formatting
    - Tags with autocomplete
    - Notes field
    - Form validation
    - Keyboard shortcuts

    Signals:
        saved(Transaction): Emitted when transaction is saved
        cancelled(): Emitted when form is cancelled
    """

    saved = pyqtSignal(object)
    cancelled = pyqtSignal()

    def __init__(
        self,
        transaction: Optional[Transaction] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._transaction = transaction
        self._is_edit_mode = transaction is not None
        self._categories: List[str] = []
        self._accounts: List[str] = []
        self._tags: List[str] = []
        self._setup_ui()
        self._setup_shortcuts()

        if transaction:
            self._load_transaction(transaction)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Edit Transaction" if self._is_edit_mode else "New Transaction")
        self.setMinimumSize(500, 650)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("Edit Transaction" if self._is_edit_mode else "New Transaction")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        close_btn = QPushButton("\u00D7")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 20px;
                color: #757575;
            }
            QPushButton:hover {
                color: #212121;
            }
        """)
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self._on_cancel)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Scrollable content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: white; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Type selector
        type_label = QLabel("Transaction Type")
        type_label.setStyleSheet("font-size: 13px; font-weight: 500;")
        content_layout.addWidget(type_label)

        self._type_selector = TypeSelector()
        self._type_selector.type_changed.connect(self._on_type_changed)
        content_layout.addWidget(self._type_selector)

        # Amount
        self._amount_field = AmountInputField()
        content_layout.addWidget(self._amount_field)

        # Description
        self._description_field = TextInputField(
            label="Description",
            placeholder="What was this transaction for?",
            required=True
        )
        content_layout.addWidget(self._description_field)

        # Date
        self._date_field = DateInputField()
        content_layout.addWidget(self._date_field)

        # Category
        self._category_field = CategoryInputField()
        content_layout.addWidget(self._category_field)

        # Account
        self._account_field = AccountInputField()
        content_layout.addWidget(self._account_field)

        # To Account (for transfers)
        self._to_account_field = AccountInputField(label="To Account")
        self._to_account_field.hide()
        content_layout.addWidget(self._to_account_field)

        # Merchant
        self._merchant_field = TextInputField(
            label="Merchant",
            placeholder="Store or business name (optional)",
            required=False
        )
        content_layout.addWidget(self._merchant_field)

        # Tags
        self._tags_field = TagsInputField()
        content_layout.addWidget(self._tags_field)

        # Notes
        self._notes_field = NotesInputField()
        content_layout.addWidget(self._notes_field)

        content_layout.addStretch()

        scroll_area.setWidget(content)
        layout.addWidget(scroll_area, 1)

        # Footer
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

        footer_layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #757575;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        cancel_btn.clicked.connect(self._on_cancel)
        footer_layout.addWidget(cancel_btn)

        # Save button
        self._save_btn = QPushButton("Save Transaction")
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self._save_btn.clicked.connect(self._on_save)
        footer_layout.addWidget(self._save_btn)

        layout.addWidget(footer)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Save with Ctrl+S
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self._on_save)

        # Cancel with Escape
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._on_cancel)

    def _on_type_changed(self, txn_type: TransactionType) -> None:
        """Handle transaction type change."""
        # Show/hide transfer-specific fields
        self._to_account_field.setVisible(txn_type == TransactionType.TRANSFER)

    def _load_transaction(self, txn: Transaction) -> None:
        """Load transaction data into the form."""
        self._type_selector.set_transaction_type(txn.type)
        self._amount_field.set_amount(txn.amount)
        self._description_field.set_text(txn.description)
        self._date_field.set_date(QDate(txn.date.year, txn.date.month, txn.date.day))
        self._category_field.set_category(txn.category)
        self._account_field.set_account(txn.account)

        if txn.to_account:
            self._to_account_field.set_account(txn.to_account)

        if txn.merchant:
            self._merchant_field.set_text(txn.merchant)

        if txn.tags:
            self._tags_field.set_tags(txn.tags)

        if txn.notes:
            self._notes_field.set_notes(txn.notes)

        # Show transfer fields if applicable
        self._on_type_changed(txn.type)

    def _validate(self) -> bool:
        """Validate form inputs."""
        is_valid = True

        # Description required
        if not self._description_field.text().strip():
            self._description_field.set_error("Description is required")
            is_valid = False

        # Category required
        if not self._category_field.category().strip():
            self._category_field.set_error("Category is required")
            is_valid = False

        # Amount must be positive
        if self._amount_field.amount() <= 0:
            self._amount_field.set_error("Amount must be greater than $0.00")
            is_valid = False

        # Account required
        if not self._account_field.account().strip():
            self._account_field.set_error("Account is required")
            is_valid = False

        # To Account required for transfers
        if self._type_selector.transaction_type() == TransactionType.TRANSFER:
            if not self._to_account_field.account().strip():
                self._to_account_field.set_error("Destination account is required")
                is_valid = False

        return is_valid

    def _on_save(self) -> None:
        """Handle save button click."""
        if not self._validate():
            return

        # Build transaction object
        qdate = self._date_field.date()
        txn_date = date(qdate.year(), qdate.month(), qdate.day())

        transaction = Transaction(
            id=self._transaction.id if self._transaction else None,
            date=txn_date,
            type=self._type_selector.transaction_type(),
            category=self._category_field.category().strip(),
            description=self._description_field.text().strip(),
            amount=self._amount_field.amount(),
            account=self._account_field.account().strip(),
            notes=self._notes_field.notes().strip() or None,
            tags=self._tags_field.tags() or None,
            merchant=self._merchant_field.text().strip() or None,
            to_account=self._to_account_field.account().strip() or None
        )

        self.saved.emit(transaction)
        self.accept()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self._has_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to cancel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.cancelled.emit()
        self.reject()

    def _has_changes(self) -> bool:
        """Check if form has unsaved changes."""
        if not self._transaction:
            # New transaction - check if any fields are filled
            return (
                self._description_field.text().strip() != "" or
                self._amount_field.amount() > 0 or
                self._notes_field.notes().strip() != "" or
                len(self._tags_field.tags()) > 0
            )

        # Edit mode - compare with original
        txn = self._transaction
        return (
            self._description_field.text().strip() != txn.description or
            self._amount_field.amount() != txn.amount or
            self._category_field.category() != txn.category or
            self._account_field.account() != txn.account
        )

    def set_categories(self, categories: List[str], recent: Optional[List[str]] = None) -> None:
        """Set available categories."""
        self._categories = categories
        self._category_field.set_categories(categories)
        if recent:
            self._category_field.set_recent_categories(recent)

    def set_accounts(self, accounts: List[str]) -> None:
        """Set available accounts."""
        self._accounts = accounts
        self._account_field.set_accounts(accounts)
        self._to_account_field.set_accounts(accounts)

    def set_tags(self, tags: List[str]) -> None:
        """Set available tags for autocomplete."""
        self._tags = tags
        self._tags_field.set_available_tags(tags)

    def clear_form(self) -> None:
        """Clear form to default state."""
        self._transaction = None
        self._is_edit_mode = False
        self.setWindowTitle("New Transaction")

        self._type_selector.set_transaction_type(TransactionType.EXPENSE)
        self._amount_field.clear()
        self._description_field.clear()
        self._date_field.clear()
        self._category_field.clear()
        self._account_field.clear()
        self._to_account_field.clear()
        self._merchant_field.clear()
        self._tags_field.clear()
        self._notes_field.clear()

        self._description_field.setFocus()

    @property
    def is_edit_mode(self) -> bool:
        """Check if form is in edit mode."""
        return self._is_edit_mode

    @property
    def transaction(self) -> Optional[Transaction]:
        """Get the current transaction being edited."""
        return self._transaction
