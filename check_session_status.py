"""Check actual session statuses in database."""
import sqlite3
import glob
from pathlib import Path

# Find the database file with actual data (largest)
db_files = glob.glob('database/pos_*.db')
if not db_files:
    print('No database found')
else:
    # Use the largest file (most likely has data)
    db_path = max(db_files, key=lambda f: Path(f).stat().st_size)
    print(f'Using database: {db_path}')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check reconciliation sessions
    cursor.execute('SELECT session_id, status, reconciliation_date FROM reconciliation_sessions ORDER BY session_id DESC LIMIT 15')
    sessions = cursor.fetchall()
    
    print(f'\nTotal sessions: {len(sessions) if sessions else 0}')
    if sessions:
        print('\nSession Details:')
        for session_id, status, date in sessions:
            print(f'  Session {session_id}: status="{status}" (type:{type(status).__name__}, repr:{repr(status)}) | date={date}')
    
    conn.close()
