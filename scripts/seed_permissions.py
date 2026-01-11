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
    """Seed default permissions for all existing users."""
    print("Seeding default permissions for existing users...")

    # Initialize database
    app_dir = Path(__file__).parent
    config = get_or_create_config(app_dir)
    db_path = config.get('db_path', 'database/pos_test.db')
    os.environ['KIOSK_POS_DB_PATH'] = db_path
    initialize_database(Path(db_path))

    # Seed default permissions
    permissions.seed_default_permissions()

    print("Permission seeding completed!")
    print("\nDefault permissions assigned:")
    print("- Admins: All permissions")
    print("- Cashiers: POS, Dashboard, limited Inventory/Reports/Expenses access")

if __name__ == "__main__":
    seed_permissions()