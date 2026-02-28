from database.init_db import get_connection
conn = get_connection()
cursor = conn.execute('SELECT username, active, role FROM users')
users = cursor.fetchall()
print('Users:')
for user in users:
    print(f'  {user}')
conn.close()