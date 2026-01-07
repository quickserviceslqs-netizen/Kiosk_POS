import sqlite3
conn = sqlite3.connect('database/kioskpos.db')
cur = conn.cursor()
print('id | name | unit | unit_size_ml')
for row in cur.execute('SELECT id, name, unit, unit_size_ml FROM units'):
    print('{} | {} | {} | {}'.format(*row))
conn.close()
