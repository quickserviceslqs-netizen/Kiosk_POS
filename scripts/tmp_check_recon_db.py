import sqlite3, os
p='database/pos.db'
print('exists', os.path.exists(p))
conn=sqlite3.connect(p)
cur=conn.cursor()
print('cols', list(cur.execute('PRAGMA table_info(reconciliation_sessions)')))
print('statuses', list(cur.execute("SELECT DISTINCT status FROM reconciliation_sessions LIMIT 10")))
conn.close()