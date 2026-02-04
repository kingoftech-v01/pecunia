"""
CSV Importer Module.

Provides CSV import functionality with auto-detection
of delimiters, encodings, and column mappings.
"""
import csv
import io
import logging
from collections import Counter
from typing import Any, BinaryIO, Dict, List, Optional, TextIO, Union

from .base import (
    BaseImporter,
    ImportResult,
    ImportError,
    ValidationError,
    ParsedTransaction,
)

logger = logging.getLogger(__name__)


class ColumnMapper:
    """
    Handles automatic and manual column mapping for CSV imports.

    Maps CSV headers to transaction fields using pattern matching
    and configurable aliases.
    """

    # Default column name patterns
    DEFAULT_MAPPINGS = {
        'date': [
            'date', 'transaction_date', 'trans_date', 'posted_date',
            'posting_date', 'value_date', 'trade_date', 'settlement_date',
            'datum', 'fecha', 'data',
        ],
        'amount': [
            'amount', 'value', 'sum', 'total', 'debit/credit',
            'montant', 'betrag', 'importe', 'valor',
        ],
        'description': [
            'description', 'desc', 'memo', 'narrative', 'details',
            'transaction_description', 'trans_desc', 'particulars',
            'reference', 'beschreibung', 'descripcion',
        ],
        'type': [
            'type', 'transaction_type', 'trans_type', 'credit/debit',
            'dr/cr', 'dc', 'direction',
        ],
        'category': [
            'category', 'cat', 'classification', 'group', 'type',
            'kategorie', 'categoria',
        ],
        'merchant': [
            'merchant', 'payee', 'vendor', 'beneficiary', 'recipient',
            'counterparty', 'name', 'from/to',
        ],
        'reference': [
            'reference', 'ref', 'transaction_id', 'trans_id', 'id',
            'check_number', 'cheque_no', 'confirmation',
        ],
        'debit': [
            'debit', 'withdrawal', 'out', 'expense', 'payment',
            'ausgabe', 'debito',
        ],
        'credit': [
            'credit', 'deposit', 'in', 'income', 'receipt',
            'einnahme', 'credito',
        ],
        'balance': [
            'balance', 'running_balance', 'available', 'saldo',
        ],
        'currency': [
            'currency', 'curr', 'ccy', 'devise', 'wahrung',
        ],
        'tags': [
            'tags', 'labels', 'keywords', 'etiquetas',
        ],
    }

    def __init__(self, custom_mappings: Optional[Dict[str, str]] = None):
        """
        Initialize the column mapper.

        Args:
            custom_mappings: Optional dict mapping field names to column names
        """
        self.custom_mappings = custom_mappings or {}
        self._detected_mappings: Dict[str, str] = {}

    def detect_mapping(self, headers: List[str]) -> Dict[str, str]:
        """
        Auto-detect column mapping from headers.

        Args:
            headers: List of CSV column headers

        Returns:
            Dictionary mapping field names to column names
        """
        mappings = {}
        normalized_headers = {h.lower().strip().replace(' ', '_'): h for h in headers}

        # Apply custom mappings first
        for field, column in self.custom_mappings.items():
            if column in headers:
                mappings[field] = column

        # Auto-detect remaining fields
        for field, patterns in self.DEFAULT_MAPPINGS.items():
            if field in mappings:
                continue

            for pattern in patterns:
                # Exact match
                if pattern in normalized_headers:
                    mappings[field] = normalized_headers[pattern]
                    break

                # Partial match
                for norm_header, orig_header in normalized_headers.items():
                    if pattern in norm_header or norm_header in pattern:
                        if field not in mappings:
                            mappings[field] = orig_header
                            break

        self._detected_mappings = mappings
        return mappings

    def get_mapping(self) -> Dict[str, str]:
        """Get the current column mapping."""
        return self._detected_mappings

    def map_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a row using the detected/configured mapping.

        Args:
            row: Dictionary representing a CSV row

        Returns:
            Dictionary with standardized field names
        """
        result = {}

        for field, column in self._detected_mappings.items():
            if column in row:
                result[field] = row[column]

        # Handle separate debit/credit columns
        if 'debit' in result or 'credit' in result:
            debit = result.pop('debit', None)
            credit = result.pop('credit', None)

            if debit and str(debit).strip():
                result['amount'] = f"-{debit}"
                result['type'] = 'expense'
            elif credit and str(credit).strip():
                result['amount'] = credit
                result['type'] = 'income'

        return result


class CSVImporter(BaseImporter):
    """
    CSV file importer with multi-format support.

    Features:
    - Auto-detection of delimiter (comma, semicolon, tab, pipe)
    - Auto-detection of encoding (UTF-8, Latin-1, etc.)
    - Automatic column mapping
    - Support for debit/credit split columns
    - Progress tracking for large files
    """

    # Possible delimiters to detect
    DELIMITERS = [',', ';', '\t', '|']

    def __init__(self, user=None, bank_account=None,
                 delimiter: Optional[str] = None,
                 encoding: Optional[str] = None,
                 column_mapping: Optional[Dict[str, str]] = None,
                 skip_rows: int = 0,
                 date_format: Optional[str] = None):
        """
        Initialize the CSV importer.

        Args:
            user: Django user instance
            bank_account: Optional bank account
            delimiter: CSV delimiter (auto-detect if None)
            encoding: File encoding (auto-detect if None)
            column_mapping: Custom column mapping
            skip_rows: Number of rows to skip at beginning
            date_format: Date format to use (auto-detect if None)
        """
        super().__init__(user, bank_account)
        self.delimiter = delimiter
        self.encoding = encoding
        self.column_mapping = column_mapping
        self.skip_rows = skip_rows
        self.date_format = date_format
        self.mapper = ColumnMapper(column_mapping)

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file extensions."""
        return ['csv', 'txt', 'tsv']

    def detect_delimiter(self, sample: str) -> str:
        """
        Detect the CSV delimiter from a sample.

        Args:
            sample: Sample text from the file

        Returns:
            Detected delimiter character
        """
        # Count occurrences of each delimiter
        counts = {}
        for delim in self.DELIMITERS:
            counts[delim] = sample.count(delim)

        # Use csv.Sniffer for more accurate detection
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=''.join(self.DELIMITERS))
            return dialect.delimiter
        except csv.Error:
            pass

        # Fall back to most common delimiter
        if counts:
            return max(counts, key=counts.get)

        return ','

    def parse(self, file_obj: Union[BinaryIO, TextIO]) -> ImportResult:
        """
        Parse a CSV file and extract transactions.

        Args:
            file_obj: File object to parse

        Returns:
            ImportResult with parsed transactions
        """
        result = ImportResult(success=True)

        try:
            # Handle binary vs text file
            if hasattr(file_obj, 'mode') and 'b' in file_obj.mode:
                content = self._read_binary_file(file_obj)
            else:
                # Check if it's a binary stream without mode attribute
                try:
                    content = file_obj.read()
                    if isinstance(content, bytes):
                        encoding = self.encoding or self.detect_encoding(
                            io.BytesIO(content)
                        )
                        content = content.decode(encoding)
                except UnicodeDecodeError:
                    file_obj.seek(0)
                    content = self._read_binary_file(file_obj)

            # Detect delimiter if not specified
            delimiter = self.delimiter
            if not delimiter:
                delimiter = self.detect_delimiter(content[:4096])

            # Parse CSV
            reader = csv.DictReader(
                io.StringIO(content),
                delimiter=delimiter,
            )

            # Skip specified rows
            rows = list(reader)
            if self.skip_rows:
                rows = rows[self.skip_rows:]

            result.total_rows = len(rows)

            if not rows:
                result.add_warning("File contains no data rows")
                return result

            # Detect column mapping
            headers = reader.fieldnames or []
            mapping = self.mapper.detect_mapping(headers)

            # Validate required columns
            if 'date' not in mapping:
                result.add_warning(
                    "Could not detect date column. "
                    "Please specify column mapping manually."
                )
            if 'amount' not in mapping and 'debit' not in mapping:
                result.add_warning(
                    "Could not detect amount column. "
                    "Please specify column mapping manually."
                )

            # Parse each row
            for i, row in enumerate(rows):
                try:
                    # Map columns
                    mapped_data = self.mapper.map_row(row)

                    # Skip empty rows
                    if not mapped_data.get('amount') and not mapped_data.get('date'):
                        result.skipped_count += 1
                        continue

                    # Validate and create transaction
                    transaction = self.validate_transaction(mapped_data, i + 1)
                    result.add_transaction(transaction)

                    # Report progress
                    self._report_progress(i + 1, result.total_rows)

                except ValidationError as e:
                    result.add_error(str(e), i + 1, {'field': e.field, 'value': e.value})
                except Exception as e:
                    result.add_error(str(e), i + 1)

            # Final status
            if result.error_count > 0 and result.imported_count == 0:
                result.success = False

        except csv.Error as e:
            result.success = False
            result.add_error(f"CSV parsing error: {e}")
        except Exception as e:
            result.success = False
            result.add_error(f"Unexpected error: {e}")
            logger.exception("CSV import failed")

        return result

    def _read_binary_file(self, file_obj: BinaryIO) -> str:
        """Read binary file with encoding detection."""
        position = file_obj.tell()
        file_obj.seek(0)

        # Detect encoding
        encoding = self.encoding or self.detect_encoding(file_obj)

        # Read and decode
        file_obj.seek(0)
        content = file_obj.read()

        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            # Try fallback encodings
            for enc in self.SUPPORTED_ENCODINGS:
                try:
                    return content.decode(enc)
                except UnicodeDecodeError:
                    continue

            # Last resort: decode with replacement
            return content.decode('utf-8', errors='replace')

    def preview(self, file_obj: Union[BinaryIO, TextIO],
                num_rows: int = 10) -> Dict[str, Any]:
        """
        Preview the CSV file without full parsing.

        Args:
            file_obj: File object to preview
            num_rows: Number of rows to preview

        Returns:
            Dictionary with preview information
        """
        try:
            # Read file content
            if hasattr(file_obj, 'mode') and 'b' in file_obj.mode:
                content = self._read_binary_file(file_obj)
            else:
                content = file_obj.read()
                if isinstance(content, bytes):
                    content = content.decode(
                        self.encoding or
                        self.detect_encoding(io.BytesIO(content))
                    )

            # Detect delimiter
            delimiter = self.delimiter or self.detect_delimiter(content[:4096])

            # Parse header and sample rows
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            headers = reader.fieldnames or []

            rows = []
            for i, row in enumerate(reader):
                if i >= num_rows:
                    break
                rows.append(row)

            # Detect column mapping
            mapping = self.mapper.detect_mapping(headers)

            return {
                'success': True,
                'headers': headers,
                'delimiter': delimiter,
                'detected_mapping': mapping,
                'sample_rows': rows,
                'total_rows_preview': len(rows),
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def validate_mapping(self, mapping: Dict[str, str],
                        headers: List[str]) -> List[str]:
        """
        Validate a column mapping against available headers.

        Args:
            mapping: Proposed column mapping
            headers: Available CSV headers

        Returns:
            List of validation error messages
        """
        errors = []

        # Check required fields
        required_fields = ['date']
        if 'amount' not in mapping and not ('debit' in mapping or 'credit' in mapping):
            required_fields.append('amount')

        for field in required_fields:
            if field not in mapping:
                errors.append(f"Required field '{field}' is not mapped")
            elif mapping[field] not in headers:
                errors.append(
                    f"Column '{mapping[field]}' for field '{field}' "
                    f"not found in file"
                )

        # Check that mapped columns exist
        for field, column in mapping.items():
            if column not in headers:
                errors.append(f"Column '{column}' not found in file")

        return errors
