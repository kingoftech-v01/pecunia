"""Tests for src/constants.py — Application constants."""

import pytest

from constants import (
    # App info
    APP_NAME, APP_VERSION, APP_ORGANIZATION, APP_DOMAIN, APP_IDENTIFIER,
    # API
    DEFAULT_API_BASE_URL, API_TIMEOUT_SECONDS, KEYRING_SERVICE_NAME,
    # Enums
    APIEndpoints, Endpoints, DatabaseTables, SyncStatus, TransactionType,
    TransactionCategory, BudgetPeriod, DateTimeFormats, CurrencyCode,
    AccountType, Language,
    # Dicts
    CATEGORY_LABELS_EN, CATEGORY_LABELS_FR, BUDGET_PERIOD_DAYS,
    CURRENCY_SYMBOLS, CURRENCY_DECIMALS, CURRENCY_NAMES_EN,
    ERROR_MESSAGES_BY_LANG, SUCCESS_MESSAGES_BY_LANG,
    CATEGORY_LABELS_BY_LANG, BUDGET_PERIOD_LABELS_BY_LANG,
    CURRENCY_NAMES_BY_LANG,
    # Classes
    UIDimensions, UIColors, ErrorMessagesEN, ErrorMessages,
    SuccessMessagesEN, SuccessMessages, ErrorMessagesFR, SuccessMessagesFR,
    # Misc
    DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MAX_IMPORT_FILE_SIZE,
    EXPORT_FORMATS, IMPORT_FORMATS,
)


class TestAppConstants:
    """Tests for application-level constants."""

    def test_app_name_is_string(self):
        assert isinstance(APP_NAME, str)
        assert len(APP_NAME) > 0

    def test_app_version_format(self):
        parts = APP_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_app_organization_set(self):
        assert APP_ORGANIZATION is not None
        assert len(APP_ORGANIZATION) > 0

    def test_api_base_url_starts_with_https(self):
        assert DEFAULT_API_BASE_URL.startswith("https://")

    def test_api_timeout_reasonable(self):
        assert 1 <= API_TIMEOUT_SECONDS <= 300


class TestAPIEndpoints:
    """Tests for APIEndpoints class."""

    def test_auth_endpoints_start_with_auth(self):
        assert APIEndpoints.AUTH_LOGIN.startswith("/auth/")
        assert APIEndpoints.AUTH_LOGOUT.startswith("/auth/")
        assert APIEndpoints.AUTH_REFRESH.startswith("/auth/")

    def test_transaction_endpoints_start_with_transactions(self):
        assert APIEndpoints.TRANSACTIONS.startswith("/transactions")
        assert APIEndpoints.TRANSACTIONS_BY_ID.startswith("/transactions/")

    def test_budget_endpoints_start_with_budgets(self):
        assert APIEndpoints.BUDGETS.startswith("/budgets")

    def test_banking_endpoints_start_with_banking(self):
        assert APIEndpoints.BANKING_LINK_TOKEN.startswith("/banking/")

    def test_endpoints_alias(self):
        assert Endpoints is APIEndpoints


class TestSyncStatus:
    """Tests for SyncStatus enum."""

    def test_success_states_below_10(self):
        assert SyncStatus.SUCCESS == 0
        assert SyncStatus.UP_TO_DATE == 1
        assert SyncStatus.SYNCED == 2

    def test_pending_states_10_to_19(self):
        assert 10 <= SyncStatus.PENDING <= 19
        assert 10 <= SyncStatus.IN_PROGRESS <= 19

    def test_error_states_30_plus(self):
        assert SyncStatus.ERROR_NETWORK >= 30
        assert SyncStatus.ERROR_AUTH >= 30

    def test_is_int_enum(self):
        assert isinstance(SyncStatus.SUCCESS.value, int)


class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_income_value(self):
        assert TransactionType.INCOME.value == "income"

    def test_expense_value(self):
        assert TransactionType.EXPENSE.value == "expense"

    def test_all_types_are_strings(self):
        for t in TransactionType:
            assert isinstance(t.value, str)

    def test_has_common_types(self):
        names = [t.name for t in TransactionType]
        assert "INCOME" in names
        assert "EXPENSE" in names
        assert "TRANSFER" in names


class TestTransactionCategory:
    """Tests for TransactionCategory enum."""

    def test_salary_value(self):
        assert TransactionCategory.SALARY.value == "salary"

    def test_groceries_value(self):
        assert TransactionCategory.GROCERIES.value == "groceries"

    def test_category_labels_match_enum(self):
        for cat in TransactionCategory:
            assert cat.value in CATEGORY_LABELS_EN, f"{cat.value} missing in EN labels"

    def test_french_labels_match_enum(self):
        for cat in TransactionCategory:
            assert cat.value in CATEGORY_LABELS_FR, f"{cat.value} missing in FR labels"


class TestBudgetPeriod:
    """Tests for BudgetPeriod enum."""

    def test_monthly_value(self):
        assert BudgetPeriod.MONTHLY.value == "monthly"

    def test_all_periods_have_days(self):
        for period in BudgetPeriod:
            assert period.value in BUDGET_PERIOD_DAYS

    def test_daily_is_1_day(self):
        assert BUDGET_PERIOD_DAYS["daily"] == 1

    def test_yearly_is_365_days(self):
        assert BUDGET_PERIOD_DAYS["yearly"] == 365


class TestCurrencyCode:
    """Tests for CurrencyCode enum and related dicts."""

    def test_usd_value(self):
        assert CurrencyCode.USD.value == "USD"

    def test_all_currencies_have_symbols(self):
        for curr in CurrencyCode:
            assert curr.value in CURRENCY_SYMBOLS, f"{curr.value} missing symbol"

    def test_all_currencies_have_decimals(self):
        for curr in CurrencyCode:
            assert curr.value in CURRENCY_DECIMALS

    def test_jpy_has_zero_decimals(self):
        assert CURRENCY_DECIMALS["JPY"] == 0

    def test_usd_has_two_decimals(self):
        assert CURRENCY_DECIMALS["USD"] == 2


class TestDateTimeFormats:
    """Tests for DateTimeFormats class."""

    def test_iso_date_format(self):
        assert DateTimeFormats.ISO_DATE == "%Y-%m-%d"

    def test_database_datetime_format(self):
        assert "%Y-%m-%d" in DateTimeFormats.DATABASE_DATETIME


class TestUIConstants:
    """Tests for UIDimensions and UIColors."""

    def test_window_min_width_reasonable(self):
        assert UIDimensions.WINDOW_MIN_WIDTH >= 800

    def test_sidebar_width_positive(self):
        assert UIDimensions.SIDEBAR_WIDTH > 0
        assert UIDimensions.SIDEBAR_COLLAPSED_WIDTH > 0
        assert UIDimensions.SIDEBAR_COLLAPSED_WIDTH < UIDimensions.SIDEBAR_WIDTH

    def test_primary_color_is_hex(self):
        assert UIColors.PRIMARY.startswith("#")
        assert len(UIColors.PRIMARY) == 7

    def test_chart_colors_tuple(self):
        assert isinstance(UIColors.CHART_COLORS, tuple)
        assert len(UIColors.CHART_COLORS) > 0


class TestErrorMessages:
    """Tests for error message classes."""

    def test_error_messages_alias(self):
        assert issubclass(ErrorMessages, ErrorMessagesEN)

    def test_auth_messages_exist(self):
        assert hasattr(ErrorMessagesEN, "AUTH_INVALID_CREDENTIALS")
        assert hasattr(ErrorMessagesEN, "AUTH_SESSION_EXPIRED")

    def test_network_messages_exist(self):
        assert hasattr(ErrorMessagesEN, "NETWORK_ERROR")
        assert hasattr(ErrorMessagesEN, "NETWORK_TIMEOUT")

    def test_french_messages_exist(self):
        assert hasattr(ErrorMessagesFR, "AUTH_INVALID_CREDENTIALS")
        assert hasattr(ErrorMessagesFR, "NETWORK_ERROR")


class TestSuccessMessages:
    """Tests for success message classes."""

    def test_success_messages_alias(self):
        assert issubclass(SuccessMessages, SuccessMessagesEN)

    def test_login_success_message(self):
        assert "logged in" in SuccessMessagesEN.LOGIN_SUCCESS.lower() or \
               "success" in SuccessMessagesEN.LOGIN_SUCCESS.lower()

    def test_french_success_messages(self):
        assert hasattr(SuccessMessagesFR, "LOGIN_SUCCESS")


class TestLanguageConfig:
    """Tests for language configuration."""

    def test_language_enum(self):
        assert Language.ENGLISH.value == "en"
        assert Language.FRENCH.value == "fr"

    def test_error_messages_by_lang(self):
        assert Language.ENGLISH in ERROR_MESSAGES_BY_LANG
        assert Language.FRENCH in ERROR_MESSAGES_BY_LANG

    def test_success_messages_by_lang(self):
        assert Language.ENGLISH in SUCCESS_MESSAGES_BY_LANG

    def test_category_labels_by_lang(self):
        assert Language.ENGLISH in CATEGORY_LABELS_BY_LANG
        assert Language.FRENCH in CATEGORY_LABELS_BY_LANG


class TestMiscConstants:
    """Tests for miscellaneous constants."""

    def test_page_size_defaults(self):
        assert DEFAULT_PAGE_SIZE > 0
        assert MAX_PAGE_SIZE > DEFAULT_PAGE_SIZE

    def test_file_size_limits(self):
        assert MAX_IMPORT_FILE_SIZE > 0

    def test_export_formats(self):
        assert "csv" in EXPORT_FORMATS
        assert "pdf" in EXPORT_FORMATS

    def test_import_formats(self):
        assert "csv" in IMPORT_FORMATS
        assert "ofx" in IMPORT_FORMATS

    def test_database_tables_exist(self):
        assert DatabaseTables.USERS == "users"
        assert DatabaseTables.TRANSACTIONS == "transactions"
        assert DatabaseTables.BUDGETS == "budgets"

    def test_account_type_enum(self):
        assert AccountType.CHECKING.value == "checking"
        assert AccountType.SAVINGS.value == "savings"
