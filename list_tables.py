import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "database" / "pos.db"

with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in pos.db:")
    for table in tables:
        print("-", table[0])
