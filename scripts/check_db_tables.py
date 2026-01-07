import sqlite3, pathlib
for p in pathlib.Path('database').glob('*.db'):
    print('DB:', p)
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print('  tables:', tables)
    conn.close()