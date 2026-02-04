"""
Pecunia Desktop Widgets Module

Reusable UI widgets for charts, tables, forms, dialogs,
notifications, cards, navigation, inputs, and validation.
"""

# ============================================================================
# Chart Widgets - Base and Configuration
# ============================================================================
from .charts import (
    # Base classes
    BaseChart,
    ChartAnimationMixin,

    # Configuration
    ChartConfig,
    ChartDataPoint,
    ChartSeries,
    ColorScheme,

    # Enums
    ChartType,
    AnimationType,
    LegendPosition,

    # Color schemes
    LIGHT_SCHEME,
    DARK_SCHEME,
    FINANCE_SCHEME,
    CATEGORY_COLORS,

    # Utility functions
    get_category_color,
    get_scheme_for_mode,
    create_chart,
)

# ============================================================================
# Pie Chart Widgets
# ============================================================================
from .pie_chart import (
    PieChart,
    DonutChart,
    PieChartCanvas,

    # Convenience functions
    create_pie_chart,
    create_donut_chart,
)

# ============================================================================
# Line Chart Widgets
# ============================================================================
from .line_chart import (
    LineChart,
    LineChartCanvas,
    LineChartConfig,

    # Convenience functions
    create_line_chart,
)

# ============================================================================
# Bar Chart Widgets
# ============================================================================
from .bar_chart import (
    BarChart,
    BarChartCanvas,
    BarChartConfig,
    BarOrientation,
    BarMode,

    # Convenience functions
    create_bar_chart,
    create_grouped_bar_chart,
)

# ============================================================================
# Progress Chart Widgets
# ============================================================================
from .progress_chart import (
    ProgressChart,
    ProgressBarWidget,
    CircularProgressWidget,
    BudgetSummaryWidget,
    ProgressChartConfig,
    ProgressStyle,
    ProgressZone,
    BudgetItem,

    # Convenience functions
    create_progress_chart,
    create_budget_dashboard,
)

# ============================================================================
# Table Widgets
# ============================================================================
from .tables import (
    # Virtual Table View
    VirtualTableView,
    # Delegates
    CurrencyDelegate,
    DateDelegate,
    ProgressDelegate,
    ColoredTextDelegate,
    CategoryColorDelegate,
    # Widgets
    EmptyStateWidget,
    TablePagination,
    SortableTableWidget,
    DataTableWidget,
    TransactionTableWidget,
    BudgetTableWidget,
    CategoryTableWidget,
    AccountTableWidget
)

from .table_models import (
    # Column Definition
    ColumnType,
    ColumnDefinition,
    # Base Model
    BaseTableModel,
    # Specialized Models
    TransactionTableModel,
    BudgetTableModel,
    CategoryTableModel,
    AccountTableModel,
    # Proxy Model
    FilterSortProxyModel
)

from .delegates import (
    # Amount/Currency
    AmountDelegate,
    # Date
    DateDelegate as DateDelegateAdvanced,
    # Category
    CategoryDelegate,
    # Progress
    ProgressDelegate as ProgressDelegateAdvanced,
    # Actions
    ActionDelegate,
    # Boolean
    BooleanDelegate,
    # Status
    StatusDelegate,
    # Rating
    RatingDelegate
)

from .table_header import (
    # Enums
    SortDirection,
    # Header Views
    SortableHeader,
    # Filter Widgets
    FilterHeaderWidget,
    ColumnVisibilityMenu,
    QuickFilterToolbar
)

# ============================================================================
# Form Widgets
# ============================================================================
from .forms import (
    # Base classes
    FormWidget,
    FormMode,
    FormField,
    # Pre-built forms
    TransactionForm,
    BudgetForm,
    LoginForm,
    RegisterForm,
    # Legacy widgets (kept for compatibility)
    ValidatedLineEdit,
    CurrencyInput,
    MoneySpinBox,
    DatePicker,
    CategoryComboBox,
    SearchInput as FormSearchInput,
    ColorPicker,
    FormSection as FormGroupSection,
    FormButtons as FormButtonRow,
)

from .form_layout import (
    FormRow,
    FormSection,
    FormButtons,
    FormGrid,
    ScrollableForm,
    FormCard
)

from .inputs import (
    AmountInput,
    DateInput,
    DateRangeInput,
    CategorySelector,
    TagInput,
    SearchInput,
    PasswordInput,
    NumericInput
)

from .validators import (
    # Base classes
    BaseValidator,
    ValidationResult,
    CustomValidator,
    CompositeValidator,
    # Specific validators
    RequiredValidator,
    AmountValidator,
    DateValidator,
    EmailValidator,
    PasswordValidator,
    PhoneValidator,
    URLValidator,
    # Factory functions
    create_required_validator,
    create_amount_validator,
    create_email_validator,
    create_password_validator,
    create_date_validator
)

# ============================================================================
# Common Widgets
# ============================================================================
from .common import (
    LoadingSpinner,
    EmptyState,
    ErrorWidget,
    Badge,
    Avatar,
    AnimatedWidget,
    Separator
)

# ============================================================================
# Dialog Widgets
# ============================================================================
from .dialogs import (
    DialogType,
    BaseDialog,
    ConfirmDialog,
    MessageDialog,
    InputDialog,
    ProgressDialog,
    # Convenience functions
    show_info,
    show_warning,
    show_error,
    show_success,
    confirm,
    get_input
)

# ============================================================================
# Notification Widgets
# ============================================================================
from .notifications import (
    NotificationType,
    NotificationData,
    ToastNotification,
    NotificationManager,
    NotificationCenter,
    # Convenience functions
    notify,
    notify_success,
    notify_error,
    notify_warning,
    notify_info
)

# ============================================================================
# Card Widgets
# ============================================================================
from .cards import (
    Card,
    TrendDirection,
    StatCard,
    TransactionCard,
    BudgetCard,
    AccountCard,
    SummaryCard
)

# ============================================================================
# Navigation Widgets
# ============================================================================
from .navigation import (
    NavItem,
    SidebarItem,
    Sidebar,
    BreadcrumbItem,
    Breadcrumb,
    TabBar
)

# ============================================================================
# Legacy Compatibility Aliases
# ============================================================================
# These aliases maintain backward compatibility with the previous API
BaseChartWidget = BaseChart
PieChartWidget = PieChart
BarChartWidget = BarChart
LineChartWidget = LineChart
DonutChartWidget = DonutChart
BudgetProgressChart = ProgressChart

__all__ = [
    # ========== Chart Base ==========
    'BaseChart',
    'ChartAnimationMixin',
    'ChartConfig',
    'ChartDataPoint',
    'ChartSeries',
    'ColorScheme',
    'ChartType',
    'AnimationType',
    'LegendPosition',
    'LIGHT_SCHEME',
    'DARK_SCHEME',
    'FINANCE_SCHEME',
    'CATEGORY_COLORS',
    'get_category_color',
    'get_scheme_for_mode',
    'create_chart',

    # ========== Pie Charts ==========
    'PieChart',
    'DonutChart',
    'PieChartCanvas',
    'create_pie_chart',
    'create_donut_chart',

    # ========== Line Charts ==========
    'LineChart',
    'LineChartCanvas',
    'LineChartConfig',
    'create_line_chart',

    # ========== Bar Charts ==========
    'BarChart',
    'BarChartCanvas',
    'BarChartConfig',
    'BarOrientation',
    'BarMode',
    'create_bar_chart',
    'create_grouped_bar_chart',

    # ========== Progress Charts ==========
    'ProgressChart',
    'ProgressBarWidget',
    'CircularProgressWidget',
    'BudgetSummaryWidget',
    'ProgressChartConfig',
    'ProgressStyle',
    'ProgressZone',
    'BudgetItem',
    'create_progress_chart',
    'create_budget_dashboard',

    # ========== Legacy Chart Aliases ==========
    'BaseChartWidget',
    'PieChartWidget',
    'BarChartWidget',
    'LineChartWidget',
    'DonutChartWidget',
    'BudgetProgressChart',

    # ========== Virtual Table View ==========
    'VirtualTableView',

    # ========== Table Delegates (basic) ==========
    'CurrencyDelegate',
    'DateDelegate',
    'ProgressDelegate',
    'ColoredTextDelegate',
    'CategoryColorDelegate',

    # ========== Table Widgets ==========
    'EmptyStateWidget',
    'TablePagination',
    'SortableTableWidget',
    'DataTableWidget',
    'TransactionTableWidget',
    'BudgetTableWidget',
    'CategoryTableWidget',
    'AccountTableWidget',

    # ========== Table Models ==========
    'ColumnType',
    'ColumnDefinition',
    'BaseTableModel',
    'TransactionTableModel',
    'BudgetTableModel',
    'CategoryTableModel',
    'AccountTableModel',
    'FilterSortProxyModel',

    # ========== Advanced Delegates ==========
    'AmountDelegate',
    'DateDelegateAdvanced',
    'CategoryDelegate',
    'ProgressDelegateAdvanced',
    'ActionDelegate',
    'BooleanDelegate',
    'StatusDelegate',
    'RatingDelegate',

    # ========== Table Headers ==========
    'SortDirection',
    'SortableHeader',
    'FilterHeaderWidget',
    'ColumnVisibilityMenu',
    'QuickFilterToolbar',

    # ========== Form Base Classes ==========
    'FormWidget',
    'FormMode',
    'FormField',

    # ========== Pre-built Forms ==========
    'TransactionForm',
    'BudgetForm',
    'LoginForm',
    'RegisterForm',

    # ========== Form Layout Components ==========
    'FormRow',
    'FormSection',
    'FormButtons',
    'FormGrid',
    'ScrollableForm',
    'FormCard',

    # ========== Legacy Form Widgets ==========
    'ValidatedLineEdit',
    'CurrencyInput',
    'MoneySpinBox',
    'DatePicker',
    'CategoryComboBox',
    'FormSearchInput',
    'ColorPicker',
    'FormGroupSection',
    'FormButtonRow',

    # ========== Specialized Inputs ==========
    'AmountInput',
    'DateInput',
    'DateRangeInput',
    'CategorySelector',
    'TagInput',
    'SearchInput',
    'PasswordInput',
    'NumericInput',

    # ========== Validators - Base ==========
    'BaseValidator',
    'ValidationResult',
    'CustomValidator',
    'CompositeValidator',

    # ========== Validators - Specific ==========
    'RequiredValidator',
    'AmountValidator',
    'DateValidator',
    'EmailValidator',
    'PasswordValidator',
    'PhoneValidator',
    'URLValidator',

    # ========== Validator Factory Functions ==========
    'create_required_validator',
    'create_amount_validator',
    'create_email_validator',
    'create_password_validator',
    'create_date_validator',

    # ========== Common Widgets ==========
    'LoadingSpinner',
    'EmptyState',
    'ErrorWidget',
    'Badge',
    'Avatar',
    'AnimatedWidget',
    'Separator',

    # ========== Dialogs ==========
    'DialogType',
    'BaseDialog',
    'ConfirmDialog',
    'MessageDialog',
    'InputDialog',
    'ProgressDialog',
    'show_info',
    'show_warning',
    'show_error',
    'show_success',
    'confirm',
    'get_input',

    # ========== Notifications ==========
    'NotificationType',
    'NotificationData',
    'ToastNotification',
    'NotificationManager',
    'NotificationCenter',
    'notify',
    'notify_success',
    'notify_error',
    'notify_warning',
    'notify_info',

    # ========== Cards ==========
    'Card',
    'TrendDirection',
    'StatCard',
    'TransactionCard',
    'BudgetCard',
    'AccountCard',
    'SummaryCard',

    # ========== Navigation ==========
    'NavItem',
    'SidebarItem',
    'Sidebar',
    'BreadcrumbItem',
    'Breadcrumb',
    'TabBar',
]
