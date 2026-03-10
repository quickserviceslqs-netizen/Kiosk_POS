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
    "receive_stock": "Receive stock with lot tracking",
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

    # Customer management permissions
    "view_customers": "View customer records",
    "add_customers": "Add new customers",
    "edit_customers": "Edit customer information",
    "delete_customers": "Delete customer records",

    # Cart management permissions
    "view_cart": "View shopping cart",
    "manage_suspended_carts": "Manage suspended carts",

    # Reconciliation permissions
    "view_reconciliation": "View financial reconciliation",
    "create_reconciliation": "Create reconciliation sessions",
    "edit_reconciliation": "Edit reconciliation data",
    "approve_reconciliation": "Approve reconciliation sessions",
    "view_reconciliation_reports": "View reconciliation reports",

    # External accounts permissions
    "view_external_accounts": "View external account balances",
    "manage_external_accounts": "Configure external account integrations",

    # User management permissions
    "view_users": "View user accounts",
    "manage_users": "Create/edit/delete users",

    # Permission management permissions
    "manage_permissions": "Manage user permissions",

    # Settings permissions
    "view_settings": "View system settings",
    "manage_settings": "Modify system settings",
    "manage_upgrades": "Upload and apply system upgrades",
    "view_system_info": "View system information",
    "manage_vat_settings": "Manage VAT rate settings",
    "manage_uom_settings": "Manage units of measure",
    "manage_email_settings": "Manage email notification settings",
    "manage_currency_settings": "Manage currency settings",
    "manage_date_format": "Manage date format settings",
    "manage_receipt_settings": "Manage receipt printing settings",
    "manage_pos_settings": "Manage POS behavior settings",
    "manage_report_settings": "Manage report display settings",
    "manage_inventory_settings": "Manage inventory alert settings",

    # System permissions
    "backup_database": "Create database backups",
    "restore_database": "Restore database from backups",
    "view_backup_schedules": "View backup schedules",
    "view_audit_logs": "View audit logs",
    "export_audit_logs": "Export audit logs",
    "change_own_password": "Change own password",

    # Purchase Order permissions
    "create_purchase_orders": "Create and manage purchase orders (LPO/PO)",
    "view_purchase_orders": "View purchase order history",
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

        # Customers (basic)
        "view_customers",
        "add_customers",

        # Cart
        "view_cart",

        # Limited settings
        "view_settings",
        "change_own_password",
    },

    "manager": {
        # Dashboard
        "view_dashboard",

        # POS
        "access_pos",
        "process_sales",
        "apply_discounts",
        "void_sales",

        # Inventory
        "view_inventory",
        "add_inventory",
        "edit_inventory",
        "adjust_stock",
        "receive_stock",
        "view_low_stock",
        "add_categories",

        # Reports
        "view_reports",
        "export_reports",
        "view_profit_reports",

        # Order history
        "view_order_history",
        "refund_orders",

        # Expenses
        "view_expenses",
        "add_expenses",
        "edit_expenses",
        "add_expense_categories",

        # Customers
        "view_customers",
        "add_customers",
        "edit_customers",

        # Cart
        "view_cart",
        "manage_suspended_carts",

        # Reconciliation (view only)
        "view_reconciliation",
        "view_reconciliation_reports",

        # External accounts (view only)
        "view_external_accounts",

        # Users (view only)
        "view_users",

        # Settings
        "view_settings",
        "manage_date_format",
        "manage_receipt_settings",
        "manage_pos_settings",
        "manage_report_settings",
        "manage_inventory_settings",
        "change_own_password",

        # System
        "backup_database",
        "view_audit_logs",
        "view_system_info",

        # Purchase Orders
        "create_purchase_orders",
        "view_purchase_orders",
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


def get_effective_permissions(user: dict | str) -> Set[str]:
    """Get effective permissions for a user.
    
    Args:
        user: User dictionary or username string
    
    Returns:
        Set of effective permission strings
    """
    if not user:
        return set()

    # Handle string username - convert to user dict
    if isinstance(user, str):
        from modules.users import get_user_by_username
        user = get_user_by_username(user)
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

    # For non-admin users, combine role defaults with explicitly granted/revoked permissions
    role_perms = get_role_permissions(role)

    if user_id:
        # Get explicitly granted permissions
        granted_perms = get_user_permissions(user_id)
        # Get explicitly revoked permissions
        revoked_perms = get_revoked_permissions(user_id)

        # Combine: role permissions + granted permissions - revoked permissions
        return (role_perms | granted_perms) - revoked_perms

    # No user_id, just return role permissions
    return role_perms


def has_permission(user: dict | str, permission: str) -> bool:
    """Check if a user has a specific permission.
    
    Args:
        user: User dictionary or username string
        permission: Permission name to check
    
    Returns:
        True if user has the permission, False otherwise
    """
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