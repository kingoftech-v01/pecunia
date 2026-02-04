"""
Bar Chart Widget Module

Provides BarChart widget for comparing categories and values.
Features: stacked/grouped bars, horizontal/vertical orientation, tooltips, animations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QToolTip, QMenu
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPointF, QRectF, QLineF,
    QPropertyAnimation, QEasingCurve, Property
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath,
    QLinearGradient, QMouseEvent, QAction
)

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from .charts import (
    BaseChart, ChartConfig, ChartDataPoint, ChartSeries, ColorScheme,
    AnimationType, LegendPosition, ChartAnimationMixin,
    LIGHT_SCHEME, DARK_SCHEME
)


class BarOrientation(Enum):
    """Bar chart orientation."""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class BarMode(Enum):
    """Bar grouping mode."""
    GROUPED = "grouped"
    STACKED = "stacked"


@dataclass
class BarChartConfig:
    """Configuration specific to bar charts."""
    orientation: BarOrientation = BarOrientation.VERTICAL
    mode: BarMode = BarMode.GROUPED
    bar_width: float = 0.7  # Relative to category spacing
    bar_spacing: float = 0.1  # Spacing between bars in group
    show_values: bool = True
    value_format: str = "${value:,.0f}"
    show_grid: bool = True
    grid_opacity: float = 0.3
    rounded_corners: bool = True
    corner_radius: int = 4
    gradient_fill: bool = True


class BarChartCanvas(QWidget, ChartAnimationMixin):
    """
    Custom canvas widget for rendering bar charts.

    Features:
    - Grouped or stacked bars
    - Vertical or horizontal orientation
    - Gradient fills
    - Value labels
    - Hover effects
    """

    # Signals
    bar_hovered = pyqtSignal(str, str, float)  # group, category, value
    bar_clicked = pyqtSignal(str, str, float)  # group, category, value

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._groups: List[Dict[str, Any]] = []  # For grouped/stacked bars
        self._data: List[Dict[str, Any]] = []  # For simple bars
        self._categories: List[str] = []
        self._scheme: Optional[ColorScheme] = None
        self._config = BarChartConfig()

        # Interaction state
        self._hover_bar: Optional[Tuple[int, int]] = None  # group_idx, bar_idx
        self._animation_progress = 0.0

        # View bounds
        self._y_max = 100.0
        self._y_min = 0.0

        self.setMouseTracking(True)
        self.setMinimumSize(200, 150)

    def set_data(
        self,
        data: List[Dict[str, Any]],
        scheme: ColorScheme,
        config: Optional[BarChartConfig] = None
    ):
        """Set simple bar data."""
        self._data = data
        self._groups = []
        self._scheme = scheme
        if config:
            self._config = config

        # Extract categories from data
        self._categories = [d.get('label', '') for d in data]

        # Auto-scale Y axis
        values = [d.get('value', 0) for d in data]
        if values:
            self._y_max = max(values) * 1.1
            self._y_min = min(0, min(values))

        self.update()

    def set_groups(
        self,
        groups: List[Dict[str, Any]],
        categories: List[str],
        scheme: ColorScheme,
        config: Optional[BarChartConfig] = None
    ):
        """
        Set grouped/stacked bar data.

        Args:
            groups: List of group definitions with 'label', 'color', 'values'
            categories: List of category labels
            scheme: Color scheme
            config: Bar chart configuration
        """
        self._groups = groups
        self._data = []
        self._categories = categories
        self._scheme = scheme
        if config:
            self._config = config

        # Auto-scale Y axis
        if self._config.mode == BarMode.STACKED:
            # Sum values per category
            max_sums = []
            for i in range(len(categories)):
                total = sum(g.get('values', [])[i] if i < len(g.get('values', [])) else 0
                           for g in groups)
                max_sums.append(total)
            self._y_max = max(max_sums) * 1.1 if max_sums else 100
        else:
            # Max individual value
            all_values = []
            for g in groups:
                all_values.extend(g.get('values', []))
            self._y_max = max(all_values) * 1.1 if all_values else 100

        self._y_min = 0
        self.update()

    def paintEvent(self, event):
        """Paint the bar chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._scheme:
            return

        # Fill background
        painter.fillRect(self.rect(), QColor(self._scheme.background))

        margin = 60
        plot_rect = QRectF(
            margin, 20,
            self.width() - margin - 20,
            self.height() - margin - 20
        )

        # Draw grid
        if self._config.show_grid:
            self._draw_grid(painter, plot_rect)

        # Draw axes
        self._draw_axes(painter, plot_rect)

        # Draw bars
        if self._groups:
            self._draw_grouped_bars(painter, plot_rect)
        elif self._data:
            self._draw_simple_bars(painter, plot_rect)

    def _draw_grid(self, painter: QPainter, plot_rect: QRectF):
        """Draw grid lines."""
        grid_color = QColor(self._scheme.grid)
        grid_color.setAlphaF(self._config.grid_opacity)
        painter.setPen(QPen(grid_color, 1, Qt.PenStyle.DotLine))

        if self._config.orientation == BarOrientation.VERTICAL:
            # Horizontal grid lines
            for i in range(6):
                y = plot_rect.bottom() - plot_rect.height() * i / 5
                painter.drawLine(QLineF(plot_rect.left(), y, plot_rect.right(), y))
        else:
            # Vertical grid lines
            for i in range(6):
                x = plot_rect.left() + plot_rect.width() * i / 5
                painter.drawLine(QLineF(x, plot_rect.top(), x, plot_rect.bottom()))

    def _draw_axes(self, painter: QPainter, plot_rect: QRectF):
        """Draw axes and labels."""
        axis_color = QColor(self._scheme.axis)
        text_color = QColor(self._scheme.text)

        painter.setPen(QPen(axis_color, 2))

        if self._config.orientation == BarOrientation.VERTICAL:
            # Y axis
            painter.drawLine(QLineF(
                plot_rect.left(), plot_rect.top(),
                plot_rect.left(), plot_rect.bottom()
            ))
            # X axis
            painter.drawLine(QLineF(
                plot_rect.left(), plot_rect.bottom(),
                plot_rect.right(), plot_rect.bottom()
            ))

            # Y axis labels
            painter.setPen(text_color)
            painter.setFont(QFont("Segoe UI", 8))

            y_range = self._y_max - self._y_min
            for i in range(6):
                y = plot_rect.bottom() - plot_rect.height() * i / 5
                value = self._y_min + y_range * i / 5
                label = f"${value:,.0f}"
                painter.drawText(
                    QRectF(0, y - 10, plot_rect.left() - 5, 20),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    label
                )

            # Category labels
            if self._categories:
                cat_width = plot_rect.width() / len(self._categories)
                for i, cat in enumerate(self._categories):
                    x = plot_rect.left() + cat_width * (i + 0.5)
                    painter.drawText(
                        QRectF(x - cat_width/2, plot_rect.bottom() + 5, cat_width, 30),
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
                        cat
                    )
        else:
            # Horizontal orientation
            # X axis (value axis)
            painter.drawLine(QLineF(
                plot_rect.left(), plot_rect.bottom(),
                plot_rect.right(), plot_rect.bottom()
            ))
            # Y axis (category axis)
            painter.drawLine(QLineF(
                plot_rect.left(), plot_rect.top(),
                plot_rect.left(), plot_rect.bottom()
            ))

            # X axis labels
            painter.setPen(text_color)
            painter.setFont(QFont("Segoe UI", 8))

            x_range = self._y_max - self._y_min
            for i in range(6):
                x = plot_rect.left() + plot_rect.width() * i / 5
                value = self._y_min + x_range * i / 5
                label = f"${value:,.0f}"
                painter.drawText(
                    QRectF(x - 30, plot_rect.bottom() + 5, 60, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    label
                )

            # Category labels
            if self._categories:
                cat_height = plot_rect.height() / len(self._categories)
                for i, cat in enumerate(self._categories):
                    y = plot_rect.top() + cat_height * (i + 0.5)
                    painter.drawText(
                        QRectF(5, y - 10, plot_rect.left() - 10, 20),
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        cat
                    )

    def _draw_simple_bars(self, painter: QPainter, plot_rect: QRectF):
        """Draw simple bar chart."""
        if not self._data:
            return

        num_bars = len(self._data)
        bar_spacing = plot_rect.width() / num_bars if self._config.orientation == BarOrientation.VERTICAL else plot_rect.height() / num_bars
        bar_width = bar_spacing * self._config.bar_width

        for i, d in enumerate(self._data):
            value = d.get('value', 0) * self._animation_progress
            color = QColor(d.get('color', self._scheme.positive if value >= 0 else self._scheme.negative))

            is_hovered = self._hover_bar == (i, 0)
            if is_hovered:
                color = color.lighter(115)

            self._draw_bar(
                painter, plot_rect, i, 0, 1, value,
                color, bar_width, bar_spacing, is_hovered
            )

    def _draw_grouped_bars(self, painter: QPainter, plot_rect: QRectF):
        """Draw grouped or stacked bars."""
        if not self._groups or not self._categories:
            return

        num_categories = len(self._categories)
        num_groups = len(self._groups)

        if self._config.orientation == BarOrientation.VERTICAL:
            cat_spacing = plot_rect.width() / num_categories
        else:
            cat_spacing = plot_rect.height() / num_categories

        if self._config.mode == BarMode.GROUPED:
            bar_width = (cat_spacing * self._config.bar_width) / num_groups
        else:
            bar_width = cat_spacing * self._config.bar_width

        for cat_idx in range(num_categories):
            stack_offset = 0.0

            for grp_idx, group in enumerate(self._groups):
                values = group.get('values', [])
                value = values[cat_idx] if cat_idx < len(values) else 0
                value *= self._animation_progress

                color = QColor(group.get('color', self._scheme.colors[grp_idx % len(self._scheme.colors)]))

                is_hovered = self._hover_bar == (cat_idx, grp_idx)
                if is_hovered:
                    color = color.lighter(115)

                if self._config.mode == BarMode.STACKED:
                    self._draw_bar(
                        painter, plot_rect, cat_idx, 0, 1, value,
                        color, bar_width, cat_spacing, is_hovered,
                        stack_offset=stack_offset
                    )
                    stack_offset += value
                else:
                    self._draw_bar(
                        painter, plot_rect, cat_idx, grp_idx, num_groups, value,
                        color, bar_width, cat_spacing, is_hovered
                    )

    def _draw_bar(
        self,
        painter: QPainter,
        plot_rect: QRectF,
        cat_idx: int,
        bar_idx: int,
        num_bars: int,
        value: float,
        color: QColor,
        bar_width: float,
        cat_spacing: float,
        is_hovered: bool,
        stack_offset: float = 0.0
    ):
        """Draw a single bar."""
        y_range = self._y_max - self._y_min
        if y_range == 0:
            y_range = 1

        if self._config.orientation == BarOrientation.VERTICAL:
            # Calculate bar position
            cat_center = plot_rect.left() + cat_spacing * (cat_idx + 0.5)

            if self._config.mode == BarMode.GROUPED:
                bar_x = cat_center - (cat_spacing * self._config.bar_width / 2) + bar_width * bar_idx
            else:
                bar_x = cat_center - bar_width / 2

            bar_height = abs(value) / y_range * plot_rect.height()
            base_y = plot_rect.bottom() - (stack_offset / y_range * plot_rect.height())

            if value >= 0:
                bar_rect = QRectF(bar_x, base_y - bar_height, bar_width, bar_height)
            else:
                bar_rect = QRectF(bar_x, base_y, bar_width, bar_height)
        else:
            # Horizontal bars
            cat_center = plot_rect.top() + cat_spacing * (cat_idx + 0.5)

            if self._config.mode == BarMode.GROUPED:
                bar_y = cat_center - (cat_spacing * self._config.bar_width / 2) + bar_width * bar_idx
            else:
                bar_y = cat_center - bar_width / 2

            bar_length = abs(value) / y_range * plot_rect.width()
            base_x = plot_rect.left() + (stack_offset / y_range * plot_rect.width())

            bar_rect = QRectF(base_x, bar_y, bar_length, bar_width)

        # Draw bar with gradient
        if self._config.gradient_fill:
            gradient = QLinearGradient(bar_rect.topLeft(), bar_rect.bottomRight())
            gradient.setColorAt(0, color.lighter(110))
            gradient.setColorAt(1, color)
            painter.setBrush(QBrush(gradient))
        else:
            painter.setBrush(QBrush(color))

        # Border on hover
        if is_hovered:
            painter.setPen(QPen(color.darker(120), 2))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        # Draw with rounded corners
        if self._config.rounded_corners:
            path = QPainterPath()
            radius = min(self._config.corner_radius, bar_rect.width() / 2, bar_rect.height() / 2)
            path.addRoundedRect(bar_rect, radius, radius)
            painter.drawPath(path)
        else:
            painter.drawRect(bar_rect)

        # Draw value label
        if self._config.show_values and value != 0:
            painter.setPen(QColor(self._scheme.text))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))

            label = f"${value:,.0f}"
            if self._config.orientation == BarOrientation.VERTICAL:
                label_rect = QRectF(
                    bar_rect.left() - 10, bar_rect.top() - 18,
                    bar_rect.width() + 20, 15
                )
            else:
                label_rect = QRectF(
                    bar_rect.right() + 5, bar_rect.top(),
                    50, bar_rect.height()
                )

            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse movement for hover."""
        pos = event.position()
        new_hover = self._find_bar_at_position(pos)

        if new_hover != self._hover_bar:
            self._hover_bar = new_hover
            self.update()

            if new_hover:
                cat_idx, bar_idx = new_hover
                if self._groups:
                    if bar_idx < len(self._groups):
                        group = self._groups[bar_idx]
                        values = group.get('values', [])
                        value = values[cat_idx] if cat_idx < len(values) else 0
                        category = self._categories[cat_idx] if cat_idx < len(self._categories) else ''
                        tooltip = f"{group.get('label', '')}\n{category}: ${value:,.2f}"
                        QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                        self.bar_hovered.emit(group.get('label', ''), category, value)
                elif self._data and cat_idx < len(self._data):
                    d = self._data[cat_idx]
                    tooltip = f"{d.get('label', '')}: ${d.get('value', 0):,.2f}"
                    QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                    self.bar_hovered.emit('', d.get('label', ''), d.get('value', 0))
            else:
                QToolTip.hideText()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse click."""
        if event.button() == Qt.MouseButton.LeftButton and self._hover_bar:
            cat_idx, bar_idx = self._hover_bar
            if self._groups:
                if bar_idx < len(self._groups):
                    group = self._groups[bar_idx]
                    values = group.get('values', [])
                    value = values[cat_idx] if cat_idx < len(values) else 0
                    category = self._categories[cat_idx] if cat_idx < len(self._categories) else ''
                    self.bar_clicked.emit(group.get('label', ''), category, value)
            elif self._data and cat_idx < len(self._data):
                d = self._data[cat_idx]
                self.bar_clicked.emit('', d.get('label', ''), d.get('value', 0))

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover_bar = None
        QToolTip.hideText()
        self.update()

    def _find_bar_at_position(self, pos: QPointF) -> Optional[Tuple[int, int]]:
        """Find bar at given position."""
        margin = 60
        plot_rect = QRectF(
            margin, 20,
            self.width() - margin - 20,
            self.height() - margin - 20
        )

        if not plot_rect.contains(pos):
            return None

        num_categories = len(self._categories) or len(self._data)
        if num_categories == 0:
            return None

        if self._config.orientation == BarOrientation.VERTICAL:
            cat_spacing = plot_rect.width() / num_categories
            cat_idx = int((pos.x() - plot_rect.left()) / cat_spacing)
        else:
            cat_spacing = plot_rect.height() / num_categories
            cat_idx = int((pos.y() - plot_rect.top()) / cat_spacing)

        if cat_idx < 0 or cat_idx >= num_categories:
            return None

        # For grouped bars, find which bar in group
        if self._groups and self._config.mode == BarMode.GROUPED:
            num_groups = len(self._groups)
            bar_width = (cat_spacing * self._config.bar_width) / num_groups

            if self._config.orientation == BarOrientation.VERTICAL:
                cat_start = plot_rect.left() + cat_spacing * cat_idx + cat_spacing * (1 - self._config.bar_width) / 2
                bar_idx = int((pos.x() - cat_start) / bar_width)
            else:
                cat_start = plot_rect.top() + cat_spacing * cat_idx + cat_spacing * (1 - self._config.bar_width) / 2
                bar_idx = int((pos.y() - cat_start) / bar_width)

            if 0 <= bar_idx < num_groups:
                return (cat_idx, bar_idx)
        else:
            return (cat_idx, 0)

        return None


class BarChart(BaseChart):
    """
    Bar chart widget for comparing categories.

    Features:
    - Grouped or stacked bar modes
    - Vertical or horizontal orientation
    - Value labels on bars
    - Hover tooltips
    - Smooth animations
    - Dark/light theme support

    Usage:
        # Simple bar chart
        bar_chart = BarChart(config=ChartConfig(title="Monthly Expenses"))
        bar_chart.set_data([
            {'label': 'Jan', 'value': 1500, 'color': '#4CAF50'},
            {'label': 'Feb', 'value': 1800, 'color': '#2196F3'},
        ])

        # Grouped bar chart (income vs expenses)
        bar_chart.set_categories(['Jan', 'Feb', 'Mar', 'Apr'])
        bar_chart.set_groups([
            {'label': 'Income', 'color': '#4CAF50', 'values': [3000, 3200, 2800, 3500]},
            {'label': 'Expenses', 'color': '#F44336', 'values': [2500, 2800, 2200, 2900]},
        ])
    """

    def __init__(
        self,
        config: Optional[ChartConfig] = None,
        parent: Optional[QWidget] = None,
        bar_config: Optional[BarChartConfig] = None
    ):
        self._bar_config = bar_config or BarChartConfig()
        super().__init__(config, parent)

    def _setup_base_ui(self):
        """Setup bar chart specific UI."""
        super()._setup_base_ui()

        # Create bar chart canvas
        self.canvas = BarChartCanvas(parent=self.chart_container)
        self.canvas.bar_hovered.connect(self._on_bar_hover)
        self.canvas.bar_clicked.connect(self._on_bar_click)

        # Layout canvas
        canvas_layout = QVBoxLayout(self.chart_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.canvas)

    def _on_bar_hover(self, group: str, category: str, value: float):
        """Handle bar hover."""
        label = f"{group}: {category}" if group else category
        self.item_hovered.emit(label, value)

    def _on_bar_click(self, group: str, category: str, value: float):
        """Handle bar click."""
        label = f"{group}: {category}" if group else category
        self.item_clicked.emit(label, value)

    def _get_legend_data(self) -> List[Dict[str, Any]]:
        """Get legend data."""
        if hasattr(self, '_groups_data') and self._groups_data:
            return [
                {
                    'label': g.get('label', ''),
                    'color': g.get('color', self._scheme.colors[i % len(self._scheme.colors)])
                }
                for i, g in enumerate(self._groups_data)
            ]
        else:
            colors = self._config.get_colors()
            return [
                {
                    'label': dp.label,
                    'value': dp.value,
                    'color': dp.color or colors[i % len(colors)]
                }
                for i, dp in enumerate(self._data)
            ]

    def update_chart(self):
        """Update the bar chart."""
        super().update_chart()

        if not hasattr(self, 'canvas'):
            return

        colors = self._config.get_colors()

        # Check if we have group data or simple data
        if hasattr(self, '_groups_data') and self._groups_data:
            canvas_groups = []
            for i, g in enumerate(self._groups_data):
                canvas_groups.append({
                    'label': g.get('label', f'Group {i+1}'),
                    'color': g.get('color', colors[i % len(colors)]),
                    'values': g.get('values', [])
                })

            self.canvas.set_groups(
                canvas_groups,
                self._categories if hasattr(self, '_categories') else [],
                self._scheme,
                self._bar_config
            )
        else:
            # Simple bar data
            canvas_data = []
            for i, dp in enumerate(self._data):
                canvas_data.append({
                    'label': dp.label,
                    'value': dp.value,
                    'color': dp.color or colors[i % len(colors)]
                })

            self.canvas.set_data(canvas_data, self._scheme, self._bar_config)

        # Animation
        if self._config.animation_type != AnimationType.NONE:
            self.canvas._animation_progress = 0.0
            self.canvas.start_animation(
                self._config.animation_type,
                self._config.animation_duration
            )
        else:
            self.canvas._animation_progress = 1.0

    def set_categories(self, categories: List[str]):
        """Set category labels for x-axis."""
        self._categories = categories
        self.update_chart()

    def set_groups(self, groups: List[Dict[str, Any]]):
        """
        Set grouped bar data.

        Args:
            groups: List of group definitions with:
                - 'label': Group name
                - 'color': Bar color
                - 'values': List of values for each category
        """
        self._groups_data = groups
        self.update_chart()

    def set_bar_config(self, config: BarChartConfig):
        """Update bar chart configuration."""
        self._bar_config = config
        self.update_chart()

    def set_orientation(self, orientation: BarOrientation):
        """Set bar orientation (vertical or horizontal)."""
        self._bar_config.orientation = orientation
        self.update_chart()

    def set_mode(self, mode: BarMode):
        """Set bar mode (grouped or stacked)."""
        self._bar_config.mode = mode
        self.update_chart()

    def set_show_values(self, show: bool):
        """Show/hide value labels on bars."""
        self._bar_config.show_values = show
        self.update_chart()


# Convenience functions
def create_bar_chart(
    title: str = "",
    data: Optional[List[Dict[str, Any]]] = None,
    dark_mode: bool = False,
    horizontal: bool = False
) -> BarChart:
    """Create a simple bar chart."""
    config = ChartConfig(
        title=title,
        dark_mode=dark_mode,
        animation_type=AnimationType.GROW
    )
    bar_config = BarChartConfig(
        orientation=BarOrientation.HORIZONTAL if horizontal else BarOrientation.VERTICAL
    )

    chart = BarChart(config=config, bar_config=bar_config)
    if data:
        chart.set_data(data)
    return chart


def create_grouped_bar_chart(
    title: str = "",
    categories: Optional[List[str]] = None,
    groups: Optional[List[Dict[str, Any]]] = None,
    dark_mode: bool = False,
    stacked: bool = False
) -> BarChart:
    """Create a grouped or stacked bar chart."""
    config = ChartConfig(
        title=title,
        dark_mode=dark_mode,
        animation_type=AnimationType.GROW
    )
    bar_config = BarChartConfig(
        mode=BarMode.STACKED if stacked else BarMode.GROUPED
    )

    chart = BarChart(config=config, bar_config=bar_config)
    if categories:
        chart.set_categories(categories)
    if groups:
        chart.set_groups(groups)
    return chart
