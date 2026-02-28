#!/usr/bin/env python3
"""
Large Data Test Script for Kiosk POS Reports

This script creates synthetic large datasets and tests the scalability
of the reporting system, including pagination, streaming exports, and
performance under load.
"""

import sys
import os
import time
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import get_connection, initialize_database
from modules.reconciliation_core import ReconciliationService
from ui.reports_base import ReportGenerator
from ui.reports_service import ReportService
from ui.reports_export import ExportManager

def create_synthetic_sales_data(num_sales: int = 10000) -> None:
    """Create synthetic sales data for testing."""
    print(f"Creating {num_sales} synthetic sales records...")

    # Initialize database
    db_path = initialize_database()
    
    # Connect to database
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM sales")
    cursor.execute("DELETE FROM sales_items")
    cursor.execute("DELETE FROM items")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='sales'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='sales_items'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='items'")

    # Sample data
    items = [
        {"name": "Coffee", "price": 3.50, "category": "Beverages"},
        {"name": "Sandwich", "price": 8.99, "category": "Food"},
        {"name": "Cake", "price": 4.50, "category": "Desserts"},
        {"name": "Juice", "price": 2.99, "category": "Beverages"},
        {"name": "Burger", "price": 12.99, "category": "Food"},
        {"name": "Salad", "price": 7.50, "category": "Food"},
        {"name": "Cookie", "price": 2.25, "category": "Desserts"},
        {"name": "Tea", "price": 2.75, "category": "Beverages"},
        {"name": "Pizza Slice", "price": 6.99, "category": "Food"},
        {"name": "Ice Cream", "price": 3.99, "category": "Desserts"},
    ]

    # Create sample items
    item_ids = []
    for item in items:
        cursor.execute("""
            INSERT INTO items (name, category, selling_price, cost_price, quantity, vat_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            item["name"],
            item["category"],
            item["price"],
            item["price"] * 0.6,  # cost price = 60% of selling price
            random.randint(50, 200),  # random stock quantity
            15.0  # VAT rate
        ))
        item_ids.append(cursor.lastrowid)

    # Map item names to IDs
    item_name_to_id = dict(zip([item["name"] for item in items], item_ids))

    customers = ["Walk-in", "John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"]
    users = ["admin", "cashier1", "cashier2", "manager"]
    payment_methods = ["Cash", "Card", "Mobile"]

    # Generate sales
    base_date = datetime.now() - timedelta(days=365)
    receipt_number = 1000

    for i in range(num_sales):
        # Random date within the last year
        sale_date = base_date + timedelta(days=random.randint(0, 365))
        sale_time = f"{random.randint(8, 22):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"

        # Random customer and user
        customer = random.choice(customers)
        user = random.choice(users)
        payment_method = random.choice(payment_methods)

        # Random number of items (1-5)
        num_items = random.randint(1, 5)
        sale_items = random.sample(items, num_items)

        # Calculate totals
        subtotal = sum(item["price"] * random.randint(1, 3) for item in sale_items)
        vat_rate = 0.15  # 15% VAT
        vat_amount = subtotal * vat_rate
        discount = random.choice([0, 0, 0, 0.5, 1.0, 2.0])  # Mostly no discount
        total = subtotal + vat_amount - discount

        # Insert sale
        cursor.execute("""
            INSERT INTO sales (
                date, time, payment_method, subtotal, vat_amount, 
                discount_amount, total, receipt_number, payment_received, change
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sale_date.strftime("%Y-%m-%d"),
            sale_time,
            payment_method,
            subtotal,
            vat_amount,
            discount,
            total,
            f"#{receipt_number}",
            total,  # payment_received = total (assuming full payment)
            0.0     # change = 0
        ))

        sale_id = cursor.lastrowid
        receipt_number += 1

        # Insert sale items
        for item in sale_items:
            quantity = random.randint(1, 3)
            item_id = item_name_to_id[item["name"]]

            cursor.execute("""
                INSERT INTO sales_items (
                    sale_id, item_id, quantity, price, cost_price
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                sale_id,
                item_id,
                quantity,
                item["price"],
                item["price"] * 0.6  # cost price
            ))

        if (i + 1) % 1000 == 0:
            print(f"Created {i + 1} sales...")
            conn.commit()

    conn.commit()
    conn.close()
    print(f"Successfully created {num_sales} synthetic sales records.")

def test_report_generation(report_type: str, num_records: int) -> dict:
    """Test report generation performance."""
    print(f"\nTesting {report_type} report with {num_records} records...")

    start_time = time.time()

    try:
        # Create report service
        service = ReportService()

        # Generate report
        if report_type == "transactions":
            report_data = service.generate_report_sync(
                report_type="transactions",
                start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d")
            )
        elif report_type == "inventory_stock_levels":
            report_data = service.generate_report_sync(
                report_type="inventory_stock_levels",
                start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d")
            )
        elif report_type == "reconciliation":
            report_data = service.generate_report_sync(
                report_type="reconciliation_details",
                start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                status_filter="all"
            )
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        generation_time = time.time() - start_time

        # Check results
        if hasattr(report_data, 'data') and report_data.data:
            actual_records = len(report_data.data)
        elif isinstance(report_data, list):
            actual_records = len(report_data)
        else:
            actual_records = 0

        print(f"  Generated {actual_records} records in {generation_time:.2f}s")
        print(".2f")

        return {
            "report_type": report_type,
            "num_records": num_records,
            "generation_time": generation_time,
            "actual_records": actual_records,
            "success": True
        }

    except Exception as e:
        error_time = time.time() - start_time
        print(f"  Error: {e} (took {error_time:.2f}s)")
        return {
            "report_type": report_type,
            "num_records": num_records,
            "generation_time": error_time,
            "actual_records": 0,
            "success": False,
            "error": str(e)
        }

def test_streaming_export(report_type: str, num_records: int) -> dict:
    """Test streaming export performance."""
    print(f"\nTesting streaming export for {report_type} with {num_records} records...")

    start_time = time.time()

    try:
        # Create export manager
        export_manager = ExportManager()

        # Create temporary file for export
        temp_file = f"temp_test_export_{report_type}_{num_records}.csv"

        # Perform streaming export
        if report_type == "transactions":
            success = export_manager.export_report_streaming(
                report_type="sales_log",
                start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                file_path=temp_file
            )
        elif report_type == "inventory_stock_levels":
            success = export_manager.export_report_streaming(
                report_type="inventory_stock_levels",
                start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                file_path=temp_file
            )
        elif report_type == "reconciliation":
            success = export_manager.export_report_streaming(
                report_type="reconciliation_details",
                start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                file_path=temp_file,
                status_filter="all"
            )
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        export_time = time.time() - start_time

        # Check file size
        if os.path.exists(temp_file):
            file_size = os.path.getsize(temp_file)
            print(f"  Exported to {file_size} bytes in {export_time:.2f}s")
            print(".2f")

            # Clean up
            os.remove(temp_file)

            return {
                "report_type": report_type,
                "num_records": num_records,
                "export_time": export_time,
                "file_size": file_size,
                "success": success
            }
        else:
            print(f"  Export failed - file not created")
            return {
                "report_type": report_type,
                "num_records": num_records,
                "export_time": export_time,
                "file_size": 0,
                "success": False,
                "error": "File not created"
            }

    except Exception as e:
        error_time = time.time() - start_time
        print(f"  Error: {e} (took {error_time:.2f}s)")
        return {
            "report_type": report_type,
            "num_records": num_records,
            "export_time": error_time,
            "file_size": 0,
            "success": False,
            "error": str(e)
        }

def run_large_data_tests():
    """Run comprehensive large data tests."""
    print("=== Kiosk POS Large Data Test Suite ===\n")

    # Test configurations
    test_configs = [
        {"num_sales": 1000, "description": "Small dataset (1K sales)"},
        {"num_sales": 10000, "description": "Medium dataset (10K sales)"},
        {"num_sales": 50000, "description": "Large dataset (50K sales)"},
    ]

    report_types = ["transactions", "inventory_stock_levels", "reconciliation"]

    all_results = []

    for config in test_configs:
        print(f"\n{'='*60}")
        print(f"Testing with {config['description']}")
        print(f"{'='*60}")

        # Create synthetic data
        create_synthetic_sales_data(config["num_sales"])

        # Test each report type
        for report_type in report_types:
            # Test report generation
            gen_result = test_report_generation(report_type, config["num_sales"])
            all_results.append(gen_result)

            # Test streaming export
            export_result = test_streaming_export(report_type, config["num_sales"])
            all_results.append(export_result)

    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    successful_tests = 0
    total_tests = len(all_results)

    for result in all_results:
        status = "✓ PASS" if result.get("success", False) else "✗ FAIL"
        test_type = "Generation" if "generation_time" in result else "Export"
        print(f"{status} {result['report_type']} {test_type} ({result['num_records']} records)")

        if not result.get("success", False):
            print(f"    Error: {result.get('error', 'Unknown')}")

        successful_tests += 1 if result.get("success", False) else 0

    print(f"\nOverall: {successful_tests}/{total_tests} tests passed")

    # Performance analysis
    print(f"\n{'='*60}")
    print("PERFORMANCE ANALYSIS")
    print(f"{'='*60}")

    for report_type in report_types:
        gen_times = [r["generation_time"] for r in all_results
                    if r["report_type"] == report_type and "generation_time" in r and r["success"]]
        export_times = [r["export_time"] for r in all_results
                       if r["report_type"] == report_type and "export_time" in r and r["success"]]

        if gen_times:
            avg_gen = sum(gen_times) / len(gen_times)
            max_gen = max(gen_times)
            print(f"{report_type.title()} Report Generation:")
            print(".2f")
            print(".2f")

        if export_times:
            avg_export = sum(export_times) / len(export_times)
            max_export = max(export_times)
            print(f"{report_type.title()} Streaming Export:")
            print(".2f")
            print(".2f")

    print("\nLarge data testing completed!")

if __name__ == "__main__":
    run_large_data_tests()