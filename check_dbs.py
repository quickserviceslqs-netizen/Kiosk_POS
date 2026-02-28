import sqlite3
import os

db_dir = r"c:\Users\ADMIN\Kiosk_POS\database"
dbs = [f for f in os.listdir(db_dir) if f.endswith('.db')]

for db in dbs:
    db_path = os.path.join(db_dir, db)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        if 'users' in tables:
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"{db}: {user_count} users")
        else:
            print(f"{db}: no users table")
        conn.close()
    except Exception as e:
        print(f"{db}: error - {e}")