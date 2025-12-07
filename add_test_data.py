"""Add test data to the POS system."""
from database.init_db import get_connection

def add_test_items():
    """Add sample items to the database."""
    items = [
        # Beverages
        ("Coca Cola 500ml", "Beverages", 25.00, 50.00, 100, "12345001", 16.0),
        ("Pepsi 500ml", "Beverages", 24.00, 48.00, 80, "12345002", 16.0),
        ("Sprite 500ml", "Beverages", 24.00, 48.00, 90, "12345003", 16.0),
        ("Mineral Water 1L", "Beverages", 15.00, 30.00, 150, "12345004", 16.0),
        ("Fresh Milk 500ml", "Beverages", 45.00, 80.00, 60, "12345005", 0.0),
        
        # Snacks
        ("Potato Crisps", "Snacks", 30.00, 60.00, 120, "12345006", 16.0),
        ("Chocolate Bar", "Snacks", 40.00, 80.00, 100, "12345007", 16.0),
        ("Biscuits Pack", "Snacks", 35.00, 70.00, 90, "12345008", 16.0),
        ("Peanuts 200g", "Snacks", 50.00, 100.00, 75, "12345009", 16.0),
        ("Chewing Gum", "Snacks", 10.00, 20.00, 200, "12345010", 16.0),
        
        # Groceries
        ("Rice 2kg", "Groceries", 120.00, 200.00, 50, "12345011", 0.0),
        ("Sugar 1kg", "Groceries", 80.00, 130.00, 60, "12345012", 0.0),
        ("Cooking Oil 1L", "Groceries", 180.00, 280.00, 40, "12345013", 16.0),
        ("Wheat Flour 2kg", "Groceries", 90.00, 150.00, 55, "12345014", 0.0),
        ("Salt 500g", "Groceries", 20.00, 35.00, 100, "12345015", 0.0),
        
        # Personal Care
        ("Soap Bar", "Personal Care", 25.00, 50.00, 150, "12345016", 16.0),
        ("Toothpaste", "Personal Care", 60.00, 120.00, 80, "12345017", 16.0),
        ("Shampoo 200ml", "Personal Care", 80.00, 150.00, 70, "12345018", 16.0),
        ("Tissue Paper", "Personal Care", 30.00, 60.00, 100, "12345019", 16.0),
        ("Hand Sanitizer", "Personal Care", 70.00, 130.00, 90, "12345020", 16.0),
        
        # Household
        ("Detergent 500g", "Household", 90.00, 160.00, 65, "12345021", 16.0),
        ("Dishwashing Liquid", "Household", 70.00, 130.00, 75, "12345022", 16.0),
        ("Bleach 500ml", "Household", 50.00, 90.00, 60, "12345023", 16.0),
        ("Broom", "Household", 120.00, 220.00, 30, "12345024", 16.0),
        ("Garbage Bags", "Household", 80.00, 140.00, 85, "12345025", 16.0),
    ]
    
    with get_connection() as conn:
        for item in items:
            name, category, cost, price, qty, barcode, vat = item
            conn.execute(
                """INSERT INTO items (name, category, cost_price, selling_price, quantity, barcode, vat_rate)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, category, cost, price, qty, barcode, vat)
            )
        conn.commit()
        print(f"✓ Added {len(items)} test items successfully!")

if __name__ == "__main__":
    add_test_items()
