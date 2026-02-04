"""
Import Service for Finance Desktop Application.

Provides functionality to import financial data from various formats
including CSV, OFX/QFX (bank exports), and other common formats.
"""

import csv
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple, Set
import logging

logger = logging.getLogger(__name__)

# Try to import pandas for advanced CSV handling
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None


class ImportError(Exception):
    """Exception raised for import-related errors."""
    pass


class ValidationError(Exception):
    """Exception raised for data validation errors."""
    pass


class ImportRecord:
    """Represents a single imported transaction record."""

    def __init__(
        self,
        date: date,
        amount: Decimal,
        description: str,
        transaction_type: str = 'expense',
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        account: Optional[str] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.date = date
        self.amount = amount
        self.description = description
        self.transaction_type = transaction_type
        self.category = category
        self.merchant = merchant
        self.account = account
        self.reference = reference
        self.notes = notes
        self.raw_data = raw_data or {}
        self._hash: Optional[str] = None

    @property
    def unique_hash(self) -> str:
        """Generate a unique hash for duplicate detection."""
        if self._hash is None:
            hash_str = f"{self.date.isoformat()}|{self.amount}|{self.description}"
            self._hash = hashlib.md5(hash_str.encode()).hexdigest()
        return self._hash

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'date': self.date.isoformat(),
            'amount': float(self.amount),
            'description': self.description,
            'type': self.transaction_type,
            'category': self.category,
            'merchant': self.merchant,
            'account': self.account,
            'reference': self.reference,
            'notes': self.notes,
            'unique_hash': self.unique_hash
        }

    def __repr__(self) -> str:
        return f"<ImportRecord date={self.date} amount={self.amount} desc='{self.description[:30]}...'>"


class ImportResult:
    """Result of an import operation."""

    def __init__(self):
        self.records: List[ImportRecord] = []
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.duplicates: List[ImportRecord] = []
        self.source_file: Optional[str] = None
        self.source_format: Optional[str] = None
        self.import_date: datetime = datetime.now()

    @property
    def total_count(self) -> int:
        """Total number of records processed."""
        return len(self.records) + len(self.errors) + len(self.duplicates)

    @property
    def success_count(self) -> int:
        """Number of successfully imported records."""
        return len(self.records)

    @property
    def error_count(self) -> int:
        """Number of records with errors."""
        return len(self.errors)

    @property
    def duplicate_count(self) -> int:
        """Number of duplicate records detected."""
        return len(self.duplicates)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'source_file': self.source_file,
            'source_format': self.source_format,
            'import_date': self.import_date.isoformat(),
            'total_count': self.total_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'duplicate_count': self.duplicate_count,
            'records': [r.to_dict() for r in self.records],
            'errors': self.errors,
            'warnings': self.warnings
        }


class ImportService:
    """
    Service for importing financial data from various file formats.

    Supports CSV, OFX, QFX, and other common bank export formats
    with automatic format detection and data validation.
    """

    # Supported formats
    FORMAT_CSV = 'csv'
    FORMAT_OFX = 'ofx'
    FORMAT_QFX = 'qfx'
    FORMAT_QIF = 'qif'

    # Common CSV column mappings
    CSV_COLUMN_MAPPINGS = {
        'date': ['date', 'transaction date', 'post date', 'posted date', 'trans date',
                 'fecha', 'datum', 'data'],
        'amount': ['amount', 'transaction amount', 'sum', 'value', 'debit/credit',
                   'importe', 'betrag', 'montant'],
        'description': ['description', 'memo', 'narrative', 'details', 'transaction description',
                       'merchant', 'payee', 'descripcion', 'beschreibung'],
        'category': ['category', 'type', 'transaction type', 'categoria', 'kategorie'],
        'reference': ['reference', 'ref', 'transaction id', 'id', 'check number', 'referencia'],
        'balance': ['balance', 'running balance', 'saldo']
    }

    # Common date formats to try
    DATE_FORMATS = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%m-%d-%Y',
        '%d-%m-%Y',
        '%d.%m.%Y',
        '%Y.%m.%d',
        '%b %d, %Y',
        '%d %b %Y',
        '%B %d, %Y',
        '%Y%m%d',
    ]

    def __init__(self):
        """Initialize the import service."""
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._existing_hashes: Set[str] = set()

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """
        Set a callback function for progress updates.

        Args:
            callback: Function that receives (current, total, message) parameters
        """
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str = "") -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def set_existing_hashes(self, hashes: Set[str]) -> None:
        """
        Set existing transaction hashes for duplicate detection.

        Args:
            hashes: Set of existing transaction hashes
        """
        self._existing_hashes = hashes

    # =========================================================================
    # Format Detection
    # =========================================================================

    def detect_format(self, file_path: Path) -> str:
        """
        Detect the format of an import file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Detected format identifier

        Raises:
            ImportError: If format cannot be detected
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ImportError(f"File not found: {file_path}")

        # Check by extension first
        extension = file_path.suffix.lower()

        if extension == '.csv':
            return self.FORMAT_CSV
        elif extension == '.ofx':
            return self.FORMAT_OFX
        elif extension == '.qfx':
            return self.FORMAT_QFX
        elif extension == '.qif':
            return self.FORMAT_QIF

        # Try to detect by content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(4096)  # Read first 4KB

            content_lower = content.lower()

            # Check for OFX/QFX markers
            if '<ofx>' in content_lower or 'ofxheader' in content_lower:
                return self.FORMAT_OFX

            # Check for QIF markers
            if content.startswith('!') and ('Type:' in content or 'Account' in content):
                return self.FORMAT_QIF

            # Default to CSV if it looks like delimited data
            if ',' in content or '\t' in content or ';' in content:
                return self.FORMAT_CSV

        except Exception as e:
            logger.warning(f"Error detecting format: {e}")

        raise ImportError(f"Unable to detect format for file: {file_path}")

    # =========================================================================
    # CSV Import
    # =========================================================================

    def import_csv(
        self,
        file_path: Path,
        column_mapping: Optional[Dict[str, str]] = None,
        date_format: Optional[str] = None,
        encoding: str = 'utf-8',
        delimiter: Optional[str] = None,
        skip_rows: int = 0,
        has_header: bool = True
    ) -> ImportResult:
        """
        Import transactions from a CSV file.

        Args:
            file_path: Path to the CSV file
            column_mapping: Optional custom column mapping
            date_format: Optional date format string
            encoding: File encoding
            delimiter: CSV delimiter (auto-detected if None)
            skip_rows: Number of rows to skip at the beginning
            has_header: Whether the file has a header row

        Returns:
            ImportResult with imported records

        Raises:
            ImportError: If import fails
        """
        file_path = Path(file_path)
        result = ImportResult()
        result.source_file = str(file_path)
        result.source_format = self.FORMAT_CSV

        try:
            self._report_progress(0, 100, "Reading CSV file...")

            # Read file content
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()

            # Auto-detect delimiter if not specified
            if delimiter is None:
                delimiter = self._detect_csv_delimiter(content)

            # Parse CSV
            lines = content.strip().split('\n')

            if skip_rows > 0:
                lines = lines[skip_rows:]

            if not lines:
                raise ImportError("CSV file is empty")

            # Parse with csv module
            reader = csv.DictReader(
                lines if has_header else [''] + lines,
                delimiter=delimiter
            )

            # Get headers and detect column mappings
            if has_header:
                headers = reader.fieldnames or []
                detected_mapping = self._detect_csv_columns(headers)
            else:
                # Use column indices as names
                first_row = lines[0].split(delimiter)
                headers = [f'col{i}' for i in range(len(first_row))]
                detected_mapping = {}

            # Apply custom mapping over detected
            final_mapping = {**detected_mapping, **(column_mapping or {})}

            if 'date' not in final_mapping or 'amount' not in final_mapping:
                result.warnings.append(
                    "Could not auto-detect date and amount columns. "
                    "Please provide column mapping."
                )
                raise ImportError("Missing required column mappings for date and amount")

            self._report_progress(10, 100, "Processing records...")

            # Process rows
            rows = list(reader)
            total_rows = len(rows)

            for i, row in enumerate(rows):
                try:
                    record = self._parse_csv_row(row, final_mapping, date_format)

                    # Check for duplicates
                    if record.unique_hash in self._existing_hashes:
                        result.duplicates.append(record)
                    else:
                        result.records.append(record)
                        self._existing_hashes.add(record.unique_hash)

                except Exception as e:
                    result.errors.append({
                        'row': i + 2,  # +2 for header and 1-based index
                        'error': str(e),
                        'data': dict(row)
                    })

                if (i + 1) % 100 == 0 or i == total_rows - 1:
                    progress = 10 + int((i + 1) / total_rows * 90)
                    self._report_progress(progress, 100, f"Processed {i + 1} of {total_rows} rows")

            self._report_progress(100, 100, "CSV import complete!")

            logger.info(f"CSV import: {result.success_count} records, "
                       f"{result.error_count} errors, {result.duplicate_count} duplicates")

            return result

        except ImportError:
            raise
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            raise ImportError(f"Failed to import CSV: {str(e)}") from e

    def _detect_csv_delimiter(self, content: str) -> str:
        """Detect the CSV delimiter from content."""
        # Count occurrences of common delimiters in first few lines
        first_lines = '\n'.join(content.split('\n')[:5])
        delimiters = {',': 0, ';': 0, '\t': 0, '|': 0}

        for d in delimiters:
            delimiters[d] = first_lines.count(d)

        # Return the most common delimiter
        return max(delimiters, key=delimiters.get)

    def _detect_csv_columns(self, headers: List[str]) -> Dict[str, str]:
        """Detect column mappings from CSV headers."""
        mapping = {}
        normalized_headers = {h.lower().strip(): h for h in headers}

        for field, possible_names in self.CSV_COLUMN_MAPPINGS.items():
            for name in possible_names:
                if name in normalized_headers:
                    mapping[field] = normalized_headers[name]
                    break

        return mapping

    def _parse_csv_row(
        self,
        row: Dict[str, str],
        mapping: Dict[str, str],
        date_format: Optional[str] = None
    ) -> ImportRecord:
        """Parse a CSV row into an ImportRecord."""
        # Parse date
        date_col = mapping.get('date', '')
        date_str = row.get(date_col, '').strip()
        parsed_date = self._parse_date(date_str, date_format)

        if parsed_date is None:
            raise ValueError(f"Invalid date: {date_str}")

        # Parse amount
        amount_col = mapping.get('amount', '')
        amount_str = row.get(amount_col, '').strip()
        amount = self._parse_amount(amount_str)

        # Parse description
        desc_col = mapping.get('description', '')
        description = row.get(desc_col, '').strip() or 'No description'

        # Determine transaction type
        transaction_type = 'income' if amount > 0 else 'expense'

        # Parse optional fields
        category = row.get(mapping.get('category', ''), '').strip() or None
        reference = row.get(mapping.get('reference', ''), '').strip() or None

        return ImportRecord(
            date=parsed_date,
            amount=abs(amount),
            description=description,
            transaction_type=transaction_type,
            category=category,
            reference=reference,
            raw_data=dict(row)
        )

    # =========================================================================
    # OFX/QFX Import
    # =========================================================================

    def import_ofx(self, file_path: Path) -> ImportResult:
        """
        Import transactions from an OFX or QFX file.

        Args:
            file_path: Path to the OFX/QFX file

        Returns:
            ImportResult with imported records

        Raises:
            ImportError: If import fails
        """
        file_path = Path(file_path)
        result = ImportResult()
        result.source_file = str(file_path)
        result.source_format = self.FORMAT_OFX

        try:
            self._report_progress(0, 100, "Reading OFX file...")

            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Parse OFX content
            transactions = self._parse_ofx_content(content)
            total = len(transactions)

            self._report_progress(20, 100, f"Found {total} transactions...")

            # Convert to ImportRecords
            for i, txn in enumerate(transactions):
                try:
                    record = self._ofx_to_record(txn)

                    if record.unique_hash in self._existing_hashes:
                        result.duplicates.append(record)
                    else:
                        result.records.append(record)
                        self._existing_hashes.add(record.unique_hash)

                except Exception as e:
                    result.errors.append({
                        'index': i,
                        'error': str(e),
                        'data': txn
                    })

                if (i + 1) % 50 == 0 or i == total - 1:
                    progress = 20 + int((i + 1) / total * 80)
                    self._report_progress(progress, 100, f"Processed {i + 1} of {total} transactions")

            self._report_progress(100, 100, "OFX import complete!")

            logger.info(f"OFX import: {result.success_count} records, "
                       f"{result.error_count} errors, {result.duplicate_count} duplicates")

            return result

        except ImportError:
            raise
        except Exception as e:
            logger.error(f"OFX import failed: {e}")
            raise ImportError(f"Failed to import OFX: {str(e)}") from e

    def _parse_ofx_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse OFX content and extract transactions."""
        transactions = []

        # OFX can be SGML-like or XML
        # Convert SGML to XML-like format for parsing
        content = self._normalize_ofx(content)

        # Extract transaction blocks
        # Pattern for STMTTRN blocks
        txn_pattern = r'<STMTTRN>(.*?)</STMTTRN>'
        matches = re.findall(txn_pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            txn = {}

            # Extract fields
            field_patterns = {
                'TRNTYPE': r'<TRNTYPE>([^<\n]+)',
                'DTPOSTED': r'<DTPOSTED>([^<\n]+)',
                'TRNAMT': r'<TRNAMT>([^<\n]+)',
                'FITID': r'<FITID>([^<\n]+)',
                'NAME': r'<NAME>([^<\n]+)',
                'MEMO': r'<MEMO>([^<\n]+)',
                'CHECKNUM': r'<CHECKNUM>([^<\n]+)',
            }

            for field, pattern in field_patterns.items():
                match_field = re.search(pattern, match, re.IGNORECASE)
                if match_field:
                    txn[field] = match_field.group(1).strip()

            if txn:
                transactions.append(txn)

        return transactions

    def _normalize_ofx(self, content: str) -> str:
        """Normalize OFX content for parsing."""
        # Remove SGML header if present
        if 'OFXHEADER' in content.upper():
            # Find the start of actual OFX data
            ofx_start = content.upper().find('<OFX>')
            if ofx_start != -1:
                content = content[ofx_start:]

        # Add closing tags to SGML-style elements
        # OFX SGML doesn't require closing tags
        sgml_tags = ['TRNTYPE', 'DTPOSTED', 'TRNAMT', 'FITID', 'NAME', 'MEMO',
                    'CHECKNUM', 'BANKID', 'ACCTID', 'BALAMT', 'DTASOF']

        for tag in sgml_tags:
            # Add closing tag if not present
            pattern = f'<{tag}>([^<\n]+)(?!</{tag}>)'
            content = re.sub(
                pattern,
                f'<{tag}>\\1</{tag}>',
                content,
                flags=re.IGNORECASE
            )

        return content

    def _ofx_to_record(self, txn: Dict[str, Any]) -> ImportRecord:
        """Convert OFX transaction to ImportRecord."""
        # Parse date (OFX format: YYYYMMDD or YYYYMMDDHHMMSS)
        date_str = txn.get('DTPOSTED', '')
        if len(date_str) >= 8:
            parsed_date = datetime.strptime(date_str[:8], '%Y%m%d').date()
        else:
            raise ValueError(f"Invalid OFX date: {date_str}")

        # Parse amount
        amount_str = txn.get('TRNAMT', '0')
        amount = self._parse_amount(amount_str)

        # Get description (prefer NAME, fallback to MEMO)
        description = txn.get('NAME', '') or txn.get('MEMO', '') or 'OFX Transaction'

        # Determine type from TRNTYPE or amount
        trntype = txn.get('TRNTYPE', '').upper()
        if trntype in ('CREDIT', 'DEP', 'INT', 'DIV'):
            transaction_type = 'income'
        elif trntype in ('DEBIT', 'CHECK', 'PAYMENT', 'FEE', 'SRVCHG'):
            transaction_type = 'expense'
        else:
            transaction_type = 'income' if amount > 0 else 'expense'

        return ImportRecord(
            date=parsed_date,
            amount=abs(amount),
            description=description,
            transaction_type=transaction_type,
            reference=txn.get('FITID') or txn.get('CHECKNUM'),
            notes=txn.get('MEMO') if txn.get('NAME') else None,
            raw_data=txn
        )

    # =========================================================================
    # QIF Import
    # =========================================================================

    def import_qif(self, file_path: Path) -> ImportResult:
        """
        Import transactions from a QIF file.

        Args:
            file_path: Path to the QIF file

        Returns:
            ImportResult with imported records

        Raises:
            ImportError: If import fails
        """
        file_path = Path(file_path)
        result = ImportResult()
        result.source_file = str(file_path)
        result.source_format = self.FORMAT_QIF

        try:
            self._report_progress(0, 100, "Reading QIF file...")

            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Parse QIF transactions
            transactions = self._parse_qif_content(content)
            total = len(transactions)

            self._report_progress(20, 100, f"Found {total} transactions...")

            for i, txn in enumerate(transactions):
                try:
                    record = self._qif_to_record(txn)

                    if record.unique_hash in self._existing_hashes:
                        result.duplicates.append(record)
                    else:
                        result.records.append(record)
                        self._existing_hashes.add(record.unique_hash)

                except Exception as e:
                    result.errors.append({
                        'index': i,
                        'error': str(e),
                        'data': txn
                    })

                if (i + 1) % 50 == 0 or i == total - 1:
                    progress = 20 + int((i + 1) / total * 80)
                    self._report_progress(progress, 100, f"Processed {i + 1} of {total} transactions")

            self._report_progress(100, 100, "QIF import complete!")

            return result

        except Exception as e:
            raise ImportError(f"Failed to import QIF: {str(e)}") from e

    def _parse_qif_content(self, content: str) -> List[Dict[str, str]]:
        """Parse QIF content and extract transactions."""
        transactions = []
        current_txn: Dict[str, str] = {}

        for line in content.split('\n'):
            line = line.strip()

            if not line:
                continue

            if line.startswith('^'):
                # End of transaction
                if current_txn:
                    transactions.append(current_txn)
                    current_txn = {}
            elif line.startswith('!'):
                # Header/type declaration
                continue
            elif line[0] in 'DTPMNCLNS':
                # QIF field codes
                code = line[0]
                value = line[1:].strip()

                if code == 'D':
                    current_txn['date'] = value
                elif code == 'T':
                    current_txn['amount'] = value
                elif code == 'P':
                    current_txn['payee'] = value
                elif code == 'M':
                    current_txn['memo'] = value
                elif code == 'N':
                    current_txn['number'] = value
                elif code == 'C':
                    current_txn['cleared'] = value
                elif code == 'L':
                    current_txn['category'] = value

        # Don't forget last transaction
        if current_txn:
            transactions.append(current_txn)

        return transactions

    def _qif_to_record(self, txn: Dict[str, str]) -> ImportRecord:
        """Convert QIF transaction to ImportRecord."""
        # Parse date (QIF format varies: M/D/Y, M/D'Y, etc.)
        date_str = txn.get('date', '')
        # Replace apostrophe with /
        date_str = date_str.replace("'", "/")
        parsed_date = self._parse_date(date_str)

        if parsed_date is None:
            raise ValueError(f"Invalid QIF date: {date_str}")

        # Parse amount
        amount = self._parse_amount(txn.get('amount', '0'))

        # Get description
        description = txn.get('payee', '') or txn.get('memo', '') or 'QIF Transaction'

        # Determine type
        transaction_type = 'income' if amount > 0 else 'expense'

        return ImportRecord(
            date=parsed_date,
            amount=abs(amount),
            description=description,
            transaction_type=transaction_type,
            category=txn.get('category'),
            reference=txn.get('number'),
            notes=txn.get('memo') if txn.get('payee') else None,
            raw_data=txn
        )

    # =========================================================================
    # Data Validation
    # =========================================================================

    def validate_data(
        self,
        records: List[ImportRecord],
        rules: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ImportRecord], List[Dict[str, Any]]]:
        """
        Validate imported records against rules.

        Args:
            records: List of ImportRecord objects to validate
            rules: Optional validation rules:
                - min_date: Minimum allowed date
                - max_date: Maximum allowed date
                - min_amount: Minimum transaction amount
                - max_amount: Maximum transaction amount
                - required_fields: List of required fields

        Returns:
            Tuple of (valid_records, validation_errors)
        """
        rules = rules or {}
        valid_records = []
        errors = []

        min_date = rules.get('min_date')
        max_date = rules.get('max_date', date.today())
        min_amount = rules.get('min_amount', Decimal('0.01'))
        max_amount = rules.get('max_amount', Decimal('10000000'))
        required_fields = rules.get('required_fields', ['date', 'amount', 'description'])

        for i, record in enumerate(records):
            record_errors = []

            # Check required fields
            for field in required_fields:
                value = getattr(record, field, None)
                if value is None or (isinstance(value, str) and not value.strip()):
                    record_errors.append(f"Missing required field: {field}")

            # Check date range
            if min_date and record.date < min_date:
                record_errors.append(f"Date {record.date} is before minimum {min_date}")

            if max_date and record.date > max_date:
                record_errors.append(f"Date {record.date} is after maximum {max_date}")

            # Check amount range
            if record.amount < min_amount:
                record_errors.append(f"Amount {record.amount} is below minimum {min_amount}")

            if record.amount > max_amount:
                record_errors.append(f"Amount {record.amount} exceeds maximum {max_amount}")

            # Check for suspicious data
            if len(record.description) > 500:
                record_errors.append("Description exceeds maximum length")

            if record_errors:
                errors.append({
                    'index': i,
                    'record': record.to_dict(),
                    'errors': record_errors
                })
            else:
                valid_records.append(record)

        return valid_records, errors

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _parse_date(
        self,
        date_str: str,
        preferred_format: Optional[str] = None
    ) -> Optional[date]:
        """Parse a date string trying multiple formats."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Try preferred format first
        if preferred_format:
            try:
                return datetime.strptime(date_str, preferred_format).date()
            except ValueError:
                pass

        # Try all known formats
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Try pandas parser if available (handles more formats)
        if PANDAS_AVAILABLE and pd is not None:
            try:
                return pd.to_datetime(date_str).date()
            except Exception:
                pass

        return None

    def _parse_amount(self, amount_str: str) -> Decimal:
        """Parse an amount string to Decimal."""
        if not amount_str:
            return Decimal('0')

        # Clean the string
        amount_str = amount_str.strip()

        # Remove currency symbols and thousands separators
        amount_str = re.sub(r'[€$£¥₹,\s]', '', amount_str)

        # Handle parentheses as negative (accounting format)
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]

        # Handle trailing minus sign
        if amount_str.endswith('-'):
            amount_str = '-' + amount_str[:-1]

        # Replace comma as decimal separator (European format)
        # Only if there's no period or period comes before comma
        if ',' in amount_str:
            if '.' not in amount_str:
                amount_str = amount_str.replace(',', '.')
            elif amount_str.rfind('.') < amount_str.rfind(','):
                # Period is thousands separator, comma is decimal
                amount_str = amount_str.replace('.', '').replace(',', '.')

        try:
            return Decimal(amount_str)
        except InvalidOperation:
            raise ValueError(f"Invalid amount: {amount_str}")

    def get_supported_formats(self) -> List[Dict[str, str]]:
        """Get list of supported import formats."""
        return [
            {
                'id': self.FORMAT_CSV,
                'name': 'CSV (Comma-Separated Values)',
                'extensions': ['.csv'],
                'description': 'Standard CSV format from most banks and spreadsheets'
            },
            {
                'id': self.FORMAT_OFX,
                'name': 'OFX (Open Financial Exchange)',
                'extensions': ['.ofx'],
                'description': 'Standard bank export format'
            },
            {
                'id': self.FORMAT_QFX,
                'name': 'QFX (Quicken Financial Exchange)',
                'extensions': ['.qfx'],
                'description': 'Quicken-compatible bank export format'
            },
            {
                'id': self.FORMAT_QIF,
                'name': 'QIF (Quicken Interchange Format)',
                'extensions': ['.qif'],
                'description': 'Legacy Quicken format'
            }
        ]

    def preview_import(
        self,
        file_path: Path,
        max_records: int = 10
    ) -> Dict[str, Any]:
        """
        Preview an import without actually importing.

        Args:
            file_path: Path to the file
            max_records: Maximum number of records to preview

        Returns:
            Preview information including detected format and sample records
        """
        file_path = Path(file_path)

        # Detect format
        detected_format = self.detect_format(file_path)

        # Create temporary service without existing hashes
        temp_service = ImportService()

        # Import with limit
        if detected_format == self.FORMAT_CSV:
            result = temp_service.import_csv(file_path)
        elif detected_format in (self.FORMAT_OFX, self.FORMAT_QFX):
            result = temp_service.import_ofx(file_path)
        elif detected_format == self.FORMAT_QIF:
            result = temp_service.import_qif(file_path)
        else:
            raise ImportError(f"Unsupported format: {detected_format}")

        # Return preview
        return {
            'format': detected_format,
            'total_records': result.total_count,
            'sample_records': [r.to_dict() for r in result.records[:max_records]],
            'errors': result.errors[:5],
            'warnings': result.warnings
        }
