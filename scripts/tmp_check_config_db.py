import sqlite3, os
p='database/pos_54ed356e.db'
print('exists', os.path.exists(p))
conn=sqlite3.connect(p)
cur=conn.cursor()
print('sql', cur.execute("SELECT sql FROM sqlite_master WHERE type='table' and name='reconciliation_sessions'").fetchone()[0])
try:
    print('migrations', list(cur.execute('SELECT migration_id, name FROM schema_migrations').fetchall()))
except Exception as e:
    print('migrations table error', e)
conn.close()