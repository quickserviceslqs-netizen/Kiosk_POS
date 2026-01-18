#!/usr/bin/env python3
"""
Initialize loyalty points data for existing customers.
This script runs after the database schema is updated.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.init_db import get_connection

def main():
    print("Initializing loyalty points system...")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Check if we have any existing orders to convert
            cursor.execute("SELECT COUNT(*) FROM orders")
            order_count = cursor.fetchone()[0]

            if order_count > 0:
                print(f"Found {order_count} existing orders. Converting to loyalty system...")

                # For each existing order, create a loyalty transaction if it doesn't exist
                cursor.execute("""
                    SELECT id, total_amount, customer_name
                    FROM orders
                    WHERE customer_name IS NOT NULL AND customer_name != ''
                    ORDER BY created_at DESC
                    LIMIT 50  -- Process only recent orders to avoid long execution
                """)

                orders = cursor.fetchall()
                processed_customers = set()

                for order in orders:
                    order_id, total_amount, customer_name = order

                    if customer_name in processed_customers:
                        continue

                    # Calculate points earned (1 point per dollar)
                    points_earned = int(total_amount)

                    # Create or update loyalty customer
                    cursor.execute("""
                        INSERT OR IGNORE INTO loyalty_customers (customer_name, total_points)
                        VALUES (?, ?)
                    """, (customer_name, points_earned))

                    # Get customer ID
                    cursor.execute("SELECT id FROM loyalty_customers WHERE customer_name = ?",
                                 (customer_name,))
                    customer_result = cursor.fetchone()

                    if customer_result:
                        customer_id = customer_result[0]

                        # Create loyalty transaction
                        cursor.execute("""
                            INSERT OR IGNORE INTO loyalty_transactions
                            (customer_id, transaction_type, points, order_id, description)
                            VALUES (?, 'earned', ?, ?, 'Points from existing order')
                        """, (customer_id, points_earned, order_id))

                        # Update order with customer reference
                        cursor.execute("""
                            UPDATE orders SET customer_id = ?, points_earned = ?
                            WHERE id = ?
                        """, (customer_id, points_earned, order_id))

                        processed_customers.add(customer_name)

                print(f"Processed {len(processed_customers)} customers with loyalty points")

            # Verify the installation
            cursor.execute("SELECT COUNT(*) FROM loyalty_customers")
            customer_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM loyalty_transactions")
            transaction_count = cursor.fetchone()[0]

            print(f"Loyalty system initialized: {customer_count} customers, {transaction_count} transactions")

            conn.commit()

    except Exception as e:
        print(f"Error initializing loyalty data: {e}")
        sys.exit(1)

    print("Loyalty points initialization completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())