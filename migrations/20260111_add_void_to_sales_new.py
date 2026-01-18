"""
Database migration: Add void functionality to sales table
"""
import sqlite3
from database.init_db import DB_PATH

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Add void-related columns to sales table
    cur.execute("PRAGMA table_info(sales)")
    columns = [row[1] for row in cur.fetchall()]

    if "voided" not in columns:
        cur.execute("ALTER TABLE sales ADD COLUMN voided INTEGER NOT NULL DEFAULT 0 CHECK(voided IN (0,1))")

    if "void_reason" not in columns:
        cur.execute("ALTER TABLE sales ADD COLUMN void_reason TEXT")

    if "voided_by" not in columns:
        cur.execute("ALTER TABLE sales ADD COLUMN voided_by INTEGER REFERENCES users(user_id)")

    if "voided_at" not in columns:
        cur.execute("ALTER TABLE sales ADD COLUMN voided_at TEXT")

    # Add index for voided sales
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_voided ON sales(voided)")

    conn.commit()
    conn.close()
    print("Migration complete: void functionality added to sales table.")

if __name__ == "__main__":
    run()