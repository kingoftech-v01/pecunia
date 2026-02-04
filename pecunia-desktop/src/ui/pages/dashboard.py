"""
Dashboard Page Module

Main dashboard displaying financial overview, charts, and quick actions.
Provides a comprehensive view of the user's financial status with
widgets for balance, transactions, budgets, sync status, and AI insights.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QSizePolicy, QSpacerItem, QProgressBar,
    QGraphicsDropShadowEffect, QStackedWidget
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QSize, QSettings
)
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from .dashboard_widgets import (
    BalanceWidget,
    RecentTransactionsWidget,
    BudgetProgressWidget,
    QuickActionsWidget,
    SyncStatusWidget,
    AIInsightsWidget,
    DashboardWidgetContainer
)


class SyncStatus(Enum):
    """Synchronization status states."""
    SYNCED = "synced"
    SYNCING = "syncing"
    OFFLINE = "offline"
    ERROR = "error"


class SummaryCard(QFrame):
    """A card widget displaying a summary metric."""

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        icon: str = "",
        color: str = "#4CAF50",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("summaryCard")
        self._color = color
        self._setup_ui(title, value, subtitle, icon, color)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self, title: str, value: str, subtitle: str, icon: str, color: str):
        """Set up the card UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(200, 120)
        self.setMaximumHeight(150)
        self.setStyleSheet(f"""
            QFrame#summaryCard {{
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
            QFrame#summaryCard:hover {{
                background-color: #F5F5F5;
                border-color: #BDBDBD;
            }}
        """)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        # Header with icon and title
        header_layout = QHBoxLayout()

        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI Emoji", 18))
            header_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setFont(QFont("Segoe UI", 11))
        title_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        self.value_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)

        # Subtitle
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("cardSubtitle")
            self.subtitle_label.setFont(QFont("Segoe UI", 9))
            self.subtitle_label.setStyleSheet("color: #999999;")
            layout.addWidget(self.subtitle_label)

        layout.addStretch()

    def set_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)

    def set_subtitle(self, subtitle: str):
        """Update the subtitle."""
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.setText(subtitle)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class QuickActionButton(QPushButton):
    """A styled quick action button."""

    def __init__(
        self,
        text: str,
        icon: str = "",
        color: str = "#2196F3",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("quickActionButton")

        display_text = f"{icon} {text}" if icon else text
        self.setText(display_text)

        self.setMinimumSize(140, 45)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(f"""
            QPushButton#quickActionButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }}
            QPushButton#quickActionButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton#quickActionButton:pressed {{
                background-color: {self._darken_color(color)};
            }}
        """)

    def _lighten_color(self, hex_color: str) -> str:
        """Lighten a hex color."""
        color = QColor(hex_color)
        return color.lighter(115).name()

    def _darken_color(self, hex_color: str) -> str:
        """Darken a hex color."""
        color = QColor(hex_color)
        return color.darker(115).name()


class RecentTransactionItem(QFrame):
    """A widget displaying a single recent transaction."""

    clicked = pyqtSignal(int)  # Emits transaction ID

    def __init__(
        self,
        transaction_id: int,
        description: str,
        amount: Decimal,
        category: str,
        date: datetime,
        is_expense: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.transaction_id = transaction_id
        self.setObjectName("recentTransactionItem")
        self._setup_ui(description, amount, category, date, is_expense)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(
        self,
        description: str,
        amount: Decimal,
        category: str,
        date: datetime,
        is_expense: bool
    ):
        """Set up the transaction item UI."""
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumHeight(60)
        self.setStyleSheet("""
            QFrame#recentTransactionItem {
                background-color: transparent;
                border-bottom: 1px solid #EEEEEE;
            }
            QFrame#recentTransactionItem:hover {
                background-color: #F5F5F5;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Left side - category indicator
        category_indicator = QLabel()
        category_indicator.setFixedSize(8, 40)
        category_indicator.setStyleSheet(f"""
            background-color: {'#E57373' if is_expense else '#81C784'};
            border-radius: 4px;
        """)
        layout.addWidget(category_indicator)

        # Middle - description and category
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)

        desc_label = QLabel(description)
        desc_label.setFont(QFont("Segoe UI", 11))
        desc_label.setStyleSheet("color: #333333;")
        desc_label.setObjectName("transactionDescription")
        left_layout.addWidget(desc_label)

        meta_label = QLabel(f"{category} | {date.strftime('%b %d, %Y')}")
        meta_label.setFont(QFont("Segoe UI", 9))
        meta_label.setStyleSheet("color: #888888;")
        meta_label.setObjectName("transactionMeta")
        left_layout.addWidget(meta_label)

        layout.addLayout(left_layout)
        layout.addStretch()

        # Right side - amount
        amount_str = f"-${amount:,.2f}" if is_expense else f"+${amount:,.2f}"
        amount_color = "#E57373" if is_expense else "#81C784"

        amount_label = QLabel(amount_str)
        amount_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        amount_label.setStyleSheet(f"color: {amount_color};")
        layout.addWidget(amount_label)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.transaction_id)
        super().mousePressEvent(event)


class SyncStatusIndicator(QWidget):
    """Widget displaying synchronization status."""

    sync_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._status = SyncStatus.SYNCED
        self._last_sync: Optional[datetime] = None
        self._pending_count = 0
        self._setup_ui()

    def _setup_ui(self):
        """Set up the sync status UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Status indicator dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(10, 10)
        layout.addWidget(self.status_dot)

        # Status text
        self.status_label = QLabel("Synced")
        self.status_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.status_label)

        # Pending count (if any)
        self.pending_label = QLabel()
        self.pending_label.setFont(QFont("Segoe UI", 9))
        self.pending_label.setStyleSheet("color: #FF9800;")
        self.pending_label.hide()
        layout.addWidget(self.pending_label)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_display()

    def mousePressEvent(self, event):
        """Handle click to trigger sync."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.sync_clicked.emit()
        super().mousePressEvent(event)

    def set_status(
        self,
        status: SyncStatus,
        last_sync: Optional[datetime] = None,
        pending_count: int = 0
    ):
        """Update the sync status."""
        self._status = status
        self._last_sync = last_sync
        self._pending_count = pending_count
        self._update_display()

    def _update_display(self):
        """Update the visual display based on status."""
        status_styles = {
            SyncStatus.SYNCED: ("#4CAF50", "Synced"),
            SyncStatus.SYNCING: ("#2196F3", "Syncing..."),
            SyncStatus.OFFLINE: ("#9E9E9E", "Offline"),
            SyncStatus.ERROR: ("#F44336", "Sync Error"),
        }

        color, text = status_styles.get(self._status, ("#9E9E9E", "Unknown"))

        self.status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 5px;
        """)

        if self._status == SyncStatus.SYNCED and self._last_sync:
            time_ago = self._get_time_ago(self._last_sync)
            text = f"Synced {time_ago}"

        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

        # Show pending count if any
        if self._pending_count > 0 and self._status != SyncStatus.SYNCING:
            self.pending_label.setText(f"({self._pending_count} pending)")
            self.pending_label.show()
        else:
            self.pending_label.hide()

    def _get_time_ago(self, dt: datetime) -> str:
        """Get human-readable time ago string."""
        now = datetime.now()
        diff = now - dt

        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago"


class BudgetProgressItem(QWidget):
    """Widget displaying a single budget progress bar."""

    clicked = pyqtSignal(str)  # Emits category name

    def __init__(
        self,
        category: str,
        spent: Decimal,
        budget: Decimal,
        color: str = "#4CAF50",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.category = category
        self._setup_ui(category, spent, budget, color)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self, category: str, spent: Decimal, budget: Decimal, color: str):
        """Set up the budget progress item UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(4)

        # Header row
        header_layout = QHBoxLayout()

        name_label = QLabel(category)
        name_label.setFont(QFont("Segoe UI", 10))
        name_label.setStyleSheet("color: #333333;")
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        percentage = (spent / budget * 100) if budget > 0 else 0
        amount_text = f"${spent:,.2f} / ${budget:,.2f}"

        # Color based on percentage
        if percentage >= 100:
            text_color = "#F44336"
        elif percentage >= 80:
            text_color = "#FF9800"
        else:
            text_color = "#666666"

        amount_label = QLabel(amount_text)
        amount_label.setFont(QFont("Segoe UI", 9))
        amount_label.setStyleSheet(f"color: {text_color};")
        header_layout.addWidget(amount_label)

        layout.addLayout(header_layout)

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        progress_bar.setValue(min(int(percentage), 100))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(8)

        # Progress bar color based on percentage
        if percentage >= 100:
            bar_color = "#F44336"
        elif percentage >= 80:
            bar_color = "#FF9800"
        else:
            bar_color = color

        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(progress_bar)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.category)
        super().mousePressEvent(event)


class ChartPlaceholder(QFrame):
    """Placeholder widget for charts."""

    def __init__(
        self,
        title: str,
        chart_type: str = "pie",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.title = title
        self.chart_type = chart_type
        self._data: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the chart placeholder UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        self.setMinimumHeight(200)

        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333; border: none;")
        layout.addWidget(title_label)

        layout.addStretch()

        # Chart icon placeholder
        icon = "O" if self.chart_type == "pie" else "~"
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 48))
        icon_label.setStyleSheet("color: #BDBDBD; border: none;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Placeholder text
        self.placeholder_label = QLabel("Chart will appear here")
        self.placeholder_label.setFont(QFont("Segoe UI", 10))
        self.placeholder_label.setStyleSheet("color: #999999; border: none;")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder_label)

        layout.addStretch()

    def set_data(self, data: List[Dict[str, Any]]):
        """Set chart data (for future implementation)."""
        self._data = data
        if data:
            self.placeholder_label.setText(f"{len(data)} data points")
        else:
            self.placeholder_label.setText("No data available")


class DashboardPage(QWidget):
    """
    Main dashboard page displaying financial overview.

    Features:
    - Summary cards (total balance, income, expenses this month)
    - Recent transactions list
    - Budget progress overview
    - Quick add transaction buttons
    - Spending by category pie chart placeholder
    - Monthly trend line chart placeholder
    - Sync status indicator
    - AI insights widget
    - Refresh button with auto-refresh support
    - Responsive layout with draggable widgets

    Signals:
        navigate_to_transactions: Navigate to transactions page
        navigate_to_budgets: Navigate to budgets page
        navigate_to_settings: Navigate to settings page
        navigate_to_accounts: Navigate to accounts page
        add_transaction_requested: Open add transaction dialog
        add_income_requested: Open add income dialog
        add_expense_requested: Open add expense dialog
        view_transaction_requested: View specific transaction (int: ID)
        view_budget_requested: View specific budget (str: category)
        export_requested: Export data
        refresh_requested: Refresh dashboard data
        sync_requested: Trigger sync
    """

    # Navigation signals
    navigate_to_transactions = pyqtSignal()
    navigate_to_budgets = pyqtSignal()
    navigate_to_settings = pyqtSignal()
    navigate_to_accounts = pyqtSignal()

    # Action signals
    add_transaction_requested = pyqtSignal()
    add_income_requested = pyqtSignal()
    add_expense_requested = pyqtSignal()
    view_transaction_requested = pyqtSignal(int)
    view_budget_requested = pyqtSignal(str)
    export_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    sync_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("dashboardPage")
        self._summary_cards: Dict[str, SummaryCard] = {}
        self._transaction_items: List[RecentTransactionItem] = []
        self._budget_items: List[BudgetProgressItem] = []
        self._auto_refresh_timer: Optional[QTimer] = None
        self._auto_refresh_interval = 60000  # 1 minute default
        self._settings = QSettings("Pecunia", "Dashboard")
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the dashboard UI."""
        # Main scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #F5F5F5;
                border: none;
            }
        """)

        # Content widget
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #F5F5F5;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(25)

        # Header section
        header_layout = self._create_header()
        content_layout.addLayout(header_layout)

        # Summary cards section
        cards_layout = self._create_summary_cards()
        content_layout.addLayout(cards_layout)

        # Main content area (charts and transactions side by side)
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(20)

        # Left column - Charts and Budget
        left_column = self._create_left_column()
        main_content_layout.addWidget(left_column, stretch=2)

        # Right column - Transactions and Quick Actions
        right_column = self._create_right_column()
        main_content_layout.addWidget(right_column, stretch=1)

        content_layout.addLayout(main_content_layout)

        # AI Insights section (full width at bottom)
        self.ai_insights_widget = AIInsightsWidget()
        self.ai_insights_widget.insight_clicked.connect(self._on_insight_clicked)
        self.ai_insights_widget.refresh_insights_clicked.connect(self._refresh_insights)
        content_layout.addWidget(self.ai_insights_widget)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

    def _create_header(self) -> QHBoxLayout:
        """Create the header section with greeting and controls."""
        layout = QHBoxLayout()

        # Welcome message
        welcome_layout = QVBoxLayout()

        greeting = self._get_greeting()
        self.greeting_label = QLabel(greeting)
        self.greeting_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.greeting_label.setStyleSheet("color: #333333;")
        welcome_layout.addWidget(self.greeting_label)

        self.date_label = QLabel(datetime.now().strftime("%A, %B %d, %Y"))
        self.date_label.setFont(QFont("Segoe UI", 11))
        self.date_label.setStyleSheet("color: #666666;")
        welcome_layout.addWidget(self.date_label)

        layout.addLayout(welcome_layout)
        layout.addStretch()

        # Sync status indicator
        self.sync_indicator = SyncStatusIndicator()
        self.sync_indicator.sync_clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_indicator)

        layout.addSpacing(20)

        # Auto-refresh toggle
        self.auto_refresh_btn = QPushButton("Auto")
        self.auto_refresh_btn.setObjectName("autoRefreshButton")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.setFont(QFont("Segoe UI", 9))
        self.auto_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_refresh_btn.setToolTip("Toggle auto-refresh")
        self.auto_refresh_btn.setStyleSheet("""
            QPushButton#autoRefreshButton {
                background-color: #FFFFFF;
                color: #666666;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton#autoRefreshButton:checked {
                background-color: #E3F2FD;
                color: #1976D2;
                border-color: #1976D2;
            }
            QPushButton#autoRefreshButton:hover {
                background-color: #F5F5F5;
            }
        """)
        self.auto_refresh_btn.toggled.connect(self._toggle_auto_refresh)
        layout.addWidget(self.auto_refresh_btn)

        layout.addSpacing(10)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("refreshButton")
        refresh_btn.setFont(QFont("Segoe UI", 10))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton#refreshButton {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #BDBDBD;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton#refreshButton:hover {
                background-color: #F5F5F5;
                border-color: #9E9E9E;
            }
            QPushButton#refreshButton:pressed {
                background-color: #EEEEEE;
            }
        """)
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(refresh_btn)

        return layout

    def _get_greeting(self) -> str:
        """Get appropriate greeting based on time of day."""
        hour = datetime.now().hour
        if hour < 12:
            return "Good Morning"
        elif hour < 17:
            return "Good Afternoon"
        else:
            return "Good Evening"

    def _create_summary_cards(self) -> QHBoxLayout:
        """Create the summary cards section."""
        layout = QHBoxLayout()
        layout.setSpacing(15)

        # Total Balance card
        balance_card = SummaryCard(
            title="Total Balance",
            value="$0.00",
            subtitle="Across all accounts",
            color="#2196F3"
        )
        balance_card.clicked.connect(self.navigate_to_accounts.emit)
        self._summary_cards['balance'] = balance_card
        layout.addWidget(balance_card)

        # Monthly Income card
        income_card = SummaryCard(
            title="Income This Month",
            value="$0.00",
            subtitle="Total deposits",
            color="#4CAF50"
        )
        income_card.clicked.connect(self.navigate_to_transactions.emit)
        self._summary_cards['income'] = income_card
        layout.addWidget(income_card)

        # Monthly Expenses card
        expenses_card = SummaryCard(
            title="Expenses This Month",
            value="$0.00",
            subtitle="Total spending",
            color="#F44336"
        )
        expenses_card.clicked.connect(self.navigate_to_transactions.emit)
        self._summary_cards['expenses'] = expenses_card
        layout.addWidget(expenses_card)

        # Net Savings card
        savings_card = SummaryCard(
            title="Net Savings",
            value="$0.00",
            subtitle="This month",
            color="#9C27B0"
        )
        savings_card.clicked.connect(self.navigate_to_budgets.emit)
        self._summary_cards['savings'] = savings_card
        layout.addWidget(savings_card)

        return layout

    def _create_left_column(self) -> QWidget:
        """Create the left column with charts and budget overview."""
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Spending by Category chart placeholder
        self.pie_chart = ChartPlaceholder(
            title="Spending by Category",
            chart_type="pie"
        )
        layout.addWidget(self.pie_chart)

        # Monthly Trend chart placeholder
        self.line_chart = ChartPlaceholder(
            title="Monthly Trend",
            chart_type="line"
        )
        layout.addWidget(self.line_chart)

        # Budget Progress section
        budget_section = self._create_budget_section()
        layout.addWidget(budget_section)

        return column

    def _create_budget_section(self) -> QFrame:
        """Create the budget progress overview section."""
        frame = QFrame()
        frame.setObjectName("budgetSection")
        frame.setStyleSheet("""
            QFrame#budgetSection {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)

        # Add shadow
        shadow = QGraphicsDropShadowEffect(frame)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 2)
        frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Section header
        header_layout = QHBoxLayout()

        title = QLabel("Budget Progress")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #333333;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        view_all_btn = QPushButton("View All")
        view_all_btn.setObjectName("linkButton")
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_all_btn.setStyleSheet("""
            QPushButton#linkButton {
                background-color: transparent;
                color: #2196F3;
                border: none;
                padding: 5px;
            }
            QPushButton#linkButton:hover {
                color: #1976D2;
                text-decoration: underline;
            }
        """)
        view_all_btn.clicked.connect(self.navigate_to_budgets.emit)
        header_layout.addWidget(view_all_btn)

        layout.addLayout(header_layout)

        # Budget items container
        self.budget_container = QVBoxLayout()
        self.budget_container.setSpacing(5)

        # Placeholder message
        self.no_budgets_label = QLabel("No budgets configured")
        self.no_budgets_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_budgets_label.setStyleSheet("color: #999999; padding: 20px;")
        self.budget_container.addWidget(self.no_budgets_label)

        layout.addLayout(self.budget_container)

        return frame

    def _create_right_column(self) -> QWidget:
        """Create the right column with quick actions and transactions."""
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Quick actions section
        actions_section = self._create_quick_actions()
        layout.addWidget(actions_section)

        # Sync status widget
        self.sync_widget = SyncStatusWidget()
        self.sync_widget.sync_now_clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_widget)

        # Recent transactions section
        transactions_section = self._create_recent_transactions()
        layout.addWidget(transactions_section)

        layout.addStretch()

        return column

    def _create_quick_actions(self) -> QFrame:
        """Create the quick actions section."""
        frame = QFrame()
        frame.setObjectName("quickActionsSection")
        frame.setStyleSheet("""
            QFrame#quickActionsSection {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)

        # Add shadow
        shadow = QGraphicsDropShadowEffect(frame)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 2)
        frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Section title
        title = QLabel("Quick Actions")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #333333;")
        layout.addWidget(title)

        # Quick Add Transaction button (primary action)
        add_transaction_btn = QuickActionButton(
            "Add Transaction",
            icon="+",
            color="#4CAF50"
        )
        add_transaction_btn.setMinimumHeight(50)
        add_transaction_btn.clicked.connect(self.add_transaction_requested.emit)
        layout.addWidget(add_transaction_btn)

        # Secondary actions grid
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(10)

        add_income_btn = QuickActionButton("Income", icon="+", color="#2196F3")
        add_income_btn.clicked.connect(self.add_income_requested.emit)
        buttons_layout.addWidget(add_income_btn, 0, 0)

        add_expense_btn = QuickActionButton("Expense", icon="-", color="#FF5722")
        add_expense_btn.clicked.connect(self.add_expense_requested.emit)
        buttons_layout.addWidget(add_expense_btn, 0, 1)

        view_budgets_btn = QuickActionButton("Budgets", color="#9C27B0")
        view_budgets_btn.clicked.connect(self.navigate_to_budgets.emit)
        buttons_layout.addWidget(view_budgets_btn, 1, 0)

        export_btn = QuickActionButton("Export", color="#607D8B")
        export_btn.clicked.connect(self.export_requested.emit)
        buttons_layout.addWidget(export_btn, 1, 1)

        layout.addLayout(buttons_layout)

        return frame

    def _create_recent_transactions(self) -> QFrame:
        """Create the recent transactions section."""
        frame = QFrame()
        frame.setObjectName("recentTransactionsSection")
        frame.setStyleSheet("""
            QFrame#recentTransactionsSection {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        frame.setMinimumWidth(300)

        # Add shadow
        shadow = QGraphicsDropShadowEffect(frame)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 2)
        frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Section header
        header_layout = QHBoxLayout()

        title = QLabel("Recent Transactions")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #333333;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        view_all_btn = QPushButton("View All")
        view_all_btn.setObjectName("linkButton")
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_all_btn.setStyleSheet("""
            QPushButton#linkButton {
                background-color: transparent;
                color: #2196F3;
                border: none;
                padding: 5px;
            }
            QPushButton#linkButton:hover {
                color: #1976D2;
                text-decoration: underline;
            }
        """)
        view_all_btn.clicked.connect(self.navigate_to_transactions.emit)
        header_layout.addWidget(view_all_btn)

        layout.addLayout(header_layout)

        # Transactions container
        self.transactions_container = QVBoxLayout()
        self.transactions_container.setSpacing(0)

        # Placeholder message
        self.no_transactions_label = QLabel("No recent transactions")
        self.no_transactions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_transactions_label.setStyleSheet("color: #999999; padding: 30px;")
        self.transactions_container.addWidget(self.no_transactions_label)

        layout.addLayout(self.transactions_container)

        return frame

    # -------------------------------------------------------------------------
    # Settings Management
    # -------------------------------------------------------------------------

    def _load_settings(self):
        """Load dashboard settings."""
        auto_refresh = self._settings.value("auto_refresh", False, type=bool)
        self.auto_refresh_btn.setChecked(auto_refresh)

        interval = self._settings.value("refresh_interval", 60000, type=int)
        self._auto_refresh_interval = interval

    def _save_settings(self):
        """Save dashboard settings."""
        self._settings.setValue("auto_refresh", self.auto_refresh_btn.isChecked())
        self._settings.setValue("refresh_interval", self._auto_refresh_interval)

    # -------------------------------------------------------------------------
    # Auto-refresh
    # -------------------------------------------------------------------------

    def _toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh functionality."""
        if enabled:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()
        self._save_settings()

    def _start_auto_refresh(self):
        """Start the auto-refresh timer."""
        if self._auto_refresh_timer is None:
            self._auto_refresh_timer = QTimer(self)
            self._auto_refresh_timer.timeout.connect(self._on_auto_refresh)

        self._auto_refresh_timer.start(self._auto_refresh_interval)

    def _stop_auto_refresh(self):
        """Stop the auto-refresh timer."""
        if self._auto_refresh_timer:
            self._auto_refresh_timer.stop()

    def _on_auto_refresh(self):
        """Handle auto-refresh timer tick."""
        self.refresh_requested.emit()

    def _on_refresh_clicked(self):
        """Handle manual refresh button click."""
        self.refresh_requested.emit()

    def set_auto_refresh_interval(self, interval_ms: int):
        """Set the auto-refresh interval in milliseconds."""
        self._auto_refresh_interval = interval_ms
        if self._auto_refresh_timer and self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.setInterval(interval_ms)
        self._save_settings()

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_insight_clicked(self, insight_id: str):
        """Handle insight click."""
        # Could navigate to relevant page or show detail dialog
        pass

    def _refresh_insights(self):
        """Refresh AI insights."""
        self.ai_insights_widget.set_loading(True)
        # In real implementation, this would trigger AI analysis
        # For now, show sample insights
        QTimer.singleShot(1000, self.ai_insights_widget.add_sample_insights)

    # -------------------------------------------------------------------------
    # Public methods for updating dashboard data
    # -------------------------------------------------------------------------

    def update_summary(
        self,
        balance: Decimal,
        income: Decimal,
        expenses: Decimal,
        savings: Optional[Decimal] = None
    ):
        """Update the summary cards with new values."""
        self._summary_cards['balance'].set_value(f"${balance:,.2f}")
        self._summary_cards['income'].set_value(f"${income:,.2f}")
        self._summary_cards['expenses'].set_value(f"${expenses:,.2f}")

        if savings is not None:
            self._summary_cards['savings'].set_value(f"${savings:,.2f}")
        else:
            calculated_savings = income - expenses
            self._summary_cards['savings'].set_value(f"${calculated_savings:,.2f}")

            # Update savings card color based on value
            if calculated_savings >= 0:
                self._summary_cards['savings'].value_label.setStyleSheet("color: #4CAF50;")
            else:
                self._summary_cards['savings'].value_label.setStyleSheet("color: #F44336;")

    def update_balance_subtitle(self, subtitle: str):
        """Update the balance card subtitle."""
        self._summary_cards['balance'].set_subtitle(subtitle)

    def update_recent_transactions(self, transactions: List[Dict[str, Any]]):
        """
        Update the recent transactions list.

        Args:
            transactions: List of transaction dicts with keys:
                - id: Transaction ID
                - description: Transaction description
                - amount: Transaction amount
                - category: Category name
                - date: Transaction date (datetime)
                - type: 'income' or 'expense'
        """
        # Clear existing items
        self._transaction_items.clear()
        while self.transactions_container.count():
            item = self.transactions_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not transactions:
            self.no_transactions_label = QLabel("No recent transactions")
            self.no_transactions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.no_transactions_label.setStyleSheet("color: #999999; padding: 30px;")
            self.transactions_container.addWidget(self.no_transactions_label)
            return

        # Add transaction items (limit to 10)
        for txn in transactions[:10]:
            item = RecentTransactionItem(
                transaction_id=txn.get('id', 0),
                description=txn.get('description', 'Unknown'),
                amount=Decimal(str(txn.get('amount', 0))),
                category=txn.get('category', 'Uncategorized'),
                date=txn.get('date', datetime.now()),
                is_expense=txn.get('type', 'expense') == 'expense'
            )
            item.clicked.connect(self.view_transaction_requested.emit)
            self.transactions_container.addWidget(item)
            self._transaction_items.append(item)

    def update_budget_progress(self, budgets: List[Dict[str, Any]]):
        """
        Update the budget progress overview.

        Args:
            budgets: List of budget dicts with keys:
                - category: Budget category name
                - spent: Amount spent
                - limit: Budget limit
                - color: Optional color code
        """
        # Clear existing items
        self._budget_items.clear()
        while self.budget_container.count():
            item = self.budget_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not budgets:
            self.no_budgets_label = QLabel("No budgets configured")
            self.no_budgets_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.no_budgets_label.setStyleSheet("color: #999999; padding: 20px;")
            self.budget_container.addWidget(self.no_budgets_label)
            return

        # Default colors for budgets
        default_colors = [
            "#4CAF50", "#2196F3", "#FF9800", "#E91E63",
            "#9C27B0", "#00BCD4", "#FFC107", "#795548"
        ]

        # Add budget items (show top 5)
        for i, budget in enumerate(budgets[:5]):
            color = budget.get('color', default_colors[i % len(default_colors)])
            item = BudgetProgressItem(
                category=budget.get('category', 'Unknown'),
                spent=Decimal(str(budget.get('spent', 0))),
                budget=Decimal(str(budget.get('limit', 0))),
                color=color
            )
            item.clicked.connect(self.view_budget_requested.emit)
            self.budget_container.addWidget(item)
            self._budget_items.append(item)

    def update_spending_chart(self, data: List[Dict[str, Any]]):
        """
        Update the spending by category pie chart.

        Args:
            data: List of dicts with 'label', 'value', and optional 'color'
        """
        self.pie_chart.set_data(data)

    def update_trend_chart(self, data: List[Dict[str, Any]]):
        """
        Update the monthly trend line chart.

        Args:
            data: List of dicts with 'label' (month) and 'value'
        """
        self.line_chart.set_data(data)

    def update_ai_insights(self, insights: List[Dict[str, Any]]):
        """
        Update AI insights.

        Args:
            insights: List of insight dicts with 'id', 'type', 'title', 'description'
        """
        self.ai_insights_widget.update_insights(insights)

    def set_sync_status(
        self,
        status: SyncStatus,
        last_sync: Optional[datetime] = None,
        pending_count: int = 0
    ):
        """Update the sync status indicator."""
        self.sync_indicator.set_status(status, last_sync, pending_count)

        # Also update the sync widget
        widget_status = SyncStatusWidget.Status[status.name]
        self.sync_widget.set_status(widget_status, last_sync, pending_count)

    def set_pie_chart_widget(self, widget: QWidget):
        """Replace the pie chart placeholder with an actual chart widget."""
        layout = self.pie_chart.layout()
        # Clear placeholder content
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        layout.addWidget(widget)

    def set_line_chart_widget(self, widget: QWidget):
        """Replace the line chart placeholder with an actual chart widget."""
        layout = self.line_chart.layout()
        # Clear placeholder content
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        layout.addWidget(widget)

    def refresh_greeting(self):
        """Refresh the greeting based on current time."""
        self.greeting_label.setText(self._get_greeting())
        self.date_label.setText(datetime.now().strftime("%A, %B %d, %Y"))

    def set_user_name(self, name: str):
        """Set the user's name in the greeting."""
        greeting = self._get_greeting()
        if name:
            self.greeting_label.setText(f"{greeting}, {name}")
        else:
            self.greeting_label.setText(greeting)

    def show_loading(self, loading: bool = True):
        """Show or hide loading state."""
        # Could add a loading overlay or skeleton screens
        pass

    def cleanup(self):
        """Clean up resources when page is hidden or destroyed."""
        self._stop_auto_refresh()
        self._save_settings()

    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        self.refresh_greeting()

        # Start auto-refresh if enabled
        if self.auto_refresh_btn.isChecked():
            self._start_auto_refresh()

    def hideEvent(self, event):
        """Handle hide event."""
        super().hideEvent(event)
        # Don't stop auto-refresh on hide, let it continue in background

    def closeEvent(self, event):
        """Handle close event."""
        self.cleanup()
        super().closeEvent(event)
