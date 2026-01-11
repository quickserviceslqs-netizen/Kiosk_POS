import sqlite3
import os

# Check both database files
for db_file in ['database/pos.db', 'database/pos_54ed356e.db']:
    if os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        tables = [row[0] for row in conn.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()]
        print(f'{db_file} tables:', tables)
        if 'customers' in tables:
            print(f'Customers table found in {db_file}')
        else:
            print(f'Customers table NOT found in {db_file}')
        conn.close()