#!/usr/bin/env python3
"""Test date filtering with length-based detection."""

import sqlite3
from datetime import datetime, timedelta

db_path = 'database/pos_84409ac2.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Test date filtering with improved SQL that handles both formats
# using LENGTH and SUBSTR to detect the format
today = datetime.now().date()
thirty_days_ago = today - timedelta(days=30)

from_date = str(thirty_days_ago)  # YYYY-MM-DD format
to_date = str(today)

query = """
    SELECT session_id, reconciliation_date, status
    FROM reconciliation_sessions
    WHERE 1=1
    AND (
        CASE 
            WHEN SUBSTR(reconciliation_date, 3, 1) = '.' THEN DATE(SUBSTR(reconciliation_date, 7, 4) || '-' || SUBSTR(reconciliation_date, 4, 2) || '-' || SUBSTR(reconciliation_date, 1, 2))
            ELSE DATE(reconciliation_date)
        END >= DATE(?)
    )
    AND (
        CASE 
            WHEN SUBSTR(reconciliation_date, 3, 1) = '.' THEN DATE(SUBSTR(reconciliation_date, 7, 4) || '-' || SUBSTR(reconciliation_date, 4, 2) || '-' || SUBSTR(reconciliation_date, 1, 2))
            ELSE DATE(reconciliation_date)
        END <= DATE(?)
    )
    ORDER BY reconciliation_date DESC, session_id DESC
"""

cursor.execute(query, (from_date, to_date))
rows = cursor.fetchall()
print(f'Date filter test with SUBSTR-based detection:')
print(f'From: {from_date}, To: {to_date}')
print(f'Found {len(rows)} sessions')
for row in rows:
    print(f'  Session {row[0]}: {row[1]} - {row[2]}')
conn.close()
