"""Audit logging system for tracking user actions and data changes."""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional

from database.init_db import get_connection


AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    username TEXT,
    action TEXT NOT NULL,
    table_name TEXT,
    record_id INTEGER,
    old_values TEXT,
    new_values TEXT,
    ip_address TEXT,
    user_agent TEXT,
    session_id TEXT
);
"""


class AuditLogger:
    """Audit logger for tracking system activities."""

    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        """Ensure audit table exists."""
        with get_connection() as conn:
            conn.execute(AUDIT_TABLE)
            conn.commit()

    def log_action(self,
                   action: str,
                   user_id: Optional[int] = None,
                   username: Optional[str] = None,
                   table_name: Optional[str] = None,
                   record_id: Optional[int] = None,
                   old_values: Optional[Dict[str, Any]] = None,
                   new_values: Optional[Dict[str, Any]] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None,
                   session_id: Optional[str] = None) -> None:
        """
        Log an audit event.

        Args:
            action: The action performed (CREATE, UPDATE, DELETE, LOGIN, etc.)
            user_id: ID of the user performing the action
            username: Username of the user performing the action
            table_name: Name of the table affected
            record_id: ID of the record affected
            old_values: Previous values (for UPDATE operations)
            new_values: New values (for CREATE/UPDATE operations)
            ip_address: IP address of the client
            user_agent: User agent string
            session_id: Session identifier
        """
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO audit_log
                    (user_id, username, action, table_name, record_id, old_values, new_values,
                     ip_address, user_agent, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        action,
                        table_name,
                        record_id,
                        json.dumps(old_values) if old_values else None,
                        json.dumps(new_values) if new_values else None,
                        ip_address,
                        user_agent,
                        session_id
                    )
                )
                conn.commit()
        except Exception as e:
            # Log audit failure but don't crash the application
            print(f"Audit logging failed: {e}")

    def log_login(self, user_id: int, username: str, success: bool = True,
                  ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Log a login attempt."""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        self.log_action(action, user_id=user_id, username=username,
                       ip_address=ip_address, user_agent=user_agent)

    def log_logout(self, user_id: int, username: str,
                   ip_address: Optional[str] = None, session_id: Optional[str] = None) -> None:
        """Log a logout event."""
        self.log_action("LOGOUT", user_id=user_id, username=username,
                       ip_address=ip_address, session_id=session_id)

    def log_data_change(self, action: str, table_name: str, record_id: int,
                       user_id: Optional[int] = None, username: Optional[str] = None,
                       old_values: Optional[Dict[str, Any]] = None,
                       new_values: Optional[Dict[str, Any]] = None) -> None:
        """Log a data modification event."""
        self.log_action(action, user_id=user_id, username=username,
                       table_name=table_name, record_id=record_id,
                       old_values=old_values, new_values=new_values)

    def get_audit_trail(self, table_name: Optional[str] = None,
                       user_id: Optional[int] = None,
                       action: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> list[Dict[str, Any]]:
        """Retrieve audit trail entries with optional filtering."""
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if table_name:
            query += " AND table_name = ?"
            params.append(table_name)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if action:
            query += " AND action = ?"
            params.append(action)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

            results = []
            for row in rows:
                result = dict(row)
                # Parse JSON fields
                if result.get('old_values'):
                    result['old_values'] = json.loads(result['old_values'])
                if result.get('new_values'):
                    result['new_values'] = json.loads(result['new_values'])
                results.append(result)

            return results

    def cleanup_old_entries(self, days_to_keep: int = 365) -> int:
        """Remove audit entries older than specified days. Returns number of deleted entries."""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)

        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM audit_log WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count


# Global audit logger instance
audit_logger = AuditLogger()