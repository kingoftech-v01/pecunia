"""
Dashboard Widgets Module

Provides specialized widgets for the dashboard page including:
- BalanceWidget: Total balance, income, expense display
- RecentTransactionsWidget: List of recent transactions
- BudgetProgressWidget: Active budget progress
- QuickActionsWidget: Quick action buttons
- SyncStatusWidget: Synchronization status indicator
- AIInsightsWidget: AI-powered recommendations
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QSizePolicy, QSpacerItem, QProgressBar,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QPoint, QSize, QMimeData
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen,
    QLinearGradient, QDrag, QPixmap
)
from typing import Optional, Dict, Any, List, Callable
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum


class WidgetSize(Enum):
    """Widget size presets for responsive layout."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class DraggableWidget(QFrame):
    """Base class for draggable dashboard widgets."""

    position_changed = pyqtSignal(str, int)  # widget_id, new_position

    def __init__(
        self,
        widget_id: str,
        title: str,
        draggable: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.widget_id = widget_id
        self._title = title
        self._draggable = draggable
        self._drag_start_position: Optional[QPoint] = None
        self._setup_base_style()

    def _setup_base_style(self):
        """Set up base styling for the widget."""
        self.setObjectName("dashboardWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame#dashboardWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
            QFrame#dashboardWidget:hover {
                border-color: #BDBDBD;
            }
        """)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation."""
        if self._draggable and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag operation."""
        if not self._draggable or self._drag_start_position is None:
            return super().mouseMoveEvent(event)

        if (event.pos() - self._drag_start_position).manhattanLength() < 10:
            return super().mouseMoveEvent(event)

        # Start drag operation
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.widget_id)
        drag.setMimeData(mime_data)

        # Create drag pixmap
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        self.render(pixmap)
        drag.setPixmap(pixmap.scaled(
            pixmap.size() * 0.8,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        drag.setHotSpot(event.pos())

        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self._drag_start_position = None
        super().mouseReleaseEvent(event)


class BalanceWidget(DraggableWidget):
    """
    Widget displaying financial balance overview.

    Shows total balance, monthly income, and monthly expenses
    with animated value updates.
    """

    navigate_to_accounts = pyqtSignal()
    navigate_to_income = pyqtSignal()
    navigate_to_expenses = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("balance", "Financial Overview", draggable=True, parent=parent)
        self._total_balance = Decimal("0.00")
        self._monthly_income = Decimal("0.00")
        self._monthly_expenses = Decimal("0.00")
        self._currency_symbol = "$"
        self._setup_ui()

    def _setup_ui(self):
        """Set up the balance widget UI."""
        self.setMinimumSize(300, 200)
        self.setMaximumHeight(250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Financial Overview")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Period indicator
        self.period_label = QLabel("This Month")
        self.period_label.setFont(QFont("Segoe UI", 10))
        self.period_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(self.period_label)

        layout.addLayout(header_layout)

        # Total Balance Section
        balance_frame = QFrame()
        balance_frame.setObjectName("balanceFrame")
        balance_frame.setStyleSheet("""
            QFrame#balanceFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1976D2, stop:1 #42A5F5);
                border-radius: 10px;
                padding: 15px;
            }
        """)

        balance_layout = QVBoxLayout(balance_frame)
        balance_layout.setContentsMargins(15, 12, 15, 12)
        balance_layout.setSpacing(5)

        balance_title = QLabel("Total Balance")
        balance_title.setFont(QFont("Segoe UI", 11))
        balance_title.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        balance_layout.addWidget(balance_title)

        self.balance_value_label = QLabel(f"{self._currency_symbol}0.00")
        self.balance_value_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.balance_value_label.setStyleSheet("color: #FFFFFF;")
        balance_layout.addWidget(self.balance_value_label)

        balance_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        balance_frame.mousePressEvent = lambda e: self.navigate_to_accounts.emit()

        layout.addWidget(balance_frame)

        # Income/Expense Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(15)

        # Income Card
        income_card = self._create_metric_card(
            "Income",
            "#4CAF50",
            is_income=True
        )
        income_card.mousePressEvent = lambda e: self.navigate_to_income.emit()
        metrics_layout.addWidget(income_card)

        # Expense Card
        expense_card = self._create_metric_card(
            "Expenses",
            "#F44336",
            is_income=False
        )
        expense_card.mousePressEvent = lambda e: self.navigate_to_expenses.emit()
        metrics_layout.addWidget(expense_card)

        layout.addLayout(metrics_layout)

    def _create_metric_card(
        self,
        title: str,
        color: str,
        is_income: bool
    ) -> QFrame:
        """Create a metric card for income/expense."""
        card = QFrame()
        card.setObjectName(f"{'income' if is_income else 'expense'}Card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame#{card.objectName()} {{
                background-color: #F5F5F5;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
            QFrame#{card.objectName()}:hover {{
                background-color: #EEEEEE;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)

        # Icon and title
        header = QHBoxLayout()
        icon = QLabel("+" if is_income else "-")
        icon.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        icon.setStyleSheet(f"color: {color};")
        header.addWidget(icon)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10))
        title_label.setStyleSheet("color: #666666;")
        header.addWidget(title_label)
        header.addStretch()

        card_layout.addLayout(header)

        # Value
        if is_income:
            self.income_value_label = QLabel(f"{self._currency_symbol}0.00")
            self.income_value_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            self.income_value_label.setStyleSheet(f"color: {color};")
            card_layout.addWidget(self.income_value_label)
        else:
            self.expense_value_label = QLabel(f"{self._currency_symbol}0.00")
            self.expense_value_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            self.expense_value_label.setStyleSheet(f"color: {color};")
            card_layout.addWidget(self.expense_value_label)

        return card

    def update_values(
        self,
        total_balance: Decimal,
        monthly_income: Decimal,
        monthly_expenses: Decimal
    ):
        """Update all displayed values."""
        self._total_balance = total_balance
        self._monthly_income = monthly_income
        self._monthly_expenses = monthly_expenses

        self.balance_value_label.setText(
            f"{self._currency_symbol}{total_balance:,.2f}"
        )
        self.income_value_label.setText(
            f"{self._currency_symbol}{monthly_income:,.2f}"
        )
        self.expense_value_label.setText(
            f"{self._currency_symbol}{monthly_expenses:,.2f}"
        )

    def set_currency(self, symbol: str):
        """Set the currency symbol."""
        self._currency_symbol = symbol
        self.update_values(
            self._total_balance,
            self._monthly_income,
            self._monthly_expenses
        )

    def set_period(self, period_text: str):
        """Set the period label text."""
        self.period_label.setText(period_text)


class RecentTransactionsWidget(DraggableWidget):
    """
    Widget displaying recent transactions.

    Shows the last 5 transactions with quick navigation.
    """

    view_all_clicked = pyqtSignal()
    transaction_clicked = pyqtSignal(int)  # transaction_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("recent_transactions", "Recent Transactions", draggable=True, parent=parent)
        self._transactions: List[Dict[str, Any]] = []
        self._transaction_widgets: List[QWidget] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the recent transactions UI."""
        self.setMinimumSize(320, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Recent Transactions")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        view_all_btn = QPushButton("View All")
        view_all_btn.setObjectName("linkButton")
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_all_btn.setStyleSheet("""
            QPushButton#linkButton {
                background-color: transparent;
                color: #1976D2;
                border: none;
                font-size: 12px;
                padding: 5px;
            }
            QPushButton#linkButton:hover {
                color: #1565C0;
                text-decoration: underline;
            }
        """)
        view_all_btn.clicked.connect(self.view_all_clicked.emit)
        header_layout.addWidget(view_all_btn)

        layout.addLayout(header_layout)

        # Transactions container
        self.transactions_container = QVBoxLayout()
        self.transactions_container.setSpacing(8)

        # Placeholder
        self.placeholder_label = QLabel("No recent transactions")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #999999; padding: 40px;")
        self.transactions_container.addWidget(self.placeholder_label)

        layout.addLayout(self.transactions_container)
        layout.addStretch()

    def update_transactions(self, transactions: List[Dict[str, Any]]):
        """
        Update the transactions list.

        Args:
            transactions: List of transaction dicts with:
                - id: Transaction ID
                - description: Description text
                - amount: Transaction amount
                - category: Category name
                - category_color: Optional category color
                - date: Transaction datetime
                - type: 'income' or 'expense'
        """
        self._transactions = transactions[:5]  # Limit to 5

        # Clear existing widgets
        for widget in self._transaction_widgets:
            widget.deleteLater()
        self._transaction_widgets.clear()

        # Remove placeholder if exists
        if self.placeholder_label:
            self.placeholder_label.hide()

        if not self._transactions:
            self.placeholder_label.show()
            return

        # Add transaction items
        for txn in self._transactions:
            item = self._create_transaction_item(txn)
            self.transactions_container.addWidget(item)
            self._transaction_widgets.append(item)

    def _create_transaction_item(self, txn: Dict[str, Any]) -> QFrame:
        """Create a transaction item widget."""
        item = QFrame()
        item.setObjectName("transactionItem")
        item.setCursor(Qt.CursorShape.PointingHandCursor)
        item.setStyleSheet("""
            QFrame#transactionItem {
                background-color: transparent;
                border-radius: 8px;
                padding: 8px;
            }
            QFrame#transactionItem:hover {
                background-color: #F5F5F5;
            }
        """)

        # Store transaction ID for click handling
        txn_id = txn.get('id', 0)
        item.mousePressEvent = lambda e: self.transaction_clicked.emit(txn_id)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Category indicator
        is_expense = txn.get('type', 'expense') == 'expense'
        indicator_color = txn.get('category_color', '#E57373' if is_expense else '#81C784')

        indicator = QFrame()
        indicator.setFixedSize(4, 40)
        indicator.setStyleSheet(f"""
            background-color: {indicator_color};
            border-radius: 2px;
        """)
        layout.addWidget(indicator)

        # Description and meta
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        desc_label = QLabel(txn.get('description', 'Unknown')[:30])
        desc_label.setFont(QFont("Segoe UI", 11))
        desc_label.setStyleSheet("color: #333333;")
        info_layout.addWidget(desc_label)

        txn_date = txn.get('date', datetime.now())
        if isinstance(txn_date, str):
            txn_date = datetime.fromisoformat(txn_date)
        meta_text = f"{txn.get('category', 'Uncategorized')} | {txn_date.strftime('%b %d')}"

        meta_label = QLabel(meta_text)
        meta_label.setFont(QFont("Segoe UI", 9))
        meta_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(meta_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Amount
        amount = Decimal(str(txn.get('amount', 0)))
        amount_str = f"-${amount:,.2f}" if is_expense else f"+${amount:,.2f}"
        amount_color = "#E57373" if is_expense else "#81C784"

        amount_label = QLabel(amount_str)
        amount_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        amount_label.setStyleSheet(f"color: {amount_color};")
        layout.addWidget(amount_label)

        return item


class BudgetProgressWidget(DraggableWidget):
    """
    Widget displaying active budget progress.

    Shows progress bars for budget categories with percentage indicators.
    """

    view_all_clicked = pyqtSignal()
    budget_clicked = pyqtSignal(str)  # category name

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("budget_progress", "Budget Progress", draggable=True, parent=parent)
        self._budgets: List[Dict[str, Any]] = []
        self._budget_widgets: List[QWidget] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the budget progress UI."""
        self.setMinimumSize(300, 250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Budget Progress")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        view_all_btn = QPushButton("Manage")
        view_all_btn.setObjectName("linkButton")
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_all_btn.setStyleSheet("""
            QPushButton#linkButton {
                background-color: transparent;
                color: #1976D2;
                border: none;
                font-size: 12px;
                padding: 5px;
            }
            QPushButton#linkButton:hover {
                color: #1565C0;
                text-decoration: underline;
            }
        """)
        view_all_btn.clicked.connect(self.view_all_clicked.emit)
        header_layout.addWidget(view_all_btn)

        layout.addLayout(header_layout)

        # Budget items container
        self.budget_container = QVBoxLayout()
        self.budget_container.setSpacing(10)

        # Placeholder
        self.placeholder_label = QLabel("No active budgets")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #999999; padding: 30px;")
        self.budget_container.addWidget(self.placeholder_label)

        layout.addLayout(self.budget_container)
        layout.addStretch()

    def update_budgets(self, budgets: List[Dict[str, Any]]):
        """
        Update the budget progress display.

        Args:
            budgets: List of budget dicts with:
                - category: Category name
                - spent: Amount spent
                - limit: Budget limit
                - color: Optional color code
        """
        self._budgets = budgets[:5]  # Limit to 5

        # Clear existing widgets
        for widget in self._budget_widgets:
            widget.deleteLater()
        self._budget_widgets.clear()

        if not self._budgets:
            self.placeholder_label.show()
            return

        self.placeholder_label.hide()

        # Default colors
        colors = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#00BCD4"]

        for i, budget in enumerate(self._budgets):
            color = budget.get('color', colors[i % len(colors)])
            item = self._create_budget_item(budget, color)
            self.budget_container.addWidget(item)
            self._budget_widgets.append(item)

    def _create_budget_item(self, budget: Dict[str, Any], color: str) -> QWidget:
        """Create a budget progress item."""
        item = QWidget()
        item.setCursor(Qt.CursorShape.PointingHandCursor)

        category = budget.get('category', 'Unknown')
        item.mousePressEvent = lambda e: self.budget_clicked.emit(category)

        layout = QVBoxLayout(item)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()

        name_label = QLabel(category)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        name_label.setStyleSheet("color: #333333;")
        header.addWidget(name_label)

        header.addStretch()

        spent = Decimal(str(budget.get('spent', 0)))
        limit = Decimal(str(budget.get('limit', 1)))
        percentage = float((spent / limit) * 100) if limit > 0 else 0

        # Status color
        if percentage >= 100:
            status_color = "#F44336"
        elif percentage >= 80:
            status_color = "#FF9800"
        else:
            status_color = "#666666"

        amount_text = f"${spent:,.0f} / ${limit:,.0f}"
        amount_label = QLabel(amount_text)
        amount_label.setFont(QFont("Segoe UI", 9))
        amount_label.setStyleSheet(f"color: {status_color};")
        header.addWidget(amount_label)

        layout.addLayout(header)

        # Progress bar
        progress = QProgressBar()
        progress.setMaximum(100)
        progress.setValue(min(int(percentage), 100))
        progress.setTextVisible(False)
        progress.setFixedHeight(6)

        # Dynamic color based on percentage
        if percentage >= 100:
            bar_color = "#F44336"
        elif percentage >= 80:
            bar_color = "#FF9800"
        else:
            bar_color = color

        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(progress)

        return item


class QuickActionsWidget(DraggableWidget):
    """
    Widget providing quick action buttons.

    Allows rapid access to common operations.
    """

    add_transaction_clicked = pyqtSignal()
    add_income_clicked = pyqtSignal()
    add_expense_clicked = pyqtSignal()
    view_reports_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("quick_actions", "Quick Actions", draggable=True, parent=parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the quick actions UI."""
        self.setMinimumSize(280, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        title_label = QLabel("Quick Actions")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333;")
        layout.addWidget(title_label)

        # Primary action - Add Transaction
        add_btn = self._create_action_button(
            "Add Transaction",
            "+",
            "#4CAF50",
            large=True
        )
        add_btn.clicked.connect(self.add_transaction_clicked.emit)
        layout.addWidget(add_btn)

        # Secondary actions grid
        grid = QGridLayout()
        grid.setSpacing(10)

        income_btn = self._create_action_button("Income", "+", "#2196F3")
        income_btn.clicked.connect(self.add_income_clicked.emit)
        grid.addWidget(income_btn, 0, 0)

        expense_btn = self._create_action_button("Expense", "-", "#FF5722")
        expense_btn.clicked.connect(self.add_expense_clicked.emit)
        grid.addWidget(expense_btn, 0, 1)

        reports_btn = self._create_action_button("Reports", "=", "#9C27B0")
        reports_btn.clicked.connect(self.view_reports_clicked.emit)
        grid.addWidget(reports_btn, 1, 0)

        export_btn = self._create_action_button("Export", ">", "#607D8B")
        export_btn.clicked.connect(self.export_clicked.emit)
        grid.addWidget(export_btn, 1, 1)

        layout.addLayout(grid)

    def _create_action_button(
        self,
        text: str,
        icon: str,
        color: str,
        large: bool = False
    ) -> QPushButton:
        """Create a styled action button."""
        btn = QPushButton(f"{icon}  {text}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 11 if large else 10))

        height = 50 if large else 40
        btn.setMinimumHeight(height)

        # Lighten/darken color helpers
        base_color = QColor(color)
        hover_color = base_color.lighter(115).name()
        pressed_color = base_color.darker(115).name()

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)

        return btn


class SyncStatusWidget(DraggableWidget):
    """
    Widget displaying synchronization status.

    Shows current sync state, last sync time, and pending items.
    """

    sync_now_clicked = pyqtSignal()
    view_conflicts_clicked = pyqtSignal()

    class Status(Enum):
        SYNCED = "synced"
        SYNCING = "syncing"
        OFFLINE = "offline"
        ERROR = "error"
        PENDING = "pending"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("sync_status", "Sync Status", draggable=True, parent=parent)
        self._status = self.Status.SYNCED
        self._last_sync: Optional[datetime] = None
        self._pending_count = 0
        self._error_message: Optional[str] = None
        self._setup_ui()
        self._start_animation_timer()

    def _setup_ui(self):
        """Set up the sync status UI."""
        self.setMinimumSize(250, 120)
        self.setMaximumHeight(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Header with status indicator
        header_layout = QHBoxLayout()

        # Status dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        header_layout.addWidget(self.status_dot)

        # Status text
        self.status_label = QLabel("Synced")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        header_layout.addWidget(self.status_label)

        header_layout.addStretch()

        # Sync button
        self.sync_btn = QPushButton("Sync Now")
        self.sync_btn.setObjectName("syncButton")
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setStyleSheet("""
            QPushButton#syncButton {
                background-color: transparent;
                color: #1976D2;
                border: 1px solid #1976D2;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton#syncButton:hover {
                background-color: #E3F2FD;
            }
            QPushButton#syncButton:disabled {
                color: #BDBDBD;
                border-color: #BDBDBD;
            }
        """)
        self.sync_btn.clicked.connect(self.sync_now_clicked.emit)
        header_layout.addWidget(self.sync_btn)

        layout.addLayout(header_layout)

        # Last sync time
        self.last_sync_label = QLabel("Last synced: Never")
        self.last_sync_label.setFont(QFont("Segoe UI", 9))
        self.last_sync_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.last_sync_label)

        # Pending items / Error message
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Segoe UI", 9))
        self.info_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.info_label)

        self._update_display()

    def _start_animation_timer(self):
        """Start timer for syncing animation."""
        self._animation_frame = 0
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate_syncing)

    def _animate_syncing(self):
        """Animate the syncing indicator."""
        if self._status == self.Status.SYNCING:
            dots = "." * ((self._animation_frame % 3) + 1)
            self.status_label.setText(f"Syncing{dots}")
            self._animation_frame += 1

    def set_status(
        self,
        status: 'SyncStatusWidget.Status',
        last_sync: Optional[datetime] = None,
        pending_count: int = 0,
        error_message: Optional[str] = None
    ):
        """Update the sync status."""
        self._status = status
        self._last_sync = last_sync
        self._pending_count = pending_count
        self._error_message = error_message

        if status == self.Status.SYNCING:
            self._animation_timer.start(500)
        else:
            self._animation_timer.stop()

        self._update_display()

    def _update_display(self):
        """Update the visual display."""
        status_config = {
            self.Status.SYNCED: ("#4CAF50", "Synced"),
            self.Status.SYNCING: ("#2196F3", "Syncing"),
            self.Status.OFFLINE: ("#9E9E9E", "Offline"),
            self.Status.ERROR: ("#F44336", "Sync Error"),
            self.Status.PENDING: ("#FF9800", "Changes Pending"),
        }

        color, text = status_config.get(self._status, ("#9E9E9E", "Unknown"))

        self.status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
        """)

        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

        # Update last sync time
        if self._last_sync:
            time_ago = self._format_time_ago(self._last_sync)
            self.last_sync_label.setText(f"Last synced: {time_ago}")
        else:
            self.last_sync_label.setText("Last synced: Never")

        # Update info label
        if self._status == self.Status.ERROR and self._error_message:
            self.info_label.setText(self._error_message)
            self.info_label.setStyleSheet("color: #F44336;")
        elif self._pending_count > 0:
            self.info_label.setText(f"{self._pending_count} changes pending sync")
            self.info_label.setStyleSheet("color: #FF9800;")
        else:
            self.info_label.setText("All data synchronized")
            self.info_label.setStyleSheet("color: #4CAF50;")

        # Update sync button state
        self.sync_btn.setEnabled(
            self._status not in [self.Status.SYNCING, self.Status.OFFLINE]
        )

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as human-readable time ago."""
        now = datetime.now()
        diff = now - dt

        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        else:
            days = int(seconds / 86400)
            return f"{days}d ago"


class AIInsightsWidget(DraggableWidget):
    """
    Widget displaying AI-powered financial insights.

    Shows recommendations, alerts, and tips based on spending patterns.
    """

    insight_clicked = pyqtSignal(str)  # insight_id
    refresh_insights_clicked = pyqtSignal()

    class InsightType(Enum):
        TIP = "tip"
        WARNING = "warning"
        ACHIEVEMENT = "achievement"
        SUGGESTION = "suggestion"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("ai_insights", "AI Insights", draggable=True, parent=parent)
        self._insights: List[Dict[str, Any]] = []
        self._insight_widgets: List[QWidget] = []
        self._loading = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the AI insights UI."""
        self.setMinimumSize(300, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()

        # AI icon and title
        icon_label = QLabel("*")
        icon_label.setFont(QFont("Segoe UI", 16))
        icon_label.setStyleSheet("color: #9C27B0;")
        header_layout.addWidget(icon_label)

        title_label = QLabel("AI Insights")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333333;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("refreshInsightsBtn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton#refreshInsightsBtn {
                background-color: transparent;
                color: #9C27B0;
                border: none;
                font-size: 11px;
                padding: 5px;
            }
            QPushButton#refreshInsightsBtn:hover {
                color: #7B1FA2;
                text-decoration: underline;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_insights_clicked.emit)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Insights container
        self.insights_container = QVBoxLayout()
        self.insights_container.setSpacing(10)

        # Placeholder/Loading
        self.placeholder_label = QLabel("Analyzing your finances...")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #999999; padding: 30px;")
        self.insights_container.addWidget(self.placeholder_label)

        layout.addLayout(self.insights_container)
        layout.addStretch()

    def set_loading(self, loading: bool):
        """Set loading state."""
        self._loading = loading
        if loading:
            self.placeholder_label.setText("Analyzing your finances...")
            self.placeholder_label.show()
        else:
            self.placeholder_label.hide()

    def update_insights(self, insights: List[Dict[str, Any]]):
        """
        Update the insights display.

        Args:
            insights: List of insight dicts with:
                - id: Insight ID
                - type: InsightType value ('tip', 'warning', etc.)
                - title: Short title
                - description: Detailed description
                - action: Optional action text
        """
        self._insights = insights[:4]  # Limit to 4

        # Clear existing widgets
        for widget in self._insight_widgets:
            widget.deleteLater()
        self._insight_widgets.clear()

        self._loading = False

        if not self._insights:
            self.placeholder_label.setText("No insights available")
            self.placeholder_label.show()
            return

        self.placeholder_label.hide()

        for insight in self._insights:
            item = self._create_insight_item(insight)
            self.insights_container.addWidget(item)
            self._insight_widgets.append(item)

    def _create_insight_item(self, insight: Dict[str, Any]) -> QFrame:
        """Create an insight item widget."""
        item = QFrame()
        item.setObjectName("insightItem")
        item.setCursor(Qt.CursorShape.PointingHandCursor)

        # Type-based styling
        insight_type = insight.get('type', 'tip')
        type_config = {
            'tip': ("#E3F2FD", "#1976D2", "i"),
            'warning': ("#FFF3E0", "#F57C00", "!"),
            'achievement': ("#E8F5E9", "#4CAF50", "*"),
            'suggestion': ("#F3E5F5", "#9C27B0", ">"),
        }

        bg_color, accent_color, icon = type_config.get(
            insight_type, ("#F5F5F5", "#666666", "?")
        )

        item.setStyleSheet(f"""
            QFrame#insightItem {{
                background-color: {bg_color};
                border-radius: 8px;
                border-left: 3px solid {accent_color};
            }}
            QFrame#insightItem:hover {{
                background-color: {QColor(bg_color).darker(105).name()};
            }}
        """)

        insight_id = insight.get('id', '')
        item.mousePressEvent = lambda e: self.insight_clicked.emit(insight_id)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        icon_label.setStyleSheet(f"color: {accent_color};")
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)

        title_label = QLabel(insight.get('title', 'Insight'))
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        title_label.setStyleSheet(f"color: {accent_color};")
        title_label.setWordWrap(True)
        content_layout.addWidget(title_label)

        desc_label = QLabel(insight.get('description', '')[:100])
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #666666;")
        desc_label.setWordWrap(True)
        content_layout.addWidget(desc_label)

        layout.addLayout(content_layout)

        return item

    def add_sample_insights(self):
        """Add sample insights for demonstration."""
        sample_insights = [
            {
                'id': '1',
                'type': 'tip',
                'title': 'Spending Pattern Detected',
                'description': 'You spend 30% more on weekends. Consider setting a weekend budget.'
            },
            {
                'id': '2',
                'type': 'warning',
                'title': 'Budget Alert',
                'description': 'Food & Dining is at 85% of monthly budget with 10 days remaining.'
            },
            {
                'id': '3',
                'type': 'achievement',
                'title': 'Savings Goal Progress',
                'description': 'Great job! You saved $200 more than last month.'
            },
            {
                'id': '4',
                'type': 'suggestion',
                'title': 'Subscription Review',
                'description': 'You have 5 recurring subscriptions. Review for potential savings.'
            }
        ]
        self.update_insights(sample_insights)


class DashboardWidgetContainer(QWidget):
    """
    Container for dashboard widgets with drag-and-drop support.

    Manages widget layout and allows rearrangement.
    """

    layout_changed = pyqtSignal(list)  # List of widget IDs in order

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._widgets: Dict[str, DraggableWidget] = {}
        self._widget_order: List[str] = []
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the container UI."""
        self.setStyleSheet("background-color: transparent;")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(20)

    def add_widget(
        self,
        widget: DraggableWidget,
        position: Optional[int] = None
    ):
        """Add a widget to the container."""
        self._widgets[widget.widget_id] = widget

        if position is not None and position < len(self._widget_order):
            self._widget_order.insert(position, widget.widget_id)
            self.main_layout.insertWidget(position, widget)
        else:
            self._widget_order.append(widget.widget_id)
            self.main_layout.addWidget(widget)

    def remove_widget(self, widget_id: str):
        """Remove a widget from the container."""
        if widget_id in self._widgets:
            widget = self._widgets.pop(widget_id)
            self._widget_order.remove(widget_id)
            self.main_layout.removeWidget(widget)
            widget.deleteLater()

    def get_widget(self, widget_id: str) -> Optional[DraggableWidget]:
        """Get a widget by ID."""
        return self._widgets.get(widget_id)

    def get_widget_order(self) -> List[str]:
        """Get the current widget order."""
        return self._widget_order.copy()

    def set_widget_order(self, order: List[str]):
        """Set the widget order."""
        # Remove all widgets from layout
        for widget_id in self._widget_order:
            widget = self._widgets.get(widget_id)
            if widget:
                self.main_layout.removeWidget(widget)

        # Re-add in new order
        self._widget_order = []
        for widget_id in order:
            widget = self._widgets.get(widget_id)
            if widget:
                self._widget_order.append(widget_id)
                self.main_layout.addWidget(widget)

    def dragEnterEvent(self, event):
        """Handle drag enter."""
        if event.mimeData().hasText():
            widget_id = event.mimeData().text()
            if widget_id in self._widgets:
                event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle drop."""
        widget_id = event.mimeData().text()
        if widget_id not in self._widgets:
            return

        # Calculate new position based on drop location
        drop_y = event.position().y()
        new_position = 0

        for i, wid in enumerate(self._widget_order):
            widget = self._widgets.get(wid)
            if widget:
                widget_center = widget.geometry().center().y()
                if drop_y > widget_center:
                    new_position = i + 1

        # Move widget to new position
        if widget_id in self._widget_order:
            old_position = self._widget_order.index(widget_id)
            if old_position != new_position:
                self._widget_order.remove(widget_id)
                if new_position > old_position:
                    new_position -= 1
                self._widget_order.insert(new_position, widget_id)

                # Update layout
                self.set_widget_order(self._widget_order)
                self.layout_changed.emit(self._widget_order)

        event.acceptProposedAction()
