from database.init_db import get_connection

conn = get_connection()
cursor = conn.execute('PRAGMA table_info(reconciliation_entries)')
columns = [col[1] for col in cursor.fetchall()]
print('reviewed in entries:', 'reviewed' in columns)
if 'reviewed' not in columns:
    conn.execute('ALTER TABLE reconciliation_entries ADD COLUMN reviewed INTEGER NOT NULL DEFAULT 0')
    conn.commit()
    print('Added reviewed to entries')
conn.close()