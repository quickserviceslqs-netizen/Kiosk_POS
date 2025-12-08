"""Sales reporting and analytics."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from database.init_db import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_sales_summary(start_date: str, end_date: str) -> dict:
    """Get sales summary for a date range."""
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
    """Get best-selling items for a date range."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                i.item_id,
                i.name,
                i.category,
                SUM(si.quantity) as total_sold,
                SUM(si.quantity * si.price) as revenue,
                SUM(si.quantity * (si.price - si.cost_price)) as profit
            FROM sales_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.date BETWEEN ? AND ?
            GROUP BY i.item_id
            ORDER BY total_sold DESC
            LIMIT ?
            """,
            (start_date, end_date, limit)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_profit_analysis(start_date: str, end_date: str) -> dict:
    """Calculate profit/loss for a date range."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Sales revenue and cost
        sales_row = conn.execute(
            """
            SELECT 
                SUM(si.quantity * si.price) as total_revenue,
                SUM(si.quantity * si.cost_price) as total_cost
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.date BETWEEN ? AND ?
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
        expenses = expenses_row['total_expenses'] or 0
        gross_profit = revenue - cost
        net_profit = gross_profit - expenses
        
        return {
            'total_revenue': revenue,
            'total_cost': cost,
            'gross_profit': gross_profit,
            'total_expenses': expenses,
            'net_profit': net_profit,
            'profit_margin': (net_profit / revenue * 100) if revenue > 0 else 0
        }


def get_category_sales(start_date: str, end_date: str) -> list[dict]:
    """Get sales grouped by item category."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                COALESCE(i.category, 'Uncategorized') as category,
                SUM(si.quantity) as total_quantity,
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
    return [_row_to_dict(r) for r in rows]


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
