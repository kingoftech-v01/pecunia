"""
Table Delegates Module

Custom QStyledItemDelegate implementations for rich table cell rendering:
- AmountDelegate: Colored positive/negative amounts
- DateDelegate: Formatted dates with calendar popup
- CategoryDelegate: Icon + colored name
- ProgressDelegate: Visual progress bar
- ActionDelegate: Edit/Delete action buttons
"""

from PyQt6.QtWidgets import (
    QStyledItemDelegate, QWidget, QStyleOptionViewItem, QStyle,
    QApplication, QPushButton, QHBoxLayout, QLineEdit, QDateEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar, QLabel,
    QStyleOptionProgressBar, QToolButton, QMenu
)
from PyQt6.QtCore import (
    Qt, QModelIndex, QRect, QSize, QPoint, QDate, QEvent,
    pyqtSignal, QObject, QAbstractItemModel
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QIcon,
    QPalette, QPixmap, QPainterPath, QLinearGradient
)
from typing import Optional, Dict, Any, Callable, List, Tuple
from datetime import datetime, date
from decimal import Decimal


# =============================================================================
# Amount Delegate - Colored Currency Display
# =============================================================================

class AmountDelegate(QStyledItemDelegate):
    """
    Delegate for displaying monetary amounts with color coding.

    Features:
    - Green color for positive amounts (income)
    - Red color for negative amounts (expenses)
    - Currency symbol formatting
    - Right-aligned display
    - Optional sign prefix (+/-)
    """

    def __init__(self,
                 currency_symbol: str = "$",
                 positive_color: str = "#81C784",
                 negative_color: str = "#E57373",
                 zero_color: str = "#9E9E9E",
                 show_sign: bool = False,
                 decimal_places: int = 2,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.currency_symbol = currency_symbol
        self.positive_color = QColor(positive_color)
        self.negative_color = QColor(negative_color)
        self.zero_color = QColor(zero_color)
        self.show_sign = show_sign
        self.decimal_places = decimal_places

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the amount with appropriate color."""
        painter.save()

        # Get value
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            value = index.data(Qt.ItemDataRole.DisplayRole)

        # Parse numeric value
        try:
            num_value = float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            num_value = 0.0

        # Determine color
        if num_value > 0:
            color = self.positive_color
        elif num_value < 0:
            color = self.negative_color
        else:
            color = self.zero_color

        # Format text
        if self.show_sign and num_value > 0:
            text = f"+{self.currency_symbol}{abs(num_value):,.{self.decimal_places}f}"
        elif num_value < 0:
            text = f"-{self.currency_symbol}{abs(num_value):,.{self.decimal_places}f}"
        else:
            text = f"{self.currency_symbol}{abs(num_value):,.{self.decimal_places}f}"

        # Draw background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            color = option.palette.highlightedText().color()

        # Draw text
        painter.setPen(color)
        font = painter.font()
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)

        text_rect = option.rect.adjusted(4, 0, -8, 0)
        painter.drawText(text_rect,
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                         text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        return QSize(100, 32)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        """Create a double spin box editor."""
        editor = QDoubleSpinBox(parent)
        editor.setDecimals(self.decimal_places)
        editor.setMinimum(-999999999.99)
        editor.setMaximum(999999999.99)
        editor.setPrefix(self.currency_symbol)
        return editor

    def setEditorData(self, editor: QDoubleSpinBox, index: QModelIndex):
        """Set editor data from model."""
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            value = index.data(Qt.ItemDataRole.EditRole)
        try:
            editor.setValue(float(value) if value else 0.0)
        except (ValueError, TypeError):
            editor.setValue(0.0)

    def setModelData(self, editor: QDoubleSpinBox, model: QAbstractItemModel,
                     index: QModelIndex):
        """Set model data from editor."""
        model.setData(index, editor.value(), Qt.ItemDataRole.EditRole)


# =============================================================================
# Date Delegate - Formatted Date Display
# =============================================================================

class DateDelegate(QStyledItemDelegate):
    """
    Delegate for displaying and editing dates.

    Features:
    - Customizable date format
    - Calendar popup for editing
    - Relative date display (Today, Yesterday, etc.)
    - Highlighted overdue dates
    """

    def __init__(self,
                 display_format: str = "%Y-%m-%d",
                 show_relative: bool = False,
                 highlight_past: bool = False,
                 past_color: str = "#E57373",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.display_format = display_format
        self.show_relative = show_relative
        self.highlight_past = highlight_past
        self.past_color = QColor(past_color)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the date."""
        painter.save()

        # Get value
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            value = index.data(Qt.ItemDataRole.DisplayRole)

        # Parse date
        date_value = self._parse_date(value)

        # Format display text
        if date_value:
            if self.show_relative:
                text = self._get_relative_text(date_value)
            else:
                text = date_value.strftime(self.display_format)
        else:
            text = str(value) if value else ""

        # Determine color
        text_color = option.palette.text().color()

        if self.highlight_past and date_value:
            today = date.today()
            if date_value < today:
                text_color = self.past_color

        # Draw background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_color = option.palette.highlightedText().color()

        # Draw text
        painter.setPen(text_color)
        text_rect = option.rect.adjusted(8, 0, -8, 0)
        painter.drawText(text_rect,
                         Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                         text)

        painter.restore()

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse value to date object."""
        if isinstance(value, datetime):
            return value.date()
        elif isinstance(value, date):
            return value
        elif isinstance(value, str):
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    return datetime.strptime(value.split("T")[0], fmt.split("T")[0]).date()
                except ValueError:
                    continue
        return None

    def _get_relative_text(self, date_value: date) -> str:
        """Get relative date text."""
        today = date.today()
        delta = (date_value - today).days

        if delta == 0:
            return "Today"
        elif delta == -1:
            return "Yesterday"
        elif delta == 1:
            return "Tomorrow"
        elif -7 <= delta < 0:
            return f"{abs(delta)} days ago"
        elif 0 < delta <= 7:
            return f"In {delta} days"
        else:
            return date_value.strftime(self.display_format)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        return QSize(100, 32)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        """Create a date edit widget."""
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor

    def setEditorData(self, editor: QDateEdit, index: QModelIndex):
        """Set editor data from model."""
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            value = index.data(Qt.ItemDataRole.EditRole)

        date_value = self._parse_date(value)
        if date_value:
            editor.setDate(QDate(date_value.year, date_value.month, date_value.day))
        else:
            editor.setDate(QDate.currentDate())

    def setModelData(self, editor: QDateEdit, model: QAbstractItemModel,
                     index: QModelIndex):
        """Set model data from editor."""
        qdate = editor.date()
        py_date = date(qdate.year(), qdate.month(), qdate.day())
        model.setData(index, py_date, Qt.ItemDataRole.EditRole)


# =============================================================================
# Category Delegate - Icon + Colored Name
# =============================================================================

class CategoryDelegate(QStyledItemDelegate):
    """
    Delegate for displaying categories with icon and color.

    Features:
    - Category color indicator (dot or badge)
    - Optional category icon
    - Colored text based on category type
    - Dropdown for editing
    """

    def __init__(self,
                 show_color_dot: bool = True,
                 dot_size: int = 10,
                 categories: Optional[List[Dict[str, Any]]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.show_color_dot = show_color_dot
        self.dot_size = dot_size
        self.categories = categories or []
        self._category_map: Dict[str, Dict[str, Any]] = {}
        self._update_category_map()

    def _update_category_map(self):
        """Update category lookup map."""
        self._category_map = {
            cat.get("name", ""): cat for cat in self.categories
        }

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Update available categories."""
        self.categories = categories
        self._update_category_map()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the category with icon and color."""
        painter.save()

        # Get category data
        display_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        user_data = index.data(Qt.ItemDataRole.UserRole)

        # Get category info
        category_info = {}
        if isinstance(user_data, dict):
            category_info = user_data
        elif display_text in self._category_map:
            category_info = self._category_map[display_text]

        color = QColor(category_info.get("color", "#888888"))
        icon = category_info.get("icon")

        # Draw background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        rect = option.rect
        x_offset = 8

        # Draw color dot
        if self.show_color_dot:
            dot_y = rect.top() + (rect.height() - self.dot_size) // 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(rect.left() + x_offset, dot_y,
                                self.dot_size, self.dot_size)
            x_offset += self.dot_size + 8

        # Draw icon if available
        if icon and isinstance(icon, QIcon):
            icon_size = 16
            icon_y = rect.top() + (rect.height() - icon_size) // 2
            icon.paint(painter, rect.left() + x_offset, icon_y,
                       icon_size, icon_size)
            x_offset += icon_size + 6

        # Draw text
        text_rect = QRect(
            rect.left() + x_offset,
            rect.top(),
            rect.width() - x_offset - 8,
            rect.height()
        )

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        painter.drawText(text_rect,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         display_text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        return QSize(150, 32)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        """Create a combo box editor."""
        editor = QComboBox(parent)
        for cat in self.categories:
            name = cat.get("name", "")
            color = cat.get("color", "#888888")
            # Create colored icon
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(color))
            editor.addItem(QIcon(pixmap), name)
        return editor

    def setEditorData(self, editor: QComboBox, index: QModelIndex):
        """Set editor data from model."""
        value = index.data(Qt.ItemDataRole.DisplayRole)
        idx = editor.findText(str(value) if value else "")
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model: QAbstractItemModel,
                     index: QModelIndex):
        """Set model data from editor."""
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)


# =============================================================================
# Progress Delegate - Visual Progress Bar
# =============================================================================

class ProgressDelegate(QStyledItemDelegate):
    """
    Delegate for displaying progress as a visual bar.

    Features:
    - Color-coded progress (green -> yellow -> orange -> red)
    - Percentage text overlay
    - Rounded corners
    - Gradient fill option
    - Support for values over 100%
    """

    def __init__(self,
                 bar_height: int = 18,
                 show_text: bool = True,
                 use_gradient: bool = True,
                 color_thresholds: Optional[List[Tuple[float, str]]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.bar_height = bar_height
        self.show_text = show_text
        self.use_gradient = use_gradient

        # Default color thresholds: (percentage, color)
        self.color_thresholds = color_thresholds or [
            (50, "#4CAF50"),   # Green - under 50%
            (75, "#FFC107"),   # Yellow - 50-75%
            (100, "#FF9800"),  # Orange - 75-100%
            (float('inf'), "#F44336")  # Red - over 100%
        ]

    def _get_color(self, progress: float) -> QColor:
        """Get color based on progress value."""
        for threshold, color in self.color_thresholds:
            if progress < threshold:
                return QColor(color)
        return QColor(self.color_thresholds[-1][1])

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the progress bar."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get value
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            value = index.data(Qt.ItemDataRole.DisplayRole)

        try:
            progress = float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            progress = 0.0

        # Calculate dimensions
        rect = option.rect
        padding = 4
        bar_rect = QRect(
            rect.left() + padding,
            rect.top() + (rect.height() - self.bar_height) // 2,
            rect.width() - 2 * padding,
            self.bar_height
        )

        # Draw background
        bg_path = QPainterPath()
        bg_path.addRoundedRect(bar_rect.x(), bar_rect.y(),
                               bar_rect.width(), bar_rect.height(), 4, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E8E8E8"))
        painter.drawPath(bg_path)

        # Draw progress fill
        if progress > 0:
            fill_width = int(bar_rect.width() * min(progress / 100, 1.0))
            color = self._get_color(progress)

            if self.use_gradient:
                gradient = QLinearGradient(bar_rect.left(), bar_rect.top(),
                                            bar_rect.left(), bar_rect.bottom())
                lighter = QColor(color)
                lighter.setAlpha(200)
                gradient.setColorAt(0, lighter)
                gradient.setColorAt(1, color)
                painter.setBrush(gradient)
            else:
                painter.setBrush(color)

            # Clip to rounded rect
            fill_rect = QRect(bar_rect.left(), bar_rect.top(),
                              fill_width, bar_rect.height())
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect.x(), fill_rect.y(),
                                     fill_rect.width(), fill_rect.height(), 4, 4)

            # Intersect with background shape
            painter.setClipPath(bg_path)
            painter.drawPath(fill_path)
            painter.setClipping(False)

        # Draw text
        if self.show_text:
            text = f"{progress:.0f}%" if progress <= 999 else ">999%"

            # Determine text color based on fill
            if progress >= 50:
                painter.setPen(Qt.GlobalColor.white)
            else:
                painter.setPen(QColor("#333333"))

            font = painter.font()
            font.setPointSize(9)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, text)

        # Draw border
        painter.setPen(QPen(QColor("#D0D0D0"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(bar_rect, 4, 4)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        return QSize(120, self.bar_height + 8)


# =============================================================================
# Action Delegate - Edit/Delete Buttons
# =============================================================================

class ActionDelegate(QStyledItemDelegate):
    """
    Delegate for displaying action buttons in table cells.

    Features:
    - Edit and Delete buttons
    - Customizable button icons
    - Hover effects
    - Click signal emission
    """

    # Class-level signals (to be connected via the delegate instance)
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    view_clicked = pyqtSignal(int)

    def __init__(self,
                 show_edit: bool = True,
                 show_delete: bool = True,
                 show_view: bool = False,
                 button_size: int = 24,
                 button_spacing: int = 4,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.show_edit = show_edit
        self.show_delete = show_delete
        self.show_view = show_view
        self.button_size = button_size
        self.button_spacing = button_spacing

        # Track hover state
        self._hover_row = -1
        self._hover_button = -1  # 0=view, 1=edit, 2=delete

        # Button colors
        self.edit_color = QColor("#2196F3")
        self.delete_color = QColor("#F44336")
        self.view_color = QColor("#4CAF50")
        self.hover_color = QColor("#E0E0E0")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the action buttons."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        row = index.row()

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, option.palette.highlight())

        # Calculate button positions
        buttons = self._get_buttons()
        total_width = len(buttons) * self.button_size + (len(buttons) - 1) * self.button_spacing
        start_x = rect.left() + (rect.width() - total_width) // 2
        button_y = rect.top() + (rect.height() - self.button_size) // 2

        for i, (action, color, icon_text) in enumerate(buttons):
            button_x = start_x + i * (self.button_size + self.button_spacing)
            button_rect = QRect(button_x, button_y, self.button_size, self.button_size)

            # Hover effect
            is_hover = (row == self._hover_row and i == self._hover_button)

            # Draw button background
            if is_hover:
                painter.setBrush(self.hover_color)
            else:
                painter.setBrush(QColor(color).lighter(150))

            painter.setPen(QPen(color, 1))
            painter.drawRoundedRect(button_rect, 4, 4)

            # Draw icon/text
            painter.setPen(color)
            font = painter.font()
            font.setPointSize(10)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, icon_text)

        painter.restore()

    def _get_buttons(self) -> List[Tuple[str, QColor, str]]:
        """Get list of buttons to display."""
        buttons = []
        if self.show_view:
            buttons.append(("view", self.view_color, "V"))
        if self.show_edit:
            buttons.append(("edit", self.edit_color, "E"))
        if self.show_delete:
            buttons.append(("delete", self.delete_color, "X"))
        return buttons

    def editorEvent(self, event: QEvent, model: QAbstractItemModel,
                    option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        """Handle mouse events for button clicks."""
        from PyQt6.QtCore import QEvent as QE

        if event.type() == QE.Type.MouseButtonRelease:
            mouse_event = event
            pos = mouse_event.pos()
            row = index.row()

            # Check which button was clicked
            buttons = self._get_buttons()
            rect = option.rect
            total_width = len(buttons) * self.button_size + (len(buttons) - 1) * self.button_spacing
            start_x = rect.left() + (rect.width() - total_width) // 2
            button_y = rect.top() + (rect.height() - self.button_size) // 2

            for i, (action, _, _) in enumerate(buttons):
                button_x = start_x + i * (self.button_size + self.button_spacing)
                button_rect = QRect(button_x, button_y, self.button_size, self.button_size)

                if button_rect.contains(pos):
                    if action == "edit":
                        self.edit_clicked.emit(row)
                    elif action == "delete":
                        self.delete_clicked.emit(row)
                    elif action == "view":
                        self.view_clicked.emit(row)
                    return True

        elif event.type() == QE.Type.MouseMove:
            mouse_event = event
            pos = mouse_event.pos()
            row = index.row()

            # Update hover state
            buttons = self._get_buttons()
            rect = option.rect
            total_width = len(buttons) * self.button_size + (len(buttons) - 1) * self.button_spacing
            start_x = rect.left() + (rect.width() - total_width) // 2
            button_y = rect.top() + (rect.height() - self.button_size) // 2

            new_hover_button = -1
            for i, _ in enumerate(buttons):
                button_x = start_x + i * (self.button_size + self.button_spacing)
                button_rect = QRect(button_x, button_y, self.button_size, self.button_size)

                if button_rect.contains(pos):
                    new_hover_button = i
                    break

            if row != self._hover_row or new_hover_button != self._hover_button:
                self._hover_row = row
                self._hover_button = new_hover_button
                return True

        return super().editorEvent(event, model, option, index)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        buttons = self._get_buttons()
        width = len(buttons) * self.button_size + (len(buttons) - 1) * self.button_spacing + 16
        return QSize(width, self.button_size + 8)


# =============================================================================
# Boolean Delegate - Checkbox Display
# =============================================================================

class BooleanDelegate(QStyledItemDelegate):
    """
    Delegate for displaying boolean values as checkboxes or text.

    Features:
    - Checkbox or text display mode
    - Custom true/false labels
    - Color coding
    """

    def __init__(self,
                 use_checkbox: bool = True,
                 true_text: str = "Yes",
                 false_text: str = "No",
                 true_color: str = "#4CAF50",
                 false_color: str = "#9E9E9E",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.use_checkbox = use_checkbox
        self.true_text = true_text
        self.false_text = false_text
        self.true_color = QColor(true_color)
        self.false_color = QColor(false_color)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the boolean value."""
        painter.save()

        # Get value
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            value = index.data(Qt.ItemDataRole.DisplayRole)

        is_true = bool(value) if value is not None else False

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        if self.use_checkbox:
            # Draw checkbox
            checkbox_size = 18
            x = option.rect.left() + (option.rect.width() - checkbox_size) // 2
            y = option.rect.top() + (option.rect.height() - checkbox_size) // 2
            checkbox_rect = QRect(x, y, checkbox_size, checkbox_size)

            painter.setPen(QPen(QColor("#BDBDBD"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(checkbox_rect, 3, 3)

            if is_true:
                painter.setBrush(self.true_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(checkbox_rect.adjusted(2, 2, -2, -2), 2, 2)

                # Draw checkmark
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawLine(x + 4, y + 9, x + 7, y + 12)
                painter.drawLine(x + 7, y + 12, x + 14, y + 5)
        else:
            # Draw text
            text = self.true_text if is_true else self.false_text
            color = self.true_color if is_true else self.false_color

            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.setPen(color)

            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        return QSize(60, 32)


# =============================================================================
# Status Delegate - Colored Status Badge
# =============================================================================

class StatusDelegate(QStyledItemDelegate):
    """
    Delegate for displaying status as a colored badge.

    Features:
    - Customizable status colors
    - Rounded badge style
    - Icon support
    """

    def __init__(self,
                 status_colors: Optional[Dict[str, str]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.status_colors = status_colors or {
            "active": "#4CAF50",
            "inactive": "#9E9E9E",
            "pending": "#FFC107",
            "completed": "#2196F3",
            "cancelled": "#F44336",
            "draft": "#607D8B"
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the status badge."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get value
        value = index.data(Qt.ItemDataRole.DisplayRole)
        text = str(value) if value else ""
        text_lower = text.lower()

        # Get color
        color = QColor(self.status_colors.get(text_lower, "#9E9E9E"))

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Calculate badge dimensions
        font = painter.font()
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)
        badge_width = text_width + 16
        badge_height = 22

        x = option.rect.left() + (option.rect.width() - badge_width) // 2
        y = option.rect.top() + (option.rect.height() - badge_height) // 2
        badge_rect = QRect(x, y, badge_width, badge_height)

        # Draw badge background
        lighter = QColor(color)
        lighter.setAlpha(50)
        painter.setBrush(lighter)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, badge_height // 2, badge_height // 2)

        # Draw text
        painter.setPen(color)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        return QSize(100, 32)


# =============================================================================
# Rating Delegate - Star Rating Display
# =============================================================================

class RatingDelegate(QStyledItemDelegate):
    """
    Delegate for displaying ratings as stars.

    Features:
    - Configurable max stars
    - Half-star support
    - Interactive editing
    """

    def __init__(self,
                 max_stars: int = 5,
                 star_size: int = 16,
                 filled_color: str = "#FFC107",
                 empty_color: str = "#E0E0E0",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.max_stars = max_stars
        self.star_size = star_size
        self.filled_color = QColor(filled_color)
        self.empty_color = QColor(empty_color)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex):
        """Paint the star rating."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get value (0-max_stars)
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            value = index.data(Qt.ItemDataRole.DisplayRole)

        try:
            rating = float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            rating = 0.0

        rating = max(0, min(rating, self.max_stars))

        # Draw selection background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Calculate positions
        total_width = self.max_stars * self.star_size
        start_x = option.rect.left() + (option.rect.width() - total_width) // 2
        star_y = option.rect.top() + (option.rect.height() - self.star_size) // 2

        for i in range(self.max_stars):
            star_x = start_x + i * self.star_size

            # Determine fill level for this star
            if rating >= i + 1:
                fill = 1.0
            elif rating > i:
                fill = rating - i
            else:
                fill = 0.0

            # Draw star
            self._draw_star(painter, star_x, star_y, self.star_size, fill)

        painter.restore()

    def _draw_star(self, painter: QPainter, x: int, y: int, size: int, fill: float):
        """Draw a single star with specified fill level."""
        # Draw empty star
        painter.setBrush(self.empty_color)
        painter.setPen(Qt.PenStyle.NoPen)

        # Simple star using polygon (5-pointed)
        import math
        points = []
        for i in range(5):
            angle = math.radians(i * 144 - 90)
            px = x + size // 2 + int(size // 2 * 0.9 * math.cos(angle))
            py = y + size // 2 + int(size // 2 * 0.9 * math.sin(angle))
            points.append(QPoint(px, py))

        from PyQt6.QtGui import QPolygon
        star_polygon = QPolygon(points)
        painter.drawPolygon(star_polygon)

        # Draw filled portion
        if fill > 0:
            painter.setBrush(self.filled_color)
            if fill >= 1.0:
                painter.drawPolygon(star_polygon)
            else:
                # Clip to partial width
                clip_rect = QRect(x, y, int(size * fill), size)
                painter.setClipRect(clip_rect)
                painter.drawPolygon(star_polygon)
                painter.setClipping(False)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return preferred size."""
        return QSize(self.max_stars * self.star_size + 16, self.star_size + 8)
