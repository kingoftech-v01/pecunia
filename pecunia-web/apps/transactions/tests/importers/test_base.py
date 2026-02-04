"""Tests for base importer module."""
import io
import pytest
from datetime import date, datetime
from decimal import Decimal
from typing import BinaryIO, List, TextIO, Union

from apps.transactions.importers.base import (
    BaseImporter,
    ImportError as ImporterError,
    ImportResult,
    ParsedTransaction,
    TransactionType,
    ValidationError,
)


class ConcreteImporter(BaseImporter):
    """Concrete subclass of BaseImporter for testing."""

    def parse(self, file_obj):
        return ImportResult(success=True)

    def get_supported_formats(self):
        return ["test"]


class TestImportError:
    """Tests for ImportError exception class."""

    def test_basic_message(self):
        err = ImporterError("Something failed")
        assert err.message == "Something failed"
        assert str(err) == "Something failed"
        assert err.line_number is None

    def test_with_line_number(self):
        err = ImporterError("Bad data", line_number=42)
        assert str(err) == "Line 42: Bad data"
        assert err.line_number == 42

    def test_with_details(self):
        err = ImporterError("Error", details={"field": "amount"})
        assert err.details == {"field": "amount"}

    def test_empty_details_default(self):
        err = ImporterError("Error")
        assert err.details == {}

    def test_format_message_no_line(self):
        err = ImporterError("Test")
        assert err.format_message() == "Test"

    def test_format_message_with_line(self):
        err = ImporterError("Test", line_number=5)
        assert err.format_message() == "Line 5: Test"


class TestValidationError:
    """Tests for ValidationError exception class."""

    def test_basic(self):
        err = ValidationError("amount", "is required")
        assert str(err) == "amount: is required"
        assert err.field == "amount"
        assert err.message == "is required"

    def test_with_value(self):
        err = ValidationError("amount", "invalid", "abc")
        assert err.value == "abc"

    def test_value_default_none(self):
        err = ValidationError("date", "bad format")
        assert err.value is None


class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_income_value(self):
        assert TransactionType.INCOME.value == "income"

    def test_expense_value(self):
        assert TransactionType.EXPENSE.value == "expense"

    def test_transfer_value(self):
        assert TransactionType.TRANSFER.value == "transfer"


class TestParsedTransaction:
    """Tests for ParsedTransaction dataclass."""

    def test_to_dict(self):
        tx = ParsedTransaction(
            amount=Decimal("100.00"),
            transaction_date=date(2026, 1, 15),
            type=TransactionType.EXPENSE,
            description="Test",
            merchant="Store",
            reference="REF123",
            tags=["food"],
        )
        d = tx.to_dict()
        assert d["amount"] == Decimal("100.00")
        assert d["transaction_date"] == date(2026, 1, 15)
        assert d["type"] == "expense"
        assert d["description"] == "Test"
        assert d["merchant"] == "Store"
        assert d["reference"] == "REF123"
        assert d["tags"] == ["food"]

    def test_defaults(self):
        tx = ParsedTransaction(
            amount=Decimal("10.00"),
            transaction_date=date(2026, 1, 1),
            type=TransactionType.INCOME,
        )
        assert tx.description == ""
        assert tx.merchant == ""
        assert tx.reference == ""
        assert tx.category_name is None
        assert tx.tags == []
        assert tx.raw_data == {}

    def test_with_raw_data(self):
        tx = ParsedTransaction(
            amount=Decimal("10.00"),
            transaction_date=date(2026, 1, 1),
            type=TransactionType.INCOME,
            raw_data={"original": "data"},
        )
        assert tx.raw_data == {"original": "data"}


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_initial_state(self):
        result = ImportResult(success=True)
        assert result.success is True
        assert result.total_rows == 0
        assert result.imported_count == 0
        assert result.skipped_count == 0
        assert result.error_count == 0
        assert result.transactions == []
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        result = ImportResult(success=True)
        result.add_error("Bad row", line_number=3, details={"col": "date"})
        assert result.error_count == 1
        assert result.errors[0]["message"] == "Bad row"
        assert result.errors[0]["line_number"] == 3
        assert result.errors[0]["details"]["col"] == "date"

    def test_add_error_no_details(self):
        result = ImportResult(success=True)
        result.add_error("Error")
        assert result.errors[0]["details"] == {}

    def test_add_warning(self):
        result = ImportResult(success=True)
        result.add_warning("Skipped empty row")
        assert result.warnings == ["Skipped empty row"]

    def test_add_transaction(self):
        result = ImportResult(success=True)
        tx = ParsedTransaction(
            amount=Decimal("10.00"),
            transaction_date=date(2026, 1, 1),
            type=TransactionType.INCOME,
        )
        result.add_transaction(tx)
        assert result.imported_count == 1
        assert len(result.transactions) == 1
        assert result.transactions[0] is tx

    def test_to_dict(self):
        result = ImportResult(success=True, total_rows=5)
        result.add_error("Error")
        result.add_warning("Warning")
        d = result.to_dict()
        assert d["success"] is True
        assert d["total_rows"] == 5
        assert d["imported_count"] == 0
        assert d["skipped_count"] == 0
        assert d["error_count"] == 1
        assert len(d["errors"]) == 1
        assert len(d["warnings"]) == 1

    def test_to_dict_does_not_include_transactions(self):
        result = ImportResult(success=True)
        d = result.to_dict()
        assert "transactions" not in d


class TestBaseImporterParseAmount:
    """Tests for BaseImporter._parse_amount."""

    @pytest.fixture
    def importer(self):
        return ConcreteImporter()

    def test_none_raises(self, importer):
        with pytest.raises(ValidationError):
            importer._parse_amount(None)

    def test_empty_string_raises(self, importer):
        with pytest.raises(ValidationError):
            importer._parse_amount("")

    def test_decimal_passthrough(self, importer):
        assert importer._parse_amount(Decimal("42.50")) == Decimal("42.50")

    def test_integer(self, importer):
        assert importer._parse_amount(42) == Decimal("42")

    def test_float(self, importer):
        assert importer._parse_amount(42.5) == Decimal("42.5")

    def test_string_simple(self, importer):
        assert importer._parse_amount("42.50") == Decimal("42.50")

    def test_string_negative(self, importer):
        assert importer._parse_amount("-42.50") == Decimal("-42.50")

    def test_parentheses_negative(self, importer):
        assert importer._parse_amount("(42.50)") == Decimal("-42.50")

    def test_currency_dollar(self, importer):
        assert importer._parse_amount("$42.50") == Decimal("42.50")

    def test_currency_euro(self, importer):
        assert importer._parse_amount("42.50") == Decimal("42.50")

    def test_currency_code(self, importer):
        assert importer._parse_amount("USD42.50") == Decimal("42.50")

    def test_us_format_thousands(self, importer):
        assert importer._parse_amount("1,234.56") == Decimal("1234.56")

    def test_european_format(self, importer):
        assert importer._parse_amount("1.234,56") == Decimal("1234.56")

    def test_comma_decimal(self, importer):
        assert importer._parse_amount("123,45") == Decimal("123.45")

    def test_comma_thousands_only(self, importer):
        assert importer._parse_amount("1,234") == Decimal("1234")

    def test_invalid_format(self, importer):
        with pytest.raises(ValidationError):
            importer._parse_amount("not-a-number")

    def test_whitespace_stripped(self, importer):
        assert importer._parse_amount("  42.50  ") == Decimal("42.50")


class TestBaseImporterParseDate:
    """Tests for BaseImporter._parse_date."""

    @pytest.fixture
    def importer(self):
        return ConcreteImporter()

    def test_none_raises(self, importer):
        with pytest.raises(ValidationError):
            importer._parse_date(None)

    def test_empty_string_raises(self, importer):
        with pytest.raises(ValidationError):
            importer._parse_date("")

    def test_date_passthrough(self, importer):
        d = date(2026, 1, 15)
        assert importer._parse_date(d) == d

    def test_datetime_converts(self, importer):
        dt = datetime(2026, 1, 15, 12, 30)
        # datetime is a subclass of date, so isinstance(dt, date) is True
        # and the function returns the datetime as-is
        result = importer._parse_date(dt)
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_iso_format(self, importer):
        assert importer._parse_date("2026-01-15") == date(2026, 1, 15)

    def test_european_slash(self, importer):
        assert importer._parse_date("15/01/2026") == date(2026, 1, 15)

    def test_us_slash(self, importer):
        assert importer._parse_date("01/15/2026") == date(2026, 1, 15)

    def test_dot_format(self, importer):
        assert importer._parse_date("15.01.2026") == date(2026, 1, 15)

    def test_unrecognized_raises(self, importer):
        with pytest.raises(ValidationError):
            importer._parse_date("not-a-date")

    def test_iso_with_time(self, importer):
        assert importer._parse_date("2026-01-15T12:30:00") == date(2026, 1, 15)

    def test_iso_with_timezone(self, importer):
        assert importer._parse_date("2026-01-15T12:30:00Z") == date(2026, 1, 15)


class TestBaseImporterDetermineType:
    """Tests for BaseImporter._determine_type."""

    @pytest.fixture
    def importer(self):
        return ConcreteImporter()

    def test_positive_amount_no_hint(self, importer):
        assert importer._determine_type(Decimal("100")) == TransactionType.INCOME

    def test_negative_amount_no_hint(self, importer):
        assert importer._determine_type(Decimal("-100")) == TransactionType.EXPENSE

    def test_zero_amount_no_hint(self, importer):
        assert importer._determine_type(Decimal("0")) == TransactionType.INCOME

    def test_hint_income(self, importer):
        assert importer._determine_type(Decimal("100"), "income") == TransactionType.INCOME

    def test_hint_expense(self, importer):
        assert importer._determine_type(Decimal("100"), "expense") == TransactionType.EXPENSE

    def test_hint_credit(self, importer):
        assert importer._determine_type(Decimal("100"), "credit") == TransactionType.INCOME

    def test_hint_debit(self, importer):
        assert importer._determine_type(Decimal("100"), "debit") == TransactionType.EXPENSE

    def test_hint_transfer(self, importer):
        assert importer._determine_type(Decimal("100"), "transfer") == TransactionType.TRANSFER

    def test_hint_xfer(self, importer):
        assert importer._determine_type(Decimal("100"), "xfer") == TransactionType.TRANSFER

    def test_hint_deposit(self, importer):
        assert importer._determine_type(Decimal("100"), "deposit") == TransactionType.INCOME

    def test_hint_withdrawal(self, importer):
        assert importer._determine_type(Decimal("100"), "withdrawal") == TransactionType.EXPENSE

    def test_hint_payment(self, importer):
        assert importer._determine_type(Decimal("100"), "payment") == TransactionType.EXPENSE

    def test_hint_case_insensitive(self, importer):
        assert importer._determine_type(Decimal("100"), "INCOME") == TransactionType.INCOME

    def test_hint_unknown_falls_to_amount(self, importer):
        assert importer._determine_type(Decimal("-50"), "unknown") == TransactionType.EXPENSE


class TestBaseImporterCleanString:
    """Tests for BaseImporter._clean_string."""

    @pytest.fixture
    def importer(self):
        return ConcreteImporter()

    def test_none(self, importer):
        assert importer._clean_string(None) == ""

    def test_strips_whitespace(self, importer):
        assert importer._clean_string("  hello  ") == "hello"

    def test_normalizes_spaces(self, importer):
        assert importer._clean_string("hello   world") == "hello world"

    def test_number(self, importer):
        assert importer._clean_string(42) == "42"


class TestBaseImporterParseTags:
    """Tests for BaseImporter._parse_tags."""

    @pytest.fixture
    def importer(self):
        return ConcreteImporter()

    def test_empty_value(self, importer):
        assert importer._parse_tags(None) == []
        assert importer._parse_tags("") == []
        assert importer._parse_tags([]) == []

    def test_list_of_strings(self, importer):
        assert importer._parse_tags(["food", "weekly"]) == ["food", "weekly"]

    def test_list_filters_empty(self, importer):
        assert importer._parse_tags(["food", "", "weekly"]) == ["food", "weekly"]

    def test_comma_separated(self, importer):
        assert importer._parse_tags("food,weekly") == ["food", "weekly"]

    def test_semicolon_separated(self, importer):
        assert importer._parse_tags("food;weekly") == ["food", "weekly"]

    def test_pipe_separated(self, importer):
        assert importer._parse_tags("food|weekly") == ["food", "weekly"]

    def test_single_tag(self, importer):
        assert importer._parse_tags("food") == ["food"]

    def test_other_type_returns_empty(self, importer):
        assert importer._parse_tags(42) == []


class TestBaseImporterDetectEncoding:
    """Tests for BaseImporter.detect_encoding."""

    @pytest.fixture
    def importer(self):
        return ConcreteImporter()

    def test_utf8_bom(self, importer):
        content = b"\xef\xbb\xbfhello"
        result = importer.detect_encoding(io.BytesIO(content))
        assert result == "utf-8-sig"

    def test_utf16_bom_le(self, importer):
        content = b"\xff\xfeh\x00e\x00l\x00"
        result = importer.detect_encoding(io.BytesIO(content))
        assert result == "utf-16"

    def test_utf16_bom_be(self, importer):
        content = b"\xfe\xff\x00h\x00e\x00l"
        result = importer.detect_encoding(io.BytesIO(content))
        assert result == "utf-16"

    def test_plain_utf8(self, importer):
        content = "Hello, World!".encode("utf-8")
        result = importer.detect_encoding(io.BytesIO(content))
        assert result == "utf-8"

    def test_preserves_position(self, importer):
        content = "Hello".encode("utf-8")
        f = io.BytesIO(content)
        f.seek(3)
        importer.detect_encoding(f)
        assert f.tell() == 3


class TestBaseImporterValidateTransaction:
    """Tests for BaseImporter.validate_transaction."""

    @pytest.fixture
    def importer(self):
        return ConcreteImporter()

    def test_valid_data(self, importer):
        data = {
            "amount": "100.00",
            "date": "2026-01-15",
            "description": "Test purchase",
            "merchant": "Store",
        }
        tx = importer.validate_transaction(data)
        assert tx.amount == Decimal("100.00")
        assert tx.transaction_date == date(2026, 1, 15)
        assert tx.description == "Test purchase"

    def test_negative_amount_becomes_expense(self, importer):
        data = {"amount": "-50.00", "date": "2026-01-15"}
        tx = importer.validate_transaction(data)
        assert tx.amount == Decimal("50.00")  # abs
        assert tx.type == TransactionType.EXPENSE

    def test_positive_amount_becomes_income(self, importer):
        data = {"amount": "50.00", "date": "2026-01-15"}
        tx = importer.validate_transaction(data)
        assert tx.type == TransactionType.INCOME

    def test_with_type_hint(self, importer):
        data = {"amount": "50.00", "date": "2026-01-15", "type": "expense"}
        tx = importer.validate_transaction(data)
        assert tx.type == TransactionType.EXPENSE

    def test_with_tags(self, importer):
        data = {"amount": "50.00", "date": "2026-01-15", "tags": "food,weekly"}
        tx = importer.validate_transaction(data)
        assert tx.tags == ["food", "weekly"]

    def test_with_category(self, importer):
        data = {
            "amount": "50.00",
            "date": "2026-01-15",
            "category": "Groceries",
        }
        tx = importer.validate_transaction(data)
        assert tx.category_name == "Groceries"

    def test_missing_amount_raises(self, importer):
        data = {"date": "2026-01-15"}
        with pytest.raises(ValidationError):
            importer.validate_transaction(data)

    def test_missing_date_raises(self, importer):
        data = {"amount": "50.00"}
        with pytest.raises(ValidationError):
            importer.validate_transaction(data)


class TestBaseImporterProgressCallback:
    """Tests for progress callback mechanism."""

    def test_set_callback(self):
        importer = ConcreteImporter()
        called_with = []
        importer.set_progress_callback(lambda c, t: called_with.append((c, t)))
        importer._report_progress(5, 10)
        assert called_with == [(5, 10)]
        assert importer._current_line == 5
        assert importer._total_lines == 10

    def test_no_callback(self):
        importer = ConcreteImporter()
        # Should not raise
        importer._report_progress(5, 10)
        assert importer._current_line == 5


@pytest.mark.django_db
class TestBaseImporterImportToDatabase:
    """Tests for BaseImporter.import_to_database."""

    def test_import_creates_transactions(self, user, category):
        importer = ConcreteImporter(user=user)
        result = ImportResult(success=True)
        result.add_transaction(ParsedTransaction(
            amount=Decimal("50.00"),
            transaction_date=date(2026, 1, 15),
            type=TransactionType.EXPENSE,
            description="Test",
        ))
        stats = importer.import_to_database(result)
        assert stats["created"] == 1
        assert stats["duplicates"] == 0

    def test_import_detects_duplicates(self, user):
        importer = ConcreteImporter(user=user)
        result = ImportResult(success=True)
        tx = ParsedTransaction(
            amount=Decimal("50.00"),
            transaction_date=date(2026, 1, 15),
            type=TransactionType.EXPENSE,
            description="Duplicate test",
        )
        result.add_transaction(tx)
        importer.import_to_database(result)

        # Import again - should detect duplicate
        result2 = ImportResult(success=True)
        result2.add_transaction(tx)
        stats = importer.import_to_database(result2)
        assert stats["duplicates"] == 1
        assert stats["created"] == 0

    def test_import_without_user_raises(self):
        importer = ConcreteImporter()
        result = ImportResult(success=True)
        with pytest.raises(ImporterError):
            importer.import_to_database(result)

    def test_import_with_category(self, user, category):
        importer = ConcreteImporter(user=user)
        result = ImportResult(success=True)
        result.add_transaction(ParsedTransaction(
            amount=Decimal("50.00"),
            transaction_date=date(2026, 1, 15),
            type=TransactionType.EXPENSE,
            description="With category",
            category_name="Groceries",
        ))
        stats = importer.import_to_database(result)
        assert stats["created"] == 1

    def test_import_with_unknown_category(self, user):
        importer = ConcreteImporter(user=user)
        result = ImportResult(success=True)
        result.add_transaction(ParsedTransaction(
            amount=Decimal("50.00"),
            transaction_date=date(2026, 1, 15),
            type=TransactionType.EXPENSE,
            description="Unknown category",
            category_name="NonExistent",
        ))
        stats = importer.import_to_database(result)
        assert stats["created"] == 1

    def test_import_reports_progress(self, user):
        importer = ConcreteImporter(user=user)
        called_with = []
        importer.set_progress_callback(lambda c, t: called_with.append((c, t)))
        result = ImportResult(success=True)
        result.add_transaction(ParsedTransaction(
            amount=Decimal("50.00"),
            transaction_date=date(2026, 1, 15),
            type=TransactionType.EXPENSE,
        ))
        importer.import_to_database(result)
        assert len(called_with) == 1
