#!/usr/bin/env python3
"""Test LIKE pattern matching on dates."""

import sqlite3

conn = sqlite3.connect('database/pos_84409ac2.db')
cursor = conn.cursor()

# Test the CASE statement directly
query = '''
SELECT session_id, reconciliation_date,
    CASE 
        WHEN reconciliation_date LIKE '__.__.__' THEN 'MATCHED DD.MM.YYYY'
        ELSE 'DID NOT MATCH'
    END as format_check,
    LENGTH(reconciliation_date) as date_length
FROM reconciliation_sessions
ORDER BY session_id
'''
cursor.execute(query)
rows = cursor.fetchall()
print('Format detection test:')
for row in rows:
    print(f'  Session {row[0]}: {repr(row[1])} (len={row[3]}) => {row[2]}')
conn.close()
