"""
Report Generator Service for Finance Desktop Application.

Provides comprehensive report generation functionality including monthly,
yearly, and custom date range reports with PDF generation and chart support.
"""

import calendar
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import BytesIO
from typing import List, Dict, Any, Optional, Callable, Tuple
from collections import defaultdict

# Third-party imports (with graceful fallbacks)
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, Image, KeepTogether, Flowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.legends import Legend
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None


class ReportError(Exception):
    """Exception raised for report generation errors."""
    pass


class ReportGenerator:
    """
    Service for generating financial reports with charts and analysis.

    Supports monthly, yearly, and custom date range reports with
    PDF output including visual charts.
    """

    # Color scheme for charts
    CHART_COLORS = [
        colors.HexColor('#4472C4'),  # Blue
        colors.HexColor('#ED7D31'),  # Orange
        colors.HexColor('#A5A5A5'),  # Gray
        colors.HexColor('#FFC000'),  # Yellow
        colors.HexColor('#5B9BD5'),  # Light Blue
        colors.HexColor('#70AD47'),  # Green
        colors.HexColor('#9E480E'),  # Brown
        colors.HexColor('#997300'),  # Dark Yellow
        colors.HexColor('#264478'),  # Dark Blue
        colors.HexColor('#43682B'),  # Dark Green
    ]

    def __init__(self):
        """Initialize the report generator."""
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

    # =========================================================================
    # Data Aggregation Methods
    # =========================================================================

    def _aggregate_by_category(
        self,
        transactions: List[Dict[str, Any]],
        transaction_type: Optional[str] = None
    ) -> Dict[str, Decimal]:
        """
        Aggregate transaction amounts by category.

        Args:
            transactions: List of transaction dictionaries
            transaction_type: Filter by type ('income', 'expense', etc.)

        Returns:
            Dictionary mapping category names to total amounts
        """
        aggregated = defaultdict(Decimal)

        for txn in transactions:
            if transaction_type and txn.get('type') != transaction_type:
                continue
            category = txn.get('category', 'Uncategorized')
            amount = Decimal(str(txn.get('amount', 0)))
            aggregated[category] += abs(amount)

        return dict(aggregated)

    def _aggregate_by_date(
        self,
        transactions: List[Dict[str, Any]],
        granularity: str = 'daily'
    ) -> Dict[str, Decimal]:
        """
        Aggregate transaction amounts by date.

        Args:
            transactions: List of transaction dictionaries
            granularity: 'daily', 'weekly', or 'monthly'

        Returns:
            Dictionary mapping date strings to total amounts
        """
        aggregated = defaultdict(Decimal)

        for txn in transactions:
            txn_date = txn.get('date')
            if isinstance(txn_date, str):
                txn_date = datetime.strptime(txn_date, '%Y-%m-%d').date()
            elif isinstance(txn_date, datetime):
                txn_date = txn_date.date()

            if granularity == 'daily':
                key = txn_date.strftime('%Y-%m-%d')
            elif granularity == 'weekly':
                # Use Monday of the week as key
                monday = txn_date - timedelta(days=txn_date.weekday())
                key = monday.strftime('%Y-%m-%d')
            elif granularity == 'monthly':
                key = txn_date.strftime('%Y-%m')
            else:
                key = txn_date.strftime('%Y-%m-%d')

            amount = Decimal(str(txn.get('amount', 0)))
            aggregated[key] += amount

        return dict(sorted(aggregated.items()))

    def _calculate_summary_stats(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate summary statistics for transactions.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with summary statistics
        """
        if not transactions:
            return {
                'total_income': Decimal('0'),
                'total_expenses': Decimal('0'),
                'net_amount': Decimal('0'),
                'transaction_count': 0,
                'average_transaction': Decimal('0'),
                'largest_expense': Decimal('0'),
                'largest_income': Decimal('0'),
            }

        total_income = Decimal('0')
        total_expenses = Decimal('0')
        largest_expense = Decimal('0')
        largest_income = Decimal('0')

        for txn in transactions:
            amount = Decimal(str(txn.get('amount', 0)))
            txn_type = txn.get('type', '').lower()

            if txn_type == 'income':
                total_income += abs(amount)
                largest_income = max(largest_income, abs(amount))
            elif txn_type == 'expense':
                total_expenses += abs(amount)
                largest_expense = max(largest_expense, abs(amount))

        count = len(transactions)
        total = total_income - total_expenses

        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_amount': total,
            'transaction_count': count,
            'average_transaction': total / count if count > 0 else Decimal('0'),
            'largest_expense': largest_expense,
            'largest_income': largest_income,
        }

    def _filter_transactions_by_date(
        self,
        transactions: List[Dict[str, Any]],
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Filter transactions within a date range."""
        filtered = []
        for txn in transactions:
            txn_date = txn.get('date')
            if isinstance(txn_date, str):
                txn_date = datetime.strptime(txn_date, '%Y-%m-%d').date()
            elif isinstance(txn_date, datetime):
                txn_date = txn_date.date()

            if start_date <= txn_date <= end_date:
                filtered.append(txn)

        return filtered

    # =========================================================================
    # Chart Generation (using ReportLab)
    # =========================================================================

    def _create_pie_chart(
        self,
        data: Dict[str, Decimal],
        title: str = "",
        width: int = 300,
        height: int = 200
    ) -> Drawing:
        """
        Create a pie chart for category breakdown.

        Args:
            data: Dictionary mapping labels to values
            title: Chart title
            width: Chart width
            height: Chart height

        Returns:
            ReportLab Drawing object
        """
        drawing = Drawing(width, height)

        # Create pie chart
        pie = Pie()
        pie.x = width // 2 - 60
        pie.y = 30
        pie.width = 120
        pie.height = 120

        # Set data
        values = [float(v) for v in data.values()]
        labels = list(data.keys())

        if not values or all(v == 0 for v in values):
            # Return empty drawing if no data
            drawing.add(String(width // 2, height // 2, "No data available",
                              textAnchor='middle', fontSize=10))
            return drawing

        pie.data = values
        pie.labels = [f"{k[:15]}..." if len(k) > 15 else k for k in labels]

        # Set colors
        for i, _ in enumerate(values):
            pie.slices[i].fillColor = self.CHART_COLORS[i % len(self.CHART_COLORS)]
            pie.slices[i].strokeWidth = 0.5
            pie.slices[i].strokeColor = colors.white

        # Add legend
        legend = Legend()
        legend.x = width - 100
        legend.y = height - 30
        legend.dx = 8
        legend.dy = 8
        legend.fontName = 'Helvetica'
        legend.fontSize = 7
        legend.boxAnchor = 'nw'
        legend.columnMaximum = 10
        legend.strokeWidth = 0.5
        legend.strokeColor = colors.black
        legend.deltax = 75
        legend.deltay = 10
        legend.autoXPadding = 5
        legend.yGap = 0
        legend.dxTextSpace = 3
        legend.alignment = 'right'
        legend.dividerLines = 1 | 2 | 4
        legend.dividerOffsY = 4.5
        legend.subCols.rpad = 30

        legend.colorNamePairs = [
            (self.CHART_COLORS[i % len(self.CHART_COLORS)], labels[i][:20])
            for i in range(len(labels))
        ]

        drawing.add(pie)
        drawing.add(legend)

        # Add title
        if title:
            drawing.add(String(width // 2, height - 10, title,
                              textAnchor='middle', fontSize=11, fontName='Helvetica-Bold'))

        return drawing

    def _create_bar_chart(
        self,
        data: Dict[str, Decimal],
        title: str = "",
        width: int = 400,
        height: int = 200
    ) -> Drawing:
        """
        Create a bar chart for time-based data.

        Args:
            data: Dictionary mapping labels to values
            title: Chart title
            width: Chart width
            height: Chart height

        Returns:
            ReportLab Drawing object
        """
        drawing = Drawing(width, height)

        if not data:
            drawing.add(String(width // 2, height // 2, "No data available",
                              textAnchor='middle', fontSize=10))
            return drawing

        # Create bar chart
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 30
        bc.width = width - 100
        bc.height = height - 70
        bc.data = [[float(v) for v in data.values()]]

        # Configure bars
        bc.bars[0].fillColor = self.CHART_COLORS[0]
        bc.bars[0].strokeWidth = 0.5

        # Configure axes
        bc.categoryAxis.labels.boxAnchor = 'ne'
        bc.categoryAxis.labels.dx = -8
        bc.categoryAxis.labels.dy = -2
        bc.categoryAxis.labels.angle = 45
        bc.categoryAxis.labels.fontName = 'Helvetica'
        bc.categoryAxis.labels.fontSize = 7
        bc.categoryAxis.categoryNames = list(data.keys())

        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = max(float(v) for v in data.values()) * 1.1
        bc.valueAxis.valueStep = bc.valueAxis.valueMax / 5
        bc.valueAxis.labels.fontName = 'Helvetica'
        bc.valueAxis.labels.fontSize = 8

        drawing.add(bc)

        # Add title
        if title:
            drawing.add(String(width // 2, height - 10, title,
                              textAnchor='middle', fontSize=11, fontName='Helvetica-Bold'))

        return drawing

    def _create_matplotlib_chart(
        self,
        data: Dict[str, Decimal],
        chart_type: str = 'bar',
        title: str = "",
        figsize: Tuple[int, int] = (8, 4)
    ) -> Optional[BytesIO]:
        """
        Create a chart using matplotlib (higher quality).

        Args:
            data: Dictionary mapping labels to values
            chart_type: 'bar', 'pie', or 'line'
            title: Chart title
            figsize: Figure size in inches

        Returns:
            BytesIO buffer containing PNG image, or None if matplotlib unavailable
        """
        if not MATPLOTLIB_AVAILABLE or not plt:
            return None

        fig, ax = plt.subplots(figsize=figsize)

        labels = list(data.keys())
        values = [float(v) for v in data.values()]

        if not values:
            plt.close(fig)
            return None

        if chart_type == 'pie':
            # Pie chart
            colors_list = ['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000',
                          '#5B9BD5', '#70AD47', '#9E480E', '#997300']
            wedges, texts, autotexts = ax.pie(
                values,
                labels=None,
                autopct='%1.1f%%',
                colors=colors_list[:len(values)],
                startangle=90
            )
            ax.legend(wedges, labels, loc='center left', bbox_to_anchor=(1, 0.5))

        elif chart_type == 'line':
            # Line chart
            ax.plot(labels, values, marker='o', color='#4472C4', linewidth=2)
            ax.fill_between(labels, values, alpha=0.3, color='#4472C4')
            plt.xticks(rotation=45, ha='right')
            ax.set_ylabel('Amount ($)')
            ax.grid(True, alpha=0.3)

        else:  # bar chart
            bars = ax.bar(labels, values, color='#4472C4', edgecolor='white')
            plt.xticks(rotation=45, ha='right')
            ax.set_ylabel('Amount ($)')
            ax.grid(True, axis='y', alpha=0.3)

        if title:
            ax.set_title(title, fontsize=12, fontweight='bold')

        plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buffer.seek(0)

        return buffer

    # =========================================================================
    # Report Generation Methods
    # =========================================================================

    def generate_monthly_report(
        self,
        transactions: List[Dict[str, Any]],
        month: int,
        year: int,
        output_path: str,
        budgets: Optional[List[Dict[str, Any]]] = None,
        include_charts: bool = True
    ) -> str:
        """
        Generate a monthly financial report.

        Args:
            transactions: List of all transaction dictionaries
            month: Month number (1-12)
            year: Year (e.g., 2024)
            output_path: Path for the output PDF file
            budgets: Optional list of budget data for comparison
            include_charts: Whether to include visual charts

        Returns:
            Path to the created PDF file

        Raises:
            ReportError: If report generation fails
        """
        if not PDF_AVAILABLE:
            raise ReportError("PDF generation requires reportlab. Install with: pip install reportlab")

        try:
            self._report_progress(0, 10, "Starting monthly report generation...")

            # Calculate date range
            start_date = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)
            month_name = calendar.month_name[month]

            # Filter transactions
            filtered = self._filter_transactions_by_date(transactions, start_date, end_date)
            self._report_progress(1, 10, "Filtered transactions...")

            # Calculate statistics
            stats = self._calculate_summary_stats(filtered)
            expense_by_category = self._aggregate_by_category(filtered, 'expense')
            income_by_category = self._aggregate_by_category(filtered, 'income')
            daily_totals = self._aggregate_by_date(filtered, 'daily')
            self._report_progress(3, 10, "Calculated statistics...")

            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch
            )

            styles = getSampleStyleSheet()
            elements = []

            # Title
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=20,
                alignment=TA_CENTER,
                spaceAfter=10
            )
            subtitle_style = ParagraphStyle(
                'ReportSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.gray
            )
            section_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor('#4472C4')
            )

            elements.append(Paragraph(f"Monthly Financial Report", title_style))
            elements.append(Paragraph(f"{month_name} {year}", subtitle_style))
            elements.append(Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                subtitle_style
            ))
            elements.append(Spacer(1, 20))
            self._report_progress(4, 10, "Created header...")

            # Summary Section
            elements.append(Paragraph("Financial Summary", section_style))

            summary_data = [
                ['Metric', 'Amount'],
                ['Total Income', f"${stats['total_income']:,.2f}"],
                ['Total Expenses', f"${stats['total_expenses']:,.2f}"],
                ['Net Savings', f"${stats['net_amount']:,.2f}"],
                ['Transaction Count', str(stats['transaction_count'])],
                ['Average Transaction', f"${abs(stats['average_transaction']):,.2f}"],
                ['Largest Income', f"${stats['largest_income']:,.2f}"],
                ['Largest Expense', f"${stats['largest_expense']:,.2f}"],
            ]

            summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))
            self._report_progress(5, 10, "Created summary table...")

            # Charts
            if include_charts and expense_by_category:
                elements.append(Paragraph("Expense Breakdown by Category", section_style))

                # Try matplotlib first for better quality
                chart_buffer = self._create_matplotlib_chart(
                    expense_by_category, 'pie', 'Expenses by Category', (6, 4)
                )
                if chart_buffer:
                    elements.append(Image(chart_buffer, width=5*inch, height=3.3*inch))
                else:
                    # Fallback to reportlab
                    pie_chart = self._create_pie_chart(expense_by_category, "Expenses by Category", 400, 250)
                    elements.append(pie_chart)

                elements.append(Spacer(1, 20))
                self._report_progress(6, 10, "Created expense chart...")

            # Daily spending chart
            if include_charts and daily_totals:
                elements.append(Paragraph("Daily Transaction Totals", section_style))

                chart_buffer = self._create_matplotlib_chart(
                    daily_totals, 'bar', 'Daily Totals', (8, 3)
                )
                if chart_buffer:
                    elements.append(Image(chart_buffer, width=6*inch, height=2.5*inch))
                else:
                    bar_chart = self._create_bar_chart(daily_totals, "Daily Totals", 450, 200)
                    elements.append(bar_chart)

                elements.append(Spacer(1, 20))
                self._report_progress(7, 10, "Created daily chart...")

            # Category breakdown table
            if expense_by_category:
                elements.append(Paragraph("Expense Categories Detail", section_style))

                category_data = [['Category', 'Amount', '% of Total']]
                total_exp = sum(expense_by_category.values())

                for cat, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
                    pct = (amount / total_exp * 100) if total_exp > 0 else 0
                    category_data.append([cat, f"${amount:,.2f}", f"{pct:.1f}%"])

                cat_table = Table(category_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
                cat_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
                ]))
                elements.append(cat_table)
                self._report_progress(8, 10, "Created category table...")

            # Budget comparison (if provided)
            if budgets:
                elements.append(PageBreak())
                elements.append(Paragraph("Budget vs Actual", section_style))

                budget_data = [['Category', 'Budgeted', 'Actual', 'Difference', 'Status']]
                for budget in budgets:
                    budgeted = Decimal(str(budget.get('budgeted', 0)))
                    actual = expense_by_category.get(budget.get('category', ''), Decimal('0'))
                    diff = budgeted - actual
                    status = 'Under' if diff >= 0 else 'Over'

                    budget_data.append([
                        budget.get('category', 'Unknown'),
                        f"${budgeted:,.2f}",
                        f"${actual:,.2f}",
                        f"${abs(diff):,.2f}",
                        status
                    ])

                budget_table = Table(budget_data, colWidths=[1.8*inch, 1.1*inch, 1.1*inch, 1.1*inch, 0.8*inch])
                budget_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (3, -1), 'RIGHT'),
                    ('ALIGN', (4, 0), (4, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
                ]))
                elements.append(budget_table)

            self._report_progress(9, 10, "Building PDF...")

            # Build PDF
            doc.build(elements)

            self._report_progress(10, 10, "Monthly report complete!")
            return output_path

        except Exception as e:
            raise ReportError(f"Failed to generate monthly report: {str(e)}") from e

    def generate_yearly_report(
        self,
        transactions: List[Dict[str, Any]],
        year: int,
        output_path: str,
        include_charts: bool = True
    ) -> str:
        """
        Generate a yearly financial report.

        Args:
            transactions: List of all transaction dictionaries
            year: Year (e.g., 2024)
            output_path: Path for the output PDF file
            include_charts: Whether to include visual charts

        Returns:
            Path to the created PDF file

        Raises:
            ReportError: If report generation fails
        """
        if not PDF_AVAILABLE:
            raise ReportError("PDF generation requires reportlab. Install with: pip install reportlab")

        try:
            self._report_progress(0, 10, "Starting yearly report generation...")

            # Calculate date range
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

            # Filter transactions
            filtered = self._filter_transactions_by_date(transactions, start_date, end_date)
            self._report_progress(1, 10, "Filtered transactions...")

            # Calculate statistics
            stats = self._calculate_summary_stats(filtered)
            expense_by_category = self._aggregate_by_category(filtered, 'expense')
            income_by_category = self._aggregate_by_category(filtered, 'income')
            monthly_totals = self._aggregate_by_date(filtered, 'monthly')
            self._report_progress(2, 10, "Calculated statistics...")

            # Calculate monthly breakdown
            monthly_breakdown = {}
            for month in range(1, 13):
                month_start = date(year, month, 1)
                month_end = date(year, month, calendar.monthrange(year, month)[1])
                month_txns = self._filter_transactions_by_date(filtered, month_start, month_end)
                month_stats = self._calculate_summary_stats(month_txns)
                monthly_breakdown[calendar.month_abbr[month]] = {
                    'income': month_stats['total_income'],
                    'expenses': month_stats['total_expenses'],
                    'net': month_stats['net_amount']
                }
            self._report_progress(3, 10, "Calculated monthly breakdown...")

            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch
            )

            styles = getSampleStyleSheet()
            elements = []

            # Styles
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=22,
                alignment=TA_CENTER,
                spaceAfter=10
            )
            subtitle_style = ParagraphStyle(
                'ReportSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.gray
            )
            section_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor('#4472C4')
            )

            # Title page
            elements.append(Paragraph(f"Annual Financial Report", title_style))
            elements.append(Paragraph(f"Year {year}", subtitle_style))
            elements.append(Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                subtitle_style
            ))
            elements.append(Spacer(1, 30))
            self._report_progress(4, 10, "Created header...")

            # Annual Summary
            elements.append(Paragraph("Annual Summary", section_style))

            summary_data = [
                ['Metric', 'Amount'],
                ['Total Income', f"${stats['total_income']:,.2f}"],
                ['Total Expenses', f"${stats['total_expenses']:,.2f}"],
                ['Net Savings', f"${stats['net_amount']:,.2f}"],
                ['Savings Rate', f"{(stats['net_amount'] / stats['total_income'] * 100):.1f}%" if stats['total_income'] > 0 else 'N/A'],
                ['Total Transactions', str(stats['transaction_count'])],
                ['Monthly Avg Income', f"${stats['total_income'] / 12:,.2f}"],
                ['Monthly Avg Expenses', f"${stats['total_expenses'] / 12:,.2f}"],
            ]

            summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))
            self._report_progress(5, 10, "Created summary...")

            # Monthly chart
            if include_charts:
                elements.append(Paragraph("Monthly Overview", section_style))

                monthly_income = {k: v['income'] for k, v in monthly_breakdown.items()}
                monthly_expenses = {k: v['expenses'] for k, v in monthly_breakdown.items()}

                chart_buffer = self._create_matplotlib_chart(
                    monthly_expenses, 'bar', 'Monthly Expenses', (8, 3)
                )
                if chart_buffer:
                    elements.append(Image(chart_buffer, width=6*inch, height=2.5*inch))

                elements.append(Spacer(1, 15))
                self._report_progress(6, 10, "Created monthly chart...")

            # Monthly breakdown table
            elements.append(Paragraph("Monthly Breakdown", section_style))

            monthly_data = [['Month', 'Income', 'Expenses', 'Net']]
            for month, data in monthly_breakdown.items():
                monthly_data.append([
                    month,
                    f"${data['income']:,.2f}",
                    f"${data['expenses']:,.2f}",
                    f"${data['net']:,.2f}"
                ])

            monthly_table = Table(monthly_data, colWidths=[1.2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            monthly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
            ]))
            elements.append(monthly_table)
            self._report_progress(7, 10, "Created monthly table...")

            # Category breakdown
            elements.append(PageBreak())
            elements.append(Paragraph("Expense Categories", section_style))

            if include_charts and expense_by_category:
                chart_buffer = self._create_matplotlib_chart(
                    expense_by_category, 'pie', 'Annual Expenses by Category', (6, 4)
                )
                if chart_buffer:
                    elements.append(Image(chart_buffer, width=5*inch, height=3.3*inch))

                elements.append(Spacer(1, 15))

            if expense_by_category:
                category_data = [['Category', 'Amount', '% of Total', 'Monthly Avg']]
                total_exp = sum(expense_by_category.values())

                for cat, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
                    pct = (amount / total_exp * 100) if total_exp > 0 else 0
                    category_data.append([
                        cat,
                        f"${amount:,.2f}",
                        f"{pct:.1f}%",
                        f"${amount / 12:,.2f}"
                    ])

                cat_table = Table(category_data, colWidths=[2*inch, 1.3*inch, 1*inch, 1.3*inch])
                cat_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
                ]))
                elements.append(cat_table)

            self._report_progress(9, 10, "Building PDF...")

            # Build PDF
            doc.build(elements)

            self._report_progress(10, 10, "Yearly report complete!")
            return output_path

        except Exception as e:
            raise ReportError(f"Failed to generate yearly report: {str(e)}") from e

    def generate_custom_report(
        self,
        transactions: List[Dict[str, Any]],
        start_date: date,
        end_date: date,
        output_path: str,
        title: str = "Custom Financial Report",
        include_charts: bool = True,
        categories: Optional[List[str]] = None
    ) -> str:
        """
        Generate a custom date range financial report.

        Args:
            transactions: List of all transaction dictionaries
            start_date: Start date for the report
            end_date: End date for the report
            output_path: Path for the output PDF file
            title: Custom report title
            include_charts: Whether to include visual charts
            categories: Optional list of categories to filter

        Returns:
            Path to the created PDF file

        Raises:
            ReportError: If report generation fails
        """
        if not PDF_AVAILABLE:
            raise ReportError("PDF generation requires reportlab. Install with: pip install reportlab")

        try:
            self._report_progress(0, 10, "Starting custom report generation...")

            # Filter transactions
            filtered = self._filter_transactions_by_date(transactions, start_date, end_date)

            # Apply category filter if provided
            if categories:
                filtered = [t for t in filtered if t.get('category') in categories]

            self._report_progress(1, 10, "Filtered transactions...")

            # Calculate statistics
            stats = self._calculate_summary_stats(filtered)
            expense_by_category = self._aggregate_by_category(filtered, 'expense')
            income_by_category = self._aggregate_by_category(filtered, 'income')

            # Determine granularity based on date range
            days = (end_date - start_date).days
            if days <= 31:
                granularity = 'daily'
            elif days <= 90:
                granularity = 'weekly'
            else:
                granularity = 'monthly'

            time_totals = self._aggregate_by_date(filtered, granularity)
            self._report_progress(2, 10, "Calculated statistics...")

            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch
            )

            styles = getSampleStyleSheet()
            elements = []

            # Styles
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=20,
                alignment=TA_CENTER,
                spaceAfter=10
            )
            subtitle_style = ParagraphStyle(
                'ReportSubtitle',
                parent=styles['Normal'],
                fontSize=11,
                alignment=TA_CENTER,
                spaceAfter=15,
                textColor=colors.gray
            )
            section_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor('#4472C4')
            )

            # Title
            elements.append(Paragraph(title, title_style))
            elements.append(Paragraph(
                f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}",
                subtitle_style
            ))
            elements.append(Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                subtitle_style
            ))

            if categories:
                elements.append(Paragraph(
                    f"Categories: {', '.join(categories)}",
                    subtitle_style
                ))

            elements.append(Spacer(1, 20))
            self._report_progress(3, 10, "Created header...")

            # Summary Section
            elements.append(Paragraph("Financial Summary", section_style))

            summary_data = [
                ['Metric', 'Amount'],
                ['Total Income', f"${stats['total_income']:,.2f}"],
                ['Total Expenses', f"${stats['total_expenses']:,.2f}"],
                ['Net Amount', f"${stats['net_amount']:,.2f}"],
                ['Transaction Count', str(stats['transaction_count'])],
                ['Period Duration', f"{days} days"],
                ['Daily Avg Income', f"${stats['total_income'] / max(days, 1):,.2f}"],
                ['Daily Avg Expenses', f"${stats['total_expenses'] / max(days, 1):,.2f}"],
            ]

            summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))
            self._report_progress(4, 10, "Created summary...")

            # Charts
            if include_charts:
                # Expense pie chart
                if expense_by_category:
                    elements.append(Paragraph("Expense Breakdown", section_style))
                    chart_buffer = self._create_matplotlib_chart(
                        expense_by_category, 'pie', 'Expenses by Category', (6, 4)
                    )
                    if chart_buffer:
                        elements.append(Image(chart_buffer, width=5*inch, height=3.3*inch))
                    elements.append(Spacer(1, 15))
                    self._report_progress(5, 10, "Created expense chart...")

                # Time-based chart
                if time_totals:
                    chart_title = f"{'Daily' if granularity == 'daily' else 'Weekly' if granularity == 'weekly' else 'Monthly'} Totals"
                    elements.append(Paragraph(chart_title, section_style))
                    chart_buffer = self._create_matplotlib_chart(
                        time_totals, 'bar', chart_title, (8, 3)
                    )
                    if chart_buffer:
                        elements.append(Image(chart_buffer, width=6*inch, height=2.5*inch))
                    elements.append(Spacer(1, 15))
                    self._report_progress(6, 10, "Created time chart...")

            # Category details
            if expense_by_category:
                elements.append(Paragraph("Category Details", section_style))

                category_data = [['Category', 'Amount', '% of Total']]
                total_exp = sum(expense_by_category.values())

                for cat, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
                    pct = (amount / total_exp * 100) if total_exp > 0 else 0
                    category_data.append([cat, f"${amount:,.2f}", f"{pct:.1f}%"])

                cat_table = Table(category_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
                cat_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
                ]))
                elements.append(cat_table)

            self._report_progress(8, 10, "Building PDF...")

            # Build PDF
            doc.build(elements)

            self._report_progress(10, 10, "Custom report complete!")
            return output_path

        except Exception as e:
            raise ReportError(f"Failed to generate custom report: {str(e)}") from e

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_available_features(self) -> Dict[str, bool]:
        """
        Get dictionary of available report features.

        Returns:
            Dictionary with feature names as keys and availability as values
        """
        return {
            'pdf_reports': PDF_AVAILABLE,
            'pandas_analysis': PANDAS_AVAILABLE,
            'matplotlib_charts': MATPLOTLIB_AVAILABLE,
            'basic_charts': PDF_AVAILABLE,  # ReportLab charts always available with PDF
        }

    def generate_report_data(
        self,
        transactions: List[Dict[str, Any]],
        start_date: date,
        end_date: date,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate report data without creating a PDF.

        Useful for displaying in UI or exporting to other formats.

        Args:
            transactions: List of transaction dictionaries
            start_date: Start date for the report
            end_date: End date for the report
            categories: Optional list of categories to filter

        Returns:
            Dictionary containing all report data
        """
        # Filter transactions
        filtered = self._filter_transactions_by_date(transactions, start_date, end_date)

        if categories:
            filtered = [t for t in filtered if t.get('category') in categories]

        # Calculate all statistics
        stats = self._calculate_summary_stats(filtered)
        expense_by_category = self._aggregate_by_category(filtered, 'expense')
        income_by_category = self._aggregate_by_category(filtered, 'income')

        # Determine granularity
        days = (end_date - start_date).days
        if days <= 31:
            granularity = 'daily'
        elif days <= 90:
            granularity = 'weekly'
        else:
            granularity = 'monthly'

        time_totals = self._aggregate_by_date(filtered, granularity)

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'summary': {
                'total_income': float(stats['total_income']),
                'total_expenses': float(stats['total_expenses']),
                'net_amount': float(stats['net_amount']),
                'transaction_count': stats['transaction_count'],
                'average_transaction': float(stats['average_transaction']),
                'largest_expense': float(stats['largest_expense']),
                'largest_income': float(stats['largest_income']),
            },
            'expense_by_category': {k: float(v) for k, v in expense_by_category.items()},
            'income_by_category': {k: float(v) for k, v in income_by_category.items()},
            'time_series': {
                'granularity': granularity,
                'data': {k: float(v) for k, v in time_totals.items()}
            },
            'transactions': filtered
        }
