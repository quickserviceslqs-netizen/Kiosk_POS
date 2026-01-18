"""Permission management system for granular access control."""
from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional, Set
from database.init_db import get_connection
from utils.audit import audit_logger


# Define all available permissions
PERMISSIONS = {
    # Dashboard permissions
    "view_dashboard": "View dashboard and analytics",

    # POS permissions
    "access_pos": "Access Point of Sale interface",
    "process_sales": "Process sales transactions",
    "apply_discounts": "Apply discounts to sales",
    "void_sales": "Void/cancel sales",

    # Inventory permissions
    "view_inventory": "View inventory items",
    "add_inventory": "Add new inventory items",
    "edit_inventory": "Edit existing inventory items",
    "delete_inventory": "Delete inventory items",
    "adjust_stock": "Adjust stock levels",
    "view_low_stock": "View low stock alerts",
    "add_categories": "Add new item categories",
    "delete_categories": "Delete item categories",

    # Reports permissions
    "view_reports": "View sales and inventory reports",
    "export_reports": "Export reports to files",
    "view_profit_reports": "View profit/loss reports",

    # Order history permissions
    "view_order_history": "View past orders",
    "refund_orders": "Process refunds",

    # Expense permissions
    "view_expenses": "View expense records",
    "add_expenses": "Add new expenses",
    "edit_expenses": "Edit existing expenses",
    "delete_expenses": "Delete expenses",
    "add_expense_categories": "Add new expense categories",
    "delete_expense_categories": "Delete expense categories",

    # User management permissions
    "view_users": "View user accounts",
    "manage_users": "Create/edit/delete users",
    "manage_roles": "Assign user roles",

    # Settings permissions
    "view_settings": "View system settings",
    "manage_settings": "Modify system settings",
    "manage_upgrades": "Upload and apply system upgrades",
    "manage_permissions": "Manage user permissions",

    # System permissions
    "backup_database": "Create database backups",
    "view_audit_logs": "View audit logs",
    "system_info": "View system information",
}


# Default permission sets for roles
DEFAULT_ROLE_PERMISSIONS = {
    "admin": set(PERMISSIONS.keys()),  # Admins get all permissions

    "cashier": {
        # Dashboard
        "view_dashboard",

        # POS
        "access_pos",
        "process_sales",

        # Inventory (read-only)
        "view_inventory",
        "view_low_stock",

        # Reports (limited)
        "view_reports",

        # Order history
        "view_order_history",

        # Expenses (add only)
        "view_expenses",
        "add_expenses",

        # Limited settings
        "view_settings",
    }
}


def _ensure_permissions_table() -> None:
    """Ensure the permissions table exists."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id INTEGER NOT NULL,
                permission TEXT NOT NULL,
                granted INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, permission),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_user_permissions(user_id: int) -> Set[str]:
    """Get all permissions granted to a user."""
    _ensure_permissions_table()

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT permission FROM user_permissions WHERE user_id = ? AND granted = 1",
            (user_id,)
        )
        return {row['permission'] for row in cursor.fetchall()}


def get_revoked_permissions(user_id: int) -> Set[str]:
    """Get all permissions explicitly revoked from a user."""
    _ensure_permissions_table()

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT permission FROM user_permissions WHERE user_id = ? AND granted = 0",
            (user_id,)
        )
        return {row['permission'] for row in cursor.fetchall()}


def get_role_permissions(role: str) -> Set[str]:
    """Get default permissions for a role."""
    return DEFAULT_ROLE_PERMISSIONS.get(role, set())


def get_effective_permissions(user: dict) -> Set[str]:
    """Get effective permissions for a user."""
    if not user:
        return set()

    user_id = user.get('user_id')
    role = user.get('role', 'cashier')

    if role == 'admin':
        # Admin users get all permissions by default, but can have explicit revocations
        all_perms = set(PERMISSIONS.keys())
        if user_id:
            # Check for explicit revocations (granted=0)
            revoked_perms = get_revoked_permissions(user_id)
            return all_perms - revoked_perms
        return all_perms

    # For non-admin users, only return explicitly granted permissions
    if user_id:
        return get_user_permissions(user_id)

    return set()


def has_permission(user: dict, permission: str) -> bool:
    """Check if a user has a specific permission."""
    effective_perms = get_effective_permissions(user)
    return permission in effective_perms


def grant_permission(user_id: int, permission: str, granted_by: int = None) -> None:
    """Grant a permission to a user."""
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")

    _ensure_permissions_table()

    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO user_permissions (user_id, permission, granted, updated_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        """, (user_id, permission))
        conn.commit()

    # Audit the permission change
    audit_logger.log_action(
        table_name="user_permissions",
        action="GRANT",
        record_id=f"{user_id}:{permission}",
        user_id=granted_by
    )


def revoke_permission(user_id: int, permission: str, revoked_by: int = None) -> None:
    """Revoke a permission from a user."""
    _ensure_permissions_table()

    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO user_permissions (user_id, permission, granted, updated_at)
            VALUES (?, ?, 0, CURRENT_TIMESTAMP)
        """, (user_id, permission))
        conn.commit()

    # Audit the permission change
    audit_logger.log_action(
        table_name="user_permissions",
        action="REVOKE",
        record_id=f"{user_id}:{permission}",
        user_id=revoked_by
    )


def reset_user_permissions(user_id: int, role: str, reset_by: int = None) -> None:
    """Reset user permissions by revoking all permissions (no automatic granting)."""
    _ensure_permissions_table()

    # Remove all user-specific permissions (no automatic role defaults)
    with get_connection() as conn:
        conn.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        conn.commit()

    # Audit the reset
    audit_logger.log_action(
        table_name="user_permissions",
        action="RESET",
        record_id=str(user_id),
        user_id=reset_by
    )


def seed_default_permissions() -> None:
    """Initialize permission system without automatically granting permissions.

    This function now only ensures the permissions table exists.
    Permissions should be explicitly granted by admins through the UI.
    """
    _ensure_permissions_table()
    print("Permission system initialized. No automatic permissions granted.")
    print("Use the Permission Management UI to grant permissions to users.")


def get_all_permissions() -> Dict[str, str]:
    """Get all available permissions with descriptions."""
    return PERMISSIONS.copy()


def get_permission_matrix() -> List[Dict]:
    """Get permission matrix showing users and their permissions."""
    from modules import users

    _ensure_permissions_table()

    all_users = users.list_users()
    all_perms = list(PERMISSIONS.keys())

    matrix = []
    for user in all_users:
        user_perms = get_user_permissions(user['user_id'])
        role_perms = get_role_permissions(user['role'])
        effective_perms = user_perms.union(role_perms)

        matrix.append({
            'user': user,
            'role_permissions': role_perms,
            'user_permissions': user_perms,
            'effective_permissions': effective_perms,
            'all_permissions': set(all_perms)
        })

    return matrix