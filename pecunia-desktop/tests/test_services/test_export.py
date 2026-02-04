"""Tests for src/services/export.py — ExportService and related classes."""

import csv
import os
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from services.export import ExportService, ExportError


@pytest.fixture
def sample_transactions():
    """Provide sample transaction data for tests."""
    return [
        {
            "date": "2024-01-15",
            "description": "Grocery Store",
            "category": "Food",
            "amount": 125.50,
            "type": "expense",
            "account": "Checking",
            "notes": "Weekly shopping",
            "tags": ["groceries", "food"],
        },
        {
            "date": "2024-01-16",
            "description": "Salary",
            "category": "Income",
            "amount": 5000.00,
            "type": "income",
            "account": "Checking",
            "notes": "",
            "tags": [],
        },
        {
            "date": "2024-02-01",
            "description": "Rent",
            "category": "Housing",
            "amount": 1500.00,
            "type": "expense",
            "account": "Checking",
            "notes": "February rent",
            "tags": ["rent"],
        },
    ]


class TestExportServiceInit:
    """Tests for ExportService initialization."""

    def test_init(self):
        svc = ExportService()
        assert svc._progress_callback is None

    def test_set_progress_callback(self):
        svc = ExportService()
        cb = MagicMock()
        svc.set_progress_callback(cb)
        svc._report_progress(1, 10, "test")
        cb.assert_called_once_with(1, 10, "test")

    def test_report_progress_no_callback(self):
        svc = ExportService()
        svc._report_progress(1, 10, "test")  # Should not raise


class TestExportServiceFormatters:
    """Tests for ExportService format helper methods."""

    def test_format_amount_decimal(self):
        svc = ExportService()
        assert svc._format_amount(Decimal("125.50")) == "$125.50"

    def test_format_amount_int(self):
        svc = ExportService()
        assert svc._format_amount(100) == "$100.00"

    def test_format_amount_float(self):
        svc = ExportService()
        assert svc._format_amount(99.99) == "$99.99"

    def test_format_amount_string(self):
        svc = ExportService()
        assert svc._format_amount("N/A") == "N/A"

    def test_format_date_string(self):
        svc = ExportService()
        assert svc._format_date("2024-01-15") == "2024-01-15"

    def test_format_date_datetime(self):
        svc = ExportService()
        assert svc._format_date(datetime(2024, 1, 15, 12, 0)) == "2024-01-15"

    def test_format_date_date(self):
        svc = ExportService()
        assert svc._format_date(date(2024, 1, 15)) == "2024-01-15"

    def test_format_date_other(self):
        svc = ExportService()
        assert svc._format_date(12345) == "12345"


class TestExportServiceFilterByDateRange:
    """Tests for date range filtering."""

    def test_no_filter(self, sample_transactions):
        svc = ExportService()
        result = svc._filter_by_date_range(sample_transactions)
        assert len(result) == 3

    def test_filter_start_date(self, sample_transactions):
        svc = ExportService()
        result = svc._filter_by_date_range(
            sample_transactions,
            start_date=date(2024, 1, 16),
        )
        assert len(result) == 2  # Jan 16 and Feb 1

    def test_filter_end_date(self, sample_transactions):
        svc = ExportService()
        result = svc._filter_by_date_range(
            sample_transactions,
            end_date=date(2024, 1, 16),
        )
        assert len(result) == 2  # Jan 15 and Jan 16

    def test_filter_both_dates(self, sample_transactions):
        svc = ExportService()
        result = svc._filter_by_date_range(
            sample_transactions,
            start_date=date(2024, 1, 16),
            end_date=date(2024, 1, 16),
        )
        assert len(result) == 1

    def test_filter_with_datetime_values(self):
        svc = ExportService()
        txns = [
            {"date": datetime(2024, 1, 15, 12, 0), "amount": 100},
            {"date": datetime(2024, 2, 1, 12, 0), "amount": 200},
        ]
        result = svc._filter_by_date_range(
            txns,
            start_date=date(2024, 1, 20),
        )
        assert len(result) == 1


class TestExportServiceCSV:
    """Tests for CSV export functionality."""

    def test_export_csv_basic(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.csv")
        result = svc.export_transactions_to_csv(sample_transactions, output)
        assert os.path.exists(result)

        with open(result, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 3
        assert rows[0]["description"] == "Grocery Store"

    def test_export_csv_without_headers(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.csv")
        svc.export_transactions_to_csv(
            sample_transactions, output, include_headers=False,
        )
        with open(output, 'r') as f:
            content = f.read()
        assert "date" not in content.split('\n')[0]  # No header row

    def test_export_csv_with_date_filter(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.csv")
        svc.export_transactions_to_csv(
            sample_transactions, output,
            start_date=date(2024, 1, 16),
        )
        with open(output, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2

    def test_export_csv_progress_callback(self, tmp_path, sample_transactions):
        svc = ExportService()
        progress = []
        svc.set_progress_callback(lambda c, t, m: progress.append((c, t, m)))
        output = str(tmp_path / "export.csv")
        svc.export_transactions_to_csv(sample_transactions, output)
        assert len(progress) > 0

    def test_export_csv_tags_as_list(self, tmp_path):
        svc = ExportService()
        txns = [
            {"date": "2024-01-01", "description": "test", "amount": 10,
             "type": "expense", "tags": ["a", "b", "c"]},
        ]
        output = str(tmp_path / "export.csv")
        svc.export_transactions_to_csv(txns, output)
        with open(output, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert "a, b, c" == rows[0]["tags"]

    def test_export_csv_empty_transactions(self, tmp_path):
        svc = ExportService()
        output = str(tmp_path / "export.csv")
        svc.export_transactions_to_csv([], output)
        assert os.path.exists(output)


class TestExportServiceExcel:
    """Tests for Excel export functionality."""

    def test_export_excel_raises_if_unavailable(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.xlsx")
        with patch("services.export.EXCEL_AVAILABLE", False):
            with pytest.raises(ExportError, match="openpyxl"):
                svc.export_transactions_to_excel(sample_transactions, output)

    def test_export_excel_basic(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.xlsx")
        try:
            result = svc.export_transactions_to_excel(sample_transactions, output)
            assert os.path.exists(result)
        except ExportError as e:
            if "openpyxl" in str(e):
                pytest.skip("openpyxl not installed")
            raise

    def test_export_excel_custom_sheet(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.xlsx")
        try:
            svc.export_transactions_to_excel(
                sample_transactions, output, sheet_name="Custom",
            )
        except ExportError as e:
            if "openpyxl" in str(e):
                pytest.skip("openpyxl not installed")
            raise


class TestExportServicePDF:
    """Tests for PDF export functionality."""

    def test_export_pdf_raises_if_unavailable(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.pdf")
        with patch("services.export.PDF_AVAILABLE", False):
            with pytest.raises(ExportError, match="reportlab"):
                svc.export_transactions_to_pdf(sample_transactions, output)

    def test_export_pdf_basic(self, tmp_path, sample_transactions):
        svc = ExportService()
        output = str(tmp_path / "export.pdf")
        try:
            result = svc.export_transactions_to_pdf(sample_transactions, output)
            assert os.path.exists(result)
        except ExportError as e:
            if "reportlab" in str(e):
                pytest.skip("reportlab not installed")
            raise

    def test_export_budget_report_raises_if_unavailable(self, tmp_path):
        svc = ExportService()
        output = str(tmp_path / "budget.pdf")
        with patch("services.export.PDF_AVAILABLE", False):
            with pytest.raises(ExportError, match="reportlab"):
                svc.export_budget_report_to_pdf({}, output)


class TestExportServiceAvailableFormats:
    """Tests for available formats detection."""

    def test_csv_always_available(self):
        svc = ExportService()
        formats = svc.get_available_formats()
        assert formats["csv"] is True

    def test_excel_availability(self):
        svc = ExportService()
        formats = svc.get_available_formats()
        assert isinstance(formats["excel"], bool)

    def test_pdf_availability(self):
        svc = ExportService()
        formats = svc.get_available_formats()
        assert isinstance(formats["pdf"], bool)


class TestExportServiceExportToBytes:
    """Tests for export_to_bytes method."""

    def test_export_csv_to_bytes(self, sample_transactions):
        svc = ExportService()
        result = svc.export_to_bytes(sample_transactions, "csv")
        assert isinstance(result, BytesIO)
        content = result.read()
        assert len(content) > 0

    def test_export_unsupported_format(self, sample_transactions):
        svc = ExportService()
        with pytest.raises(ExportError, match="Unsupported format"):
            svc.export_to_bytes(sample_transactions, "xml")

    def test_export_excel_to_bytes(self, sample_transactions):
        svc = ExportService()
        try:
            result = svc.export_to_bytes(sample_transactions, "excel")
            assert isinstance(result, BytesIO)
        except ExportError as e:
            if "openpyxl" in str(e):
                pytest.skip("openpyxl not installed")
            raise


class TestExportError:
    """Tests for ExportError exception."""

    def test_creation(self):
        err = ExportError("test error")
        assert str(err) == "test error"

    def test_is_exception(self):
        assert issubclass(ExportError, Exception)
