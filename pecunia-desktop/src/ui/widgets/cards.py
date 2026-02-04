"""
Card widgets for Pecunia Desktop.

Provides card-based UI components for displaying financial data
including stats, transactions, and budgets.
"""

from typing import Optional, List
from enum import Enum
from decimal import Decimal

from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal,
    QSize, QRectF
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsDropShadowEffect,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush,
    QPainterPath, QLinearGradient
)

from ..styles.theme import get_theme_manager, ThemeManager


class Card(QFrame):
    """
    Base card widget with consistent styling.

    Provides a styled container with optional shadow, hover effects,
    and click handling.

    Usage:
        card = Card(title="My Card")
        card.add_content(my_widget)
    """

    clicked = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None,
        clickable: bool = False,
        shadow: bool = True,
        padding: int = 16
    ):
        """
        Initialize card widget.

        Args:
            parent: Parent widget
            title: Optional card title
            clickable: Whether card is clickable
            shadow: Whether to show drop shadow
            padding: Content padding in pixels
        """
        super().__init__(parent)

        self._clickable = clickable
        self._padding = padding

        self._setup_style(shadow)
        self._setup_layout(title)

        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_style(self, shadow: bool) -> None:
        """Setup card styling."""
        theme = get_theme_manager()
        palette = theme.current_palette

        self.setObjectName("cardWidget")
        self.setStyleSheet(f"""
            #cardWidget {{
                background-color: {palette.surface};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}
            #cardWidget:hover {{
                border-color: {palette.primary if self._clickable else palette.border};
            }}
        """)

        if shadow:
            shadow_effect = QGraphicsDropShadowEffect(self)
            shadow_effect.setBlurRadius(16)
            shadow_effect.setXOffset(0)
            shadow_effect.setYOffset(2)
            shadow_effect.setColor(QColor(0, 0, 0, 25))
            self.setGraphicsEffect(shadow_effect)

        # Connect theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode) -> None:
        """Handle theme change."""
        theme = get_theme_manager()
        palette = theme.current_palette
        self.setStyleSheet(f"""
            #cardWidget {{
                background-color: {palette.surface};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}
            #cardWidget:hover {{
                border-color: {palette.primary if self._clickable else palette.border};
            }}
        """)

    def _setup_layout(self, title: Optional[str]) -> None:
        """Setup card layout."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            self._padding, self._padding,
            self._padding, self._padding
        )
        self._layout.setSpacing(12)

        if title:
            self._title_label = QLabel(title)
            theme = get_theme_manager()
            self._title_label.setStyleSheet(f"""
                font-size: 16px;
                font-weight: 600;
                color: {theme.current_palette.text_primary};
            """)
            self._layout.addWidget(self._title_label)

        # Content area
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(8)
        self._layout.addLayout(self._content_layout)

    def set_title(self, title: str) -> None:
        """Set or update the card title."""
        if hasattr(self, '_title_label'):
            self._title_label.setText(title)

    def add_content(self, widget: QWidget) -> None:
        """Add a widget to the card content area."""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        """Add a layout to the card content area."""
        self._content_layout.addLayout(layout)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press for clickable cards."""
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class TrendDirection(Enum):
    """Trend direction for stat cards."""
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class StatCard(Card):
    """
    Statistics card with number, label, and trend indicator.

    Displays a key metric with optional trend comparison.

    Usage:
        stat = StatCard(
            title="Total Balance",
            value=15234.56,
            prefix="$",
            trend_value=5.2,
            trend_direction=TrendDirection.UP,
            trend_label="vs last month"
        )
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
        value: float = 0,
        prefix: str = "",
        suffix: str = "",
        trend_value: Optional[float] = None,
        trend_direction: TrendDirection = TrendDirection.NEUTRAL,
        trend_label: str = "",
        decimal_places: int = 2,
        compact: bool = False
    ):
        """
        Initialize stat card.

        Args:
            parent: Parent widget
            title: Card title/label
            value: The main numeric value
            prefix: Value prefix (e.g., "$")
            suffix: Value suffix (e.g., "%")
            trend_value: Trend percentage change
            trend_direction: Up, down, or neutral
            trend_label: Additional trend context
            decimal_places: Number of decimal places
            compact: Whether to use compact layout
        """
        super().__init__(parent, shadow=not compact, padding=16 if not compact else 12)

        self._value = value
        self._prefix = prefix
        self._suffix = suffix
        self._decimal_places = decimal_places
        self._trend_value = trend_value
        self._trend_direction = trend_direction

        self._setup_stat_ui(title, trend_label, compact)
        self._update_display()

    def _setup_stat_ui(self, title: str, trend_label: str, compact: bool) -> None:
        """Setup stat card UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Title
        self._stat_title = QLabel(title)
        self._stat_title.setStyleSheet(f"""
            font-size: {'12px' if compact else '14px'};
            color: {palette.text_secondary};
            font-weight: 500;
        """)
        self._content_layout.addWidget(self._stat_title)

        # Value row
        value_layout = QHBoxLayout()
        value_layout.setSpacing(8)

        self._value_label = QLabel()
        self._value_label.setStyleSheet(f"""
            font-size: {'24px' if not compact else '20px'};
            font-weight: 700;
            color: {palette.text_primary};
        """)
        value_layout.addWidget(self._value_label)

        value_layout.addStretch()

        # Trend indicator
        if self._trend_value is not None:
            self._trend_widget = QWidget()
            trend_layout = QHBoxLayout(self._trend_widget)
            trend_layout.setContentsMargins(0, 0, 0, 0)
            trend_layout.setSpacing(4)

            # Arrow
            self._trend_arrow = QLabel()
            self._trend_arrow.setFixedSize(16, 16)

            # Percentage
            self._trend_percent = QLabel()
            self._trend_percent.setStyleSheet("font-size: 12px; font-weight: 500;")

            trend_layout.addWidget(self._trend_arrow)
            trend_layout.addWidget(self._trend_percent)

            value_layout.addWidget(self._trend_widget)

        self._content_layout.addLayout(value_layout)

        # Trend label
        if trend_label:
            self._trend_label = QLabel(trend_label)
            self._trend_label.setStyleSheet(f"""
                font-size: 11px;
                color: {palette.text_secondary};
            """)
            self._content_layout.addWidget(self._trend_label)

    def _update_display(self) -> None:
        """Update the display values."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Format value
        if self._decimal_places == 0:
            formatted = f"{self._prefix}{int(self._value):,}{self._suffix}"
        else:
            formatted = f"{self._prefix}{self._value:,.{self._decimal_places}f}{self._suffix}"

        self._value_label.setText(formatted)

        # Update trend if present
        if hasattr(self, '_trend_arrow') and self._trend_value is not None:
            if self._trend_direction == TrendDirection.UP:
                color = palette.positive
                arrow = "\u2191"  # Up arrow
            elif self._trend_direction == TrendDirection.DOWN:
                color = palette.negative
                arrow = "\u2193"  # Down arrow
            else:
                color = palette.neutral
                arrow = "\u2192"  # Right arrow

            self._trend_arrow.setText(arrow)
            self._trend_arrow.setStyleSheet(f"""
                color: {color};
                font-size: 14px;
                font-weight: bold;
            """)

            self._trend_percent.setText(f"{abs(self._trend_value):.1f}%")
            self._trend_percent.setStyleSheet(f"""
                color: {color};
                font-size: 12px;
                font-weight: 500;
            """)

    def set_value(
        self,
        value: float,
        trend_value: Optional[float] = None,
        trend_direction: Optional[TrendDirection] = None
    ) -> None:
        """Update the stat value and optionally the trend."""
        self._value = value
        if trend_value is not None:
            self._trend_value = trend_value
        if trend_direction is not None:
            self._trend_direction = trend_direction
        self._update_display()


class TransactionCard(Card):
    """
    Transaction preview card.

    Displays a transaction summary with category, amount, and date.

    Usage:
        txn = TransactionCard(
            description="Coffee Shop",
            category="Food & Drink",
            amount=-4.50,
            date="Today",
            category_color="#4CAF50"
        )
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        description: str = "",
        category: str = "",
        amount: float = 0,
        date: str = "",
        category_color: Optional[str] = None,
        account_name: Optional[str] = None,
        clickable: bool = True
    ):
        """
        Initialize transaction card.

        Args:
            parent: Parent widget
            description: Transaction description
            category: Category name
            amount: Transaction amount (negative for expenses)
            date: Date string
            category_color: Color for category indicator
            account_name: Optional account name
            clickable: Whether card is clickable
        """
        super().__init__(parent, clickable=clickable, shadow=False, padding=12)

        self._amount = amount
        self._setup_transaction_ui(
            description, category, date,
            category_color, account_name
        )

    def _setup_transaction_ui(
        self,
        description: str,
        category: str,
        date: str,
        category_color: Optional[str],
        account_name: Optional[str]
    ) -> None:
        """Setup transaction card UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Main row
        main_layout = QHBoxLayout()
        main_layout.setSpacing(12)

        # Category color indicator
        if category_color:
            indicator = QFrame()
            indicator.setFixedSize(4, 40)
            indicator.setStyleSheet(f"""
                background-color: {category_color};
                border-radius: 2px;
            """)
            main_layout.addWidget(indicator)

        # Left side - description and category
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {palette.text_primary};
        """)
        left_layout.addWidget(desc_label)

        # Category and date row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        cat_label = QLabel(category)
        cat_label.setStyleSheet(f"""
            font-size: 12px;
            color: {palette.text_secondary};
        """)
        meta_layout.addWidget(cat_label)

        if account_name:
            sep = QLabel("\u2022")  # Bullet
            sep.setStyleSheet(f"color: {palette.text_disabled};")
            meta_layout.addWidget(sep)

            account_label = QLabel(account_name)
            account_label.setStyleSheet(f"""
                font-size: 12px;
                color: {palette.text_secondary};
            """)
            meta_layout.addWidget(account_label)

        meta_layout.addStretch()
        left_layout.addLayout(meta_layout)

        main_layout.addLayout(left_layout, 1)

        # Right side - amount and date
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.setSpacing(2)

        # Amount with color
        amount_color = palette.positive if self._amount >= 0 else palette.negative
        amount_prefix = "+" if self._amount > 0 else ""
        amount_label = QLabel(f"{amount_prefix}${abs(self._amount):,.2f}")
        amount_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {amount_color};
        """)
        amount_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(amount_label)

        date_label = QLabel(date)
        date_label.setStyleSheet(f"""
            font-size: 12px;
            color: {palette.text_secondary};
        """)
        date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(date_label)

        main_layout.addLayout(right_layout)

        self._content_layout.addLayout(main_layout)


class BudgetCard(Card):
    """
    Budget card with progress indicator.

    Displays budget information with visual progress bar.

    Usage:
        budget = BudgetCard(
            name="Groceries",
            spent=350.00,
            limit=500.00,
            category_color="#4CAF50",
            period="This Month"
        )
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        name: str = "",
        spent: float = 0,
        limit: float = 0,
        category_color: Optional[str] = None,
        period: str = "",
        clickable: bool = True
    ):
        """
        Initialize budget card.

        Args:
            parent: Parent widget
            name: Budget name
            spent: Amount spent
            limit: Budget limit
            category_color: Color for progress bar
            period: Budget period text
            clickable: Whether card is clickable
        """
        super().__init__(parent, clickable=clickable, shadow=True, padding=16)

        self._spent = spent
        self._limit = limit
        self._category_color = category_color

        self._setup_budget_ui(name, period)
        self._update_progress()

    def _setup_budget_ui(self, name: str, period: str) -> None:
        """Setup budget card UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Header row
        header = QHBoxLayout()

        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {palette.text_primary};
        """)
        header.addWidget(name_label)

        header.addStretch()

        if period:
            period_label = QLabel(period)
            period_label.setStyleSheet(f"""
                font-size: 12px;
                color: {palette.text_secondary};
            """)
            header.addWidget(period_label)

        self._content_layout.addLayout(header)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)

        color = self._category_color or palette.primary
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {palette.border};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        self._content_layout.addWidget(self._progress_bar)

        # Footer row
        footer = QHBoxLayout()

        self._spent_label = QLabel()
        self._spent_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {palette.text_primary};
        """)
        footer.addWidget(self._spent_label)

        footer.addStretch()

        self._remaining_label = QLabel()
        self._remaining_label.setStyleSheet(f"""
            font-size: 13px;
            color: {palette.text_secondary};
        """)
        footer.addWidget(self._remaining_label)

        self._content_layout.addLayout(footer)

    def _update_progress(self) -> None:
        """Update progress display."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Calculate percentage
        if self._limit > 0:
            percentage = min((self._spent / self._limit) * 100, 100)
        else:
            percentage = 0

        self._progress_bar.setValue(int(percentage))

        # Update spent label
        self._spent_label.setText(f"${self._spent:,.2f} of ${self._limit:,.2f}")

        # Update remaining
        remaining = self._limit - self._spent
        if remaining >= 0:
            self._remaining_label.setText(f"${remaining:,.2f} remaining")
            self._remaining_label.setStyleSheet(f"""
                font-size: 13px;
                color: {palette.text_secondary};
            """)
        else:
            self._remaining_label.setText(f"${abs(remaining):,.2f} over budget")
            self._remaining_label.setStyleSheet(f"""
                font-size: 13px;
                color: {palette.error};
                font-weight: 500;
            """)

        # Update progress bar color if over budget
        if percentage >= 100:
            self._progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {palette.border};
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {palette.error};
                    border-radius: 4px;
                }}
            """)
        elif percentage >= 80:
            self._progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {palette.border};
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {palette.warning};
                    border-radius: 4px;
                }}
            """)

    def set_values(self, spent: float, limit: float) -> None:
        """Update spent and limit values."""
        self._spent = spent
        self._limit = limit
        self._update_progress()


class AccountCard(Card):
    """
    Account summary card.

    Displays account information with balance and type.

    Usage:
        account = AccountCard(
            name="Checking Account",
            account_type="Checking",
            balance=5432.10,
            institution="Bank of America",
            last_updated="2 hours ago"
        )
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        name: str = "",
        account_type: str = "",
        balance: float = 0,
        institution: Optional[str] = None,
        last_updated: Optional[str] = None,
        color: Optional[str] = None,
        clickable: bool = True
    ):
        """
        Initialize account card.

        Args:
            parent: Parent widget
            name: Account name
            account_type: Type of account
            balance: Current balance
            institution: Bank/institution name
            last_updated: Last sync time
            color: Accent color
            clickable: Whether card is clickable
        """
        super().__init__(parent, clickable=clickable, shadow=True, padding=16)

        self._balance = balance
        self._color = color

        self._setup_account_ui(name, account_type, institution, last_updated)

    def _setup_account_ui(
        self,
        name: str,
        account_type: str,
        institution: Optional[str],
        last_updated: Optional[str]
    ) -> None:
        """Setup account card UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Top row with icon and name
        header = QHBoxLayout()
        header.setSpacing(12)

        # Account icon/color indicator
        color = self._color or palette.primary
        icon = QLabel()
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"""
            background-color: {color}20;
            color: {color};
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
        """)
        # Use first letter of name
        icon.setText(name[0].upper() if name else "A")
        header.addWidget(icon)

        # Name and type
        name_layout = QVBoxLayout()
        name_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {palette.text_primary};
        """)
        name_layout.addWidget(name_label)

        type_label = QLabel(account_type)
        type_label.setStyleSheet(f"""
            font-size: 12px;
            color: {palette.text_secondary};
        """)
        name_layout.addWidget(type_label)

        header.addLayout(name_layout, 1)

        self._content_layout.addLayout(header)
        self._content_layout.addSpacing(8)

        # Balance
        balance_color = palette.positive if self._balance >= 0 else palette.negative
        balance_label = QLabel(f"${abs(self._balance):,.2f}")
        balance_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {balance_color};
        """)
        self._content_layout.addWidget(balance_label)

        # Footer with institution and last updated
        if institution or last_updated:
            footer = QHBoxLayout()

            if institution:
                inst_label = QLabel(institution)
                inst_label.setStyleSheet(f"""
                    font-size: 12px;
                    color: {palette.text_secondary};
                """)
                footer.addWidget(inst_label)

            footer.addStretch()

            if last_updated:
                updated_label = QLabel(f"Updated {last_updated}")
                updated_label.setStyleSheet(f"""
                    font-size: 11px;
                    color: {palette.text_disabled};
                """)
                footer.addWidget(updated_label)

            self._content_layout.addLayout(footer)


class SummaryCard(Card):
    """
    Financial summary card with income/expense breakdown.

    Displays a summary of income and expenses for a period.

    Usage:
        summary = SummaryCard(
            period="This Month",
            income=5000.00,
            expenses=3500.00
        )
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        period: str = "",
        income: float = 0,
        expenses: float = 0
    ):
        """
        Initialize summary card.

        Args:
            parent: Parent widget
            period: Period label
            income: Total income
            expenses: Total expenses
        """
        super().__init__(parent, title=period, shadow=True, padding=16)

        self._income = income
        self._expenses = expenses

        self._setup_summary_ui()

    def _setup_summary_ui(self) -> None:
        """Setup summary card UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        # Income row
        income_row = QHBoxLayout()
        income_label = QLabel("Income")
        income_label.setStyleSheet(f"color: {palette.text_secondary};")
        income_row.addWidget(income_label)
        income_row.addStretch()
        income_value = QLabel(f"+${self._income:,.2f}")
        income_value.setStyleSheet(f"""
            font-weight: 600;
            color: {palette.positive};
        """)
        income_row.addWidget(income_value)
        self._content_layout.addLayout(income_row)

        # Expenses row
        expense_row = QHBoxLayout()
        expense_label = QLabel("Expenses")
        expense_label.setStyleSheet(f"color: {palette.text_secondary};")
        expense_row.addWidget(expense_label)
        expense_row.addStretch()
        expense_value = QLabel(f"-${self._expenses:,.2f}")
        expense_value.setStyleSheet(f"""
            font-weight: 600;
            color: {palette.negative};
        """)
        expense_row.addWidget(expense_value)
        self._content_layout.addLayout(expense_row)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"background-color: {palette.divider};")
        divider.setFixedHeight(1)
        self._content_layout.addWidget(divider)

        # Net row
        net = self._income - self._expenses
        net_color = palette.positive if net >= 0 else palette.negative
        net_prefix = "+" if net >= 0 else "-"

        net_row = QHBoxLayout()
        net_label = QLabel("Net")
        net_label.setStyleSheet(f"""
            font-weight: 600;
            color: {palette.text_primary};
        """)
        net_row.addWidget(net_label)
        net_row.addStretch()
        net_value = QLabel(f"{net_prefix}${abs(net):,.2f}")
        net_value.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {net_color};
        """)
        net_row.addWidget(net_value)
        self._content_layout.addLayout(net_row)
