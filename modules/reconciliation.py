"""Reconciliation module for financial reconciliation of sales data."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from database.init_db import get_connection
from modules import reports


@dataclass
class ReconciliationEntry:
    """Represents a reconciliation entry for a payment method."""
    payment_method: str
    system_amount: float
    actual_amount: float = 0.0
    variance: float = 0.0
    explanation: str = ""


@dataclass
class ReconciliationSession:
    """Represents a reconciliation session."""
    session_id: Optional[int]
    reconciliation_date: str
    period_type: str
    start_date: str
    end_date: str
    total_system_sales: float
    total_actual_cash: float
    total_variance: float
    status: str
    reconciled_by: Optional[int]
    reconciled_at: Optional[str]
    notes: str
    entries: List[ReconciliationEntry]


def get_sales_by_payment_method_for_period(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get sales breakdown by payment method for a specific period."""
    return reports.get_sales_by_payment_method(start_date, end_date)


def calculate_date_range(period_type: str, reference_date: str = None) -> Tuple[str, str]:
    """Calculate start and end dates for different period types."""
    if reference_date is None:
        reference_date = datetime.now().strftime("%Y-%m-%d")

    ref_date = datetime.strptime(reference_date, "%Y-%m-%d")

    if period_type == "daily":
        start_date = end_date = reference_date
    elif period_type == "weekly":
        # Start of week (Monday)
        start_of_week = ref_date - timedelta(days=ref_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_date = start_of_week.strftime("%Y-%m-%d")
        end_date = end_of_week.strftime("%Y-%m-%d")
    elif period_type == "monthly":
        # Start of month
        start_of_month = ref_date.replace(day=1)
        # End of month
        next_month = start_of_month.replace(month=start_of_month.month % 12 + 1, day=1)
        end_of_month = next_month - timedelta(days=1)
        start_date = start_of_month.strftime("%Y-%m-%d")
        end_date = end_of_month.strftime("%Y-%m-%d")
    elif period_type == "yearly":
        # Start of year
        start_of_year = ref_date.replace(month=1, day=1)
        # End of year
        end_of_year = ref_date.replace(month=12, day=31)
        start_date = start_of_year.strftime("%Y-%m-%d")
        end_date = end_of_year.strftime("%Y-%m-%d")
    else:
        # Custom - return the reference date as both start and end
        start_date = end_date = reference_date

    return start_date, end_date


def create_reconciliation_session(
    reconciliation_date: str,
    period_type: str,
    start_date: str,
    end_date: str,
    user_id: int
) -> int:
    """Create a new reconciliation session and return the session ID."""
    # Get sales data for the period
    sales_data = get_sales_by_payment_method_for_period(start_date, end_date)
    total_system_sales = sum(entry['total_sales'] for entry in sales_data)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reconciliation_sessions
            (reconciliation_date, period_type, start_date, end_date,
             total_system_sales, total_actual_cash, total_variance, status, reconciled_by)
            VALUES (?, ?, ?, ?, ?, 0, ?, 'draft', ?)
            """,
            (reconciliation_date, period_type, start_date, end_date,
             total_system_sales, -total_system_sales, user_id)
        )
        session_id = cursor.lastrowid

        # Create entries for each payment method
        for entry in sales_data:
            conn.execute(
                """
                INSERT INTO reconciliation_entries
                (session_id, payment_method, system_amount, actual_amount, variance)
                VALUES (?, ?, ?, 0, ?)
                """,
                (session_id, entry['payment_method'], entry['total_sales'], -entry['total_sales'])
            )

        conn.commit()
        return session_id


def get_reconciliation_session(session_id: int) -> Optional[ReconciliationSession]:
    """Get a reconciliation session by ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        # Get session data
        session_row = conn.execute(
            "SELECT * FROM reconciliation_sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()

        if not session_row:
            return None

        # Get entries
        entries_rows = conn.execute(
            "SELECT * FROM reconciliation_entries WHERE session_id = ? ORDER BY payment_method",
            (session_id,)
        ).fetchall()

        entries = [
            ReconciliationEntry(
                payment_method=row['payment_method'],
                system_amount=row['system_amount'],
                actual_amount=row['actual_amount'],
                variance=row['variance'],
                explanation=row.get('explanation', '')
            )
            for row in entries_rows
        ]

        return ReconciliationSession(
            session_id=session_row['session_id'],
            reconciliation_date=session_row['reconciliation_date'],
            period_type=session_row['period_type'],
            start_date=session_row['start_date'],
            end_date=session_row['end_date'],
            total_system_sales=session_row['total_system_sales'],
            total_actual_cash=session_row['total_actual_cash'],
            total_variance=session_row['total_variance'],
            status=session_row['status'],
            reconciled_by=session_row['reconciled_by'],
            reconciled_at=session_row['reconciled_at'],
            notes=session_row.get('notes', ''),
            entries=entries
        )


def update_reconciliation_entry(
    session_id: int,
    payment_method: str,
    actual_amount: float,
    explanation: str = ""
) -> None:
    """Update an entry in a reconciliation session."""
    variance = actual_amount - get_system_amount_for_payment_method(session_id, payment_method)

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE reconciliation_entries
            SET actual_amount = ?, variance = ?, explanation = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ? AND payment_method = ?
            """,
            (actual_amount, variance, explanation, session_id, payment_method)
        )
        conn.commit()

        # Update session totals
        _update_session_totals(session_id)


def get_system_amount_for_payment_method(session_id: int, payment_method: str) -> float:
    """Get the system amount for a payment method in a session."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT system_amount FROM reconciliation_entries WHERE session_id = ? AND payment_method = ?",
            (session_id, payment_method)
        ).fetchone()
        return row['system_amount'] if row else 0.0


def _update_session_totals(session_id: int) -> None:
    """Update the total actual cash and variance for a session."""
    with get_connection() as conn:
        # Calculate totals from entries
        totals = conn.execute(
            """
            SELECT
                SUM(actual_amount) as total_actual,
                SUM(variance) as total_variance
            FROM reconciliation_entries
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchone()

        conn.execute(
            """
            UPDATE reconciliation_sessions
            SET total_actual_cash = ?, total_variance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (totals['total_actual'] or 0, totals['total_variance'] or 0, session_id)
        )
        conn.commit()


def complete_reconciliation_session(session_id: int, user_id: int, notes: str = "") -> None:
    """Mark a reconciliation session as completed."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE reconciliation_sessions
            SET status = 'completed', reconciled_by = ?, reconciled_at = CURRENT_TIMESTAMP,
                notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (user_id, notes, session_id)
        )
        conn.commit()


def get_reconciliation_sessions(
    start_date: str = None,
    end_date: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get reconciliation sessions with optional filters."""
    query = """
        SELECT rs.*, u.username as reconciled_by_name
        FROM reconciliation_sessions rs
        LEFT JOIN users u ON rs.reconciled_by = u.user_id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND rs.reconciliation_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND rs.reconciliation_date <= ?"
        params.append(end_date)

    if status:
        query += " AND rs.status = ?"
        params.append(status)

    query += " ORDER BY rs.reconciliation_date DESC, rs.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def add_reconciliation_explanation(
    session_id: int,
    explanation_type: str,
    explanation: str,
    payment_method: str = None,
    amount: float = 0,
    user_id: int = None
) -> None:
    """Add an explanation/note to a reconciliation session."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reconciliation_explanations
            (session_id, explanation_type, payment_method, explanation, amount, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, explanation_type, payment_method, explanation, amount, user_id)
        )
        conn.commit()


def get_reconciliation_explanations(session_id: int) -> List[Dict[str, Any]]:
    """Get explanations for a reconciliation session."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT re.*, u.username as created_by_name
            FROM reconciliation_explanations re
            LEFT JOIN users u ON re.created_by = u.user_id
            WHERE re.session_id = ?
            ORDER BY re.created_at DESC
            """,
            (session_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_reconciliation_summary(period_type: str, reference_date: str = None) -> Dict[str, Any]:
    """Get a summary of reconciliation data for reporting."""
    start_date, end_date = calculate_date_range(period_type, reference_date)

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        # Get sessions for the period
        sessions = conn.execute(
            """
            SELECT * FROM reconciliation_sessions
            WHERE start_date >= ? AND end_date <= ? AND status = 'completed'
            ORDER BY reconciliation_date DESC
            """,
            (start_date, end_date)
        ).fetchall()

        total_sessions = len(sessions)
        total_variance = sum(session['total_variance'] for session in sessions)
        avg_variance = total_variance / total_sessions if total_sessions > 0 else 0

        return {
            'period_type': period_type,
            'start_date': start_date,
            'end_date': end_date,
            'total_sessions': total_sessions,
            'total_variance': total_variance,
            'avg_variance': avg_variance,
            'sessions': [dict(session) for session in sessions]
        }