#!/usr/bin/env python3
from database.init_db import get_connection

with get_connection() as conn:
    cursor = conn.cursor()
    
    # Drop tables
    try:
        cursor.execute("DROP TABLE IF EXISTS loyalty_transactions")
        print("Dropped loyalty_transactions table")
    except Exception as e:
        print(f"Error dropping loyalty_transactions: {e}")
    
    try:
        cursor.execute("DROP TABLE IF EXISTS loyalty_customers")
        print("Dropped loyalty_customers table")
    except Exception as e:
        print(f"Error dropping loyalty_customers: {e}")
    
    # Drop columns from sales
    try:
        cursor.execute("ALTER TABLE sales DROP COLUMN customer_id")
        print("Dropped customer_id column from sales")
    except Exception as e:
        print(f"Error dropping customer_id: {e}")
    
    try:
        cursor.execute("ALTER TABLE sales DROP COLUMN points_earned")
        print("Dropped points_earned column from sales")
    except Exception as e:
        print(f"Error dropping points_earned: {e}")
    
    try:
        cursor.execute("ALTER TABLE sales DROP COLUMN points_redeemed")
        print("Dropped points_redeemed column from sales")
    except Exception as e:
        print(f"Error dropping points_redeemed: {e}")
    
    # Remove loyalty settings
    cursor.execute("DELETE FROM settings WHERE key LIKE 'loyalty_%'")
    print("Deleted loyalty settings")
    
    # Drop indexes
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_loyalty_customers_phone")
        print("Dropped idx_loyalty_customers_phone")
    except Exception as e:
        print(f"Error dropping index: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_loyalty_transactions_customer")
        print("Dropped idx_loyalty_transactions_customer")
    except Exception as e:
        print(f"Error dropping index: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_loyalty_transactions_date")
        print("Dropped idx_loyalty_transactions_date")
    except Exception as e:
        print(f"Error dropping index: {e}")
    
    conn.commit()