"""CSV formatters for reports."""

from typing import List, Any
from utils.date_utils import format_date
from .reports_base import CSVReportFormatter


def _fmt_date(val) -> str:
    """Format a date or datetime value from DB using the system date format."""
    if not val:
        return ''
    try:
        s = str(val)
        parts = s.split(' ', 1)
        formatted = format_date(parts[0])
        return f"{formatted} {parts[1]}" if len(parts) > 1 else formatted
    except Exception:
        return str(val)


class SalesCSVFormatter(CSVReportFormatter):
    """CSV formatter for sales reports."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for sales data."""
        rows = []

        # Header
        rows.append(['Receipt Number', 'Item Name', 'Quantity', 'Price', 'Total', 'Timestamp'])

        # Data rows (limit to export limit)
        for item in self.report_data.data[:self.report_data.metadata.get('export_limit', 1000)]:
            rows.append([
                item.get('receipt_number', ''),
                item.get('item_name', ''),
                item.get('quantity', 0),
                item.get('price', 0),
                item.get('total', 0),
                _fmt_date(item.get('timestamp', ''))
            ])

        return rows


class ProfitCSVFormatter(CSVReportFormatter):
    """CSV formatter for profit analysis."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for profit data."""
        rows = []

        # Header
        rows.append(['Metric', 'Value'])

        # Data from analysis
        analysis = self.report_data.metadata.get('analysis', {})
        if analysis:
            rows.extend([
                ['Total Revenue', analysis.get('total_revenue', 0)],
                ['Total Cost', analysis.get('total_cost', 0)],
                ['Gross Profit', analysis.get('gross_profit', 0)],
                ['Profit Margin', f"{analysis.get('profit_margin', 0):.1f}%"]
            ])

            # Profitable items
            profitable_items = analysis.get('profitable_items', [])
            if profitable_items:
                rows.append([])  # Empty row
                rows.append(['Top Profitable Items'])
                rows.append(['Item Name', 'Profit'])
                for item in profitable_items[:20]:
                    rows.append([item.get('item_name', ''), item.get('profit', 0)])

        return rows


class CategoryCSVFormatter(CSVReportFormatter):
    """CSV formatter for category sales."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for category data."""
        rows = []

        # Header
        rows.append(['Category', 'Total Revenue', 'Total Quantity', 'Percentage'])

        # Data rows
        total_revenue = self.report_data.metadata.get('total_revenue', 0)
        for item in sorted(self.report_data.data, key=lambda x: x['total_revenue'], reverse=True):
            category = item['category'] or 'Uncategorized'
            revenue = item['total_revenue']
            quantity = item['total_quantity']
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0

            rows.append([
                category,
                revenue,
                quantity,
                f"{percentage:.1f}%"
            ])

        return rows


class PaymentMethodsCSVFormatter(CSVReportFormatter):
    """CSV formatter for payment methods."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for payment methods data."""
        rows = []

        # Header
        rows.append(['Payment Method', 'Total Amount', 'Transaction Count', 'Average Transaction'])

        # Data rows
        for item in sorted(self.report_data.data, key=lambda x: x['total_amount'], reverse=True):
            amount = item['total_amount']
            count = item['transaction_count']
            avg_transaction = amount / count if count > 0 else 0

            rows.append([
                item['payment_method'],
                amount,
                count,
                avg_transaction
            ])

        return rows


class VoidedSalesCSVFormatter(CSVReportFormatter):
    """CSV formatter for voided sales."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for voided sales data."""
        rows = []

        # Header
        rows.append(['Item Name', 'Quantity', 'Total', 'Void Reason', 'Timestamp'])

        # Data rows
        for item in self.report_data.data:
            rows.append([
                item.get('item_name', ''),
                item.get('quantity', 0),
                item.get('total', 0),
                item.get('void_reason', 'N/A'),
                _fmt_date(item.get('timestamp', ''))
            ])

        return rows


class ReconciliationCSVFormatter(CSVReportFormatter):
    """CSV formatter for reconciliation reports."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for reconciliation data."""
        rows = []

        if self.report_data.report_type == 'reconciliation_summary':
            # Summary format
            rows.append(['Status', 'Session Count'])
            status_counts = self.report_data.metadata.get('status_counts', {})
            for status, count in status_counts.items():
                rows.append([status.title(), count])

            rows.append([])  # Empty row
            rows.append(['Metric', 'Amount'])
            rows.extend([
                ['Total System Amount', self.report_data.metadata.get('total_system', 0)],
                ['Total Actual Amount', self.report_data.metadata.get('total_actual', 0)],
                ['Total Variance', self.report_data.metadata.get('total_variance', 0)]
            ])

        else:
            # Details format
            rows.append(['Session ID', 'Date', 'Status', 'System Amount', 'Actual Amount', 'Variance'])

            for session in self.report_data.data:
                date = format_date(session.created_at.date()) if hasattr(session, 'created_at') and session.created_at else 'N/A'
                rows.append([
                    session.id if hasattr(session, 'id') else 'N/A',
                    date,
                    session.status.title(),
                    session.total_system_amount or 0,
                    session.total_actual_amount or 0,
                    session.total_variance or 0
                ])

        return rows


class POSummaryCSVFormatter(CSVReportFormatter):
    """CSV formatter for Purchase Order Summary."""

    def get_csv_rows(self) -> List[List[Any]]:
        rows = [['PO Number', 'Supplier', 'Status', 'Created Date', 'Created By', 'Items', 'Total Amount', 'Notes']]
        for po in self.report_data.data:
            rows.append([
                po.get('po_number', ''),
                po.get('supplier', ''),
                po.get('status', ''),
                _fmt_date(po.get('created_date', '')),
                po.get('created_by', ''),
                po.get('item_count', 0),
                po.get('total_amount', 0),
                po.get('notes', ''),
            ])
        return rows


class POBySupplierCSVFormatter(CSVReportFormatter):
    """CSV formatter for PO spending by supplier."""

    def get_csv_rows(self) -> List[List[Any]]:
        rows = [['Supplier', 'PO Count', 'Total Spent', 'Avg Order Value', 'Last Order Date', 'Received', 'Pending']]
        for row in self.report_data.data:
            rows.append([
                row.get('supplier', ''),
                row.get('po_count', 0),
                row.get('total_spent', 0),
                row.get('avg_order_value', 0),
                _fmt_date(row.get('last_order_date', '')),
                row.get('received_count', 0),
                row.get('pending_count', 0),
            ])
        return rows


class POItemsDetailCSVFormatter(CSVReportFormatter):
    """CSV formatter for detailed PO line items."""

    def get_csv_rows(self) -> List[List[Any]]:
        rows = [['PO Number', 'Supplier', 'Status', 'Created Date', 'Item Name', 'Qty Ordered', 'Qty Received', 'Unit Cost', 'Line Total']]
        for item in self.report_data.data:
            rows.append([
                item.get('po_number', ''),
                item.get('supplier', ''),
                item.get('status', ''),
                _fmt_date(item.get('created_date', '')),
                item.get('item_name', ''),
                item.get('quantity_ordered', 0),
                item.get('quantity_received', 0),
                item.get('unit_cost', 0),
                item.get('line_total', 0),
            ])
        return rows


class InventoryStockLevelsCSVFormatter(CSVReportFormatter):
    """CSV formatter for inventory stock levels report."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for inventory stock levels data."""
        rows = []

        # Header
        rows.append(['Item ID', 'Name', 'Category', 'Quantity', 'Unit', 'Cost Price', 'Selling Price', 'Inventory Value', 'Low Stock'])

        # Data rows
        for item in self.report_data.data:
            inventory_value = item.get('quantity', 0) * item.get('cost_price', 0)
            rows.append([
                item.get('item_id', ''),
                item.get('name', ''),
                item.get('category', ''),
                item.get('quantity', 0),
                item.get('unit', ''),
                item.get('cost_price', 0),
                item.get('selling_price', 0),
                inventory_value,
                'Yes' if item.get('is_low_stock', False) else 'No'
            ])

        return rows


class InventoryLowStockCSVFormatter(CSVReportFormatter):
    """CSV formatter for low stock items report."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for low stock items data."""
        rows = []

        # Header
        rows.append(['Item ID', 'Name', 'Category', 'Current Quantity', 'Low Stock Threshold', 'Status'])

        # Data rows
        for item in self.report_data.data:
            status = 'LOW STOCK' if item.get('quantity', 0) <= item.get('low_stock_threshold', 0) else 'OK'
            rows.append([
                item.get('item_id', ''),
                item.get('name', ''),
                item.get('category', ''),
                item.get('quantity', 0),
                item.get('low_stock_threshold', 0),
                status
            ])

        return rows


class InventoryValueCSVFormatter(CSVReportFormatter):
    """CSV formatter for inventory value analysis report."""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows for inventory value data."""
        rows = []

        # Header
        rows.append(['Category', 'Item Count', 'Total Quantity', 'Total Value', 'Average Value per Item'])

        # Data rows
        for category in self.report_data.data:
            rows.append([
                category.get('category', ''),
                category.get('item_count', 0),
                category.get('total_quantity', 0),
                category.get('total_value', 0),
                category.get('avg_value', 0)
            ])

        return rows