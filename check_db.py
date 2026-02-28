import sqlite3
conn = sqlite3.connect('database/pos_54ed356e.db')
cursor = conn.cursor()
tables = cursor.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()
print('Tables:', [t[0] for t in tables])
try:
    cursor.execute('SELECT COUNT(*) FROM stock_movements')
    print('Stock movements count:', cursor.fetchone()[0])
except Exception as e:
    print('Error checking stock_movements:', e)
conn.close()