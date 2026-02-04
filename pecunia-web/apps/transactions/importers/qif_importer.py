"""
QIF Importer Module.

Provides import functionality for Quicken Interchange Format (QIF) files.
"""
import io
import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Any, BinaryIO, Dict, List, Optional, TextIO, Union

from .base import (
    BaseImporter,
    ImportResult,
    ImportError,
    ValidationError,
    ParsedTransaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


class QIFParser:
    """
    Parser for QIF (Quicken Interchange Format) files.

    QIF Format:
    - Lines starting with ! indicate account type or header
    - Each field starts with a single letter code
    - Records are separated by ^ (caret)

    Field codes:
    - D: Date
    - T: Amount
    - U: Amount (alternative)
    - M: Memo
    - P: Payee
    - N: Check number or reference
    - L: Category
    - C: Cleared status
    - A: Address (multiple lines)
    - S: Split category
    - E: Split memo
    - $: Split amount
    """

    # Account type headers
    ACCOUNT_TYPES = {
        '!Type:Bank': 'bank',
        '!Type:Cash': 'cash',
        '!Type:CCard': 'credit_card',
        '!Type:Invst': 'investment',
        '!Type:Oth A': 'asset',
        '!Type:Oth L': 'liability',
    }

    def __init__(self):
        self.account_type: Optional[str] = None
        self.account_name: Optional[str] = None

    def parse(self, content: str) -> Dict[str, Any]:
        """
        Parse QIF content.

        Args:
            content: QIF file content

        Returns:
            Dictionary with account info and transactions
        """
        lines = content.split('\n')
        transactions = []
        current_record: Dict[str, Any] = {}
        splits: List[Dict[str, Any]] = []
        current_split: Dict[str, Any] = {}

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Check for account type header
            if line.startswith('!'):
                if line in self.ACCOUNT_TYPES:
                    self.account_type = self.ACCOUNT_TYPES[line]
                elif line.startswith('!Account'):
                    # Account definition follows
                    pass
                continue

            # Record separator
            if line == '^':
                if current_record:
                    # Add any splits to the record
                    if splits:
                        current_record['splits'] = splits
                        splits = []
                    if current_split:
                        splits.append(current_split)
                        current_split = {}

                    transactions.append(current_record)
                    current_record = {}
                continue

            # Parse field
            if len(line) >= 1:
                code = line[0]
                value = line[1:].strip()

                self._parse_field(code, value, current_record,
                                 current_split, splits)

        # Add last record if present
        if current_record:
            if splits:
                current_record['splits'] = splits
            transactions.append(current_record)

        return {
            'account_type': self.account_type,
            'account_name': self.account_name,
            'transactions': transactions,
        }

    def _parse_field(self, code: str, value: str,
                    record: Dict[str, Any],
                    current_split: Dict[str, Any],
                    splits: List[Dict[str, Any]]):
        """Parse a single QIF field."""

        if code == 'D':
            record['date'] = self._parse_qif_date(value)
        elif code in ('T', 'U'):
            record['amount'] = value
        elif code == 'M':
            record['memo'] = value
        elif code == 'P':
            record['payee'] = value
        elif code == 'N':
            record['number'] = value
        elif code == 'L':
            record['category'] = value
        elif code == 'C':
            record['cleared'] = value
        elif code == 'A':
            # Address line
            if 'address' not in record:
                record['address'] = []
            record['address'].append(value)
        # Split transaction fields
        elif code == 'S':
            # New split category
            if current_split:
                splits.append(current_split)
            current_split.clear()
            current_split['category'] = value
        elif code == 'E':
            current_split['memo'] = value
        elif code == '$':
            current_split['amount'] = value

    def _parse_qif_date(self, value: str) -> Optional[date]:
        """
        Parse QIF date format.

        QIF dates can be in various formats:
        - M/D/YY or M/D/YYYY
        - M/D'YY (with apostrophe for years 2000+)
        - D/M/YY (European)
        """
        if not value:
            return None

        # Handle apostrophe year separator
        value = value.replace("'", "/")

        # Try common formats
        formats = [
            '%m/%d/%Y',
            '%m/%d/%y',
            '%d/%m/%Y',
            '%d/%m/%y',
            '%m-%d-%Y',
            '%m-%d-%y',
            '%Y-%m-%d',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        # Try to handle single-digit months/days
        parts = re.split(r'[/\-]', value)
        if len(parts) == 3:
            try:
                month = int(parts[0])
                day = int(parts[1])
                year = int(parts[2])

                # Handle 2-digit years
                if year < 100:
                    year += 2000 if year < 50 else 1900

                return date(year, month, day)
            except (ValueError, TypeError):
                pass

        return None


class QIFImporter(BaseImporter):
    """
    QIF (Quicken Interchange Format) file importer.

    Features:
    - Support for all QIF account types
    - Split transaction handling
    - Multiple date format support
    - Category extraction
    """

    def __init__(self, user=None, bank_account=None,
                 date_format: Optional[str] = None,
                 default_type: Optional[str] = None):
        """
        Initialize the QIF importer.

        Args:
            user: Django user instance
            bank_account: Optional bank account
            date_format: Date format hint (us/eu)
            default_type: Default transaction type if not determinable
        """
        super().__init__(user, bank_account)
        self.parser = QIFParser()
        self.date_format = date_format
        self.default_type = default_type

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file extensions."""
        return ['qif']

    def parse(self, file_obj: Union[BinaryIO, TextIO]) -> ImportResult:
        """
        Parse a QIF file and extract transactions.

        Args:
            file_obj: File object to parse

        Returns:
            ImportResult with parsed transactions
        """
        result = ImportResult(success=True)

        try:
            # Read file content
            content = self._read_file(file_obj)

            # Parse QIF
            parsed = self.parser.parse(content)

            # Log account type
            if parsed.get('account_type'):
                result.add_warning(
                    f"Account type: {parsed['account_type']}"
                )

            transactions = parsed.get('transactions', [])
            result.total_rows = len(transactions)

            if not transactions:
                result.add_warning("No transactions found in QIF file")
                return result

            # Process each transaction
            for i, tx in enumerate(transactions):
                try:
                    # Handle split transactions
                    if tx.get('splits'):
                        split_txs = self._process_splits(tx, i + 1)
                        for split_tx in split_txs:
                            result.add_transaction(split_tx)
                    else:
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

        except ImportError as e:
            result.success = False
            result.add_error(str(e))
        except Exception as e:
            result.success = False
            result.add_error(f"Unexpected error: {e}")
            logger.exception("QIF import failed")

        return result

    def _read_file(self, file_obj: Union[BinaryIO, TextIO]) -> str:
        """Read file content with encoding detection."""
        file_obj.seek(0)
        content = file_obj.read()

        if isinstance(content, bytes):
            # Try common encodings
            for encoding in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue

            # Fallback with replacement
            return content.decode('utf-8', errors='replace')

        return content

    def _convert_transaction(self, tx: Dict[str, Any],
                            line_number: int) -> ParsedTransaction:
        """
        Convert QIF transaction to ParsedTransaction.

        Args:
            tx: QIF transaction dictionary
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

        # Determine type from amount sign
        if amount < 0:
            tx_type = TransactionType.EXPENSE
        else:
            tx_type = TransactionType.INCOME

        # Check for transfer
        category = tx.get('category', '')
        if category.startswith('[') and category.endswith(']'):
            tx_type = TransactionType.TRANSFER
            category = category[1:-1]  # Remove brackets

        # Build description
        payee = tx.get('payee', '')
        memo = tx.get('memo', '')
        description = f"{payee} - {memo}".strip(' -') if memo else payee

        # Build reference
        reference = tx.get('number', '')

        return ParsedTransaction(
            amount=abs(amount),
            transaction_date=tx_date,
            type=tx_type,
            description=description,
            merchant=payee,
            reference=reference,
            category_name=category if category else None,
            raw_data=tx,
        )

    def _process_splits(self, tx: Dict[str, Any],
                       line_number: int) -> List[ParsedTransaction]:
        """
        Process a split transaction into multiple transactions.

        Args:
            tx: QIF transaction with splits
            line_number: Line number for error reporting

        Returns:
            List of ParsedTransaction instances
        """
        transactions = []
        tx_date = tx.get('date')

        if not tx_date:
            raise ValidationError('date', 'Transaction date is missing')

        payee = tx.get('payee', '')

        for split in tx.get('splits', []):
            amount_str = split.get('amount', '0')
            amount = self._parse_amount(amount_str, line_number)

            # Determine type
            if amount < 0:
                tx_type = TransactionType.EXPENSE
            else:
                tx_type = TransactionType.INCOME

            # Category
            category = split.get('category', '')
            if category.startswith('[') and category.endswith(']'):
                tx_type = TransactionType.TRANSFER
                category = category[1:-1]

            # Description
            memo = split.get('memo', '')
            description = f"{payee} - {memo}".strip(' -') if memo else payee

            transactions.append(ParsedTransaction(
                amount=abs(amount),
                transaction_date=tx_date,
                type=tx_type,
                description=description,
                merchant=payee,
                category_name=category if category else None,
                raw_data={'parent': tx, 'split': split},
            ))

        return transactions

    def get_preview(self, file_obj: Union[BinaryIO, TextIO],
                   num_rows: int = 10) -> Dict[str, Any]:
        """
        Preview QIF file without full parsing.

        Args:
            file_obj: File object to preview
            num_rows: Number of transactions to preview

        Returns:
            Dictionary with preview information
        """
        try:
            content = self._read_file(file_obj)
            parsed = self.parser.parse(content)

            transactions = parsed.get('transactions', [])[:num_rows]

            preview_data = []
            for tx in transactions:
                preview_data.append({
                    'date': str(tx.get('date', '')),
                    'amount': tx.get('amount', ''),
                    'payee': tx.get('payee', ''),
                    'memo': tx.get('memo', ''),
                    'category': tx.get('category', ''),
                    'has_splits': bool(tx.get('splits')),
                })

            return {
                'success': True,
                'account_type': parsed.get('account_type'),
                'total_transactions': len(parsed.get('transactions', [])),
                'preview': preview_data,
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
