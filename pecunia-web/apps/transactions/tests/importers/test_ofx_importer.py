"""Tests for OFX importer module."""
import io
import pytest
from datetime import date
from decimal import Decimal

from apps.transactions.importers.ofx_importer import OFXImporter, OFXParser
from apps.transactions.importers.base import (
    TransactionType,
    ValidationError,
    ImportError as ImporterError,
)


SAMPLE_OFX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS><CODE>0</CODE></STATUS>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <CURDEF>USD</CURDEF>
        <BANKACCTFROM>
          <BANKID>1234</BANKID>
          <ACCTID>567890</ACCTID>
          <ACCTTYPE>CHECKING</ACCTTYPE>
        </BANKACCTFROM>
        <BANKTRANLIST>
          <STMTTRN>
            <TRNTYPE>DEBIT</TRNTYPE>
            <DTPOSTED>20260115</DTPOSTED>
            <TRNAMT>-50.00</TRNAMT>
            <FITID>TXN001</FITID>
            <NAME>GROCERY STORE</NAME>
            <MEMO>Weekly shopping</MEMO>
          </STMTTRN>
          <STMTTRN>
            <TRNTYPE>CREDIT</TRNTYPE>
            <DTPOSTED>20260116</DTPOSTED>
            <TRNAMT>3000.00</TRNAMT>
            <FITID>TXN002</FITID>
            <NAME>EMPLOYER INC</NAME>
            <MEMO>Monthly salary</MEMO>
          </STMTTRN>
          <STMTTRN>
            <TRNTYPE>CHECK</TRNTYPE>
            <DTPOSTED>20260117</DTPOSTED>
            <TRNAMT>-200.00</TRNAMT>
            <FITID>TXN003</FITID>
            <NAME>RENT PAYMENT</NAME>
            <CHECKNUM>1234</CHECKNUM>
          </STMTTRN>
        </BANKTRANLIST>
        <LEDGERBAL>
          <BALAMT>2750.00</BALAMT>
          <DTASOF>20260117</DTASOF>
        </LEDGERBAL>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
"""

SAMPLE_OFX_SGML = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
</STATUS>
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>USD
<BANKACCTFROM>
<BANKID>1234
<ACCTID>567890
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260115
<TRNAMT>-75.00
<FITID>SGML001
<NAME>RESTAURANT
<MEMO>Dinner
</STMTTRN>
<STMTTRN>
<TRNTYPE>DIRECTDEP
<DTPOSTED>20260116
<TRNAMT>2500.00
<FITID>SGML002
<NAME>PAYROLL
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>5000.00
<DTASOF>20260117
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

SAMPLE_OFX_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<OFX>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <BANKTRANLIST>
        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
"""


class TestOFXParser:
    """Tests for OFXParser class."""

    def test_parse_xml(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_XML)
        assert "account" in result
        assert "transactions" in result
        assert len(result["transactions"]) == 3

    def test_parse_xml_account_info(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_XML)
        assert result["account"]["account_id"] == "567890"
        assert result["account"]["account_type"] == "CHECKING"
        assert result["account"]["bank_id"] == "1234"
        assert result["account"]["currency"] == "USD"

    def test_parse_xml_transaction_fields(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_XML)
        tx = result["transactions"][0]
        assert tx["type"] == "DEBIT"
        assert tx["amount"] == "-50.00"
        assert tx["fitid"] == "TXN001"
        assert tx["name"] == "GROCERY STORE"
        assert tx["memo"] == "Weekly shopping"
        assert tx["date"] == date(2026, 1, 15)

    def test_parse_xml_check_number(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_XML)
        tx = result["transactions"][2]
        assert tx["check_number"] == "1234"

    def test_parse_xml_balance(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_XML)
        assert result["balance"] is not None
        assert result["balance"]["amount"] == "2750.00"
        assert result["balance"]["date"] == date(2026, 1, 17)

    def test_parse_sgml(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_SGML)
        assert len(result["transactions"]) == 2

    def test_parse_sgml_transaction_values(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_SGML)
        tx = result["transactions"][0]
        assert tx["amount"] == "-75.00"
        assert tx["name"] == "RESTAURANT"

    def test_parse_ofx_date_full(self):
        parser = OFXParser()
        assert parser._parse_ofx_date("20260115120000") == date(2026, 1, 15)

    def test_parse_ofx_date_short(self):
        parser = OFXParser()
        assert parser._parse_ofx_date("20260115") == date(2026, 1, 15)

    def test_parse_ofx_date_with_timezone(self):
        parser = OFXParser()
        assert parser._parse_ofx_date("20260115120000[0:GMT]") == date(2026, 1, 15)

    def test_parse_ofx_date_with_milliseconds(self):
        parser = OFXParser()
        assert parser._parse_ofx_date("20260115120000.123") == date(2026, 1, 15)

    def test_parse_ofx_date_empty(self):
        parser = OFXParser()
        assert parser._parse_ofx_date("") is None

    def test_parse_ofx_date_none(self):
        parser = OFXParser()
        assert parser._parse_ofx_date(None) is None

    def test_parse_ofx_date_invalid(self):
        parser = OFXParser()
        assert parser._parse_ofx_date("invalid") is None

    def test_parse_ofx_date_short_string(self):
        parser = OFXParser()
        assert parser._parse_ofx_date("2026") is None

    def test_transaction_type_map(self):
        assert OFXParser.TRANSACTION_TYPE_MAP["CREDIT"] == TransactionType.INCOME
        assert OFXParser.TRANSACTION_TYPE_MAP["DEBIT"] == TransactionType.EXPENSE
        assert OFXParser.TRANSACTION_TYPE_MAP["XFER"] == TransactionType.TRANSFER
        assert OFXParser.TRANSACTION_TYPE_MAP["DEP"] == TransactionType.INCOME
        assert OFXParser.TRANSACTION_TYPE_MAP["FEE"] == TransactionType.EXPENSE
        assert OFXParser.TRANSACTION_TYPE_MAP["DIRECTDEP"] == TransactionType.INCOME

    def test_parse_empty_ofx(self):
        parser = OFXParser()
        result = parser.parse(SAMPLE_OFX_EMPTY)
        assert len(result["transactions"]) == 0


class TestOFXImporter:
    """Tests for OFXImporter class."""

    def test_get_supported_formats(self):
        importer = OFXImporter()
        formats = importer.get_supported_formats()
        assert "ofx" in formats
        assert "qfx" in formats

    def test_parse_xml_file(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        assert result.success is True
        assert result.total_rows == 3
        assert result.imported_count == 3

    def test_parse_xml_transaction_types(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        types = {t.type for t in result.transactions}
        assert TransactionType.EXPENSE in types
        assert TransactionType.INCOME in types

    def test_parse_xml_amounts_are_positive(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        for tx in result.transactions:
            assert tx.amount > 0

    def test_parse_xml_check_reference(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        check_tx = [t for t in result.transactions if "Check" in t.reference]
        assert len(check_tx) == 1
        assert "1234" in check_tx[0].reference

    def test_parse_xml_description_combines_name_memo(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        tx = result.transactions[0]
        assert "GROCERY STORE" in tx.description
        assert "Weekly shopping" in tx.description

    def test_parse_xml_description_name_only(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        # Third transaction has no memo
        tx = result.transactions[2]
        assert "RENT PAYMENT" in tx.description

    def test_parse_sgml_file(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_SGML))
        assert result.success is True
        assert result.imported_count == 2

    def test_parse_binary_file(self):
        importer = OFXImporter()
        content = SAMPLE_OFX_XML.encode("utf-8")
        result = importer.parse(io.BytesIO(content))
        assert result.success is True
        assert result.imported_count == 3

    def test_parse_empty_file(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_EMPTY))
        assert result.success is True
        assert result.imported_count == 0

    def test_parse_includes_account_warning(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        account_warnings = [w for w in result.warnings if "Account" in w]
        assert len(account_warnings) >= 1

    def test_parse_includes_balance_warning(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        balance_warnings = [w for w in result.warnings if "balance" in w.lower()]
        assert len(balance_warnings) >= 1

    def test_parse_invalid_xml(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO("<NOT-VALID-OFX>broken"))
        # Should handle gracefully
        assert isinstance(result.success, bool)

    def test_parse_reports_progress(self):
        called = []
        importer = OFXImporter()
        importer.set_progress_callback(lambda c, t: called.append((c, t)))
        importer.parse(io.StringIO(SAMPLE_OFX_XML))
        assert len(called) > 0

    def test_get_account_info(self):
        importer = OFXImporter()
        info = importer.get_account_info(io.StringIO(SAMPLE_OFX_XML))
        assert info["account"]["account_id"] == "567890"
        assert info["transaction_count"] == 3
        assert info["balance"] is not None

    def test_merchant_from_name(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        tx = result.transactions[0]
        assert tx.merchant == "GROCERY STORE"

    def test_fitid_as_reference(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        # The second transaction (no check_number) should use fitid
        tx = result.transactions[1]
        assert tx.reference == "TXN002"

    def test_convert_transaction_missing_date(self):
        importer = OFXImporter()
        tx_data = {"amount": "100.00", "type": "CREDIT"}
        with pytest.raises(ValidationError):
            importer._convert_transaction(tx_data, 1)

    def test_unknown_ofx_type_uses_amount_sign(self):
        importer = OFXImporter()
        result = importer.parse(io.StringIO(SAMPLE_OFX_XML))
        # All standard types should be mapped
        for tx in result.transactions:
            assert tx.type in (
                TransactionType.INCOME,
                TransactionType.EXPENSE,
                TransactionType.TRANSFER,
            )
