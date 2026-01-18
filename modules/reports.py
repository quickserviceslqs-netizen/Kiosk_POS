"""Sales reporting and analytics."""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional

from database.init_db import get_connection

# Simple in-memory cache with TTL
_cache = {}
_CACHE_TTL = 300  # 5 minutes


def invalidate_cache():
    """Clear all cached report data."""
    global _cache
    _cache.clear()


def _get_cached(key: str, func, *args, **kwargs):
    """Get from cache or compute and cache."""
    now = time.time()
    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < _CACHE_TTL:
            return data
    data = func(*args, **kwargs)
    _cache[key] = (data, now)
    return data


def _convert_quantity_to_display(qty_raw: float, is_special: bool, unit_multiplier: float, unit_of_measure: str) -> tuple[float, str]:
    """Convert raw quantity to display quantity and unit label."""
    if is_special:
        multiplier = float(unit_multiplier or 1000)
        qty_base = qty_raw / multiplier
        unit = unit_of_measure.lower() if unit_of_measure else ""
        if unit in ("litre", "liter", "liters", "litres", "l"):
            unit_label = "L"
        elif unit in ("kilogram", "kilograms", "kg", "kgs"):
            unit_label = "kg"
        elif unit in ("meter", "meters", "metre", "metres", "m"):
            unit_label = "m"
        else:
            unit_label = unit_of_measure or "unit"
        return qty_base, unit_label
    else:
        return qty_raw, ""


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_sales_summary(start_date: str, end_date: str) -> dict:
    """Get sales summary for a date range."""
    key = f"sales_summary_{start_date}_{end_date}"
    return _get_cached(key, _get_sales_summary_uncached, start_date, end_date)


def _get_sales_summary_uncached(start_date: str, end_date: str) -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        # No currency_code in sales table, so just return as is
        row = conn.execute(
            """
            SELECT 
                COUNT(*) as total_transactions,
                SUM(total) as total_sales,
                SUM(payment) as total_payments,
                AVG(total) as avg_transaction
            FROM sales
            WHERE date BETWEEN ? AND ?
            AND (voided IS NULL OR voided = 0)
            """,
            (start_date, end_date)
        ).fetchone()
    return _row_to_dict(row) if row else {}


def get_daily_sales(date: str) -> list[dict]:
    """Get all sales for a specific date."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT s.*, 
                   s.receipt_number,
                   (SELECT COUNT(*) FROM sales_items WHERE sale_id = s.sale_id) as item_count
            FROM sales s
            WHERE s.date = ?
            AND (s.voided IS NULL OR s.voided = 0)
            ORDER BY s.time DESC
            """,
            (date,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_date_range_sales(start_date: str, end_date: str) -> list[dict]:
    """Get sales grouped by date for a date range."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                date,
                COUNT(*) as transactions,
                SUM(total) as total_sales,
                AVG(total) as avg_sale
            FROM sales
            WHERE date BETWEEN ? AND ?
            AND (voided IS NULL OR voided = 0)
            GROUP BY date
            ORDER BY date DESC
            """,
            (start_date, end_date)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_best_selling_items(start_date: str, end_date: str, limit: int = 10) -> list[dict]:
    """Get best-selling items for a date range (excludes refunded sales).
    For fractional items, quantities are converted to base units (L/kg/m)."""
    key = f"best_selling_{start_date}_{end_date}_{limit}"
    return _get_cached(key, _get_best_selling_items_uncached, start_date, end_date, limit)


def _get_best_selling_items_uncached(start_date: str, end_date: str, limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                i.item_id,
                i.name,
                i.category,
                i.is_special_volume,
                i.unit_multiplier,
                i.unit_of_measure,
                SUM(si.quantity) as total_sold_raw,
                -- Revenue: account for refunds by subtracting refunded quantities
                SUM(CASE WHEN i.is_special_volume = 1 THEN (si.quantity - COALESCE(ri.quantity, 0)) * si.price
                         ELSE (si.quantity - COALESCE(ri.quantity, 0)) * (CASE WHEN si.price = i.selling_price THEN (si.price / CASE WHEN COALESCE(i.unit_size_ml,1) = 0 THEN 1 ELSE i.unit_size_ml END) ELSE si.price END) END) as revenue,
                SUM(CASE WHEN i.is_special_volume = 1 THEN (si.quantity - COALESCE(ri.quantity, 0)) * (si.price - si.cost_price)
                         ELSE (si.quantity - COALESCE(ri.quantity, 0)) * ((CASE WHEN si.price = i.selling_price THEN (si.price / CASE WHEN COALESCE(i.unit_size_ml,1) = 0 THEN 1 ELSE i.unit_size_ml END) ELSE si.price END) - (CASE WHEN si.cost_price = i.cost_price THEN (si.cost_price / CASE WHEN COALESCE(i.unit_size_ml,1) = 0 THEN 1 ELSE i.unit_size_ml END) ELSE si.cost_price END)) END) as profit
            FROM sales_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            LEFT JOIN refunds_items ri ON si.sale_item_id = ri.sale_item_id
            WHERE s.date BETWEEN ? AND ?
            GROUP BY i.item_id
            HAVING total_sold_raw > 0
            ORDER BY total_sold_raw DESC
            LIMIT ?
            """,
            (start_date, end_date, limit)
        ).fetchall()
    
    results = []
    for r in rows:
        row_dict = _row_to_dict(r)
        qty_raw = row_dict.get("total_sold_raw", 0) or 0
        
        # Convert fractional items from small units to base units
        qty_base, unit_label = _convert_quantity_to_display(
            qty_raw, 
            row_dict.get("is_special_volume"), 
            row_dict.get("unit_multiplier"), 
            row_dict.get("unit_of_measure")
        )
        row_dict["total_sold"] = qty_base
        row_dict["qty_display"] = f"{qty_base:.2f} {unit_label}" if unit_label else f"{int(qty_base)}"
        
        results.append(row_dict)
    
    return results


def get_profit_analysis(start_date: str, end_date: str) -> dict:
    """Calculate profit/loss for a date range."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Sales revenue and cost: compute using per-sale-unit prices (normalize non-special items by unit_size)
        sales_row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN i.is_special_volume = 1 THEN si.quantity * si.price
                         ELSE si.quantity * (CASE WHEN si.price = i.selling_price THEN (si.price / CASE WHEN COALESCE(i.unit_size_ml,1) = 0 THEN 1 ELSE i.unit_size_ml END) ELSE si.price END) END) as total_revenue,
                SUM(CASE WHEN i.is_special_volume = 1 THEN si.quantity * si.cost_price
                         ELSE si.quantity * (CASE WHEN si.cost_price = i.cost_price THEN (si.cost_price / CASE WHEN COALESCE(i.unit_size_ml,1) = 0 THEN 1 ELSE i.unit_size_ml END) ELSE si.cost_price END) END) as total_cost
            FROM sales_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()

        # Refunds: subtract refunded revenue and costs for refunds created in this date range
        refunds_row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN i.is_special_volume = 1 THEN ri.quantity * si.price
                                  ELSE ri.quantity * (CASE WHEN si.price = i.selling_price THEN (si.price / CASE WHEN COALESCE(i.unit_size_ml,1) = 0 THEN 1 ELSE i.unit_size_ml END) ELSE si.price END) END), 0) as refunded_revenue,
                COALESCE(SUM(CASE WHEN i.is_special_volume = 1 THEN ri.quantity * si.cost_price
                                  ELSE ri.quantity * (CASE WHEN si.cost_price = i.cost_price THEN (si.cost_price / CASE WHEN COALESCE(i.unit_size_ml,1) = 0 THEN 1 ELSE i.unit_size_ml END) ELSE si.cost_price END) END), 0) as refunded_cost
            FROM refunds_items ri
            JOIN refunds r ON ri.refund_id = r.refund_id
            JOIN sales_items si ON ri.sale_item_id = si.sale_item_id
            JOIN items i ON ri.item_id = i.item_id
            WHERE DATE(r.created_at) BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()
        
        # Expenses (if exists)
        expenses_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) as total_expenses
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()
        
        revenue = sales_row['total_revenue'] or 0
        cost = sales_row['total_cost'] or 0

        # Subtract refunds recorded in the same period
        refunded_revenue = refunds_row['refunded_revenue'] or 0
        refunded_cost = refunds_row['refunded_cost'] or 0

        revenue_after_refunds = revenue - refunded_revenue
        cost_after_refunds = cost - refunded_cost

        expenses = expenses_row['total_expenses'] or 0
        gross_profit = revenue_after_refunds - cost_after_refunds
        net_profit = gross_profit - expenses
        
        return {
            'total_revenue': revenue_after_refunds,
            'total_cost': cost_after_refunds,
            'gross_profit': gross_profit,
            'total_expenses': expenses,
            'net_profit': net_profit,
            'profit_margin': (net_profit / revenue_after_refunds * 100) if revenue_after_refunds > 0 else 0,
            'refunded_revenue': refunded_revenue,
            'refunded_cost': refunded_cost,
        }


def get_category_sales(start_date: str, end_date: str) -> list[dict]:
    """Get sales grouped by item category.
    For categories with fractional items, shows total items sold (integer count).
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                COALESCE(i.category, 'Uncategorized') as category,
                COUNT(*) as total_items,
                SUM(si.quantity * si.price) as total_revenue,
                COUNT(DISTINCT si.sale_id) as transactions
            FROM sales_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.date BETWEEN ? AND ?
            AND (s.voided IS NULL OR s.voided = 0)
            GROUP BY i.category
            ORDER BY total_revenue DESC
            """,
            (start_date, end_date)
        ).fetchall()
    
    results = []
    for r in rows:
        row_dict = _row_to_dict(r)
        # Rename total_items to total_quantity for backward compatibility
        row_dict['total_quantity'] = row_dict.pop('total_items', 0)
        results.append(row_dict)
    return results


def get_hourly_sales(date: str) -> list[dict]:
    """Get sales grouped by hour for a specific date."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                substr(time, 1, 2) as hour,
                COUNT(*) as transactions,
                SUM(total) as total_sales
            FROM sales
            WHERE date = ?
            AND (voided IS NULL OR voided = 0)
            GROUP BY hour
            ORDER BY hour
            """,
            (date,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_refunds(start_date: str, end_date: str) -> list[dict]:
    """Get refunds within a date range (inclusive)."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                r.refund_id,
                r.refund_code,
                r.original_sale_id,
                r.refund_amount,
                r.reason,
                r.created_at,
                s.receipt_number
            FROM refunds r
            JOIN sales s ON r.original_sale_id = s.sale_id
            WHERE DATE(r.created_at) BETWEEN ? AND ?
            ORDER BY r.created_at DESC
            """,
            (start_date, end_date)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_voided_sales(start_date: str, end_date: str) -> list[dict]:
    """Get voided sales within a date range."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                s.sale_id,
                s.receipt_number,
                s.date,
                s.time,
                s.total,
                s.void_reason,
                s.voided_at,
                u.username as voided_by_username,
                (SELECT COUNT(*) FROM sales_items WHERE sale_id = s.sale_id) as item_count
            FROM sales s
            LEFT JOIN users u ON s.voided_by = u.user_id
            WHERE s.voided = 1
            AND s.date BETWEEN ? AND ?
            ORDER BY s.voided_at DESC
            """,
            (start_date, end_date)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_comprehensive_sales_summary(start_date: str, end_date: str) -> dict:
    """Get comprehensive sales summary including voided sales and refunds."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Valid sales (not voided)
        valid_sales = conn.execute(
            """
            SELECT 
                COUNT(*) as transactions,
                SUM(total) as total_sales,
                AVG(total) as avg_transaction
            FROM sales
            WHERE date BETWEEN ? AND ?
            AND (voided IS NULL OR voided = 0)
            """,
            (start_date, end_date)
        ).fetchone()
        
        # Voided sales
        voided_sales = conn.execute(
            """
            SELECT 
                COUNT(*) as voided_transactions,
                SUM(total) as voided_amount
            FROM sales
            WHERE date BETWEEN ? AND ?
            AND voided = 1
            """,
            (start_date, end_date)
        ).fetchone()
        
        # Refunds
        refunds = conn.execute(
            """
            SELECT 
                COUNT(*) as refund_count,
                SUM(refund_amount) as total_refunded
            FROM refunds
            WHERE DATE(created_at) BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()
        
        # Net sales (valid sales minus refunds)
        net_sales = (valid_sales['total_sales'] or 0) - (refunds['total_refunded'] or 0)
        
        return {
            'valid_transactions': valid_sales['transactions'] or 0,
            'valid_sales_amount': valid_sales['total_sales'] or 0,
            'avg_valid_transaction': valid_sales['avg_transaction'] or 0,
            'voided_transactions': voided_sales['voided_transactions'] or 0,
            'voided_amount': voided_sales['voided_amount'] or 0,
            'refund_count': refunds['refund_count'] or 0,
            'total_refunded': refunds['total_refunded'] or 0,
            'net_sales': max(0, net_sales),
            'total_gross_sales': (valid_sales['total_sales'] or 0) + (voided_sales['voided_amount'] or 0)
        }


def get_voided_sales_by_reason(start_date: str, end_date: str) -> list[dict]:
    """Get voided sales grouped by reason."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                COALESCE(void_reason, 'No Reason Specified') as reason,
                COUNT(*) as count,
                SUM(total) as total_amount
            FROM sales
            WHERE voided = 1
            AND date BETWEEN ? AND ?
            GROUP BY void_reason
            ORDER BY total_amount DESC
            """,
            (start_date, end_date)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_refunds_by_reason(start_date: str, end_date: str) -> list[dict]:
    """Get refunds grouped by reason."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                COALESCE(r.reason, 'No Reason Specified') as reason,
                COUNT(*) as count,
                SUM(r.refund_amount) as total_amount
            FROM refunds r
            WHERE DATE(r.created_at) BETWEEN ? AND ?
            GROUP BY r.reason
            ORDER BY total_amount DESC
            """,
            (start_date, end_date)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_daily_voided_and_refunds(start_date: str, end_date: str) -> list[dict]:
    """Get daily breakdown of voided sales and refunds."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Get voided sales by date
        voided_rows = conn.execute(
            """
            SELECT 
                date,
                COUNT(*) as voided_count,
                SUM(total) as voided_amount
            FROM sales
            WHERE voided = 1
            AND date BETWEEN ? AND ?
            GROUP BY date
            """,
            (start_date, end_date)
        ).fetchall()
        
        # Get refunds by date
        refund_rows = conn.execute(
            """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as refund_count,
                SUM(refund_amount) as refunded_amount
            FROM refunds
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY DATE(created_at)
            """,
            (start_date, end_date)
        ).fetchall()
        
        # Combine the data
        voided_dict = {row['date']: _row_to_dict(row) for row in voided_rows}
        refund_dict = {row['date']: _row_to_dict(row) for row in refund_rows}
        
        # Get all dates in range
        from datetime import datetime, timedelta
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        results = []
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            voided = voided_dict.get(date_str, {'voided_count': 0, 'voided_amount': 0})
            refunded = refund_dict.get(date_str, {'refund_count': 0, 'refunded_amount': 0})
            
            results.append({
                'date': date_str,
                'voided_count': voided['voided_count'],
                'voided_amount': voided['voided_amount'],
                'refund_count': refunded['refund_count'],
                'refunded_amount': refunded['refunded_amount']
            })
            current += timedelta(days=1)
        
        return results


def get_detailed_sales_transactions(start_date: str, end_date: str, limit: int = None, offset: int = 0) -> list[dict]:
    """Get detailed sales transactions with line items for a date range, including voided sales and refunds."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        # Get regular sales (not voided) with line items
        regular_sales_query = """
            SELECT
                'sale' as transaction_type,
                s.sale_id,
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
        """

        # Get voided sales with line items
        voided_sales_query = """
            SELECT
                'void' as transaction_type,
                s.sale_id,
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
        """

        # Get refunds (refunds don't have line items, so we'll create a single line entry)
        refunds_query = """
            SELECT
                'refund' as transaction_type,
                r.refund_id as sale_id,
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
        """

        # Combine all queries
        combined_query = f"""
            {regular_sales_query}
            UNION ALL
            {voided_sales_query}
            UNION ALL
            {refunds_query}
            ORDER BY date DESC, time DESC, sale_id DESC
        """

        params = [start_date, end_date, start_date, end_date, start_date, end_date]

        if limit is not None:
            combined_query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = conn.execute(combined_query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_sales_by_payment_method(start_date: str, end_date: str) -> list[dict]:
    """Get sales breakdown by payment method."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                COALESCE(payment_method, 'Cash') as payment_method,
                COUNT(*) as transaction_count,
                SUM(total) as total_sales,
                AVG(total) as avg_transaction,
                MIN(total) as min_transaction,
                MAX(total) as max_transaction
            FROM sales
            WHERE date BETWEEN ? AND ?
            AND (voided IS NULL OR voided = 0)
            GROUP BY payment_method
            ORDER BY total_sales DESC
            """,
            (start_date, end_date)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_sales_performance_trends(start_date: str, end_date: str, group_by: str = 'day') -> list[dict]:
    """Get sales performance trends over time."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        if group_by == 'day':
            date_format = '%Y-%m-%d'
            group_field = 'date'
        elif group_by == 'week':
            date_format = '%Y-%W'
            group_field = "strftime('%Y-%W', date)"
        elif group_by == 'month':
            date_format = '%Y-%m'
            group_field = "strftime('%Y-%m', date)"
        else:
            date_format = '%Y-%m-%d'
            group_field = 'date'
        
        # Get sales data
        sales_query = f"""
            SELECT 
                {group_field} as period,
                COUNT(*) as transactions,
                SUM(total) as total_sales,
                AVG(total) as avg_sale,
                SUM(payment) as subtotal,
                SUM(total - payment) as total_vat,
                SUM(total - payment) as total_discounts
            FROM sales
            WHERE date BETWEEN ? AND ?
            AND (voided IS NULL OR voided = 0)
            GROUP BY period
            ORDER BY period
        """
        
        rows = conn.execute(sales_query, (start_date, end_date)).fetchall()
        
        results = []
        for r in rows:
            row_dict = _row_to_dict(r)
            # Format period label nicely
            if group_by == 'day':
                row_dict['period_label'] = row_dict['period']
            elif group_by == 'week':
                year, week = row_dict['period'].split('-')
                row_dict['period_label'] = f"{year} Week {int(week) + 1}"
            elif group_by == 'month':
                year, month = row_dict['period'].split('-')
                from datetime import datetime
                month_name = datetime.strptime(month, '%m').strftime('%B')
                row_dict['period_label'] = f"{month_name} {year}"
            else:
                row_dict['period_label'] = row_dict['period']
            
            results.append(row_dict)
        
        return results


def get_comprehensive_sales_log(start_date: str, end_date: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """Get comprehensive sales log including all transactions, refunds, and voids for audit trail."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        # Get regular sales (not voided)
        sales_query = """
            SELECT
                'sale' as transaction_type,
                s.sale_id as transaction_id,
                s.receipt_number,
                s.date,
                s.time,
                s.total as amount,
                s.payment,
                s.change,
                s.payment_method,
                s.subtotal,
                s.vat_amount,
                s.discount_amount,
                NULL as refund_amount,
                NULL as void_reason,
                NULL as refund_reason,
                u.username as user_name,
                GROUP_CONCAT(i.name || ' (x' || si.quantity || ')', ', ') as items_summary,
                COUNT(si.item_id) as item_count
            FROM sales s
            LEFT JOIN users u ON s.user_id = u.user_id
            LEFT JOIN sales_items si ON s.sale_id = si.sale_id
            LEFT JOIN items i ON si.item_id = i.item_id
            WHERE s.date BETWEEN ? AND ?
            AND (s.voided IS NULL OR s.voided = 0)
            GROUP BY s.sale_id
        """

        # Get voided sales
        voided_query = """
            SELECT
                'void' as transaction_type,
                s.sale_id as transaction_id,
                s.receipt_number,
                s.date,
                s.time,
                s.total as amount,
                s.payment,
                s.change,
                s.payment_method,
                s.subtotal,
                s.vat_amount,
                s.discount_amount,
                NULL as refund_amount,
                s.void_reason,
                NULL as refund_reason,
                vu.username as user_name,
                GROUP_CONCAT(i.name || ' (x' || si.quantity || ')', ', ') as items_summary,
                COUNT(si.item_id) as item_count
            FROM sales s
            LEFT JOIN users vu ON s.voided_by = vu.user_id
            LEFT JOIN sales_items si ON s.sale_id = si.sale_id
            LEFT JOIN items i ON si.item_id = i.item_id
            WHERE s.date BETWEEN ? AND ?
            AND s.voided = 1
            GROUP BY s.sale_id
        """

        # Get refunds
        refunds_query = """
            SELECT
                'refund' as transaction_type,
                r.refund_id as transaction_id,
                r.receipt_number,
                r.created_at as date,
                r.created_at as time,
                r.refund_amount as amount,
                NULL as payment,
                NULL as change,
                NULL as payment_method,
                NULL as subtotal,
                NULL as vat_amount,
                NULL as discount_amount,
                r.refund_amount,
                NULL as void_reason,
                r.reason as refund_reason,
                u.username as user_name,
                'Refund' as items_summary,
                1 as item_count
            FROM refunds r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE date(r.created_at) BETWEEN ? AND ?
        """

        # Combine all queries with UNION ALL and apply pagination
        combined_query = f"""
            {sales_query}
            UNION ALL
            {voided_query}
            UNION ALL
            {refunds_query}
            ORDER BY date DESC, time DESC
            LIMIT ? OFFSET ?
        """

        params = [start_date, end_date, start_date, end_date, start_date, end_date, limit, offset]

        rows = conn.execute(combined_query, params).fetchall()

        # Convert to dict and add formatted fields
        results = []
        for row in rows:
            row_dict = _row_to_dict(row)

            # Format date/time for display
            if row_dict.get('time') and len(row_dict['time']) > 5:
                # Extract time part if it's a full datetime
                row_dict['time_display'] = row_dict['time'].split(' ')[-1] if ' ' in row_dict['time'] else row_dict['time']
            else:
                row_dict['time_display'] = row_dict.get('time', '')

            # Add transaction description
            if row_dict['transaction_type'] == 'sale':
                row_dict['description'] = f"Sale - {row_dict['item_count']} items"
            elif row_dict['transaction_type'] == 'void':
                row_dict['description'] = f"Voided Sale - {row_dict.get('void_reason', 'No reason')}"
            elif row_dict['transaction_type'] == 'refund':
                row_dict['description'] = f"Refund - {row_dict.get('refund_reason', 'No reason')}"

            results.append(row_dict)

        return results


def get_sales_log_count(start_date: str, end_date: str) -> int:
    """Get total count of transactions in the sales log for pagination."""
    with get_connection() as conn:
        # Count regular sales
        sales_count = conn.execute(
            "SELECT COUNT(*) FROM sales WHERE date BETWEEN ? AND ? AND (voided IS NULL OR voided = 0)",
            (start_date, end_date)
        ).fetchone()[0]

        # Count voided sales
        voided_count = conn.execute(
            "SELECT COUNT(*) FROM sales WHERE date BETWEEN ? AND ? AND voided = 1",
            (start_date, end_date)
        ).fetchone()[0]

        # Count refunds
        refunds_count = conn.execute(
            "SELECT COUNT(*) FROM refunds WHERE date(created_at) BETWEEN ? AND ?",
            (start_date, end_date)
        ).fetchone()[0]

        return sales_count + voided_count + refunds_count
