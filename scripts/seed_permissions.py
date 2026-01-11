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
    """Initialize the permission system without automatically granting permissions.

    This ensures the permissions table exists but does not grant any permissions.
    Permissions should be explicitly managed by admins through the Permission Management UI.
    """
    # Initialize database
    app_dir = Path(__file__).parent.parent
    config = get_or_create_config(app_dir)
    db_path = config.get('db_path', 'database/pos_test.db')
    os.environ['KIOSK_POS_DB_PATH'] = db_path
    initialize_database(Path(db_path))

    # Initialize permission system (no automatic grants)
    permissions.seed_default_permissions()

    print("\nPermission system initialized!")
    print("⚠️  No permissions were automatically granted.")
    print("📋 Use Settings → 🔐 Permission Management to grant permissions to users.")
    print("\nRole suggestions are available in the UI for quick assignment.")

if __name__ == "__main__":
    seed_permissions()