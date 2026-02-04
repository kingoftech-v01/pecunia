"""
Progress Chart Widget Module

Provides ProgressChart widget for displaying budget progress and targets.
Features: target line, color zones (safe/warning/danger), animations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QToolTip, QScrollArea, QFrame
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPointF, QRectF, QLineF,
    QPropertyAnimation, QEasingCurve, Property, QTimer
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient
)

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from .charts import (
    BaseChart, ChartConfig, ChartDataPoint, ColorScheme,
    AnimationType, LegendPosition, ChartAnimationMixin,
    LIGHT_SCHEME, DARK_SCHEME, get_category_color
)


class ProgressStyle(Enum):
    """Progress bar style options."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    CIRCULAR = "circular"
    SEMICIRCLE = "semicircle"


@dataclass
class ProgressZone:
    """Define a color zone for progress visualization."""
    threshold: float  # Percentage threshold (0-100)
    color: str  # Zone color


@dataclass
class ProgressChartConfig:
    """Configuration for progress charts."""
    style: ProgressStyle = ProgressStyle.HORIZONTAL
    bar_height: int = 16
    bar_spacing: int = 20
    show_percentage: bool = True
    show_amounts: bool = True
    show_target_line: bool = True
    animated: bool = True
    animation_duration: int = 800
    rounded_corners: bool = True
    corner_radius: int = 8
    gradient_fill: bool = True

    # Color zones (percentages)
    safe_threshold: float = 70.0
    warning_threshold: float = 90.0

    # Zone colors (will use scheme colors if not specified)
    safe_color: Optional[str] = None
    warning_color: Optional[str] = None
    danger_color: Optional[str] = None


@dataclass
class BudgetItem:
    """Budget progress item data."""
    category: str
    spent: float
    budget: float
    color: Optional[str] = None
    icon: Optional[str] = None

    @property
    def percentage(self) -> float:
        """Calculate spent percentage."""
        if self.budget <= 0:
            return 0.0
        return min(100.0, (self.spent / self.budget) * 100)

    @property
    def remaining(self) -> float:
        """Calculate remaining budget."""
        return max(0, self.budget - self.spent)

    @property
    def is_over_budget(self) -> bool:
        """Check if over budget."""
        return self.spent > self.budget


class ProgressBarWidget(QWidget, ChartAnimationMixin):
    """
    Individual progress bar widget with animations and color zones.
    """

    clicked = pyqtSignal(str, float, float)  # category, spent, budget

    def __init__(
        self,
        item: BudgetItem,
        scheme: ColorScheme,
        config: Optional[ProgressChartConfig] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._item = item
        self._scheme = scheme
        self._config = config or ProgressChartConfig()
        self._animation_progress = 0.0
        self._hover = False

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the progress bar UI."""
        self.setMinimumHeight(60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(5)

        # Header row (category + amounts)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Category label
        self.category_label = QLabel(self._item.category)
        self.category_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.category_label.setStyleSheet(f"color: {self._scheme.text};")
        header_layout.addWidget(self.category_label)

        header_layout.addStretch()

        # Amount labels
        if self._config.show_amounts:
            # Spent amount
            spent_color = self._get_zone_color(self._item.percentage)
            if self._item.is_over_budget:
                spent_text = f"${self._item.spent:,.2f}"
                spent_style = f"color: {self._scheme.negative}; font-weight: bold;"
            else:
                spent_text = f"${self._item.spent:,.2f}"
                spent_style = f"color: {self._scheme.text};"

            self.spent_label = QLabel(spent_text)
            self.spent_label.setFont(QFont("Segoe UI", 10))
            self.spent_label.setStyleSheet(spent_style)
            header_layout.addWidget(self.spent_label)

            # Separator
            sep = QLabel("/")
            sep.setFont(QFont("Segoe UI", 10))
            sep.setStyleSheet(f"color: {self._scheme.axis};")
            header_layout.addWidget(sep)

            # Budget amount
            self.budget_label = QLabel(f"${self._item.budget:,.2f}")
            self.budget_label.setFont(QFont("Segoe UI", 10))
            self.budget_label.setStyleSheet(f"color: {self._scheme.text};")
            header_layout.addWidget(self.budget_label)

        # Percentage
        if self._config.show_percentage:
            pct = self._item.percentage
            if pct > 100:
                pct_style = f"color: {self._scheme.negative}; font-weight: bold;"
            elif pct >= self._config.warning_threshold:
                pct_style = f"color: {self._config.warning_color or self._scheme.warning}; font-weight: bold;"
            else:
                pct_style = f"color: {self._scheme.text};"

            self.percentage_label = QLabel(f"{pct:.0f}%")
            self.percentage_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.percentage_label.setStyleSheet(pct_style)
            self.percentage_label.setFixedWidth(50)
            self.percentage_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            header_layout.addWidget(self.percentage_label)

        layout.addLayout(header_layout)

        # Progress bar canvas
        self.bar_canvas = ProgressBarCanvas(
            self._item, self._scheme, self._config, self
        )
        self.bar_canvas.setFixedHeight(self._config.bar_height)
        layout.addWidget(self.bar_canvas)

        # Remaining info (optional)
        if self._item.is_over_budget:
            over_by = self._item.spent - self._item.budget
            remaining_label = QLabel(f"Over budget by ${over_by:,.2f}")
            remaining_label.setFont(QFont("Segoe UI", 9))
            remaining_label.setStyleSheet(f"color: {self._scheme.negative};")
            layout.addWidget(remaining_label)
        elif self._item.remaining > 0:
            remaining_label = QLabel(f"${self._item.remaining:,.2f} remaining")
            remaining_label.setFont(QFont("Segoe UI", 9))
            remaining_label.setStyleSheet(f"color: {self._scheme.positive};")
            layout.addWidget(remaining_label)

    def _get_zone_color(self, percentage: float) -> str:
        """Get color for current percentage zone."""
        if percentage > 100:
            return self._config.danger_color or self._scheme.negative
        elif percentage >= self._config.warning_threshold:
            return self._config.warning_color or self._scheme.warning
        else:
            return self._config.safe_color or self._scheme.positive

    def start_animation(self):
        """Start the progress animation."""
        self.bar_canvas._animation_progress = 0.0
        self.bar_canvas.start_animation(
            AnimationType.GROW,
            self._config.animation_duration
        )

    def enterEvent(self, event):
        """Handle mouse enter."""
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        """Handle click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(
                self._item.category,
                self._item.spent,
                self._item.budget
            )


class ProgressBarCanvas(QWidget, ChartAnimationMixin):
    """Canvas for drawing the actual progress bar."""

    def __init__(
        self,
        item: BudgetItem,
        scheme: ColorScheme,
        config: ProgressChartConfig,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._item = item
        self._scheme = scheme
        self._config = config
        self._animation_progress = 1.0

    def paintEvent(self, event):
        """Paint the progress bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        radius = self._config.corner_radius if self._config.rounded_corners else 0

        # Background track
        bg_color = QColor(self._scheme.grid)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, width, height), radius, radius)

        # Calculate progress width
        percentage = min(self._item.percentage, 100) * self._animation_progress
        progress_width = width * (percentage / 100)

        if progress_width > 0:
            # Get zone color
            color = QColor(self._get_zone_color(self._item.percentage * self._animation_progress))

            # Draw progress fill
            if self._config.gradient_fill:
                gradient = QLinearGradient(0, 0, progress_width, 0)
                gradient.setColorAt(0, color.lighter(110))
                gradient.setColorAt(1, color)
                painter.setBrush(QBrush(gradient))
            else:
                painter.setBrush(QBrush(color))

            progress_rect = QRectF(0, 0, progress_width, height)
            painter.drawRoundedRect(progress_rect, radius, radius)

        # Draw over-budget indicator
        if self._item.is_over_budget and self._animation_progress >= 1.0:
            over_percentage = min((self._item.spent - self._item.budget) / self._item.budget, 0.3)
            stripe_width = width * over_percentage

            # Draw striped pattern
            painter.setClipRect(QRectF(width, 0, stripe_width, height))
            painter.setBrush(QBrush(QColor(self._scheme.negative)))
            painter.setOpacity(0.6)

            stripe_size = 8
            for i in range(int(width), int(width + stripe_width + stripe_size * 2), stripe_size * 2):
                path = QPainterPath()
                path.moveTo(i, 0)
                path.lineTo(i + stripe_size, 0)
                path.lineTo(i - height, height)
                path.lineTo(i - height - stripe_size, height)
                path.closeSubpath()
                painter.drawPath(path)

            painter.setOpacity(1.0)
            painter.setClipping(False)

        # Draw target line at 100%
        if self._config.show_target_line and self._item.percentage < 100:
            target_x = width
            painter.setPen(QPen(QColor(self._scheme.axis), 2, Qt.PenStyle.DashLine))
            painter.drawLine(QLineF(target_x, 2, target_x, height - 2))

    def _get_zone_color(self, percentage: float) -> str:
        """Get color for percentage zone."""
        if percentage > 100:
            return self._config.danger_color or self._scheme.negative
        elif percentage >= self._config.warning_threshold:
            return self._config.warning_color or self._scheme.warning
        elif percentage >= self._config.safe_threshold:
            return self._scheme.warning
        else:
            return self._config.safe_color or self._scheme.positive


class CircularProgressWidget(QWidget, ChartAnimationMixin):
    """Circular/gauge style progress widget."""

    clicked = pyqtSignal(str, float, float)

    def __init__(
        self,
        item: BudgetItem,
        scheme: ColorScheme,
        config: Optional[ProgressChartConfig] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._item = item
        self._scheme = scheme
        self._config = config or ProgressChartConfig(style=ProgressStyle.CIRCULAR)
        self._animation_progress = 0.0

        self.setMinimumSize(120, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        """Paint circular progress."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dimensions
        size = min(self.width(), self.height() - 40)
        x = (self.width() - size) / 2
        y = 10
        rect = QRectF(x, y, size, size)
        center = rect.center()

        line_width = 12
        inner_rect = rect.adjusted(line_width/2, line_width/2, -line_width/2, -line_width/2)

        # Background arc
        painter.setPen(QPen(QColor(self._scheme.grid), line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._config.style == ProgressStyle.SEMICIRCLE:
            painter.drawArc(inner_rect, 180 * 16, 180 * 16)
        else:
            painter.drawEllipse(inner_rect)

        # Progress arc
        percentage = min(self._item.percentage, 100) * self._animation_progress
        color = QColor(self._get_zone_color(self._item.percentage * self._animation_progress))

        # Create gradient pen (simulated with solid color)
        painter.setPen(QPen(color, line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

        if self._config.style == ProgressStyle.SEMICIRCLE:
            span_angle = int((percentage / 100) * 180 * 16)
            painter.drawArc(inner_rect, 180 * 16, span_angle)
        else:
            span_angle = int((percentage / 100) * 360 * 16)
            painter.drawArc(inner_rect, 90 * 16, -span_angle)

        # Center text
        painter.setPen(QColor(self._scheme.text))
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{percentage:.0f}%")

        # Category label below
        label_rect = QRectF(0, y + size + 5, self.width(), 25)
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._item.category)

        # Amount
        amount_rect = QRectF(0, y + size + 25, self.width(), 20)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(self._scheme.axis))
        painter.drawText(
            amount_rect,
            Qt.AlignmentFlag.AlignCenter,
            f"${self._item.spent:,.0f} / ${self._item.budget:,.0f}"
        )

    def _get_zone_color(self, percentage: float) -> str:
        """Get zone color."""
        if percentage > 100:
            return self._config.danger_color or self._scheme.negative
        elif percentage >= self._config.warning_threshold:
            return self._config.warning_color or self._scheme.warning
        else:
            return self._config.safe_color or self._scheme.positive

    def start_animation(self):
        """Start animation."""
        self._animation_progress = 0.0
        self.start_animation(AnimationType.GROW, self._config.animation_duration)

    def mousePressEvent(self, event):
        """Handle click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(
                self._item.category,
                self._item.spent,
                self._item.budget
            )


class ProgressChart(BaseChart):
    """
    Progress chart widget for budget tracking.

    Features:
    - Multiple budget items with progress bars
    - Color zones (safe/warning/danger)
    - Target line at 100%
    - Horizontal or circular style
    - Smooth animations
    - Over-budget indicators

    Usage:
        progress_chart = ProgressChart(config=ChartConfig(title="Budget Progress"))
        progress_chart.set_budget_data([
            {'category': 'Food', 'spent': 450, 'budget': 500},
            {'category': 'Transport', 'spent': 180, 'budget': 200},
            {'category': 'Entertainment', 'spent': 250, 'budget': 150},  # Over budget
        ])
    """

    # Additional signals
    category_clicked = pyqtSignal(str, float, float)  # category, spent, budget

    def __init__(
        self,
        config: Optional[ChartConfig] = None,
        parent: Optional[QWidget] = None,
        progress_config: Optional[ProgressChartConfig] = None
    ):
        self._progress_config = progress_config or ProgressChartConfig()
        self._budget_items: List[BudgetItem] = []
        self._progress_widgets: List[QWidget] = []

        # Disable default legend for this chart type
        if config is None:
            config = ChartConfig(show_legend=False)
        else:
            config.show_legend = False

        super().__init__(config, parent)

    def _setup_base_ui(self):
        """Setup progress chart UI."""
        super()._setup_base_ui()

        # Create scrollable container for progress items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(10, 5, 10, 5)
        self.items_layout.setSpacing(15)
        self.items_layout.addStretch()

        self.scroll_area.setWidget(self.items_container)

        # Add to chart container
        layout = QVBoxLayout(self.chart_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)

    def set_budget_data(self, data: List[Dict[str, Any]]):
        """
        Set budget progress data.

        Args:
            data: List of budget items with:
                - 'category': Category name
                - 'spent': Amount spent
                - 'budget': Budget limit
                - 'color': Optional color
        """
        self._budget_items = [
            BudgetItem(
                category=d.get('category', 'Unknown'),
                spent=float(d.get('spent', 0)),
                budget=float(d.get('budget', 0)),
                color=d.get('color') or get_category_color(d.get('category', ''))
            )
            for d in data
        ]
        self.update_chart()

        # Start animations
        if self._progress_config.animated:
            QTimer.singleShot(100, self._animate_items)

    def _animate_items(self):
        """Animate all progress items."""
        for widget in self._progress_widgets:
            if hasattr(widget, 'start_animation'):
                widget.start_animation()

    def update_chart(self):
        """Update the progress chart."""
        # Clear existing widgets
        for widget in self._progress_widgets:
            widget.deleteLater()
        self._progress_widgets.clear()

        # Create new progress widgets
        for item in self._budget_items:
            if self._progress_config.style in [ProgressStyle.CIRCULAR, ProgressStyle.SEMICIRCLE]:
                widget = CircularProgressWidget(
                    item, self._scheme, self._progress_config, self
                )
            else:
                widget = ProgressBarWidget(
                    item, self._scheme, self._progress_config, self
                )

            widget.clicked.connect(self._on_item_clicked)
            self.items_layout.insertWidget(
                self.items_layout.count() - 1,  # Before stretch
                widget
            )
            self._progress_widgets.append(widget)

    def _on_item_clicked(self, category: str, spent: float, budget: float):
        """Handle item click."""
        self.item_clicked.emit(category, spent)
        self.category_clicked.emit(category, spent, budget)

    def set_progress_config(self, config: ProgressChartConfig):
        """Update progress chart configuration."""
        self._progress_config = config
        self.update_chart()

    def set_style(self, style: ProgressStyle):
        """Set progress bar style."""
        self._progress_config.style = style
        self.update_chart()

    def set_thresholds(self, safe: float = 70, warning: float = 90):
        """Set color zone thresholds."""
        self._progress_config.safe_threshold = safe
        self._progress_config.warning_threshold = warning
        self.update_chart()

    def get_total_budget(self) -> float:
        """Get total budget amount."""
        return sum(item.budget for item in self._budget_items)

    def get_total_spent(self) -> float:
        """Get total spent amount."""
        return sum(item.spent for item in self._budget_items)

    def get_over_budget_categories(self) -> List[str]:
        """Get list of categories that are over budget."""
        return [item.category for item in self._budget_items if item.is_over_budget]


# Summary widget for budget overview
class BudgetSummaryWidget(QWidget):
    """
    Summary widget showing overall budget status.
    """

    def __init__(
        self,
        total_spent: float,
        total_budget: float,
        scheme: ColorScheme,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._spent = total_spent
        self._budget = total_budget
        self._scheme = scheme

        self._setup_ui()

    def _setup_ui(self):
        """Setup summary UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Total budget
        budget_layout = QVBoxLayout()
        budget_title = QLabel("Total Budget")
        budget_title.setFont(QFont("Segoe UI", 10))
        budget_title.setStyleSheet(f"color: {self._scheme.axis};")
        budget_layout.addWidget(budget_title)

        budget_value = QLabel(f"${self._budget:,.2f}")
        budget_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        budget_value.setStyleSheet(f"color: {self._scheme.text};")
        budget_layout.addWidget(budget_value)
        layout.addLayout(budget_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"background-color: {self._scheme.grid};")
        layout.addWidget(sep)

        # Total spent
        spent_layout = QVBoxLayout()
        spent_title = QLabel("Total Spent")
        spent_title.setFont(QFont("Segoe UI", 10))
        spent_title.setStyleSheet(f"color: {self._scheme.axis};")
        spent_layout.addWidget(spent_title)

        spent_color = self._scheme.negative if self._spent > self._budget else self._scheme.text
        spent_value = QLabel(f"${self._spent:,.2f}")
        spent_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        spent_value.setStyleSheet(f"color: {spent_color};")
        spent_layout.addWidget(spent_value)
        layout.addLayout(spent_layout)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"background-color: {self._scheme.grid};")
        layout.addWidget(sep2)

        # Remaining
        remaining_layout = QVBoxLayout()
        remaining_title = QLabel("Remaining")
        remaining_title.setFont(QFont("Segoe UI", 10))
        remaining_title.setStyleSheet(f"color: {self._scheme.axis};")
        remaining_layout.addWidget(remaining_title)

        remaining = self._budget - self._spent
        remaining_color = self._scheme.positive if remaining >= 0 else self._scheme.negative
        remaining_text = f"${abs(remaining):,.2f}" if remaining >= 0 else f"-${abs(remaining):,.2f}"
        remaining_value = QLabel(remaining_text)
        remaining_value.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        remaining_value.setStyleSheet(f"color: {remaining_color};")
        remaining_layout.addWidget(remaining_value)
        layout.addLayout(remaining_layout)

        layout.addStretch()


# Convenience functions
def create_progress_chart(
    title: str = "",
    data: Optional[List[Dict[str, Any]]] = None,
    dark_mode: bool = False,
    style: ProgressStyle = ProgressStyle.HORIZONTAL
) -> ProgressChart:
    """Create a configured progress chart."""
    config = ChartConfig(
        title=title,
        dark_mode=dark_mode,
        show_legend=False
    )
    progress_config = ProgressChartConfig(style=style)

    chart = ProgressChart(config=config, progress_config=progress_config)
    if data:
        chart.set_budget_data(data)
    return chart


def create_budget_dashboard(
    title: str = "",
    data: Optional[List[Dict[str, Any]]] = None,
    dark_mode: bool = False
) -> QWidget:
    """
    Create a complete budget dashboard with summary and progress bars.

    Returns a widget containing:
    - Budget summary (total, spent, remaining)
    - Progress bars for each category
    """
    from .charts import get_scheme_for_mode

    scheme = get_scheme_for_mode(dark_mode)

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(15)

    # Calculate totals
    if data:
        total_spent = sum(d.get('spent', 0) for d in data)
        total_budget = sum(d.get('budget', 0) for d in data)
    else:
        total_spent = 0
        total_budget = 0

    # Summary widget
    summary = BudgetSummaryWidget(total_spent, total_budget, scheme)
    layout.addWidget(summary)

    # Progress chart
    chart = create_progress_chart(title, data, dark_mode)
    layout.addWidget(chart, stretch=1)

    return container
