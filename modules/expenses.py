"""Expense tracking data access helpers."""
from __future__ import annotations

import sqlite3
from typing import Optional
from datetime import datetime

from database.init_db import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_expenses(start_date: str = None, end_date: str = None, category: str = None) -> list[dict]:
    """List expenses with optional filters."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY date DESC, expense_id DESC"
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_expense(expense_id: int) -> Optional[dict]:
    """Get a single expense by ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expenses WHERE expense_id = ?", (expense_id,)).fetchone()
    return _row_to_dict(row) if row else None


def create_expense(*, date: str, category: str, amount: float, description: str = "", user_id: int = None, username: str = None) -> dict:
    """Create a new expense record with user tracking."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO expenses (date, category, amount, description, user_id, username, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, category, amount, description, user_id, username, created_at)
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expenses WHERE rowid = last_insert_rowid()").fetchone()
    return _row_to_dict(row)


def update_expense(expense_id: int, **fields) -> Optional[dict]:
    """Update an expense record."""
    if not fields:
        return get_expense(expense_id)
    
    allowed = {"date", "category", "amount", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_expense(expense_id)
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    params = list(updates.values()) + [expense_id]
    
    with get_connection() as conn:
        conn.execute(f"UPDATE expenses SET {set_clause} WHERE expense_id = ?", params)
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expenses WHERE expense_id = ?", (expense_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_expense(expense_id: int) -> None:
    """Delete an expense record."""
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE expense_id = ?", (expense_id,))
        conn.commit()


def get_expense_summary(start_date: str, end_date: str) -> dict:
    """Get expense summary for a date range."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT 
                COUNT(*) as total_count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()
    return _row_to_dict(row) if row else {}


def get_expenses_by_category(start_date: str, end_date: str) -> list[dict]:
    """Get expenses grouped by category."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT 
                category,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total_amount DESC
            """,
            (start_date, end_date)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_expense_categories() -> list[str]:
    """Get all unique expense categories."""
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM expenses ORDER BY category").fetchall()
    return [row[0] for row in rows]
