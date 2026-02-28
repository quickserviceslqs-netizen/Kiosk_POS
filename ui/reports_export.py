"""Export manager for handling report exports."""

from typing import Dict, List, Any, Optional, Callable
import csv
import logging
from datetime import datetime

from utils.date_utils import format_date
# ReportData and CSVReportFormatter imported lazily in functions to avoid circular imports
from .reports_constants import FILE_EXTENSIONS, REPORT_LIMITS

logger = logging.getLogger(__name__)


class ExportManager:
    """Manager for exporting reports to various formats."""

    def __init__(self):
        self.formatters = self._initialize_formatters()

    def _initialize_formatters(self) -> Dict[str, Callable]:
        """Initialize export formatters."""
        return {
            'csv': self._export_csv,
            'txt': self._export_text,
            'xlsx': self._export_excel,
            'pdf': self._export_pdf
        }

    def export_report(self, report_data, file_path: str,
                     format_type: Optional[str] = None) -> bool:
        from .reports_base import ReportData  # local to avoid circular import
        """Export a report to the specified file."""
        try:
            # Determine format from file extension if not specified
            if not format_type:
                if file_path.lower().endswith(FILE_EXTENSIONS['csv']):
                    format_type = 'csv'
                elif file_path.lower().endswith(FILE_EXTENSIONS['txt']):
                    format_type = 'txt'
                elif file_path.lower().endswith(('.xlsx', '.xls')):
                    format_type = 'xlsx'
                elif file_path.lower().endswith('.pdf'):
                    format_type = 'pdf'
                else:
                    format_type = 'csv'  # Default to CSV

            if format_type not in self.formatters:
                logger.error(f"Unsupported export format: {format_type}")
                return False

            formatter = self.formatters[format_type]
            return formatter(report_data, file_path)

        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return False

    def _export_csv(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData, CSVReportFormatter
        """Export report as CSV."""
        try:
            formatter = self._get_csv_formatter(report_data)
            if formatter:
                rows = formatter.get_csv_rows()
            else:
                # fallback: simple header + values from report_data.data
                data = report_data.data or []
                if not data:
                    return False
                cols = list(data[0].keys())
                rows = [cols]
                for r in data:
                    rows.append([r.get(c) for c in cols])

            if not rows:
                return False

            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(rows)

            return True

        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return False

    def _export_text(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData
        """Export report as formatted text."""
        try:
            formatter = report_data.get_formatter(report_data)
            content = formatter.format_report()

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        except Exception as e:
            logger.error(f"Error exporting text: {e}")
            return False

    def _get_csv_formatter(self, report_data, ) -> Optional['CSVReportFormatter']:
        from .reports_base import CSVReportFormatter
        """Get the appropriate CSV formatter for the report type."""
        # Import here to avoid circular imports
        from .reports_csv_formatters import (
            SalesCSVFormatter, ProfitCSVFormatter, CategoryCSVFormatter,
            PaymentMethodsCSVFormatter, VoidedSalesCSVFormatter,
            ReconciliationCSVFormatter, InventoryStockLevelsCSVFormatter,
            InventoryLowStockCSVFormatter, InventoryValueCSVFormatter
        )

        formatters = {
            'daily': SalesCSVFormatter,
            'range': SalesCSVFormatter,
            'bestsellers': SalesCSVFormatter,
            'profit': ProfitCSVFormatter,
            'category': CategoryCSVFormatter,
            'payment_methods': PaymentMethodsCSVFormatter,
            'voided': VoidedSalesCSVFormatter,
            'sales_log': SalesCSVFormatter,
            'transactions': SalesCSVFormatter,
            'trends': SalesCSVFormatter,
            'reconciliation_summary': ReconciliationCSVFormatter,
            'reconciliation_details': ReconciliationCSVFormatter,
            'inventory_stock_levels': InventoryStockLevelsCSVFormatter,
            'inventory_low_stock': InventoryLowStockCSVFormatter,
            'inventory_value': InventoryValueCSVFormatter,
        }

        formatter_class = formatters.get(report_data.report_type)
        if formatter_class:
            return formatter_class(report_data)

        return None

    def export_report_streaming(self, report_type: str, start_date: str, end_date: str,
                                file_path: str, format_type: str = 'csv', page_size: int = 1000,
                                use_keyset: bool = False, status_filter: str = 'all') -> bool:
        """Stream a large report directly to disk in CSV format without materializing the full dataset.

        Currently supports 'sales_log' and 'reconciliation_details' (others will fall back to full export).
        """
        try:
            # Only CSV supported for streaming
            if format_type != 'csv':
                logger.error('Streaming export currently only supports CSV')
                return False

            from .reports_controller import ReportController as ReportService
            service = ReportService()

            # Open file and write rows per page
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Sales log streaming
                if report_type == 'sales_log':
                    # write header
                    writer.writerow(['transaction_id', 'receipt_number', 'date', 'time', 'amount', 'payment_method', 'items_summary'])
                    cursor = None
                    while True:
                        rows, next_cursor, meta = service.generate_report_page('sales_log', start_date, end_date, page_size=page_size, cursor=cursor, use_keyset=use_keyset)
                        if not rows:
                            break
                        for r in rows:
                            writer.writerow([r.get('transaction_id'), r.get('receipt_number'), format_date(r.get('date')), r.get('time'), r.get('amount'), r.get('payment_method'), r.get('items_summary')])
                        if not next_cursor:
                            break
                        cursor = next_cursor
                    return True

                # Reconciliation details streaming
                if report_type == 'reconciliation_details':
                    writer.writerow(['session_id', 'reconciliation_date', 'status', 'total_system_sales', 'total_actual_cash', 'total_variance'])
                    cursor = None
                    while True:
                        rows, next_cursor, meta = service.generate_report_page('reconciliation_details', start_date, end_date, page_size=page_size, cursor=cursor, use_keyset=use_keyset)
                        if not rows:
                            break
                        for r in rows:
                            # r may be dict or object
                            if isinstance(r, dict):
                                writer.writerow([r.get('session_id'), format_date(r.get('reconciliation_date')), r.get('status'), r.get('total_system_sales'), r.get('total_actual_cash'), r.get('total_variance')])
                            else:
                                writer.writerow([r.session_id, format_date(r.reconciliation_date), r.status, r.total_system_sales, r.total_actual_cash, r.total_variance])
                        if not next_cursor:
                            break
                        cursor = next_cursor
                    return True

                # Inventory stock levels streaming
                if report_type == 'inventory_stock_levels':
                    writer.writerow(['item_id', 'name', 'category', 'quantity', 'unit', 'inventory_value', 'is_low_stock'])
                    cursor = None
                    while True:
                        rows, next_cursor, meta = service.generate_report_page('inventory_stock_levels', start_date, end_date, page_size=page_size, cursor=cursor, use_keyset=use_keyset)
                        if not rows:
                            break
                        for r in rows:
                            # row expected to be dict
                            writer.writerow([r.get('item_id'), r.get('name'), r.get('category'), r.get('quantity'), r.get('unit'), r.get('inventory_value'), r.get('is_low_stock')])
                        if not next_cursor:
                            break
                        cursor = next_cursor
                    return True

            # Fallback: unsupported report types - return False
            logger.error(f"Streaming not implemented for report type: {report_type}")
            return False

        except Exception as e:
            logger.error(f"Error streaming export: {e}")
            return False

    def _export_excel(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData
        """Export report as Excel file."""
        try:
            import pandas as pd

            # Get CSV data
            formatter = self._get_csv_formatter(report_data)
            if not formatter:
                return False

            csv_rows = formatter.get_csv_rows()
            if not csv_rows:
                return False

            # Convert to DataFrame
            df = pd.DataFrame(csv_rows[1:], columns=csv_rows[0])  # First row is headers

            # Export to Excel
            df.to_excel(file_path, index=False, engine='openpyxl')

            return True

        except ImportError:
            logger.error("pandas and openpyxl required for Excel export")
            return False
        except Exception as e:
            logger.error(f"Error exporting Excel: {e}")
            return False

    def _export_pdf(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData
        """Export report as PDF file."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch

            # Get CSV data
            formatter = self._get_csv_formatter(report_data)
            if not formatter:
                return False

            csv_rows = formatter.get_csv_rows()
            if not csv_rows:
                return False

            # Create PDF document
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []

            # Add title
            title = Paragraph(f"{report_data.report_type.replace('_', ' ').title()} Report", styles['Heading1'])
            elements.append(title)
            elements.append(Spacer(1, 12))

            # Add date range
            date_info = Paragraph(f"Period: {report_data.start_date} to {report_data.end_date}", styles['Normal'])
            elements.append(date_info)
            elements.append(Spacer(1, 12))

            # Create table
            table_data = csv_rows
            table = Table(table_data)

            # Style the table
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])
            table.setStyle(style)

            elements.append(table)

            # Build PDF
            doc.build(elements)

            return True

        except ImportError:
            logger.error("reportlab required for PDF export")
            return False
        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            return False