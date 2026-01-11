"""Expense tracking data access helpers."""
from __future__ import annotations

import sqlite3
from typing import Optional
from datetime import datetime, date
import re

from database.init_db import get_connection


def _validate_date(date_str: str) -> str:
    """Validate and normalize date string to YYYY-MM-DD format."""
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date is required and must be a string")

    date_str = date_str.strip()
    if not date_str:
        raise ValueError("Date cannot be empty")

    # Try to parse the date
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format")

    # Check if date is not in the future (allow today)
    today = date.today()
    if parsed_date > today:
        raise ValueError("Expense date cannot be in the future")

    return date_str


def _validate_category(category: str) -> str:
    """Validate expense category."""
    if not category or not isinstance(category, str):
        raise ValueError("Category is required and must be a string")

    category = category.strip()
    if not category:
        raise ValueError("Category cannot be empty")

    if len(category) > 100:
        raise ValueError("Category name cannot exceed 100 characters")

    # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9\s\-_&]+$', category):
        raise ValueError("Category contains invalid characters")

    return category


def _validate_amount(amount: float) -> float:
    """Validate expense amount."""
    if amount is None:
        raise ValueError("Amount is required")

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        raise ValueError("Amount must be a valid number")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero")

    if amount > 999999.99:  # Reasonable upper limit
        raise ValueError("Amount cannot exceed 999,999.99")

    return round(amount, 2)


def _validate_description(description: str) -> Optional[str]:
    """Validate expense description."""
    if description is None:
        return None

    if not isinstance(description, str):
        raise ValueError("Description must be a string")

    description = description.strip()
    if not description:
        return None

    if len(description) > 500:
        raise ValueError("Description cannot exceed 500 characters")

    return description


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


def list_expenses_advanced(*, start_date: str = None, end_date: str = None, category: str = None,
                          min_amount: float = None, max_amount: float = None, search_text: str = None,
                          user_id: int = None, limit: int = None, offset: int = 0) -> list[dict]:
    """List expenses with advanced filtering and pagination."""
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
        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)
        if max_amount is not None:
            query += " AND amount <= ?"
            params.append(max_amount)
        if search_text:
            search_term = f"%{search_text}%"
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.extend([search_term, search_term])
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY date DESC, expense_id DESC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_expenses_count(*, start_date: str = None, end_date: str = None, category: str = None,
                      min_amount: float = None, max_amount: float = None, search_text: str = None,
                      user_id: int = None) -> int:
    """Get count of expenses matching advanced filters."""
    with get_connection() as conn:
        query = "SELECT COUNT(*) FROM expenses WHERE 1=1"
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
        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)
        if max_amount is not None:
            query += " AND amount <= ?"
            params.append(max_amount)
        if search_text:
            search_term = f"%{search_text}%"
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.extend([search_term, search_term])
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        row = conn.execute(query, params).fetchone()
    return row[0] if row else 0


def get_expense(expense_id: int) -> Optional[dict]:
    """Get a single expense by ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expenses WHERE expense_id = ?", (expense_id,)).fetchone()
    return _row_to_dict(row) if row else None


def create_expense(*, date: str, category: str, amount: float, description: str = "", user_id: int = None, username: str = None) -> dict:
    """Create a new expense record with user tracking."""
    # Validate inputs
    validated_date = _validate_date(date)
    validated_category = _validate_category(category)
    validated_amount = _validate_amount(amount)
    validated_description = _validate_description(description)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from utils.security import get_currency_code
    currency_code = get_currency_code()

    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (validated_category,))
        conn.execute(
            "INSERT INTO expenses (date, category, amount, description, user_id, username, created_at, currency_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (validated_date, validated_category, validated_amount, validated_description, user_id, username, created_at, currency_code)
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expenses WHERE rowid = last_insert_rowid()").fetchone()

    result = _row_to_dict(row)

    # Log audit event
    try:
        from utils.audit import audit_logger
        audit_logger.log_action(
            action="CREATE",
            username=username,
            table_name="expenses",
            record_id=result["expense_id"],
            old_values=None,
            new_values={
                "date": validated_date,
                "category": validated_category,
                "amount": validated_amount,
                "description": validated_description,
                "currency_code": currency_code
            }
        )
    except Exception:
        # Don't fail expense creation if audit logging fails
        pass

    return result


def update_expense(expense_id: int, **fields) -> Optional[dict]:
    """Update an expense record."""
    if not fields:
        return get_expense(expense_id)

    # Get current expense for audit logging
    current_expense = get_expense(expense_id)
    if not current_expense:
        return None

    # Validate allowed fields
    allowed = {"date", "category", "amount", "description", "currency_code"}
    updates = {}
    old_values = {}

    for k, v in fields.items():
        if k not in allowed:
            continue

        old_values[k] = current_expense.get(k)

        if k == "date":
            updates[k] = _validate_date(v)
        elif k == "category":
            updates[k] = _validate_category(v)
        elif k == "amount":
            updates[k] = _validate_amount(v)
        elif k == "description":
            updates[k] = _validate_description(v)
        elif k == "currency_code":
            updates[k] = v  # Basic validation for currency code

    if not updates:
        return current_expense

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    params = list(updates.values()) + [expense_id]

    with get_connection() as conn:
        if "category" in updates:
            conn.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (updates["category"],))
        conn.execute(f"UPDATE expenses SET {set_clause} WHERE expense_id = ?", params)
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expenses WHERE expense_id = ?", (expense_id,)).fetchone()

    result = _row_to_dict(row) if row else None

    # Log audit event
    if result:
        try:
            from utils.audit import audit_logger
            audit_logger.log_action(
                action="UPDATE",
                username=result.get("username"),
                table_name="expenses",
                record_id=expense_id,
                old_values=old_values,
                new_values=updates
            )
        except Exception:
            # Don't fail expense update if audit logging fails
            pass

    return result


def delete_expense(expense_id: int) -> None:
    """Delete an expense record."""
    # Get expense details for audit logging before deletion
    expense = get_expense(expense_id)
    if not expense:
        return

    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE expense_id = ?", (expense_id,))
        conn.commit()

    # Log audit event
    try:
        from utils.audit import audit_logger
        audit_logger.log_action(
            action="DELETE",
            username=expense.get("username"),
            table_name="expenses",
            record_id=expense_id,
            old_values={
                "date": expense.get("date"),
                "category": expense.get("category"),
                "amount": expense.get("amount"),
                "description": expense.get("description"),
                "currency_code": expense.get("currency_code")
            },
            new_values=None
        )
    except Exception:
        # Don't fail expense deletion if audit logging fails
        pass


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
        rows = conn.execute("SELECT name FROM expense_categories ORDER BY name").fetchall()
        if not rows:
            # Fallback/backfill from expenses if table is empty
            rows = conn.execute("SELECT DISTINCT category FROM expenses ORDER BY category").fetchall()
            for (cat,) in rows:
                conn.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (cat,))
            conn.commit()
        # Ensure an Uncategorized bucket exists for safe reassignments
        conn.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", ("Uncategorized",))
        conn.commit()
    return [row[0] for row in rows]


def add_expense_category(name: str) -> dict:
    """Add a new expense category (idempotent)."""
    clean = (name or "").strip()
    if not clean:
        raise ValueError("Category name is required")
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (clean,))
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expense_categories WHERE name = ?", (clean,)).fetchone()

    result = _row_to_dict(row) if row else {"name": clean}

    # Log audit event
    try:
        from utils.audit import audit_logger
        audit_logger.log_action(
            action="CREATE",
            table_name="expense_categories",
            record_id=result.get("category_id"),
            old_values=None,
            new_values={"name": clean}
        )
    except Exception:
        pass

    return result


def rename_expense_category(old_name: str, new_name: str) -> dict:
    """Rename a category and update expenses to the new name."""
    old_clean = (old_name or "").strip()
    new_clean = (new_name or "").strip()
    if not old_clean or not new_clean:
        raise ValueError("Both old and new category names are required")
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (new_clean,))
        conn.execute("UPDATE expense_categories SET name = ? WHERE name = ?", (new_clean, old_clean))
        conn.execute("UPDATE expenses SET category = ? WHERE category = ?", (new_clean, old_clean))
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM expense_categories WHERE name = ?", (new_clean,)).fetchone()

    result = _row_to_dict(row) if row else {"name": new_clean}

    # Log audit event
    try:
        from utils.audit import audit_logger
        audit_logger.log_action(
            action="UPDATE",
            table_name="expense_categories",
            record_id=result.get("category_id"),
            old_values={"name": old_clean},
            new_values={"name": new_clean}
        )
    except Exception:
        pass

    return result


def delete_expense_category(name: str, *, reassign_to: str = "Uncategorized") -> None:
    """Delete a category and reassign existing expenses to a fallback bucket."""
    target = (name or "").strip()
    fallback = (reassign_to or "Uncategorized").strip()
    if not target:
        raise ValueError("Category name is required")
    with get_connection() as conn:
        # Ensure fallback exists
        conn.execute("INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (fallback,))
        # Reassign expenses first
        conn.execute("UPDATE expenses SET category = ? WHERE category = ?", (fallback, target))
        # Delete the category entry
        conn.execute("DELETE FROM expense_categories WHERE name = ?", (target,))
        conn.commit()

    # Log audit event
    try:
        from utils.audit import audit_logger
        audit_logger.log_action(
            action="DELETE",
            table_name="expense_categories",
            old_values={"name": target, "reassigned_to": fallback},
            new_values=None
        )
    except Exception:
        pass
