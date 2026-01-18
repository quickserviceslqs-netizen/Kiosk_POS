import sqlite3
from pathlib import Path

db_path = Path('database/pos.db')
with sqlite3.connect(db_path) as conn:
    cursor = conn.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()
    print('All tables in database:')
    for table in tables:
        print(f'  {table[0]}')

    # Check if sales table exists
    cursor = conn.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="sales"')
    sales_table = cursor.fetchone()
    print(f'\nSales table exists: {sales_table is not None}')

    if sales_table:
        # Check sales table structure
        cursor = conn.execute('PRAGMA table_info(sales)')
        columns = cursor.fetchall()
        print('Sales table columns:')
        for col in columns:
            print(f'  {col[1]} ({col[2]})')