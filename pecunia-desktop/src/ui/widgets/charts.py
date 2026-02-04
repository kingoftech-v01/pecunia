"""
Charts Base Module

Base classes and utilities for chart widgets.
Provides BaseChart class, color schemes, configuration, and animation support.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QGraphicsOpacityEffect, QFrame
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QSequentialAnimationGroup,
    Property, QTimer, QPointF
)
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import math

# Try to import pyqtgraph
try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    pg = None


# ============================================================================
# Enums and Constants
# ============================================================================

class ChartType(Enum):
    """Available chart types."""
    PIE = "pie"
    DONUT = "donut"
    LINE = "line"
    BAR = "bar"
    AREA = "area"
    PROGRESS = "progress"
    SPARKLINE = "sparkline"


class AnimationType(Enum):
    """Animation types for charts."""
    NONE = "none"
    FADE_IN = "fade_in"
    GROW = "grow"
    SLIDE = "slide"
    BOUNCE = "bounce"


class LegendPosition(Enum):
    """Legend position options."""
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"
    TOP = "top"
    NONE = "none"


# ============================================================================
# Color Schemes
# ============================================================================

@dataclass
class ColorScheme:
    """Color scheme definition for charts."""
    name: str
    colors: List[str]
    background: str = "#FFFFFF"
    foreground: str = "#333333"
    grid: str = "#E0E0E0"
    axis: str = "#666666"
    text: str = "#333333"
    tooltip_bg: str = "#FFFFFF"
    tooltip_border: str = "#CCCCCC"
    positive: str = "#4CAF50"
    negative: str = "#F44336"
    warning: str = "#FF9800"


# Predefined color schemes
LIGHT_SCHEME = ColorScheme(
    name="light",
    colors=[
        "#4CAF50",  # Green
        "#2196F3",  # Blue
        "#FF9800",  # Orange
        "#E91E63",  # Pink
        "#9C27B0",  # Purple
        "#00BCD4",  # Cyan
        "#FFC107",  # Amber
        "#795548",  # Brown
        "#607D8B",  # Blue Grey
        "#F44336",  # Red
        "#8BC34A",  # Light Green
        "#03A9F4",  # Light Blue
    ],
    background="#FFFFFF",
    foreground="#333333",
    grid="#E0E0E0",
    axis="#666666",
    text="#333333",
    tooltip_bg="#FFFFFF",
    tooltip_border="#CCCCCC",
)

DARK_SCHEME = ColorScheme(
    name="dark",
    colors=[
        "#81C784",  # Light Green
        "#64B5F6",  # Light Blue
        "#FFB74D",  # Light Orange
        "#F06292",  # Light Pink
        "#BA68C8",  # Light Purple
        "#4DD0E1",  # Light Cyan
        "#FFD54F",  # Light Amber
        "#A1887F",  # Light Brown
        "#90A4AE",  # Light Blue Grey
        "#E57373",  # Light Red
        "#AED581",  # Lighter Green
        "#4FC3F7",  # Lighter Blue
    ],
    background="#1E1E1E",
    foreground="#E0E0E0",
    grid="#3A3A3A",
    axis="#888888",
    text="#E0E0E0",
    tooltip_bg="#2D2D2D",
    tooltip_border="#444444",
    positive="#81C784",
    negative="#E57373",
    warning="#FFD54F",
)

# Finance-specific color scheme
FINANCE_SCHEME = ColorScheme(
    name="finance",
    colors=[
        "#1976D2",  # Primary Blue
        "#26A69A",  # Teal
        "#FFA726",  # Orange
        "#AB47BC",  # Purple
        "#66BB6A",  # Green
        "#EF5350",  # Red
        "#42A5F5",  # Light Blue
        "#FFCA28",  # Yellow
        "#8D6E63",  # Brown
        "#78909C",  # Blue Grey
    ],
    background="#FFFFFF",
    foreground="#212121",
    grid="#E0E0E0",
    axis="#757575",
    text="#212121",
    tooltip_bg="#FFFFFF",
    tooltip_border="#BDBDBD",
    positive="#4CAF50",
    negative="#F44336",
    warning="#FF9800",
)

# Category-specific colors for finance
CATEGORY_COLORS = {
    "Food & Dining": "#FF5722",
    "Transportation": "#2196F3",
    "Shopping": "#9C27B0",
    "Entertainment": "#E91E63",
    "Bills & Utilities": "#607D8B",
    "Healthcare": "#F44336",
    "Education": "#3F51B5",
    "Travel": "#00BCD4",
    "Income": "#4CAF50",
    "Salary": "#4CAF50",
    "Investment": "#8BC34A",
    "Savings": "#009688",
    "Housing": "#795548",
    "Insurance": "#FF9800",
    "Personal Care": "#FFC107",
    "Gifts & Donations": "#E91E63",
    "Other": "#9E9E9E",
}


def get_category_color(category: str) -> str:
    """Get color for a specific category."""
    return CATEGORY_COLORS.get(category, "#9E9E9E")


def get_scheme_for_mode(dark_mode: bool) -> ColorScheme:
    """Get appropriate color scheme based on theme mode."""
    return DARK_SCHEME if dark_mode else LIGHT_SCHEME


# ============================================================================
# Chart Configuration
# ============================================================================

@dataclass
class ChartConfig:
    """Configuration options for charts."""
    # General
    title: str = ""
    subtitle: str = ""
    show_title: bool = True

    # Theme
    dark_mode: bool = False
    color_scheme: Optional[ColorScheme] = None
    custom_colors: Optional[List[str]] = None

    # Legend
    show_legend: bool = True
    legend_position: LegendPosition = LegendPosition.RIGHT

    # Animation
    animation_type: AnimationType = AnimationType.FADE_IN
    animation_duration: int = 500  # milliseconds

    # Tooltips
    show_tooltips: bool = True
    tooltip_format: str = "{label}: {value}"

    # Sizing
    min_width: int = 200
    min_height: int = 200
    padding: int = 10

    # Interaction
    interactive: bool = True
    clickable: bool = True
    hoverable: bool = True

    def get_scheme(self) -> ColorScheme:
        """Get the effective color scheme."""
        if self.color_scheme:
            return self.color_scheme
        return get_scheme_for_mode(self.dark_mode)

    def get_colors(self) -> List[str]:
        """Get the effective color list."""
        if self.custom_colors:
            return self.custom_colors
        return self.get_scheme().colors


@dataclass
class ChartDataPoint:
    """Single data point for charts."""
    label: str
    value: float
    color: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartSeries:
    """Data series for multi-series charts."""
    name: str
    data: List[ChartDataPoint]
    color: Optional[str] = None
    line_style: str = "solid"  # solid, dashed, dotted
    line_width: int = 2
    show_points: bool = True
    fill_area: bool = False


# ============================================================================
# Animation Helpers
# ============================================================================

class ChartAnimationMixin:
    """Mixin class providing animation capabilities for charts."""

    _animation_progress: float = 0.0
    _animation_group: Optional[QParallelAnimationGroup] = None

    def _get_animation_progress(self) -> float:
        return self._animation_progress

    def _set_animation_progress(self, value: float):
        self._animation_progress = value
        if hasattr(self, 'update'):
            self.update()

    animation_progress = Property(
        float, _get_animation_progress, _set_animation_progress
    )

    def start_animation(
        self,
        animation_type: AnimationType = AnimationType.FADE_IN,
        duration: int = 500,
        callback: Optional[Callable] = None
    ):
        """Start chart animation."""
        if animation_type == AnimationType.NONE:
            self._animation_progress = 1.0
            if callback:
                callback()
            return

        # Stop any existing animation
        if self._animation_group and self._animation_group.state() == QParallelAnimationGroup.State.Running:
            self._animation_group.stop()

        # Create progress animation
        progress_anim = QPropertyAnimation(self, b"animation_progress")
        progress_anim.setStartValue(0.0)
        progress_anim.setEndValue(1.0)
        progress_anim.setDuration(duration)

        # Set easing based on animation type
        if animation_type == AnimationType.BOUNCE:
            progress_anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        elif animation_type == AnimationType.GROW:
            progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        elif animation_type == AnimationType.SLIDE:
            progress_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        else:  # FADE_IN
            progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Create animation group
        self._animation_group = QParallelAnimationGroup()
        self._animation_group.addAnimation(progress_anim)

        # Handle opacity for fade animation
        if animation_type == AnimationType.FADE_IN and hasattr(self, 'setGraphicsEffect'):
            opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(opacity_effect)

            opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
            opacity_anim.setStartValue(0.0)
            opacity_anim.setEndValue(1.0)
            opacity_anim.setDuration(duration)
            opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation_group.addAnimation(opacity_anim)

        if callback:
            self._animation_group.finished.connect(callback)

        self._animation_group.start()

    def stop_animation(self):
        """Stop current animation."""
        if self._animation_group:
            self._animation_group.stop()
            self._animation_progress = 1.0


# ============================================================================
# Base Chart Widget
# ============================================================================

class BaseChart(QWidget, ChartAnimationMixin):
    """
    Base class for all chart widgets.

    Provides common functionality for:
    - Theme management (dark/light mode)
    - Color scheme handling
    - Legend display
    - Animation support
    - Tooltip support
    - Click/hover interactions

    Signals:
        item_clicked: Emitted when a chart item is clicked (label, value)
        item_hovered: Emitted when hovering over an item (label, value)
        selection_changed: Emitted when selection changes (list of labels)
    """

    item_clicked = pyqtSignal(str, float)  # label, value
    item_hovered = pyqtSignal(str, float)  # label, value
    selection_changed = pyqtSignal(list)  # list of selected labels

    def __init__(
        self,
        config: Optional[ChartConfig] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # Initialize configuration
        self._config = config or ChartConfig()
        self._data: List[ChartDataPoint] = []
        self._series: List[ChartSeries] = []
        self._selected_items: List[str] = []
        self._hovered_item: Optional[str] = None
        self._legend_items: List[QWidget] = []

        # Get color scheme
        self._scheme = self._config.get_scheme()

        # Setup UI
        self._setup_base_ui()

        # Enable mouse tracking for hover
        self.setMouseTracking(True)

    def _setup_base_ui(self):
        """Setup the base UI structure."""
        self.setObjectName("chartWidget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(self._config.min_width, self._config.min_height)

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(
            self._config.padding,
            self._config.padding,
            self._config.padding,
            self._config.padding
        )
        self.main_layout.setSpacing(10)

        # Title section
        if self._config.show_title and self._config.title:
            self._create_title_section()

        # Content area (chart + legend)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(10)
        self.main_layout.addLayout(self.content_layout, stretch=1)

        # Chart container
        self.chart_container = QWidget()
        self.chart_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Add chart container to content layout
        if self._config.legend_position == LegendPosition.LEFT:
            self._create_legend_widget()
            self.content_layout.addWidget(self.chart_container, stretch=3)
        elif self._config.legend_position == LegendPosition.RIGHT:
            self.content_layout.addWidget(self.chart_container, stretch=3)
            self._create_legend_widget()
        else:
            self.content_layout.addWidget(self.chart_container, stretch=1)

        # Bottom legend if needed
        if self._config.legend_position == LegendPosition.BOTTOM:
            self._create_legend_widget(horizontal=True)

        # Apply initial styling
        self._apply_theme()

    def _create_title_section(self):
        """Create the title section."""
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 5)
        title_layout.setSpacing(2)

        # Main title
        self.title_label = QLabel(self._config.title)
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(self.title_label)

        # Subtitle
        if self._config.subtitle:
            self.subtitle_label = QLabel(self._config.subtitle)
            self.subtitle_label.setFont(QFont("Segoe UI", 10))
            self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_layout.addWidget(self.subtitle_label)

        self.main_layout.addWidget(title_widget)

    def _create_legend_widget(self, horizontal: bool = False):
        """Create the legend widget."""
        if not self._config.show_legend or self._config.legend_position == LegendPosition.NONE:
            return

        self.legend_widget = QWidget()
        self.legend_widget.setObjectName("chartLegend")

        if horizontal:
            self.legend_layout = QHBoxLayout(self.legend_widget)
            self.legend_layout.addStretch()
            self.main_layout.addWidget(self.legend_widget)
        else:
            self.legend_layout = QVBoxLayout(self.legend_widget)
            self.legend_layout.addStretch()
            self.content_layout.addWidget(self.legend_widget, stretch=1)

        self.legend_layout.setContentsMargins(10, 10, 10, 10)
        self.legend_layout.setSpacing(5)

    def _apply_theme(self):
        """Apply current theme styling."""
        self._scheme = self._config.get_scheme()

        # Apply background
        self.setStyleSheet(f"""
            QWidget#chartWidget {{
                background-color: {self._scheme.background};
            }}
            QWidget#chartLegend {{
                background-color: transparent;
            }}
        """)

        # Update title styling
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {self._scheme.text};")
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.setStyleSheet(f"color: {self._scheme.axis};")

        # Update legend
        self._update_legend()

    def _update_legend(self):
        """Update legend display with current data."""
        if not hasattr(self, 'legend_layout'):
            return

        # Clear existing items
        for item in self._legend_items:
            item.deleteLater()
        self._legend_items.clear()

        if not self._config.show_legend:
            return

        # Get data for legend
        legend_data = self._get_legend_data()

        for item_data in legend_data:
            item_widget = self._create_legend_item(item_data)
            insert_index = self.legend_layout.count() - 1
            self.legend_layout.insertWidget(insert_index, item_widget)
            self._legend_items.append(item_widget)

    def _get_legend_data(self) -> List[Dict[str, Any]]:
        """Get data for legend. Override in subclasses."""
        colors = self._config.get_colors()
        return [
            {
                'label': dp.label,
                'value': dp.value,
                'color': dp.color or colors[i % len(colors)]
            }
            for i, dp in enumerate(self._data)
        ]

    def _create_legend_item(self, data: Dict[str, Any]) -> QWidget:
        """Create a single legend item widget."""
        item_widget = QWidget()
        item_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 2, 0, 2)
        item_layout.setSpacing(8)

        # Color indicator
        color_label = QLabel()
        color_label.setFixedSize(12, 12)
        color_label.setStyleSheet(
            f"background-color: {data.get('color', '#888')}; "
            f"border-radius: 2px;"
        )
        item_layout.addWidget(color_label)

        # Label
        label = QLabel(data.get('label', ''))
        label.setFont(QFont("Segoe UI", 9))
        label.setStyleSheet(f"color: {self._scheme.text};")
        item_layout.addWidget(label)

        item_layout.addStretch()

        # Value if present
        if 'value' in data:
            value_label = QLabel(f"${data['value']:,.2f}")
            value_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            value_label.setStyleSheet(f"color: {self._scheme.text};")
            item_layout.addWidget(value_label)

        return item_widget

    # =========================================================================
    # Public API
    # =========================================================================

    def set_config(self, config: ChartConfig):
        """Update chart configuration."""
        self._config = config
        self._apply_theme()
        self.update_chart()

    def set_dark_mode(self, dark: bool):
        """Set dark/light mode."""
        self._config.dark_mode = dark
        self._apply_theme()
        self.update_chart()

    def set_colors(self, colors: List[str]):
        """Set custom color palette."""
        self._config.custom_colors = colors
        self.update_chart()

    def set_data(self, data: List[Dict[str, Any]]):
        """
        Set chart data.

        Args:
            data: List of dicts with 'label' and 'value' keys
        """
        self._data = [
            ChartDataPoint(
                label=d.get('label', ''),
                value=float(d.get('value', 0)),
                color=d.get('color'),
                metadata=d.get('metadata', {})
            )
            for d in data
        ]
        self.update_chart()

        # Start animation
        if self._config.animation_type != AnimationType.NONE:
            self.start_animation(
                self._config.animation_type,
                self._config.animation_duration
            )

    def set_series(self, series: List[Dict[str, Any]]):
        """
        Set multi-series data.

        Args:
            series: List of series definitions
        """
        self._series = [
            ChartSeries(
                name=s.get('name', f'Series {i+1}'),
                data=[
                    ChartDataPoint(
                        label=d.get('label', ''),
                        value=float(d.get('value', d.get('y', 0))),
                        color=d.get('color')
                    )
                    for d in s.get('data', [])
                ],
                color=s.get('color'),
                line_style=s.get('line_style', 'solid'),
                line_width=s.get('line_width', 2),
                show_points=s.get('show_points', True),
                fill_area=s.get('fill_area', False)
            )
            for i, s in enumerate(series)
        ]
        self.update_chart()

    def clear(self):
        """Clear all data."""
        self._data = []
        self._series = []
        self._selected_items = []
        self.update_chart()

    def select_item(self, label: str):
        """Select an item by label."""
        if label not in self._selected_items:
            self._selected_items.append(label)
            self.selection_changed.emit(self._selected_items.copy())
            self.update()

    def deselect_item(self, label: str):
        """Deselect an item by label."""
        if label in self._selected_items:
            self._selected_items.remove(label)
            self.selection_changed.emit(self._selected_items.copy())
            self.update()

    def clear_selection(self):
        """Clear all selections."""
        self._selected_items = []
        self.selection_changed.emit([])
        self.update()

    def update_chart(self):
        """Update the chart display. Override in subclasses."""
        self._update_legend()
        self.update()

    def export_image(self, filepath: str, width: int = 800, height: int = 600):
        """Export chart as image."""
        from PyQt6.QtGui import QPixmap
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(self._scheme.background))
        self.render(pixmap)
        pixmap.save(filepath)


class DonutChart(BaseChart):
    """Donut chart variant of pie chart with center hole."""
    pass  # Implemented in pie_chart.py


# Export convenience functions
def create_chart(
    chart_type: ChartType,
    config: Optional[ChartConfig] = None,
    parent: Optional[QWidget] = None
) -> BaseChart:
    """
    Factory function to create chart widgets.

    Args:
        chart_type: Type of chart to create
        config: Chart configuration
        parent: Parent widget

    Returns:
        Chart widget instance
    """
    from .pie_chart import PieChart
    from .line_chart import LineChart
    from .bar_chart import BarChart
    from .progress_chart import ProgressChart

    chart_classes = {
        ChartType.PIE: PieChart,
        ChartType.LINE: LineChart,
        ChartType.BAR: BarChart,
        ChartType.PROGRESS: ProgressChart,
    }

    chart_class = chart_classes.get(chart_type, BaseChart)
    return chart_class(config=config, parent=parent)
