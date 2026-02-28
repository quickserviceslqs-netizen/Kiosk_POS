"""Text formatters for sales reports."""

from typing import Dict, List, Any
from utils.date_utils import format_date
from .reports_base import TextReportFormatter


class SalesTextFormatter(TextReportFormatter):
    """Base formatter for sales reports."""

    def format_body(self) -> str:
        """Format the main sales report content."""
        if self.report_data.is_empty:
            return "No sales data found for this period.\n"

        metadata = self.report_data.metadata
        output = ""

        # Summary statistics
        if 'total_sales' in metadata:
            output += "SUMMARY:\n"
            output += "-" * 20 + "\n"
            output += f"Total Sales: {self._format_currency(metadata['total_sales'])}\n"
            output += f"Total Items Sold: {metadata['total_items']}\n"
            output += f"Number of Transactions: {metadata['unique_transactions']}\n\n"

        # Top items
        if 'top_items' in metadata and metadata['top_items']:
            output += "TOP ITEMS SOLD:\n"
            output += "-" * 30 + "\n"
            header = f"{'#':<3} {'Item Name':<25} {'Qty':<8} {'Total':<12}"
            output += header + "\n"
            output += "-" * len(header) + "\n"

            for i, item in enumerate(metadata['top_items'], 1):
                name = item['name'][:24] if len(item['name']) > 24 else item['name']
                qty = item['quantity']
                total = item['total']
                line = f"{i:<3} {name:<25} {qty:<8} {self._format_currency(total):<12}"
                output += line + "\n"
        else:
            output += "No item details available.\n"

        return output


class ProfitTextFormatter(TextReportFormatter):
    """Formatter for profit analysis reports."""

    def _get_report_title(self) -> str:
        return "PROFIT ANALYSIS REPORT"

    def format_body(self) -> str:
        """Format profit analysis content."""
        analysis = self.report_data.metadata.get('analysis', {})

        if not analysis:
            return "No profit data found for this period.\n"

        output = "REVENUE SUMMARY:\n"
        output += "-" * 20 + "\n"
        output += f"Total Revenue: {self._format_currency(analysis.get('total_revenue', 0))}\n"
        output += f"Total Cost: {self._format_currency(analysis.get('total_cost', 0))}\n"
        output += f"Gross Profit: {self._format_currency(analysis.get('gross_profit', 0))}\n"
        output += f"Profit Margin: {analysis.get('profit_margin', 0):.1f}%\n\n"

        # Top profitable items
        profitable_items = analysis.get('profitable_items', [])
        if profitable_items:
            output += "TOP PROFITABLE ITEMS:\n"
            output += "-" * 25 + "\n"
            header = f"{'#':<3} {'Item':<20} {'Profit':<12}"
            output += header + "\n"
            output += "-" * len(header) + "\n"
            for i, item in enumerate(profitable_items[:10], 1):
                name = item.get('name', '')[:19]
                profit = item.get('profit', 0)
                line = f"{i:<3} {name:<20} {self._format_currency(profit):<12}"
                output += line + "\n"
        else:
            output += "No profit data available.\n"

        return output


class CategoryTextFormatter(TextReportFormatter):
    """Formatter for category sales reports."""

    def _get_report_title(self) -> str:
        return "SALES BY CATEGORY REPORT"

    def format_body(self) -> str:
        """Format category sales content."""
        if self.report_data.is_empty:
            return "No category sales data found for this period.\n"

        metadata = self.report_data.metadata
        total_revenue = metadata.get('total_revenue', 0)

        output = f"Total Revenue: {self._format_currency(total_revenue)}\n"
        output += f"Total Items Sold: {metadata.get('total_quantity', 0)}\n\n"

        header = f"{'Category':<20} {'Revenue':<12} {'Quantity':<10} {'% of Total':<12}"
        output += header + "\n"
        output += "-" * len(header) + "\n"

        for item in sorted(self.report_data.data, key=lambda x: x['total_revenue'], reverse=True):
            category = item['category'] or 'Uncategorized'
            revenue = item['total_revenue']
            quantity = item['total_quantity']
            percentage = self._format_percentage(revenue, total_revenue)
            line = f"{category[:19]:<20} {self._format_currency(revenue):<12} {quantity:<10} {percentage:<12}"
            output += line + "\n"

        return output


class PaymentMethodsTextFormatter(TextReportFormatter):
    """Formatter for payment methods reports."""

    def _get_report_title(self) -> str:
        return "PAYMENT METHODS REPORT"

    def format_body(self) -> str:
        """Format payment methods content."""
        if self.report_data.is_empty:
            return "No payment method data found for this period.\n"

        metadata = self.report_data.metadata
        total_revenue = metadata.get('total_revenue', 0)

        output = f"Total Revenue: {self._format_currency(total_revenue)}\n"
        output += f"Total Transactions: {metadata.get('total_transactions', 0)}\n\n"

        header = f"{'Method':<15} {'Amount':<12} {'Count':<8} {'Avg':<10} {'% of Total':<12}"
        output += header + "\n"
        output += "-" * len(header) + "\n"

        for item in sorted(self.report_data.data, key=lambda x: x['total_sales'], reverse=True):
            method = item['payment_method']
            amount = item['total_sales']
            count = item['transaction_count']
            avg_transaction = amount / count if count > 0 else 0
            percentage = self._format_percentage(amount, total_revenue)
            line = f"{method[:14]:<15} {self._format_currency(amount):<12} {count:<8} {self._format_currency(avg_transaction):<10} {percentage:<12}"
            output += line + "\n"

        return output


class VoidedSalesTextFormatter(TextReportFormatter):
    """Formatter for voided sales reports."""

    def _get_report_title(self) -> str:
        return "VOIDED SALES REPORT"

    def format_body(self) -> str:
        """Format voided sales content."""
        if self.report_data.is_empty:
            return "No voided sales found for this period.\n"

        metadata = self.report_data.metadata

        output = f"Total Voided Amount: {self._format_currency(metadata.get('total_voided', 0))}\n"
        output += f"Total Voided Items: {metadata.get('total_items', 0)}\n"
        output += f"Number of Voided Transactions: {metadata.get('transaction_count', 0)}\n\n"

        output += "VOIDED SALES:\n"
        output += "-" * 70 + "\n"
        header = f"{'Receipt':<12} {'Date':<12} {'Time':<10} {'Items':<8} {'Total':<12} {'Reason':<15}"
        output += header + "\n"
        output += "-" * len(header) + "\n"

        for item in self.report_data.data:
            receipt = item['receipt_number'][:11] if item.get('receipt_number') else 'N/A'
            date = item['date']
            time = item['time'][:9] if item.get('time') else ''
            item_count = item['item_count']
            total = item['total']
            reason = item.get('void_reason', 'N/A')[:14]
            line = f"{receipt:<12} {date:<12} {time:<10} {item_count:<8} {self._format_currency(total):<12} {reason:<15}"
            output += line + "\n"

        return output


class SalesLogTextFormatter(TextReportFormatter):
    """Formatter for sales log reports."""

    def _get_report_title(self) -> str:
        return "SALES LOG REPORT"

    def format_body(self) -> str:
        """Format sales log content."""
        if self.report_data.is_empty:
            return "No sales transactions found for this period.\n"

        metadata = self.report_data.metadata

        output = f"Total Transactions: {metadata.get('transaction_count', 0)}\n"
        output += f"Total Line Items: {metadata.get('line_items', 0)}\n"
        output += f"Total Revenue: {self._format_currency(metadata.get('total_revenue', 0))}\n\n"

        output += "TRANSACTION DETAILS:\n"
        output += "-" * 80 + "\n"
        header = f"{'Time':<19} {'Receipt':<10} {'Method':<12} {'Items':<6} {'Total':<12}"
        output += header + "\n"
        output += "-" * len(header) + "\n"

        # Group by receipt for display
        from collections import defaultdict
        receipts = defaultdict(list)
        for item in self.report_data.data:
            receipts[item['receipt_number']].append(item)

        for receipt, items in list(receipts.items())[:50]:  # Limit display
            transaction_total = sum(item['total'] for item in items)
            item_count = len(items)
            payment_method = items[0]['payment_method'] or 'N/A'
            timestamp = f"{format_date(items[0]['date'])} {items[0]['time']}"[:19]
            receipt_display = receipt or 'N/A'
            line = f"{timestamp:<19} {receipt_display:<10} {payment_method:<12} {item_count:<6} {self._format_currency(transaction_total):<12}"
            output += line + "\n"

        if len(receipts) > 50:
            output += f"\n... and {len(receipts) - 50} more transactions\n"

        return output


class TransactionsTextFormatter(TextReportFormatter):
    """Formatter for detailed transactions reports."""

    def _get_report_title(self) -> str:
        return "TRANSACTIONS REPORT"

    def format_body(self) -> str:
        """Format transactions content."""
        if self.report_data.is_empty:
            return "No transaction data found for this period.\n"

        metadata = self.report_data.metadata

        output = f"Total Transactions: {metadata.get('transaction_count', 0)}\n"
        output += f"Total Revenue: {self._format_currency(metadata.get('total_revenue', 0))}\n\n"

        # Group by receipt for summary
        from collections import defaultdict
        receipts = defaultdict(list)
        for item in self.report_data.data:
            receipts[item['receipt_number']].append(item)

        output += "TRANSACTION SUMMARY:\n"
        output += "-" * 90 + "\n"
        header = f"{'Time':<19} {'Receipt':<10} {'Method':<12} {'Items':<6} {'Total':<12}"
        output += header + "\n"
        output += "-" * len(header) + "\n"

        total_revenue = 0
        for receipt, items in list(receipts.items())[:50]:
            transaction_total = sum(item['total'] for item in items)
            item_count = len(items)
            payment_method = items[0]['payment_method'] or 'N/A'
            timestamp = f"{items[0]['date']} {items[0]['time']}"[:19]
            total_revenue += transaction_total
            receipt_display = receipt or 'N/A'
            line = f"{timestamp:<19} {receipt_display:<10} {payment_method:<12} {item_count:<6} {self._format_currency(transaction_total):<12}"
            output += line + "\n"

        if len(receipts) > 50:
            output += f"\n... and {len(receipts) - 50} more transactions\n"

        output += "-" * 90 + "\n"
        output += f"{'TOTAL REVENUE':<15} {self._format_currency(total_revenue)}\n\n"

        # Payment method breakdown
        payment_breakdown = metadata.get('payment_breakdown', {})
        if payment_breakdown:
            output += "PAYMENT METHOD BREAKDOWN:\n"
            output += "-" * 30 + "\n"
            header = f"{'Method':<15} {'Amount':<12} {'% of Total':<12}"
            output += header + "\n"
            output += "-" * len(header) + "\n"
            for method, total in sorted(payment_breakdown.items(), key=lambda x: x[1], reverse=True):
                method_display = method or 'N/A'
                percentage = self._format_percentage(total, total_revenue)
                line = f"{method_display[:14]:<15} {self._format_currency(total):<12} {percentage:<12}"
                output += line + "\n"

        return output


class TrendsTextFormatter(TextReportFormatter):
    """Formatter for sales trends reports."""

    def _get_report_title(self) -> str:
        return "SALES TRENDS REPORT"

    def format_body(self) -> str:
        """Format trends content."""
        if self.report_data.is_empty:
            return "No trends data found for this period.\n"

        metadata = self.report_data.metadata
        group_by = metadata.get('group_by', 'day')

        output = f"Grouped by: {group_by.title()}\n\n"

        header = f"{'Period':<12} {'Revenue':<12} {'Transactions':<12}"
        output += header + "\n"
        output += "-" * len(header) + "\n"

        for item in self.report_data.data:
            period = item['period']
            revenue = item['total_sales']
            transactions = item['transactions']
            line = f"{period:<12} {self._format_currency(revenue):<12} {transactions:<12}"
            output += line + "\n"

        return output