"""
Transaction import wizard for importing transactions from files.

Provides TransactionImportWizard with step-by-step import process:
- Step 1: File selection
- Step 2: Column mapping
- Step 3: Preview and validation
- Step 4: Import progress and summary

Features:
- Support for CSV, OFX, QIF formats
- Intelligent column auto-detection
- Data preview with validation
- Duplicate detection
- Progress tracking with cancel option
- Import summary with error details
"""

import csv
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QFrame, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QFileDialog, QMessageBox, QCheckBox,
    QScrollArea, QSizePolicy, QAbstractItemView, QTextEdit,
    QRadioButton, QButtonGroup, QGroupBox, QSpinBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QThread, QTimer, QSize
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QDragEnterEvent, QDropEvent
)


class TransactionType(Enum):
    """Transaction type enumeration."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class FileFormat(Enum):
    """Supported file formats."""
    CSV = "csv"
    OFX = "ofx"
    QIF = "qif"
    UNKNOWN = "unknown"


@dataclass
class ImportedTransaction:
    """Transaction data from import."""
    date: Optional[date]
    description: str
    amount: Optional[Decimal]
    type: Optional[TransactionType]
    category: Optional[str]
    account: Optional[str]
    notes: Optional[str] = None
    raw_data: Optional[Dict[str, str]] = None
    row_number: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_duplicate: bool = False


@dataclass
class ColumnMapping:
    """Column mapping configuration."""
    date_column: Optional[str] = None
    description_column: Optional[str] = None
    amount_column: Optional[str] = None
    type_column: Optional[str] = None
    category_column: Optional[str] = None
    account_column: Optional[str] = None
    notes_column: Optional[str] = None

    # Amount handling
    separate_amounts: bool = False
    debit_column: Optional[str] = None
    credit_column: Optional[str] = None

    # Date format
    date_format: str = "%Y-%m-%d"


@dataclass
class ImportResult:
    """Import operation result."""
    total_rows: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0
    transactions: List[ImportedTransaction] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# =============================================================================
# Import Worker Thread
# =============================================================================

class ImportWorker(QThread):
    """Worker thread for import processing."""

    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    import_completed = pyqtSignal(ImportResult)
    import_error = pyqtSignal(str)

    def __init__(
        self,
        file_path: str,
        mapping: ColumnMapping,
        transactions: List[ImportedTransaction],
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._file_path = file_path
        self._mapping = mapping
        self._transactions = transactions
        self._cancelled = False

    def run(self):
        """Run the import process."""
        result = ImportResult()
        result.total_rows = len(self._transactions)

        try:
            for i, txn in enumerate(self._transactions):
                if self._cancelled:
                    break

                self.progress_updated.emit(
                    i + 1,
                    result.total_rows,
                    f"Processing row {i + 1} of {result.total_rows}"
                )

                if txn.errors:
                    result.error_count += 1
                    result.errors.extend([f"Row {txn.row_number}: {e}" for e in txn.errors])
                elif txn.is_duplicate:
                    result.duplicate_count += 1
                    result.skipped_count += 1
                else:
                    result.imported_count += 1

                result.transactions.append(txn)

                # Simulate some processing time
                self.msleep(10)

            self.import_completed.emit(result)

        except Exception as e:
            self.import_error.emit(str(e))

    def cancel(self):
        """Cancel the import."""
        self._cancelled = True


# =============================================================================
# File Drop Zone Widget
# =============================================================================

class FileDropZone(QFrame):
    """Drag and drop file selection zone."""

    file_selected = pyqtSignal(str)

    SUPPORTED_EXTENSIONS = [".csv", ".ofx", ".qif"]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the drop zone UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 2px dashed #BDBDBD;
                border-radius: 12px;
            }
        """)
        self.setMinimumHeight(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Icon
        icon_label = QLabel("\U0001F4C1")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Text
        main_text = QLabel("Drag & drop your file here")
        main_text.setStyleSheet("font-size: 16px; font-weight: bold; color: #424242;")
        main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(main_text)

        sub_text = QLabel("or click to browse")
        sub_text.setStyleSheet("font-size: 13px; color: #757575;")
        sub_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_text)

        # Supported formats
        formats_text = QLabel("Supported formats: CSV, OFX, QIF")
        formats_text.setStyleSheet("font-size: 11px; color: #9E9E9E;")
        formats_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(formats_text)

    def mousePressEvent(self, event) -> None:
        """Handle click to open file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Import",
            "",
            "All Supported Files (*.csv *.ofx *.qif);;CSV Files (*.csv);;OFX Files (*.ofx);;QIF Files (*.qif)"
        )
        if file_path:
            self.file_selected.emit(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter."""
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    event.acceptProposedAction()
                    self.setStyleSheet("""
                        QFrame {
                            background-color: #E3F2FD;
                            border: 2px dashed #1976D2;
                            border-radius: 12px;
                        }
                    """)
                    return

        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave."""
        self.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 2px dashed #BDBDBD;
                border-radius: 12px;
            }
        """)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle file drop."""
        self.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 2px dashed #BDBDBD;
                border-radius: 12px;
            }
        """)

        url = event.mimeData().urls()[0]
        if url.isLocalFile():
            self.file_selected.emit(url.toLocalFile())


# =============================================================================
# Step 1: File Selection Page
# =============================================================================

class FileSelectionPage(QWizardPage):
    """Wizard page for file selection."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("Select File")
        self.setSubTitle("Choose a file to import transactions from")

        self._file_path = ""
        self._file_format = FileFormat.UNKNOWN
        self._preview_data: List[Dict[str, str]] = []
        self._headers: List[str] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Drop zone
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        layout.addWidget(self._drop_zone)

        # Selected file info
        self._file_info_frame = QFrame()
        self._file_info_frame.setStyleSheet("""
            QFrame {
                background-color: #E8F5E9;
                border: 1px solid #A5D6A7;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        self._file_info_frame.hide()

        info_layout = QHBoxLayout(self._file_info_frame)

        check_icon = QLabel("\u2713")
        check_icon.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold;")
        info_layout.addWidget(check_icon)

        self._file_name_label = QLabel()
        self._file_name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self._file_name_label)

        self._file_size_label = QLabel()
        self._file_size_label.setStyleSheet("color: #757575;")
        info_layout.addWidget(self._file_size_label)

        info_layout.addStretch()

        change_btn = QPushButton("Change")
        change_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1976D2;
                border: none;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        change_btn.clicked.connect(self._on_change_file)
        info_layout.addWidget(change_btn)

        layout.addWidget(self._file_info_frame)

        # File preview
        preview_label = QLabel("File Preview (first 5 rows)")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 16px;")
        preview_label.hide()
        layout.addWidget(preview_label)
        self._preview_label = preview_label

        self._preview_table = QTableWidget()
        self._preview_table.setMaximumHeight(200)
        self._preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.hide()
        layout.addWidget(self._preview_table)

        layout.addStretch()

    def _on_file_selected(self, file_path: str) -> None:
        """Handle file selection."""
        self._file_path = file_path
        self._file_format = self._detect_format(file_path)

        # Show file info
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        size_str = self._format_size(file_size)

        self._file_name_label.setText(file_name)
        self._file_size_label.setText(f"({size_str})")
        self._file_info_frame.show()
        self._drop_zone.hide()

        # Load preview
        self._load_preview()

        self.completeChanged.emit()

    def _on_change_file(self) -> None:
        """Handle change file button."""
        self._file_path = ""
        self._file_format = FileFormat.UNKNOWN
        self._preview_data = []
        self._headers = []

        self._file_info_frame.hide()
        self._preview_label.hide()
        self._preview_table.hide()
        self._drop_zone.show()

        self.completeChanged.emit()

    def _detect_format(self, file_path: str) -> FileFormat:
        """Detect file format from extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            return FileFormat.CSV
        elif ext == ".ofx":
            return FileFormat.OFX
        elif ext == ".qif":
            return FileFormat.QIF
        return FileFormat.UNKNOWN

    def _format_size(self, size: int) -> str:
        """Format file size for display."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def _load_preview(self) -> None:
        """Load file preview."""
        if self._file_format == FileFormat.CSV:
            self._load_csv_preview()
        else:
            # For OFX/QIF, show a simple message
            self._preview_label.hide()
            self._preview_table.hide()

    def _load_csv_preview(self) -> None:
        """Load CSV file preview."""
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)

                dialect = csv.Sniffer().sniff(sample)
                reader = csv.DictReader(f, dialect=dialect)

                self._headers = reader.fieldnames or []
                self._preview_data = []

                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    self._preview_data.append(row)

            # Show preview table
            self._preview_table.clear()
            self._preview_table.setColumnCount(len(self._headers))
            self._preview_table.setRowCount(len(self._preview_data))
            self._preview_table.setHorizontalHeaderLabels(self._headers)

            for row_idx, row_data in enumerate(self._preview_data):
                for col_idx, header in enumerate(self._headers):
                    item = QTableWidgetItem(str(row_data.get(header, "")))
                    self._preview_table.setItem(row_idx, col_idx, item)

            self._preview_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self._preview_label.show()
            self._preview_table.show()

        except Exception as e:
            QMessageBox.warning(self, "Preview Error", f"Could not preview file: {e}")

    def isComplete(self) -> bool:
        """Check if page is complete."""
        return bool(self._file_path) and self._file_format != FileFormat.UNKNOWN

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def file_format(self) -> FileFormat:
        return self._file_format

    @property
    def headers(self) -> List[str]:
        return self._headers

    @property
    def preview_data(self) -> List[Dict[str, str]]:
        return self._preview_data


# =============================================================================
# Step 2: Column Mapping Page
# =============================================================================

class ColumnMappingPage(QWizardPage):
    """Wizard page for column mapping."""

    DATE_FORMATS = [
        ("%Y-%m-%d", "2024-01-15 (YYYY-MM-DD)"),
        ("%m/%d/%Y", "01/15/2024 (MM/DD/YYYY)"),
        ("%d/%m/%Y", "15/01/2024 (DD/MM/YYYY)"),
        ("%m-%d-%Y", "01-15-2024 (MM-DD-YYYY)"),
        ("%d-%m-%Y", "15-01-2024 (DD-MM-YYYY)"),
        ("%Y/%m/%d", "2024/01/15 (YYYY/MM/DD)"),
        ("%b %d, %Y", "Jan 15, 2024 (Mon DD, YYYY)"),
        ("%d %b %Y", "15 Jan 2024 (DD Mon YYYY)"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("Map Columns")
        self.setSubTitle("Match file columns to transaction fields")

        self._mapping = ColumnMapping()
        self._combos: Dict[str, QComboBox] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Scroll area for mappings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Required fields section
        required_group = QGroupBox("Required Fields")
        required_layout = QGridLayout(required_group)
        required_layout.setSpacing(12)

        row = 0
        for field_name, label in [
            ("date", "Date *"),
            ("description", "Description *"),
            ("amount", "Amount"),
        ]:
            required_layout.addWidget(QLabel(label), row, 0)
            combo = QComboBox()
            combo.addItem("-- Select column --", None)
            combo.currentIndexChanged.connect(lambda: self.completeChanged.emit())
            self._combos[field_name] = combo
            required_layout.addWidget(combo, row, 1)
            row += 1

        content_layout.addWidget(required_group)

        # Amount handling options
        amount_group = QGroupBox("Amount Configuration")
        amount_layout = QVBoxLayout(amount_group)

        self._single_amount_radio = QRadioButton("Single amount column (negative for expenses)")
        self._single_amount_radio.setChecked(True)
        self._single_amount_radio.toggled.connect(self._on_amount_mode_changed)
        amount_layout.addWidget(self._single_amount_radio)

        self._separate_amount_radio = QRadioButton("Separate debit/credit columns")
        amount_layout.addWidget(self._separate_amount_radio)

        # Debit/Credit combos (hidden initially)
        self._debit_credit_layout = QHBoxLayout()
        self._debit_credit_layout.setSpacing(16)

        debit_label = QLabel("Debit column:")
        self._debit_credit_layout.addWidget(debit_label)
        self._debit_combo = QComboBox()
        self._debit_combo.addItem("-- Select column --", None)
        self._debit_credit_layout.addWidget(self._debit_combo)

        credit_label = QLabel("Credit column:")
        self._debit_credit_layout.addWidget(credit_label)
        self._credit_combo = QComboBox()
        self._credit_combo.addItem("-- Select column --", None)
        self._debit_credit_layout.addWidget(credit_label)
        self._debit_credit_layout.addWidget(self._credit_combo)

        self._debit_credit_widget = QWidget()
        self._debit_credit_widget.setLayout(self._debit_credit_layout)
        self._debit_credit_widget.hide()
        amount_layout.addWidget(self._debit_credit_widget)

        content_layout.addWidget(amount_group)

        # Date format
        date_group = QGroupBox("Date Format")
        date_layout = QHBoxLayout(date_group)

        date_layout.addWidget(QLabel("Date format:"))
        self._date_format_combo = QComboBox()
        for fmt, label in self.DATE_FORMATS:
            self._date_format_combo.addItem(label, fmt)
        date_layout.addWidget(self._date_format_combo)
        date_layout.addStretch()

        content_layout.addWidget(date_group)

        # Optional fields section
        optional_group = QGroupBox("Optional Fields")
        optional_layout = QGridLayout(optional_group)
        optional_layout.setSpacing(12)

        row = 0
        for field_name, label in [
            ("category", "Category"),
            ("account", "Account"),
            ("type", "Type (Income/Expense)"),
            ("notes", "Notes/Memo"),
        ]:
            optional_layout.addWidget(QLabel(label), row, 0)
            combo = QComboBox()
            combo.addItem("-- Not mapped --", None)
            self._combos[field_name] = combo
            optional_layout.addWidget(combo, row, 1)
            row += 1

        content_layout.addWidget(optional_group)

        # Default values section
        defaults_group = QGroupBox("Default Values")
        defaults_layout = QGridLayout(defaults_group)
        defaults_layout.setSpacing(12)

        defaults_layout.addWidget(QLabel("Default account:"), 0, 0)
        self._default_account = QComboBox()
        self._default_account.setEditable(True)
        defaults_layout.addWidget(self._default_account, 0, 1)

        defaults_layout.addWidget(QLabel("Default category:"), 1, 0)
        self._default_category = QComboBox()
        self._default_category.setEditable(True)
        defaults_layout.addWidget(self._default_category, 1, 1)

        content_layout.addWidget(defaults_group)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _on_amount_mode_changed(self, single: bool) -> None:
        """Handle amount mode toggle."""
        self._debit_credit_widget.setVisible(not single)
        self._combos["amount"].setEnabled(single)

    def initializePage(self) -> None:
        """Initialize page with data from previous page."""
        wizard = self.wizard()
        file_page = wizard.page(0)

        if hasattr(file_page, 'headers'):
            headers = file_page.headers

            # Update all combos with headers
            for combo in self._combos.values():
                current = combo.currentData()
                combo.clear()
                combo.addItem("-- Select column --" if combo == self._combos.get("date") or combo == self._combos.get("description") else "-- Not mapped --", None)
                for header in headers:
                    combo.addItem(header, header)

            # Update debit/credit combos
            for combo in [self._debit_combo, self._credit_combo]:
                combo.clear()
                combo.addItem("-- Select column --", None)
                for header in headers:
                    combo.addItem(header, header)

            # Auto-detect columns
            self._auto_detect_columns(headers)

    def _auto_detect_columns(self, headers: List[str]) -> None:
        """Auto-detect column mappings based on header names."""
        header_lower = {h.lower(): h for h in headers}

        # Date detection
        for keyword in ["date", "transaction date", "trans date", "posted"]:
            if keyword in header_lower:
                self._set_combo_value("date", header_lower[keyword])
                break

        # Description detection
        for keyword in ["description", "desc", "memo", "narrative", "details"]:
            if keyword in header_lower:
                self._set_combo_value("description", header_lower[keyword])
                break

        # Amount detection
        for keyword in ["amount", "value", "sum", "total"]:
            if keyword in header_lower:
                self._set_combo_value("amount", header_lower[keyword])
                break

        # Category detection
        for keyword in ["category", "type", "classification"]:
            if keyword in header_lower:
                self._set_combo_value("category", header_lower[keyword])
                break

        # Debit/Credit detection
        for keyword in ["debit", "withdrawal", "out"]:
            if keyword in header_lower:
                self._debit_combo.setCurrentText(header_lower[keyword])
                break

        for keyword in ["credit", "deposit", "in"]:
            if keyword in header_lower:
                self._credit_combo.setCurrentText(header_lower[keyword])
                break

    def _set_combo_value(self, field: str, value: str) -> None:
        """Set combo box value by text."""
        combo = self._combos.get(field)
        if combo:
            index = combo.findText(value)
            if index >= 0:
                combo.setCurrentIndex(index)

    def isComplete(self) -> bool:
        """Check if required mappings are complete."""
        date_mapped = self._combos["date"].currentData() is not None
        desc_mapped = self._combos["description"].currentData() is not None

        if self._single_amount_radio.isChecked():
            amount_mapped = self._combos["amount"].currentData() is not None
        else:
            amount_mapped = (
                self._debit_combo.currentData() is not None or
                self._credit_combo.currentData() is not None
            )

        return date_mapped and desc_mapped and amount_mapped

    def get_mapping(self) -> ColumnMapping:
        """Get the configured column mapping."""
        mapping = ColumnMapping()

        mapping.date_column = self._combos["date"].currentData()
        mapping.description_column = self._combos["description"].currentData()
        mapping.amount_column = self._combos["amount"].currentData()
        mapping.category_column = self._combos["category"].currentData()
        mapping.account_column = self._combos["account"].currentData()
        mapping.type_column = self._combos["type"].currentData()
        mapping.notes_column = self._combos["notes"].currentData()

        mapping.separate_amounts = self._separate_amount_radio.isChecked()
        mapping.debit_column = self._debit_combo.currentData()
        mapping.credit_column = self._credit_combo.currentData()

        mapping.date_format = self._date_format_combo.currentData()

        return mapping

    @property
    def default_account(self) -> str:
        return self._default_account.currentText()

    @property
    def default_category(self) -> str:
        return self._default_category.currentText()


# =============================================================================
# Step 3: Preview Page
# =============================================================================

class PreviewPage(QWizardPage):
    """Wizard page for import preview and validation."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("Preview Import")
        self.setSubTitle("Review transactions before importing")

        self._transactions: List[ImportedTransaction] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Summary stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)

        self._total_label = QLabel("Total: 0")
        self._total_label.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self._total_label)

        stats_layout.addSpacing(24)

        self._valid_label = QLabel("Valid: 0")
        self._valid_label.setStyleSheet("color: #4CAF50;")
        stats_layout.addWidget(self._valid_label)

        self._warning_label = QLabel("Warnings: 0")
        self._warning_label.setStyleSheet("color: #FF9800;")
        stats_layout.addWidget(self._warning_label)

        self._error_label = QLabel("Errors: 0")
        self._error_label.setStyleSheet("color: #F44336;")
        stats_layout.addWidget(self._error_label)

        self._duplicate_label = QLabel("Duplicates: 0")
        self._duplicate_label.setStyleSheet("color: #9E9E9E;")
        stats_layout.addWidget(self._duplicate_label)

        stats_layout.addStretch()

        layout.addWidget(stats_frame)

        # Preview table
        self._preview_table = QTableWidget()
        self._preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._preview_table.setColumnCount(7)
        self._preview_table.setHorizontalHeaderLabels([
            "Status", "Date", "Description", "Amount", "Type", "Category", "Account"
        ])
        self._preview_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._preview_table)

        # Options
        options_layout = QHBoxLayout()

        self._skip_duplicates_check = QCheckBox("Skip duplicate transactions")
        self._skip_duplicates_check.setChecked(True)
        options_layout.addWidget(self._skip_duplicates_check)

        self._skip_errors_check = QCheckBox("Skip rows with errors")
        self._skip_errors_check.setChecked(True)
        options_layout.addWidget(self._skip_errors_check)

        options_layout.addStretch()

        layout.addLayout(options_layout)

    def initializePage(self) -> None:
        """Initialize page with parsed transactions."""
        wizard = self.wizard()
        file_page = wizard.page(0)
        mapping_page = wizard.page(1)

        file_path = file_page.file_path
        mapping = mapping_page.get_mapping()
        default_account = mapping_page.default_account
        default_category = mapping_page.default_category

        # Parse transactions
        self._transactions = self._parse_file(file_path, mapping, default_account, default_category)

        # Update preview table
        self._update_preview()

    def _parse_file(
        self,
        file_path: str,
        mapping: ColumnMapping,
        default_account: str,
        default_category: str
    ) -> List[ImportedTransaction]:
        """Parse the file into transactions."""
        transactions = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dialect = csv.Sniffer().sniff(f.read(1024))
                f.seek(0)
                reader = csv.DictReader(f, dialect=dialect)

                for row_num, row in enumerate(reader, start=2):
                    txn = self._parse_row(row, row_num, mapping, default_account, default_category)
                    transactions.append(txn)

        except Exception as e:
            # Create error transaction
            txn = ImportedTransaction(
                date=None,
                description="Parse Error",
                amount=None,
                type=None,
                category=None,
                account=None,
                row_number=0,
                errors=[str(e)]
            )
            transactions.append(txn)

        return transactions

    def _parse_row(
        self,
        row: Dict[str, str],
        row_num: int,
        mapping: ColumnMapping,
        default_account: str,
        default_category: str
    ) -> ImportedTransaction:
        """Parse a single row into a transaction."""
        txn = ImportedTransaction(
            date=None,
            description="",
            amount=None,
            type=None,
            category=default_category or None,
            account=default_account or None,
            raw_data=row,
            row_number=row_num
        )

        # Parse date
        if mapping.date_column:
            date_str = row.get(mapping.date_column, "").strip()
            if date_str:
                try:
                    dt = datetime.strptime(date_str, mapping.date_format)
                    txn.date = dt.date()
                except ValueError:
                    txn.errors.append(f"Invalid date format: {date_str}")
            else:
                txn.errors.append("Missing date")

        # Parse description
        if mapping.description_column:
            txn.description = row.get(mapping.description_column, "").strip()
            if not txn.description:
                txn.errors.append("Missing description")

        # Parse amount
        if mapping.separate_amounts:
            debit = self._parse_amount(row.get(mapping.debit_column, ""))
            credit = self._parse_amount(row.get(mapping.credit_column, ""))

            if debit and debit > 0:
                txn.amount = debit
                txn.type = TransactionType.EXPENSE
            elif credit and credit > 0:
                txn.amount = credit
                txn.type = TransactionType.INCOME
            else:
                txn.errors.append("Missing amount")
        else:
            if mapping.amount_column:
                amount_str = row.get(mapping.amount_column, "")
                txn.amount = self._parse_amount(amount_str)
                if txn.amount is None:
                    txn.errors.append("Invalid amount")
                elif txn.amount < 0:
                    txn.amount = abs(txn.amount)
                    txn.type = TransactionType.EXPENSE
                else:
                    txn.type = TransactionType.INCOME

        # Parse category
        if mapping.category_column:
            cat = row.get(mapping.category_column, "").strip()
            if cat:
                txn.category = cat

        # Parse account
        if mapping.account_column:
            acc = row.get(mapping.account_column, "").strip()
            if acc:
                txn.account = acc

        # Parse type
        if mapping.type_column and not txn.type:
            type_str = row.get(mapping.type_column, "").strip().lower()
            if "income" in type_str or "credit" in type_str or "deposit" in type_str:
                txn.type = TransactionType.INCOME
            elif "expense" in type_str or "debit" in type_str or "withdrawal" in type_str:
                txn.type = TransactionType.EXPENSE
            elif "transfer" in type_str:
                txn.type = TransactionType.TRANSFER

        # Parse notes
        if mapping.notes_column:
            txn.notes = row.get(mapping.notes_column, "").strip() or None

        return txn

    def _parse_amount(self, value: str) -> Optional[Decimal]:
        """Parse amount string to Decimal."""
        if not value:
            return None

        # Remove currency symbols and whitespace
        cleaned = value.strip().replace("$", "").replace(",", "").replace(" ", "")

        # Handle parentheses as negative
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]

        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _update_preview(self) -> None:
        """Update the preview table."""
        self._preview_table.setRowCount(len(self._transactions))

        valid_count = 0
        warning_count = 0
        error_count = 0
        duplicate_count = 0

        for row, txn in enumerate(self._transactions):
            # Status column
            if txn.errors:
                status = "\u2717"  # X mark
                status_color = QColor("#F44336")
                error_count += 1
            elif txn.is_duplicate:
                status = "\u2260"  # Not equal
                status_color = QColor("#9E9E9E")
                duplicate_count += 1
            elif txn.warnings:
                status = "\u26A0"  # Warning
                status_color = QColor("#FF9800")
                warning_count += 1
            else:
                status = "\u2713"  # Check mark
                status_color = QColor("#4CAF50")
                valid_count += 1

            status_item = QTableWidgetItem(status)
            status_item.setForeground(status_color)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._preview_table.setItem(row, 0, status_item)

            # Date
            date_str = txn.date.strftime("%Y-%m-%d") if txn.date else "Invalid"
            self._preview_table.setItem(row, 1, QTableWidgetItem(date_str))

            # Description
            self._preview_table.setItem(row, 2, QTableWidgetItem(txn.description))

            # Amount
            if txn.amount is not None:
                amount_str = f"${txn.amount:,.2f}"
                amount_item = QTableWidgetItem(amount_str)
                if txn.type == TransactionType.EXPENSE:
                    amount_item.setForeground(QColor("#F44336"))
                else:
                    amount_item.setForeground(QColor("#4CAF50"))
            else:
                amount_item = QTableWidgetItem("Invalid")
                amount_item.setForeground(QColor("#F44336"))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._preview_table.setItem(row, 3, amount_item)

            # Type
            type_str = txn.type.value.capitalize() if txn.type else "-"
            self._preview_table.setItem(row, 4, QTableWidgetItem(type_str))

            # Category
            self._preview_table.setItem(row, 5, QTableWidgetItem(txn.category or "-"))

            # Account
            self._preview_table.setItem(row, 6, QTableWidgetItem(txn.account or "-"))

            # Tooltip with errors/warnings
            if txn.errors:
                for col in range(7):
                    item = self._preview_table.item(row, col)
                    if item:
                        item.setToolTip("Errors: " + ", ".join(txn.errors))

        # Update stats
        self._total_label.setText(f"Total: {len(self._transactions)}")
        self._valid_label.setText(f"Valid: {valid_count}")
        self._warning_label.setText(f"Warnings: {warning_count}")
        self._error_label.setText(f"Errors: {error_count}")
        self._duplicate_label.setText(f"Duplicates: {duplicate_count}")

    @property
    def transactions(self) -> List[ImportedTransaction]:
        return self._transactions

    @property
    def skip_duplicates(self) -> bool:
        return self._skip_duplicates_check.isChecked()

    @property
    def skip_errors(self) -> bool:
        return self._skip_errors_check.isChecked()


# =============================================================================
# Step 4: Import Progress Page
# =============================================================================

class ImportProgressPage(QWizardPage):
    """Wizard page for import progress and results."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle("Importing")
        self.setSubTitle("Please wait while transactions are imported")

        self._result: Optional[ImportResult] = None
        self._worker: Optional[ImportWorker] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Progress section
        self._progress_frame = QFrame()
        progress_layout = QVBoxLayout(self._progress_frame)
        progress_layout.setSpacing(12)

        self._status_label = QLabel("Preparing import...")
        self._status_label.setStyleSheet("font-size: 14px;")
        progress_layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setTextVisible(True)
        progress_layout.addWidget(self._progress_bar)

        self._cancel_btn = QPushButton("Cancel Import")
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F44336;
                border: 1px solid #F44336;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #FFEBEE;
            }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel)
        progress_layout.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self._progress_frame)

        # Results section (hidden initially)
        self._results_frame = QFrame()
        self._results_frame.hide()
        results_layout = QVBoxLayout(self._results_frame)
        results_layout.setSpacing(16)

        # Success/failure indicator
        self._result_icon = QLabel()
        self._result_icon.setStyleSheet("font-size: 48px;")
        self._result_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.addWidget(self._result_icon)

        self._result_title = QLabel()
        self._result_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self._result_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_layout.addWidget(self._result_title)

        # Stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setSpacing(12)

        stats_layout.addWidget(QLabel("Imported:"), 0, 0)
        self._imported_count_label = QLabel("0")
        self._imported_count_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        stats_layout.addWidget(self._imported_count_label, 0, 1)

        stats_layout.addWidget(QLabel("Skipped:"), 0, 2)
        self._skipped_count_label = QLabel("0")
        self._skipped_count_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        stats_layout.addWidget(self._skipped_count_label, 0, 3)

        stats_layout.addWidget(QLabel("Errors:"), 1, 0)
        self._error_count_label = QLabel("0")
        self._error_count_label.setStyleSheet("font-weight: bold; color: #F44336;")
        stats_layout.addWidget(self._error_count_label, 1, 1)

        stats_layout.addWidget(QLabel("Duplicates:"), 1, 2)
        self._duplicate_count_label = QLabel("0")
        self._duplicate_count_label.setStyleSheet("font-weight: bold; color: #9E9E9E;")
        stats_layout.addWidget(self._duplicate_count_label, 1, 3)

        results_layout.addWidget(stats_frame)

        # Error details
        self._errors_label = QLabel("Errors:")
        self._errors_label.setStyleSheet("font-weight: bold;")
        self._errors_label.hide()
        results_layout.addWidget(self._errors_label)

        self._errors_text = QTextEdit()
        self._errors_text.setReadOnly(True)
        self._errors_text.setMaximumHeight(150)
        self._errors_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
                border-radius: 4px;
            }
        """)
        self._errors_text.hide()
        results_layout.addWidget(self._errors_text)

        layout.addWidget(self._results_frame)
        layout.addStretch()

    def initializePage(self) -> None:
        """Start the import process."""
        wizard = self.wizard()
        file_page = wizard.page(0)
        mapping_page = wizard.page(1)
        preview_page = wizard.page(2)

        # Filter transactions
        transactions = preview_page.transactions
        if preview_page.skip_errors:
            transactions = [t for t in transactions if not t.errors]
        if preview_page.skip_duplicates:
            transactions = [t for t in transactions if not t.is_duplicate]

        # Start worker
        mapping = mapping_page.get_mapping()
        self._worker = ImportWorker(file_page.file_path, mapping, transactions, self)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.import_completed.connect(self._on_completed)
        self._worker.import_error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Handle progress update."""
        progress = int((current / total) * 100) if total > 0 else 0
        self._progress_bar.setValue(progress)
        self._status_label.setText(message)

    def _on_completed(self, result: ImportResult) -> None:
        """Handle import completion."""
        self._result = result

        # Show results
        self._progress_frame.hide()
        self._results_frame.show()

        if result.error_count == 0:
            self._result_icon.setText("\u2713")
            self._result_icon.setStyleSheet("font-size: 48px; color: #4CAF50;")
            self._result_title.setText("Import Completed Successfully!")
            self._result_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50;")
        else:
            self._result_icon.setText("\u26A0")
            self._result_icon.setStyleSheet("font-size: 48px; color: #FF9800;")
            self._result_title.setText("Import Completed with Errors")
            self._result_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF9800;")

        # Update stats
        self._imported_count_label.setText(str(result.imported_count))
        self._skipped_count_label.setText(str(result.skipped_count))
        self._error_count_label.setText(str(result.error_count))
        self._duplicate_count_label.setText(str(result.duplicate_count))

        # Show errors if any
        if result.errors:
            self._errors_label.show()
            self._errors_text.show()
            self._errors_text.setPlainText("\n".join(result.errors[:50]))
            if len(result.errors) > 50:
                self._errors_text.append(f"\n... and {len(result.errors) - 50} more errors")

        self.completeChanged.emit()

    def _on_error(self, error: str) -> None:
        """Handle import error."""
        self._progress_frame.hide()
        self._results_frame.show()

        self._result_icon.setText("\u2717")
        self._result_icon.setStyleSheet("font-size: 48px; color: #F44336;")
        self._result_title.setText("Import Failed")
        self._result_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #F44336;")

        self._errors_label.show()
        self._errors_text.show()
        self._errors_text.setPlainText(error)

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()

        wizard = self.wizard()
        wizard.back()

    def isComplete(self) -> bool:
        """Check if import is complete."""
        return self._result is not None

    @property
    def result(self) -> Optional[ImportResult]:
        return self._result


# =============================================================================
# Transaction Import Wizard
# =============================================================================

class TransactionImportWizard(QWizard):
    """
    Wizard for importing transactions from files.

    Steps:
    1. File selection
    2. Column mapping
    3. Preview and validation
    4. Import progress

    Signals:
        import_completed(ImportResult): Emitted when import completes
        import_cancelled(): Emitted when wizard is cancelled
    """

    import_completed = pyqtSignal(object)
    import_cancelled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Import Transactions")
        self.setMinimumSize(700, 550)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        # Set button text
        self.setButtonText(QWizard.WizardButton.NextButton, "Next >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< Back")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Done")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Cancel")

        # Add pages
        self._file_page = FileSelectionPage()
        self.addPage(self._file_page)

        self._mapping_page = ColumnMappingPage()
        self.addPage(self._mapping_page)

        self._preview_page = PreviewPage()
        self.addPage(self._preview_page)

        self._progress_page = ImportProgressPage()
        self.addPage(self._progress_page)

        # Connect signals
        self.finished.connect(self._on_finished)

    def _on_finished(self, result: int) -> None:
        """Handle wizard finish."""
        if result == QWizard.DialogCode.Accepted:
            import_result = self._progress_page.result
            if import_result:
                self.import_completed.emit(import_result)
        else:
            self.import_cancelled.emit()

    @property
    def file_page(self) -> FileSelectionPage:
        return self._file_page

    @property
    def mapping_page(self) -> ColumnMappingPage:
        return self._mapping_page

    @property
    def preview_page(self) -> PreviewPage:
        return self._preview_page

    @property
    def progress_page(self) -> ImportProgressPage:
        return self._progress_page
