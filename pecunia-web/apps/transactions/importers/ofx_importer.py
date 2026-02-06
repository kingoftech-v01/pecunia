"""
OFX/QFX Importer Module.

Provides import functionality for Open Financial Exchange (OFX)
and Quicken Financial Exchange (QFX) files.
"""
import io
import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Any, BinaryIO, Dict, List, Optional, TextIO, Union
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element as _Element

from .base import (
    BaseImporter,
    ImportResult,
    ImportError,
    ValidationError,
    ParsedTransaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


class OFXParser:
    """
    Parser for OFX (Open Financial Exchange) format.

    Handles both SGML-based OFX 1.x and XML-based OFX 2.x formats.
    """

    # OFX transaction types to internal types
    TRANSACTION_TYPE_MAP = {
        'CREDIT': TransactionType.INCOME,
        'DEBIT': TransactionType.EXPENSE,
        'INT': TransactionType.INCOME,  # Interest
        'DIV': TransactionType.INCOME,  # Dividend
        'FEE': TransactionType.EXPENSE,
        'SRVCHG': TransactionType.EXPENSE,  # Service charge
        'DEP': TransactionType.INCOME,  # Deposit
        'ATM': TransactionType.EXPENSE,
        'POS': TransactionType.EXPENSE,  # Point of sale
        'XFER': TransactionType.TRANSFER,
        'CHECK': TransactionType.EXPENSE,
        'PAYMENT': TransactionType.EXPENSE,
        'CASH': TransactionType.EXPENSE,
        'DIRECTDEP': TransactionType.INCOME,  # Direct deposit
        'DIRECTDEBIT': TransactionType.EXPENSE,  # Direct debit
        'REPEATPMT': TransactionType.EXPENSE,  # Repeating payment
        'OTHER': TransactionType.EXPENSE,
    }

    def __init__(self):
        self.account_info: Dict[str, Any] = {}
        self.transactions: List[Dict[str, Any]] = []

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse OFX content.

        Args:
            content: OFX file content as string

        Returns:
            Dictionary with account info and transactions
        """
        # OFX 1.x uses SGML, 2.x uses XML; check first 100 chars for declaration.
        if '<?xml' in content[:100].lower() or '<?OFX' in content[:100]:
            return self._parse_xml(content)
        else:
            return self._parse_sgml(content)

    def _parse_sgml(self, content: str) -> Dict[str, Any]:
        """
        Parse SGML-based OFX 1.x format.

        Converts SGML to XML-like structure for parsing.
        """
        # Remove headers
        if '<OFX>' in content:
            content = content[content.index('<OFX>'):]

        # Convert SGML to valid XML
        content = self._sgml_to_xml(content)

        return self._parse_xml(content)

    def _sgml_to_xml(self, content: str) -> str:
        """
        Convert SGML OFX to valid XML.

        OFX SGML uses unclosed tags which need to be closed for XML parsing.
        """
        # SGML allows unclosed tags; data_tags need explicit closing for XML parsing.
        data_tags = {
            'TRNTYPE', 'DTPOSTED', 'DTUSER', 'DTAVAIL', 'TRNAMT',
            'FITID', 'CORRECTFITID', 'CORRECTACTION', 'SRVRTID',
            'CHECKNUM', 'REFNUM', 'SIC', 'PAYEEID', 'NAME', 'MEMO',
            'ACCTID', 'ACCTTYPE', 'BANKID', 'BRANCHID', 'ACCTKEY',
            'DTSTART', 'DTEND', 'BALAMT', 'DTASOF', 'CURDEF',
            'ORG', 'FID', 'INTU.BID', 'INTU.USERID',
        }

        lines = content.split('\n')
        result = []
        tag_stack = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match opening tags
            match = re.match(r'<(\w+)>(.*)$', line)
            if match:
                tag = match.group(1).upper()
                value = match.group(2).strip()

                if value:
                    # Tag with value - self-closing
                    result.append(f'<{tag}>{value}</{tag}>')
                elif tag in data_tags:
                    # Data tag without value
                    result.append(f'<{tag}></{tag}>')
                else:
                    # Container tag
                    result.append(f'<{tag}>')
                    tag_stack.append(tag)
            # Match closing tags
            elif line.startswith('</'):
                result.append(line.upper())
                if tag_stack:
                    tag_stack.pop()
            else:
                result.append(line)

        # Close any remaining open tags
        while tag_stack:
            result.append(f'</{tag_stack.pop()}>')

        return '\n'.join(result)

    def _parse_xml(self, content: str) -> Dict[str, Any]:
        """
        Parse XML-based OFX content.

        Args:
            content: XML OFX content

        Returns:
            Dictionary with account info and transactions
        """
        # Clean up content
        content = content.strip()

        # Remove XML declaration if present
        if content.startswith('<?'):
            end = content.find('?>')
            if end != -1:
                content = content[end + 2:].strip()

        # Remove OFX headers
        while content and not content.startswith('<OFX'):
            newline = content.find('\n')
            if newline == -1:
                break
            content = content[newline + 1:].strip()

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            # Try wrapping in OFX tag
            try:
                root = ET.fromstring(f'<OFX>{content}</OFX>')
            except ET.ParseError:
                raise ImportError(f"Failed to parse OFX XML: {e}")

        result = {
            'account': {},
            'transactions': [],
            'balance': None,
        }

        # Find bank statement response
        for stmtrs in root.iter():
            if stmtrs.tag.upper() in ('STMTRS', 'CCSTMTRS'):
                # Extract account info
                result['account'] = self._extract_account_info(stmtrs)

                # Extract transactions
                for banktranlist in stmtrs.iter():
                    if banktranlist.tag.upper() == 'BANKTRANLIST':
                        result['transactions'] = self._extract_transactions(banktranlist)

                # Extract balance
                for ledgerbal in stmtrs.iter():
                    if ledgerbal.tag.upper() == 'LEDGERBAL':
                        result['balance'] = self._extract_balance(ledgerbal)

        return result

    def _extract_account_info(self, element: _Element) -> Dict[str, Any]:
        """Extract account information from statement."""
        info = {}

        # Look for account ID
        for child in element.iter():
            tag = child.tag.upper()
            if tag == 'ACCTID':
                info['account_id'] = child.text
            elif tag == 'ACCTTYPE':
                info['account_type'] = child.text
            elif tag == 'BANKID':
                info['bank_id'] = child.text
            elif tag == 'CURDEF':
                info['currency'] = child.text

        return info

    def _extract_transactions(self, banktranlist: _Element) -> List[Dict[str, Any]]:
        """Extract transactions from bank transaction list."""
        transactions = []

        for stmttrn in banktranlist.iter():
            if stmttrn.tag.upper() == 'STMTTRN':
                tx = self._parse_transaction(stmttrn)
                if tx:
                    transactions.append(tx)

        return transactions

    def _parse_transaction(self, element: _Element) -> Optional[Dict[str, Any]]:
        """Parse a single transaction element."""
        tx = {}

        for child in element:
            tag = child.tag.upper()
            value = child.text.strip() if child.text else ''

            if tag == 'TRNTYPE':
                tx['type'] = value
            elif tag == 'DTPOSTED':
                tx['date'] = self._parse_ofx_date(value)
            elif tag == 'TRNAMT':
                tx['amount'] = value
            elif tag == 'FITID':
                tx['fitid'] = value
            elif tag == 'NAME':
                tx['name'] = value
            elif tag == 'MEMO':
                tx['memo'] = value
            elif tag == 'CHECKNUM':
                tx['check_number'] = value
            elif tag == 'REFNUM':
                tx['reference'] = value

        return tx if tx else None

    def _extract_balance(self, element: _Element) -> Optional[Dict[str, Any]]:
        """Extract balance information."""
        balance = {}

        for child in element:
            tag = child.tag.upper()
            if tag == 'BALAMT':
                balance['amount'] = child.text
            elif tag == 'DTASOF':
                balance['date'] = self._parse_ofx_date(child.text)

        return balance if balance else None

    def _parse_ofx_date(self, value: str) -> Optional[date]:
        """
        Parse OFX date format.

        OFX dates are in format: YYYYMMDDHHMMSS[.XXX[:tz]]
        """
        if not value:
            return None

        # Remove timezone and milliseconds
        value = value.split('[')[0].split('.')[0]

        # Parse date portion
        try:
            if len(value) >= 8:
                return datetime.strptime(value[:8], '%Y%m%d').date()
        except ValueError:
            pass

        return None


class OFXImporter(BaseImporter):
    """
    OFX/QFX file importer.

    Supports:
    - OFX 1.x (SGML format)
    - OFX 2.x (XML format)
    - QFX (Quicken variant of OFX)
    """

    def __init__(self, user=None, bank_account=None):
        """
        Initialize the OFX importer.

        Args:
            user: Django user instance
            bank_account: Optional bank account to link transactions
        """
        super().__init__(user, bank_account)
        self.parser = OFXParser()

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file extensions."""
        return ['ofx', 'qfx']

    def parse(self, file_obj: Union[BinaryIO, TextIO]) -> ImportResult:
        """
        Parse an OFX/QFX file and extract transactions.

        Args:
            file_obj: File object to parse

        Returns:
            ImportResult with parsed transactions
        """
        result = ImportResult(success=True)

        try:
            # Read file content
            content = self._read_file(file_obj)

            # Parse OFX
            parsed = self.parser.parse(content)

            # Store account info
            if parsed.get('account'):
                result.warnings.append(
                    f"Account: {parsed['account'].get('account_id', 'Unknown')}"
                )

            transactions = parsed.get('transactions', [])
            result.total_rows = len(transactions)

            if not transactions:
                result.add_warning("No transactions found in OFX file")
                return result

            # Process each transaction
            for i, tx in enumerate(transactions):
                try:
                    parsed_tx = self._convert_transaction(tx, i + 1)
                    result.add_transaction(parsed_tx)
                    self._report_progress(i + 1, result.total_rows)

                except ValidationError as e:
                    result.add_error(str(e), i + 1, {
                        'field': e.field,
                        'value': e.value
                    })
                except Exception as e:
                    result.add_error(str(e), i + 1)

            # Add balance info if available
            if parsed.get('balance'):
                result.add_warning(
                    f"Ending balance: {parsed['balance'].get('amount', 'N/A')}"
                )

        except ImportError as e:
            result.success = False
            result.add_error(str(e))
        except Exception as e:
            result.success = False
            result.add_error(f"Unexpected error: {e}")
            logger.exception("OFX import failed")

        return result

    def _read_file(self, file_obj: Union[BinaryIO, TextIO]) -> str:
        """Read file content with encoding detection."""
        # Reset to beginning
        file_obj.seek(0)
        content = file_obj.read()

        if isinstance(content, bytes):
            # Try UTF-8 first
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                pass

            # Detect encoding
            encoding = self.detect_encoding(io.BytesIO(content))
            return content.decode(encoding, errors='replace')

        return content

    def _convert_transaction(self, tx: Dict[str, Any],
                            line_number: int) -> ParsedTransaction:
        """
        Convert OFX transaction to ParsedTransaction.

        Args:
            tx: OFX transaction dictionary
            line_number: Line number for error reporting

        Returns:
            ParsedTransaction instance
        """
        # Parse amount
        amount_str = tx.get('amount', '0')
        amount = self._parse_amount(amount_str, line_number)

        # Parse date
        tx_date = tx.get('date')
        if not tx_date:
            raise ValidationError('date', 'Transaction date is missing')

        # Determine type
        ofx_type = tx.get('type', '').upper()
        tx_type = OFXParser.TRANSACTION_TYPE_MAP.get(
            ofx_type,
            TransactionType.EXPENSE if amount < 0 else TransactionType.INCOME
        )

        # Combine name and memo for description
        name = tx.get('name', '')
        memo = tx.get('memo', '')
        description = f"{name} - {memo}".strip(' -') if memo else name

        # Reference from FITID or check number
        reference = tx.get('fitid', '') or tx.get('reference', '')
        if tx.get('check_number'):
            reference = f"Check #{tx['check_number']}"

        return ParsedTransaction(
            amount=abs(amount),
            transaction_date=tx_date,
            type=tx_type,
            description=description,
            merchant=name,
            reference=reference,
            raw_data=tx,
        )

    def get_account_info(self, file_obj: Union[BinaryIO, TextIO]) -> Dict[str, Any]:
        """
        Extract account information from OFX file.

        Args:
            file_obj: File object to parse

        Returns:
            Dictionary with account information
        """
        content = self._read_file(file_obj)
        parsed = self.parser.parse(content)

        return {
            'account': parsed.get('account', {}),
            'balance': parsed.get('balance'),
            'transaction_count': len(parsed.get('transactions', [])),
        }
