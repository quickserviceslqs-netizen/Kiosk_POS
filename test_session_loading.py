#!/usr/bin/env python3
"""Diagnostic test for reconciliation sessions loading."""

import sqlite3
from datetime import datetime

db_path = 'database/pos_84409ac2.db'

def test_session_loading():
    """Test if sessions load properly without filters."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("RECONCILIATION SESSIONS LOADING TEST")
    print("=" * 60)
    
    # Test 1: Basic query
    print("\n[1] Testing basic query (no filters)...")
    cursor.execute("""
        SELECT session_id, reconciliation_date, period_type, status, 
               total_system_sales, total_variance
        FROM reconciliation_sessions
        WHERE 1=1
        ORDER BY reconciliation_date DESC, session_id DESC
    """)
    rows = cursor.fetchall()
    print(f"✓ Query returned {len(rows)} sessions")
    
    # Test 2: With status filter for 'draft'
    print("\n[2] Testing with status='draft' filter...")
    cursor.execute("""
        SELECT session_id, reconciliation_date, period_type, status,
               total_system_sales, total_variance
        FROM reconciliation_sessions
        WHERE 1=1 AND status = ?
        ORDER BY reconciliation_date DESC, session_id DESC
    """, ('draft',))
    rows = cursor.fetchall()
    print(f"✓ Query returned {len(rows)} sessions with status='draft'")
    
    # Test 3: With status filter for 'completed'
    print("\n[3] Testing with status='completed' filter...")
    cursor.execute("""
        SELECT session_id, reconciliation_date, period_type, status,
               total_system_sales, total_variance
        FROM reconciliation_sessions
        WHERE 1=1 AND status = ?
        ORDER BY reconciliation_date DESC, session_id DESC
    """, ('completed',))
    rows = cursor.fetchall()
    print(f"✓ Query returned {len(rows)} sessions with status='completed'")
    
    # Test 4: With Reviewed filter (status = 'completed' OR status = 'approved')
    print("\n[4] Testing with Reviewed filter (status='completed' OR 'approved')...")
    cursor.execute("""
        SELECT session_id, reconciliation_date, period_type, status,
               total_system_sales, total_variance
        FROM reconciliation_sessions
        WHERE 1=1 AND (status = 'completed' OR status = 'approved')
        ORDER BY reconciliation_date DESC, session_id DESC
    """)
    rows = cursor.fetchall()
    print(f"✓ Query returned {len(rows)} sessions with Reviewed filter")
    
    # Test 5: Showing actual dates in database
    print("\n[5] Actual dates in database:")
    cursor.execute("SELECT DISTINCT reconciliation_date FROM reconciliation_sessions")
    dates = cursor.fetchall()
    for date in dates:
        print(f"  - {date[0]}")
    
    # Test 6: Sessions summary
    print("\n[6] Sessions summary:")
    cursor.execute("SELECT COUNT(*), status FROM reconciliation_sessions GROUP BY status")
    for count, status in cursor.fetchall():
        print(f"  {status}: {count} session(s)")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    test_session_loading()
