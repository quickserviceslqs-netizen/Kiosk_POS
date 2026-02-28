"""Specific report generators for different report types."""

from typing import Dict, List, Any, Optional
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from .reports_base import ReportGenerator, ReportData, TextReportFormatter, CSVReportFormatter
from .reports_formatters import (
    SalesTextFormatter, ProfitTextFormatter, CategoryTextFormatter,
    PaymentMethodsTextFormatter, VoidedSalesTextFormatter, SalesLogTextFormatter,
    TransactionsTextFormatter, TrendsTextFormatter
)
from .reports_constants import REPORT_LIMITS
from modules import reports

logger = logging.getLogger(__name__)


class SalesReportGenerator(ReportGenerator):
    """Base class for sales-related report generators."""

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get text formatter for sales reports."""
        return SalesTextFormatter(report_data)


class DailySalesGenerator(SalesReportGenerator):
    """Generator for daily sales reports."""

    def generate_data(self) -> ReportData:
        """Generate daily sales data."""
        data = reports.get_daily_sales(self.start_date)

        # Calculate summary statistics
        if data:
            total_sales = sum(item['total'] for item in data)
            total_items = sum(item['quantity'] for item in data)
            unique_transactions = len(set(item['receipt_number'] for item in data))

            # Group by item for top sellers
            item_totals = defaultdict(float)
            item_quantities = defaultdict(int)

            for item in data:
                item_totals[item['item_name']] += item['total']
                item_quantities[item['item_name']] += item['quantity']

            top_items = sorted(item_totals.items(), key=lambda x: x[1], reverse=True)[:10]

            metadata = {
                'total_sales': total_sales,
                'total_items': total_items,
                'unique_transactions': unique_transactions,
                'top_items': [{'name': name, 'total': total, 'quantity': item_quantities[name]}
                            for name, total in top_items]
            }
        else:
            metadata = {}

        return ReportData('daily', self.start_date, self.end_date, data, metadata)


class DateRangeSalesGenerator(SalesReportGenerator):
    """Generator for date range sales reports."""

    def generate_data(self) -> ReportData:
        """Generate date range sales data."""
        data = reports.get_detailed_sales_transactions(self.start_date, self.end_date)

        if data:
            total_sales = sum(item['total'] for item in data)
            total_items = sum(item['quantity'] for item in data)
            unique_transactions = len(set(item['receipt_number'] for item in data))

            # Group by item for top sellers
            item_totals = defaultdict(float)
            item_quantities = defaultdict(int)

            for item in data:
                item_totals[item['item_name']] += item['total']
                item_quantities[item['item_name']] += item['quantity']

            top_items = sorted(item_totals.items(), key=lambda x: x[1], reverse=True)[:20]

            metadata = {
                'total_sales': total_sales,
                'total_items': total_items,
                'unique_transactions': unique_transactions,
                'top_items': [{'name': name, 'total': total, 'quantity': item_quantities[name]}
                            for name, total in top_items]
            }
        else:
            metadata = {}

        return ReportData('range', self.start_date, self.end_date, data, metadata)


class BestSellersGenerator(SalesReportGenerator):
    """Generator for best sellers reports."""

    def generate_data(self) -> ReportData:
        """Generate best sellers data."""
        data = reports.get_best_selling_items(self.start_date, self.end_date,
                                            limit=REPORT_LIMITS['bestsellers'])

        if data:
            total_revenue = sum(item['revenue'] for item in data)
            total_quantity = sum(item['total_sold_raw'] for item in data)

            metadata = {
                'total_revenue': total_revenue,
                'total_quantity': total_quantity,
                'item_count': len(data)
            }
        else:
            metadata = {}

        return ReportData('bestsellers', self.start_date, self.end_date, data, metadata)


class ProfitAnalysisGenerator(ReportGenerator):
    """Generator for profit analysis reports."""

    def generate_data(self) -> ReportData:
        """Generate profit analysis data."""
        data = reports.get_profit_analysis(self.start_date, self.end_date)

        return ReportData('profit', self.start_date, self.end_date, [], {'analysis': data})

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get profit analysis formatter."""
        return ProfitTextFormatter(report_data)


class CategorySalesGenerator(ReportGenerator):
    """Generator for category sales reports."""

    def generate_data(self) -> ReportData:
        """Generate category sales data."""
        data = reports.get_category_sales(self.start_date, self.end_date)

        if data:
            total_revenue = sum(item['total_revenue'] for item in data)
            total_quantity = sum(item['total_quantity'] for item in data)

            metadata = {
                'total_revenue': total_revenue,
                'total_quantity': total_quantity,
                'category_count': len(data)
            }
        else:
            metadata = {}

        return ReportData('category', self.start_date, self.end_date, data, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get category sales formatter."""
        return CategoryTextFormatter(report_data)


class PaymentMethodsGenerator(ReportGenerator):
    """Generator for payment methods reports."""

    def generate_data(self) -> ReportData:
        """Generate payment methods data."""
        data = reports.get_sales_by_payment_method(self.start_date, self.end_date)

        if data:
            total_revenue = sum(item['total_sales'] for item in data)
            total_transactions = sum(item['transaction_count'] for item in data)

            metadata = {
                'total_revenue': total_revenue,
                'total_transactions': total_transactions,
                'method_count': len(data)
            }
        else:
            metadata = {}

        return ReportData('payment_methods', self.start_date, self.end_date, data, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get payment methods formatter."""
        return PaymentMethodsTextFormatter(report_data)


class VoidedSalesGenerator(ReportGenerator):
    """Generator for voided sales reports."""

    def generate_data(self) -> ReportData:
        """Generate voided sales data."""
        data = reports.get_voided_sales(self.start_date, self.end_date)

        if data:
            total_voided = sum(item['total'] for item in data)
            total_items = sum(item['item_count'] for item in data)

            metadata = {
                'total_voided': total_voided,
                'total_items': total_items,
                'transaction_count': len(data)
            }
        else:
            metadata = {}

        return ReportData('voided', self.start_date, self.end_date, data, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get voided sales formatter."""
        return VoidedSalesTextFormatter(report_data)


class SalesLogGenerator(ReportGenerator):
    """Generator for sales log reports."""

    def generate_data(self) -> ReportData:
        """Generate sales log data."""
        data = reports.get_detailed_sales_transactions(
            self.start_date, self.end_date,
            limit=REPORT_LIMITS['display']
        )

        if data:
            # Group by receipt for summary
            receipts = defaultdict(list)
            for item in data:
                receipts[item['receipt_number']].append(item)

            total_revenue = sum(item['total'] for item in data)
            total_items = sum(item['quantity'] for item in data)

            metadata = {
                'total_revenue': total_revenue,
                'total_items': total_items,
                'transaction_count': len(receipts),
                'line_items': len(data)
            }
        else:
            metadata = {}

        return ReportData('sales_log', self.start_date, self.end_date, data, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get sales log formatter."""
        return SalesLogTextFormatter(report_data)

    def fetch_page(self, page_size: int = 100, cursor: str | None = None, use_keyset: bool = False) -> tuple[list[dict], str | None, dict]:
        """Fetch a page of sales log transactions.

        Supports both offset pagination (cursor is offset string) and keyset pagination (cursor like 'key:YYYY-MM-DD|HH:MM:SS|id').
        Returns (rows, next_cursor, metadata).
        """
        import sqlite3
        from modules.reports import get_connection

        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row

            if use_keyset:
                # Keyset cursor format: key:date|time|transaction_id (all strings)
                last_date = last_time = None
                last_id = None
                if cursor and cursor.startswith('key:'):
                    try:
                        payload = cursor[4:]
                        last_date, last_time, last_id = payload.split('|', 2)
                        last_id = int(last_id)
                    except Exception:
                        last_date = last_time = last_id = None

                # Build combined query as CTE then filter by keyset
                combined_cte = f"""
                    WITH combined AS (
                        SELECT * FROM (
                            SELECT
                                'sale' as transaction_type,
                                s.sale_id as transaction_id,
                                s.receipt_number,
                                s.date,
                                s.time,
                                i.name as item_name,
                                i.category,
                                si.quantity,
                                si.price,
                                (si.quantity * si.price) as line_total,
                                s.total,
                                s.payment,
                                s.payment_method,
                                NULL as void_reason,
                                NULL as refund_reason,
                                NULL as refund_amount,
                                0 as is_voided,
                                0 as is_refund
                            FROM sales s
                            JOIN sales_items si ON s.sale_id = si.sale_id
                            JOIN items i ON si.item_id = i.item_id
                            WHERE s.date BETWEEN ? AND ?
                            AND (s.voided IS NULL OR s.voided = 0)

                            UNION ALL

                            SELECT
                                'void' as transaction_type,
                                s.sale_id as transaction_id,
                                s.receipt_number,
                                s.date,
                                s.time,
                                i.name as item_name,
                                i.category,
                                si.quantity,
                                si.price,
                                (si.quantity * si.price) as line_total,
                                s.total,
                                s.payment,
                                s.payment_method,
                                s.void_reason,
                                NULL as refund_reason,
                                NULL as refund_amount,
                                1 as is_voided,
                                0 as is_refund
                            FROM sales s
                            JOIN sales_items si ON s.sale_id = si.sale_id
                            JOIN items i ON si.item_id = i.item_id
                            WHERE s.date BETWEEN ? AND ?
                            AND s.voided = 1

                            UNION ALL

                            SELECT
                                'refund' as transaction_type,
                                r.refund_id as transaction_id,
                                r.receipt_number,
                                date(r.created_at) as date,
                                time(r.created_at) as time,
                                'REFUND' as item_name,
                                'Refund' as category,
                                1 as quantity,
                                r.refund_amount as price,
                                r.refund_amount as line_total,
                                r.refund_amount as total,
                                NULL as payment,
                                NULL as payment_method,
                                NULL as void_reason,
                                r.reason as refund_reason,
                                r.refund_amount,
                                0 as is_voided,
                                1 as is_refund
                            FROM refunds r
                            WHERE date(r.created_at) BETWEEN ? AND ?
                        )
                    )
                """

                if last_date and last_time and last_id is not None:
                    where_clause = "WHERE (date < ?) OR (date = ? AND time < ?) OR (date = ? AND time = ? AND transaction_id < ?)"
                    params = [self.start_date, self.end_date, self.start_date, self.end_date, self.start_date, self.end_date, last_date, last_date, last_time, last_date, last_time, last_id, page_size + 1]
                else:
                    where_clause = ""
                    params = [self.start_date, self.end_date, self.start_date, self.end_date, self.start_date, self.end_date, page_size + 1]

                final_q = combined_cte + f"SELECT * FROM combined {where_clause} ORDER BY date DESC, time DESC, transaction_id DESC LIMIT ?"
                rows = conn.execute(final_q, params).fetchall()

                fetched = rows
                has_more = len(fetched) > page_size
                page_rows = fetched[:page_size]

                # Convert sqlite Row to dict
                result = [dict(r) for r in page_rows]

                if has_more and page_rows:
                    last = page_rows[-1]
                    next_cursor = f"key:{last['date']}|{last['time']}|{last['transaction_id']}"
                else:
                    next_cursor = None

                # total count is expensive; leave unset or provide line_items from metadata
                metadata = {'page_size': page_size}
                return result, next_cursor, metadata

            else:
                # Offset pagination using existing helper
                offset = int(cursor) if cursor and cursor.isdigit() else 0
                rows = reports.get_comprehensive_sales_log(self.start_date, self.end_date, limit=page_size, offset=offset)
                next_cursor = str(offset + len(rows)) if len(rows) == page_size else None
                metadata = {'page_size': page_size}
                return rows, next_cursor, metadata

        except Exception as e:
            # Fallback to full generation
            full = self.generate_data()
            offset = int(cursor) if cursor and cursor.isdigit() else 0
            rows = full.data[offset:offset + page_size]
            next_cursor = str(offset + len(rows)) if offset + len(rows) < len(full.data) else None
            metadata = {**full.metadata, 'total_items': len(full.data)}
            return rows, next_cursor, metadata

class TransactionsGenerator(ReportGenerator):
    """Generator for detailed transactions reports."""

    def generate_data(self) -> ReportData:
        """Generate transactions data."""
        data = reports.get_detailed_sales_transactions(
            self.start_date, self.end_date,
            limit=REPORT_LIMITS['display']
        )

        if data:
            # Group by receipt for summary
            receipts = defaultdict(list)
            for item in data:
                receipts[item['receipt_number']].append(item)

            total_revenue = sum(item['total'] for item in data)

            # Payment method breakdown
            payment_totals = defaultdict(float)
            for receipt, items in receipts.items():
                payment_method = items[0]['payment_method']
                transaction_total = sum(item['total'] for item in items)
                payment_totals[payment_method] += transaction_total

            metadata = {
                'total_revenue': total_revenue,
                'transaction_count': len(receipts),
                'line_items': len(data),
                'payment_breakdown': dict(payment_totals)
            }
        else:
            metadata = {}

        return ReportData('transactions', self.start_date, self.end_date, data, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get transactions formatter."""
        return TransactionsTextFormatter(report_data)


class TrendsGenerator(ReportGenerator):
    """Generator for sales trends reports."""

    def generate_data(self) -> ReportData:
        """Generate trends data."""
        # Determine grouping based on date range
        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
        days_diff = (end_dt - start_dt).days

        if days_diff <= 7:
            group_by = 'day'
        elif days_diff <= 31:
            group_by = 'week'
        else:
            group_by = 'month'

        data = reports.get_sales_performance_trends(self.start_date, self.end_date, group_by)

        metadata = {
            'group_by': group_by,
            'days_diff': days_diff
        }

        return ReportData('trends', self.start_date, self.end_date, data, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get trends formatter."""
        return TrendsTextFormatter(report_data)