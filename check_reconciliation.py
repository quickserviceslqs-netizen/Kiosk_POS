import sqlite3
from pathlib import Path

db_path = Path('database/pos.db')
with sqlite3.connect(db_path) as conn:
    cursor = conn.execute('SELECT name FROM sqlite_master WHERE type="table" AND name LIKE "%reconciliation%"')
    tables = cursor.fetchall()
    print('Reconciliation tables found:', tables)

    if not tables:
        print('No reconciliation tables found. Applying migration...')
        with open('migrations/20260118_add_reconciliation_tables.sql', 'r') as f:
            sql = f.read()
        conn.executescript(sql)
        conn.commit()
        print('Migration applied successfully')

        # Verify tables were created
        cursor = conn.execute('SELECT name FROM sqlite_master WHERE type="table" AND name LIKE "%reconciliation%"')
        tables = cursor.fetchall()
        print('Reconciliation tables after migration:', tables)