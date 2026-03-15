"""Debug database schema and content."""
import sqlite3
import glob
from pathlib import Path

# Find the database file with actual data (largest)
db_files = glob.glob('database/pos_*.db')
if not db_files:
    print('No database found')
else:
    # Use the largest file (most likely has data)
    db_path = max(db_files, key=lambda f: Path(f).stat().st_size)
    print(f'Using database: {db_path}\n')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f'Tables in database: {len(tables)}\n')
    for table_name, in tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        count = cursor.fetchone()[0]
        print(f'  {table_name}: {count} records')
    
    print('\n--- Reconciliation Sessions ---')
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reconciliation_sessions'")
    if cursor.fetchone():
        print('Table exists')
        cursor.execute('SELECT * FROM reconciliation_sessions ORDER BY session_id DESC LIMIT 5')
        columns = [desc[0] for desc in cursor.description]
        print(f'Columns: {columns}')
        rows = cursor.fetchall()
        for row in rows:
            print(f'  {row}')
    else:
        print('Table does NOT exist')
    
    conn.close()
