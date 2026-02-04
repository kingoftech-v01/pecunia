"""
Line Chart Widget Module

Provides LineChart widget for displaying time series data and trends.
Features: multiple lines, zoom/pan, tooltips, smooth animations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QToolTip, QScrollBar, QMenu
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPointF, QRectF, QLineF,
    QPropertyAnimation, QEasingCurve, Property, QTimer
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath,
    QLinearGradient, QPolygonF, QWheelEvent, QMouseEvent,
    QCursor, QAction
)

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import math

from .charts import (
    BaseChart, ChartConfig, ChartDataPoint, ChartSeries, ColorScheme,
    AnimationType, LegendPosition, ChartAnimationMixin,
    LIGHT_SCHEME, DARK_SCHEME
)

# Try to import pyqtgraph for advanced features
try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False


@dataclass
class LineChartConfig:
    """Configuration specific to line charts."""
    show_points: bool = True
    point_size: int = 8
    line_width: int = 2
    fill_area: bool = False
    fill_opacity: float = 0.3
    show_grid: bool = True
    grid_opacity: float = 0.3
    smooth_lines: bool = True
    show_value_labels: bool = False
    enable_zoom: bool = True
    enable_pan: bool = True
    min_zoom: float = 0.5
    max_zoom: float = 5.0


class LineChartCanvas(QWidget, ChartAnimationMixin):
    """
    Custom canvas widget for rendering line charts.

    Features:
    - Multiple data series
    - Smooth line interpolation
    - Area fill option
    - Interactive zoom and pan
    - Crosshair cursor
    - Value tooltips
    """

    # Signals
    point_hovered = pyqtSignal(str, int, float, float)  # series, index, x, y
    point_clicked = pyqtSignal(str, int, float, float)  # series, index, x, y
    range_changed = pyqtSignal(float, float, float, float)  # x_min, x_max, y_min, y_max

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._series: List[Dict[str, Any]] = []
        self._scheme: Optional[ColorScheme] = None
        self._config = LineChartConfig()
        self._x_labels: List[str] = []
        self._y_label: str = ""
        self._x_label: str = ""

        # View state
        self._zoom_level = 1.0
        self._pan_offset = QPointF(0, 0)
        self._view_x_min = 0.0
        self._view_x_max = 10.0
        self._view_y_min = 0.0
        self._view_y_max = 100.0

        # Interaction state
        self._hover_point: Optional[Tuple[str, int]] = None
        self._is_panning = False
        self._pan_start: Optional[QPointF] = None
        self._crosshair_pos: Optional[QPointF] = None

        # Animation
        self._animation_progress = 0.0

        self.setMouseTracking(True)
        self.setMinimumSize(200, 150)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)

    def set_data(
        self,
        series: List[Dict[str, Any]],
        scheme: ColorScheme,
        config: Optional[LineChartConfig] = None
    ):
        """Set chart data and configuration."""
        self._series = series
        self._scheme = scheme
        if config:
            self._config = config

        # Auto-calculate view bounds
        self._auto_scale()
        self.update()

    def set_x_labels(self, labels: List[str]):
        """Set labels for x-axis."""
        self._x_labels = labels
        self.update()

    def set_axis_labels(self, x_label: str = "", y_label: str = ""):
        """Set axis labels."""
        self._x_label = x_label
        self._y_label = y_label
        self.update()

    def _auto_scale(self):
        """Auto-calculate view bounds from data."""
        if not self._series:
            return

        x_values = []
        y_values = []

        for series in self._series:
            data = series.get('data', [])
            for i, d in enumerate(data):
                x_values.append(d.get('x', i))
                y_values.append(d.get('y', d.get('value', 0)))

        if x_values and y_values:
            x_margin = (max(x_values) - min(x_values)) * 0.05 or 1
            y_margin = (max(y_values) - min(y_values)) * 0.1 or 10

            self._view_x_min = min(x_values) - x_margin
            self._view_x_max = max(x_values) + x_margin
            self._view_y_min = max(0, min(y_values) - y_margin)
            self._view_y_max = max(y_values) + y_margin

    def _data_to_screen(self, x: float, y: float) -> QPointF:
        """Convert data coordinates to screen coordinates."""
        margin = 50
        plot_width = self.width() - 2 * margin
        plot_height = self.height() - 2 * margin

        x_range = self._view_x_max - self._view_x_min
        y_range = self._view_y_max - self._view_y_min

        if x_range == 0:
            x_range = 1
        if y_range == 0:
            y_range = 1

        screen_x = margin + (x - self._view_x_min) / x_range * plot_width
        screen_y = margin + (1 - (y - self._view_y_min) / y_range) * plot_height

        return QPointF(screen_x, screen_y)

    def _screen_to_data(self, pos: QPointF) -> Tuple[float, float]:
        """Convert screen coordinates to data coordinates."""
        margin = 50
        plot_width = self.width() - 2 * margin
        plot_height = self.height() - 2 * margin

        x_range = self._view_x_max - self._view_x_min
        y_range = self._view_y_max - self._view_y_min

        data_x = self._view_x_min + (pos.x() - margin) / plot_width * x_range
        data_y = self._view_y_min + (1 - (pos.y() - margin) / plot_height) * y_range

        return data_x, data_y

    def paintEvent(self, event):
        """Paint the line chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._scheme:
            return

        # Fill background
        painter.fillRect(self.rect(), QColor(self._scheme.background))

        margin = 50
        plot_rect = QRectF(
            margin, margin,
            self.width() - 2 * margin,
            self.height() - 2 * margin
        )

        # Draw grid
        if self._config.show_grid:
            self._draw_grid(painter, plot_rect)

        # Draw axes
        self._draw_axes(painter, plot_rect)

        # Draw series
        if self._series:
            for series in self._series:
                self._draw_series(painter, series, plot_rect)

        # Draw crosshair
        if self._crosshair_pos and plot_rect.contains(self._crosshair_pos):
            self._draw_crosshair(painter, plot_rect)

    def _draw_grid(self, painter: QPainter, plot_rect: QRectF):
        """Draw grid lines."""
        grid_color = QColor(self._scheme.grid)
        grid_color.setAlphaF(self._config.grid_opacity)
        painter.setPen(QPen(grid_color, 1, Qt.PenStyle.DotLine))

        # Horizontal grid lines (5 lines)
        for i in range(6):
            y = plot_rect.top() + plot_rect.height() * i / 5
            painter.drawLine(QLineF(plot_rect.left(), y, plot_rect.right(), y))

        # Vertical grid lines
        num_x_lines = min(10, len(self._x_labels)) if self._x_labels else 10
        for i in range(num_x_lines + 1):
            x = plot_rect.left() + plot_rect.width() * i / num_x_lines
            painter.drawLine(QLineF(x, plot_rect.top(), x, plot_rect.bottom()))

    def _draw_axes(self, painter: QPainter, plot_rect: QRectF):
        """Draw axes and labels."""
        axis_color = QColor(self._scheme.axis)
        text_color = QColor(self._scheme.text)

        # Draw axes lines
        painter.setPen(QPen(axis_color, 2))
        painter.drawLine(QLineF(
            plot_rect.left(), plot_rect.bottom(),
            plot_rect.right(), plot_rect.bottom()
        ))
        painter.drawLine(QLineF(
            plot_rect.left(), plot_rect.top(),
            plot_rect.left(), plot_rect.bottom()
        ))

        # Draw Y-axis labels
        painter.setPen(text_color)
        painter.setFont(QFont("Segoe UI", 8))

        y_range = self._view_y_max - self._view_y_min
        for i in range(6):
            y = plot_rect.top() + plot_rect.height() * i / 5
            value = self._view_y_max - (y_range * i / 5)
            label = f"${value:,.0f}" if value >= 1000 else f"${value:,.2f}"
            painter.drawText(
                QRectF(0, y - 10, plot_rect.left() - 5, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label
            )

        # Draw X-axis labels
        if self._x_labels:
            num_labels = min(10, len(self._x_labels))
            step = max(1, len(self._x_labels) // num_labels)
            for i in range(0, len(self._x_labels), step):
                x = plot_rect.left() + plot_rect.width() * i / max(1, len(self._x_labels) - 1)
                label = self._x_labels[i]
                painter.drawText(
                    QRectF(x - 30, plot_rect.bottom() + 5, 60, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    label
                )

        # Draw axis titles
        if self._y_label:
            painter.save()
            painter.translate(15, plot_rect.center().y())
            painter.rotate(-90)
            painter.drawText(QRectF(-50, -10, 100, 20), Qt.AlignmentFlag.AlignCenter, self._y_label)
            painter.restore()

        if self._x_label:
            painter.drawText(
                QRectF(plot_rect.left(), self.height() - 20, plot_rect.width(), 20),
                Qt.AlignmentFlag.AlignCenter,
                self._x_label
            )

    def _draw_series(self, painter: QPainter, series: Dict[str, Any], plot_rect: QRectF):
        """Draw a single data series."""
        data = series.get('data', [])
        if not data:
            return

        color = QColor(series.get('color', '#2196F3'))
        line_width = series.get('line_width', self._config.line_width)
        show_points = series.get('show_points', self._config.show_points)
        fill_area = series.get('fill_area', self._config.fill_area)

        # Build path
        path = QPainterPath()
        points = []

        for i, d in enumerate(data):
            x = d.get('x', i)
            y = d.get('y', d.get('value', 0))

            # Apply animation
            animated_y = y * self._animation_progress
            screen_point = self._data_to_screen(x, animated_y)
            points.append(screen_point)

            if i == 0:
                path.moveTo(screen_point)
            else:
                if self._config.smooth_lines and i > 0:
                    # Smooth curve using cubic bezier
                    prev = points[i - 1]
                    ctrl1 = QPointF(prev.x() + (screen_point.x() - prev.x()) / 3, prev.y())
                    ctrl2 = QPointF(screen_point.x() - (screen_point.x() - prev.x()) / 3, screen_point.y())
                    path.cubicTo(ctrl1, ctrl2, screen_point)
                else:
                    path.lineTo(screen_point)

        # Draw fill area
        if fill_area and points:
            fill_path = QPainterPath(path)
            fill_path.lineTo(points[-1].x(), plot_rect.bottom())
            fill_path.lineTo(points[0].x(), plot_rect.bottom())
            fill_path.closeSubpath()

            gradient = QLinearGradient(0, plot_rect.top(), 0, plot_rect.bottom())
            fill_color = QColor(color)
            fill_color.setAlphaF(self._config.fill_opacity)
            gradient.setColorAt(0, fill_color)
            fill_color.setAlphaF(0.05)
            gradient.setColorAt(1, fill_color)

            painter.fillPath(fill_path, QBrush(gradient))

        # Draw line
        pen = QPen(color, line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Draw points
        if show_points:
            point_radius = self._config.point_size / 2
            series_name = series.get('name', '')

            for i, point in enumerate(points):
                is_hovered = (
                    self._hover_point is not None and
                    self._hover_point[0] == series_name and
                    self._hover_point[1] == i
                )

                if is_hovered:
                    # Larger point on hover
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(QColor(self._scheme.background), 3))
                    painter.drawEllipse(point, point_radius + 3, point_radius + 3)
                else:
                    painter.setBrush(QBrush(QColor(self._scheme.background)))
                    painter.setPen(QPen(color, 2))
                    painter.drawEllipse(point, point_radius, point_radius)

    def _draw_crosshair(self, painter: QPainter, plot_rect: QRectF):
        """Draw crosshair at cursor position."""
        if not self._crosshair_pos:
            return

        crosshair_color = QColor(self._scheme.axis)
        crosshair_color.setAlphaF(0.5)
        painter.setPen(QPen(crosshair_color, 1, Qt.PenStyle.DashLine))

        # Vertical line
        painter.drawLine(QLineF(
            self._crosshair_pos.x(), plot_rect.top(),
            self._crosshair_pos.x(), plot_rect.bottom()
        ))

        # Horizontal line
        painter.drawLine(QLineF(
            plot_rect.left(), self._crosshair_pos.y(),
            plot_rect.right(), self._crosshair_pos.y()
        ))

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse movement."""
        pos = event.position()

        # Update crosshair
        margin = 50
        plot_rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        if plot_rect.contains(pos):
            self._crosshair_pos = pos
        else:
            self._crosshair_pos = None

        # Handle panning
        if self._is_panning and self._pan_start and self._config.enable_pan:
            delta = pos - self._pan_start
            x_range = self._view_x_max - self._view_x_min
            y_range = self._view_y_max - self._view_y_min

            dx = -delta.x() / (self.width() - 2 * margin) * x_range
            dy = delta.y() / (self.height() - 2 * margin) * y_range

            self._view_x_min += dx
            self._view_x_max += dx
            self._view_y_min += dy
            self._view_y_max += dy

            self._pan_start = pos
            self.range_changed.emit(
                self._view_x_min, self._view_x_max,
                self._view_y_min, self._view_y_max
            )

        # Find nearest point for hover
        nearest_point = self._find_nearest_point(pos)
        if nearest_point != self._hover_point:
            self._hover_point = nearest_point
            if nearest_point:
                series_name, idx = nearest_point
                # Find the data point
                for series in self._series:
                    if series.get('name') == series_name:
                        data = series.get('data', [])
                        if idx < len(data):
                            d = data[idx]
                            x = d.get('x', idx)
                            y = d.get('y', d.get('value', 0))
                            self.point_hovered.emit(series_name, idx, x, y)

                            # Show tooltip
                            x_label = self._x_labels[int(x)] if int(x) < len(self._x_labels) else str(x)
                            tooltip = f"{series_name}\n{x_label}: ${y:,.2f}"
                            QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                        break
            else:
                QToolTip.hideText()

        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._config.enable_pan:
                self._is_panning = True
                self._pan_start = event.position()
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

            # Check for point click
            if self._hover_point:
                series_name, idx = self._hover_point
                for series in self._series:
                    if series.get('name') == series_name:
                        data = series.get('data', [])
                        if idx < len(data):
                            d = data[idx]
                            self.point_clicked.emit(
                                series_name, idx,
                                d.get('x', idx),
                                d.get('y', d.get('value', 0))
                            )
                        break

        elif event.button() == Qt.MouseButton.RightButton:
            # Context menu
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self._pan_start = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if not self._config.enable_zoom:
            return

        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9

        # Get mouse position in data coordinates
        pos = event.position()
        data_x, data_y = self._screen_to_data(pos)

        # Calculate new bounds
        x_range = self._view_x_max - self._view_x_min
        y_range = self._view_y_max - self._view_y_min

        new_x_range = x_range / zoom_factor
        new_y_range = y_range / zoom_factor

        # Clamp zoom level
        if zoom_factor > 1:  # Zoom in
            if new_x_range < x_range / self._config.max_zoom:
                return
        else:  # Zoom out
            if new_x_range > x_range / self._config.min_zoom:
                return

        # Center zoom on mouse position
        x_ratio = (data_x - self._view_x_min) / x_range
        y_ratio = (data_y - self._view_y_min) / y_range

        self._view_x_min = data_x - new_x_range * x_ratio
        self._view_x_max = data_x + new_x_range * (1 - x_ratio)
        self._view_y_min = data_y - new_y_range * y_ratio
        self._view_y_max = data_y + new_y_range * (1 - y_ratio)

        self.range_changed.emit(
            self._view_x_min, self._view_x_max,
            self._view_y_min, self._view_y_max
        )
        self.update()

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._crosshair_pos = None
        self._hover_point = None
        QToolTip.hideText()
        self.update()

    def _find_nearest_point(self, pos: QPointF) -> Optional[Tuple[str, int]]:
        """Find the nearest data point to the given position."""
        if not self._series:
            return None

        nearest = None
        min_dist = 20  # Threshold in pixels

        for series in self._series:
            data = series.get('data', [])
            series_name = series.get('name', '')

            for i, d in enumerate(data):
                x = d.get('x', i)
                y = d.get('y', d.get('value', 0))
                screen_point = self._data_to_screen(x, y * self._animation_progress)

                dist = math.sqrt(
                    (pos.x() - screen_point.x()) ** 2 +
                    (pos.y() - screen_point.y()) ** 2
                )

                if dist < min_dist:
                    min_dist = dist
                    nearest = (series_name, i)

        return nearest

    def _show_context_menu(self, pos):
        """Show context menu."""
        menu = QMenu(self)

        reset_action = QAction("Reset View", self)
        reset_action.triggered.connect(self._reset_view)
        menu.addAction(reset_action)

        menu.exec(pos)

    def _reset_view(self):
        """Reset view to auto-scaled bounds."""
        self._auto_scale()
        self.update()

    def reset_zoom(self):
        """Public method to reset zoom."""
        self._reset_view()


class LineChart(BaseChart):
    """
    Line chart widget for displaying time series data.

    Features:
    - Multiple data series with different styles
    - Interactive zoom and pan
    - Hover tooltips with values
    - Crosshair cursor
    - Smooth line interpolation
    - Area fill option
    - Dark/light theme support

    Usage:
        line_chart = LineChart(config=ChartConfig(title="Monthly Spending"))
        line_chart.set_x_labels(['Jan', 'Feb', 'Mar', 'Apr', 'May'])
        line_chart.set_series([
            {
                'name': 'Expenses',
                'color': '#F44336',
                'data': [
                    {'x': 0, 'y': 1500},
                    {'x': 1, 'y': 1800},
                    {'x': 2, 'y': 1200},
                ]
            },
            {
                'name': 'Income',
                'color': '#4CAF50',
                'data': [...]
            }
        ])
    """

    # Additional signals
    zoom_changed = pyqtSignal(float)  # zoom level

    def __init__(
        self,
        config: Optional[ChartConfig] = None,
        parent: Optional[QWidget] = None,
        line_config: Optional[LineChartConfig] = None
    ):
        self._line_config = line_config or LineChartConfig()
        super().__init__(config, parent)

    def _setup_base_ui(self):
        """Setup line chart specific UI."""
        super()._setup_base_ui()

        # Create line chart canvas
        self.canvas = LineChartCanvas(parent=self.chart_container)
        self.canvas.point_hovered.connect(self._on_point_hover)
        self.canvas.point_clicked.connect(self._on_point_click)
        self.canvas.range_changed.connect(self._on_range_change)

        # Layout canvas
        canvas_layout = QVBoxLayout(self.chart_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.canvas)

    def _on_point_hover(self, series: str, index: int, x: float, y: float):
        """Handle point hover."""
        self.item_hovered.emit(f"{series}[{index}]", y)

    def _on_point_click(self, series: str, index: int, x: float, y: float):
        """Handle point click."""
        self.item_clicked.emit(f"{series}[{index}]", y)

    def _on_range_change(self, x_min: float, x_max: float, y_min: float, y_max: float):
        """Handle view range change."""
        pass  # Can be extended for sync between multiple charts

    def _get_legend_data(self) -> List[Dict[str, Any]]:
        """Get legend data from series."""
        colors = self._config.get_colors()
        return [
            {
                'label': s.name,
                'color': s.color or colors[i % len(colors)]
            }
            for i, s in enumerate(self._series)
        ]

    def update_chart(self):
        """Update the line chart."""
        super().update_chart()

        if not hasattr(self, 'canvas'):
            return

        colors = self._config.get_colors()

        # Convert series to canvas format
        canvas_series = []
        for i, s in enumerate(self._series):
            canvas_series.append({
                'name': s.name,
                'color': s.color or colors[i % len(colors)],
                'data': [
                    {'x': j, 'y': dp.value, 'label': dp.label}
                    for j, dp in enumerate(s.data)
                ],
                'line_width': s.line_width,
                'show_points': s.show_points,
                'fill_area': s.fill_area
            })

        self.canvas.set_data(canvas_series, self._scheme, self._line_config)

        # Animation
        if self._config.animation_type != AnimationType.NONE:
            self.canvas._animation_progress = 0.0
            self.canvas.start_animation(
                self._config.animation_type,
                self._config.animation_duration
            )
        else:
            self.canvas._animation_progress = 1.0

    def set_x_labels(self, labels: List[str]):
        """Set x-axis labels."""
        if hasattr(self, 'canvas'):
            self.canvas.set_x_labels(labels)

    def set_axis_labels(self, x_label: str = "", y_label: str = ""):
        """Set axis labels."""
        if hasattr(self, 'canvas'):
            self.canvas.set_axis_labels(x_label, y_label)

    def set_line_config(self, config: LineChartConfig):
        """Update line chart configuration."""
        self._line_config = config
        self.update_chart()

    def enable_fill_area(self, enabled: bool = True, opacity: float = 0.3):
        """Enable/disable area fill under lines."""
        self._line_config.fill_area = enabled
        self._line_config.fill_opacity = opacity
        self.update_chart()

    def enable_smooth_lines(self, enabled: bool = True):
        """Enable/disable smooth line interpolation."""
        self._line_config.smooth_lines = enabled
        self.update_chart()

    def reset_zoom(self):
        """Reset zoom to default."""
        if hasattr(self, 'canvas'):
            self.canvas.reset_zoom()


# Convenience function
def create_line_chart(
    title: str = "",
    x_labels: Optional[List[str]] = None,
    series: Optional[List[Dict[str, Any]]] = None,
    dark_mode: bool = False,
    fill_area: bool = False
) -> LineChart:
    """Create a configured line chart widget."""
    config = ChartConfig(
        title=title,
        dark_mode=dark_mode,
        animation_type=AnimationType.GROW
    )
    line_config = LineChartConfig(fill_area=fill_area)

    chart = LineChart(config=config, line_config=line_config)

    if x_labels:
        chart.set_x_labels(x_labels)
    if series:
        chart.set_series(series)

    return chart
