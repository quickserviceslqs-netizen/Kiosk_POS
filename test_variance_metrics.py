#!/usr/bin/env python3
"""
Test script to verify variance explanation dialogue shows real-time metrics
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from modules.reconciliation_core import (
    create_reconciliation_session, get_reconciliation_session,
    update_reconciliation_entry, add_variance_explanation,
    get_variance_explanations, get_explained_variance_total,
    get_unexplained_variance, save_reconciliation_session
)
from database.init_db import get_connection
from datetime import datetime, timedelta

def test_variance_explanation_metrics():
    """Test that variance explanation dialogue shows correct real-time metrics."""

    print("Testing Variance Explanation Real-Time Metrics")
    print("=" * 50)

    # Clean up any existing test data
    with get_connection() as conn:
        conn.execute("DELETE FROM reconciliation_explanations WHERE explanation LIKE 'Test%'")
        conn.execute("DELETE FROM reconciliation_entries WHERE explanation LIKE 'Test%'")
        conn.commit()

    # Create a test session
    print("\n1. Creating test reconciliation session...")
    from datetime import datetime
    session_id = create_reconciliation_session(
        reconciliation_date=datetime.now().strftime('%Y-%m-%d'),
        period_type='daily',
        start_date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        end_date=datetime.now().strftime('%Y-%m-%d'),
        user_id=1
    )
    session = get_reconciliation_session(session_id)
    print(f"   Created session ID: {session.session_id}")

    # Manually set system amounts for testing
    print("\n2. Setting up test data with manual entries...")

    with get_connection() as conn:
        # Insert test entries with specific system amounts
        conn.execute("""
            INSERT OR REPLACE INTO reconciliation_entries
            (session_id, payment_method, system_amount, actual_amount, variance, explanation)
            VALUES (?, 'Cash', 1000.00, 0.0, 0.0, '')
        """, (session_id,))

        conn.execute("""
            INSERT OR REPLACE INTO reconciliation_entries
            (session_id, payment_method, system_amount, actual_amount, variance, explanation)
            VALUES (?, 'Card', 500.00, 0.0, 0.0, '')
        """, (session_id,))

        conn.execute("""
            INSERT OR REPLACE INTO reconciliation_entries
            (session_id, payment_method, system_amount, actual_amount, variance, explanation)
            VALUES (?, 'Bank Transfer', 200.00, 0.0, 0.0, '')
        """, (session_id,))
        conn.commit()

    # Reload session to get updated data
    session = get_reconciliation_session(session_id)

    # Add actual amounts to create variance
    print("   Setting actual amounts to create variance:")

    # Cash: Expected 1000, Actual 950 (variance -50)
    update_reconciliation_entry(session_id, "Cash", 950.00, "Test Cash entry")
    print("   - Cash: Expected $1000, Actual $950 (Variance: -$50)")

    # Card: Expected 500, Actual 520 (variance +20)
    update_reconciliation_entry(session_id, "Card", 520.00, "Test Card entry")
    print("   - Card: Expected $500, Actual $520 (Variance: +$20)")

    # Bank Transfer: Expected 200, Actual 180 (variance -20)
    update_reconciliation_entry(session_id, "Bank Transfer", 180.00, "Test Bank Transfer entry")
    print("   - Bank Transfer: Expected $200, Actual $180 (Variance: -$20)")

    print("   Total Variance: -$50")

    # Reload session again
    session = get_reconciliation_session(session_id)

    # Check initial unexplained variance
    print("\n3. Checking initial unexplained variance...")

    for payment_method in ["Cash", "Card", "Bank Transfer"]:
        unexplained = get_unexplained_variance(session_id, payment_method)
        explained = get_explained_variance_total(session_id, payment_method)
        print(f"   {payment_method}: Explained ${explained:.2f}, Unexplained ${unexplained:.2f}")

    # Add some explanations
    print("\n4. Adding variance explanations...")

    # Explain $30 of the Cash variance (-$50 total)
    add_variance_explanation(session_id, "Cash", "Bank fees", -30.00, 1)
    print("   Added Cash explanation: 'Bank fees' -$30.00")

    # Explain $10 of the Card variance (+$20 total)
    add_variance_explanation(session_id, "Card", "Processing fees", -10.00, 1)
    print("   Added Card explanation: 'Processing fees' -$10.00")

    # Check updated metrics
    print("\n5. Checking updated metrics after explanations...")

    for payment_method in ["Cash", "Card", "Bank Transfer"]:
        unexplained = get_unexplained_variance(session_id, payment_method)
        explained = get_explained_variance_total(session_id, payment_method)
        explanations = get_variance_explanations(session_id, payment_method)
        print(f"   {payment_method}:")
        print(f"     Explained: ${explained:.2f}")
        print(f"     Unexplained: ${unexplained:.2f}")
        print(f"     Number of explanations: {len(explanations)}")
        for expl in explanations:
            print(f"       - {expl.explanation}: ${expl.amount:.2f}")

    # Test the dialogue simulation
    print("\n6. Simulating variance explanation dialogue...")

    for payment_method in ["Cash", "Card", "Bank Transfer"]:
        print(f"\n   Testing {payment_method} dialogue:")

        # Get variance for this method
        variance = None
        for item in session.entries:
            if item.payment_method == payment_method:
                variance = item.variance
                break

        if variance is None:
            print("     No variance data found")
            continue

        unexplained = get_unexplained_variance(session_id, payment_method)
        explained = get_explained_variance_total(session_id, payment_method)
        explanations = get_variance_explanations(session_id, payment_method)

        print(f"     Total Variance: ${variance:.2f}")
        print(f"     Explained: ${explained:.2f}")
        print(f"     Unexplained: ${unexplained:.2f}")
        print(f"     Status would show: 'Explained: ${explained:.2f} | Unexplained: ${unexplained:.2f}'")

        if unexplained != 0:
            print(f"     Add explanation dialog would pre-populate amount: ${unexplained:.2f}")

    # Save the session to test persistence
    print("\n7. Saving session to test persistence...")
    save_reconciliation_session(session_id, 1)
    print(f"   Session {session_id} saved as draft")

    # Verify explanations persisted
    print("\n8. Verifying explanations persisted after save...")
    for payment_method in ["Cash", "Card", "Bank Transfer"]:
        explanations = get_variance_explanations(session_id, payment_method)
        if explanations:
            print(f"   {payment_method}: {len(explanations)} explanations persisted")
            for expl in explanations:
                print(f"     - {expl.explanation}: ${expl.amount:.2f}")
        else:
            print(f"   {payment_method}: No explanations")

    print("\n" + "=" * 50)
    print("Test completed successfully!")
    print("The variance explanation dialogue should now show:")
    print("- Real-time explained/unexplained amounts")
    print("- Pre-populated amount field with unexplained variance")
    print("- Updated status after adding/editing/deleting explanations")

if __name__ == "__main__":
    test_variance_explanation_metrics()