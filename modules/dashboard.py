"""Dashboard statistics and analytics."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from database.init_db import get_connection


def get_today_summary() -> dict:
    """Get today's sales summary (after refunds)."""
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
        
        # Subtract refunds for today
        refunds_row = conn.execute(
            """
            SELECT COALESCE(SUM(refund_amount), 0) as refunded_amount
            FROM refunds
            WHERE DATE(created_at) = ?
            """,
            (today,)
        ).fetchone()
        
        # Count line items sold (not raw quantities) - excludes refunded sales
        items_row = conn.execute(
            """
            SELECT COUNT(*) as line_items_sold
            FROM sales_items si
            JOIN sales s ON si.sale_id = s.sale_id
            LEFT JOIN refunds r ON s.sale_id = r.original_sale_id
            WHERE s.date = ? AND r.refund_id IS NULL
            """,
            (today,)
        ).fetchone()
        
        total_revenue = (sales_row["revenue"] or 0) - (refunds_row["refunded_amount"] or 0)
        
        return {
            "transactions": sales_row["transactions"] or 0,
            "revenue": max(0, total_revenue),
            "avg_sale": sales_row["avg_sale"] or 0,
            "items_sold": items_row["line_items_sold"] or 0
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
    """Get this week's sales summary (after refunds)."""
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
        
        # Subtract refunds for this week
        refunds_row = conn.execute(
            """
            SELECT COALESCE(SUM(refund_amount), 0) as refunded_amount
            FROM refunds
            WHERE DATE(created_at) BETWEEN ? AND ?
            """,
            (week_start, today_str)
        ).fetchone()
        
        total_revenue = (row["revenue"] or 0) - (refunds_row["refunded_amount"] or 0)
        
        return {
            "transactions": row["transactions"] or 0,
            "revenue": max(0, total_revenue)
        }


def get_month_summary() -> dict:
    """Get this month's sales summary (after refunds)."""
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
        
        # Subtract refunds for this month
        refunds_row = conn.execute(
            """
            SELECT COALESCE(SUM(refund_amount), 0) as refunded_amount
            FROM refunds
            WHERE DATE(created_at) BETWEEN ? AND ?
            """,
            (month_start, today_str)
        ).fetchone()
        
        total_revenue = (row["revenue"] or 0) - (refunds_row["refunded_amount"] or 0)
        
        return {
            "transactions": row["transactions"] or 0,
            "revenue": max(0, total_revenue)
        }


def get_top_products(limit: int = 5) -> list[dict]:
    """Get top selling products today (excludes refunded sales).
    For fractional items, quantities are converted to base units (L/kg/m)."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            """
            SELECT 
                i.name,
                i.is_special_volume,
                i.unit_multiplier,
                i.unit_of_measure,
                SUM(si.quantity) as quantity_sold_raw,
                SUM(si.quantity * si.price) as revenue
            FROM sales_items si
            JOIN items i ON si.item_id = i.item_id
            JOIN sales s ON si.sale_id = s.sale_id
            LEFT JOIN refunds r ON s.sale_id = r.original_sale_id
            WHERE s.date = ? AND r.refund_id IS NULL
            GROUP BY i.item_id
            ORDER BY quantity_sold_raw DESC
            LIMIT ?
            """,
            (today, limit)
        ).fetchall()
        
        results = []
        for r in rows:
            row_dict = dict(r)
            qty_raw = row_dict.get("quantity_sold_raw", 0) or 0
            
            # Convert fractional items from small units to base units
            if row_dict.get("is_special_volume"):
                multiplier = float(row_dict.get("unit_multiplier") or 1000)
                qty_base = qty_raw / multiplier  # e.g., 500ml / 1000 = 0.5 L
                unit = row_dict.get("unit_of_measure", "L")
                unit_lower = (unit or "").lower()
                if unit_lower in ("litre", "liter", "liters", "litres", "l"):
                    unit_label = "L"
                elif unit_lower in ("kilogram", "kilograms", "kg", "kgs"):
                    unit_label = "kg"
                elif unit_lower in ("meter", "meters", "metre", "metres", "m"):
                    unit_label = "m"
                else:
                    unit_label = unit
                row_dict["quantity_sold"] = qty_base
                row_dict["qty_display"] = f"{qty_base:.2f} {unit_label}"
            else:
                row_dict["quantity_sold"] = qty_raw
                row_dict["qty_display"] = f"{int(qty_raw)}"
            
            results.append(row_dict)
        
        return results


def get_low_stock_items(threshold: int = 10) -> list[dict]:
    """Get items with low stock based on item-specific thresholds.
    For fractional items, checks actual volume against threshold."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Get all items with their unit info
        rows = conn.execute(
            """
            SELECT 
                item_id,
                name,
                category,
                quantity,
                selling_price,
                COALESCE(low_stock_threshold, 10) as threshold,
                is_special_volume,
                unit_size_ml,
                unit_of_measure
            FROM items
            ORDER BY quantity ASC
            """,
        ).fetchall()
        
        low_items = []
        for row in rows:
            item = dict(row)
            item_threshold = item.get("threshold", threshold)
            
            if item.get("is_special_volume"):
                # For fractional items, check actual volume
                unit_size = float(item.get("unit_size_ml") or 1)
                actual_volume = item["quantity"] * unit_size
                item["actual_volume"] = actual_volume
                
                # Determine display unit
                unit = (item.get("unit_of_measure") or "").lower()
                if unit in ("litre", "liter", "liters", "litres", "l"):
                    item["display_unit"] = "L"
                elif unit in ("kilogram", "kilograms", "kg", "kgs"):
                    item["display_unit"] = "kg"
                elif unit in ("meter", "meters", "metre", "metres", "m"):
                    item["display_unit"] = "m"
                else:
                    item["display_unit"] = unit
                
                if actual_volume <= item_threshold:
                    low_items.append(item)
            else:
                # For regular items, check quantity
                item["actual_volume"] = item["quantity"]
                item["display_unit"] = "units"
                if item["quantity"] <= item_threshold:
                    low_items.append(item)
            
            if len(low_items) >= 10:
                break
        
        return low_items


def get_recent_sales(limit: int = 10) -> list[dict]:
    """Get recent sales and refund transactions."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Get sales
        sales = conn.execute(
            """
            SELECT 
                'sale' as type,
                sale_id as id,
                receipt_number as code,
                date,
                time,
                total as amount,
                (SELECT COUNT(*) FROM sales_items WHERE sale_id = s.sale_id) as items
            FROM sales s
            ORDER BY date DESC, time DESC
            LIMIT ?
            """,
            (limit * 2,)
        ).fetchall()
        
        # Get refunds
        refunds = conn.execute(
            """
            SELECT 
                'refund' as type,
                r.refund_id as id,
                r.refund_code as code,
                DATE(r.created_at) as date,
                TIME(r.created_at) as time,
                -r.refund_amount as amount,
                s.receipt_number as original_receipt,
                (SELECT COUNT(*) FROM sales_items WHERE sale_id = r.original_sale_id) as items
            FROM refunds r
            JOIN sales s ON r.original_sale_id = s.sale_id
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (limit * 2,)
        ).fetchall()
        
        # Combine and sort by date/time
        all_transactions = []
        for row in sales:
            all_transactions.append(dict(row))
        for row in refunds:
            all_transactions.append(dict(row))
        
        # Sort by date and time descending
        all_transactions.sort(key=lambda x: (x['date'], x['time']), reverse=True)
        
        return all_transactions[:limit]


def get_sales_trend_data(days: int = 7) -> list[dict]:
    """Get sales data for the last N days for charting (after refunds)."""
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
        
        # Get refunds by date
        refunds_rows = conn.execute(
            """
            SELECT 
                DATE(created_at) as date,
                COALESCE(SUM(refund_amount), 0) as refunded_amount
            FROM refunds
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY DATE(created_at)
            """,
            (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        ).fetchall()
        
        refunds_dict = {row["date"]: row["refunded_amount"] for row in refunds_rows}
        
        # Fill in missing dates with 0
        result = []
        current_date = start_date
        sales_dict = {row["date"]: dict(row) for row in rows}
        
        for i in range(days):
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in sales_dict:
                item = sales_dict[date_str]
                refunded = refunds_dict.get(date_str, 0)
                item["revenue"] = max(0, item["revenue"] - refunded)
                result.append(item)
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


def get_hourly_sales_data(date: str) -> list[dict]:
    """Get sales data grouped by hour for a specific date."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                substr(time, 1, 2) as hour,
                COUNT(*) as transactions,
                COALESCE(SUM(total), 0) as revenue
            FROM sales
            WHERE date = ?
            GROUP BY hour
            ORDER BY hour
            """,
            (date,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_sales_trend_data(days: int = 7) -> list[dict]:
    """Get sales data for the last N days."""
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        results = []
        for date in dates:
            row = conn.execute(
                """
                SELECT 
                    ? as date,
                    COALESCE(SUM(total), 0) as revenue
                FROM sales
                WHERE date = ?
                """,
                (date, date)
            ).fetchone()
            results.append(dict(row))
        return results
