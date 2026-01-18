#!/usr/bin/env python3
from database.init_db import get_connection

with get_connection() as conn:
    cursor = conn.cursor()
    # Remove the added column
    try:
        cursor.execute("ALTER TABLE settings DROP COLUMN example_column")
        print("Dropped example_column")
    except Exception as e:
        print(f"Error dropping column: {e}")
    
    # Remove the inserted settings
    cursor.execute("DELETE FROM settings WHERE key IN ('upgrade_demo_version', 'last_upgrade_applied')")
    print("Deleted upgrade settings")
    
    conn.commit()