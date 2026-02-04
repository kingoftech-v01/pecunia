"""Tests for CSV importer module."""
import io
import pytest
from decimal import Decimal
from datetime import date

from apps.transactions.importers.csv_importer import CSVImporter, ColumnMapper
from apps.transactions.importers.base import ValidationError


SAMPLE_CSV = """Date,Amount,Description,Type,Merchant,Category
2026-01-15,-50.00,Weekly shopping,expense,Grocery Store,Groceries
2026-01-16,1000.00,Monthly salary,income,Employer Inc.,Salary
2026-01-17,-25.00,Bus pass,expense,Transit Co,Transport
"""

SAMPLE_CSV_SEMICOLON = """Date;Amount;Description;Type;Merchant
2026-01-15;-50.00;Weekly shopping;expense;Grocery Store
2026-01-16;1000.00;Monthly salary;income;Employer Inc.
"""

SAMPLE_CSV_DEBIT_CREDIT = """Date,Description,Debit,Credit,Balance
2026-01-15,Weekly shopping,50.00,,950.00
2026-01-16,Monthly salary,,1000.00,1950.00
"""

SAMPLE_CSV_EUROPEAN = """Datum;Betrag;Beschreibung
15.01.2026;-50,00;Einkauf
16.01.2026;1.000,00;Gehalt
"""

EMPTY_CSV = """Date,Amount,Description
"""


class TestColumnMapper:
    """Tests for ColumnMapper class."""

    def test_detect_mapping_standard(self):
        mapper = ColumnMapper()
        headers = ["Date", "Amount", "Description", "Type", "Merchant"]
        mapping = mapper.detect_mapping(headers)
        assert "date" in mapping
        assert "amount" in mapping
        assert "description" in mapping

    def test_detect_mapping_alternate_names(self):
        mapper = ColumnMapper()
        headers = ["posted_date", "value", "memo", "payee"]
        mapping = mapper.detect_mapping(headers)
        assert "date" in mapping
        assert "amount" in mapping

    def test_detect_mapping_debit_credit(self):
        mapper = ColumnMapper()
        headers = ["Date", "Description", "Debit", "Credit"]
        mapping = mapper.detect_mapping(headers)
        assert "date" in mapping
        assert "debit" in mapping
        assert "credit" in mapping

    def test_custom_mappings_take_priority(self):
        mapper = ColumnMapper(custom_mappings={"date": "MyDate"})
        headers = ["MyDate", "Date", "Amount"]
        mapping = mapper.detect_mapping(headers)
        assert mapping["date"] == "MyDate"

    def test_get_mapping(self):
        mapper = ColumnMapper()
        headers = ["Date", "Amount"]
        mapper.detect_mapping(headers)
        assert mapper.get_mapping() == mapper._detected_mappings

    def test_map_row_basic(self):
        mapper = ColumnMapper()
        mapper.detect_mapping(["Date", "Amount", "Description"])
        row = {"Date": "2026-01-15", "Amount": "100.00", "Description": "Test"}
        result = mapper.map_row(row)
        assert result["date"] == "2026-01-15"
        assert result["amount"] == "100.00"

    def test_map_row_debit_column(self):
        mapper = ColumnMapper()
        mapper.detect_mapping(["Date", "Description", "Debit", "Credit"])
        row = {"Date": "2026-01-15", "Description": "Test", "Debit": "50.00", "Credit": ""}
        result = mapper.map_row(row)
        assert result["amount"] == "-50.00"
        assert result["type"] == "expense"

    def test_map_row_credit_column(self):
        mapper = ColumnMapper()
        mapper.detect_mapping(["Date", "Description", "Debit", "Credit"])
        row = {"Date": "2026-01-15", "Description": "Test", "Debit": "", "Credit": "100.00"}
        result = mapper.map_row(row)
        assert result["amount"] == "100.00"
        assert result["type"] == "income"

    def test_map_row_missing_column(self):
        mapper = ColumnMapper()
        mapper.detect_mapping(["Date", "Amount"])
        row = {"Date": "2026-01-15"}
        result = mapper.map_row(row)
        assert "date" in result
        assert "amount" not in result


class TestCSVImporter:
    """Tests for CSVImporter class."""

    def test_get_supported_formats(self):
        importer = CSVImporter()
        assert "csv" in importer.get_supported_formats()
        assert "txt" in importer.get_supported_formats()
        assert "tsv" in importer.get_supported_formats()

    def test_detect_delimiter_comma(self):
        importer = CSVImporter()
        assert importer.detect_delimiter("a,b,c\n1,2,3") == ","

    def test_detect_delimiter_semicolon(self):
        importer = CSVImporter()
        assert importer.detect_delimiter("a;b;c\n1;2;3") == ";"

    def test_detect_delimiter_tab(self):
        importer = CSVImporter()
        assert importer.detect_delimiter("a\tb\tc\n1\t2\t3") == "\t"

    def test_parse_standard_csv(self):
        importer = CSVImporter()
        result = importer.parse(io.StringIO(SAMPLE_CSV))
        assert result.success is True
        assert result.total_rows == 3
        assert result.imported_count == 3
        # Check types
        types = [t.type.value for t in result.transactions]
        assert "expense" in types
        assert "income" in types

    def test_parse_semicolon_csv(self):
        importer = CSVImporter()
        result = importer.parse(io.StringIO(SAMPLE_CSV_SEMICOLON))
        assert result.success is True
        assert result.imported_count == 2

    def test_parse_debit_credit_columns(self):
        importer = CSVImporter()
        result = importer.parse(io.StringIO(SAMPLE_CSV_DEBIT_CREDIT))
        assert result.success is True
        assert result.imported_count >= 1

    def test_parse_empty_csv(self):
        importer = CSVImporter()
        result = importer.parse(io.StringIO(EMPTY_CSV))
        assert result.total_rows == 0
        assert result.imported_count == 0

    def test_parse_with_explicit_delimiter(self):
        importer = CSVImporter(delimiter=";")
        result = importer.parse(io.StringIO(SAMPLE_CSV_SEMICOLON))
        assert result.success is True
        assert result.imported_count == 2

    def test_parse_with_skip_rows(self):
        importer = CSVImporter(skip_rows=1)
        result = importer.parse(io.StringIO(SAMPLE_CSV))
        assert result.total_rows == 2  # 3 - 1 skipped

    def test_parse_binary_content(self):
        importer = CSVImporter()
        content = SAMPLE_CSV.encode("utf-8")
        result = importer.parse(io.BytesIO(content))
        assert result.success is True
        assert result.imported_count == 3

    def test_parse_with_bom(self):
        importer = CSVImporter()
        content = b"\xef\xbb\xbf" + SAMPLE_CSV.encode("utf-8")
        result = importer.parse(io.BytesIO(content))
        assert result.success is True

    def test_parse_reports_progress(self):
        called = []
        importer = CSVImporter()
        importer.set_progress_callback(lambda c, t: called.append((c, t)))
        importer.parse(io.StringIO(SAMPLE_CSV))
        assert len(called) > 0

    def test_parse_handles_invalid_row(self):
        csv_content = "Date,Amount,Description\n2026-01-15,not-a-number,Test\n"
        importer = CSVImporter()
        result = importer.parse(io.StringIO(csv_content))
        assert result.error_count >= 1

    def test_parse_all_errors_means_failure(self):
        csv_content = "Date,Amount,Description\nBAD,BAD,Test\n"
        importer = CSVImporter()
        result = importer.parse(io.StringIO(csv_content))
        assert result.success is False

    def test_preview(self):
        importer = CSVImporter()
        result = importer.preview(io.StringIO(SAMPLE_CSV))
        assert result["success"] is True
        assert "headers" in result
        assert "delimiter" in result
        assert "detected_mapping" in result
        assert "sample_rows" in result
        assert len(result["sample_rows"]) <= 10

    def test_preview_binary(self):
        importer = CSVImporter()
        content = SAMPLE_CSV.encode("utf-8")
        result = importer.preview(io.BytesIO(content))
        assert result["success"] is True

    def test_preview_limit(self):
        importer = CSVImporter()
        result = importer.preview(io.StringIO(SAMPLE_CSV), num_rows=1)
        assert len(result["sample_rows"]) == 1

    def test_preview_error(self):
        """Preview with bad data should return error."""
        importer = CSVImporter()
        # Create a file object that raises an error on read
        class BadFile:
            def read(self):
                raise Exception("Broken file")
        result = importer.preview(BadFile())
        assert result["success"] is False
        assert "error" in result

    def test_validate_mapping_valid(self):
        importer = CSVImporter()
        headers = ["Date", "Amount", "Description"]
        mapping = {"date": "Date", "amount": "Amount"}
        errors = importer.validate_mapping(mapping, headers)
        assert len(errors) == 0

    def test_validate_mapping_missing_date(self):
        importer = CSVImporter()
        headers = ["Amount", "Description"]
        mapping = {"amount": "Amount"}
        errors = importer.validate_mapping(mapping, headers)
        assert any("date" in e.lower() for e in errors)

    def test_validate_mapping_missing_amount(self):
        importer = CSVImporter()
        headers = ["Date", "Description"]
        mapping = {"date": "Date"}
        errors = importer.validate_mapping(mapping, headers)
        assert any("amount" in e.lower() for e in errors)

    def test_validate_mapping_missing_amount_ok_with_debit(self):
        importer = CSVImporter()
        headers = ["Date", "Debit", "Credit"]
        mapping = {"date": "Date", "debit": "Debit", "credit": "Credit"}
        errors = importer.validate_mapping(mapping, headers)
        assert not any("amount" in e.lower() for e in errors)

    def test_validate_mapping_column_not_in_headers(self):
        importer = CSVImporter()
        headers = ["Date", "Amount"]
        mapping = {"date": "Date", "description": "NonExistent"}
        errors = importer.validate_mapping(mapping, headers)
        assert any("NonExistent" in e for e in errors)

    def test_validate_mapping_date_column_not_found(self):
        importer = CSVImporter()
        headers = ["Date", "Amount"]
        mapping = {"date": "WrongDate"}
        errors = importer.validate_mapping(mapping, headers)
        assert len(errors) > 0

    def test_parse_european_format(self):
        importer = CSVImporter()
        result = importer.parse(io.StringIO(SAMPLE_CSV_EUROPEAN))
        assert result.success is True
        assert result.imported_count >= 1
