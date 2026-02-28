"""Database repository implementations for reconciliation."""
from __future__ import annotations
from typing import List, Optional
import sqlite3
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from database.init_db import get_connection
from ..domain.entities import (
    ReconciliationSession, ReconciliationEntry, VarianceExplanation,
    ReconciliationStatus, PeriodType
)
from ..domain.repositories.interfaces import (
    ReconciliationSessionRepository, VarianceExplanationRepository
)


class SQLiteReconciliationSessionRepository(ReconciliationSessionRepository):
    """SQLite implementation of reconciliation session repository."""

    def save(self, session: ReconciliationSession) -> int:
        """Save a session and return its ID."""
        with get_connection() as conn:
            cursor = conn.cursor()

            if session.session_id is None:
                # Insert new session
                cursor.execute("""
                    INSERT INTO reconciliation_sessions
                    (reconciliation_date, period_type, start_date, end_date,
                     total_system_sales, total_actual_cash, total_variance,
                     status, reconciled_by, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.date,
                    session.period_type.value,
                    session.start_date,
                    session.end_date,
                    session.total_system_amount,
                    session.total_actual_amount,
                    session.total_variance,
                    session.status.value,
                    session.created_by,
                    session.notes
                ))
                session_id = cursor.lastrowid

                # Insert entries
                for entry in session.entries:
                    cursor.execute("""
                        INSERT INTO reconciliation_entries
                        (session_id, payment_method, system_amount, actual_amount, variance,
                         reviewed, opening_balance, cash_out)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        entry.payment_method,
                        entry.system_amount,
                        entry.actual_amount,
                        entry.variance,
                        1 if entry.is_reviewed else 0,
                        getattr(entry, 'opening_balance', 0.0),
                        getattr(entry, 'cash_out', 0.0),
                    ))
            else:
                # Update existing session
                cursor.execute("""
                    UPDATE reconciliation_sessions
                    SET total_system_sales = ?, total_actual_cash = ?, total_variance = ?,
                        status = ?, reconciled_at = ?, notes = ?, updated_at = ?
                    WHERE session_id = ?
                """, (
                    session.total_system_amount,
                    session.total_actual_amount,
                    session.total_variance,
                    session.status.value,
                    session.completed_at.isoformat() if session.completed_at else None,
                    session.notes,
                    datetime.now().isoformat(),
                    session.session_id
                ))

                # Update entries
                for entry in session.entries:
                    cursor.execute("""
                        UPDATE reconciliation_entries
                        SET actual_amount = ?, variance = ?, reviewed = ?, explanation = ?,
                            opening_balance = ?, cash_out = ?
                        WHERE session_id = ? AND payment_method = ?
                    """, (
                        entry.actual_amount,
                        entry.variance,
                        1 if entry.is_reviewed else 0,
                        entry.notes,
                        getattr(entry, 'opening_balance', 0.0),
                        getattr(entry, 'cash_out', 0.0),
                        session.session_id,
                        entry.payment_method
                    ))

                session_id = session.session_id

            conn.commit()
            return session_id

    def find_by_id(self, session_id: int) -> Optional[ReconciliationSession]:
        """Find a session by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get session
            cursor.execute("""
                SELECT session_id, reconciliation_date, period_type, start_date, end_date,
                       total_system_sales, total_actual_cash, total_variance, status,
                       reconciled_by, reconciled_at, notes, created_at, updated_at
                FROM reconciliation_sessions WHERE session_id = ?
            """, (session_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # Get entries - fetch all relevant columns
            try:
                cursor.execute("""
                    SELECT payment_method, system_amount, actual_amount, variance,
                           reviewed, explanation, opening_balance, cash_out
                    FROM reconciliation_entries WHERE session_id = ?
                """, (session_id,))
                has_new_cols = True
            except Exception:
                try:
                    cursor.execute("""
                        SELECT payment_method, system_amount, actual_amount, variance, reviewed, explanation
                        FROM reconciliation_entries WHERE session_id = ?
                    """, (session_id,))
                    has_new_cols = False
                except Exception:
                    cursor.execute("""
                        SELECT payment_method, system_amount, actual_amount, variance
                        FROM reconciliation_entries WHERE session_id = ?
                    """, (session_id,))
                    has_new_cols = False

            entries = []
            for entry_row in cursor.fetchall():
                entries.append(ReconciliationEntry(
                    payment_method=entry_row[0],
                    system_amount=entry_row[1],
                    actual_amount=entry_row[2],
                    variance=entry_row[3],
                    is_reviewed=bool(entry_row[4]) if len(entry_row) > 4 else False,
                    notes=entry_row[5] if len(entry_row) > 5 and entry_row[5] else "",
                    opening_balance=float(entry_row[6]) if has_new_cols and len(entry_row) > 6 and entry_row[6] is not None else 0.0,
                    cash_out=float(entry_row[7]) if has_new_cols and len(entry_row) > 7 and entry_row[7] is not None else 0.0,
                ))

            # Get explanations
            cursor.execute("""
                SELECT explanation_id, payment_method, explanation, amount, created_by, created_at
                FROM reconciliation_explanations WHERE session_id = ?
            """, (session_id,))

            explanations = []
            for exp_row in cursor.fetchall():
                explanations.append(VarianceExplanation(
                    explanation_id=exp_row[0],
                    payment_method=exp_row[1],
                    explanation=exp_row[2],
                    amount=exp_row[3],
                    created_by=exp_row[4],
                    created_at=datetime.fromisoformat(exp_row[5]) if exp_row[5] else None
                ))

            return ReconciliationSession(
                session_id=row[0],
                date=row[1],
                period_type=PeriodType(row[2]),
                start_date=row[3],
                end_date=row[4],
                created_by=row[9],
                status=ReconciliationStatus(row[8]),
                completed_at=datetime.fromisoformat(row[10]) if row[10] else None,
                notes=row[11] or "",
                entries=entries,
                explanations=explanations,
                created_at=datetime.fromisoformat(row[12]) if row[12] else None,
                updated_at=datetime.fromisoformat(row[13]) if row[13] else None
            )

    def find_all(self, start_date: Optional[str] = None,
                end_date: Optional[str] = None,
                status: Optional[str] = None,
                limit: int = 50,
                offset: int = 0) -> List[ReconciliationSession]:
        """Find all sessions with optional filters."""
        with get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT session_id, reconciliation_date, period_type, start_date, end_date,
                       total_system_sales, total_actual_cash, total_variance, status,
                       reconciled_by, reconciled_at, notes, created_at, updated_at
                FROM reconciliation_sessions
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND reconciliation_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND reconciliation_date <= ?"
                params.append(end_date)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY reconciliation_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            sessions = []
            for row in rows:
                # Get entries for this session - fetch all relevant columns
                try:
                    cursor.execute("""
                        SELECT payment_method, system_amount, actual_amount, variance,
                               reviewed, explanation, opening_balance, cash_out
                        FROM reconciliation_entries WHERE session_id = ?
                    """, (row[0],))
                    has_new_cols = True
                except Exception:
                    try:
                        cursor.execute("""
                            SELECT payment_method, system_amount, actual_amount, variance, reviewed, explanation
                            FROM reconciliation_entries WHERE session_id = ?
                        """, (row[0],))
                        has_new_cols = False
                    except Exception:
                        cursor.execute("""
                            SELECT payment_method, system_amount, actual_amount, variance
                            FROM reconciliation_entries WHERE session_id = ?
                        """, (row[0],))
                        has_new_cols = False

                entries = []
                for entry_row in cursor.fetchall():
                    entries.append(ReconciliationEntry(
                        payment_method=entry_row[0],
                        system_amount=entry_row[1],
                        actual_amount=entry_row[2],
                        variance=entry_row[3],
                        is_reviewed=bool(entry_row[4]) if len(entry_row) > 4 else False,
                        notes=entry_row[5] if len(entry_row) > 5 and entry_row[5] else "",
                        opening_balance=float(entry_row[6]) if has_new_cols and len(entry_row) > 6 and entry_row[6] is not None else 0.0,
                        cash_out=float(entry_row[7]) if has_new_cols and len(entry_row) > 7 and entry_row[7] is not None else 0.0,
                    ))

                sessions.append(ReconciliationSession(
                    session_id=row[0],
                    date=row[1],
                    period_type=PeriodType(row[2]),
                    start_date=row[3],
                    end_date=row[4],
                    created_by=row[9],
                    status=ReconciliationStatus(row[8]),
                    completed_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    notes=row[11] or "",
                    entries=entries,
                    created_at=datetime.fromisoformat(row[12]) if row[12] else None,
                    updated_at=datetime.fromisoformat(row[13]) if row[13] else None
                ))

            return sessions

    def delete(self, session_id: int) -> None:
        """Delete a session."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reconciliation_explanations WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM reconciliation_entries WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM reconciliation_sessions WHERE session_id = ?", (session_id,))
            conn.commit()


class SQLiteVarianceExplanationRepository(VarianceExplanationRepository):
    """SQLite implementation of variance explanation repository."""

    def save(self, session_id: int, explanation: VarianceExplanation) -> int:
        """Save an explanation and return its ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reconciliation_explanations
                (session_id, explanation_type, payment_method, explanation, amount, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                'variance',  # explanation_type is required
                explanation.payment_method,
                explanation.explanation,
                explanation.amount,
                explanation.created_by,
                explanation.created_at.isoformat() if explanation.created_at else datetime.now().isoformat()
            ))
            explanation_id = cursor.lastrowid
            conn.commit()
            return explanation_id

    def find_by_session_id(self, session_id: int) -> List[VarianceExplanation]:
        """Find all explanations for a session."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT explanation_id, payment_method, explanation, amount, created_by, created_at
                FROM reconciliation_explanations WHERE session_id = ?
                ORDER BY created_at
            """, (session_id,))

            explanations = []
            for row in cursor.fetchall():
                explanations.append(VarianceExplanation(
                    explanation_id=row[0],
                    payment_method=row[1],
                    explanation=row[2],
                    amount=row[3],
                    created_by=row[4],
                    created_at=datetime.fromisoformat(row[5]) if row[5] else None
                ))

            return explanations

    def update(self, explanation_id: int, explanation: str, amount: float) -> None:
        """Update an explanation."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE reconciliation_explanations
                SET explanation = ?, amount = ?
                WHERE explanation_id = ?
            """, (explanation, amount, explanation_id))
            conn.commit()

    def delete(self, explanation_id: int) -> None:
        """Delete an explanation."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reconciliation_explanations WHERE explanation_id = ?", (explanation_id,))
            conn.commit()