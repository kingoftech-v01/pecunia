"""
Export Service for Finance Desktop Application.

Provides functionality to export transactions and reports to various formats
including CSV, Excel, and PDF with progress tracking for large exports.
"""

import csv
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Callable
from decimal import Decimal
from io import BytesIO

# Third-party imports (with graceful fallbacks)
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, Image
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ExportError(Exception):
    """Exception raised for export-related errors."""
    pass


class ExportService:
    """
    Service for exporting financial data to various formats.

    Supports CSV, Excel (.xlsx), and PDF exports with progress
    callbacks for large data sets.
    """

    def __init__(self):
        """Initialize the export service."""
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

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

    def _filter_by_date_range(
        self,
        transactions: List[Dict[str, Any]],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter transactions by date range.

        Args:
            transactions: List of transaction dictionaries
            start_date: Start date for filtering (inclusive)
            end_date: End date for filtering (inclusive)

        Returns:
            Filtered list of transactions
        """
        if not start_date and not end_date:
            return transactions

        filtered = []
        for txn in transactions:
            txn_date = txn.get('date')
            if isinstance(txn_date, str):
                txn_date = datetime.strptime(txn_date, '%Y-%m-%d').date()
            elif isinstance(txn_date, datetime):
                txn_date = txn_date.date()

            if start_date and txn_date < start_date:
                continue
            if end_date and txn_date > end_date:
                continue
            filtered.append(txn)

        return filtered

    def _format_amount(self, amount: Any) -> str:
        """Format amount for display."""
        if isinstance(amount, Decimal):
            return f"${amount:,.2f}"
        elif isinstance(amount, (int, float)):
            return f"${amount:,.2f}"
        return str(amount)

    def _format_date(self, dt: Any) -> str:
        """Format date for display."""
        if isinstance(dt, str):
            return dt
        elif isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d')
        elif isinstance(dt, date):
            return dt.strftime('%Y-%m-%d')
        return str(dt)

    # =========================================================================
    # CSV Export
    # =========================================================================

    def export_transactions_to_csv(
        self,
        transactions: List[Dict[str, Any]],
        output_path: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_headers: bool = True
    ) -> str:
        """
        Export transactions to a CSV file.

        Args:
            transactions: List of transaction dictionaries
            output_path: Path for the output CSV file
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            include_headers: Whether to include column headers

        Returns:
            Path to the created file

        Raises:
            ExportError: If export fails
        """
        try:
            filtered = self._filter_by_date_range(transactions, start_date, end_date)
            total = len(filtered)

            self._report_progress(0, total, "Starting CSV export...")

            # Define CSV columns
            fieldnames = [
                'date', 'description', 'category', 'amount',
                'type', 'account', 'notes', 'tags'
            ]

            # Validate output path
            output_path = os.path.realpath(output_path)
            if not os.path.isabs(output_path):
                raise ExportError("Output path must be absolute")

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

                if include_headers:
                    writer.writeheader()

                for i, txn in enumerate(filtered):
                    # Prepare row data
                    row = {
                        'date': self._format_date(txn.get('date', '')),
                        'description': txn.get('description', ''),
                        'category': txn.get('category', ''),
                        'amount': txn.get('amount', 0),
                        'type': txn.get('type', ''),
                        'account': txn.get('account', ''),
                        'notes': txn.get('notes', ''),
                        'tags': ', '.join(txn.get('tags', [])) if isinstance(txn.get('tags'), list) else txn.get('tags', '')
                    }
                    writer.writerow(row)

                    if (i + 1) % 100 == 0 or i == total - 1:
                        self._report_progress(i + 1, total, f"Exported {i + 1} of {total} transactions")

            self._report_progress(total, total, "CSV export complete!")
            return output_path

        except Exception as e:
            raise ExportError(f"Failed to export to CSV: {str(e)}") from e

    # =========================================================================
    # Excel Export
    # =========================================================================

    def export_transactions_to_excel(
        self,
        transactions: List[Dict[str, Any]],
        output_path: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sheet_name: str = "Transactions"
    ) -> str:
        """
        Export transactions to an Excel file.

        Args:
            transactions: List of transaction dictionaries
            output_path: Path for the output Excel file
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            sheet_name: Name of the worksheet

        Returns:
            Path to the created file

        Raises:
            ExportError: If export fails or openpyxl is not available
        """
        if not EXCEL_AVAILABLE:
            raise ExportError("Excel export requires openpyxl. Install with: pip install openpyxl")

        try:
            filtered = self._filter_by_date_range(transactions, start_date, end_date)
            total = len(filtered)

            self._report_progress(0, total, "Starting Excel export...")

            # Create workbook and worksheet
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet_name

            # Define headers
            headers = ['Date', 'Description', 'Category', 'Amount', 'Type', 'Account', 'Notes', 'Tags']

            # Style definitions
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")

            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # Write headers
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border

            # Write data rows
            for i, txn in enumerate(filtered):
                row = i + 2  # Start from row 2 (after headers)

                ws.cell(row=row, column=1, value=self._format_date(txn.get('date', '')))
                ws.cell(row=row, column=2, value=txn.get('description', ''))
                ws.cell(row=row, column=3, value=txn.get('category', ''))

                # Amount cell with number formatting
                amount_cell = ws.cell(row=row, column=4, value=txn.get('amount', 0))
                amount_cell.number_format = '$#,##0.00'

                ws.cell(row=row, column=5, value=txn.get('type', ''))
                ws.cell(row=row, column=6, value=txn.get('account', ''))
                ws.cell(row=row, column=7, value=txn.get('notes', ''))

                tags = txn.get('tags', [])
                ws.cell(row=row, column=8, value=', '.join(tags) if isinstance(tags, list) else tags)

                # Apply borders to data cells
                for col in range(1, len(headers) + 1):
                    ws.cell(row=row, column=col).border = thin_border

                if (i + 1) % 100 == 0 or i == total - 1:
                    self._report_progress(i + 1, total, f"Exported {i + 1} of {total} transactions")

            # Auto-adjust column widths
            for col in range(1, len(headers) + 1):
                max_length = len(headers[col - 1])
                column_letter = get_column_letter(col)

                for row in range(2, min(total + 2, 102)):  # Check first 100 rows
                    cell_value = ws.cell(row=row, column=col).value
                    if cell_value:
                        max_length = max(max_length, len(str(cell_value)))

                ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

            # Freeze header row
            ws.freeze_panes = 'A2'

            # Add summary row
            if total > 0:
                summary_row = total + 3
                ws.cell(row=summary_row, column=1, value="Summary").font = Font(bold=True)
                ws.cell(row=summary_row, column=3, value="Total:")
                ws.cell(row=summary_row, column=4, value=f"=SUM(D2:D{total + 1})")
                ws.cell(row=summary_row, column=4).number_format = '$#,##0.00'

            # Save workbook
            wb.save(output_path)

            self._report_progress(total, total, "Excel export complete!")
            return output_path

        except Exception as e:
            raise ExportError(f"Failed to export to Excel: {str(e)}") from e

    # =========================================================================
    # PDF Export - Transactions
    # =========================================================================

    def export_transactions_to_pdf(
        self,
        transactions: List[Dict[str, Any]],
        output_path: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        title: str = "Transaction Report",
        page_size: str = "letter"
    ) -> str:
        """
        Export transactions to a PDF file.

        Args:
            transactions: List of transaction dictionaries
            output_path: Path for the output PDF file
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            title: Title for the report
            page_size: Page size ('letter' or 'a4')

        Returns:
            Path to the created file

        Raises:
            ExportError: If export fails or reportlab is not available
        """
        if not PDF_AVAILABLE:
            raise ExportError("PDF export requires reportlab. Install with: pip install reportlab")

        try:
            filtered = self._filter_by_date_range(transactions, start_date, end_date)
            total = len(filtered)

            self._report_progress(0, total, "Starting PDF export...")

            # Page size configuration
            page = letter if page_size.lower() == 'letter' else A4

            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch
            )

            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=20
            )
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.gray
            )

            # Build document elements
            elements = []

            # Title
            elements.append(Paragraph(title, title_style))

            # Date range subtitle
            date_range_text = "All transactions"
            if start_date and end_date:
                date_range_text = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            elif start_date:
                date_range_text = f"From: {start_date.strftime('%Y-%m-%d')}"
            elif end_date:
                date_range_text = f"Until: {end_date.strftime('%Y-%m-%d')}"

            elements.append(Paragraph(date_range_text, subtitle_style))
            elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
            elements.append(Spacer(1, 20))

            # Table data
            table_data = [['Date', 'Description', 'Category', 'Amount', 'Type']]

            for i, txn in enumerate(filtered):
                row = [
                    self._format_date(txn.get('date', '')),
                    str(txn.get('description', ''))[:30],  # Truncate long descriptions
                    str(txn.get('category', ''))[:15],
                    self._format_amount(txn.get('amount', 0)),
                    str(txn.get('type', ''))
                ]
                table_data.append(row)

                if (i + 1) % 100 == 0:
                    self._report_progress(i + 1, total, f"Processing {i + 1} of {total} transactions")

            # Calculate totals
            total_amount = sum(
                float(txn.get('amount', 0))
                for txn in filtered
                if isinstance(txn.get('amount'), (int, float, Decimal))
            )
            table_data.append(['', '', 'Total:', self._format_amount(total_amount), ''])

            # Create table
            col_widths = [0.9 * inch, 2.5 * inch, 1.2 * inch, 1.0 * inch, 0.8 * inch]
            table = Table(table_data, colWidths=col_widths)

            # Table style
            table_style = TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

                # Data styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Amount column

                # Total row styling
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E7E6E6')),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F2F2F2')])
            ])
            table.setStyle(table_style)

            elements.append(table)

            # Build PDF
            doc.build(elements)

            self._report_progress(total, total, "PDF export complete!")
            return output_path

        except Exception as e:
            raise ExportError(f"Failed to export to PDF: {str(e)}") from e

    # =========================================================================
    # PDF Export - Budget Report
    # =========================================================================

    def export_budget_report_to_pdf(
        self,
        budget_data: Dict[str, Any],
        output_path: str,
        title: str = "Budget Report",
        page_size: str = "letter"
    ) -> str:
        """
        Export a budget report to PDF.

        Args:
            budget_data: Dictionary containing budget information:
                - 'categories': List of category budgets with 'name', 'budgeted', 'spent', 'remaining'
                - 'period': Budget period (e.g., "January 2024")
                - 'total_budgeted': Total budgeted amount
                - 'total_spent': Total spent amount
                - 'income': Optional income data
            output_path: Path for the output PDF file
            title: Title for the report
            page_size: Page size ('letter' or 'a4')

        Returns:
            Path to the created file

        Raises:
            ExportError: If export fails or reportlab is not available
        """
        if not PDF_AVAILABLE:
            raise ExportError("PDF export requires reportlab. Install with: pip install reportlab")

        try:
            categories = budget_data.get('categories', [])
            total = len(categories)

            self._report_progress(0, total, "Starting budget report export...")

            # Page size configuration
            page = letter if page_size.lower() == 'letter' else A4

            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch
            )

            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'BudgetTitle',
                parent=styles['Heading1'],
                fontSize=20,
                alignment=TA_CENTER,
                spaceAfter=10
            )
            period_style = ParagraphStyle(
                'Period',
                parent=styles['Normal'],
                fontSize=12,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.HexColor('#666666')
            )
            section_style = ParagraphStyle(
                'Section',
                parent=styles['Heading2'],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10
            )

            elements = []

            # Title
            elements.append(Paragraph(title, title_style))

            # Period
            period = budget_data.get('period', datetime.now().strftime('%B %Y'))
            elements.append(Paragraph(f"Period: {period}", period_style))
            elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", period_style))
            elements.append(Spacer(1, 20))

            # Summary section
            elements.append(Paragraph("Budget Summary", section_style))

            total_budgeted = budget_data.get('total_budgeted', 0)
            total_spent = budget_data.get('total_spent', 0)
            total_remaining = total_budgeted - total_spent
            income = budget_data.get('income', 0)

            summary_data = [
                ['Metric', 'Amount'],
                ['Total Income', self._format_amount(income)] if income else None,
                ['Total Budgeted', self._format_amount(total_budgeted)],
                ['Total Spent', self._format_amount(total_spent)],
                ['Remaining', self._format_amount(total_remaining)],
                ['Budget Utilization', f"{(total_spent / total_budgeted * 100):.1f}%" if total_budgeted > 0 else "N/A"]
            ]
            summary_data = [row for row in summary_data if row is not None]

            summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 30))

            # Category breakdown
            elements.append(Paragraph("Category Breakdown", section_style))

            category_data = [['Category', 'Budgeted', 'Spent', 'Remaining', 'Status']]

            for i, cat in enumerate(categories):
                budgeted = cat.get('budgeted', 0)
                spent = cat.get('spent', 0)
                remaining = cat.get('remaining', budgeted - spent)

                # Determine status
                if budgeted > 0:
                    pct = spent / budgeted * 100
                    if pct >= 100:
                        status = "Over Budget"
                    elif pct >= 90:
                        status = "Warning"
                    elif pct >= 75:
                        status = "On Track"
                    else:
                        status = "Under Budget"
                else:
                    status = "No Budget"

                row = [
                    str(cat.get('name', 'Unknown')),
                    self._format_amount(budgeted),
                    self._format_amount(spent),
                    self._format_amount(remaining),
                    status
                ]
                category_data.append(row)

                self._report_progress(i + 1, total, f"Processing category {i + 1} of {total}")

            # Add totals row
            category_data.append([
                'TOTAL',
                self._format_amount(total_budgeted),
                self._format_amount(total_spent),
                self._format_amount(total_remaining),
                ''
            ])

            col_widths = [1.8 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch]
            category_table = Table(category_data, colWidths=col_widths)

            # Build table style with conditional formatting
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
                ('ALIGN', (4, 0), (4, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F2F2F2')]),
                # Total row styling
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E7E6E6')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]

            # Add conditional colors for status column
            for i, row in enumerate(category_data[1:-1], start=1):
                status = row[4]
                if status == "Over Budget":
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.red))
                elif status == "Warning":
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.orange))
                elif status == "On Track":
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.green))

            category_table.setStyle(TableStyle(table_style))
            elements.append(category_table)

            # Notes section
            notes = budget_data.get('notes')
            if notes:
                elements.append(Spacer(1, 30))
                elements.append(Paragraph("Notes", section_style))
                notes_style = ParagraphStyle(
                    'Notes',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#333333')
                )
                elements.append(Paragraph(notes, notes_style))

            # Build PDF
            doc.build(elements)

            self._report_progress(total, total, "Budget report export complete!")
            return output_path

        except Exception as e:
            raise ExportError(f"Failed to export budget report to PDF: {str(e)}") from e

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_available_formats(self) -> Dict[str, bool]:
        """
        Get dictionary of available export formats.

        Returns:
            Dictionary with format names as keys and availability as values
        """
        return {
            'csv': True,  # Always available (built-in)
            'excel': EXCEL_AVAILABLE,
            'pdf': PDF_AVAILABLE
        }

    def export_to_bytes(
        self,
        transactions: List[Dict[str, Any]],
        format: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> BytesIO:
        """
        Export transactions to a BytesIO buffer instead of a file.

        Useful for web applications or when file path is not needed.

        Args:
            transactions: List of transaction dictionaries
            format: Export format ('csv', 'excel', 'pdf')
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            BytesIO buffer containing the exported data

        Raises:
            ExportError: If export fails or format is not supported
        """
        import tempfile

        buffer = BytesIO()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format}') as tmp:
            tmp_path = tmp.name

        try:
            if format.lower() == 'csv':
                self.export_transactions_to_csv(transactions, tmp_path, start_date, end_date)
            elif format.lower() in ('excel', 'xlsx'):
                self.export_transactions_to_excel(transactions, tmp_path, start_date, end_date)
            elif format.lower() == 'pdf':
                self.export_transactions_to_pdf(transactions, tmp_path, start_date, end_date)
            else:
                raise ExportError(f"Unsupported format: {format}")

            with open(tmp_path, 'rb') as f:
                buffer.write(f.read())

            buffer.seek(0)
            return buffer

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
