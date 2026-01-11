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
