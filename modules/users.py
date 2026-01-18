"""User management helpers for authentication and seeding."""
from __future__ import annotations

import sqlite3
from typing import Optional

from database.init_db import get_connection
from utils.security import hash_password, verify_password
from utils.audit import audit_logger


VALID_ROLES = {"admin", "cashier"}


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength requirements.
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    # Check for common weak passwords
    weak_passwords = ["password", "123456", "admin123", "password123", "qwerty", "letmein"]
    if password.lower() in weak_passwords:
        return False, "Password is too common and easily guessable"

    return True, ""


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

    # Validate password strength
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise ValueError(f"Password validation failed: {error_msg}")

    salt_hex, hash_hex = hash_password(password)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, password_salt, plain_password, role, active) VALUES (?, ?, ?, ?, ?, ?)",
            (username, hash_hex, salt_hex, password, role, int(active)),
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


def delete_user(username: str) -> tuple[bool, str]:
    """Delete a user. Returns (success, message)."""
    # Prevent deleting the admin user
    if username.lower() == "admin":
        return False, "Cannot delete the admin user"

    with get_connection() as conn:
        # Check if user has sales records
        sales_count = conn.execute("SELECT COUNT(*) FROM sales WHERE user_id = (SELECT user_id FROM users WHERE username = ?)", (username,)).fetchone()[0]
        if sales_count > 0:
            return False, f"Cannot delete user with {sales_count} sales records. Deactivate instead."

        # Check if user has expense records
        expense_count = conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = (SELECT user_id FROM users WHERE username = ?)", (username,)).fetchone()[0]
        if expense_count > 0:
            return False, f"Cannot delete user with {expense_count} expense records. Deactivate instead."

        # Delete the user
        cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()

        if cursor.rowcount > 0:
            return True, f"User '{username}' deleted successfully"
        else:
            return False, f"User '{username}' not found"


def set_password(username: str, new_password: str) -> Optional[dict]:
    salt_hex, hash_hex = hash_password(new_password)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, password_salt = ?, plain_password = ? WHERE username = ?",
            (hash_hex, salt_hex, new_password, username),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return _row_to_dict(row) if row else None


def validate_credentials(username: str, password: str) -> Optional[dict]:
    """Return user dict on valid credentials; None otherwise."""
    user = get_user_by_username(username)
    if not user or not user.get("active"):
        # Log failed login attempt
        audit_logger.log_login(None, username, success=False)
        return None

    salt_hex = user.get("password_salt")
    hash_hex = user.get("password_hash")
    if not salt_hex or not hash_hex:
        audit_logger.log_login(user.get("user_id"), username, success=False)
        return None

    if not verify_password(password, salt_hex, hash_hex):
        audit_logger.log_login(user.get("user_id"), username, success=False)
        return None

    # Log successful login
    audit_logger.log_login(user.get("user_id"), username, success=True)
    return user


def ensure_admin_user(username: str = "admin", password: str | None = None) -> dict:
    """
    Create a default admin if missing; returns the admin user.
    If password is None, will prompt for a strong password during first setup.
    """
    existing = get_user_by_username(username)
    if existing:
        return existing

    if password is None:
        raise ValueError("Admin password must be provided during initial setup. Please set a strong password.")

    return create_user(username=username, password=password, role="admin", active=True)


def change_own_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """Verify old password and set new one; returns (success, message)."""
    user = validate_credentials(username, old_password)
    if not user:
        return False, "Current password is incorrect"

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        return False, error_msg

    set_password(username, new_password)
    
    # Audit logging
    audit_logger.log_action("PASSWORD_CHANGE", user_id=user.get("user_id"), username=username)
    
    return True, "Password changed successfully"


def log_user_logout(user_id: int, username: str) -> None:
    """Log user logout event."""
    audit_logger.log_logout(user_id, username)
