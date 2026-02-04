"""
Base Importer Module.

Provides abstract base class and common utilities for all importers.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, BinaryIO, Callable, Dict, List, Optional, TextIO, Union
from enum import Enum

logger = logging.getLogger(__name__)


class ImportError(Exception):
    """Exception raised when import fails."""

    def __init__(self, message: str, line_number: Optional[int] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.line_number = line_number
        self.details = details or {}
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format error message with line number if available."""
        if self.line_number:
            return f"Line {self.line_number}: {self.message}"
        return self.message


class ValidationError(Exception):
    """Exception raised when data validation fails."""

    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


class TransactionType(Enum):
    """Transaction type enumeration."""
    INCOME = 'income'
    EXPENSE = 'expense'
    TRANSFER = 'transfer'


@dataclass
class ParsedTransaction:
    """
    Represents a parsed transaction from import file.

    This is an intermediate representation before creating
    the actual Transaction model instance.
    """
    amount: Decimal
    transaction_date: date
    type: TransactionType
    description: str = ''
    merchant: str = ''
    reference: str = ''
    category_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for model creation."""
        return {
            'amount': self.amount,
            'transaction_date': self.transaction_date,
            'type': self.type.value,
            'description': self.description,
            'merchant': self.merchant,
            'reference': self.reference,
            'tags': self.tags,
        }


@dataclass
class ImportResult:
    """
    Result of an import operation.

    Contains statistics and details about the import.
    """
    success: bool
    total_rows: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    transactions: List[ParsedTransaction] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str, line_number: Optional[int] = None,
                  details: Optional[Dict[str, Any]] = None):
        """Add an error to the result."""
        self.error_count += 1
        self.errors.append({
            'message': message,
            'line_number': line_number,
            'details': details or {},
        })

    def add_warning(self, message: str):
        """Add a warning to the result."""
        self.warnings.append(message)

    def add_transaction(self, transaction: ParsedTransaction):
        """Add a successfully parsed transaction."""
        self.transactions.append(transaction)
        self.imported_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses."""
        return {
            'success': self.success,
            'total_rows': self.total_rows,
            'imported_count': self.imported_count,
            'skipped_count': self.skipped_count,
            'error_count': self.error_count,
            'errors': self.errors,
            'warnings': self.warnings,
        }


class BaseImporter(ABC):
    """
    Abstract base class for all transaction importers.

    Provides common functionality for parsing, validating,
    and importing financial transaction data.
    """

    # Supported encodings for auto-detection
    SUPPORTED_ENCODINGS = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

    # Date formats to try during parsing
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%m-%d-%Y',
        '%d.%m.%Y',
        '%Y.%m.%d',
        '%b %d, %Y',
        '%B %d, %Y',
        '%d %b %Y',
        '%d %B %Y',
    ]

    def __init__(self, user=None, bank_account=None):
        """
        Initialize the importer.

        Args:
            user: Django user instance for associating transactions
            bank_account: Optional bank account to link transactions to
        """
        self.user = user
        self.bank_account = bank_account
        self.progress_callback: Optional[Callable[[int, int], None]] = None
        self._current_line = 0
        self._total_lines = 0

    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """
        Set a callback function for progress tracking.

        Args:
            callback: Function that receives (current, total) progress
        """
        self.progress_callback = callback

    def _report_progress(self, current: int, total: int):
        """Report progress if callback is set."""
        self._current_line = current
        self._total_lines = total
        if self.progress_callback:
            self.progress_callback(current, total)

    @abstractmethod
    def parse(self, file_obj: Union[BinaryIO, TextIO]) -> ImportResult:
        """
        Parse the file and extract transactions.

        Args:
            file_obj: File object to parse

        Returns:
            ImportResult with parsed transactions and statistics
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file extensions.

        Returns:
            List of supported extensions (without dot)
        """
        pass

    def validate_transaction(self, data: Dict[str, Any],
                            line_number: Optional[int] = None) -> ParsedTransaction:
        """
        Validate and convert raw data to ParsedTransaction.

        Args:
            data: Raw transaction data dictionary
            line_number: Line number for error reporting

        Returns:
            Validated ParsedTransaction instance

        Raises:
            ValidationError: If validation fails
        """
        # Validate and parse amount
        amount = self._parse_amount(data.get('amount'), line_number)

        # Validate and parse date
        transaction_date = self._parse_date(data.get('date'), line_number)

        # Determine transaction type
        tx_type = self._determine_type(amount, data.get('type'))

        # Clean description
        description = self._clean_string(data.get('description', ''))
        merchant = self._clean_string(data.get('merchant', ''))
        reference = self._clean_string(data.get('reference', ''))

        # Parse tags
        tags = self._parse_tags(data.get('tags', []))

        return ParsedTransaction(
            amount=abs(amount),
            transaction_date=transaction_date,
            type=tx_type,
            description=description,
            merchant=merchant,
            reference=reference,
            category_name=data.get('category'),
            tags=tags,
            raw_data=data,
        )

    def _parse_amount(self, value: Any, line_number: Optional[int] = None) -> Decimal:
        """
        Parse amount from various formats.

        Handles:
        - Numeric values
        - String with currency symbols
        - Different decimal separators
        - Parentheses for negative values
        """
        if value is None:
            raise ValidationError('amount', 'Amount is required')

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        # Clean string value
        str_value = str(value).strip()

        # Check for empty
        if not str_value:
            raise ValidationError('amount', 'Amount cannot be empty')

        # Check for parentheses notation (negative)
        is_negative = False
        if str_value.startswith('(') and str_value.endswith(')'):
            is_negative = True
            str_value = str_value[1:-1]

        # Check for minus sign
        if str_value.startswith('-'):
            is_negative = True
            str_value = str_value[1:]

        # Remove currency symbols and whitespace
        currency_symbols = ['$', '€', '£', '¥', '₹', 'USD', 'EUR', 'GBP', 'CAD', 'AUD']
        for symbol in currency_symbols:
            str_value = str_value.replace(symbol, '')

        str_value = str_value.strip()

        # Handle thousand separators and decimal points
        # Detect format: 1,234.56 vs 1.234,56
        if ',' in str_value and '.' in str_value:
            # Both present - determine which is decimal
            if str_value.rfind(',') > str_value.rfind('.'):
                # European format: 1.234,56
                str_value = str_value.replace('.', '').replace(',', '.')
            else:
                # US format: 1,234.56
                str_value = str_value.replace(',', '')
        elif ',' in str_value:
            # Only comma - could be decimal or thousand separator
            parts = str_value.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Likely decimal: 123,45
                str_value = str_value.replace(',', '.')
            else:
                # Likely thousand separator: 1,234
                str_value = str_value.replace(',', '')

        try:
            amount = Decimal(str_value)
            if is_negative:
                amount = -amount
            return amount
        except InvalidOperation:
            raise ValidationError(
                'amount',
                f'Invalid amount format: {value}',
                value
            )

    def _parse_date(self, value: Any, line_number: Optional[int] = None) -> date:
        """
        Parse date from various formats.

        Tries multiple date formats to find a match.
        """
        if value is None:
            raise ValidationError('date', 'Date is required')

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        str_value = str(value).strip()

        if not str_value:
            raise ValidationError('date', 'Date cannot be empty')

        # Try each format
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(str_value, fmt).date()
            except ValueError:
                continue

        # Try ISO format with time
        try:
            return datetime.fromisoformat(str_value.replace('Z', '+00:00')).date()
        except ValueError:
            pass

        raise ValidationError(
            'date',
            f'Unrecognized date format: {value}. '
            f'Supported formats include: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY',
            value
        )

    def _determine_type(self, amount: Decimal,
                       type_hint: Optional[str] = None) -> TransactionType:
        """
        Determine transaction type from amount sign or hint.

        Args:
            amount: Transaction amount (can be negative)
            type_hint: Optional type string from data

        Returns:
            TransactionType enum value
        """
        if type_hint:
            type_lower = type_hint.lower().strip()
            type_mapping = {
                'income': TransactionType.INCOME,
                'revenue': TransactionType.INCOME,
                'credit': TransactionType.INCOME,
                'deposit': TransactionType.INCOME,
                'expense': TransactionType.EXPENSE,
                'debit': TransactionType.EXPENSE,
                'withdrawal': TransactionType.EXPENSE,
                'payment': TransactionType.EXPENSE,
                'transfer': TransactionType.TRANSFER,
                'xfer': TransactionType.TRANSFER,
            }
            if type_lower in type_mapping:
                return type_mapping[type_lower]

        # Determine from amount sign
        if amount >= 0:
            return TransactionType.INCOME
        return TransactionType.EXPENSE

    def _clean_string(self, value: Any) -> str:
        """Clean and normalize string value."""
        if value is None:
            return ''
        return ' '.join(str(value).split()).strip()

    def _parse_tags(self, value: Any) -> List[str]:
        """Parse tags from various formats."""
        if not value:
            return []

        if isinstance(value, list):
            return [self._clean_string(t) for t in value if t]

        if isinstance(value, str):
            # Split by common delimiters
            for delimiter in [',', ';', '|']:
                if delimiter in value:
                    return [self._clean_string(t) for t in value.split(delimiter) if t.strip()]
            return [self._clean_string(value)] if value.strip() else []

        return []

    def detect_encoding(self, file_obj: BinaryIO) -> str:
        """
        Detect file encoding by trying different encodings.

        Args:
            file_obj: Binary file object

        Returns:
            Detected encoding name
        """
        # Read sample for detection
        position = file_obj.tell()
        sample = file_obj.read(8192)
        file_obj.seek(position)

        # Check for BOM
        if sample.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        if sample.startswith(b'\xff\xfe') or sample.startswith(b'\xfe\xff'):
            return 'utf-16'

        # Try encodings in order
        for encoding in self.SUPPORTED_ENCODINGS:
            try:
                sample.decode(encoding)
                return encoding
            except (UnicodeDecodeError, LookupError):
                continue

        # Default to latin-1 (accepts any byte sequence)
        return 'latin-1'

    def import_to_database(self, result: ImportResult) -> Dict[str, Any]:
        """
        Import parsed transactions to the database.

        Args:
            result: ImportResult containing parsed transactions

        Returns:
            Dictionary with import statistics
        """
        from apps.transactions.models import Transaction, TransactionCategory

        if not self.user:
            raise ImportError("User is required for database import")

        created_count = 0
        duplicate_count = 0
        error_count = 0

        # Cache categories for performance
        category_cache = {}

        for i, parsed_tx in enumerate(result.transactions):
            try:
                # Look up or create category
                category = None
                if parsed_tx.category_name:
                    if parsed_tx.category_name not in category_cache:
                        category_cache[parsed_tx.category_name] = (
                            TransactionCategory.objects.filter(
                                user=self.user,
                                name__iexact=parsed_tx.category_name
                            ).first()
                        )
                    category = category_cache[parsed_tx.category_name]

                # Check for duplicates
                existing = Transaction.objects.filter(
                    user=self.user,
                    amount=parsed_tx.amount,
                    transaction_date=parsed_tx.transaction_date,
                    description=parsed_tx.description,
                ).exists()

                if existing:
                    duplicate_count += 1
                    continue

                # Create transaction
                Transaction.objects.create(
                    user=self.user,
                    bank_account=self.bank_account,
                    category=category,
                    amount=parsed_tx.amount,
                    type=parsed_tx.type.value,
                    description=parsed_tx.description,
                    merchant=parsed_tx.merchant,
                    reference=parsed_tx.reference,
                    transaction_date=parsed_tx.transaction_date,
                    is_manual=False,
                    tags=parsed_tx.tags,
                )
                created_count += 1

                # Report progress
                self._report_progress(i + 1, len(result.transactions))

            except Exception as e:
                error_count += 1
                logger.error(f"Error importing transaction: {e}")

        return {
            'created': created_count,
            'duplicates': duplicate_count,
            'errors': error_count,
        }
