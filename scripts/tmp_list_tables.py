import sqlite3
conn=sqlite3.connect('database/pos.db')
cur=conn.cursor()
print(cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name LIKE 'reconciliation_sessions%';").fetchall())
conn.close()