import sqlite3
conn=sqlite3.connect('database/pos.db')
cur=conn.cursor()
row=cur.execute("SELECT sql FROM sqlite_master WHERE type='table' and name='reconciliation_sessions'").fetchone()
print(row[0])
conn.close()