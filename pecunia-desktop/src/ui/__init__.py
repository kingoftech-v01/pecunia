"""
Pecunia Desktop UI Module

This module contains all UI components for the desktop application.
Built with PyQt6 for a modern, cross-platform experience.
"""

from .pages import (
    DashboardPage,
    TransactionsPage,
    BudgetsPage,
    SettingsPage,
    LoginPage,
    RegisterPage
)

from .widgets import (
    PieChartWidget,
    BarChartWidget,
    LineChartWidget,
    DataTableWidget,
    TransactionTableWidget,
    BudgetTableWidget,
    FormWidget,
    TransactionForm,
    BudgetForm,
    LoginForm,
    RegisterForm
)

from .styles import ThemeManager, Theme

__all__ = [
    # Pages
    'DashboardPage',
    'TransactionsPage',
    'BudgetsPage',
    'SettingsPage',
    'LoginPage',
    'RegisterPage',
    # Widgets
    'PieChartWidget',
    'BarChartWidget',
    'LineChartWidget',
    'DataTableWidget',
    'TransactionTableWidget',
    'BudgetTableWidget',
    'FormWidget',
    'TransactionForm',
    'BudgetForm',
    'LoginForm',
    'RegisterForm',
    # Styles
    'ThemeManager',
    'Theme'
]
