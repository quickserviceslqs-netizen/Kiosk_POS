import tempfile, sqlite3, os, shutil


td = tempfile.mkdtemp()
db = os.path.join(td, 'pos_test.db')
conn = sqlite3.connect(db)
conn.execute('CREATE TABLE IF NOT EXISTS t_upgrade (id integer primary key)')
conn.commit()
conn.close()
print('size after commit:', os.path.getsize(db))
conn2 = sqlite3.connect(db)
print('tables:', [r[0] for r in conn2.execute("SELECT name FROM sqlite_master WHERE type='table'")])
conn2.close()
shutil.rmtree(td)
