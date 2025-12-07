"""User management helpers for authentication and seeding."""
from __future__ import annotations

import sqlite3
from typing import Optional

from database.init_db import get_connection
from utils.security import hash_password, verify_password


VALID_ROLES = {"admin", "cashier"}


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_users(*, include_inactive: bool = True) -> list[dict]:
    """Return all users as dicts."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if include_inactive:
            cursor = conn.execute("SELECT * FROM users ORDER BY username COLLATE NOCASE")
        else:
            cursor = conn.execute("SELECT * FROM users WHERE active = 1 ORDER BY username COLLATE NOCASE")
        return [_row_to_dict(row) for row in cursor.fetchall()]


def get_user_by_username(username: str, *, conn: sqlite3.Connection | None = None) -> Optional[dict]:
    """Return user as dict if it exists; None otherwise."""
    owns_conn = conn is None
    connection = conn or get_connection()
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        if owns_conn:
            connection.close()


def create_user(username: str, password: str, role: str = "cashier", active: bool = True) -> dict:
    """Create a new user with hashed password. Raises on invalid role or duplicate username."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    salt_hex, hash_hex = hash_password(password)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, password_salt, role, active) VALUES (?, ?, ?, ?, ?)",
            (username, hash_hex, salt_hex, role, int(active)),
        )
        conn.commit()
        created = get_user_by_username(username, conn=conn)
    if created is None:
        raise RuntimeError("User creation failed unexpectedly.")
    return created


def set_active(username: str, active: bool) -> Optional[dict]:
    with get_connection() as conn:
        conn.execute("UPDATE users SET active = ? WHERE username = ?", (int(active), username))
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return _row_to_dict(row) if row else None


def set_password(username: str, new_password: str) -> Optional[dict]:
    salt_hex, hash_hex = hash_password(new_password)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, password_salt = ? WHERE username = ?",
            (hash_hex, salt_hex, username),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return _row_to_dict(row) if row else None


def validate_credentials(username: str, password: str) -> Optional[dict]:
    """Return user dict on valid credentials; None otherwise."""
    user = get_user_by_username(username)
    if not user or not user.get("active"):
        return None

    salt_hex = user.get("password_salt")
    hash_hex = user.get("password_hash")
    if not salt_hex or not hash_hex:
        return None

    if not verify_password(password, salt_hex, hash_hex):
        return None

    return user


def ensure_admin_user(username: str = "admin", password: str = "admin123") -> dict:
    """Create a default admin if missing; returns the admin user."""
    existing = get_user_by_username(username)
    if existing:
        return existing
    return create_user(username=username, password=password, role="admin", active=True)


def change_own_password(username: str, old_password: str, new_password: str) -> bool:
    """Verify old password and set new one; returns True on success."""
    user = validate_credentials(username, old_password)
    if not user:
        return False
    set_password(username, new_password)
    return True
