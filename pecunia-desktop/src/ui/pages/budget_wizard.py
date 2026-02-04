"""
Budget Wizard Module

Multi-step wizard dialog for creating and configuring budgets.
Includes steps for general info, category allocation, alerts, and review.
"""

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit,
    QDateEdit, QCheckBox, QGroupBox, QScrollArea, QSlider,
    QListWidget, QListWidgetItem, QProgressBar, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStackedWidget, QMessageBox, QSplitter, QRadioButton,
    QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QBrush, QPen
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, date


class WizardPageBase(QWizardPage):
    """Base class for wizard pages with common styling."""

    def __init__(self, title: str, subtitle: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setTitle(title)
        self.setSubTitle(subtitle)
        self._setup_base_style()

    def _setup_base_style(self):
        """Apply base styling to the wizard page."""
        self.setStyleSheet("""
            QWizardPage {
                background-color: #FAFAFA;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {
                padding: 8px 12px;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                background-color: #FFFFFF;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
            QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #2196F3;
                border-width: 2px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)


class GeneralInfoPage(WizardPageBase):
    """
    Step 1: General Budget Information

    Collects basic budget details:
    - Budget name
    - Period type (weekly, monthly, quarterly, yearly)
    - Start and end dates
    - Total budget amount
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            "Budget Information",
            "Enter the basic details for your budget",
            parent
        )
        self._setup_ui()
        self._register_fields()

    def _setup_ui(self):
        """Set up the general info page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Form container
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(25, 25, 25, 25)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Budget name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Monthly Household Budget")
        self.name_input.setMinimumWidth(350)
        form_layout.addRow("Budget Name *", self.name_input)

        # Period type
        period_widget = QWidget()
        period_layout = QHBoxLayout(period_widget)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.setSpacing(10)

        self.period_group = QButtonGroup(self)
        periods = [
            ("Weekly", "weekly"),
            ("Monthly", "monthly"),
            ("Quarterly", "quarterly"),
            ("Yearly", "yearly")
        ]

        for text, value in periods:
            btn = QRadioButton(text)
            btn.setProperty("period_value", value)
            btn.setStyleSheet("""
                QRadioButton {
                    padding: 10px 20px;
                    border: 2px solid #E0E0E0;
                    border-radius: 6px;
                    background-color: #FFFFFF;
                }
                QRadioButton:checked {
                    border-color: #2196F3;
                    background-color: #E3F2FD;
                }
                QRadioButton:hover {
                    border-color: #90CAF9;
                }
                QRadioButton::indicator {
                    width: 0px;
                    height: 0px;
                }
            """)
            self.period_group.addButton(btn)
            period_layout.addWidget(btn)
            if value == "monthly":
                btn.setChecked(True)

        period_layout.addStretch()
        form_layout.addRow("Period *", period_widget)

        # Date range
        date_widget = QWidget()
        date_layout = QHBoxLayout(date_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(15)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setMinimumWidth(150)
        date_layout.addWidget(QLabel("Start:"))
        date_layout.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate().addMonths(1))
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setMinimumWidth(150)
        date_layout.addWidget(QLabel("End:"))
        date_layout.addWidget(self.end_date)

        date_layout.addStretch()
        form_layout.addRow("Date Range *", date_widget)

        # Total budget amount
        amount_widget = QWidget()
        amount_layout = QHBoxLayout(amount_widget)
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(5)

        currency_label = QLabel("$")
        currency_label.setFont(QFont("Segoe UI", 14))
        amount_layout.addWidget(currency_label)

        self.total_amount = QDoubleSpinBox()
        self.total_amount.setPrefix("")
        self.total_amount.setDecimals(2)
        self.total_amount.setMaximum(999999999.99)
        self.total_amount.setMinimum(0.01)
        self.total_amount.setValue(1000.00)
        self.total_amount.setMinimumWidth(200)
        self.total_amount.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 16px;
                font-weight: bold;
            }
        """)
        amount_layout.addWidget(self.total_amount)
        amount_layout.addStretch()

        form_layout.addRow("Total Budget *", amount_widget)

        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Optional description or notes about this budget...")
        self.description_input.setMaximumHeight(80)
        form_layout.addRow("Description", self.description_input)

        layout.addWidget(form_frame)

        # Period auto-calculation note
        note_label = QLabel(
            "Tip: The end date will be automatically calculated based on the selected "
            "period when you click Next."
        )
        note_label.setStyleSheet("color: #666666; font-style: italic; font-size: 11px;")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        layout.addStretch()

        # Connect period change to update end date
        self.period_group.buttonClicked.connect(self._update_end_date)
        self.start_date.dateChanged.connect(self._update_end_date)

    def _register_fields(self):
        """Register fields for wizard access."""
        self.registerField("budget_name*", self.name_input)
        self.registerField("total_amount", self.total_amount, "value")
        self.registerField("start_date", self.start_date, "date")
        self.registerField("end_date", self.end_date, "date")

    def _update_end_date(self):
        """Update end date based on period selection."""
        checked_btn = self.period_group.checkedButton()
        if not checked_btn:
            return

        period = checked_btn.property("period_value")
        start = self.start_date.date()

        if period == "weekly":
            self.end_date.setDate(start.addDays(7))
        elif period == "monthly":
            self.end_date.setDate(start.addMonths(1))
        elif period == "quarterly":
            self.end_date.setDate(start.addMonths(3))
        elif period == "yearly":
            self.end_date.setDate(start.addYears(1))

    def get_period(self) -> str:
        """Get the selected period."""
        checked_btn = self.period_group.checkedButton()
        return checked_btn.property("period_value") if checked_btn else "monthly"

    def validatePage(self) -> bool:
        """Validate the page data."""
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a budget name."
            )
            self.name_input.setFocus()
            return False

        if self.total_amount.value() <= 0:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a valid budget amount."
            )
            self.total_amount.setFocus()
            return False

        if self.end_date.date() <= self.start_date.date():
            QMessageBox.warning(
                self,
                "Validation Error",
                "End date must be after start date."
            )
            self.end_date.setFocus()
            return False

        return True


class CategoryAllocationPage(WizardPageBase):
    """
    Step 2: Category Allocation

    Allows allocating budget amounts to different spending categories.
    Features:
    - Add/remove categories
    - Set amounts per category
    - Visual progress showing total allocation
    """

    allocation_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            "Category Allocation",
            "Distribute your budget across spending categories",
            parent
        )
        self._categories: List[Dict[str, Any]] = []
        self._allocations: List[Dict[str, Any]] = []
        self._total_budget = Decimal("1000.00")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the category allocation page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Summary bar
        summary_frame = QFrame()
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(20, 15, 20, 15)

        summary_layout.addWidget(QLabel("Total Budget:"))
        self.total_label = QLabel("$1,000.00")
        self.total_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.total_label.setStyleSheet("color: #1976D2;")
        summary_layout.addWidget(self.total_label)

        summary_layout.addSpacing(30)

        summary_layout.addWidget(QLabel("Allocated:"))
        self.allocated_label = QLabel("$0.00")
        self.allocated_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.allocated_label.setStyleSheet("color: #4CAF50;")
        summary_layout.addWidget(self.allocated_label)

        summary_layout.addSpacing(30)

        summary_layout.addWidget(QLabel("Remaining:"))
        self.remaining_label = QLabel("$1,000.00")
        self.remaining_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.remaining_label.setStyleSheet("color: #FF9800;")
        summary_layout.addWidget(self.remaining_label)

        summary_layout.addStretch()

        # Allocation progress
        self.allocation_progress = QProgressBar()
        self.allocation_progress.setMaximum(100)
        self.allocation_progress.setValue(0)
        self.allocation_progress.setMinimumWidth(200)
        self.allocation_progress.setMaximumHeight(20)
        self.allocation_progress.setFormat("%p% allocated")
        self.allocation_progress.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border-radius: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 6px;
            }
        """)
        summary_layout.addWidget(self.allocation_progress)

        layout.addWidget(summary_frame)

        # Main content - Categories and allocation
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Available categories
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QLabel("Available Categories")
        left_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        left_layout.addWidget(left_header)

        self.category_list = QListWidget()
        self.category_list.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
        """)
        self.category_list.itemDoubleClicked.connect(self._add_category_to_allocation)
        left_layout.addWidget(self.category_list)

        add_btn = QPushButton("Add Selected Category")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_btn.clicked.connect(self._add_selected_category)
        left_layout.addWidget(add_btn)

        content_splitter.addWidget(left_widget)

        # Right side - Allocation table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_header = QLabel("Budget Allocations")
        right_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        right_layout.addWidget(right_header)

        self.allocation_table = QTableWidget()
        self.allocation_table.setColumnCount(4)
        self.allocation_table.setHorizontalHeaderLabels([
            "Category", "Amount", "% of Budget", "Actions"
        ])

        header = self.allocation_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 150)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 100)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 80)

        self.allocation_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.allocation_table.verticalHeader().setVisible(False)
        self.allocation_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        right_layout.addWidget(self.allocation_table)

        # Quick allocation buttons
        quick_layout = QHBoxLayout()

        distribute_btn = QPushButton("Distribute Evenly")
        distribute_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        distribute_btn.clicked.connect(self._distribute_evenly)
        quick_layout.addWidget(distribute_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        clear_btn.clicked.connect(self._clear_allocations)
        quick_layout.addWidget(clear_btn)

        quick_layout.addStretch()
        right_layout.addLayout(quick_layout)

        content_splitter.addWidget(right_widget)
        content_splitter.setSizes([300, 500])

        layout.addWidget(content_splitter)

    def initializePage(self):
        """Initialize page when shown."""
        # Get total budget from previous page
        total = self.field("total_amount")
        if total:
            self._total_budget = Decimal(str(total))
            self.total_label.setText(f"${self._total_budget:,.2f}")
            self.remaining_label.setText(f"${self._total_budget:,.2f}")

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self._categories = categories
        self.category_list.clear()

        for cat in categories:
            item = QListWidgetItem(cat.get('name', 'Unknown'))
            item.setData(Qt.ItemDataRole.UserRole, cat)
            self.category_list.addItem(item)

    def _add_selected_category(self):
        """Add the selected category to allocations."""
        current_item = self.category_list.currentItem()
        if current_item:
            self._add_category_to_allocation(current_item)

    def _add_category_to_allocation(self, item: QListWidgetItem):
        """Add a category to the allocation table."""
        category = item.data(Qt.ItemDataRole.UserRole)
        if not category:
            return

        # Check if already added
        for alloc in self._allocations:
            if alloc.get('category_id') == category.get('id'):
                QMessageBox.information(
                    self,
                    "Already Added",
                    f"'{category.get('name')}' is already in your allocations."
                )
                return

        # Add to allocations
        allocation = {
            'category_id': category.get('id'),
            'category_name': category.get('name'),
            'amount': Decimal('0.00'),
            'color': category.get('color', '#888888')
        }
        self._allocations.append(allocation)
        self._refresh_allocation_table()

    def _refresh_allocation_table(self):
        """Refresh the allocation table."""
        self.allocation_table.setRowCount(len(self._allocations))

        for row, alloc in enumerate(self._allocations):
            # Category name
            name_item = QTableWidgetItem(alloc['category_name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.allocation_table.setItem(row, 0, name_item)

            # Amount input
            amount_spin = QDoubleSpinBox()
            amount_spin.setPrefix("$ ")
            amount_spin.setDecimals(2)
            amount_spin.setMaximum(float(self._total_budget))
            amount_spin.setValue(float(alloc['amount']))
            amount_spin.valueChanged.connect(
                lambda val, r=row: self._on_amount_changed(r, val)
            )
            self.allocation_table.setCellWidget(row, 1, amount_spin)

            # Percentage
            percentage = (
                (alloc['amount'] / self._total_budget * 100)
                if self._total_budget > 0 else 0
            )
            pct_item = QTableWidgetItem(f"{percentage:.1f}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pct_item.setFlags(pct_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.allocation_table.setItem(row, 2, pct_item)

            # Remove button
            remove_btn = QPushButton("X")
            remove_btn.setFixedSize(30, 30)
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFEBEE;
                    color: #F44336;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FFCDD2;
                }
            """)
            remove_btn.clicked.connect(lambda checked, r=row: self._remove_allocation(r))
            self.allocation_table.setCellWidget(row, 3, remove_btn)

            self.allocation_table.setRowHeight(row, 50)

        self._update_summary()

    def _on_amount_changed(self, row: int, value: float):
        """Handle amount change in allocation."""
        if 0 <= row < len(self._allocations):
            self._allocations[row]['amount'] = Decimal(str(value))
            self._update_summary()
            self._update_percentage_cell(row)

    def _update_percentage_cell(self, row: int):
        """Update the percentage cell for a row."""
        if 0 <= row < len(self._allocations):
            alloc = self._allocations[row]
            percentage = (
                (alloc['amount'] / self._total_budget * 100)
                if self._total_budget > 0 else 0
            )
            pct_item = self.allocation_table.item(row, 2)
            if pct_item:
                pct_item.setText(f"{percentage:.1f}%")

    def _update_summary(self):
        """Update the allocation summary."""
        total_allocated = sum(a['amount'] for a in self._allocations)
        remaining = self._total_budget - total_allocated
        percentage = int(
            (total_allocated / self._total_budget * 100)
            if self._total_budget > 0 else 0
        )

        self.allocated_label.setText(f"${total_allocated:,.2f}")

        if remaining >= 0:
            self.remaining_label.setText(f"${remaining:,.2f}")
            self.remaining_label.setStyleSheet("color: #FF9800;")
        else:
            self.remaining_label.setText(f"-${abs(remaining):,.2f}")
            self.remaining_label.setStyleSheet("color: #F44336; font-weight: bold;")

        self.allocation_progress.setValue(min(percentage, 100))

        if percentage > 100:
            self.allocation_progress.setStyleSheet("""
                QProgressBar {
                    background-color: #E0E0E0;
                    border-radius: 6px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #F44336;
                    border-radius: 6px;
                }
            """)
        else:
            self.allocation_progress.setStyleSheet("""
                QProgressBar {
                    background-color: #E0E0E0;
                    border-radius: 6px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 6px;
                }
            """)

        self.allocation_changed.emit()

    def _remove_allocation(self, row: int):
        """Remove an allocation."""
        if 0 <= row < len(self._allocations):
            del self._allocations[row]
            self._refresh_allocation_table()

    def _distribute_evenly(self):
        """Distribute budget evenly across categories."""
        if not self._allocations:
            QMessageBox.information(
                self,
                "No Categories",
                "Please add at least one category to distribute the budget."
            )
            return

        amount_each = self._total_budget / len(self._allocations)
        for alloc in self._allocations:
            alloc['amount'] = amount_each

        self._refresh_allocation_table()

    def _clear_allocations(self):
        """Clear all allocations."""
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Are you sure you want to clear all allocations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._allocations.clear()
            self._refresh_allocation_table()

    def get_allocations(self) -> List[Dict[str, Any]]:
        """Get the current allocations."""
        return self._allocations

    def validatePage(self) -> bool:
        """Validate the page data."""
        if not self._allocations:
            QMessageBox.warning(
                self,
                "No Allocations",
                "Please add at least one category allocation."
            )
            return False

        total_allocated = sum(a['amount'] for a in self._allocations)
        if total_allocated > self._total_budget:
            reply = QMessageBox.question(
                self,
                "Over Budget",
                f"Your allocations (${total_allocated:,.2f}) exceed the total budget "
                f"(${self._total_budget:,.2f}).\n\nDo you want to continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes

        return True


class AlertsConfigPage(WizardPageBase):
    """
    Step 3: Alert Configuration

    Configure budget alerts and notifications:
    - Alert threshold percentage
    - Notification preferences
    - Alert frequency
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            "Alert Configuration",
            "Set up notifications to stay on track with your budget",
            parent
        )
        self._setup_ui()

    def _setup_ui(self):
        """Set up the alerts configuration page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Main form
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(25, 25, 25, 25)
        form_layout.setSpacing(25)

        # Enable alerts
        self.enable_alerts = QCheckBox("Enable budget alerts and notifications")
        self.enable_alerts.setChecked(True)
        self.enable_alerts.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.enable_alerts.toggled.connect(self._toggle_alert_options)
        form_layout.addWidget(self.enable_alerts)

        # Alert options container
        self.options_widget = QWidget()
        options_layout = QVBoxLayout(self.options_widget)
        options_layout.setContentsMargins(20, 0, 0, 0)
        options_layout.setSpacing(20)

        # Threshold slider
        threshold_group = QGroupBox("Alert Threshold")
        threshold_layout = QVBoxLayout(threshold_group)

        threshold_desc = QLabel(
            "Get notified when spending reaches this percentage of your budget:"
        )
        threshold_desc.setStyleSheet("color: #666666;")
        threshold_layout.addWidget(threshold_desc)

        slider_layout = QHBoxLayout()

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(50)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(80)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.valueChanged.connect(self._update_threshold_label)
        slider_layout.addWidget(self.threshold_slider)

        self.threshold_label = QLabel("80%")
        self.threshold_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.threshold_label.setStyleSheet("color: #2196F3;")
        self.threshold_label.setMinimumWidth(60)
        slider_layout.addWidget(self.threshold_label)

        threshold_layout.addLayout(slider_layout)

        # Threshold preview
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(20)

        for pct, text, color in [
            (50, "50% - Early warning", "#4CAF50"),
            (80, "80% - Near limit", "#FF9800"),
            (100, "100% - Over budget", "#F44336")
        ]:
            preview_label = QLabel(text)
            preview_label.setStyleSheet(f"color: {color}; font-size: 11px;")
            preview_layout.addWidget(preview_label)

        preview_layout.addStretch()
        threshold_layout.addLayout(preview_layout)

        options_layout.addWidget(threshold_group)

        # Notification types
        notif_group = QGroupBox("Notification Types")
        notif_layout = QVBoxLayout(notif_group)

        self.notify_threshold = QCheckBox(
            "Notify when spending reaches alert threshold"
        )
        self.notify_threshold.setChecked(True)
        notif_layout.addWidget(self.notify_threshold)

        self.notify_over_budget = QCheckBox(
            "Notify when budget is exceeded"
        )
        self.notify_over_budget.setChecked(True)
        notif_layout.addWidget(self.notify_over_budget)

        self.notify_daily_summary = QCheckBox(
            "Send daily spending summary"
        )
        notif_layout.addWidget(self.notify_daily_summary)

        self.notify_weekly_report = QCheckBox(
            "Send weekly budget report"
        )
        self.notify_weekly_report.setChecked(True)
        notif_layout.addWidget(self.notify_weekly_report)

        options_layout.addWidget(notif_group)

        # Rollover options
        rollover_group = QGroupBox("Budget Rollover")
        rollover_layout = QVBoxLayout(rollover_group)

        self.enable_rollover = QCheckBox(
            "Roll over unused budget to next period"
        )
        rollover_layout.addWidget(self.enable_rollover)

        rollover_desc = QLabel(
            "If enabled, any unspent amount will be added to your next budget period."
        )
        rollover_desc.setStyleSheet("color: #666666; font-size: 11px;")
        rollover_desc.setWordWrap(True)
        rollover_layout.addWidget(rollover_desc)

        options_layout.addWidget(rollover_group)

        form_layout.addWidget(self.options_widget)
        layout.addWidget(form_frame)
        layout.addStretch()

    def _toggle_alert_options(self, enabled: bool):
        """Toggle alert options visibility."""
        self.options_widget.setEnabled(enabled)
        self.options_widget.setStyleSheet(
            "" if enabled else "color: #999999;"
        )

    def _update_threshold_label(self, value: int):
        """Update threshold percentage label."""
        self.threshold_label.setText(f"{value}%")

        if value >= 90:
            self.threshold_label.setStyleSheet("color: #F44336;")
        elif value >= 75:
            self.threshold_label.setStyleSheet("color: #FF9800;")
        else:
            self.threshold_label.setStyleSheet("color: #4CAF50;")

    def get_alert_settings(self) -> Dict[str, Any]:
        """Get the alert configuration."""
        return {
            'enabled': self.enable_alerts.isChecked(),
            'threshold': self.threshold_slider.value(),
            'notify_threshold': self.notify_threshold.isChecked(),
            'notify_over_budget': self.notify_over_budget.isChecked(),
            'notify_daily': self.notify_daily_summary.isChecked(),
            'notify_weekly': self.notify_weekly_report.isChecked(),
            'rollover': self.enable_rollover.isChecked()
        }


class ReviewPage(WizardPageBase):
    """
    Step 4: Review and Confirm

    Shows a summary of all budget configuration before creation.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            "Review Budget",
            "Review your budget configuration before creating it",
            parent
        )
        self._setup_ui()

    def _setup_ui(self):
        """Set up the review page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Scroll area for review content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(20)

        # General info section
        general_group = QGroupBox("General Information")
        general_group.setStyleSheet("""
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        general_layout = QFormLayout(general_group)
        general_layout.setContentsMargins(20, 25, 20, 20)
        general_layout.setSpacing(12)

        self.review_name = QLabel("-")
        self.review_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        general_layout.addRow("Budget Name:", self.review_name)

        self.review_period = QLabel("-")
        general_layout.addRow("Period:", self.review_period)

        self.review_dates = QLabel("-")
        general_layout.addRow("Date Range:", self.review_dates)

        self.review_total = QLabel("-")
        self.review_total.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.review_total.setStyleSheet("color: #2196F3;")
        general_layout.addRow("Total Budget:", self.review_total)

        self.review_description = QLabel("-")
        self.review_description.setWordWrap(True)
        general_layout.addRow("Description:", self.review_description)

        content_layout.addWidget(general_group)

        # Allocations section
        alloc_group = QGroupBox("Category Allocations")
        alloc_group.setStyleSheet("""
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        alloc_layout = QVBoxLayout(alloc_group)
        alloc_layout.setContentsMargins(20, 25, 20, 20)

        self.allocations_list = QListWidget()
        self.allocations_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F0F0F0;
            }
        """)
        self.allocations_list.setMaximumHeight(200)
        alloc_layout.addWidget(self.allocations_list)

        content_layout.addWidget(alloc_group)

        # Alert settings section
        alert_group = QGroupBox("Alert Settings")
        alert_group.setStyleSheet("""
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        alert_layout = QFormLayout(alert_group)
        alert_layout.setContentsMargins(20, 25, 20, 20)
        alert_layout.setSpacing(12)

        self.review_alerts_enabled = QLabel("-")
        alert_layout.addRow("Alerts Enabled:", self.review_alerts_enabled)

        self.review_threshold = QLabel("-")
        alert_layout.addRow("Alert Threshold:", self.review_threshold)

        self.review_notifications = QLabel("-")
        self.review_notifications.setWordWrap(True)
        alert_layout.addRow("Notifications:", self.review_notifications)

        self.review_rollover = QLabel("-")
        alert_layout.addRow("Budget Rollover:", self.review_rollover)

        content_layout.addWidget(alert_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Create button note
        note = QLabel(
            "Click 'Finish' to create this budget. You can modify it later if needed."
        )
        note.setStyleSheet("color: #666666; font-style: italic;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

    def initializePage(self):
        """Initialize the review page with collected data."""
        wizard = self.wizard()
        if not wizard:
            return

        # General info
        self.review_name.setText(self.field("budget_name") or "-")

        general_page = wizard.page(0)
        if isinstance(general_page, GeneralInfoPage):
            period = general_page.get_period().capitalize()
            self.review_period.setText(period)

            desc = general_page.description_input.toPlainText()
            self.review_description.setText(desc if desc else "(No description)")

        start = self.field("start_date")
        end = self.field("end_date")
        if start and end:
            self.review_dates.setText(
                f"{start.toString('MMM dd, yyyy')} - {end.toString('MMM dd, yyyy')}"
            )

        total = self.field("total_amount")
        if total:
            self.review_total.setText(f"${total:,.2f}")

        # Allocations
        alloc_page = wizard.page(1)
        if isinstance(alloc_page, CategoryAllocationPage):
            allocations = alloc_page.get_allocations()
            self.allocations_list.clear()

            total_allocated = Decimal('0')
            for alloc in allocations:
                amount = alloc['amount']
                total_allocated += amount
                item = QListWidgetItem(
                    f"{alloc['category_name']}: ${amount:,.2f}"
                )
                self.allocations_list.addItem(item)

            if not allocations:
                self.allocations_list.addItem("No categories allocated")

        # Alert settings
        alert_page = wizard.page(2)
        if isinstance(alert_page, AlertsConfigPage):
            settings = alert_page.get_alert_settings()

            self.review_alerts_enabled.setText(
                "Yes" if settings['enabled'] else "No"
            )

            self.review_threshold.setText(f"{settings['threshold']}%")

            notifications = []
            if settings['notify_threshold']:
                notifications.append("Threshold alerts")
            if settings['notify_over_budget']:
                notifications.append("Over budget alerts")
            if settings['notify_daily']:
                notifications.append("Daily summary")
            if settings['notify_weekly']:
                notifications.append("Weekly report")

            self.review_notifications.setText(
                ", ".join(notifications) if notifications else "None"
            )

            self.review_rollover.setText(
                "Enabled" if settings['rollover'] else "Disabled"
            )


class BudgetWizardDialog(QWizard):
    """
    Multi-step wizard dialog for creating budgets.

    Steps:
    1. General Information (name, period, dates, amount)
    2. Category Allocation (distribute budget across categories)
    3. Alert Configuration (thresholds, notifications)
    4. Review and Confirm

    Signals:
        budget_created: Emitted with complete budget data when finished
        cancelled: Emitted when wizard is cancelled
    """

    budget_created = pyqtSignal(dict)
    cancelled = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        categories: Optional[List[Dict[str, Any]]] = None,
        edit_budget: Optional[Dict[str, Any]] = None
    ):
        super().__init__(parent)
        self._categories = categories or []
        self._edit_budget = edit_budget
        self._setup_wizard()
        self._setup_pages()
        self._apply_styles()

    def _setup_wizard(self):
        """Set up the wizard dialog."""
        self.setWindowTitle(
            "Edit Budget" if self._edit_budget else "Create New Budget"
        )
        self.setMinimumSize(800, 600)

        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.IndependentPages, False)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, False)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)

        # Custom button text
        self.setButtonText(QWizard.WizardButton.FinishButton, "Create Budget")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Cancel")

    def _setup_pages(self):
        """Set up wizard pages."""
        # Page 1: General Info
        self.general_page = GeneralInfoPage()
        self.addPage(self.general_page)

        # Page 2: Category Allocation
        self.allocation_page = CategoryAllocationPage()
        self.allocation_page.set_categories(self._categories)
        self.addPage(self.allocation_page)

        # Page 3: Alert Configuration
        self.alerts_page = AlertsConfigPage()
        self.addPage(self.alerts_page)

        # Page 4: Review
        self.review_page = ReviewPage()
        self.addPage(self.review_page)

        # Load edit data if provided
        if self._edit_budget:
            self._load_edit_data()

    def _apply_styles(self):
        """Apply custom styles to the wizard."""
        self.setStyleSheet("""
            QWizard {
                background-color: #FAFAFA;
            }
            QWizard QLabel#title {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
            }
            QWizard QLabel#subtitle {
                font-size: 12px;
                color: #666666;
            }
            QPushButton {
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton#qt_wizard_commit,
            QPushButton#qt_wizard_finish {
                background-color: #4CAF50;
                color: white;
                border: none;
            }
            QPushButton#qt_wizard_commit:hover,
            QPushButton#qt_wizard_finish:hover {
                background-color: #45a049;
            }
            QPushButton#qt_wizard_cancel {
                background-color: #FFFFFF;
                color: #666666;
                border: 1px solid #CCCCCC;
            }
            QPushButton#qt_wizard_cancel:hover {
                background-color: #F5F5F5;
            }
        """)

    def _load_edit_data(self):
        """Load existing budget data for editing."""
        budget = self._edit_budget
        if not budget:
            return

        # General info
        self.general_page.name_input.setText(budget.get('name', ''))
        self.general_page.total_amount.setValue(float(budget.get('limit', 1000)))

        # Period
        period = budget.get('period', 'monthly').lower()
        for btn in self.general_page.period_group.buttons():
            if btn.property("period_value") == period:
                btn.setChecked(True)
                break

        # Dates
        start_date = budget.get('start_date')
        if start_date:
            if isinstance(start_date, str):
                self.general_page.start_date.setDate(
                    QDate.fromString(start_date, "yyyy-MM-dd")
                )
            elif isinstance(start_date, date):
                self.general_page.start_date.setDate(
                    QDate(start_date.year, start_date.month, start_date.day)
                )

        end_date = budget.get('end_date')
        if end_date:
            if isinstance(end_date, str):
                self.general_page.end_date.setDate(
                    QDate.fromString(end_date, "yyyy-MM-dd")
                )
            elif isinstance(end_date, date):
                self.general_page.end_date.setDate(
                    QDate(end_date.year, end_date.month, end_date.day)
                )

        self.general_page.description_input.setText(budget.get('notes', ''))

        # Alert settings
        self.alerts_page.threshold_slider.setValue(
            budget.get('alert_threshold', 80)
        )
        self.alerts_page.enable_rollover.setChecked(
            budget.get('rollover', False)
        )

        # Update button text for edit mode
        self.setButtonText(QWizard.WizardButton.FinishButton, "Save Changes")

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self._categories = categories
        self.allocation_page.set_categories(categories)

    def accept(self):
        """Handle wizard completion."""
        budget_data = self._collect_budget_data()
        self.budget_created.emit(budget_data)
        super().accept()

    def reject(self):
        """Handle wizard cancellation."""
        self.cancelled.emit()
        super().reject()

    def _collect_budget_data(self) -> Dict[str, Any]:
        """Collect all budget data from wizard pages."""
        data = {
            'name': self.field("budget_name"),
            'period': self.general_page.get_period(),
            'start_date': self.field("start_date").toString("yyyy-MM-dd"),
            'end_date': self.field("end_date").toString("yyyy-MM-dd"),
            'limit': Decimal(str(self.field("total_amount"))),
            'notes': self.general_page.description_input.toPlainText(),
            'items': self.allocation_page.get_allocations(),
            'alert_settings': self.alerts_page.get_alert_settings(),
            'alert_threshold': self.alerts_page.get_alert_settings()['threshold'],
            'rollover': self.alerts_page.get_alert_settings()['rollover']
        }

        # Include ID if editing
        if self._edit_budget and 'id' in self._edit_budget:
            data['id'] = self._edit_budget['id']

        return data
