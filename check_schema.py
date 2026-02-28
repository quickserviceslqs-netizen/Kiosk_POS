from database.init_db import get_connection

conn = get_connection()
cursor = conn.execute('PRAGMA table_info(reconciliation_sessions)')
columns = cursor.fetchall()
print('Columns in reconciliation_sessions:')
for col in columns:
    print(col)
conn.close()