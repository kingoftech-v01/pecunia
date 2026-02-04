"""
Budget Item Editor Module

Widget for editing individual budget items with category selection,
amount input, and alert threshold configuration.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFrame, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QSlider, QProgressBar, QSizePolicy,
    QDialog, QDialogButtonBox, QGroupBox, QScrollArea, QListWidget,
    QListWidgetItem, QAbstractItemView, QMessageBox, QCheckBox,
    QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QPixmap, QIcon
from typing import Optional, Dict, Any, List, Callable
from decimal import Decimal


class ColorDot(QWidget):
    """Small colored dot widget for category indicators."""

    def __init__(
        self,
        color: str = "#888888",
        size: int = 12,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size, size)

    def set_color(self, color: str):
        """Set the dot color."""
        self._color = color
        self.update()

    def paintEvent(self, event):
        """Paint the colored dot."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(self._color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self._size, self._size)


class CategorySelector(QWidget):
    """
    Category selection widget with search, color indicators, and icons.

    Features:
    - Searchable dropdown
    - Color dots for each category
    - Optional icons
    - Create new category option
    """

    category_changed = pyqtSignal(dict)  # Emits selected category data
    create_category_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("categorySelector")
        self._categories: List[Dict[str, Any]] = []
        self._selected_category: Optional[Dict[str, Any]] = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the category selector UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Color indicator
        self.color_dot = ColorDot()
        layout.addWidget(self.color_dot)

        # Combo box
        self.combo = QComboBox()
        self.combo.setObjectName("categoryCombo")
        self.combo.setMinimumWidth(200)
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo.lineEdit().setPlaceholderText("Select or search category...")
        self.combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                background-color: #FFFFFF;
            }
            QComboBox:focus {
                border-color: #2196F3;
                border-width: 2px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                selection-background-color: #E3F2FD;
            }
        """)
        self.combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.combo, 1)

        # Add category button
        add_btn = QPushButton("+")
        add_btn.setFixedSize(36, 36)
        add_btn.setToolTip("Create new category")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: #1976D2;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        add_btn.clicked.connect(self.create_category_requested.emit)
        layout.addWidget(add_btn)

    def _on_selection_changed(self, index: int):
        """Handle category selection change."""
        if 0 <= index < len(self._categories):
            self._selected_category = self._categories[index]
            self.color_dot.set_color(
                self._selected_category.get('color', '#888888')
            )
            self.category_changed.emit(self._selected_category)
        else:
            self._selected_category = None
            self.color_dot.set_color('#888888')

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self._categories = categories
        current_text = self.combo.currentText()

        self.combo.clear()
        for cat in categories:
            name = cat.get('name', 'Unknown')
            color = cat.get('color', '#888888')

            # Create color icon
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()

            self.combo.addItem(QIcon(pixmap), name)

        # Restore selection if possible
        index = self.combo.findText(current_text)
        if index >= 0:
            self.combo.setCurrentIndex(index)

    def get_selected_category(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected category."""
        return self._selected_category

    def set_selected_category(self, category_id: int):
        """Set the selected category by ID."""
        for i, cat in enumerate(self._categories):
            if cat.get('id') == category_id:
                self.combo.setCurrentIndex(i)
                break

    def set_selected_by_name(self, name: str):
        """Set the selected category by name."""
        index = self.combo.findText(name)
        if index >= 0:
            self.combo.setCurrentIndex(index)


class AmountInput(QWidget):
    """
    Enhanced amount input with currency symbol and validation.

    Features:
    - Currency symbol display
    - Decimal precision
    - Min/max validation
    - Quick amount buttons
    """

    value_changed = pyqtSignal(Decimal)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        currency_symbol: str = "$",
        decimal_places: int = 2,
        show_quick_amounts: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("amountInput")
        self._currency_symbol = currency_symbol
        self._decimal_places = decimal_places
        self._show_quick_amounts = show_quick_amounts
        self._setup_ui()

    def _setup_ui(self):
        """Set up the amount input UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Main input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)

        # Currency symbol
        symbol_label = QLabel(self._currency_symbol)
        symbol_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        symbol_label.setStyleSheet("color: #666666;")
        input_layout.addWidget(symbol_label)

        # Spin box
        self.spin_box = QDoubleSpinBox()
        self.spin_box.setDecimals(self._decimal_places)
        self.spin_box.setMaximum(999999999.99)
        self.spin_box.setMinimum(0.00)
        self.spin_box.setValue(0.00)
        self.spin_box.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_box.setMinimumWidth(150)
        self.spin_box.setStyleSheet("""
            QDoubleSpinBox {
                padding: 10px 12px;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QDoubleSpinBox:focus {
                border-color: #2196F3;
                border-width: 2px;
            }
        """)
        self.spin_box.valueChanged.connect(self._on_value_changed)
        input_layout.addWidget(self.spin_box)
        input_layout.addStretch()

        layout.addLayout(input_layout)

        # Quick amount buttons
        if self._show_quick_amounts:
            quick_layout = QHBoxLayout()
            quick_layout.setSpacing(8)

            quick_amounts = [50, 100, 250, 500, 1000]
            for amount in quick_amounts:
                btn = QPushButton(f"${amount}")
                btn.setFixedHeight(30)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F5F5F5;
                        color: #666666;
                        border: 1px solid #E0E0E0;
                        border-radius: 4px;
                        padding: 4px 12px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #E3F2FD;
                        border-color: #2196F3;
                        color: #1976D2;
                    }
                """)
                btn.clicked.connect(lambda checked, a=amount: self.set_value(a))
                quick_layout.addWidget(btn)

            quick_layout.addStretch()
            layout.addLayout(quick_layout)

    def _on_value_changed(self, value: float):
        """Handle value change."""
        decimal_value = Decimal(str(value)).quantize(
            Decimal(10) ** -self._decimal_places
        )
        self.value_changed.emit(decimal_value)

    def value(self) -> Decimal:
        """Get the current value as Decimal."""
        return Decimal(str(self.spin_box.value())).quantize(
            Decimal(10) ** -self._decimal_places
        )

    def set_value(self, value: float | Decimal | str):
        """Set the value."""
        try:
            self.spin_box.setValue(float(value))
        except (ValueError, TypeError):
            self.spin_box.setValue(0.0)

    def set_range(self, minimum: float, maximum: float):
        """Set the valid range."""
        self.spin_box.setMinimum(minimum)
        self.spin_box.setMaximum(maximum)


class AlertThresholdSlider(QWidget):
    """
    Slider widget for setting alert threshold percentage.

    Features:
    - Visual percentage display
    - Color-coded indicator
    - Tick marks
    """

    threshold_changed = pyqtSignal(int)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        min_value: int = 50,
        max_value: int = 100,
        default_value: int = 80
    ):
        super().__init__(parent)
        self.setObjectName("alertThresholdSlider")
        self._min_value = min_value
        self._max_value = max_value
        self._default_value = default_value
        self._setup_ui()

    def _setup_ui(self):
        """Set up the threshold slider UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with label and value
        header_layout = QHBoxLayout()

        self.label = QLabel("Alert Threshold")
        self.label.setFont(QFont("Segoe UI", 10))
        header_layout.addWidget(self.label)

        header_layout.addStretch()

        self.value_label = QLabel(f"{self._default_value}%")
        self.value_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.value_label.setStyleSheet("color: #FF9800;")
        self.value_label.setMinimumWidth(50)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(self.value_label)

        layout.addLayout(header_layout)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(self._min_value)
        self.slider.setMaximum(self._max_value)
        self.slider.setValue(self._default_value)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(10)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:0.6 #FFC107, stop:1 #F44336
                );
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                margin: -6px 0;
                background-color: #FFFFFF;
                border: 2px solid #2196F3;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #E3F2FD;
            }
        """)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)

        # Labels row
        labels_layout = QHBoxLayout()
        labels_layout.setContentsMargins(0, 0, 0, 0)

        min_label = QLabel(f"{self._min_value}%")
        min_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
        labels_layout.addWidget(min_label)

        labels_layout.addStretch()

        mid_label = QLabel("75%")
        mid_label.setStyleSheet("color: #FFC107; font-size: 10px;")
        labels_layout.addWidget(mid_label)

        labels_layout.addStretch()

        max_label = QLabel(f"{self._max_value}%")
        max_label.setStyleSheet("color: #F44336; font-size: 10px;")
        labels_layout.addWidget(max_label)

        layout.addLayout(labels_layout)

    def _on_value_changed(self, value: int):
        """Handle slider value change."""
        self.value_label.setText(f"{value}%")

        # Update color based on value
        if value >= 90:
            color = "#F44336"
        elif value >= 75:
            color = "#FF9800"
        else:
            color = "#4CAF50"

        self.value_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.threshold_changed.emit(value)

    def value(self) -> int:
        """Get the current threshold value."""
        return self.slider.value()

    def set_value(self, value: int):
        """Set the threshold value."""
        self.slider.setValue(value)


class BudgetItemPreview(QFrame):
    """Preview widget showing how the budget item will appear."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("budgetItemPreview")
        self._setup_ui()

    def _setup_ui(self):
        """Set up the preview widget UI."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            #budgetItemPreview {
                background-color: #F5F5F5;
                border: 1px dashed #CCCCCC;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        # Title
        title = QLabel("Preview")
        title.setFont(QFont("Segoe UI", 9))
        title.setStyleSheet("color: #888888;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Category and amount
        info_layout = QHBoxLayout()

        self.category_label = QLabel("Category Name")
        self.category_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        info_layout.addWidget(self.category_label)

        info_layout.addStretch()

        self.amount_label = QLabel("$0.00")
        self.amount_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.amount_label.setStyleSheet("color: #2196F3;")
        info_layout.addWidget(self.amount_label)

        layout.addLayout(info_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("0%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Threshold marker
        self.threshold_label = QLabel("Alert at 80%")
        self.threshold_label.setFont(QFont("Segoe UI", 9))
        self.threshold_label.setStyleSheet("color: #FF9800;")
        self.threshold_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.threshold_label)

    def update_preview(
        self,
        category_name: str,
        amount: Decimal,
        threshold: int,
        color: str = "#4CAF50"
    ):
        """Update the preview with new data."""
        self.category_label.setText(category_name)
        self.amount_label.setText(f"${amount:,.2f}")
        self.threshold_label.setText(f"Alert at {threshold}%")

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E0E0E0;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)


class BudgetItemEditor(QWidget):
    """
    Comprehensive widget for editing budget items.

    Features:
    - Category selection with search
    - Amount input with quick amounts
    - Alert threshold slider
    - Live preview
    - Validation

    Signals:
        item_saved: Emitted when item is saved with item data
        item_cancelled: Emitted when editing is cancelled
    """

    item_saved = pyqtSignal(dict)
    item_cancelled = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        categories: Optional[List[Dict[str, Any]]] = None,
        edit_item: Optional[Dict[str, Any]] = None
    ):
        super().__init__(parent)
        self.setObjectName("budgetItemEditor")
        self._categories = categories or []
        self._edit_item = edit_item
        self._setup_ui()
        self._connect_signals()

        if categories:
            self.set_categories(categories)
        if edit_item:
            self.load_item(edit_item)

    def _setup_ui(self):
        """Set up the budget item editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Form container
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(20)

        # Category selection
        category_section = QVBoxLayout()
        category_label = QLabel("Category")
        category_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        category_section.addWidget(category_label)

        self.category_selector = CategorySelector()
        category_section.addWidget(self.category_selector)

        form_layout.addLayout(category_section)

        # Amount input
        amount_section = QVBoxLayout()
        amount_label = QLabel("Planned Amount")
        amount_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        amount_section.addWidget(amount_label)

        self.amount_input = AmountInput()
        amount_section.addWidget(self.amount_input)

        form_layout.addLayout(amount_section)

        # Alert threshold
        threshold_section = QVBoxLayout()

        self.threshold_slider = AlertThresholdSlider()
        threshold_section.addWidget(self.threshold_slider)

        form_layout.addLayout(threshold_section)

        # Additional options
        options_group = QGroupBox("Additional Options")
        options_layout = QVBoxLayout(options_group)

        self.carry_over_check = QCheckBox(
            "Carry over unused amount to next period"
        )
        options_layout.addWidget(self.carry_over_check)

        self.strict_limit_check = QCheckBox(
            "Strict limit - prevent overspending"
        )
        options_layout.addWidget(self.strict_limit_check)

        form_layout.addWidget(options_group)

        layout.addWidget(form_frame)

        # Preview
        preview_label = QLabel("Item Preview")
        preview_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(preview_label)

        self.preview = BudgetItemPreview()
        layout.addWidget(self.preview)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #666666;
                border: 1px solid #CCCCCC;
                padding: 10px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        cancel_btn.clicked.connect(self.item_cancelled.emit)
        button_layout.addWidget(cancel_btn)

        button_layout.addSpacing(10)

        save_btn = QPushButton("Save Item")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self._save_item)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect internal signals."""
        self.category_selector.category_changed.connect(self._update_preview)
        self.amount_input.value_changed.connect(self._update_preview)
        self.threshold_slider.threshold_changed.connect(self._update_preview)

    def _update_preview(self, *args):
        """Update the preview widget."""
        category = self.category_selector.get_selected_category()
        amount = self.amount_input.value()
        threshold = self.threshold_slider.value()

        category_name = category.get('name', 'Unknown') if category else 'Select Category'
        color = category.get('color', '#4CAF50') if category else '#4CAF50'

        self.preview.update_preview(
            category_name=category_name,
            amount=amount,
            threshold=threshold,
            color=color
        )

    def _save_item(self):
        """Validate and save the budget item."""
        category = self.category_selector.get_selected_category()
        if not category:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select a category."
            )
            return

        amount = self.amount_input.value()
        if amount <= 0:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a valid amount greater than zero."
            )
            return

        item_data = {
            'category_id': category.get('id'),
            'category_name': category.get('name'),
            'color': category.get('color', '#888888'),
            'planned_amount': amount,
            'alert_threshold': self.threshold_slider.value(),
            'carry_over': self.carry_over_check.isChecked(),
            'strict_limit': self.strict_limit_check.isChecked()
        }

        # Include ID if editing existing item
        if self._edit_item and 'id' in self._edit_item:
            item_data['id'] = self._edit_item['id']

        self.item_saved.emit(item_data)

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self._categories = categories
        self.category_selector.set_categories(categories)

    def load_item(self, item: Dict[str, Any]):
        """Load an existing item for editing."""
        self._edit_item = item

        # Set category
        category_id = item.get('category_id')
        if category_id:
            self.category_selector.set_selected_category(category_id)
        else:
            category_name = item.get('category_name', item.get('category'))
            if category_name:
                self.category_selector.set_selected_by_name(category_name)

        # Set amount
        amount = item.get('planned_amount', item.get('limit', 0))
        self.amount_input.set_value(float(amount))

        # Set threshold
        threshold = item.get('alert_threshold', 80)
        self.threshold_slider.set_value(threshold)

        # Set options
        self.carry_over_check.setChecked(item.get('carry_over', False))
        self.strict_limit_check.setChecked(item.get('strict_limit', False))

        self._update_preview()

    def clear(self):
        """Clear the editor."""
        self._edit_item = None
        self.category_selector.combo.setCurrentIndex(-1)
        self.amount_input.set_value(0)
        self.threshold_slider.set_value(80)
        self.carry_over_check.setChecked(False)
        self.strict_limit_check.setChecked(False)
        self._update_preview()


class BudgetItemEditorDialog(QDialog):
    """
    Dialog wrapper for the BudgetItemEditor widget.

    Provides a modal dialog for editing budget items.
    """

    item_saved = pyqtSignal(dict)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        categories: Optional[List[Dict[str, Any]]] = None,
        edit_item: Optional[Dict[str, Any]] = None
    ):
        super().__init__(parent)
        self._setup_ui(categories, edit_item)

    def _setup_ui(
        self,
        categories: Optional[List[Dict[str, Any]]],
        edit_item: Optional[Dict[str, Any]]
    ):
        """Set up the dialog UI."""
        self.setWindowTitle(
            "Edit Budget Item" if edit_item else "Add Budget Item"
        )
        self.setMinimumSize(450, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.editor = BudgetItemEditor(
            categories=categories,
            edit_item=edit_item
        )
        self.editor.item_saved.connect(self._on_saved)
        self.editor.item_cancelled.connect(self.reject)

        layout.addWidget(self.editor)

    def _on_saved(self, item_data: dict):
        """Handle item save."""
        self.item_saved.emit(item_data)
        self.accept()

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self.editor.set_categories(categories)

    def load_item(self, item: Dict[str, Any]):
        """Load an item for editing."""
        self.editor.load_item(item)


class BudgetItemsList(QWidget):
    """
    Widget displaying a list of budget items with inline editing.

    Features:
    - List of budget items with progress
    - Add/Edit/Delete actions
    - Drag and drop reordering
    - Total allocation display
    """

    item_added = pyqtSignal(dict)
    item_edited = pyqtSignal(int, dict)  # index, data
    item_removed = pyqtSignal(int)  # index
    total_changed = pyqtSignal(Decimal)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        categories: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(parent)
        self.setObjectName("budgetItemsList")
        self._categories = categories or []
        self._items: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the items list UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Budget Items")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Total display
        total_widget = QWidget()
        total_layout = QHBoxLayout(total_widget)
        total_layout.setContentsMargins(10, 5, 10, 5)
        total_layout.setSpacing(8)

        total_widget.setStyleSheet("""
            background-color: #E3F2FD;
            border-radius: 6px;
        """)

        total_layout.addWidget(QLabel("Total:"))
        self.total_label = QLabel("$0.00")
        self.total_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.total_label.setStyleSheet("color: #1976D2;")
        total_layout.addWidget(self.total_label)

        header_layout.addWidget(total_widget)

        # Add button
        add_btn = QPushButton("+ Add Item")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_btn.clicked.connect(self._add_item)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Items list
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(10)

        # Empty state
        self.empty_label = QLabel("No items added. Click '+ Add Item' to start.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            color: #999999;
            padding: 40px;
            background-color: #FAFAFA;
            border: 1px dashed #CCCCCC;
            border-radius: 8px;
        """)
        self.items_layout.addWidget(self.empty_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.items_container)

        layout.addWidget(scroll)

    def _add_item(self):
        """Open dialog to add a new item."""
        dialog = BudgetItemEditorDialog(
            parent=self,
            categories=self._categories
        )
        dialog.item_saved.connect(self._on_item_added)
        dialog.exec()

    def _on_item_added(self, item_data: dict):
        """Handle new item added."""
        self._items.append(item_data)
        self._refresh_list()
        self.item_added.emit(item_data)
        self._emit_total()

    def _edit_item(self, index: int):
        """Open dialog to edit an item."""
        if 0 <= index < len(self._items):
            dialog = BudgetItemEditorDialog(
                parent=self,
                categories=self._categories,
                edit_item=self._items[index]
            )
            dialog.item_saved.connect(lambda data: self._on_item_edited(index, data))
            dialog.exec()

    def _on_item_edited(self, index: int, item_data: dict):
        """Handle item edited."""
        if 0 <= index < len(self._items):
            self._items[index] = item_data
            self._refresh_list()
            self.item_edited.emit(index, item_data)
            self._emit_total()

    def _remove_item(self, index: int):
        """Remove an item."""
        if 0 <= index < len(self._items):
            reply = QMessageBox.question(
                self,
                "Remove Item",
                f"Are you sure you want to remove '{self._items[index].get('category_name', 'this item')}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                del self._items[index]
                self._refresh_list()
                self.item_removed.emit(index)
                self._emit_total()

    def _refresh_list(self):
        """Refresh the items list display."""
        # Clear existing items
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._items:
            self.empty_label = QLabel("No items added. Click '+ Add Item' to start.")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("""
                color: #999999;
                padding: 40px;
                background-color: #FAFAFA;
                border: 1px dashed #CCCCCC;
                border-radius: 8px;
            """)
            self.items_layout.addWidget(self.empty_label)
            return

        for i, item in enumerate(self._items):
            item_widget = self._create_item_widget(i, item)
            self.items_layout.addWidget(item_widget)

        self.items_layout.addStretch()

    def _create_item_widget(self, index: int, item: Dict[str, Any]) -> QFrame:
        """Create a widget for displaying a single item."""
        frame = QFrame()
        frame.setObjectName("itemWidget")
        frame.setStyleSheet("""
            #itemWidget {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            #itemWidget:hover {
                border-color: #2196F3;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)

        # Color dot
        color = item.get('color', '#888888')
        color_dot = ColorDot(color, 12)
        layout.addWidget(color_dot)

        # Category name
        name_label = QLabel(item.get('category_name', 'Unknown'))
        name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        layout.addWidget(name_label)

        layout.addStretch()

        # Amount
        amount = Decimal(str(item.get('planned_amount', 0)))
        amount_label = QLabel(f"${amount:,.2f}")
        amount_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        amount_label.setStyleSheet("color: #2196F3;")
        layout.addWidget(amount_label)

        # Threshold
        threshold = item.get('alert_threshold', 80)
        threshold_label = QLabel(f"Alert: {threshold}%")
        threshold_label.setStyleSheet("color: #FF9800; font-size: 10px;")
        layout.addWidget(threshold_label)

        # Action buttons
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: #1976D2;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        edit_btn.clicked.connect(lambda: self._edit_item(index))
        layout.addWidget(edit_btn)

        remove_btn = QPushButton("X")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFEBEE;
                color: #F44336;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFCDD2;
            }
        """)
        remove_btn.clicked.connect(lambda: self._remove_item(index))
        layout.addWidget(remove_btn)

        return frame

    def _emit_total(self):
        """Emit the total allocation."""
        total = sum(
            Decimal(str(item.get('planned_amount', 0)))
            for item in self._items
        )
        self.total_label.setText(f"${total:,.2f}")
        self.total_changed.emit(total)

    def set_categories(self, categories: List[Dict[str, Any]]):
        """Set available categories."""
        self._categories = categories

    def get_items(self) -> List[Dict[str, Any]]:
        """Get all items."""
        return self._items.copy()

    def set_items(self, items: List[Dict[str, Any]]):
        """Set items."""
        self._items = items
        self._refresh_list()
        self._emit_total()

    def clear(self):
        """Clear all items."""
        self._items.clear()
        self._refresh_list()
        self._emit_total()
