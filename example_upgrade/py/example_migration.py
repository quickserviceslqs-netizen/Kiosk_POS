#!/usr/bin/env python3
"""
Example Python migration script for the upgrade system.
This demonstrates how to perform complex migrations using Python.
"""

import sys
import os
from pathlib import Path
import sqlite3

def main():
    print("Running example Python migration...")

    # Get the application directory
    app_dir = Path(__file__).parent.parent.parent  # Go up to Kiosk_POS directory
    print(f"Application directory: {app_dir}")

    # Database path
    db_path = app_dir / "database" / "kiosk_pos.db"
    print(f"Database path: {db_path}")

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check if example_column exists
        cursor.execute("PRAGMA table_info(settings)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'example_column' not in columns:
            print("Adding example_column to settings table...")
            cursor.execute("ALTER TABLE settings ADD COLUMN example_column TEXT DEFAULT 'upgrade_demo'")
            print("Column added successfully")
        else:
            print("example_column already exists, skipping...")

        # Insert sample settings
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('upgrade_demo_version', '1.0.1')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('last_upgrade_applied', datetime('now'))")

        conn.commit()
        print("Settings updated successfully")

    except Exception as e:
        print(f"Database operation failed: {e}")
        conn.rollback()
        return 1
    finally:
        conn.close()

    # Example: Create a backup marker file
    marker_file = app_dir / "upgrade_marker.txt"
    with open(marker_file, 'w') as f:
        f.write("This file was created by the upgrade system on " + __import__('datetime').datetime.now().isoformat())

    print(f"Created marker file: {marker_file}")

    # Example: Check if certain files exist
    config_file = app_dir / "email_config.json"
    if config_file.exists():
        print("Email configuration found")
    else:
        print("Email configuration not found (this is normal)")

    print("Python migration completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())