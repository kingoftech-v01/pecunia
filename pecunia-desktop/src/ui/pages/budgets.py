"""
Budgets Page Module

Budget management pages for creating, editing, and tracking budgets.
Includes list view, detail view, form page, and chart visualizations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QProgressBar,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget,
    QDialog, QDialogButtonBox, QMessageBox, QSizePolicy, QSplitter,
    QAbstractItemView, QDateEdit, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QDate
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPainterPath
from PyQt6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis, QPieSeries
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, date
from enum import Enum
import copy


class BudgetPeriod(Enum):
    """Budget period options."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


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
        BudgetStatus.UNDER_BUDGET: "#4CAF50",  # Green
        BudgetStatus.WARNING: "#FFC107",        # Yellow
        BudgetStatus.NEAR_LIMIT: "#FF9800",     # Orange
        BudgetStatus.OVER_BUDGET: "#F44336",    # Red
    }
    return colors.get(status, "#4CAF50")


class BudgetItemProgressBar(QFrame):
    """Custom progress bar widget for budget items with visual indicators."""

    def __init__(
        self,
        name: str,
        spent: Decimal,
        limit: Decimal,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.name = name
        self.spent = spent
        self.limit = limit
        self._setup_ui()

    def _setup_ui(self):
        """Set up the progress bar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(4)

        # Header row with name and amounts
        header_layout = QHBoxLayout()

        name_label = QLabel(self.name)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        # Amount display
        percentage = (self.spent / self.limit * 100) if self.limit > 0 else 0
        status = get_budget_status(self.spent, self.limit)
        status_color = get_status_color(status)

        amount_text = f"${self.spent:,.2f} / ${self.limit:,.2f}"
        amount_label = QLabel(amount_text)
        amount_label.setFont(QFont("Segoe UI", 9))
        amount_label.setStyleSheet(f"color: {status_color};")
        header_layout.addWidget(amount_label)

        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(min(int(percentage), 100))
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(f"{percentage:.1f}%")
        self.progress_bar.setMaximumHeight(18)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {status_color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Over budget indicator
        if self.spent > self.limit:
            over_amount = self.spent - self.limit
            over_label = QLabel(f"Over budget by ${over_amount:,.2f}")
            over_label.setFont(QFont("Segoe UI", 9))
            over_label.setStyleSheet("color: #F44336; font-weight: bold;")
            layout.addWidget(over_label)

    def update_values(self, spent: Decimal, limit: Decimal):
        """Update the progress bar values."""
        self.spent = spent
        self.limit = limit
        # Rebuild UI
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().deleteLater()
        self._setup_ui()


class BudgetVsActualChart(QChartView):
    """Bar chart comparing budgeted amounts vs actual spending."""

    def __init__(self, parent: Optional[QWidget] = None):
        self.chart = QChart()
        super().__init__(self.chart, parent)
        self._setup_chart()

    def _setup_chart(self):
        """Set up the chart."""
        self.chart.setTitle("Budget vs Actual Spending")
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        # Set chart background
        self.chart.setBackgroundBrush(QBrush(QColor("#FFFFFF")))

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(300)

    def update_data(self, budget_data: List[Dict[str, Any]]):
        """Update chart with budget data."""
        # Clear existing series
        self.chart.removeAllSeries()

        # Remove existing axes
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        if not budget_data:
            return

        # Create bar sets
        budget_set = QBarSet("Budgeted")
        budget_set.setColor(QColor("#2196F3"))

        actual_set = QBarSet("Actual")
        actual_set.setColor(QColor("#4CAF50"))

        categories = []

        for budget in budget_data[:8]:  # Limit to 8 items for readability
            name = budget.get('name', 'Unknown')
            if len(name) > 12:
                name = name[:10] + "..."
            categories.append(name)

            limit = float(budget.get('limit', 0))
            spent = float(budget.get('spent', 0))

            budget_set.append(limit)
            actual_set.append(spent)

            # Color actual bar based on status
            if spent > limit:
                actual_set.setColor(QColor("#F44336"))

        # Create series
        series = QBarSeries()
        series.append(budget_set)
        series.append(actual_set)

        self.chart.addSeries(series)

        # Create axes
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        max_value = max(
            max(float(b.get('limit', 0)) for b in budget_data),
            max(float(b.get('spent', 0)) for b in budget_data)
        )
        axis_y.setRange(0, max_value * 1.1)
        axis_y.setLabelFormat("$%.0f")
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)


class BudgetDistributionChart(QChartView):
    """Pie chart showing budget distribution by category."""

    def __init__(self, parent: Optional[QWidget] = None):
        self.chart = QChart()
        super().__init__(self.chart, parent)
        self._setup_chart()

    def _setup_chart(self):
        """Set up the chart."""
        self.chart.setTitle("Budget Distribution")
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)

        self.chart.setBackgroundBrush(QBrush(QColor("#FFFFFF")))

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(300)

    def update_data(self, budget_data: List[Dict[str, Any]]):
        """Update chart with budget data."""
        self.chart.removeAllSeries()

        if not budget_data:
            return

        series = QPieSeries()

        colors = [
            "#2196F3", "#4CAF50", "#FF9800", "#9C27B0",
            "#F44336", "#00BCD4", "#795548", "#607D8B"
        ]

        for i, budget in enumerate(budget_data[:8]):
            name = budget.get('name', 'Unknown')
            limit = float(budget.get('limit', 0))

            slice = series.append(name, limit)
            slice.setColor(QColor(colors[i % len(colors)]))
            slice.setLabelVisible(True)
            slice.setLabelColor(QColor("#333333"))

        self.chart.addSeries(series)


class BudgetCard(QFrame):
    """Card widget displaying a single budget with status and progress."""

    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    view_details_requested = pyqtSignal(int)
    copy_requested = pyqtSignal(int)

    def __init__(
        self,
        budget_id: int,
        name: str,
        category: str,
        spent: Decimal,
        limit: Decimal,
        period: str,
        alert_threshold: int = 80,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.budget_id = budget_id
        self.setObjectName("budgetCard")
        self._setup_ui(name, category, spent, limit, period, alert_threshold)

    def _setup_ui(
        self,
        name: str,
        category: str,
        spent: Decimal,
        limit: Decimal,
        period: str,
        alert_threshold: int
    ):
        """Set up the budget card UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(300, 200)
        self.setMaximumWidth(380)

        status = get_budget_status(spent, limit, alert_threshold)
        status_color = get_status_color(status)

        # Add left border color indicator
        self.setStyleSheet(f"""
            #budgetCard {{
                border-left: 4px solid {status_color};
                background-color: #FFFFFF;
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # Header with name and status badge
        header_layout = QHBoxLayout()

        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        name_label.setObjectName("budgetName")
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        # Status badge
        status_text = status.name.replace("_", " ").title()
        status_badge = QLabel(status_text)
        status_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        status_badge.setStyleSheet(f"""
            background-color: {status_color};
            color: white;
            padding: 3px 8px;
            border-radius: 10px;
        """)
        header_layout.addWidget(status_badge)

        layout.addLayout(header_layout)

        # Category and period info
        meta_layout = QHBoxLayout()

        category_label = QLabel(f"Category: {category}")
        category_label.setFont(QFont("Segoe UI", 10))
        category_label.setStyleSheet("color: #666666;")
        meta_layout.addWidget(category_label)

        meta_layout.addStretch()

        period_label = QLabel(period.capitalize())
        period_label.setFont(QFont("Segoe UI", 9))
        period_label.setStyleSheet("""
            background-color: #E3F2FD;
            color: #1976D2;
            padding: 2px 8px;
            border-radius: 8px;
        """)
        meta_layout.addWidget(period_label)

        layout.addLayout(meta_layout)

        # Progress section
        progress_widget = BudgetItemProgressBar("Progress", spent, limit)
        layout.addWidget(progress_widget)

        # Remaining amount
        remaining = limit - spent
        if remaining >= 0:
            remaining_text = f"${remaining:,.2f} remaining"
            remaining_style = "color: #4CAF50;"
        else:
            remaining_text = f"${abs(remaining):,.2f} over budget"
            remaining_style = "color: #F44336; font-weight: bold;"

        remaining_label = QLabel(remaining_text)
        remaining_label.setFont(QFont("Segoe UI", 11))
        remaining_label.setStyleSheet(remaining_style)
        layout.addWidget(remaining_label)

        # Action buttons
        button_layout = QHBoxLayout()

        view_btn = QPushButton("View Details")
        view_btn.setObjectName("linkButton")
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.clicked.connect(lambda: self.view_details_requested.emit(self.budget_id))
        button_layout.addWidget(view_btn)

        button_layout.addStretch()

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("smallButton")
        copy_btn.setMaximumWidth(50)
        copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.budget_id))
        button_layout.addWidget(copy_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("smallButton")
        edit_btn.setMaximumWidth(50)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.budget_id))
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("X")
        delete_btn.setObjectName("dangerButton")
        delete_btn.setMaximumWidth(30)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.budget_id))
        button_layout.addWidget(delete_btn)

        layout.addLayout(button_layout)


class BudgetSummaryWidget(QFrame):
    """Widget showing overall budget summary statistics."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetSummaryWidget")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the summary widget UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            #budgetSummaryWidget {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(40)

        # Total budgeted
        budgeted_layout = QVBoxLayout()
        budgeted_title = QLabel("Total Budgeted")
        budgeted_title.setFont(QFont("Segoe UI", 10))
        budgeted_title.setStyleSheet("color: #666666;")
        budgeted_layout.addWidget(budgeted_title)

        self.budgeted_value = QLabel("$0.00")
        self.budgeted_value.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.budgeted_value.setStyleSheet("color: #2196F3;")
        budgeted_layout.addWidget(self.budgeted_value)
        layout.addLayout(budgeted_layout)

        # Total spent
        spent_layout = QVBoxLayout()
        spent_title = QLabel("Total Spent")
        spent_title.setFont(QFont("Segoe UI", 10))
        spent_title.setStyleSheet("color: #666666;")
        spent_layout.addWidget(spent_title)

        self.spent_value = QLabel("$0.00")
        self.spent_value.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.spent_value.setStyleSheet("color: #FF9800;")
        spent_layout.addWidget(self.spent_value)
        layout.addLayout(spent_layout)

        # Remaining
        remaining_layout = QVBoxLayout()
        remaining_title = QLabel("Remaining")
        remaining_title.setFont(QFont("Segoe UI", 10))
        remaining_title.setStyleSheet("color: #666666;")
        remaining_layout.addWidget(remaining_title)

        self.remaining_value = QLabel("$0.00")
        self.remaining_value.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.remaining_value.setStyleSheet("color: #4CAF50;")
        remaining_layout.addWidget(self.remaining_value)
        layout.addLayout(remaining_layout)

        # Over budget count
        over_layout = QVBoxLayout()
        over_title = QLabel("Over Budget")
        over_title.setFont(QFont("Segoe UI", 10))
        over_title.setStyleSheet("color: #666666;")
        over_layout.addWidget(over_title)

        self.over_count = QLabel("0")
        self.over_count.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.over_count.setStyleSheet("color: #F44336;")
        over_layout.addWidget(self.over_count)
        layout.addLayout(over_layout)

        # Overall progress
        progress_layout = QVBoxLayout()
        progress_title = QLabel("Overall Usage")
        progress_title.setFont(QFont("Segoe UI", 10))
        progress_title.setStyleSheet("color: #666666;")
        progress_layout.addWidget(progress_title)

        self.overall_progress = QProgressBar()
        self.overall_progress.setMaximum(100)
        self.overall_progress.setValue(0)
        self.overall_progress.setMinimumWidth(200)
        self.overall_progress.setMaximumHeight(24)
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(self.overall_progress)
        layout.addLayout(progress_layout)

        layout.addStretch()

    def update_summary(
        self,
        total_budgeted: Decimal,
        total_spent: Decimal,
        over_budget_count: int = 0
    ):
        """Update the summary values."""
        remaining = total_budgeted - total_spent
        percentage = int((total_spent / total_budgeted) * 100) if total_budgeted > 0 else 0

        self.budgeted_value.setText(f"${total_budgeted:,.2f}")
        self.spent_value.setText(f"${total_spent:,.2f}")
        self.over_count.setText(str(over_budget_count))

        if remaining >= 0:
            self.remaining_value.setText(f"${remaining:,.2f}")
            self.remaining_value.setStyleSheet("color: #4CAF50;")
        else:
            self.remaining_value.setText(f"-${abs(remaining):,.2f}")
            self.remaining_value.setStyleSheet("color: #F44336;")

        self.overall_progress.setValue(min(percentage, 100))
        self.overall_progress.setFormat(f"{percentage}%")

        # Update progress bar color
        if percentage < 50:
            color = "#4CAF50"
        elif percentage < 75:
            color = "#FFC107"
        elif percentage < 100:
            color = "#FF9800"
        else:
            color = "#F44336"

        self.overall_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)


class BudgetListPage(QWidget):
    """
    Page displaying list of all budgets with status indicators.

    Features:
    - Grid/list view of budget cards
    - Period filtering (weekly, monthly, yearly)
    - Status filtering
    - Overall summary statistics
    - Copy budget functionality
    """

    # Signals
    create_budget_requested = pyqtSignal()
    edit_budget_requested = pyqtSignal(int)
    delete_budget_requested = pyqtSignal(int)
    view_details_requested = pyqtSignal(int)
    copy_budget_requested = pyqtSignal(dict)
    refresh_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetListPage")
        self._budgets: List[Dict[str, Any]] = []
        self._categories: List[str] = []
        self._current_period_filter: Optional[str] = None
        self._current_status_filter: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # Header section
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Filter section
        filter_layout = self._create_filters()
        layout.addLayout(filter_layout)

        # Summary widget
        self.summary_widget = BudgetSummaryWidget()
        layout.addWidget(self.summary_widget)

        # Main content with charts and budgets
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Budgets scroll area
        budgets_widget = QWidget()
        budgets_layout = QVBoxLayout(budgets_widget)
        budgets_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.budgets_container = QWidget()
        self.budgets_grid = QGridLayout(self.budgets_container)
        self.budgets_grid.setContentsMargins(0, 0, 10, 0)
        self.budgets_grid.setSpacing(20)
        self.budgets_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll_area.setWidget(self.budgets_container)
        budgets_layout.addWidget(scroll_area)

        content_splitter.addWidget(budgets_widget)

        # Charts panel
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setContentsMargins(10, 0, 0, 0)
        charts_layout.setSpacing(15)

        self.bar_chart = BudgetVsActualChart()
        charts_layout.addWidget(self.bar_chart)

        self.pie_chart = BudgetDistributionChart()
        charts_layout.addWidget(self.pie_chart)

        content_splitter.addWidget(charts_widget)

        # Set splitter proportions
        content_splitter.setSizes([600, 400])

        layout.addWidget(content_splitter)

        # Placeholder for empty state
        self.empty_label = QLabel("No budgets found. Create a budget to get started!")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setStyleSheet("color: #999999;")
        self.empty_label.hide()

    def _create_header(self) -> QHBoxLayout:
        """Create the header section."""
        layout = QHBoxLayout()

        title = QLabel("Budget Management")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #333333;")
        layout.addWidget(title)

        layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(refresh_btn)

        # Create budget button
        create_btn = QPushButton("+ Create Budget")
        create_btn.setObjectName("primaryButton")
        create_btn.setStyleSheet("""
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
        create_btn.clicked.connect(self.create_budget_requested.emit)
        layout.addWidget(create_btn)

        return layout

    def _create_filters(self) -> QHBoxLayout:
        """Create the filter section."""
        layout = QHBoxLayout()

        # Period filter
        period_label = QLabel("Period:")
        period_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(period_label)

        self.period_filter = QComboBox()
        self.period_filter.addItems(["All Periods", "Weekly", "Monthly", "Quarterly", "Yearly"])
        self.period_filter.setMinimumWidth(120)
        self.period_filter.currentTextChanged.connect(self._apply_filters)
        layout.addWidget(self.period_filter)

        layout.addSpacing(20)

        # Status filter
        status_label = QLabel("Status:")
        status_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(status_label)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Under Budget", "Warning", "Near Limit", "Over Budget"])
        self.status_filter.setMinimumWidth(130)
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        layout.addWidget(self.status_filter)

        layout.addSpacing(20)

        # Category filter
        category_label = QLabel("Category:")
        category_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(category_label)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.setMinimumWidth(150)
        self.category_filter.currentTextChanged.connect(self._apply_filters)
        layout.addWidget(self.category_filter)

        layout.addStretch()

        return layout

    def _apply_filters(self):
        """Apply current filters to the budget list."""
        self._display_budgets(self._get_filtered_budgets())

    def _get_filtered_budgets(self) -> List[Dict[str, Any]]:
        """Get filtered list of budgets."""
        filtered = self._budgets.copy()

        # Period filter
        period_text = self.period_filter.currentText()
        if period_text != "All Periods":
            period = period_text.lower()
            filtered = [b for b in filtered if b.get('period', '').lower() == period]

        # Status filter
        status_text = self.status_filter.currentText()
        if status_text != "All Status":
            status_map = {
                "Under Budget": BudgetStatus.UNDER_BUDGET,
                "Warning": BudgetStatus.WARNING,
                "Near Limit": BudgetStatus.NEAR_LIMIT,
                "Over Budget": BudgetStatus.OVER_BUDGET,
            }
            target_status = status_map.get(status_text)
            if target_status:
                filtered = [
                    b for b in filtered
                    if get_budget_status(
                        Decimal(str(b.get('spent', 0))),
                        Decimal(str(b.get('limit', 0))),
                        b.get('alert_threshold', 80)
                    ) == target_status
                ]

        # Category filter
        category_text = self.category_filter.currentText()
        if category_text != "All Categories":
            filtered = [b for b in filtered if b.get('category', '') == category_text]

        return filtered

    def _display_budgets(self, budgets: List[Dict[str, Any]]):
        """Display budget cards in the grid."""
        # Clear existing cards
        while self.budgets_grid.count():
            item = self.budgets_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not budgets:
            self.budgets_grid.addWidget(self.empty_label, 0, 0, 1, 3)
            self.empty_label.show()
            return

        self.empty_label.hide()

        # Add budget cards
        for i, budget in enumerate(budgets):
            row = i // 2
            col = i % 2

            card = BudgetCard(
                budget_id=budget.get('id', 0),
                name=budget.get('name', 'Unknown'),
                category=budget.get('category', 'Uncategorized'),
                spent=Decimal(str(budget.get('spent', 0))),
                limit=Decimal(str(budget.get('limit', 0))),
                period=budget.get('period', 'monthly'),
                alert_threshold=budget.get('alert_threshold', 80)
            )

            card.edit_requested.connect(self.edit_budget_requested.emit)
            card.delete_requested.connect(self._confirm_delete)
            card.view_details_requested.connect(self.view_details_requested.emit)
            card.copy_requested.connect(self._handle_copy_budget)

            self.budgets_grid.addWidget(card, row, col)

    def _confirm_delete(self, budget_id: int):
        """Show delete confirmation dialog."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this budget?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.delete_budget_requested.emit(budget_id)

    def _handle_copy_budget(self, budget_id: int):
        """Handle copy budget request."""
        budget = next((b for b in self._budgets if b.get('id') == budget_id), None)
        if budget:
            # Create a copy of the budget data
            budget_copy = copy.deepcopy(budget)
            budget_copy.pop('id', None)
            budget_copy['name'] = f"{budget_copy.get('name', 'Budget')} (Copy)"
            budget_copy['spent'] = Decimal('0')
            self.copy_budget_requested.emit(budget_copy)

    def load_budgets(self, budgets: List[Dict[str, Any]]):
        """Load budgets into the page."""
        self._budgets = budgets

        # Update category filter
        categories = set(b.get('category', '') for b in budgets if b.get('category'))
        current_category = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        self.category_filter.addItems(sorted(categories))

        # Restore selection if possible
        index = self.category_filter.findText(current_category)
        if index >= 0:
            self.category_filter.setCurrentIndex(index)

        # Display filtered budgets
        filtered = self._get_filtered_budgets()
        self._display_budgets(filtered)

        # Update summary
        total_budgeted = sum(Decimal(str(b.get('limit', 0))) for b in budgets)
        total_spent = sum(Decimal(str(b.get('spent', 0))) for b in budgets)
        over_count = sum(
            1 for b in budgets
            if Decimal(str(b.get('spent', 0))) > Decimal(str(b.get('limit', 0)))
        )
        self.summary_widget.update_summary(total_budgeted, total_spent, over_count)

        # Update charts
        self.bar_chart.update_data(budgets)
        self.pie_chart.update_data(budgets)

    def set_categories(self, categories: List[str]):
        """Set available categories."""
        self._categories = categories


class BudgetDetailPage(QWidget):
    """
    Page showing detailed budget information with items and progress.

    Features:
    - Budget overview with progress
    - List of budget items/transactions
    - Progress bars for each item
    - Visual indicators for over/under budget
    - Charts showing spending breakdown
    """

    # Signals
    back_requested = pyqtSignal()
    edit_budget_requested = pyqtSignal(int)
    refresh_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetDetailPage")
        self._budget: Optional[Dict[str, Any]] = None
        self._transactions: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # Header with back button
        header_layout = QHBoxLayout()

        back_btn = QPushButton("< Back to Budgets")
        back_btn.setObjectName("linkButton")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(back_btn)

        header_layout.addStretch()

        # Edit button
        self.edit_btn = QPushButton("Edit Budget")
        self.edit_btn.setObjectName("secondaryButton")
        self.edit_btn.clicked.connect(self._request_edit)
        header_layout.addWidget(self.edit_btn)

        layout.addLayout(header_layout)

        # Budget title and info
        self.title_label = QLabel("Budget Details")
        self.title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side - Budget info and items
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Budget overview card
        self.overview_frame = QFrame()
        self.overview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.overview_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        overview_layout = QVBoxLayout(self.overview_frame)
        overview_layout.setContentsMargins(20, 15, 20, 15)
        overview_layout.setSpacing(15)

        # Category and period
        self.meta_label = QLabel("Category: - | Period: -")
        self.meta_label.setFont(QFont("Segoe UI", 11))
        self.meta_label.setStyleSheet("color: #666666;")
        overview_layout.addWidget(self.meta_label)

        # Main progress
        self.main_progress = BudgetItemProgressBar("Total Progress", Decimal('0'), Decimal('100'))
        overview_layout.addWidget(self.main_progress)

        # Amount details
        amounts_layout = QHBoxLayout()

        self.spent_label = QLabel("Spent: $0.00")
        self.spent_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        amounts_layout.addWidget(self.spent_label)

        amounts_layout.addStretch()

        self.remaining_label = QLabel("Remaining: $0.00")
        self.remaining_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.remaining_label.setStyleSheet("color: #4CAF50;")
        amounts_layout.addWidget(self.remaining_label)

        overview_layout.addLayout(amounts_layout)

        # Notes
        self.notes_label = QLabel("")
        self.notes_label.setFont(QFont("Segoe UI", 10))
        self.notes_label.setStyleSheet("color: #888888; font-style: italic;")
        self.notes_label.setWordWrap(True)
        overview_layout.addWidget(self.notes_label)

        left_layout.addWidget(self.overview_frame)

        # Budget items section
        items_group = QGroupBox("Budget Items / Transactions")
        items_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        items_layout = QVBoxLayout(items_group)

        # Items scroll area
        items_scroll = QScrollArea()
        items_scroll.setWidgetResizable(True)
        items_scroll.setFrameShape(QFrame.Shape.NoFrame)
        items_scroll.setMaximumHeight(300)

        self.items_container = QWidget()
        self.items_list_layout = QVBoxLayout(self.items_container)
        self.items_list_layout.setContentsMargins(0, 0, 0, 0)
        self.items_list_layout.setSpacing(5)

        items_scroll.setWidget(self.items_container)
        items_layout.addWidget(items_scroll)

        left_layout.addWidget(items_group)
        left_layout.addStretch()

        content_layout.addWidget(left_widget, stretch=3)

        # Right side - Chart
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.spending_chart = BudgetVsActualChart()
        self.spending_chart.chart.setTitle("Spending Over Time")
        right_layout.addWidget(self.spending_chart)

        content_layout.addWidget(right_widget, stretch=2)

        layout.addLayout(content_layout)

    def _request_edit(self):
        """Request to edit the current budget."""
        if self._budget:
            self.edit_budget_requested.emit(self._budget.get('id', 0))

    def load_budget(self, budget: Dict[str, Any], transactions: Optional[List[Dict[str, Any]]] = None):
        """Load budget details into the page."""
        self._budget = budget
        self._transactions = transactions or []

        # Update title
        name = budget.get('name', 'Unknown Budget')
        self.title_label.setText(name)

        # Update meta info
        category = budget.get('category', 'Uncategorized')
        period = budget.get('period', 'monthly').capitalize()
        self.meta_label.setText(f"Category: {category} | Period: {period}")

        # Update amounts
        spent = Decimal(str(budget.get('spent', 0)))
        limit = Decimal(str(budget.get('limit', 0)))
        remaining = limit - spent

        self.spent_label.setText(f"Spent: ${spent:,.2f}")

        if remaining >= 0:
            self.remaining_label.setText(f"Remaining: ${remaining:,.2f}")
            self.remaining_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.remaining_label.setText(f"Over Budget: ${abs(remaining):,.2f}")
            self.remaining_label.setStyleSheet("color: #F44336; font-weight: bold;")

        # Update main progress
        # Remove old progress widget and add new one
        for i in reversed(range(self.overview_frame.layout().count())):
            widget = self.overview_frame.layout().itemAt(i).widget()
            if isinstance(widget, BudgetItemProgressBar):
                widget.deleteLater()

        self.main_progress = BudgetItemProgressBar("Total Progress", spent, limit)
        self.overview_frame.layout().insertWidget(1, self.main_progress)

        # Update notes
        notes = budget.get('notes', '')
        if notes:
            self.notes_label.setText(f"Notes: {notes}")
            self.notes_label.show()
        else:
            self.notes_label.hide()

        # Update items list
        self._display_items()

        # Update chart
        self.spending_chart.update_data([budget])

    def _display_items(self):
        """Display budget items/transactions."""
        # Clear existing items
        while self.items_list_layout.count():
            item = self.items_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._transactions:
            no_items_label = QLabel("No transactions found for this budget.")
            no_items_label.setStyleSheet("color: #999999;")
            no_items_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_list_layout.addWidget(no_items_label)
            return

        # Add transaction items
        for transaction in self._transactions[:20]:  # Limit to 20 items
            item_frame = QFrame()
            item_frame.setFrameShape(QFrame.Shape.StyledPanel)
            item_frame.setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border-radius: 4px;
                    border: none;
                }
            """)

            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 8, 10, 8)

            # Transaction description
            desc = transaction.get('description', 'Unknown')
            desc_label = QLabel(desc)
            desc_label.setFont(QFont("Segoe UI", 10))
            item_layout.addWidget(desc_label)

            # Date
            trans_date = transaction.get('date', '')
            if trans_date:
                date_label = QLabel(str(trans_date))
                date_label.setFont(QFont("Segoe UI", 9))
                date_label.setStyleSheet("color: #888888;")
                item_layout.addWidget(date_label)

            item_layout.addStretch()

            # Amount
            amount = Decimal(str(transaction.get('amount', 0)))
            amount_label = QLabel(f"${amount:,.2f}")
            amount_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            amount_label.setStyleSheet("color: #F44336;")
            item_layout.addWidget(amount_label)

            self.items_list_layout.addWidget(item_frame)

        self.items_list_layout.addStretch()


class BudgetFormPage(QWidget):
    """
    Page for creating or editing a budget.

    Features:
    - Form fields for budget properties
    - Period selection (weekly, monthly, yearly)
    - Category selection/creation
    - Alert threshold setting
    - Budget items management
    """

    # Signals
    budget_saved = pyqtSignal(dict)
    cancel_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetFormPage")
        self._budget: Optional[Dict[str, Any]] = None
        self._categories: List[str] = []
        self._is_copy: bool = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the form page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        self.title_label = QLabel("Create New Budget")
        self.title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Form container
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.Shape.StyledPanel)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        form_frame.setMaximumWidth(700)

        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(30, 25, 30, 25)
        form_layout.setSpacing(20)

        # Form fields
        fields_layout = QFormLayout()
        fields_layout.setSpacing(15)
        fields_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Budget name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Monthly Groceries")
        self.name_input.setMinimumWidth(300)
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        fields_layout.addRow("Budget Name:", self.name_input)

        # Category
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setMinimumWidth(300)
        self.category_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
        """)
        fields_layout.addRow("Category:", self.category_combo)

        # Budget limit
        self.limit_input = QDoubleSpinBox()
        self.limit_input.setPrefix("$ ")
        self.limit_input.setDecimals(2)
        self.limit_input.setMaximum(999999999.99)
        self.limit_input.setMinimum(0.01)
        self.limit_input.setValue(100.00)
        self.limit_input.setMinimumWidth(200)
        self.limit_input.setStyleSheet("""
            QDoubleSpinBox {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
        """)
        fields_layout.addRow("Budget Limit:", self.limit_input)

        # Period selection
        period_widget = QWidget()
        period_layout = QHBoxLayout(period_widget)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.setSpacing(15)

        self.period_buttons = {}
        for period in ["Weekly", "Monthly", "Quarterly", "Yearly"]:
            btn = QPushButton(period)
            btn.setCheckable(True)
            btn.setMinimumWidth(80)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 15px;
                    border: 2px solid #CCCCCC;
                    border-radius: 4px;
                    background-color: #FFFFFF;
                }
                QPushButton:checked {
                    border-color: #2196F3;
                    background-color: #E3F2FD;
                    color: #1976D2;
                }
                QPushButton:hover {
                    border-color: #2196F3;
                }
            """)
            btn.clicked.connect(lambda checked, p=period: self._select_period(p))
            period_layout.addWidget(btn)
            self.period_buttons[period.lower()] = btn

        period_layout.addStretch()
        fields_layout.addRow("Period:", period_widget)

        # Select monthly by default
        self.period_buttons["monthly"].setChecked(True)
        self._selected_period = "monthly"

        # Start date
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setMinimumWidth(200)
        self.start_date.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
        """)
        fields_layout.addRow("Start Date:", self.start_date)

        # Alert threshold
        threshold_widget = QWidget()
        threshold_layout = QHBoxLayout(threshold_widget)
        threshold_layout.setContentsMargins(0, 0, 0, 0)

        self.threshold_input = QSpinBox()
        self.threshold_input.setSuffix(" %")
        self.threshold_input.setRange(50, 100)
        self.threshold_input.setValue(80)
        self.threshold_input.setMinimumWidth(100)
        self.threshold_input.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
        """)
        threshold_layout.addWidget(self.threshold_input)

        threshold_help = QLabel("Alert when spending reaches this percentage")
        threshold_help.setStyleSheet("color: #888888; font-size: 11px;")
        threshold_layout.addWidget(threshold_help)
        threshold_layout.addStretch()

        fields_layout.addRow("Alert Threshold:", threshold_widget)

        # Auto-rollover checkbox
        self.rollover_check = QCheckBox("Roll over unused amount to next period")
        fields_layout.addRow("", self.rollover_check)

        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Optional notes about this budget...")
        self.notes_input.setStyleSheet("""
            QTextEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
        """)
        fields_layout.addRow("Notes:", self.notes_input)

        form_layout.addLayout(fields_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        cancel_btn.clicked.connect(self.cancel_requested.emit)
        button_layout.addWidget(cancel_btn)

        button_layout.addSpacing(10)

        save_btn = QPushButton("Save Budget")
        save_btn.setObjectName("primaryButton")
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
                border: none;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self._save_budget)
        button_layout.addWidget(save_btn)

        form_layout.addLayout(button_layout)

        layout.addWidget(form_frame)
        layout.addStretch()

    def _select_period(self, period: str):
        """Handle period button selection."""
        period_lower = period.lower()
        for p, btn in self.period_buttons.items():
            btn.setChecked(p == period_lower)
        self._selected_period = period_lower

    def _save_budget(self):
        """Validate and save the budget."""
        # Validate required fields
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a budget name."
            )
            self.name_input.setFocus()
            return

        if not self.category_combo.currentText().strip():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select or enter a category."
            )
            self.category_combo.setFocus()
            return

        if self.limit_input.value() <= 0:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a valid budget limit."
            )
            self.limit_input.setFocus()
            return

        # Build budget data
        budget_data = {
            'name': self.name_input.text().strip(),
            'category': self.category_combo.currentText().strip(),
            'limit': Decimal(str(self.limit_input.value())),
            'period': self._selected_period,
            'start_date': self.start_date.date().toString("yyyy-MM-dd"),
            'alert_threshold': self.threshold_input.value(),
            'rollover': self.rollover_check.isChecked(),
            'notes': self.notes_input.toPlainText().strip()
        }

        if self._budget and not self._is_copy:
            budget_data['id'] = self._budget.get('id')

        self.budget_saved.emit(budget_data)

    def set_categories(self, categories: List[str]):
        """Set available categories for the dropdown."""
        self._categories = categories
        current = self.category_combo.currentText()
        self.category_combo.clear()
        self.category_combo.addItems(categories)
        if current:
            self.category_combo.setCurrentText(current)

    def load_budget(self, budget: Optional[Dict[str, Any]] = None, is_copy: bool = False):
        """Load budget data into the form for editing or copying."""
        self._budget = budget
        self._is_copy = is_copy

        if budget:
            if is_copy:
                self.title_label.setText("Copy Budget")
            else:
                self.title_label.setText("Edit Budget")

            self.name_input.setText(budget.get('name', ''))

            category = budget.get('category', '')
            index = self.category_combo.findText(category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setCurrentText(category)

            self.limit_input.setValue(float(budget.get('limit', 100)))

            period = budget.get('period', 'monthly').lower()
            self._select_period(period)

            start_date = budget.get('start_date')
            if start_date:
                if isinstance(start_date, str):
                    self.start_date.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
                elif isinstance(start_date, date):
                    self.start_date.setDate(QDate(start_date.year, start_date.month, start_date.day))

            self.threshold_input.setValue(budget.get('alert_threshold', 80))
            self.rollover_check.setChecked(budget.get('rollover', False))
            self.notes_input.setPlainText(budget.get('notes', ''))
        else:
            self.title_label.setText("Create New Budget")
            self.clear_form()

    def clear_form(self):
        """Clear all form fields."""
        self._budget = None
        self._is_copy = False
        self.name_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.limit_input.setValue(100.00)
        self._select_period("monthly")
        self.start_date.setDate(QDate.currentDate())
        self.threshold_input.setValue(80)
        self.rollover_check.setChecked(False)
        self.notes_input.clear()


class BudgetsPage(QWidget):
    """
    Main budget management container page.

    Manages navigation between:
    - BudgetListPage: List of all budgets
    - BudgetDetailPage: Detailed view of a single budget
    - BudgetFormPage: Create/edit budget form

    Features:
    - Budget CRUD operations
    - Period filtering
    - Copy budget functionality
    - Charts for budget vs actual
    - Visual indicators for over/under budget
    """

    # Signals
    budget_created = pyqtSignal(dict)
    budget_updated = pyqtSignal(dict)
    budget_deleted = pyqtSignal(int)
    view_transactions = pyqtSignal(int, str)  # budget_id, category
    refresh_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetsPage")
        self._budgets: List[Dict[str, Any]] = []
        self._categories: List[str] = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the main page UI with stacked widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for page navigation
        self.stack = QStackedWidget()

        # Create pages
        self.list_page = BudgetListPage()
        self.detail_page = BudgetDetailPage()
        self.form_page = BudgetFormPage()

        # Add pages to stack
        self.stack.addWidget(self.list_page)   # Index 0
        self.stack.addWidget(self.detail_page)  # Index 1
        self.stack.addWidget(self.form_page)    # Index 2

        layout.addWidget(self.stack)

    def _connect_signals(self):
        """Connect page signals."""
        # List page signals
        self.list_page.create_budget_requested.connect(self._show_create_form)
        self.list_page.edit_budget_requested.connect(self._show_edit_form)
        self.list_page.delete_budget_requested.connect(self.budget_deleted.emit)
        self.list_page.view_details_requested.connect(self._show_detail_page)
        self.list_page.copy_budget_requested.connect(self._show_copy_form)
        self.list_page.refresh_requested.connect(self.refresh_requested.emit)

        # Detail page signals
        self.detail_page.back_requested.connect(self._show_list_page)
        self.detail_page.edit_budget_requested.connect(self._show_edit_form)
        self.detail_page.refresh_requested.connect(self.refresh_requested.emit)

        # Form page signals
        self.form_page.budget_saved.connect(self._handle_budget_saved)
        self.form_page.cancel_requested.connect(self._show_list_page)

    def _show_list_page(self):
        """Navigate to the list page."""
        self.stack.setCurrentIndex(0)

    def _show_detail_page(self, budget_id: int):
        """Navigate to the detail page for a specific budget."""
        budget = next((b for b in self._budgets if b.get('id') == budget_id), None)
        if budget:
            self.detail_page.load_budget(budget)
            self.stack.setCurrentIndex(1)

    def _show_create_form(self):
        """Navigate to the create budget form."""
        self.form_page.set_categories(self._categories)
        self.form_page.load_budget(None)
        self.stack.setCurrentIndex(2)

    def _show_edit_form(self, budget_id: int):
        """Navigate to the edit budget form."""
        budget = next((b for b in self._budgets if b.get('id') == budget_id), None)
        if budget:
            self.form_page.set_categories(self._categories)
            self.form_page.load_budget(budget, is_copy=False)
            self.stack.setCurrentIndex(2)

    def _show_copy_form(self, budget_data: dict):
        """Navigate to the form with copied budget data."""
        self.form_page.set_categories(self._categories)
        self.form_page.load_budget(budget_data, is_copy=True)
        self.stack.setCurrentIndex(2)

    def _handle_budget_saved(self, budget_data: dict):
        """Handle budget save from form."""
        if 'id' in budget_data:
            self.budget_updated.emit(budget_data)
        else:
            self.budget_created.emit(budget_data)
        self._show_list_page()

    def load_budgets(self, budgets: List[Dict[str, Any]]):
        """Load budgets into the page."""
        self._budgets = budgets
        self.list_page.load_budgets(budgets)

    def load_budget_details(self, budget_id: int, transactions: List[Dict[str, Any]]):
        """Load budget details with transactions."""
        budget = next((b for b in self._budgets if b.get('id') == budget_id), None)
        if budget:
            self.detail_page.load_budget(budget, transactions)

    def set_categories(self, categories: List[str]):
        """Set available categories."""
        self._categories = categories
        self.list_page.set_categories(categories)
        self.form_page.set_categories(categories)

    def show_list(self):
        """Public method to show the list page."""
        self._show_list_page()

    def show_create(self):
        """Public method to show the create form."""
        self._show_create_form()

    def show_edit(self, budget_id: int):
        """Public method to show the edit form."""
        self._show_edit_form(budget_id)

    def show_details(self, budget_id: int):
        """Public method to show budget details."""
        self._show_detail_page(budget_id)
