import sqlite3

conn = sqlite3.connect('database/pos.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%reconciliation%'")
tables = cursor.fetchall()
print('Reconciliation tables in pos.db:', tables)

cursor = conn.execute("SELECT COUNT(*) FROM reconciliation_sessions")
count = cursor.fetchone()[0]
print('Reconciliation sessions count:', count)

conn.close()