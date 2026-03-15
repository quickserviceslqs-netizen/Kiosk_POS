#!/usr/bin/env python3
"""Test split payment breaking logic in payment reconciliation."""

import sys
import sqlite3
from datetime import datetime
from modules.reports import get_sales_by_payment_method
from database.init_db import get_connection

def test_split_breaking():
    """Test that split payments are broken into individual channels."""
    
    print("=" * 60)
    print("SPLIT PAYMENT BREAKING TEST")
    print("=" * 60)
    
    # Get today's date range for testing
    today = datetime.now().strftime('%Y-%m-%d')
    start_date = today
    end_date = today
    
    print(f"\nTesting for date range: {start_date} to {end_date}")
    
    # Test 1: Check if sale_payments table exists
    print("\n[1] Checking if sale_payments table exists...")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        table_check = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sale_payments'"
        ).fetchone()
        if table_check:
            print("✓ sale_payments table EXISTS")
        else:
            print("✗ sale_payments table DOES NOT EXIST")
    
    # Test 2: Check for split sales in database
    print("\n[2] Checking for split sales in database...")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        split_count = conn.execute(
            "SELECT COUNT(*) as count FROM sales WHERE payment_method = 'Split' AND date = ?",
            (today,)
        ).fetchone()['count']
        print(f"   Found {split_count} split sales for today")
    
    # Test 3: Check for expenses
    print("\n[3] Checking for expenses in database...")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        expense_count = conn.execute(
            "SELECT COUNT(*) as count FROM expenses WHERE date = ?",
            (today,)
        ).fetchone()['count']
        expense_total = conn.execute(
            "SELECT SUM(amount) as total FROM expenses WHERE date = ?",
            (today,)
        ).fetchone()['total'] or 0.0
        print(f"   Found {expense_count} expenses for today")
        print(f"   Total expense amount: {expense_total}")
    
    # Test 4: Call get_sales_by_payment_method and check results
    print("\n[4] Testing get_sales_by_payment_method()...")
    try:
        results = get_sales_by_payment_method(start_date, end_date)
        
        print(f"\n   Results returned: {len(results)} payment method rows")
        print("\n   Payment Method Breakdown:")
        print("-" * 50)
        
        has_split = False
        total_sales = 0.0
        
        for result in results:
            pm = result.get('payment_method', 'N/A')
            count = result.get('transaction_count', 0)
            total = result.get('total_sales', 0.0)
            
            print(f"   {pm:15} | Transactions: {count:4} | Total: ${total:10.2f}")
            
            if pm == 'Split':
                has_split = True
            total_sales += total
        
        print("-" * 50)
        print(f"   {'TOTAL':15} | Total Sales: ${total_sales:10.2f}")
        
        # Validation
        print("\n[5] Validation:")
        if has_split:
            print("   ✗ FAIL: 'Split' payment method still appears in results")
            print("          Expected: Split payments to be broken into individual channels")
        else:
            print("   ✓ PASS: 'Split' payment method does NOT appear in results")
        
        if split_count > 0 and len(results) == 0:
            print("   ⚠ WARNING: Split sales exist but no payment methods returned")
        elif split_count > 0:
            print(f"   ✓ PASS: Split sales ({split_count}) were broken into channels")
        
        print("\n[6] Summary:")
        print(f"   - Split sales in DB: {split_count}")
        print(f"   - Payment methods returned: {len(results)}")
        print(f"   - 'Split' in results: {has_split}")
        
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    return not has_split  # Return True if split breaking is working

if __name__ == '__main__':
    success = test_split_breaking()
    sys.exit(0 if success else 1)
