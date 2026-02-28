import sqlite3
conn = sqlite3.connect('database/pos_54ed356e.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
all_tables = [row[0] for row in cursor.fetchall()]
recon_tables = [t for t in all_tables if 'recon' in t.lower()]
print('Reconciliation tables:', recon_tables)
conn.close()