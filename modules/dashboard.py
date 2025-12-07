"""Dashboard statistics and analytics."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from database.init_db import get_connection


def get_today_summary() -> dict:
    """Get today's sales summary."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Sales stats
        sales_row = conn.execute(
            """
            SELECT 
                COUNT(*) as transactions,
                COALESCE(SUM(total), 0) as revenue,
                COALESCE(AVG(total), 0) as avg_sale
            FROM sales
            WHERE date = ?
            """,
            (today,)
        ).fetchone()
        
        # Items sold
        items_row = conn.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) as items_sold
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.date = ?
            """,
            (today,)
        ).fetchone()
        
        return {
            "transactions": sales_row["transactions"] or 0,
            "revenue": sales_row["revenue"] or 0,
            "avg_sale": sales_row["avg_sale"] or 0,
            "items_sold": items_row["items_sold"] or 0
        }


def _to_short_code(sale_id: int) -> str:
    """Convert an integer sale_id to a short base36-like code (stable and unique per id)."""
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if sale_id == 0:
        return "0"
    result = []
    n = sale_id
    while n > 0:
        n, rem = divmod(n, 36)
        result.append(alphabet[rem])
    return "S" + "".join(reversed(result))


def get_week_summary() -> dict:
    """Get this week's sales summary."""
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        row = conn.execute(
            """
            SELECT 
                COUNT(*) as transactions,
                COALESCE(SUM(total), 0) as revenue
            FROM sales
            WHERE date BETWEEN ? AND ?
            """,
            (week_start, today_str)
        ).fetchone()
        
        return {
            "transactions": row["transactions"] or 0,
            "revenue": row["revenue"] or 0
        }


def get_month_summary() -> dict:
    """Get this month's sales summary."""
    today = datetime.now()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        row = conn.execute(
            """
            SELECT 
                COUNT(*) as transactions,
                COALESCE(SUM(total), 0) as revenue
            FROM sales
            WHERE date BETWEEN ? AND ?
            """,
            (month_start, today_str)
        ).fetchone()
        
        return {
            "transactions": row["transactions"] or 0,
            "revenue": row["revenue"] or 0
        }


def get_top_products(limit: int = 5) -> list[dict]:
    """Get top selling products today."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            """
            SELECT 
                i.name,
                SUM(si.quantity) as quantity_sold,
                SUM(si.quantity * si.price) as revenue
            FROM sales_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.date = ?
            GROUP BY i.item_id
            ORDER BY quantity_sold DESC
            LIMIT ?
            """,
            (today, limit)
        ).fetchall()
        
        return [dict(r) for r in rows]


def get_low_stock_items(threshold: int = 10) -> list[dict]:
    """Get items with low stock based on item-specific thresholds."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            """
            SELECT 
                item_id,
                name,
                category,
                quantity,
                selling_price,
                COALESCE(low_stock_threshold, 10) as threshold
            FROM items
            WHERE quantity <= COALESCE(low_stock_threshold, 10)
            ORDER BY quantity ASC
            LIMIT 10
            """,
        ).fetchall()
        
        return [dict(r) for r in rows]


def get_recent_sales(limit: int = 10) -> list[dict]:
    """Get recent sales transactions."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            """
            SELECT 
                sale_id,
                date,
                time,
                total,
                (SELECT COUNT(*) FROM sales_items WHERE sale_id = s.sale_id) as items
            FROM sales s
            ORDER BY date DESC, time DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        result = []
        for r in rows:
            row_dict = dict(r)
            row_dict["sale_code"] = _to_short_code(r["sale_id"])
            result.append(row_dict)
        return result


def get_sales_trend_data(days: int = 7) -> list[dict]:
    """Get sales data for the last N days for charting."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days-1)
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            """
            SELECT 
                date,
                COUNT(*) as transactions,
                COALESCE(SUM(total), 0) as revenue
            FROM sales
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        ).fetchall()
        
        # Fill in missing dates with 0
        result = []
        current_date = start_date
        sales_dict = {row["date"]: dict(row) for row in rows}
        
        for i in range(days):
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in sales_dict:
                result.append(sales_dict[date_str])
            else:
                result.append({
                    "date": date_str,
                    "transactions": 0,
                    "revenue": 0
                })
            current_date += timedelta(days=1)
        
        return result


def get_category_breakdown() -> list[dict]:
    """Get sales breakdown by category for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            """
            SELECT 
                i.category,
                COUNT(DISTINCT si.sale_id) as transactions,
                SUM(si.quantity) as quantity,
                SUM(si.quantity * si.price) as revenue
            FROM sales_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.date = ?
            GROUP BY i.category
            ORDER BY revenue DESC
            """,
            (today,)
        ).fetchall()
        
        return [dict(r) for r in rows]
