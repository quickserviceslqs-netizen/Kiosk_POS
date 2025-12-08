import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "database" / "pos.db"

with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("SELECT username, role FROM users WHERE role='admin';")
    admins = cursor.fetchall()
    if admins:
        print("Admin users found:")
        for user in admins:
            print("-", user[0])
    else:
        print("No admin users found.")
