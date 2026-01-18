#!/usr/bin/env python3
"""
Safe column addition script for loyalty points system.
This script checks if columns exist before adding them to avoid duplicate column errors.
"""

from database.init_db import get_connection

def add_column_if_not_exists(table_name, column_name, column_definition):
    """Add a column to a table if it doesn't already exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if column_name in column_names:
            print(f"Column '{column_name}' already exists in table '{table_name}', skipping...")
            return False

        # Add the column
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
            conn.commit()
            print(f"Added column '{column_name}' to table '{table_name}'")
            return True
        except Exception as e:
            print(f"Error adding column '{column_name}': {e}")
            return False

def main():
    """Main function to add loyalty columns safely."""
    print("Adding loyalty points columns to database...")

    # Add points_earned column to sales table
    add_column_if_not_exists(
        'sales',
        'points_earned',
        'points_earned INTEGER DEFAULT 0'
    )

    # Add points_redeemed column to sales table
    add_column_if_not_exists(
        'sales',
        'points_redeemed',
        'points_redeemed INTEGER DEFAULT 0'
    )

    print("Column addition completed.")

if __name__ == '__main__':
    main()