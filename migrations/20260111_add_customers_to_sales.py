"""
Database migration: Add customers table and customer_id to sales table
"""
import sqlite3
from database.init_db import DB_PATH

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 1. Create customers table if not exists
    cur.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 2. Add customer_id to sales table if not exists
    cur.execute("PRAGMA table_info(sales)")
    columns = [row[1] for row in cur.fetchall()]
    if "customer_id" not in columns:
        cur.execute("ALTER TABLE sales ADD COLUMN customer_id INTEGER REFERENCES customers(customer_id)")
    conn.commit()
    conn.close()
    print("Migration complete: customers table and customer_id in sales.")

if __name__ == "__main__":
    run()
