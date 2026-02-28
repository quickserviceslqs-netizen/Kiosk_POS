import sqlite3
conn=sqlite3.connect('database/pos.db')
cur=conn.cursor()
try:
    rows=list(cur.execute('SELECT migration_id, name, applied_at FROM schema_migrations'))
    print('migrations', rows)
except Exception as e:
    print('error', e)
conn.close()