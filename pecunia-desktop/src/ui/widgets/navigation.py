"""
Navigation widgets for Pecunia Desktop.

Provides navigation components including sidebar, breadcrumb, and tabs.
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal,
    QSize, QTimer, QPoint
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy,
    QGraphicsOpacityEffect, QStackedWidget, QSpacerItem
)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

from ..styles.theme import get_theme_manager
from .common import Badge


@dataclass
class NavItem:
    """Navigation item data."""
    id: str
    label: str
    icon: Optional[str] = None
    badge_count: int = 0
    children: Optional[List['NavItem']] = None
    action: Optional[Callable] = None


class SidebarItem(QWidget):
    """
    Individual sidebar navigation item.

    Represents a single item in the sidebar navigation.
    """

    clicked = pyqtSignal(str)  # Emits item ID
    hovered = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        item: NavItem = None,
        collapsed: bool = False,
        level: int = 0
    ):
        """
        Initialize sidebar item.

        Args:
            parent: Parent widget
            item: Navigation item data
            collapsed: Whether sidebar is collapsed
            level: Nesting level for sub-items
        """
        super().__init__(parent)

        self._item = item or NavItem(id="", label="")
        self._collapsed = collapsed
        self._level = level
        self._selected = False
        self._expanded = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        theme = get_theme_manager()
        palette = theme.current_palette

        self.setObjectName("sidebarItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setMaximumHeight(44)

        self._update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12 + (self._level * 16), 8, 12, 8)
        layout.setSpacing(12)

        # Icon
        if self._item.icon:
            self._icon_label = QLabel()
            pixmap = QPixmap(self._item.icon)
            if not pixmap.isNull():
                self._icon_label.setPixmap(
                    pixmap.scaled(
                        20, 20,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            else:
                # Use text placeholder
                self._icon_label.setText(self._item.label[0].upper())
                self._icon_label.setFixedSize(20, 20)
                self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._icon_label.setStyleSheet(f"""
                    background-color: {palette.primary}20;
                    color: {palette.primary};
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 11px;
                """)
            layout.addWidget(self._icon_label)
        else:
            # Placeholder for alignment
            spacer = QWidget()
            spacer.setFixedWidth(20)
            layout.addWidget(spacer)

        # Label
        self._label = QLabel(self._item.label)
        self._label.setStyleSheet(f"""
            font-size: 14px;
            color: {palette.text_primary};
        """)
        if self._collapsed:
            self._label.hide()
        layout.addWidget(self._label, 1)

        # Badge
        if self._item.badge_count > 0:
            self._badge = Badge(count=self._item.badge_count)
            if self._collapsed:
                self._badge.hide()
            layout.addWidget(self._badge)

        # Expand arrow for items with children
        if self._item.children:
            self._expand_arrow = QLabel("\u25b8")  # Right triangle
            self._expand_arrow.setStyleSheet(f"""
                color: {palette.text_secondary};
                font-size: 10px;
            """)
            if self._collapsed:
                self._expand_arrow.hide()
            layout.addWidget(self._expand_arrow)

        # Connect theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode) -> None:
        """Handle theme change."""
        self._update_style()

    def _update_style(self) -> None:
        """Update item style."""
        theme = get_theme_manager()
        palette = theme.current_palette

        if self._selected:
            bg_color = palette.selected
            text_color = palette.primary
            font_weight = "600"
        else:
            bg_color = "transparent"
            text_color = palette.text_primary
            font_weight = "normal"

        self.setStyleSheet(f"""
            #sidebarItem {{
                background-color: {bg_color};
                border-radius: 6px;
            }}
            #sidebarItem:hover {{
                background-color: {palette.hover};
            }}
        """)

        if hasattr(self, '_label'):
            self._label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: {font_weight};
                color: {text_color};
            """)

    def set_selected(self, selected: bool) -> None:
        """Set selected state."""
        self._selected = selected
        self._update_style()

    def set_collapsed(self, collapsed: bool) -> None:
        """Set collapsed state."""
        self._collapsed = collapsed
        if hasattr(self, '_label'):
            self._label.setVisible(not collapsed)
        if hasattr(self, '_badge'):
            self._badge.setVisible(not collapsed)
        if hasattr(self, '_expand_arrow'):
            self._expand_arrow.setVisible(not collapsed)

    def set_expanded(self, expanded: bool) -> None:
        """Set expanded state for items with children."""
        self._expanded = expanded
        if hasattr(self, '_expand_arrow'):
            self._expand_arrow.setText("\u25be" if expanded else "\u25b8")

    @property
    def item_id(self) -> str:
        """Get item ID."""
        return self._item.id

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._item.id)
            if self._item.action:
                self._item.action()
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        """Handle mouse enter."""
        self.hovered.emit(self._item.id)
        super().enterEvent(event)


class Sidebar(QWidget):
    """
    Navigation sidebar menu.

    Provides a collapsible navigation menu with icons and labels.

    Usage:
        sidebar = Sidebar()
        sidebar.add_item(NavItem("dashboard", "Dashboard", icon=":/icons/dashboard.svg"))
        sidebar.add_item(NavItem("transactions", "Transactions"))
        sidebar.item_selected.connect(self.navigate)
    """

    item_selected = pyqtSignal(str)
    collapsed_changed = pyqtSignal(bool)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        collapsed: bool = False,
        width: int = 250,
        collapsed_width: int = 60
    ):
        """
        Initialize sidebar.

        Args:
            parent: Parent widget
            collapsed: Initial collapsed state
            width: Expanded width
            collapsed_width: Collapsed width
        """
        super().__init__(parent)

        self._collapsed = collapsed
        self._expanded_width = width
        self._collapsed_width = collapsed_width
        self._items: Dict[str, SidebarItem] = {}
        self._selected_id: Optional[str] = None

        self._setup_ui()
        self._update_width()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        theme = get_theme_manager()
        palette = theme.current_palette

        self.setObjectName("sidebarWidget")
        self.setStyleSheet(f"""
            #sidebarWidget {{
                background-color: {palette.background_alt};
                border-right: 1px solid {palette.border};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header with collapse button
        header = QHBoxLayout()
        header.setContentsMargins(4, 8, 4, 16)

        # Logo/title area
        self._logo_label = QLabel("Finance")
        self._logo_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {palette.primary};
        """)
        if self._collapsed:
            self._logo_label.hide()
        header.addWidget(self._logo_label)

        header.addStretch()

        # Collapse button
        self._collapse_btn = QPushButton()
        self._collapse_btn.setFixedSize(32, 32)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                color: {palette.text_secondary};
            }}
            QPushButton:hover {{
                background-color: {palette.hover};
            }}
        """)
        self._update_collapse_button()
        self._collapse_btn.clicked.connect(self.toggle_collapsed)
        header.addWidget(self._collapse_btn)

        layout.addLayout(header)

        # Scroll area for nav items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet("border: none; background: transparent;")

        self._items_widget = QWidget()
        self._items_widget.setStyleSheet("background: transparent;")
        self._items_layout = QVBoxLayout(self._items_widget)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(4)
        self._items_layout.addStretch()

        scroll.setWidget(self._items_widget)
        layout.addWidget(scroll, 1)

        # Footer area (for user profile, settings, etc.)
        self._footer_layout = QVBoxLayout()
        self._footer_layout.setSpacing(4)
        layout.addLayout(self._footer_layout)

        # Connect theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode) -> None:
        """Handle theme change."""
        theme = get_theme_manager()
        palette = theme.current_palette
        self.setStyleSheet(f"""
            #sidebarWidget {{
                background-color: {palette.background_alt};
                border-right: 1px solid {palette.border};
            }}
        """)
        self._logo_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {palette.primary};
        """)
        self._collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                color: {palette.text_secondary};
            }}
            QPushButton:hover {{
                background-color: {palette.hover};
            }}
        """)

    def _update_width(self) -> None:
        """Update sidebar width based on collapsed state."""
        width = self._collapsed_width if self._collapsed else self._expanded_width
        self.setFixedWidth(width)

    def _update_collapse_button(self) -> None:
        """Update collapse button icon."""
        # Use arrows
        self._collapse_btn.setText("\u00ab" if not self._collapsed else "\u00bb")

    def add_item(
        self,
        item: NavItem,
        position: int = -1,
        is_footer: bool = False
    ) -> None:
        """
        Add a navigation item.

        Args:
            item: Navigation item to add
            position: Position in list (-1 for end)
            is_footer: Whether to add to footer section
        """
        sidebar_item = SidebarItem(
            parent=self._items_widget,
            item=item,
            collapsed=self._collapsed
        )
        sidebar_item.clicked.connect(self._on_item_clicked)

        self._items[item.id] = sidebar_item

        target_layout = self._footer_layout if is_footer else self._items_layout

        if position < 0:
            # Insert before the stretch
            target_layout.insertWidget(target_layout.count() - 1, sidebar_item)
        else:
            target_layout.insertWidget(position, sidebar_item)

    def add_section(self, label: str) -> None:
        """Add a section header."""
        theme = get_theme_manager()
        palette = theme.current_palette

        section_label = QLabel(label.upper())
        section_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {palette.text_disabled};
            padding: 16px 12px 8px 12px;
        """)
        if self._collapsed:
            section_label.hide()

        self._items_layout.insertWidget(
            self._items_layout.count() - 1, section_label
        )

    def add_separator(self) -> None:
        """Add a separator line."""
        theme = get_theme_manager()
        palette = theme.current_palette

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {palette.border};")
        separator.setFixedHeight(1)

        self._items_layout.insertWidget(
            self._items_layout.count() - 1, separator
        )

    def remove_item(self, item_id: str) -> None:
        """Remove a navigation item."""
        if item_id in self._items:
            item = self._items.pop(item_id)
            item.deleteLater()

    def select_item(self, item_id: str) -> None:
        """Select a navigation item."""
        if self._selected_id:
            if self._selected_id in self._items:
                self._items[self._selected_id].set_selected(False)

        self._selected_id = item_id
        if item_id in self._items:
            self._items[item_id].set_selected(True)

    def _on_item_clicked(self, item_id: str) -> None:
        """Handle item click."""
        self.select_item(item_id)
        self.item_selected.emit(item_id)

    def toggle_collapsed(self) -> None:
        """Toggle collapsed state."""
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Set collapsed state."""
        self._collapsed = collapsed
        self._update_width()
        self._update_collapse_button()

        # Update all items
        for item in self._items.values():
            item.set_collapsed(collapsed)

        # Show/hide logo
        self._logo_label.setVisible(not collapsed)

        self.collapsed_changed.emit(collapsed)

    @property
    def is_collapsed(self) -> bool:
        """Get collapsed state."""
        return self._collapsed


class BreadcrumbItem(QWidget):
    """Individual breadcrumb item."""

    clicked = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        item_id: str = "",
        label: str = "",
        is_last: bool = False
    ):
        """
        Initialize breadcrumb item.

        Args:
            parent: Parent widget
            item_id: Item identifier
            label: Display label
            is_last: Whether this is the last item
        """
        super().__init__(parent)

        self._item_id = item_id
        self._is_last = is_last

        self._setup_ui(label)

    def _setup_ui(self, label: str) -> None:
        """Setup the UI."""
        theme = get_theme_manager()
        palette = theme.current_palette

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        self._label = QPushButton(label)
        self._label.setFlat(True)

        if self._is_last:
            self._label.setEnabled(False)
            self._label.setStyleSheet(f"""
                QPushButton {{
                    color: {palette.text_primary};
                    font-weight: 600;
                    border: none;
                    padding: 4px 8px;
                }}
            """)
        else:
            self._label.setCursor(Qt.CursorShape.PointingHandCursor)
            self._label.setStyleSheet(f"""
                QPushButton {{
                    color: {palette.text_secondary};
                    border: none;
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    color: {palette.primary};
                    text-decoration: underline;
                }}
            """)
            self._label.clicked.connect(
                lambda: self.clicked.emit(self._item_id)
            )

        layout.addWidget(self._label)

        # Separator
        if not self._is_last:
            separator = QLabel("/")
            separator.setStyleSheet(f"color: {palette.text_disabled};")
            layout.addWidget(separator)


class Breadcrumb(QWidget):
    """
    Breadcrumb path display.

    Shows the current navigation path with clickable items.

    Usage:
        breadcrumb = Breadcrumb()
        breadcrumb.set_path([
            ("dashboard", "Dashboard"),
            ("transactions", "Transactions"),
            ("details", "Transaction Details")
        ])
        breadcrumb.item_clicked.connect(self.navigate_to)
    """

    item_clicked = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize breadcrumb.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._items: List[BreadcrumbItem] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addStretch()

    def set_path(self, path: List[tuple]) -> None:
        """
        Set the breadcrumb path.

        Args:
            path: List of (id, label) tuples
        """
        # Clear existing
        for item in self._items:
            item.deleteLater()
        self._items.clear()

        # Add new items
        for i, (item_id, label) in enumerate(path):
            is_last = i == len(path) - 1
            item = BreadcrumbItem(
                parent=self,
                item_id=item_id,
                label=label,
                is_last=is_last
            )
            item.clicked.connect(self.item_clicked.emit)
            self._items.append(item)
            self._layout.insertWidget(i, item)

    def push(self, item_id: str, label: str) -> None:
        """Add an item to the path."""
        # Update previous last item
        if self._items:
            # Recreate previous last item as non-last
            old_last = self._items[-1]
            old_id = old_last._item_id
            old_label = old_last._label.text()
            old_last.deleteLater()
            self._items.pop()

            new_item = BreadcrumbItem(
                parent=self,
                item_id=old_id,
                label=old_label,
                is_last=False
            )
            new_item.clicked.connect(self.item_clicked.emit)
            self._items.append(new_item)
            self._layout.insertWidget(len(self._items) - 1, new_item)

        # Add new last item
        item = BreadcrumbItem(
            parent=self,
            item_id=item_id,
            label=label,
            is_last=True
        )
        item.clicked.connect(self.item_clicked.emit)
        self._items.append(item)
        self._layout.insertWidget(len(self._items) - 1, item)

    def pop(self) -> Optional[str]:
        """Remove the last item from the path."""
        if len(self._items) > 1:
            removed = self._items.pop()
            removed_id = removed._item_id
            removed.deleteLater()

            # Update new last item
            if self._items:
                last = self._items[-1]
                last_id = last._item_id
                last_label = last._label.text()
                last.deleteLater()
                self._items.pop()

                new_last = BreadcrumbItem(
                    parent=self,
                    item_id=last_id,
                    label=last_label,
                    is_last=True
                )
                new_last.clicked.connect(self.item_clicked.emit)
                self._items.append(new_last)
                self._layout.insertWidget(len(self._items) - 1, new_last)

            return removed_id
        return None


class TabBar(QWidget):
    """
    Custom tab bar widget.

    Provides a horizontal tab bar with animated indicator.

    Usage:
        tabs = TabBar()
        tabs.add_tab("overview", "Overview")
        tabs.add_tab("details", "Details")
        tabs.add_tab("history", "History")
        tabs.tab_changed.connect(self.switch_view)
    """

    tab_changed = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        stretch: bool = False
    ):
        """
        Initialize tab bar.

        Args:
            parent: Parent widget
            stretch: Whether tabs should stretch to fill width
        """
        super().__init__(parent)

        self._tabs: Dict[str, QPushButton] = {}
        self._selected_id: Optional[str] = None
        self._stretch = stretch

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI components."""
        theme = get_theme_manager()
        palette = theme.current_palette

        self.setObjectName("tabBar")
        self.setStyleSheet(f"""
            #tabBar {{
                background-color: transparent;
                border-bottom: 1px solid {palette.border};
            }}
        """)
        self.setFixedHeight(48)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        if not self._stretch:
            self._layout.addStretch()

        # Indicator line (animated)
        self._indicator = QFrame(self)
        self._indicator.setFixedHeight(2)
        self._indicator.setStyleSheet(f"background-color: {palette.primary};")
        self._indicator.hide()

        # Indicator animation
        self._indicator_anim = QPropertyAnimation(self._indicator, b"geometry")
        self._indicator_anim.setDuration(200)
        self._indicator_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Connect theme changes
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, mode) -> None:
        """Handle theme change."""
        theme = get_theme_manager()
        palette = theme.current_palette
        self.setStyleSheet(f"""
            #tabBar {{
                background-color: transparent;
                border-bottom: 1px solid {palette.border};
            }}
        """)
        self._indicator.setStyleSheet(f"background-color: {palette.primary};")
        self._update_tab_styles()

    def _update_tab_styles(self) -> None:
        """Update all tab button styles."""
        theme = get_theme_manager()
        palette = theme.current_palette

        for tab_id, btn in self._tabs.items():
            if tab_id == self._selected_id:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {palette.primary};
                        font-weight: 600;
                        border: none;
                        padding: 12px 16px;
                        background-color: transparent;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {palette.text_secondary};
                        border: none;
                        padding: 12px 16px;
                        background-color: transparent;
                    }}
                    QPushButton:hover {{
                        color: {palette.text_primary};
                        background-color: {palette.hover};
                    }}
                """)

    def add_tab(
        self,
        tab_id: str,
        label: str,
        icon: Optional[str] = None
    ) -> None:
        """
        Add a tab.

        Args:
            tab_id: Tab identifier
            label: Tab label
            icon: Optional icon path
        """
        theme = get_theme_manager()
        palette = theme.current_palette

        btn = QPushButton(label)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {palette.text_secondary};
                border: none;
                padding: 12px 16px;
                background-color: transparent;
            }}
            QPushButton:hover {{
                color: {palette.text_primary};
                background-color: {palette.hover};
            }}
        """)

        if icon:
            btn.setIcon(QIcon(icon))

        btn.clicked.connect(lambda: self._on_tab_clicked(tab_id))

        self._tabs[tab_id] = btn

        if self._stretch:
            self._layout.addWidget(btn, 1)
        else:
            # Insert before the stretch
            self._layout.insertWidget(self._layout.count() - 1, btn)

        # Select first tab automatically
        if len(self._tabs) == 1:
            self.select_tab(tab_id)

    def remove_tab(self, tab_id: str) -> None:
        """Remove a tab."""
        if tab_id in self._tabs:
            btn = self._tabs.pop(tab_id)
            btn.deleteLater()

            if self._selected_id == tab_id:
                self._selected_id = None
                # Select first remaining tab
                if self._tabs:
                    self.select_tab(list(self._tabs.keys())[0])

    def select_tab(self, tab_id: str) -> None:
        """Select a tab."""
        if tab_id not in self._tabs:
            return

        self._selected_id = tab_id
        self._update_tab_styles()
        self._update_indicator()

    def _on_tab_clicked(self, tab_id: str) -> None:
        """Handle tab click."""
        if tab_id != self._selected_id:
            self.select_tab(tab_id)
            self.tab_changed.emit(tab_id)

    def _update_indicator(self) -> None:
        """Update indicator position."""
        if not self._selected_id or self._selected_id not in self._tabs:
            self._indicator.hide()
            return

        btn = self._tabs[self._selected_id]
        btn_geo = btn.geometry()

        # Calculate indicator position
        x = btn_geo.x()
        y = self.height() - 2
        width = btn_geo.width()
        height = 2

        if self._indicator.isHidden():
            self._indicator.setGeometry(x, y, width, height)
            self._indicator.show()
        else:
            # Animate to new position
            from PyQt6.QtCore import QRect
            self._indicator_anim.setStartValue(self._indicator.geometry())
            self._indicator_anim.setEndValue(QRect(x, y, width, height))
            self._indicator_anim.start()

    def resizeEvent(self, event) -> None:
        """Handle resize to update indicator."""
        super().resizeEvent(event)
        # Update indicator without animation
        if self._selected_id and self._selected_id in self._tabs:
            btn = self._tabs[self._selected_id]
            btn_geo = btn.geometry()
            self._indicator.setGeometry(
                btn_geo.x(),
                self.height() - 2,
                btn_geo.width(),
                2
            )

    @property
    def selected_tab(self) -> Optional[str]:
        """Get selected tab ID."""
        return self._selected_id

    @property
    def tab_count(self) -> int:
        """Get number of tabs."""
        return len(self._tabs)
