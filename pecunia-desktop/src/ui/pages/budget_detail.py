"""
Budget Detail Page Module

Enhanced budget detail view with comprehensive statistics, transaction list,
category breakdown charts, and interactive progress visualization.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QGroupBox, QSizePolicy, QStackedWidget, QTabWidget,
    QAbstractItemView, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QDate
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QAction, QCursor
from PyQt6.QtCharts import (
    QChart, QChartView, QPieSeries, QPieSlice,
    QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QLineSeries, QDateTimeAxis
)
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, date, timedelta
from enum import Enum


class BudgetStatus(Enum):
    """Budget status indicators."""
    UNDER_BUDGET = "under_budget"
    WARNING = "warning"
    NEAR_LIMIT = "near_limit"
    OVER_BUDGET = "over_budget"


def get_budget_status(spent: Decimal, limit: Decimal, threshold: int = 80) -> BudgetStatus:
    """Determine budget status based on spending percentage."""
    if limit <= 0:
        return BudgetStatus.UNDER_BUDGET
    percentage = (spent / limit) * 100
    if percentage >= 100:
        return BudgetStatus.OVER_BUDGET
    elif percentage >= threshold:
        return BudgetStatus.NEAR_LIMIT
    elif percentage >= 50:
        return BudgetStatus.WARNING
    else:
        return BudgetStatus.UNDER_BUDGET


def get_status_color(status: BudgetStatus) -> str:
    """Get color for budget status."""
    colors = {
        BudgetStatus.UNDER_BUDGET: "#4CAF50",
        BudgetStatus.WARNING: "#FFC107",
        BudgetStatus.NEAR_LIMIT: "#FF9800",
        BudgetStatus.OVER_BUDGET: "#F44336",
    }
    return colors.get(status, "#4CAF50")


class AnimatedProgressBar(QProgressBar):
    """Custom progress bar with animation and color transitions."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._target_value = 0
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(500)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setTextVisible(True)
        self.setMaximum(100)

    def set_progress(self, value: int, animate: bool = True):
        """Set progress with optional animation."""
        self._target_value = min(value, 100)
        if animate:
            self._animation.setStartValue(self.value())
            self._animation.setEndValue(self._target_value)
            self._animation.start()
        else:
            self.setValue(self._target_value)

    def set_status_color(self, status: BudgetStatus):
        """Set progress bar color based on status."""
        color = get_status_color(status)
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)


class BudgetHeaderCard(QFrame):
    """Header card showing budget overview with key metrics."""

    edit_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    copy_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetHeaderCard")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the header card UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            #budgetHeaderCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        # Top row - Title and actions
        top_layout = QHBoxLayout()

        # Budget name and category
        title_layout = QVBoxLayout()

        self.name_label = QLabel("Budget Name")
        self.name_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #333333;")
        title_layout.addWidget(self.name_label)

        self.meta_label = QLabel("Category | Period")
        self.meta_label.setFont(QFont("Segoe UI", 11))
        self.meta_label.setStyleSheet("color: #666666;")
        title_layout.addWidget(self.meta_label)

        top_layout.addLayout(title_layout)
        top_layout.addStretch()

        # Status badge
        self.status_badge = QLabel("On Track")
        self.status_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.status_badge.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            padding: 6px 14px;
            border-radius: 12px;
        """)
        top_layout.addWidget(self.status_badge)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("smallSecondaryButton")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: #1976D2;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        copy_btn.clicked.connect(self.copy_requested.emit)
        action_layout.addWidget(copy_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("smallPrimaryButton")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        edit_btn.clicked.connect(self.edit_requested.emit)
        action_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerButton")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFEBEE;
                color: #F44336;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FFCDD2;
            }
        """)
        delete_btn.clicked.connect(self.delete_requested.emit)
        action_layout.addWidget(delete_btn)

        top_layout.addLayout(action_layout)
        layout.addLayout(top_layout)

        # Progress section
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)

        progress_header = QHBoxLayout()
        progress_header.addWidget(QLabel("Budget Progress"))
        progress_header.addStretch()

        self.progress_percentage = QLabel("0%")
        self.progress_percentage.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        progress_header.addWidget(self.progress_percentage)

        progress_layout.addLayout(progress_header)

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setMinimumHeight(20)
        progress_layout.addWidget(self.progress_bar)

        layout.addLayout(progress_layout)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(40)

        # Spent
        spent_layout = QVBoxLayout()
        spent_title = QLabel("Spent")
        spent_title.setFont(QFont("Segoe UI", 10))
        spent_title.setStyleSheet("color: #666666;")
        spent_layout.addWidget(spent_title)

        self.spent_value = QLabel("$0.00")
        self.spent_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.spent_value.setStyleSheet("color: #FF9800;")
        spent_layout.addWidget(self.spent_value)
        stats_layout.addLayout(spent_layout)

        # Budget
        budget_layout = QVBoxLayout()
        budget_title = QLabel("Budget")
        budget_title.setFont(QFont("Segoe UI", 10))
        budget_title.setStyleSheet("color: #666666;")
        budget_layout.addWidget(budget_title)

        self.budget_value = QLabel("$0.00")
        self.budget_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.budget_value.setStyleSheet("color: #2196F3;")
        budget_layout.addWidget(self.budget_value)
        stats_layout.addLayout(budget_layout)

        # Remaining
        remaining_layout = QVBoxLayout()
        remaining_title = QLabel("Remaining")
        remaining_title.setFont(QFont("Segoe UI", 10))
        remaining_title.setStyleSheet("color: #666666;")
        remaining_layout.addWidget(remaining_title)

        self.remaining_value = QLabel("$0.00")
        self.remaining_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.remaining_value.setStyleSheet("color: #4CAF50;")
        remaining_layout.addWidget(self.remaining_value)
        stats_layout.addLayout(remaining_layout)

        # Daily average
        daily_layout = QVBoxLayout()
        daily_title = QLabel("Daily Average")
        daily_title.setFont(QFont("Segoe UI", 10))
        daily_title.setStyleSheet("color: #666666;")
        daily_layout.addWidget(daily_title)

        self.daily_value = QLabel("$0.00")
        self.daily_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.daily_value.setStyleSheet("color: #9C27B0;")
        daily_layout.addWidget(self.daily_value)
        stats_layout.addLayout(daily_layout)

        # Days left
        days_layout = QVBoxLayout()
        days_title = QLabel("Days Left")
        days_title.setFont(QFont("Segoe UI", 10))
        days_title.setStyleSheet("color: #666666;")
        days_layout.addWidget(days_title)

        self.days_value = QLabel("0")
        self.days_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.days_value.setStyleSheet("color: #607D8B;")
        days_layout.addWidget(self.days_value)
        stats_layout.addLayout(days_layout)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

    def update_data(self, budget: Dict[str, Any]):
        """Update the header card with budget data."""
        name = budget.get('name', 'Unknown Budget')
        category = budget.get('category', 'Uncategorized')
        period = budget.get('period', 'monthly').capitalize()

        spent = Decimal(str(budget.get('spent', 0)))
        limit = Decimal(str(budget.get('limit', 0)))
        remaining = limit - spent
        threshold = budget.get('alert_threshold', 80)

        self.name_label.setText(name)
        self.meta_label.setText(f"{category} | {period}")

        # Calculate percentage
        percentage = int((spent / limit * 100)) if limit > 0 else 0
        status = get_budget_status(spent, limit, threshold)
        status_color = get_status_color(status)

        # Update status badge
        status_text = status.name.replace("_", " ").title()
        self.status_badge.setText(status_text)
        self.status_badge.setStyleSheet(f"""
            background-color: {status_color};
            color: white;
            padding: 6px 14px;
            border-radius: 12px;
            font-weight: bold;
        """)

        # Update progress
        self.progress_percentage.setText(f"{percentage}%")
        self.progress_percentage.setStyleSheet(f"color: {status_color};")
        self.progress_bar.set_progress(min(percentage, 100))
        self.progress_bar.set_status_color(status)
        self.progress_bar.setFormat(f"{percentage}%")

        # Update values
        self.spent_value.setText(f"${spent:,.2f}")
        self.budget_value.setText(f"${limit:,.2f}")

        if remaining >= 0:
            self.remaining_value.setText(f"${remaining:,.2f}")
            self.remaining_value.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.remaining_value.setText(f"-${abs(remaining):,.2f}")
            self.remaining_value.setStyleSheet("color: #F44336; font-weight: bold;")

        # Calculate daily average and days left
        start_date = budget.get('start_date')
        end_date = budget.get('end_date')

        if start_date and end_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            today = date.today()
            days_passed = (today - start_date).days or 1
            days_left = max((end_date - today).days, 0)

            daily_avg = spent / Decimal(days_passed) if days_passed > 0 else Decimal(0)
            self.daily_value.setText(f"${daily_avg:,.2f}")
            self.days_value.setText(str(days_left))
        else:
            self.daily_value.setText("N/A")
            self.days_value.setText("N/A")


class BudgetItemsTable(QTableWidget):
    """Table showing budget items with progress."""

    item_selected = pyqtSignal(dict)
    item_edit_requested = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetItemsTable")
        self._items: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the table UI."""
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Category", "Planned", "Spent", "Remaining", "Progress", "Status"
        ])

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 150)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)

        self.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #F0F0F0;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #333333;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #E0E0E0;
                font-weight: bold;
            }
        """)

        self.cellClicked.connect(self._on_cell_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _on_cell_clicked(self, row: int, column: int):
        """Handle cell click."""
        if 0 <= row < len(self._items):
            self.item_selected.emit(self._items[row])

    def _show_context_menu(self, position):
        """Show context menu for item actions."""
        row = self.rowAt(position.y())
        if row < 0 or row >= len(self._items):
            return

        menu = QMenu(self)

        edit_action = QAction("Edit Item", self)
        edit_action.triggered.connect(lambda: self.item_edit_requested.emit(row))
        menu.addAction(edit_action)

        menu.exec(self.mapToGlobal(position))

    def load_items(self, items: List[Dict[str, Any]]):
        """Load budget items into the table."""
        self._items = items
        self.setRowCount(len(items))

        for row, item in enumerate(items):
            category = item.get('category_name', item.get('category', 'Unknown'))
            planned = Decimal(str(item.get('planned_amount', item.get('limit', 0))))
            spent = Decimal(str(item.get('spent_amount', item.get('spent', 0))))
            remaining = planned - spent
            percentage = int((spent / planned * 100)) if planned > 0 else 0

            # Category
            category_item = QTableWidgetItem(category)
            category_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            self.setItem(row, 0, category_item)

            # Planned
            planned_item = QTableWidgetItem(f"${planned:,.2f}")
            planned_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 1, planned_item)

            # Spent
            spent_item = QTableWidgetItem(f"${spent:,.2f}")
            spent_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 2, spent_item)

            # Remaining
            remaining_item = QTableWidgetItem(f"${remaining:,.2f}")
            remaining_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if remaining < 0:
                remaining_item.setForeground(QColor("#F44336"))
                remaining_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.setItem(row, 3, remaining_item)

            # Progress bar widget
            progress_bar = QProgressBar()
            progress_bar.setMaximum(100)
            progress_bar.setValue(min(percentage, 100))
            progress_bar.setFormat(f"{percentage}%")
            progress_bar.setMaximumHeight(20)

            status = get_budget_status(spent, planned)
            color = get_status_color(status)
            progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #E0E0E0;
                    border-radius: 4px;
                    text-align: center;
                    font-size: 10px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """)
            self.setCellWidget(row, 4, progress_bar)

            # Status
            status_text = "Over" if spent > planned else ("Warning" if percentage >= 80 else "Good")
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor(color))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.setItem(row, 5, status_item)

            self.setRowHeight(row, 50)


class TransactionsListWidget(QWidget):
    """Widget showing transactions for this budget."""

    transaction_selected = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("transactionsListWidget")
        self._transactions: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the transactions list UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Recent Transactions")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.count_label = QLabel("0 transactions")
        self.count_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(self.count_label)

        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Description", "Category", "Amount"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
            }
        """)

        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

    def _on_row_double_clicked(self, row: int, column: int):
        """Handle row double-click."""
        if 0 <= row < len(self._transactions):
            trans_id = self._transactions[row].get('id', 0)
            self.transaction_selected.emit(trans_id)

    def load_transactions(self, transactions: List[Dict[str, Any]]):
        """Load transactions into the table."""
        self._transactions = transactions
        self.count_label.setText(f"{len(transactions)} transactions")

        self.table.setRowCount(len(transactions))

        for row, trans in enumerate(transactions):
            # Date
            trans_date = trans.get('date', '')
            if isinstance(trans_date, datetime):
                date_str = trans_date.strftime("%b %d, %Y")
            elif isinstance(trans_date, date):
                date_str = trans_date.strftime("%b %d, %Y")
            else:
                date_str = str(trans_date)

            date_item = QTableWidgetItem(date_str)
            date_item.setForeground(QColor("#666666"))
            self.table.setItem(row, 0, date_item)

            # Description
            desc = trans.get('description', 'Unknown')
            desc_item = QTableWidgetItem(desc)
            desc_item.setFont(QFont("Segoe UI", 10))
            self.table.setItem(row, 1, desc_item)

            # Category
            category = trans.get('category', 'Uncategorized')
            cat_item = QTableWidgetItem(category)
            cat_item.setForeground(QColor("#888888"))
            self.table.setItem(row, 2, cat_item)

            # Amount
            amount = Decimal(str(trans.get('amount', 0)))
            amount_item = QTableWidgetItem(f"${amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amount_item.setForeground(QColor("#F44336"))
            amount_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row, 3, amount_item)

            self.table.setRowHeight(row, 45)


class CategoryBreakdownChart(QChartView):
    """Pie chart showing spending breakdown by category."""

    def __init__(self, parent: Optional[QWidget] = None):
        self.chart = QChart()
        super().__init__(self.chart, parent)
        self._setup_chart()

    def _setup_chart(self):
        """Set up the chart."""
        self.chart.setTitle("Spending by Category")
        self.chart.setTitleFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        self.chart.setBackgroundBrush(QBrush(QColor("#FFFFFF")))
        self.chart.setMargins(QChart.margins(self.chart))

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(250)

    def update_data(self, items: List[Dict[str, Any]]):
        """Update chart with budget items data."""
        self.chart.removeAllSeries()

        if not items:
            return

        series = QPieSeries()

        colors = [
            "#2196F3", "#4CAF50", "#FF9800", "#9C27B0",
            "#F44336", "#00BCD4", "#795548", "#607D8B"
        ]

        for i, item in enumerate(items[:8]):
            name = item.get('category_name', item.get('category', 'Unknown'))
            spent = float(item.get('spent_amount', item.get('spent', 0)))

            if spent > 0:
                slice = series.append(name, spent)
                slice.setColor(QColor(colors[i % len(colors)]))
                slice.setLabelVisible(True)
                slice.setLabelColor(QColor("#333333"))
                slice.setLabelFont(QFont("Segoe UI", 9))

        self.chart.addSeries(series)


class SpendingTrendChart(QChartView):
    """Line chart showing spending trend over time."""

    def __init__(self, parent: Optional[QWidget] = None):
        self.chart = QChart()
        super().__init__(self.chart, parent)
        self._setup_chart()

    def _setup_chart(self):
        """Set up the chart."""
        self.chart.setTitle("Spending Trend")
        self.chart.setTitleFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.chart.setBackgroundBrush(QBrush(QColor("#FFFFFF")))

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(250)

    def update_data(self, transactions: List[Dict[str, Any]], budget_limit: Decimal):
        """Update chart with transaction data."""
        self.chart.removeAllSeries()

        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        if not transactions:
            return

        # Group transactions by date
        daily_spending = {}
        for trans in transactions:
            trans_date = trans.get('date')
            if isinstance(trans_date, datetime):
                trans_date = trans_date.date()
            elif isinstance(trans_date, str):
                trans_date = datetime.strptime(trans_date, "%Y-%m-%d").date()

            if trans_date:
                amount = float(trans.get('amount', 0))
                daily_spending[trans_date] = daily_spending.get(trans_date, 0) + amount

        if not daily_spending:
            return

        # Sort by date
        sorted_dates = sorted(daily_spending.keys())

        # Create cumulative spending series
        cumulative_series = QLineSeries()
        cumulative_series.setName("Cumulative Spending")
        cumulative_series.setColor(QColor("#2196F3"))

        cumulative = 0
        for date_val in sorted_dates:
            cumulative += daily_spending[date_val]
            timestamp = datetime.combine(date_val, datetime.min.time()).timestamp() * 1000
            cumulative_series.append(timestamp, cumulative)

        self.chart.addSeries(cumulative_series)

        # Budget limit line
        limit_series = QLineSeries()
        limit_series.setName("Budget Limit")
        limit_series.setColor(QColor("#F44336"))

        if sorted_dates:
            start_ts = datetime.combine(sorted_dates[0], datetime.min.time()).timestamp() * 1000
            end_ts = datetime.combine(sorted_dates[-1], datetime.min.time()).timestamp() * 1000
            limit_series.append(start_ts, float(budget_limit))
            limit_series.append(end_ts, float(budget_limit))

        self.chart.addSeries(limit_series)

        # Create axes
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM dd")
        axis_x.setTitleText("Date")
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        cumulative_series.attachAxis(axis_x)
        limit_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Amount ($)")
        axis_y.setLabelFormat("$%.0f")
        max_val = max(cumulative, float(budget_limit)) * 1.1
        axis_y.setRange(0, max_val)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        cumulative_series.attachAxis(axis_y)
        limit_series.attachAxis(axis_y)


class BudgetDetailPage(QWidget):
    """
    Enhanced budget detail page with comprehensive information.

    Features:
    - Header card with key metrics and status
    - Budget items table with progress bars
    - Category breakdown pie chart
    - Spending trend line chart
    - Transaction list
    - Edit/delete/copy actions
    """

    # Signals
    back_requested = pyqtSignal()
    edit_budget_requested = pyqtSignal(int)
    delete_budget_requested = pyqtSignal(int)
    copy_budget_requested = pyqtSignal(dict)
    edit_item_requested = pyqtSignal(int, int)  # budget_id, item_index
    view_transaction_requested = pyqtSignal(int)
    refresh_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetDetailPage")
        self._budget: Optional[Dict[str, Any]] = None
        self._transactions: List[Dict[str, Any]] = []
        self._budget_items: List[Dict[str, Any]] = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(20)

        # Navigation bar
        nav_layout = QHBoxLayout()

        back_btn = QPushButton("< Back to Budgets")
        back_btn.setObjectName("linkButton")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2196F3;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #1976D2;
                text-decoration: underline;
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        nav_layout.addWidget(back_btn)

        nav_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #333333;
                border: 1px solid #E0E0E0;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        nav_layout.addWidget(refresh_btn)

        layout.addLayout(nav_layout)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(20)

        # Header card
        self.header_card = BudgetHeaderCard()
        content_layout.addWidget(self.header_card)

        # Tabs for different views
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 5px;
                background-color: #F5F5F5;
                border: none;
                border-radius: 6px 6px 0 0;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                font-weight: bold;
            }
        """)

        # Items tab
        items_widget = QWidget()
        items_layout = QVBoxLayout(items_widget)
        items_layout.setContentsMargins(0, 10, 0, 0)

        self.items_table = BudgetItemsTable()
        items_layout.addWidget(self.items_table)

        tabs.addTab(items_widget, "Budget Items")

        # Charts tab
        charts_widget = QWidget()
        charts_layout = QHBoxLayout(charts_widget)
        charts_layout.setContentsMargins(0, 10, 0, 0)
        charts_layout.setSpacing(20)

        self.category_chart = CategoryBreakdownChart()
        charts_layout.addWidget(self.category_chart)

        self.trend_chart = SpendingTrendChart()
        charts_layout.addWidget(self.trend_chart)

        tabs.addTab(charts_widget, "Charts")

        # Transactions tab
        transactions_widget = QWidget()
        transactions_layout = QVBoxLayout(transactions_widget)
        transactions_layout.setContentsMargins(0, 10, 0, 0)

        self.transactions_list = TransactionsListWidget()
        transactions_layout.addWidget(self.transactions_list)

        tabs.addTab(transactions_widget, "Transactions")

        content_layout.addWidget(tabs)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def _connect_signals(self):
        """Connect internal signals."""
        self.header_card.edit_requested.connect(self._request_edit)
        self.header_card.delete_requested.connect(self._confirm_delete)
        self.header_card.copy_requested.connect(self._request_copy)

        self.items_table.item_edit_requested.connect(self._request_item_edit)
        self.transactions_list.transaction_selected.connect(
            self.view_transaction_requested.emit
        )

    def _request_edit(self):
        """Request to edit the current budget."""
        if self._budget:
            self.edit_budget_requested.emit(self._budget.get('id', 0))

    def _confirm_delete(self):
        """Show delete confirmation dialog."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this budget?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes and self._budget:
            self.delete_budget_requested.emit(self._budget.get('id', 0))

    def _request_copy(self):
        """Request to copy the current budget."""
        if self._budget:
            import copy
            budget_copy = copy.deepcopy(self._budget)
            budget_copy.pop('id', None)
            budget_copy['name'] = f"{budget_copy.get('name', 'Budget')} (Copy)"
            budget_copy['spent'] = Decimal('0')
            self.copy_budget_requested.emit(budget_copy)

    def _request_item_edit(self, item_index: int):
        """Request to edit a budget item."""
        if self._budget:
            self.edit_item_requested.emit(self._budget.get('id', 0), item_index)

    def load_budget(
        self,
        budget: Dict[str, Any],
        transactions: Optional[List[Dict[str, Any]]] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ):
        """Load budget details into the page."""
        self._budget = budget
        self._transactions = transactions or []
        self._budget_items = items or budget.get('items', [])

        # Update header
        self.header_card.update_data(budget)

        # Update items table
        if self._budget_items:
            self.items_table.load_items(self._budget_items)
        else:
            # Create single item from budget data if no items provided
            single_item = {
                'category_name': budget.get('category', 'Total'),
                'planned_amount': budget.get('limit', 0),
                'spent_amount': budget.get('spent', 0)
            }
            self.items_table.load_items([single_item])

        # Update charts
        if self._budget_items:
            self.category_chart.update_data(self._budget_items)
        else:
            self.category_chart.update_data([{
                'category': budget.get('category', 'Total'),
                'spent': budget.get('spent', 0)
            }])

        limit = Decimal(str(budget.get('limit', 0)))
        self.trend_chart.update_data(self._transactions, limit)

        # Update transactions list
        self.transactions_list.load_transactions(self._transactions)

    def get_current_budget(self) -> Optional[Dict[str, Any]]:
        """Get the currently displayed budget."""
        return self._budget
