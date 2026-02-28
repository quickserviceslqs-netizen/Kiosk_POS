import sqlite3
p='database/pos.db'
conn=sqlite3.connect(p)
cur=conn.cursor()
row=cur.execute('SELECT session_id, status FROM reconciliation_sessions LIMIT 1').fetchone()
print('sample', row)
try:
    cur.execute("UPDATE reconciliation_sessions SET status='rejected' WHERE session_id=?", (row[0],))
    conn.commit()
    print('update succeeded')
except Exception as e:
    print('error', type(e), e)
finally:
    conn.close()