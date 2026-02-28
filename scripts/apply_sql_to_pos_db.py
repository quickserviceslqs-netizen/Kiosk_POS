import sqlite3
p='database/pos.db'
with open('migrations/20260208_add_rejected_status.sql','r',encoding='utf-8') as f:
    sql=f.read()
conn=sqlite3.connect(p)
cur=conn.cursor()
try:
    cur.executescript(sql)
    conn.commit()
    print('applied')
except Exception as e:
    print('error', e)
finally:
    conn.close()