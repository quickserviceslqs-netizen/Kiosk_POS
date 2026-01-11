#!/usr/bin/env python3
"""
Script to seed default permissions for existing users.
Run this after implementing the permission system.
"""

import sys
import os
# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from utils.app_config import get_or_create_config
from database.init_db import initialize_database
from modules import permissions

def seed_permissions():
    """Initialize the permission system and grant all permissions to admin users.

    This ensures the permissions table exists and admin users have full access.
    Other users require explicit permission grants through the Permission Management UI.
    """
    # Initialize database
    app_dir = Path(__file__).parent.parent
    config = get_or_create_config(app_dir)
    db_path = config.get('db_path', 'database/pos_test.db')
    os.environ['KIOSK_POS_DB_PATH'] = db_path
    initialize_database(Path(db_path))

    # Initialize permission system
    permissions.seed_default_permissions()

    # Grant all permissions to admin users
    from modules import users
    all_users = users.list_users()

    admin_users = [user for user in all_users if user['role'] == 'admin']
    if admin_users:
        print(f"\n🔑 Granting all permissions to {len(admin_users)} admin user(s):")
        for admin in admin_users:
            print(f"  - {admin['username']}")
            # Grant all permissions to admin users
            for perm in permissions.get_all_permissions().keys():
                permissions.grant_permission(admin['user_id'], perm, 0)  # System grant

        print("\n✅ Admin users now have full access to all features!")
    else:
        print("\n⚠️  No admin users found. Create an admin user first.")

    print("\n📋 Other users require explicit permission grants through Settings → 🔐 Permission Management.")
    print("Role suggestions are available in the UI for quick assignment.")

if __name__ == "__main__":
    seed_permissions()