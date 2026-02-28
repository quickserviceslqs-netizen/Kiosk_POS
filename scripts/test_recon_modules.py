import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.reconciliation import orchestrator

# Create or reuse a session: We'll use the latest session id from DB if present.
from database.init_db import get_connection

with get_connection() as conn:
    row = conn.execute('SELECT session_id FROM reconciliation_sessions ORDER BY created_at DESC LIMIT 1').fetchone()
    if row:
        # sqlite returns tuple by default; access first element
        sid = row[0]
    else:
        # Create a session via existing service
        from modules.reconciliation_core import reconciliation_service
        s = reconciliation_service.create_session('today', 'daily', 1)
        # reconciliation_service.create_session returns a ReconciliationSession dataclass
        sid = s.session_id if hasattr(s, 'session_id') else int(s)


print('Using session id:', sid)

summaries = orchestrator.summarize(sid)
for s in summaries:
    print(f"Module {s.module_name}: system={s.total_system:.2f}, actual={s.total_actual:.2f}, variance={s.total_variance:.2f} ({s.entries_count} entries)")
