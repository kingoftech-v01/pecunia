"""
Application theming for PyQt6 finance application.

Provides ThemeManager class with light/dark theme support, QSS stylesheets,
chart color palettes, and system theme detection.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtGui import QPalette, QColor


class ThemeMode(Enum):
    """Available theme modes."""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass
class ColorPalette:
    """Color palette definition for a theme."""
    # Primary colors
    primary: str = "#1976D2"
    primary_light: str = "#42A5F5"
    primary_dark: str = "#1565C0"

    # Secondary colors
    secondary: str = "#26A69A"
    secondary_light: str = "#4DB6AC"
    secondary_dark: str = "#00897B"

    # Background colors
    background: str = "#FFFFFF"
    background_alt: str = "#F5F5F5"
    surface: str = "#FAFAFA"

    # Text colors
    text_primary: str = "#212121"
    text_secondary: str = "#757575"
    text_disabled: str = "#BDBDBD"
    text_on_primary: str = "#FFFFFF"

    # Border colors
    border: str = "#E0E0E0"
    border_light: str = "#EEEEEE"
    divider: str = "#BDBDBD"

    # Status colors
    success: str = "#4CAF50"
    warning: str = "#FFC107"
    error: str = "#F44336"
    info: str = "#2196F3"

    # Financial colors
    positive: str = "#4CAF50"  # Green for gains
    negative: str = "#F44336"  # Red for losses
    neutral: str = "#9E9E9E"

    # Interactive states
    hover: str = "#E3F2FD"
    pressed: str = "#BBDEFB"
    selected: str = "#E3F2FD"
    focus: str = "#1976D2"

    # Chart colors
    chart_colors: List[str] = field(default_factory=lambda: [
        "#1976D2",  # Blue
        "#26A69A",  # Teal
        "#FFA726",  # Orange
        "#AB47BC",  # Purple
        "#66BB6A",  # Green
        "#EF5350",  # Red
        "#42A5F5",  # Light Blue
        "#FFCA28",  # Yellow
        "#8D6E63",  # Brown
        "#78909C",  # Blue Grey
    ])


# Pre-defined theme palettes
LIGHT_PALETTE = ColorPalette()

DARK_PALETTE = ColorPalette(
    # Primary colors
    primary="#90CAF9",
    primary_light="#BBDEFB",
    primary_dark="#64B5F6",

    # Secondary colors
    secondary="#80CBC4",
    secondary_light="#B2DFDB",
    secondary_dark="#4DB6AC",

    # Background colors
    background="#121212",
    background_alt="#1E1E1E",
    surface="#242424",

    # Text colors
    text_primary="#FFFFFF",
    text_secondary="#B0B0B0",
    text_disabled="#6B6B6B",
    text_on_primary="#000000",

    # Border colors
    border="#333333",
    border_light="#424242",
    divider="#424242",

    # Status colors
    success="#81C784",
    warning="#FFD54F",
    error="#E57373",
    info="#64B5F6",

    # Financial colors
    positive="#81C784",
    negative="#E57373",
    neutral="#9E9E9E",

    # Interactive states
    hover="#1E3A5F",
    pressed="#2E5077",
    selected="#1E3A5F",
    focus="#90CAF9",

    # Chart colors (brighter for dark mode)
    chart_colors=[
        "#64B5F6",  # Light Blue
        "#4DB6AC",  # Teal
        "#FFB74D",  # Orange
        "#BA68C8",  # Purple
        "#81C784",  # Green
        "#E57373",  # Red
        "#4FC3F7",  # Cyan
        "#FFD54F",  # Yellow
        "#A1887F",  # Brown
        "#90A4AE",  # Blue Grey
    ]
)


class StylesheetGenerator:
    """Generates QSS stylesheets from color palettes."""

    @staticmethod
    def generate(palette: ColorPalette) -> str:
        """Generate complete QSS stylesheet from palette."""
        return f"""
        /* ===== Global Styles ===== */
        QWidget {{
            background-color: {palette.background};
            color: {palette.text_primary};
            font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
            font-size: 13px;
        }}

        QMainWindow {{
            background-color: {palette.background};
        }}

        /* ===== Menu Bar ===== */
        QMenuBar {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border-bottom: 1px solid {palette.border};
            padding: 2px;
        }}

        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }}

        QMenuBar::item:selected {{
            background-color: {palette.hover};
        }}

        QMenuBar::item:pressed {{
            background-color: {palette.pressed};
        }}

        QMenu {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            padding: 4px;
        }}

        QMenu::item {{
            padding: 8px 32px 8px 16px;
            border-radius: 4px;
        }}

        QMenu::item:selected {{
            background-color: {palette.hover};
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {palette.divider};
            margin: 4px 8px;
        }}

        /* ===== Tool Bar ===== */
        QToolBar {{
            background-color: {palette.surface};
            border: none;
            border-bottom: 1px solid {palette.border};
            padding: 4px;
            spacing: 4px;
        }}

        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 6px;
        }}

        QToolButton:hover {{
            background-color: {palette.hover};
        }}

        QToolButton:pressed {{
            background-color: {palette.pressed};
        }}

        /* ===== Status Bar ===== */
        QStatusBar {{
            background-color: {palette.surface};
            color: {palette.text_secondary};
            border-top: 1px solid {palette.border};
        }}

        /* ===== Push Button ===== */
        QPushButton {{
            background-color: {palette.primary};
            color: {palette.text_on_primary};
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
            min-width: 80px;
        }}

        QPushButton:hover {{
            background-color: {palette.primary_light};
        }}

        QPushButton:pressed {{
            background-color: {palette.primary_dark};
        }}

        QPushButton:disabled {{
            background-color: {palette.border};
            color: {palette.text_disabled};
        }}

        QPushButton[flat="true"] {{
            background-color: transparent;
            color: {palette.primary};
        }}

        QPushButton[flat="true"]:hover {{
            background-color: {palette.hover};
        }}

        QPushButton#secondaryButton {{
            background-color: transparent;
            color: {palette.primary};
            border: 1px solid {palette.primary};
        }}

        QPushButton#secondaryButton:hover {{
            background-color: {palette.hover};
        }}

        QPushButton#dangerButton {{
            background-color: {palette.error};
        }}

        QPushButton#dangerButton:hover {{
            background-color: #E53935;
        }}

        QPushButton#successButton {{
            background-color: {palette.success};
        }}

        QPushButton#successButton:hover {{
            background-color: #43A047;
        }}

        /* ===== Line Edit ===== */
        QLineEdit {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            padding: 8px 12px;
            selection-background-color: {palette.primary};
            selection-color: {palette.text_on_primary};
        }}

        QLineEdit:focus {{
            border: 2px solid {palette.focus};
            padding: 7px 11px;
        }}

        QLineEdit:disabled {{
            background-color: {palette.background_alt};
            color: {palette.text_disabled};
        }}

        QLineEdit[error="true"] {{
            border: 1px solid {palette.error};
        }}

        /* ===== Text Edit ===== */
        QTextEdit, QPlainTextEdit {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            padding: 8px;
            selection-background-color: {palette.primary};
            selection-color: {palette.text_on_primary};
        }}

        QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {palette.focus};
        }}

        /* ===== Spin Box ===== */
        QSpinBox, QDoubleSpinBox {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            padding: 6px 8px;
        }}

        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {palette.focus};
        }}

        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            background-color: transparent;
            border: none;
            width: 16px;
        }}

        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: transparent;
            border: none;
            width: 16px;
        }}

        /* ===== Combo Box ===== */
        QComboBox {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            padding: 8px 12px;
            min-width: 120px;
        }}

        QComboBox:focus {{
            border: 2px solid {palette.focus};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}

        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            selection-background-color: {palette.hover};
            selection-color: {palette.text_primary};
            outline: none;
        }}

        /* ===== Check Box ===== */
        QCheckBox {{
            color: {palette.text_primary};
            spacing: 8px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {palette.border};
            border-radius: 3px;
            background-color: {palette.surface};
        }}

        QCheckBox::indicator:hover {{
            border-color: {palette.primary};
        }}

        QCheckBox::indicator:checked {{
            background-color: {palette.primary};
            border-color: {palette.primary};
        }}

        QCheckBox::indicator:disabled {{
            background-color: {palette.background_alt};
            border-color: {palette.border};
        }}

        /* ===== Radio Button ===== */
        QRadioButton {{
            color: {palette.text_primary};
            spacing: 8px;
        }}

        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {palette.border};
            border-radius: 10px;
            background-color: {palette.surface};
        }}

        QRadioButton::indicator:hover {{
            border-color: {palette.primary};
        }}

        QRadioButton::indicator:checked {{
            background-color: {palette.primary};
            border-color: {palette.primary};
        }}

        /* ===== Slider ===== */
        QSlider::groove:horizontal {{
            height: 4px;
            background-color: {palette.border};
            border-radius: 2px;
        }}

        QSlider::handle:horizontal {{
            width: 16px;
            height: 16px;
            margin: -6px 0;
            background-color: {palette.primary};
            border-radius: 8px;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {palette.primary_light};
        }}

        /* ===== Progress Bar ===== */
        QProgressBar {{
            background-color: {palette.border};
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {palette.primary};
            border-radius: 4px;
        }}

        /* ===== Table View ===== */
        QTableView, QTableWidget {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            gridline-color: {palette.border_light};
            selection-background-color: {palette.selected};
            selection-color: {palette.text_primary};
            alternate-background-color: {palette.background_alt};
        }}

        QTableView::item, QTableWidget::item {{
            padding: 8px;
            border: none;
        }}

        QTableView::item:selected, QTableWidget::item:selected {{
            background-color: {palette.selected};
            color: {palette.text_primary};
        }}

        QTableView::item:hover, QTableWidget::item:hover {{
            background-color: {palette.hover};
        }}

        QHeaderView::section {{
            background-color: {palette.background_alt};
            color: {palette.text_primary};
            font-weight: 600;
            padding: 10px 8px;
            border: none;
            border-bottom: 2px solid {palette.border};
            border-right: 1px solid {palette.border_light};
        }}

        QHeaderView::section:hover {{
            background-color: {palette.hover};
        }}

        /* ===== Tree View ===== */
        QTreeView, QTreeWidget {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            selection-background-color: {palette.selected};
            alternate-background-color: {palette.background_alt};
        }}

        QTreeView::item, QTreeWidget::item {{
            padding: 4px;
            border: none;
        }}

        QTreeView::item:selected, QTreeWidget::item:selected {{
            background-color: {palette.selected};
        }}

        QTreeView::item:hover, QTreeWidget::item:hover {{
            background-color: {palette.hover};
        }}

        QTreeView::branch:has-siblings:!adjoins-item {{
            border-image: none;
        }}

        /* ===== List View ===== */
        QListView, QListWidget {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            selection-background-color: {palette.selected};
            alternate-background-color: {palette.background_alt};
            outline: none;
        }}

        QListView::item, QListWidget::item {{
            padding: 8px;
            border: none;
            border-radius: 4px;
        }}

        QListView::item:selected, QListWidget::item:selected {{
            background-color: {palette.selected};
        }}

        QListView::item:hover, QListWidget::item:hover {{
            background-color: {palette.hover};
        }}

        /* ===== Tab Widget ===== */
        QTabWidget::pane {{
            background-color: {palette.surface};
            border: 1px solid {palette.border};
            border-radius: 4px;
            top: -1px;
        }}

        QTabBar::tab {{
            background-color: {palette.background_alt};
            color: {palette.text_secondary};
            padding: 10px 20px;
            border: 1px solid {palette.border};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}

        QTabBar::tab:selected {{
            background-color: {palette.surface};
            color: {palette.primary};
            border-bottom: 2px solid {palette.primary};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {palette.hover};
        }}

        /* ===== Scroll Bar ===== */
        QScrollBar:vertical {{
            background-color: {palette.background};
            width: 12px;
            border: none;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {palette.border};
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {palette.text_disabled};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {palette.background};
            height: 12px;
            border: none;
            border-radius: 6px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {palette.border};
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {palette.text_disabled};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* ===== Group Box ===== */
        QGroupBox {{
            background-color: {palette.surface};
            border: 1px solid {palette.border};
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {palette.text_primary};
        }}

        /* ===== Dialog ===== */
        QDialog {{
            background-color: {palette.background};
        }}

        QDialogButtonBox {{
            button-layout: 0;
        }}

        /* ===== Tooltip ===== */
        QToolTip {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            padding: 6px 10px;
        }}

        /* ===== Splitter ===== */
        QSplitter::handle {{
            background-color: {palette.border};
        }}

        QSplitter::handle:horizontal {{
            width: 2px;
        }}

        QSplitter::handle:vertical {{
            height: 2px;
        }}

        QSplitter::handle:hover {{
            background-color: {palette.primary};
        }}

        /* ===== Date Edit ===== */
        QDateEdit, QDateTimeEdit {{
            background-color: {palette.surface};
            color: {palette.text_primary};
            border: 1px solid {palette.border};
            border-radius: 4px;
            padding: 8px 12px;
        }}

        QDateEdit:focus, QDateTimeEdit:focus {{
            border: 2px solid {palette.focus};
        }}

        QCalendarWidget {{
            background-color: {palette.surface};
        }}

        QCalendarWidget QToolButton {{
            background-color: transparent;
            color: {palette.text_primary};
        }}

        QCalendarWidget QMenu {{
            background-color: {palette.surface};
        }}

        /* ===== Frame ===== */
        QFrame[frameShape="4"] {{ /* HLine */
            background-color: {palette.divider};
            border: none;
            max-height: 1px;
        }}

        QFrame[frameShape="5"] {{ /* VLine */
            background-color: {palette.divider};
            border: none;
            max-width: 1px;
        }}

        /* ===== Label ===== */
        QLabel {{
            color: {palette.text_primary};
            background-color: transparent;
        }}

        QLabel[heading="true"] {{
            font-size: 18px;
            font-weight: 600;
        }}

        QLabel[subheading="true"] {{
            font-size: 14px;
            color: {palette.text_secondary};
        }}

        QLabel[error="true"] {{
            color: {palette.error};
        }}

        QLabel[success="true"] {{
            color: {palette.success};
        }}

        /* ===== Dock Widget ===== */
        QDockWidget {{
            color: {palette.text_primary};
            titlebar-close-icon: none;
            titlebar-normal-icon: none;
        }}

        QDockWidget::title {{
            background-color: {palette.background_alt};
            padding: 8px;
            border-bottom: 1px solid {palette.border};
        }}

        QDockWidget::close-button, QDockWidget::float-button {{
            background-color: transparent;
            border: none;
        }}

        /* ===== Custom Financial Widgets ===== */
        QWidget#positiveValue {{
            color: {palette.positive};
        }}

        QWidget#negativeValue {{
            color: {palette.negative};
        }}

        QWidget#cardWidget {{
            background-color: {palette.surface};
            border: 1px solid {palette.border};
            border-radius: 8px;
            padding: 16px;
        }}

        QWidget#sidebarWidget {{
            background-color: {palette.background_alt};
            border-right: 1px solid {palette.border};
        }}

        QWidget#headerWidget {{
            background-color: {palette.surface};
            border-bottom: 1px solid {palette.border};
        }}
        """


class ThemeManager(QObject):
    """
    Manages application themes with light/dark mode support.

    Signals:
        theme_changed: Emitted when theme changes, provides ThemeMode

    Usage:
        theme_manager = ThemeManager()
        theme_manager.apply_theme(ThemeMode.DARK)
        theme_manager.theme_changed.connect(on_theme_change)
    """

    theme_changed = pyqtSignal(ThemeMode)

    _instance: Optional['ThemeManager'] = None

    def __new__(cls) -> 'ThemeManager':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the theme manager."""
        if hasattr(self, '_initialized'):
            return

        super().__init__()
        self._initialized = True
        self._current_mode: ThemeMode = ThemeMode.LIGHT
        self._current_palette: ColorPalette = LIGHT_PALETTE
        self._settings = QSettings("Pecunia", "Theme")

        # Load saved theme preference
        saved_theme = self._settings.value("theme_mode", ThemeMode.SYSTEM.value)
        try:
            self._current_mode = ThemeMode(saved_theme)
        except ValueError:
            self._current_mode = ThemeMode.SYSTEM

    @property
    def current_mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._current_mode

    @property
    def current_palette(self) -> ColorPalette:
        """Get current color palette."""
        return self._current_palette

    @property
    def is_dark(self) -> bool:
        """Check if current effective theme is dark."""
        if self._current_mode == ThemeMode.SYSTEM:
            return self._detect_system_dark_mode()
        return self._current_mode == ThemeMode.DARK

    def get_chart_colors(self) -> List[str]:
        """Get chart color palette for current theme."""
        return self._current_palette.chart_colors.copy()

    def get_color(self, color_name: str) -> str:
        """
        Get a specific color from current palette.

        Args:
            color_name: Name of the color attribute (e.g., 'primary', 'error')

        Returns:
            Color hex string
        """
        return getattr(self._current_palette, color_name, "#000000")

    def apply_theme(self, mode: ThemeMode) -> None:
        """
        Apply theme to the application.

        Args:
            mode: Theme mode to apply (LIGHT, DARK, or SYSTEM)
        """
        self._current_mode = mode
        self._settings.setValue("theme_mode", mode.value)

        # Determine effective theme
        if mode == ThemeMode.SYSTEM:
            is_dark = self._detect_system_dark_mode()
        else:
            is_dark = mode == ThemeMode.DARK

        # Set appropriate palette
        self._current_palette = DARK_PALETTE if is_dark else LIGHT_PALETTE

        # Apply to application
        app = QApplication.instance()
        if app:
            # Generate and apply stylesheet
            stylesheet = StylesheetGenerator.generate(self._current_palette)
            app.setStyleSheet(stylesheet)

            # Also set the QPalette for native widgets
            self._apply_qpalette(app, self._current_palette)

        # Emit signal
        self.theme_changed.emit(mode)

    def toggle_theme(self) -> ThemeMode:
        """
        Toggle between light and dark theme.

        Returns:
            New theme mode
        """
        if self.is_dark:
            self.apply_theme(ThemeMode.LIGHT)
        else:
            self.apply_theme(ThemeMode.DARK)
        return self._current_mode

    def refresh_system_theme(self) -> None:
        """Refresh theme if using system mode (call on system theme change)."""
        if self._current_mode == ThemeMode.SYSTEM:
            self.apply_theme(ThemeMode.SYSTEM)

    def _detect_system_dark_mode(self) -> bool:
        """
        Detect if system is using dark mode.

        Returns:
            True if system is in dark mode
        """
        app = QApplication.instance()
        if app:
            # Check system palette
            palette = app.palette()
            # Compare window color luminance
            window_color = palette.color(QPalette.ColorRole.Window)
            # Calculate luminance
            luminance = (
                0.299 * window_color.red() +
                0.587 * window_color.green() +
                0.114 * window_color.blue()
            ) / 255
            return luminance < 0.5
        return False

    def _apply_qpalette(self, app: QApplication, palette: ColorPalette) -> None:
        """
        Apply color palette to Qt's QPalette for native widgets.

        Args:
            app: Application instance
            palette: Color palette to apply
        """
        qpalette = QPalette()

        # Window and base colors
        qpalette.setColor(QPalette.ColorRole.Window, QColor(palette.background))
        qpalette.setColor(QPalette.ColorRole.WindowText, QColor(palette.text_primary))
        qpalette.setColor(QPalette.ColorRole.Base, QColor(palette.surface))
        qpalette.setColor(QPalette.ColorRole.AlternateBase, QColor(palette.background_alt))

        # Text colors
        qpalette.setColor(QPalette.ColorRole.Text, QColor(palette.text_primary))
        qpalette.setColor(QPalette.ColorRole.PlaceholderText, QColor(palette.text_disabled))
        qpalette.setColor(QPalette.ColorRole.BrightText, QColor(palette.text_on_primary))

        # Button colors
        qpalette.setColor(QPalette.ColorRole.Button, QColor(palette.surface))
        qpalette.setColor(QPalette.ColorRole.ButtonText, QColor(palette.text_primary))

        # Highlight colors
        qpalette.setColor(QPalette.ColorRole.Highlight, QColor(palette.primary))
        qpalette.setColor(QPalette.ColorRole.HighlightedText, QColor(palette.text_on_primary))

        # Link colors
        qpalette.setColor(QPalette.ColorRole.Link, QColor(palette.primary))
        qpalette.setColor(QPalette.ColorRole.LinkVisited, QColor(palette.primary_dark))

        # Disabled colors
        qpalette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.WindowText,
            QColor(palette.text_disabled)
        )
        qpalette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.Text,
            QColor(palette.text_disabled)
        )
        qpalette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(palette.text_disabled)
        )

        app.setPalette(qpalette)

    @staticmethod
    def get_financial_color(value: float, palette: Optional[ColorPalette] = None) -> str:
        """
        Get appropriate color for a financial value.

        Args:
            value: Financial value (positive, negative, or zero)
            palette: Color palette to use (uses current if None)

        Returns:
            Color hex string
        """
        if palette is None:
            palette = ThemeManager()._current_palette

        if value > 0:
            return palette.positive
        elif value < 0:
            return palette.negative
        else:
            return palette.neutral

    @staticmethod
    def format_financial_html(value: float, prefix: str = "$") -> str:
        """
        Format a financial value with appropriate color as HTML.

        Args:
            value: Financial value
            prefix: Currency prefix

        Returns:
            HTML formatted string with color
        """
        color = ThemeManager.get_financial_color(value)
        sign = "+" if value > 0 else ""
        return f'<span style="color: {color}">{sign}{prefix}{abs(value):,.2f}</span>'


# Convenience function for getting theme manager instance
def get_theme_manager() -> ThemeManager:
    """Get the singleton ThemeManager instance."""
    return ThemeManager()


# Initialize module-level colors for quick access
def get_palette() -> ColorPalette:
    """Get current color palette."""
    return get_theme_manager().current_palette


def get_chart_colors() -> List[str]:
    """Get current chart color palette."""
    return get_theme_manager().get_chart_colors()
