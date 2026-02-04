"""Tests for src/services/import_service.py — ImportService and related classes."""

import csv
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from services.import_service import (
    ImportService, ImportRecord, ImportResult,
    DataImportError, ValidationError,
)


class TestImportRecord:
    """Tests for ImportRecord dataclass."""

    def test_creation(self):
        record = ImportRecord(
            date=date(2024, 1, 15),
            amount=Decimal("125.50"),
            description="Grocery Store",
        )
        assert record.date == date(2024, 1, 15)
        assert record.amount == Decimal("125.50")
        assert record.description == "Grocery Store"

    def test_defaults(self):
        record = ImportRecord(
            date=date(2024, 1, 1),
            amount=Decimal("10"),
            description="Test",
        )
        assert record.transaction_type == "expense"
        assert record.category is None
        assert record.merchant is None
        assert record.account is None
        assert record.reference is None
        assert record.notes is None
        assert record.raw_data == {}

    def test_unique_hash_consistent(self):
        r1 = ImportRecord(date=date(2024, 1, 1), amount=Decimal("10"), description="Test")
        r2 = ImportRecord(date=date(2024, 1, 1), amount=Decimal("10"), description="Test")
        assert r1.unique_hash == r2.unique_hash

    def test_unique_hash_differs(self):
        r1 = ImportRecord(date=date(2024, 1, 1), amount=Decimal("10"), description="Test1")
        r2 = ImportRecord(date=date(2024, 1, 1), amount=Decimal("10"), description="Test2")
        assert r1.unique_hash != r2.unique_hash

    def test_unique_hash_cached(self):
        record = ImportRecord(date=date(2024, 1, 1), amount=Decimal("10"), description="Test")
        h1 = record.unique_hash
        h2 = record.unique_hash
        assert h1 is h2  # Same object (cached)

    def test_to_dict(self):
        record = ImportRecord(
            date=date(2024, 1, 15),
            amount=Decimal("125.50"),
            description="Grocery Store",
            transaction_type="expense",
            category="Food",
            reference="REF001",
        )
        d = record.to_dict()
        assert d["date"] == "2024-01-15"
        assert d["amount"] == 125.50
        assert d["description"] == "Grocery Store"
        assert d["type"] == "expense"
        assert d["category"] == "Food"
        assert d["reference"] == "REF001"
        assert "unique_hash" in d

    def test_repr(self):
        record = ImportRecord(
            date=date(2024, 1, 15),
            amount=Decimal("100"),
            description="A very long description that exceeds thirty characters limit",
        )
        r = repr(record)
        assert "ImportRecord" in r
        assert "2024-01-15" in r
        assert "100" in r


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_default_values(self):
        result = ImportResult()
        assert result.records == []
        assert result.errors == []
        assert result.warnings == []
        assert result.duplicates == []
        assert result.source_file is None
        assert result.source_format is None
        assert isinstance(result.import_date, datetime)

    def test_total_count(self):
        result = ImportResult()
        result.records = [MagicMock() for _ in range(3)]
        result.errors = [{"error": "bad"} for _ in range(2)]
        result.duplicates = [MagicMock()]
        assert result.total_count == 6

    def test_success_count(self):
        result = ImportResult()
        result.records = [MagicMock() for _ in range(5)]
        assert result.success_count == 5

    def test_error_count(self):
        result = ImportResult()
        result.errors = [{"error": "bad"}]
        assert result.error_count == 1

    def test_duplicate_count(self):
        result = ImportResult()
        result.duplicates = [MagicMock(), MagicMock()]
        assert result.duplicate_count == 2

    def test_to_dict(self):
        result = ImportResult()
        result.source_file = "test.csv"
        result.source_format = "csv"
        d = result.to_dict()
        assert d["source_file"] == "test.csv"
        assert d["source_format"] == "csv"
        assert d["total_count"] == 0
        assert d["success_count"] == 0


class TestImportServiceInit:
    """Tests for ImportService initialization."""

    def test_init(self):
        svc = ImportService()
        assert svc._progress_callback is None
        assert svc._existing_hashes == set()

    def test_set_progress_callback(self):
        svc = ImportService()
        cb = MagicMock()
        svc.set_progress_callback(cb)
        svc._report_progress(1, 10, "test")
        cb.assert_called_once_with(1, 10, "test")

    def test_set_existing_hashes(self):
        svc = ImportService()
        svc.set_existing_hashes({"abc", "def"})
        assert "abc" in svc._existing_hashes

    def test_get_supported_formats(self):
        svc = ImportService()
        formats = svc.get_supported_formats()
        assert len(formats) == 4
        ids = [f["id"] for f in formats]
        assert "csv" in ids
        assert "ofx" in ids
        assert "qfx" in ids
        assert "qif" in ids


class TestImportServiceFormatDetection:
    """Tests for format detection."""

    def test_detect_csv_by_extension(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("date,amount\n2024-01-01,100")
        svc = ImportService()
        assert svc.detect_format(f) == "csv"

    def test_detect_ofx_by_extension(self, tmp_path):
        f = tmp_path / "data.ofx"
        f.write_text("<OFX></OFX>")
        svc = ImportService()
        assert svc.detect_format(f) == "ofx"

    def test_detect_qfx_by_extension(self, tmp_path):
        f = tmp_path / "data.qfx"
        f.write_text("<OFX></OFX>")
        svc = ImportService()
        assert svc.detect_format(f) == "qfx"

    def test_detect_qif_by_extension(self, tmp_path):
        f = tmp_path / "data.qif"
        f.write_text("!Type:Bank\nD01/15/2024\nT-100\n^")
        svc = ImportService()
        assert svc.detect_format(f) == "qif"

    def test_detect_ofx_by_content(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("OFXHEADER:100\n<OFX>test</OFX>")
        svc = ImportService()
        assert svc.detect_format(f) == "ofx"

    def test_detect_qif_by_content(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("!Type:Bank\nD01/15/2024\nT-100")
        svc = ImportService()
        assert svc.detect_format(f) == "qif"

    def test_detect_csv_by_content(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("date,amount,description\n2024-01-01,100,test")
        svc = ImportService()
        assert svc.detect_format(f) == "csv"

    def test_detect_format_file_not_found(self, tmp_path):
        svc = ImportService()
        with pytest.raises(DataImportError, match="not found"):
            svc.detect_format(tmp_path / "nonexistent.xyz")

    def test_detect_format_unknown(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_bytes(b"\x00\x01\x02\x03")  # Binary content
        svc = ImportService()
        with pytest.raises(DataImportError, match="Unable to detect"):
            svc.detect_format(f)


class TestImportServiceCSV:
    """Tests for CSV import functionality."""

    def _write_csv(self, path, rows, header=None):
        with open(path, 'w', newline='') as f:
            if header:
                f.write(','.join(header) + '\n')
            for row in rows:
                f.write(','.join(str(v) for v in row) + '\n')

    def test_import_csv_basic(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [["2024-01-15", "100.00", "Grocery Store"]],
            header=["date", "amount", "description"],
        )
        svc = ImportService()
        result = svc.import_csv(f)
        assert result.success_count == 1
        assert result.records[0].description == "Grocery Store"
        assert result.records[0].amount == Decimal("100")

    def test_import_csv_multiple_rows(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [
                ["2024-01-15", "100.00", "Store A"],
                ["2024-01-16", "200.00", "Store B"],
                ["2024-01-17", "-50.00", "Refund"],
            ],
            header=["date", "amount", "description"],
        )
        svc = ImportService()
        result = svc.import_csv(f)
        assert result.success_count == 3

    def test_import_csv_duplicate_detection(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [
                ["2024-01-15", "100.00", "Store A"],
                ["2024-01-15", "100.00", "Store A"],  # Duplicate
            ],
            header=["date", "amount", "description"],
        )
        svc = ImportService()
        result = svc.import_csv(f)
        assert result.success_count == 1
        assert result.duplicate_count == 1

    def test_import_csv_with_existing_hashes(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [["2024-01-15", "100.00", "Store A"]],
            header=["date", "amount", "description"],
        )
        # First import to get the hash
        svc = ImportService()
        result1 = svc.import_csv(f)
        existing = {r.unique_hash for r in result1.records}

        # Second import with existing hashes
        svc2 = ImportService()
        svc2.set_existing_hashes(existing)
        result2 = svc2.import_csv(f)
        assert result2.duplicate_count == 1
        assert result2.success_count == 0

    def test_import_csv_invalid_date(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [["not-a-date", "100.00", "Store"]],
            header=["date", "amount", "description"],
        )
        svc = ImportService()
        result = svc.import_csv(f)
        assert result.error_count == 1
        assert result.success_count == 0

    def test_import_csv_auto_detect_delimiter(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("date;amount;description\n2024-01-15;100.00;Store\n")
        svc = ImportService()
        result = svc.import_csv(f)
        assert result.success_count == 1

    def test_import_csv_custom_column_mapping(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [["2024-01-15", "100.00", "Store"]],
            header=["fecha", "monto", "detalle"],
        )
        svc = ImportService()
        result = svc.import_csv(
            f,
            column_mapping={"date": "fecha", "amount": "monto", "description": "detalle"},
        )
        assert result.success_count == 1

    def test_import_csv_progress(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [["2024-01-15", "100.00", "Store"]],
            header=["date", "amount", "description"],
        )
        svc = ImportService()
        calls = []
        svc.set_progress_callback(lambda c, t, m: calls.append((c, t, m)))
        svc.import_csv(f)
        assert len(calls) > 0

    def test_import_csv_empty_file(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("")
        svc = ImportService()
        with pytest.raises(DataImportError, match="empty"):
            svc.import_csv(f)

    def test_import_csv_income_detection(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [["2024-01-15", "500.00", "Salary"]],
            header=["date", "amount", "description"],
        )
        svc = ImportService()
        result = svc.import_csv(f)
        assert result.records[0].transaction_type == "income"

    def test_import_csv_expense_detection(self, tmp_path):
        f = tmp_path / "test.csv"
        self._write_csv(
            f,
            [["2024-01-15", "-100.00", "Store"]],
            header=["date", "amount", "description"],
        )
        svc = ImportService()
        result = svc.import_csv(f)
        assert result.records[0].transaction_type == "expense"
        assert result.records[0].amount == Decimal("100")  # abs value


class TestImportServiceOFX:
    """Tests for OFX/QFX import functionality."""

    OFX_CONTENT = """OFXHEADER:100
DATA:OFXSGML
<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240115
<TRNAMT>-125.50
<FITID>TXN001
<NAME>Grocery Store
<MEMO>Weekly shopping
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20240116
<TRNAMT>5000.00
<FITID>TXN002
<NAME>Salary
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""

    def test_import_ofx_basic(self, tmp_path):
        f = tmp_path / "test.ofx"
        f.write_text(self.OFX_CONTENT)
        svc = ImportService()
        result = svc.import_ofx(f)
        assert result.success_count == 2
        assert result.source_format == "ofx"

    def test_import_ofx_debit_is_expense(self, tmp_path):
        f = tmp_path / "test.ofx"
        f.write_text(self.OFX_CONTENT)
        svc = ImportService()
        result = svc.import_ofx(f)
        debit = [r for r in result.records if r.description == "Grocery Store"][0]
        assert debit.transaction_type == "expense"
        assert debit.amount == Decimal("125.50")

    def test_import_ofx_credit_is_income(self, tmp_path):
        f = tmp_path / "test.ofx"
        f.write_text(self.OFX_CONTENT)
        svc = ImportService()
        result = svc.import_ofx(f)
        credit = [r for r in result.records if r.description == "Salary"][0]
        assert credit.transaction_type == "income"
        assert credit.amount == Decimal("5000")

    def test_import_ofx_dates_parsed(self, tmp_path):
        f = tmp_path / "test.ofx"
        f.write_text(self.OFX_CONTENT)
        svc = ImportService()
        result = svc.import_ofx(f)
        assert result.records[0].date == date(2024, 1, 15)

    def test_import_ofx_duplicate_detection(self, tmp_path):
        f = tmp_path / "test.ofx"
        f.write_text(self.OFX_CONTENT)
        svc = ImportService()
        r1 = svc.import_ofx(f)
        existing = {r.unique_hash for r in r1.records}

        svc2 = ImportService()
        svc2.set_existing_hashes(existing)
        r2 = svc2.import_ofx(f)
        assert r2.duplicate_count == 2
        assert r2.success_count == 0

    def test_import_ofx_empty_file(self, tmp_path):
        f = tmp_path / "test.ofx"
        f.write_text("<OFX></OFX>")
        svc = ImportService()
        result = svc.import_ofx(f)
        assert result.success_count == 0


class TestImportServiceQIF:
    """Tests for QIF import functionality."""

    QIF_CONTENT = """!Type:Bank
D01/15/2024
T-125.50
PGrocery Store
MWeekly shopping
N1001
LFood
^
D01/16/2024
T5000.00
PSalary
N1002
^"""

    def test_import_qif_basic(self, tmp_path):
        f = tmp_path / "test.qif"
        f.write_text(self.QIF_CONTENT)
        svc = ImportService()
        result = svc.import_qif(f)
        assert result.success_count == 2
        assert result.source_format == "qif"

    def test_import_qif_expense(self, tmp_path):
        f = tmp_path / "test.qif"
        f.write_text(self.QIF_CONTENT)
        svc = ImportService()
        result = svc.import_qif(f)
        expense = [r for r in result.records if r.description == "Grocery Store"][0]
        assert expense.transaction_type == "expense"
        assert expense.amount == Decimal("125.50")
        assert expense.category == "Food"

    def test_import_qif_income(self, tmp_path):
        f = tmp_path / "test.qif"
        f.write_text(self.QIF_CONTENT)
        svc = ImportService()
        result = svc.import_qif(f)
        income = [r for r in result.records if r.description == "Salary"][0]
        assert income.transaction_type == "income"
        assert income.amount == Decimal("5000")

    def test_import_qif_dates(self, tmp_path):
        f = tmp_path / "test.qif"
        f.write_text(self.QIF_CONTENT)
        svc = ImportService()
        result = svc.import_qif(f)
        assert result.records[0].date == date(2024, 1, 15)

    def test_import_qif_empty(self, tmp_path):
        f = tmp_path / "test.qif"
        f.write_text("!Type:Bank\n")
        svc = ImportService()
        result = svc.import_qif(f)
        assert result.success_count == 0


class TestImportServiceParseAmount:
    """Tests for amount parsing."""

    def test_parse_simple(self):
        svc = ImportService()
        assert svc._parse_amount("100.50") == Decimal("100.50")

    def test_parse_negative(self):
        svc = ImportService()
        assert svc._parse_amount("-50.25") == Decimal("-50.25")

    def test_parse_currency_symbol(self):
        svc = ImportService()
        assert svc._parse_amount("$1,234.56") == Decimal("1234.56")

    def test_parse_euro_symbol(self):
        svc = ImportService()
        assert svc._parse_amount("€100") == Decimal("100")

    def test_parse_parentheses_negative(self):
        svc = ImportService()
        assert svc._parse_amount("(500.00)") == Decimal("-500")

    def test_parse_trailing_minus(self):
        svc = ImportService()
        assert svc._parse_amount("100.00-") == Decimal("-100")

    def test_parse_european_format(self):
        svc = ImportService()
        assert svc._parse_amount("1.234,56") == Decimal("1234.56")

    def test_parse_comma_decimal(self):
        svc = ImportService()
        assert svc._parse_amount("100,50") == Decimal("100.50")

    def test_parse_empty(self):
        svc = ImportService()
        assert svc._parse_amount("") == Decimal("0")

    def test_parse_invalid(self):
        svc = ImportService()
        with pytest.raises(ValueError, match="Invalid amount"):
            svc._parse_amount("abc")


class TestImportServiceParseDate:
    """Tests for date parsing."""

    def test_parse_iso_format(self):
        svc = ImportService()
        assert svc._parse_date("2024-01-15") == date(2024, 1, 15)

    def test_parse_us_format(self):
        svc = ImportService()
        assert svc._parse_date("01/15/2024") == date(2024, 1, 15)

    def test_parse_european_format(self):
        svc = ImportService()
        assert svc._parse_date("15.01.2024") == date(2024, 1, 15)

    def test_parse_compact_format(self):
        svc = ImportService()
        assert svc._parse_date("20240115") == date(2024, 1, 15)

    def test_parse_preferred_format(self):
        svc = ImportService()
        result = svc._parse_date("15-01-2024", preferred_format="%d-%m-%Y")
        assert result == date(2024, 1, 15)

    def test_parse_empty(self):
        svc = ImportService()
        assert svc._parse_date("") is None

    def test_parse_invalid(self):
        svc = ImportService()
        assert svc._parse_date("not-a-date") is None


class TestImportServiceValidation:
    """Tests for data validation."""

    def test_validate_valid_records(self):
        svc = ImportService()
        records = [
            ImportRecord(date=date(2024, 1, 15), amount=Decimal("100"), description="Test"),
        ]
        valid, errors = svc.validate_data(records)
        assert len(valid) == 1
        assert len(errors) == 0

    def test_validate_amount_too_small(self):
        svc = ImportService()
        records = [
            ImportRecord(date=date(2024, 1, 15), amount=Decimal("0.001"), description="Tiny"),
        ]
        valid, errors = svc.validate_data(records, {"min_amount": Decimal("0.01")})
        assert len(valid) == 0
        assert len(errors) == 1

    def test_validate_amount_too_large(self):
        svc = ImportService()
        records = [
            ImportRecord(date=date(2024, 1, 15), amount=Decimal("99999999"), description="Big"),
        ]
        valid, errors = svc.validate_data(records, {"max_amount": Decimal("10000000")})
        assert len(valid) == 0
        assert len(errors) == 1

    def test_validate_future_date(self):
        svc = ImportService()
        records = [
            ImportRecord(date=date(2099, 1, 1), amount=Decimal("100"), description="Future"),
        ]
        valid, errors = svc.validate_data(records, {"max_date": date.today()})
        assert len(valid) == 0
        assert len(errors) == 1

    def test_validate_long_description(self):
        svc = ImportService()
        records = [
            ImportRecord(date=date(2024, 1, 1), amount=Decimal("10"), description="x" * 501),
        ]
        valid, errors = svc.validate_data(records)
        assert len(valid) == 0
        assert len(errors) == 1


class TestDataImportError:
    """Tests for DataImportError exception."""

    def test_creation(self):
        err = DataImportError("test error")
        assert str(err) == "test error"

    def test_is_exception(self):
        assert issubclass(DataImportError, Exception)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_creation(self):
        err = ValidationError("validation failed")
        assert str(err) == "validation failed"
