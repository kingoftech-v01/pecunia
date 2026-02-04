"""
Pie Chart Widget Module

Provides PieChart and DonutChart widgets for displaying category distributions.
Features: hover tooltips, click to filter, legend, smooth animations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QToolTip, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPointF, QRectF, QTimer,
    QPropertyAnimation, QEasingCurve, Property
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath,
    QConicalGradient, QRadialGradient, QLinearGradient
)

from typing import Optional, List, Dict, Any, Tuple
import math

from .charts import (
    BaseChart, ChartConfig, ChartDataPoint, ColorScheme,
    AnimationType, LegendPosition, ChartAnimationMixin
)


class PieChartCanvas(QWidget, ChartAnimationMixin):
    """
    Custom canvas widget for rendering pie/donut charts.

    Handles all painting and mouse interaction for the pie chart.
    """

    # Signals
    slice_hovered = pyqtSignal(int, str, float, float)  # index, label, value, percentage
    slice_clicked = pyqtSignal(int, str, float)  # index, label, value

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        donut: bool = False,
        donut_ratio: float = 0.5
    ):
        super().__init__(parent)

        self._data: List[Dict[str, Any]] = []
        self._scheme: Optional[ColorScheme] = None
        self._show_percentages = True
        self._show_labels = True
        self._hover_index = -1
        self._selected_indices: List[int] = []
        self._donut = donut
        self._donut_ratio = donut_ratio
        self._start_angle = 90  # Start from top
        self._animation_progress = 0.0
        self._explode_distance = 10
        self._shadow_enabled = True

        # Center text for donut
        self._center_title = ""
        self._center_value = ""

        self.setMouseTracking(True)
        self.setMinimumSize(150, 150)

    def set_data(
        self,
        data: List[Dict[str, Any]],
        scheme: ColorScheme,
        show_percentages: bool = True,
        show_labels: bool = True
    ):
        """Set chart data and appearance options."""
        self._data = data
        self._scheme = scheme
        self._show_percentages = show_percentages
        self._show_labels = show_labels
        self._hover_index = -1
        self.update()

    def set_donut_mode(self, enabled: bool, ratio: float = 0.5):
        """Enable/disable donut mode with inner radius ratio."""
        self._donut = enabled
        self._donut_ratio = max(0.1, min(0.9, ratio))
        self.update()

    def set_center_text(self, title: str, value: str = ""):
        """Set center text for donut chart."""
        self._center_title = title
        self._center_value = value
        self.update()

    def set_explode_distance(self, distance: int):
        """Set distance for exploded slices."""
        self._explode_distance = distance
        self.update()

    def set_selected(self, indices: List[int]):
        """Set selected slice indices."""
        self._selected_indices = indices
        self.update()

    def paintEvent(self, event):
        """Paint the pie/donut chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._data or not self._scheme:
            painter.setPen(QColor(self._scheme.text if self._scheme else "#333"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            return

        # Calculate dimensions
        margin = 30
        size = min(self.width(), self.height()) - 2 * margin
        if size <= 0:
            return

        x = (self.width() - size) // 2
        y = (self.height() - size) // 2
        rect = QRectF(x, y, size, size)
        center = rect.center()

        # Calculate total
        total = sum(d.get('value', 0) for d in self._data)
        if total == 0:
            return

        # Apply animation progress
        animated_total_angle = 360 * self._animation_progress

        # Draw shadow for non-donut charts
        if self._shadow_enabled and not self._donut:
            shadow_rect = rect.translated(3, 3)
            painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(shadow_rect)

        # Draw slices
        start_angle = self._start_angle * 16  # Qt uses 1/16th degrees

        for i, d in enumerate(self._data):
            value = d.get('value', 0)
            if value == 0:
                continue

            # Calculate span angle with animation
            full_span = value / total * 360
            span_angle = int(min(full_span, animated_total_angle) * 16)
            animated_total_angle -= full_span

            if span_angle <= 0:
                continue

            # Determine states
            is_hovered = (i == self._hover_index)
            is_selected = (i in self._selected_indices)

            # Get color
            color = QColor(d.get('color', '#888'))
            if is_hovered:
                color = color.lighter(115)
            elif is_selected:
                color = color.lighter(110)

            # Calculate offset for exploded slices
            draw_rect = rect
            if is_hovered or is_selected:
                mid_angle = (start_angle + span_angle / 2) / 16
                rad = math.radians(mid_angle)
                offset_x = self._explode_distance * math.cos(rad)
                offset_y = -self._explode_distance * math.sin(rad)
                draw_rect = rect.translated(offset_x, offset_y)

            # Draw slice
            painter.setBrush(QBrush(color))

            # Slice border
            if is_hovered or is_selected:
                painter.setPen(QPen(QColor(self._scheme.background), 3))
            else:
                painter.setPen(QPen(QColor(self._scheme.background), 2))

            if self._donut:
                # Draw donut slice using path
                path = self._create_donut_path(
                    draw_rect, start_angle, span_angle, self._donut_ratio
                )
                painter.drawPath(path)
            else:
                painter.drawPie(draw_rect, start_angle, span_angle)

            # Draw percentage label
            if self._show_percentages:
                percentage = d.get('percentage', value / total * 100)
                if percentage >= 5:  # Only show for slices >= 5%
                    self._draw_slice_label(
                        painter, rect, center, start_angle, span_angle,
                        size, percentage, d.get('label', '')
                    )

            start_angle += span_angle

        # Draw donut center
        if self._donut:
            self._draw_donut_center(painter, rect, center, size)

    def _create_donut_path(
        self,
        rect: QRectF,
        start_angle: int,
        span_angle: int,
        inner_ratio: float
    ) -> QPainterPath:
        """Create a donut slice path."""
        path = QPainterPath()

        center = rect.center()
        outer_radius = rect.width() / 2
        inner_radius = outer_radius * inner_ratio

        # Outer arc
        outer_rect = QRectF(
            center.x() - outer_radius,
            center.y() - outer_radius,
            outer_radius * 2,
            outer_radius * 2
        )

        # Inner arc
        inner_rect = QRectF(
            center.x() - inner_radius,
            center.y() - inner_radius,
            inner_radius * 2,
            inner_radius * 2
        )

        # Build path
        path.arcMoveTo(outer_rect, start_angle / 16)
        path.arcTo(outer_rect, start_angle / 16, span_angle / 16)

        # Line to inner arc
        end_angle = start_angle + span_angle
        path.arcTo(inner_rect, end_angle / 16, -span_angle / 16)

        path.closeSubpath()
        return path

    def _draw_slice_label(
        self,
        painter: QPainter,
        rect: QRectF,
        center: QPointF,
        start_angle: int,
        span_angle: int,
        size: float,
        percentage: float,
        label: str
    ):
        """Draw percentage/label on a slice."""
        mid_angle = (start_angle + span_angle / 2) / 16
        rad = math.radians(mid_angle)

        # Position label in middle of slice
        if self._donut:
            label_radius = size / 2 * (1 + self._donut_ratio) / 2
        else:
            label_radius = size / 3

        label_x = center.x() + label_radius * math.cos(rad)
        label_y = center.y() - label_radius * math.sin(rad)

        # Draw text
        painter.setPen(QColor('#FFFFFF'))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        text = f"{percentage:.0f}%"
        text_rect = QRectF(label_x - 30, label_y - 12, 60, 24)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_donut_center(
        self,
        painter: QPainter,
        rect: QRectF,
        center: QPointF,
        size: float
    ):
        """Draw the center of a donut chart."""
        inner_radius = (size / 2) * self._donut_ratio * 0.95
        inner_rect = QRectF(
            center.x() - inner_radius,
            center.y() - inner_radius,
            inner_radius * 2,
            inner_radius * 2
        )

        # Draw center circle
        painter.setBrush(QBrush(QColor(self._scheme.background)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(inner_rect)

        # Draw center text
        if self._center_title or self._center_value:
            painter.setPen(QColor(self._scheme.text))

            if self._center_value:
                painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
                painter.drawText(
                    inner_rect.adjusted(0, -10, 0, 0),
                    Qt.AlignmentFlag.AlignCenter,
                    self._center_value
                )

            if self._center_title:
                painter.setFont(QFont("Segoe UI", 9))
                painter.setPen(QColor(self._scheme.axis))
                painter.drawText(
                    inner_rect.adjusted(0, 15, 0, 0),
                    Qt.AlignmentFlag.AlignCenter,
                    self._center_title
                )

    def mouseMoveEvent(self, event):
        """Handle mouse move for hover detection."""
        index = self._get_slice_at_position(event.position())
        if index != self._hover_index:
            self._hover_index = index
            self.update()

            if index >= 0 and index < len(self._data):
                d = self._data[index]
                self.slice_hovered.emit(
                    index,
                    d.get('label', ''),
                    d.get('value', 0),
                    d.get('percentage', 0)
                )

                # Show tooltip
                tooltip_text = (
                    f"{d.get('label', '')}\n"
                    f"${d.get('value', 0):,.2f}\n"
                    f"({d.get('percentage', 0):.1f}%)"
                )
                QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
            else:
                self.slice_hovered.emit(-1, '', 0, 0)
                QToolTip.hideText()

    def mousePressEvent(self, event):
        """Handle mouse click."""
        if event.button() == Qt.MouseButton.LeftButton:
            index = self._get_slice_at_position(event.position())
            if index >= 0 and index < len(self._data):
                d = self._data[index]
                self.slice_clicked.emit(
                    index,
                    d.get('label', ''),
                    d.get('value', 0)
                )

                # Toggle selection
                if index in self._selected_indices:
                    self._selected_indices.remove(index)
                else:
                    self._selected_indices.append(index)
                self.update()

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover_index = -1
        self.update()
        QToolTip.hideText()
        self.slice_hovered.emit(-1, '', 0, 0)

    def _get_slice_at_position(self, pos: QPointF) -> int:
        """Get slice index at given position."""
        if not self._data:
            return -1

        # Calculate center and radius
        margin = 30
        size = min(self.width(), self.height()) - 2 * margin
        center_x = self.width() / 2
        center_y = self.height() / 2
        outer_radius = size / 2
        inner_radius = outer_radius * self._donut_ratio if self._donut else 0

        # Check distance from center
        dx = pos.x() - center_x
        dy = pos.y() - center_y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if within ring
        if distance > outer_radius or distance < inner_radius:
            return -1

        # Calculate angle
        angle = math.degrees(math.atan2(-dy, dx))
        if angle < 0:
            angle += 360
        angle = (self._start_angle - angle) % 360

        # Find slice
        total = sum(d.get('value', 0) for d in self._data)
        if total == 0:
            return -1

        current_angle = 0
        for i, d in enumerate(self._data):
            span = d.get('value', 0) / total * 360
            if current_angle <= angle < current_angle + span:
                return i
            current_angle += span

        return -1


class PieChart(BaseChart):
    """
    Pie chart widget for displaying category distributions.

    Features:
    - Smooth animations on data load
    - Hover tooltips with values
    - Click to select/filter categories
    - Customizable legend
    - Dark/light theme support
    - Export to image

    Usage:
        pie_chart = PieChart(config=ChartConfig(title="Expenses by Category"))
        pie_chart.set_data([
            {'label': 'Food', 'value': 500},
            {'label': 'Transport', 'value': 200},
            {'label': 'Entertainment', 'value': 150},
        ])
    """

    # Additional signals
    category_filtered = pyqtSignal(str)  # Emitted when clicking to filter

    def __init__(
        self,
        config: Optional[ChartConfig] = None,
        parent: Optional[QWidget] = None,
        show_percentages: bool = True,
        donut: bool = False,
        donut_ratio: float = 0.5
    ):
        self._show_percentages = show_percentages
        self._donut = donut
        self._donut_ratio = donut_ratio

        super().__init__(config, parent)

    def _setup_base_ui(self):
        """Setup pie chart specific UI."""
        super()._setup_base_ui()

        # Create pie chart canvas
        self.canvas = PieChartCanvas(
            parent=self.chart_container,
            donut=self._donut,
            donut_ratio=self._donut_ratio
        )
        self.canvas.slice_hovered.connect(self._on_slice_hover)
        self.canvas.slice_clicked.connect(self._on_slice_click)

        # Layout canvas in chart container
        canvas_layout = QVBoxLayout(self.chart_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.canvas)

    def _on_slice_hover(self, index: int, label: str, value: float, percentage: float):
        """Handle slice hover event."""
        if index >= 0:
            self.item_hovered.emit(label, value)
            self._hovered_item = label
        else:
            self._hovered_item = None

    def _on_slice_click(self, index: int, label: str, value: float):
        """Handle slice click event."""
        self.item_clicked.emit(label, value)
        self.category_filtered.emit(label)

        # Update selection
        if label in self._selected_items:
            self._selected_items.remove(label)
        else:
            self._selected_items.append(label)
        self.selection_changed.emit(self._selected_items.copy())

    def update_chart(self):
        """Update the pie chart with current data."""
        super().update_chart()

        if not hasattr(self, 'canvas'):
            return

        # Calculate percentages
        total = sum(dp.value for dp in self._data)
        colors = self._config.get_colors()

        chart_data = []
        for i, dp in enumerate(self._data):
            chart_data.append({
                'label': dp.label,
                'value': dp.value,
                'color': dp.color or colors[i % len(colors)],
                'percentage': (dp.value / total * 100) if total > 0 else 0,
                'metadata': dp.metadata
            })

        self.canvas.set_data(
            chart_data,
            self._scheme,
            self._show_percentages
        )

        # Start animation
        if self._config.animation_type != AnimationType.NONE:
            self.canvas._animation_progress = 0.0
            self.canvas.start_animation(
                self._config.animation_type,
                self._config.animation_duration
            )
        else:
            self.canvas._animation_progress = 1.0

    def set_donut_mode(self, enabled: bool, ratio: float = 0.5):
        """Enable/disable donut mode."""
        self._donut = enabled
        self._donut_ratio = ratio
        if hasattr(self, 'canvas'):
            self.canvas.set_donut_mode(enabled, ratio)

    def set_center_text(self, title: str, value: str = ""):
        """Set center text for donut chart."""
        if hasattr(self, 'canvas'):
            self.canvas.set_center_text(title, value)

    def set_show_percentages(self, show: bool):
        """Show/hide percentage labels."""
        self._show_percentages = show
        self.update_chart()

    def get_selected_categories(self) -> List[str]:
        """Get list of selected category labels."""
        return self._selected_items.copy()


class DonutChart(PieChart):
    """
    Donut chart variant with configurable inner radius.

    Extends PieChart with donut-specific features:
    - Center text display (title + value)
    - Configurable inner radius

    Usage:
        donut = DonutChart(config=ChartConfig(title="Budget"))
        donut.set_center_text("Total", "$1,500")
        donut.set_data([...])
    """

    def __init__(
        self,
        config: Optional[ChartConfig] = None,
        parent: Optional[QWidget] = None,
        inner_radius: float = 0.6
    ):
        super().__init__(
            config=config,
            parent=parent,
            show_percentages=True,
            donut=True,
            donut_ratio=inner_radius
        )

    def set_inner_radius(self, ratio: float):
        """Set the inner radius ratio (0.1 to 0.9)."""
        self._donut_ratio = max(0.1, min(0.9, ratio))
        self.set_donut_mode(True, self._donut_ratio)


# Convenience functions
def create_pie_chart(
    title: str = "",
    data: Optional[List[Dict[str, Any]]] = None,
    dark_mode: bool = False,
    show_legend: bool = True
) -> PieChart:
    """Create a configured pie chart widget."""
    config = ChartConfig(
        title=title,
        dark_mode=dark_mode,
        show_legend=show_legend,
        animation_type=AnimationType.GROW
    )
    chart = PieChart(config=config)
    if data:
        chart.set_data(data)
    return chart


def create_donut_chart(
    title: str = "",
    center_title: str = "",
    center_value: str = "",
    data: Optional[List[Dict[str, Any]]] = None,
    dark_mode: bool = False,
    inner_radius: float = 0.6
) -> DonutChart:
    """Create a configured donut chart widget."""
    config = ChartConfig(
        title=title,
        dark_mode=dark_mode,
        animation_type=AnimationType.GROW
    )
    chart = DonutChart(config=config, inner_radius=inner_radius)
    chart.set_center_text(center_title, center_value)
    if data:
        chart.set_data(data)
    return chart
