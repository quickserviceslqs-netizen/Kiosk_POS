from database.init_db import initialize_database
initialize_database()
from modules.reconciliation_core import get_reconciliation_sessions

sessions = get_reconciliation_sessions()
print(f'Current sessions in DB: {len(sessions)}')
for s in sessions[-5:]:  # Show last 5
    print(f'  ID: {s["session_id"]}, Status: {s["status"]}, Created: {s["created_at"]}')