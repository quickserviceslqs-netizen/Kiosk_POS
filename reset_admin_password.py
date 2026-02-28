#!/usr/bin/env python3
"""
Script to reset the admin password for development/testing purposes.
"""
from database.init_db import get_connection
from utils.security import hash_password

def reset_admin_password(new_password: str = "admin123"):
    """Reset the admin user's password to a known value."""
    salt_hex, hash_hex = hash_password(new_password)
    with get_connection() as conn:
        # Try both 'admin' and 'Admin'
        for username in ['admin', 'Admin']:
            conn.execute(
                "UPDATE users SET password_hash = ?, password_salt = ?, plain_password = ? WHERE username = ?",
                (hash_hex, salt_hex, new_password, username)
            )
        conn.commit()
        print(f"Admin password reset to: {new_password}")
        print("Username: check which one exists (admin or Admin)")

if __name__ == "__main__":
    reset_admin_password()