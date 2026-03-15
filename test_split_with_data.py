#!/usr/bin/env python3
"""Test split payment breaking logic with test data."""

import sys
import sqlite3
from datetime import datetime
from modules.reports import get_sales_by_payment_method
from database.init_db import get_connection

def create_test_split_payments():
    """Create test split payment data."""
    
    print("\nCreating test split payment data...")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # First, check if sale_payments table exists, if not create it
        table_check = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sale_payments'"
        ).fetchone()
        
        if not table_check:
            print("Creating sale_payments table...")
            conn.execute("""
                CREATE TABLE sale_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    amount REAL NOT NULL,
                    FOREIGN KEY (sale_id) REFERENCES sales(sale_id)
                )
            """)
            conn.commit()
        
        # Create a test split sale
        test_date = datetime.now().strftime('%Y-%m-%d')
        test_sale_id = f"test_split_{int(datetime.now().timestamp() * 1000)}"
        
        # Insert the main sale with payment_method='Split'
        try:
            conn.execute("""
                INSERT INTO sales (
                    date, time, subtotal, vat_amount, discount_amount,
                    total, payment_method, voided
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_date,
                datetime.now().strftime('%H:%M:%S'),
                100.0,  # subtotal
                10.0,   # vat
                0.0,    # discount
                100.0,  # total
                'Split',  # payment_method
                0
            ))
            
            # Get the last inserted sale_id
            last_sale = conn.execute("SELECT last_insert_rowid() as id").fetchone()
            test_sale_id = last_sale['id']
            
            # Insert split payments
            conn.execute(
                "INSERT INTO sale_payments (sale_id, payment_method, amount) VALUES (?, ?, ?)",
                (test_sale_id, 'Cash', 60.0)
            )
            conn.execute(
                "INSERT INTO sale_payments (sale_id, payment_method, amount) VALUES (?, ?, ?)",
                (test_sale_id, 'Card', 40.0)
            )
            
            conn.commit()
            print(f"✓ Created test split sale: {test_sale_id}")
            print(f"  - Cash: $60.00")
            print(f"  - Card: $40.00")
            print(f"  - Total: $100.00")
            
            return True
        except Exception as e:
            print(f"✗ Error creating test data: {e}")
            return False

def test_split_breaking():
    """Test that split payments are broken into individual channels."""
    
    print("=" * 60)
    print("SPLIT PAYMENT BREAKING TEST WITH TEST DATA")
    print("=" * 60)
    
    # Get today's date range for testing
    today = datetime.now().strftime('%Y-%m-%d')
    start_date = today
    end_date = today
    
    print(f"\nTesting for date range: {start_date} to {end_date}")
    
    # Create test data
    if not create_test_split_payments():
        return False
    
    # Test: Call get_sales_by_payment_method and check results
    print("\n[1] Testing get_sales_by_payment_method() with test split data...")
    try:
        results = get_sales_by_payment_method(start_date, end_date)
        
        print(f"\n   Results returned: {len(results)} payment method rows")
        print("\n   Payment Method Breakdown:")
        print("-" * 50)
        
        has_split = False
        total_sales = 0.0
        cash_found = False
        card_found = False
        
        for result in results:
            pm = result.get('payment_method', 'N/A')
            count = result.get('transaction_count', 0)
            total = result.get('total_sales', 0.0)
            
            print(f"   {pm:15} | Transactions: {count:4} | Total: ${total:10.2f}")
            
            if pm == 'Split':
                has_split = True
            if pm == 'Cash':
                cash_found = True
            if pm == 'Card':
                card_found = True
            
            total_sales += total
        
        print("-" * 50)
        print(f"   {'TOTAL':15} | Total Sales: ${total_sales:10.2f}")
        
        # Validation
        print("\n[2] Validation:")
        
        if has_split:
            print("   ✗ FAIL: 'Split' payment method still appears in results")
            print("          Expected: Split payments to be broken into individual channels")
            success = False
        else:
            print("   ✓ PASS: 'Split' payment method does NOT appear in results")
            success = True
        
        if cash_found and card_found:
            print("   ✓ PASS: Both Cash and Card payment methods found")
        else:
            print(f"   ✗ FAIL: Cash found: {cash_found}, Card found: {card_found}")
            success = False
        
        if abs(total_sales - 100.0) < 0.01:
            print(f"   ✓ PASS: Total sales correct: ${total_sales:.2f}")
        else:
            print(f"   ✗ FAIL: Total sales incorrect: ${total_sales:.2f} (expected $100.00)")
            success = False
        
        print("\n[3] Summary:")
        print(f"   - 'Split' appears in results: {has_split}")
        print(f"   - Cash payment method found: {cash_found}")
        print(f"   - Card payment method found: {card_found}")
        print(f"   - Total sales: ${total_sales:.2f}")
        
        return success
        
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n" + "=" * 60)
    success = test_split_breaking()
    print("\n" + "=" * 60)
    if success:
        print("\n✓ ALL TESTS PASSED - Split payment breaking is working correctly!")
    else:
        print("\n✗ TESTS FAILED - Split payment breaking has issues")
    print("=" * 60 + "\n")
    sys.exit(0 if success else 1)
