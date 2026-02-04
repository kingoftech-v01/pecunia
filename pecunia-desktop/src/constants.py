"""
Application constants for Pecunia Desktop.

This module contains all constant values used throughout the application,
including configuration, API endpoints, database schema, UI settings,
and localized messages.
"""

from enum import Enum, IntEnum
from typing import Dict, Tuple

# =============================================================================
# APPLICATION INFORMATION
# =============================================================================

APP_NAME = "Pecunia Desktop"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Pecunia Team"
APP_ORGANIZATION = "Pecunia Inc."
APP_DOMAIN = "pecunia.com"
APP_IDENTIFIER = "com.pecunia.desktop"

# =============================================================================
# API CONFIGURATION
# =============================================================================

DEFAULT_API_BASE_URL = "https://localhost:8000/api/v1"
PRODUCTION_API_BASE_URL = "https://api.pecunia.com/v1"
API_TIMEOUT_SECONDS = 30
API_MAX_RETRIES = 3
API_RETRY_DELAY_SECONDS = 1

# Token Configuration
ACCESS_TOKEN_KEY = "access_token"
REFRESH_TOKEN_KEY = "refresh_token"
TOKEN_TYPE_KEY = "token_type"
TOKEN_EXPIRY_KEY = "token_expiry"

# Secure Storage Keys
KEYRING_SERVICE_NAME = "Pecunia"
KEYRING_ACCESS_TOKEN = "access_token"
KEYRING_REFRESH_TOKEN = "refresh_token"

# HTTP Headers
HEADER_AUTHORIZATION = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_ACCEPT = "Accept"

# Content Types
CONTENT_TYPE_JSON = "application/json"

# =============================================================================
# API ENDPOINTS
# =============================================================================

class APIEndpoints:
    """API endpoint paths for the backend service."""

    # Authentication
    AUTH_LOGIN = "/auth/login"
    AUTH_LOGOUT = "/auth/logout"
    AUTH_REFRESH = "/auth/refresh"
    AUTH_REGISTER = "/auth/register"
    AUTH_ME = "/auth/me"
    AUTH_CHANGE_PASSWORD = "/auth/change-password"
    AUTH_RESET_PASSWORD = "/auth/reset-password"
    AUTH_VERIFY_EMAIL = "/auth/verify-email"

    # User management
    USER_PROFILE = "/users/profile"
    USER_SETTINGS = "/users/settings"
    USER_PREFERENCES = "/users/preferences"

    # Accounts
    ACCOUNTS = "/accounts"
    ACCOUNTS_BY_ID = "/accounts/{account_id}"
    ACCOUNTS_BALANCE = "/accounts/{account_id}/balance"
    ACCOUNTS_TRANSACTIONS = "/accounts/{account_id}/transactions"

    # Transactions
    TRANSACTIONS = "/transactions"
    TRANSACTIONS_BY_ID = "/transactions/{id}"
    TRANSACTIONS_SUMMARY = "/transactions/summary"
    TRANSACTIONS_SEARCH = "/transactions/search"
    TRANSACTIONS_BULK = "/transactions/bulk"
    TRANSACTIONS_IMPORT = "/transactions/import"
    TRANSACTIONS_EXPORT = "/transactions/export"
    TRANSACTIONS_CATEGORIES = "/transactions/categories"

    # Budgets
    BUDGETS = "/budgets"
    BUDGETS_BY_ID = "/budgets/{id}"
    BUDGETS_PROGRESS = "/budgets/{id}/progress"
    BUDGETS_ALERTS = "/budgets/alerts"

    # Categories
    CATEGORIES = "/categories"
    CATEGORIES_BY_ID = "/categories/{category_id}"

    # Reports
    REPORTS_SUMMARY = "/reports/summary"
    REPORTS_SPENDING = "/reports/spending"
    REPORTS_INCOME = "/reports/income"
    REPORTS_TRENDS = "/reports/trends"
    REPORTS_EXPORT = "/reports/export"

    # Banking / Plaid
    BANKING_LINK_TOKEN = "/banking/link-token"
    BANKING_EXCHANGE_TOKEN = "/banking/exchange-token"
    BANKING_ACCOUNTS = "/banking/accounts"
    BANKING_ACCOUNTS_BY_ID = "/banking/accounts/{id}"
    BANKING_SYNC = "/banking/sync"
    BANKING_INSTITUTIONS = "/banking/institutions"

    # Sync
    SYNC_STATUS = "/sync/status"
    SYNC_PUSH = "/sync/push"
    SYNC_PULL = "/sync/pull"
    SYNC_RESOLVE = "/sync/resolve"


# Alias for backward compatibility
Endpoints = APIEndpoints

# =============================================================================
# DATABASE TABLE NAMES
# =============================================================================

class DatabaseTables:
    """Database table names for SQLite local storage."""

    # Core tables
    USERS = "users"
    ACCOUNTS = "accounts"
    TRANSACTIONS = "transactions"
    CATEGORIES = "categories"
    BUDGETS = "budgets"
    BUDGET_CATEGORIES = "budget_categories"

    # Settings and preferences
    SETTINGS = "settings"
    PREFERENCES = "preferences"

    # Sync management
    SYNC_LOG = "sync_log"
    SYNC_QUEUE = "sync_queue"
    SYNC_CONFLICTS = "sync_conflicts"

    # Audit and history
    AUDIT_LOG = "audit_log"
    TRANSACTION_HISTORY = "transaction_history"

    # Tags and labels
    TAGS = "tags"
    TRANSACTION_TAGS = "transaction_tags"

    # Attachments
    ATTACHMENTS = "attachments"

    # Recurring transactions
    RECURRING_TRANSACTIONS = "recurring_transactions"

    # Banking links
    LINKED_ACCOUNTS = "linked_accounts"
    INSTITUTIONS = "institutions"

# =============================================================================
# SYNC STATUS CODES
# =============================================================================

class SyncStatus(IntEnum):
    """Synchronization status codes."""

    # Success states
    SUCCESS = 0
    UP_TO_DATE = 1
    SYNCED = 2

    # Pending states
    PENDING = 10
    IN_PROGRESS = 11
    QUEUED = 12

    # Warning states
    PARTIAL_SYNC = 20
    CONFLICT_DETECTED = 21
    MANUAL_REVIEW_REQUIRED = 22

    # Error states
    ERROR_NETWORK = 30
    ERROR_AUTH = 31
    ERROR_SERVER = 32
    ERROR_TIMEOUT = 33
    ERROR_DATA_VALIDATION = 34
    ERROR_CONFLICT_RESOLUTION = 35
    ERROR_UNKNOWN = 39

# =============================================================================
# TRANSACTION TYPES
# =============================================================================

class TransactionType(str, Enum):
    """Types of financial transactions."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    OPENING_BALANCE = "opening_balance"
    RECONCILIATION = "reconciliation"

# =============================================================================
# TRANSACTION CATEGORIES
# =============================================================================

class TransactionCategory(str, Enum):
    """Predefined transaction categories."""

    # Income categories
    SALARY = "salary"
    FREELANCE = "freelance"
    INVESTMENTS = "investments"
    RENTAL_INCOME = "rental_income"
    GIFTS_RECEIVED = "gifts_received"
    BONUS = "bonus"
    INTEREST = "interest"
    DIVIDENDS = "dividends"
    OTHER_INCOME = "other_income"

    # Expense categories - Housing
    RENT = "rent"
    MORTGAGE = "mortgage"
    UTILITIES = "utilities"
    HOME_INSURANCE = "home_insurance"
    HOME_MAINTENANCE = "home_maintenance"
    PROPERTY_TAX = "property_tax"

    # Expense categories - Transportation
    FUEL = "fuel"
    PUBLIC_TRANSPORT = "public_transport"
    CAR_INSURANCE = "car_insurance"
    CAR_MAINTENANCE = "car_maintenance"
    PARKING = "parking"
    RIDESHARE = "rideshare"

    # Expense categories - Food
    GROCERIES = "groceries"
    RESTAURANTS = "restaurants"
    COFFEE_SHOPS = "coffee_shops"
    FOOD_DELIVERY = "food_delivery"

    # Expense categories - Health
    HEALTHCARE = "healthcare"
    PHARMACY = "pharmacy"
    GYM_FITNESS = "gym_fitness"
    MEDICAL_INSURANCE = "medical_insurance"

    # Expense categories - Entertainment
    ENTERTAINMENT = "entertainment"
    STREAMING_SERVICES = "streaming_services"
    HOBBIES = "hobbies"
    TRAVEL = "travel"
    VACATION = "vacation"

    # Expense categories - Shopping
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    HOME_GOODS = "home_goods"
    PERSONAL_CARE = "personal_care"

    # Expense categories - Financial
    BANK_FEES = "bank_fees"
    TAXES = "taxes"
    INSURANCE = "insurance"
    LOAN_PAYMENTS = "loan_payments"
    CREDIT_CARD_PAYMENT = "credit_card_payment"

    # Expense categories - Personal
    EDUCATION = "education"
    CHILDCARE = "childcare"
    PET_CARE = "pet_care"
    GIFTS_GIVEN = "gifts_given"
    DONATIONS = "donations"
    SUBSCRIPTIONS = "subscriptions"

    # Other
    UNCATEGORIZED = "uncategorized"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    OTHER = "other"


# Category labels for display (English)
CATEGORY_LABELS_EN: Dict[str, str] = {
    "salary": "Salary",
    "freelance": "Freelance Income",
    "investments": "Investments",
    "rental_income": "Rental Income",
    "gifts_received": "Gifts Received",
    "bonus": "Bonus",
    "interest": "Interest",
    "dividends": "Dividends",
    "other_income": "Other Income",
    "rent": "Rent",
    "mortgage": "Mortgage",
    "utilities": "Utilities",
    "home_insurance": "Home Insurance",
    "home_maintenance": "Home Maintenance",
    "property_tax": "Property Tax",
    "fuel": "Fuel",
    "public_transport": "Public Transport",
    "car_insurance": "Car Insurance",
    "car_maintenance": "Car Maintenance",
    "parking": "Parking",
    "rideshare": "Rideshare",
    "groceries": "Groceries",
    "restaurants": "Restaurants",
    "coffee_shops": "Coffee Shops",
    "food_delivery": "Food Delivery",
    "healthcare": "Healthcare",
    "pharmacy": "Pharmacy",
    "gym_fitness": "Gym & Fitness",
    "medical_insurance": "Medical Insurance",
    "entertainment": "Entertainment",
    "streaming_services": "Streaming Services",
    "hobbies": "Hobbies",
    "travel": "Travel",
    "vacation": "Vacation",
    "clothing": "Clothing",
    "electronics": "Electronics",
    "home_goods": "Home Goods",
    "personal_care": "Personal Care",
    "bank_fees": "Bank Fees",
    "taxes": "Taxes",
    "insurance": "Insurance",
    "loan_payments": "Loan Payments",
    "credit_card_payment": "Credit Card Payment",
    "education": "Education",
    "childcare": "Childcare",
    "pet_care": "Pet Care",
    "gifts_given": "Gifts Given",
    "donations": "Donations",
    "subscriptions": "Subscriptions",
    "uncategorized": "Uncategorized",
    "transfer_out": "Transfer Out",
    "transfer_in": "Transfer In",
    "other": "Other",
}

# Category labels for display (French)
CATEGORY_LABELS_FR: Dict[str, str] = {
    "salary": "Salaire",
    "freelance": "Revenus Freelance",
    "investments": "Investissements",
    "rental_income": "Revenus Locatifs",
    "gifts_received": "Cadeaux Recus",
    "bonus": "Prime",
    "interest": "Interets",
    "dividends": "Dividendes",
    "other_income": "Autres Revenus",
    "rent": "Loyer",
    "mortgage": "Hypotheque",
    "utilities": "Services Publics",
    "home_insurance": "Assurance Habitation",
    "home_maintenance": "Entretien Maison",
    "property_tax": "Taxe Fonciere",
    "fuel": "Carburant",
    "public_transport": "Transport en Commun",
    "car_insurance": "Assurance Auto",
    "car_maintenance": "Entretien Auto",
    "parking": "Stationnement",
    "rideshare": "VTC",
    "groceries": "Epicerie",
    "restaurants": "Restaurants",
    "coffee_shops": "Cafes",
    "food_delivery": "Livraison Repas",
    "healthcare": "Sante",
    "pharmacy": "Pharmacie",
    "gym_fitness": "Gym et Fitness",
    "medical_insurance": "Assurance Maladie",
    "entertainment": "Divertissement",
    "streaming_services": "Services de Streaming",
    "hobbies": "Loisirs",
    "travel": "Voyage",
    "vacation": "Vacances",
    "clothing": "Vetements",
    "electronics": "Electronique",
    "home_goods": "Articles Menagers",
    "personal_care": "Soins Personnels",
    "bank_fees": "Frais Bancaires",
    "taxes": "Impots",
    "insurance": "Assurance",
    "loan_payments": "Remboursement Pret",
    "credit_card_payment": "Paiement Carte Credit",
    "education": "Education",
    "childcare": "Garde d'Enfants",
    "pet_care": "Soins Animaux",
    "gifts_given": "Cadeaux Offerts",
    "donations": "Dons",
    "subscriptions": "Abonnements",
    "uncategorized": "Non Categorise",
    "transfer_out": "Virement Sortant",
    "transfer_in": "Virement Entrant",
    "other": "Autre",
}

# =============================================================================
# BUDGET PERIODS
# =============================================================================

class BudgetPeriod(str, Enum):
    """Budget time periods."""

    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    YEARLY = "yearly"
    ANNUAL = "annual"
    CUSTOM = "custom"


# Days in each budget period (approximate for calculations)
BUDGET_PERIOD_DAYS: Dict[str, int] = {
    "daily": 1,
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,
    "quarterly": 91,
    "semi_annual": 182,
    "yearly": 365,
    "annual": 365,
    "custom": 0,
}

# Budget period labels (English)
BUDGET_PERIOD_LABELS_EN: Dict[str, str] = {
    "daily": "Daily",
    "weekly": "Weekly",
    "biweekly": "Bi-weekly",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "semi_annual": "Semi-Annual",
    "yearly": "Yearly",
    "annual": "Annual",
    "custom": "Custom",
}

# Budget period labels (French)
BUDGET_PERIOD_LABELS_FR: Dict[str, str] = {
    "daily": "Quotidien",
    "weekly": "Hebdomadaire",
    "biweekly": "Bi-hebdomadaire",
    "monthly": "Mensuel",
    "quarterly": "Trimestriel",
    "semi_annual": "Semestriel",
    "yearly": "Annuel",
    "annual": "Annuel",
    "custom": "Personnalise",
}

# =============================================================================
# DATE AND TIME FORMATS
# =============================================================================

class DateTimeFormats:
    """Date and time format strings."""

    # ISO formats
    ISO_DATE = "%Y-%m-%d"
    ISO_TIME = "%H:%M:%S"
    ISO_DATETIME = "%Y-%m-%dT%H:%M:%S"
    ISO_DATETIME_TZ = "%Y-%m-%dT%H:%M:%S%z"

    # Display formats - English
    DATE_DISPLAY_EN = "%B %d, %Y"  # January 15, 2025
    DATE_SHORT_EN = "%m/%d/%Y"     # 01/15/2025
    DATE_MEDIUM_EN = "%b %d, %Y"   # Jan 15, 2025
    TIME_DISPLAY_EN = "%I:%M %p"   # 02:30 PM
    TIME_24H = "%H:%M"             # 14:30
    DATETIME_DISPLAY_EN = "%B %d, %Y at %I:%M %p"

    # Display formats - French
    DATE_DISPLAY_FR = "%d %B %Y"   # 15 janvier 2025
    DATE_SHORT_FR = "%d/%m/%Y"     # 15/01/2025
    DATE_MEDIUM_FR = "%d %b %Y"    # 15 janv. 2025
    TIME_DISPLAY_FR = "%H:%M"      # 14:30
    DATETIME_DISPLAY_FR = "%d %B %Y a %H:%M"

    # Database format
    DATABASE_DATETIME = "%Y-%m-%d %H:%M:%S"
    DATABASE_DATE = "%Y-%m-%d"

    # File naming
    FILE_TIMESTAMP = "%Y%m%d_%H%M%S"


# Backward compatibility aliases
DATE_FORMAT_DISPLAY = DateTimeFormats.DATE_DISPLAY_EN
DATE_FORMAT_SHORT = DateTimeFormats.DATE_SHORT_EN
DATE_FORMAT_ISO = DateTimeFormats.ISO_DATE
DATETIME_FORMAT_DISPLAY = DateTimeFormats.DATETIME_DISPLAY_EN
DATETIME_FORMAT_ISO = DateTimeFormats.ISO_DATETIME

# =============================================================================
# CURRENCY CODES AND SYMBOLS
# =============================================================================

class CurrencyCode(str, Enum):
    """ISO 4217 currency codes."""

    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    CAD = "CAD"  # Canadian Dollar
    CHF = "CHF"  # Swiss Franc
    JPY = "JPY"  # Japanese Yen
    AUD = "AUD"  # Australian Dollar
    NZD = "NZD"  # New Zealand Dollar
    CNY = "CNY"  # Chinese Yuan
    INR = "INR"  # Indian Rupee
    BRL = "BRL"  # Brazilian Real
    MXN = "MXN"  # Mexican Peso
    KRW = "KRW"  # South Korean Won
    SEK = "SEK"  # Swedish Krona
    NOK = "NOK"  # Norwegian Krone
    DKK = "DKK"  # Danish Krone
    PLN = "PLN"  # Polish Zloty
    RUB = "RUB"  # Russian Ruble
    ZAR = "ZAR"  # South African Rand
    SGD = "SGD"  # Singapore Dollar
    HKD = "HKD"  # Hong Kong Dollar


# Currency symbols mapping
CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "\u20ac",
    "GBP": "\u00a3",
    "CAD": "C$",
    "CHF": "CHF",
    "JPY": "\u00a5",
    "AUD": "A$",
    "NZD": "NZ$",
    "CNY": "\u00a5",
    "INR": "\u20b9",
    "BRL": "R$",
    "MXN": "MX$",
    "KRW": "\u20a9",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "PLN": "zl",
    "RUB": "\u20bd",
    "ZAR": "R",
    "SGD": "S$",
    "HKD": "HK$",
}

# Currency names (English)
CURRENCY_NAMES_EN: Dict[str, str] = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "JPY": "Japanese Yen",
    "AUD": "Australian Dollar",
    "NZD": "New Zealand Dollar",
    "CNY": "Chinese Yuan",
    "INR": "Indian Rupee",
    "BRL": "Brazilian Real",
    "MXN": "Mexican Peso",
    "KRW": "South Korean Won",
    "SEK": "Swedish Krona",
    "NOK": "Norwegian Krone",
    "DKK": "Danish Krone",
    "PLN": "Polish Zloty",
    "RUB": "Russian Ruble",
    "ZAR": "South African Rand",
    "SGD": "Singapore Dollar",
    "HKD": "Hong Kong Dollar",
}

# Currency names (French)
CURRENCY_NAMES_FR: Dict[str, str] = {
    "USD": "Dollar americain",
    "EUR": "Euro",
    "GBP": "Livre sterling",
    "CAD": "Dollar canadien",
    "CHF": "Franc suisse",
    "JPY": "Yen japonais",
    "AUD": "Dollar australien",
    "NZD": "Dollar neo-zelandais",
    "CNY": "Yuan chinois",
    "INR": "Roupie indienne",
    "BRL": "Real bresilien",
    "MXN": "Peso mexicain",
    "KRW": "Won sud-coreen",
    "SEK": "Couronne suedoise",
    "NOK": "Couronne norvegienne",
    "DKK": "Couronne danoise",
    "PLN": "Zloty polonais",
    "RUB": "Rouble russe",
    "ZAR": "Rand sud-africain",
    "SGD": "Dollar de Singapour",
    "HKD": "Dollar de Hong Kong",
}

# Currency decimal places
CURRENCY_DECIMALS: Dict[str, int] = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "CAD": 2,
    "CHF": 2,
    "JPY": 0,
    "AUD": 2,
    "NZD": 2,
    "CNY": 2,
    "INR": 2,
    "BRL": 2,
    "MXN": 2,
    "KRW": 0,
    "SEK": 2,
    "NOK": 2,
    "DKK": 2,
    "PLN": 2,
    "RUB": 2,
    "ZAR": 2,
    "SGD": 2,
    "HKD": 2,
}

# Default currency
DEFAULT_CURRENCY = "USD"

# =============================================================================
# UI DIMENSIONS
# =============================================================================

class UIDimensions:
    """UI dimension constants in pixels."""

    # Main window
    WINDOW_MIN_WIDTH = 1024
    WINDOW_MIN_HEIGHT = 768
    WINDOW_DEFAULT_WIDTH = 1280
    WINDOW_DEFAULT_HEIGHT = 900

    # Sidebar
    SIDEBAR_WIDTH = 250
    SIDEBAR_COLLAPSED_WIDTH = 60
    SIDEBAR_ITEM_HEIGHT = 48

    # Header
    HEADER_HEIGHT = 64

    # Content area
    CONTENT_PADDING = 24
    CONTENT_MAX_WIDTH = 1200

    # Cards
    CARD_PADDING = 16
    CARD_BORDER_RADIUS = 8
    CARD_MIN_HEIGHT = 120

    # Tables
    TABLE_ROW_HEIGHT = 48
    TABLE_HEADER_HEIGHT = 56
    TABLE_CELL_PADDING = 12

    # Buttons
    BUTTON_HEIGHT_SMALL = 32
    BUTTON_HEIGHT_MEDIUM = 40
    BUTTON_HEIGHT_LARGE = 48
    BUTTON_PADDING_HORIZONTAL = 16
    BUTTON_BORDER_RADIUS = 6

    # Input fields
    INPUT_HEIGHT = 40
    INPUT_PADDING = 12
    INPUT_BORDER_RADIUS = 6

    # Modals
    MODAL_WIDTH_SMALL = 400
    MODAL_WIDTH_MEDIUM = 600
    MODAL_WIDTH_LARGE = 800
    MODAL_PADDING = 24

    # Icons
    ICON_SIZE_SMALL = 16
    ICON_SIZE_MEDIUM = 24
    ICON_SIZE_LARGE = 32
    ICON_SIZE_XLARGE = 48

    # Spacing
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    SPACING_XXL = 48

    # Charts
    CHART_MIN_HEIGHT = 300
    CHART_LEGEND_HEIGHT = 40


# Backward compatibility aliases
WINDOW_MIN_WIDTH = UIDimensions.WINDOW_MIN_WIDTH
WINDOW_MIN_HEIGHT = UIDimensions.WINDOW_MIN_HEIGHT
SIDEBAR_WIDTH = UIDimensions.SIDEBAR_WIDTH
SIDEBAR_COLLAPSED_WIDTH = UIDimensions.SIDEBAR_COLLAPSED_WIDTH

# =============================================================================
# UI COLORS
# =============================================================================

class UIColors:
    """UI color constants in hex format."""

    # Primary brand colors
    PRIMARY = "#2563EB"
    PRIMARY_LIGHT = "#3B82F6"
    PRIMARY_DARK = "#1D4ED8"
    PRIMARY_HOVER = "#1E40AF"

    # Secondary colors
    SECONDARY = "#64748B"
    SECONDARY_LIGHT = "#94A3B8"
    SECONDARY_DARK = "#475569"

    # Accent colors
    ACCENT = "#8B5CF6"
    ACCENT_LIGHT = "#A78BFA"
    ACCENT_DARK = "#7C3AED"

    # Semantic colors - Success
    SUCCESS = "#10B981"
    SUCCESS_LIGHT = "#34D399"
    SUCCESS_DARK = "#059669"
    SUCCESS_BG = "#ECFDF5"

    # Semantic colors - Warning
    WARNING = "#F59E0B"
    WARNING_LIGHT = "#FBBF24"
    WARNING_DARK = "#D97706"
    WARNING_BG = "#FFFBEB"

    # Semantic colors - Error
    ERROR = "#EF4444"
    ERROR_LIGHT = "#F87171"
    ERROR_DARK = "#DC2626"
    ERROR_BG = "#FEF2F2"

    # Semantic colors - Info
    INFO = "#3B82F6"
    INFO_LIGHT = "#60A5FA"
    INFO_DARK = "#2563EB"
    INFO_BG = "#EFF6FF"

    # Neutral colors - Light theme
    BACKGROUND = "#FFFFFF"
    BACKGROUND_SECONDARY = "#F8FAFC"
    BACKGROUND_TERTIARY = "#F1F5F9"
    SURFACE = "#FFFFFF"
    BORDER = "#E2E8F0"
    BORDER_LIGHT = "#F1F5F9"

    # Text colors - Light theme
    TEXT_PRIMARY = "#1E293B"
    TEXT_SECONDARY = "#64748B"
    TEXT_TERTIARY = "#94A3B8"
    TEXT_DISABLED = "#CBD5E1"
    TEXT_INVERSE = "#FFFFFF"

    # Dark theme colors
    DARK_BACKGROUND = "#0F172A"
    DARK_BACKGROUND_SECONDARY = "#1E293B"
    DARK_BACKGROUND_TERTIARY = "#334155"
    DARK_SURFACE = "#1E293B"
    DARK_BORDER = "#334155"
    DARK_TEXT_PRIMARY = "#F8FAFC"
    DARK_TEXT_SECONDARY = "#94A3B8"
    DARK_TEXT_TERTIARY = "#64748B"

    # Transaction colors
    INCOME_COLOR = "#10B981"
    EXPENSE_COLOR = "#EF4444"
    TRANSFER_COLOR = "#3B82F6"

    # Chart colors palette
    CHART_COLORS: Tuple[str, ...] = (
        "#2563EB",
        "#10B981",
        "#F59E0B",
        "#EF4444",
        "#8B5CF6",
        "#EC4899",
        "#06B6D4",
        "#84CC16",
        "#F97316",
        "#6366F1",
    )

# =============================================================================
# ERROR MESSAGES - ENGLISH
# =============================================================================

class ErrorMessagesEN:
    """Error messages in English."""

    # Authentication errors
    AUTH_INVALID_CREDENTIALS = "Invalid email or password. Please try again."
    AUTH_SESSION_EXPIRED = "Your session has expired. Please log in again."
    AUTH_ACCOUNT_LOCKED = "Your account has been locked. Please contact support."
    AUTH_EMAIL_NOT_VERIFIED = "Please verify your email address to continue."
    AUTH_PASSWORD_TOO_WEAK = "Password must be at least 8 characters with uppercase, lowercase, and numbers."
    AUTH_REGISTRATION_FAILED = "Registration failed. Please try again later."
    AUTH_FAILED = "Authentication failed. Please log in again."
    TOKEN_EXPIRED = "Your session has expired. Please log in again."

    # Network errors
    NETWORK_ERROR = "Unable to connect to the server. Please check your internet connection."
    NETWORK_CONNECTION_FAILED = "Unable to connect to the server. Please check your internet connection."
    NETWORK_TIMEOUT = "The request timed out. Please try again."
    NETWORK_SERVER_ERROR = "Server error occurred. Please try again later."
    NETWORK_SERVICE_UNAVAILABLE = "Service is temporarily unavailable. Please try again later."
    SERVER_ERROR = "An unexpected error occurred. Please try again later."

    # Data validation errors
    VALIDATION_ERROR = "Please check your input and try again."
    VALIDATION_REQUIRED_FIELD = "This field is required."
    VALIDATION_INVALID_EMAIL = "Please enter a valid email address."
    VALIDATION_INVALID_AMOUNT = "Please enter a valid amount."
    VALIDATION_INVALID_DATE = "Please enter a valid date."
    VALIDATION_NEGATIVE_AMOUNT = "Amount cannot be negative."
    VALIDATION_AMOUNT_TOO_LARGE = "Amount exceeds the maximum allowed value."
    VALIDATION_FUTURE_DATE = "Date cannot be in the future."
    VALIDATION_DUPLICATE_ENTRY = "This entry already exists."

    # Transaction errors
    TRANSACTION_NOT_FOUND = "Transaction not found."
    TRANSACTION_CREATE_FAILED = "Failed to create transaction. Please try again."
    TRANSACTION_UPDATE_FAILED = "Failed to update transaction. Please try again."
    TRANSACTION_DELETE_FAILED = "Failed to delete transaction. Please try again."
    TRANSACTION_INSUFFICIENT_FUNDS = "Insufficient funds for this transaction."

    # Account errors
    ACCOUNT_NOT_FOUND = "Account not found."
    ACCOUNT_CREATE_FAILED = "Failed to create account. Please try again."
    ACCOUNT_UPDATE_FAILED = "Failed to update account. Please try again."
    ACCOUNT_DELETE_FAILED = "Failed to delete account. Please try again."
    ACCOUNT_HAS_TRANSACTIONS = "Cannot delete account with existing transactions."

    # Budget errors
    BUDGET_NOT_FOUND = "Budget not found."
    BUDGET_CREATE_FAILED = "Failed to create budget. Please try again."
    BUDGET_UPDATE_FAILED = "Failed to update budget. Please try again."
    BUDGET_DELETE_FAILED = "Failed to delete budget. Please try again."
    BUDGET_PERIOD_OVERLAP = "Budget period overlaps with an existing budget."

    # Sync errors
    SYNC_FAILED = "Synchronization failed. Please try again."
    SYNC_CONFLICT = "A conflict was detected during synchronization."
    SYNC_DATA_CORRUPTED = "Sync data appears to be corrupted. Please contact support."

    # File errors
    FILE_IMPORT_FAILED = "Failed to import file. Please check the file format."
    FILE_EXPORT_FAILED = "Failed to export file. Please try again."
    FILE_FORMAT_UNSUPPORTED = "This file format is not supported."
    FILE_TOO_LARGE = "File is too large. Maximum size is {max_size} MB."

    # General errors
    NOT_FOUND = "The requested resource was not found."
    FORBIDDEN = "You do not have permission to perform this action."
    GENERAL_UNKNOWN_ERROR = "An unexpected error occurred. Please try again."
    GENERAL_OPERATION_FAILED = "Operation failed. Please try again."
    GENERAL_PERMISSION_DENIED = "You do not have permission to perform this action."
    GENERAL_FEATURE_UNAVAILABLE = "This feature is not available in your current plan."


# Backward compatibility alias
class ErrorMessages(ErrorMessagesEN):
    """Alias for ErrorMessagesEN for backward compatibility."""
    pass

# =============================================================================
# ERROR MESSAGES - FRENCH
# =============================================================================

class ErrorMessagesFR:
    """Error messages in French."""

    # Authentication errors
    AUTH_INVALID_CREDENTIALS = "Email ou mot de passe invalide. Veuillez reessayer."
    AUTH_SESSION_EXPIRED = "Votre session a expire. Veuillez vous reconnecter."
    AUTH_ACCOUNT_LOCKED = "Votre compte a ete verrouille. Veuillez contacter le support."
    AUTH_EMAIL_NOT_VERIFIED = "Veuillez verifier votre adresse email pour continuer."
    AUTH_PASSWORD_TOO_WEAK = "Le mot de passe doit contenir au moins 8 caracteres avec majuscules, minuscules et chiffres."
    AUTH_REGISTRATION_FAILED = "L'inscription a echoue. Veuillez reessayer plus tard."
    AUTH_FAILED = "L'authentification a echoue. Veuillez vous reconnecter."
    TOKEN_EXPIRED = "Votre session a expire. Veuillez vous reconnecter."

    # Network errors
    NETWORK_ERROR = "Impossible de se connecter au serveur. Verifiez votre connexion internet."
    NETWORK_CONNECTION_FAILED = "Impossible de se connecter au serveur. Verifiez votre connexion internet."
    NETWORK_TIMEOUT = "La requete a expire. Veuillez reessayer."
    NETWORK_SERVER_ERROR = "Une erreur serveur s'est produite. Veuillez reessayer plus tard."
    NETWORK_SERVICE_UNAVAILABLE = "Le service est temporairement indisponible. Veuillez reessayer plus tard."
    SERVER_ERROR = "Une erreur inattendue s'est produite. Veuillez reessayer plus tard."

    # Data validation errors
    VALIDATION_ERROR = "Veuillez verifier vos informations et reessayer."
    VALIDATION_REQUIRED_FIELD = "Ce champ est obligatoire."
    VALIDATION_INVALID_EMAIL = "Veuillez entrer une adresse email valide."
    VALIDATION_INVALID_AMOUNT = "Veuillez entrer un montant valide."
    VALIDATION_INVALID_DATE = "Veuillez entrer une date valide."
    VALIDATION_NEGATIVE_AMOUNT = "Le montant ne peut pas etre negatif."
    VALIDATION_AMOUNT_TOO_LARGE = "Le montant depasse la valeur maximale autorisee."
    VALIDATION_FUTURE_DATE = "La date ne peut pas etre dans le futur."
    VALIDATION_DUPLICATE_ENTRY = "Cette entree existe deja."

    # Transaction errors
    TRANSACTION_NOT_FOUND = "Transaction introuvable."
    TRANSACTION_CREATE_FAILED = "Echec de la creation de la transaction. Veuillez reessayer."
    TRANSACTION_UPDATE_FAILED = "Echec de la mise a jour de la transaction. Veuillez reessayer."
    TRANSACTION_DELETE_FAILED = "Echec de la suppression de la transaction. Veuillez reessayer."
    TRANSACTION_INSUFFICIENT_FUNDS = "Fonds insuffisants pour cette transaction."

    # Account errors
    ACCOUNT_NOT_FOUND = "Compte introuvable."
    ACCOUNT_CREATE_FAILED = "Echec de la creation du compte. Veuillez reessayer."
    ACCOUNT_UPDATE_FAILED = "Echec de la mise a jour du compte. Veuillez reessayer."
    ACCOUNT_DELETE_FAILED = "Echec de la suppression du compte. Veuillez reessayer."
    ACCOUNT_HAS_TRANSACTIONS = "Impossible de supprimer un compte avec des transactions existantes."

    # Budget errors
    BUDGET_NOT_FOUND = "Budget introuvable."
    BUDGET_CREATE_FAILED = "Echec de la creation du budget. Veuillez reessayer."
    BUDGET_UPDATE_FAILED = "Echec de la mise a jour du budget. Veuillez reessayer."
    BUDGET_DELETE_FAILED = "Echec de la suppression du budget. Veuillez reessayer."
    BUDGET_PERIOD_OVERLAP = "La periode du budget chevauche un budget existant."

    # Sync errors
    SYNC_FAILED = "La synchronisation a echoue. Veuillez reessayer."
    SYNC_CONFLICT = "Un conflit a ete detecte lors de la synchronisation."
    SYNC_DATA_CORRUPTED = "Les donnees de synchronisation semblent corrompues. Veuillez contacter le support."

    # File errors
    FILE_IMPORT_FAILED = "Echec de l'importation du fichier. Verifiez le format du fichier."
    FILE_EXPORT_FAILED = "Echec de l'exportation du fichier. Veuillez reessayer."
    FILE_FORMAT_UNSUPPORTED = "Ce format de fichier n'est pas pris en charge."
    FILE_TOO_LARGE = "Le fichier est trop volumineux. La taille maximale est de {max_size} Mo."

    # General errors
    NOT_FOUND = "La ressource demandee est introuvable."
    FORBIDDEN = "Vous n'avez pas la permission d'effectuer cette action."
    GENERAL_UNKNOWN_ERROR = "Une erreur inattendue s'est produite. Veuillez reessayer."
    GENERAL_OPERATION_FAILED = "L'operation a echoue. Veuillez reessayer."
    GENERAL_PERMISSION_DENIED = "Vous n'avez pas la permission d'effectuer cette action."
    GENERAL_FEATURE_UNAVAILABLE = "Cette fonctionnalite n'est pas disponible dans votre forfait actuel."

# =============================================================================
# SUCCESS MESSAGES - ENGLISH
# =============================================================================

class SuccessMessagesEN:
    """Success messages in English."""

    LOGIN_SUCCESS = "Successfully logged in."
    LOGOUT_SUCCESS = "Successfully logged out."
    REGISTER_SUCCESS = "Account created successfully."
    TRANSACTION_CREATED = "Transaction created successfully."
    TRANSACTION_UPDATED = "Transaction updated successfully."
    TRANSACTION_DELETED = "Transaction deleted successfully."
    BUDGET_CREATED = "Budget created successfully."
    BUDGET_UPDATED = "Budget updated successfully."
    BUDGET_DELETED = "Budget deleted successfully."
    ACCOUNT_CREATED = "Account created successfully."
    ACCOUNT_UPDATED = "Account updated successfully."
    ACCOUNT_DELETED = "Account deleted successfully."
    ACCOUNT_LINKED = "Bank account linked successfully."
    SYNC_COMPLETE = "Transactions synced successfully."
    IMPORT_COMPLETE = "Data imported successfully."
    EXPORT_COMPLETE = "Data exported successfully."
    SETTINGS_SAVED = "Settings saved successfully."
    PASSWORD_CHANGED = "Password changed successfully."
    PROFILE_UPDATED = "Profile updated successfully."


# Backward compatibility alias
class SuccessMessages(SuccessMessagesEN):
    """Alias for SuccessMessagesEN for backward compatibility."""
    pass

# =============================================================================
# SUCCESS MESSAGES - FRENCH
# =============================================================================

class SuccessMessagesFR:
    """Success messages in French."""

    LOGIN_SUCCESS = "Connexion reussie."
    LOGOUT_SUCCESS = "Deconnexion reussie."
    REGISTER_SUCCESS = "Compte cree avec succes."
    TRANSACTION_CREATED = "Transaction creee avec succes."
    TRANSACTION_UPDATED = "Transaction mise a jour avec succes."
    TRANSACTION_DELETED = "Transaction supprimee avec succes."
    BUDGET_CREATED = "Budget cree avec succes."
    BUDGET_UPDATED = "Budget mis a jour avec succes."
    BUDGET_DELETED = "Budget supprime avec succes."
    ACCOUNT_CREATED = "Compte cree avec succes."
    ACCOUNT_UPDATED = "Compte mis a jour avec succes."
    ACCOUNT_DELETED = "Compte supprime avec succes."
    ACCOUNT_LINKED = "Compte bancaire lie avec succes."
    SYNC_COMPLETE = "Transactions synchronisees avec succes."
    IMPORT_COMPLETE = "Donnees importees avec succes."
    EXPORT_COMPLETE = "Donnees exportees avec succes."
    SETTINGS_SAVED = "Parametres enregistres avec succes."
    PASSWORD_CHANGED = "Mot de passe modifie avec succes."
    PROFILE_UPDATED = "Profil mis a jour avec succes."

# =============================================================================
# LANGUAGE SETTINGS
# =============================================================================

class Language(str, Enum):
    """Supported languages."""

    ENGLISH = "en"
    FRENCH = "fr"


DEFAULT_LANGUAGE = Language.ENGLISH

# Message classes by language
ERROR_MESSAGES_BY_LANG = {
    Language.ENGLISH: ErrorMessagesEN,
    Language.FRENCH: ErrorMessagesFR,
}

SUCCESS_MESSAGES_BY_LANG = {
    Language.ENGLISH: SuccessMessagesEN,
    Language.FRENCH: SuccessMessagesFR,
}

CATEGORY_LABELS_BY_LANG = {
    Language.ENGLISH: CATEGORY_LABELS_EN,
    Language.FRENCH: CATEGORY_LABELS_FR,
}

BUDGET_PERIOD_LABELS_BY_LANG = {
    Language.ENGLISH: BUDGET_PERIOD_LABELS_EN,
    Language.FRENCH: BUDGET_PERIOD_LABELS_FR,
}

CURRENCY_NAMES_BY_LANG = {
    Language.ENGLISH: CURRENCY_NAMES_EN,
    Language.FRENCH: CURRENCY_NAMES_FR,
}

# =============================================================================
# ACCOUNT TYPES
# =============================================================================

class AccountType(str, Enum):
    """Types of financial accounts."""

    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    RETIREMENT = "retirement"
    OTHER = "other"


# Account type labels (English)
ACCOUNT_TYPE_LABELS_EN: Dict[str, str] = {
    "checking": "Checking Account",
    "savings": "Savings Account",
    "credit_card": "Credit Card",
    "cash": "Cash",
    "investment": "Investment Account",
    "loan": "Loan",
    "mortgage": "Mortgage",
    "retirement": "Retirement Account",
    "other": "Other",
}

# Account type labels (French)
ACCOUNT_TYPE_LABELS_FR: Dict[str, str] = {
    "checking": "Compte Courant",
    "savings": "Compte Epargne",
    "credit_card": "Carte de Credit",
    "cash": "Especes",
    "investment": "Compte Investissement",
    "loan": "Pret",
    "mortgage": "Hypotheque",
    "retirement": "Compte Retraite",
    "other": "Autre",
}

# =============================================================================
# MISCELLANEOUS CONSTANTS
# =============================================================================

# Pagination
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# File size limits (in bytes)
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024    # 5 MB

# Retry settings
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.0
RETRY_BACKOFF_MULTIPLIER = 2.0

# Cache settings
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_MAX_ENTRIES = 1000

# Session settings
SESSION_TIMEOUT_MINUTES = 30
TOKEN_REFRESH_THRESHOLD_MINUTES = 5

# Export formats
EXPORT_FORMATS = ("csv", "xlsx", "pdf", "json")

# Import formats
IMPORT_FORMATS = ("csv", "xlsx", "ofx", "qif", "json")

# Supported file extensions
SUPPORTED_IMPORT_EXTENSIONS = (".csv", ".xlsx", ".xls", ".ofx", ".qif", ".json")
SUPPORTED_EXPORT_EXTENSIONS = (".csv", ".xlsx", ".pdf", ".json")
SUPPORTED_ATTACHMENT_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".doc", ".docx")

# Amount limits
MIN_TRANSACTION_AMOUNT = 0.01
MAX_TRANSACTION_AMOUNT = 999999999.99

# Text limits
MAX_DESCRIPTION_LENGTH = 500
MAX_NOTE_LENGTH = 2000
MAX_CATEGORY_NAME_LENGTH = 50
MAX_ACCOUNT_NAME_LENGTH = 100
