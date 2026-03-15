"""Check demo database for sessions."""
import sqlite3

db_path = 'database/demo.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check reconciliation sessions
cursor.execute('SELECT session_id, status, reconciliation_date FROM reconciliation_sessions ORDER BY session_id DESC LIMIT 15')
sessions = cursor.fetchall()

print(f'Demo DB - Total sessions: {len(sessions) if sessions else 0}')
if sessions:
    print('\nSession Details:')
    for session_id, status, date in sessions:
        print(f'  Session {session_id}: status="{status}" | date={date}')

conn.close()
