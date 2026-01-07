"""Seed demo items and sales so the Dashboard shows data during development.
Run: python scripts/seed_demo_data.py
"""
import sys, os
# Ensure project root is on sys.path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules import items, pos, users, dashboard

# Create a test cashier user
try:
    users.create_user('cashier', 'cashier123', role='cashier')
    print('Created user: cashier')
except Exception:
    print('User cashier may already exist')

# Create demo items
demo_items = [
    dict(name='Bananas', category='Fruit', cost_price=20.0, selling_price=35.0, quantity=100, unit_of_measure='pieces', is_special_volume=0),
    dict(name='Milk 1L', category='Dairy', cost_price=40.0, selling_price=60.0, quantity=200, unit_of_measure='L', is_special_volume=1, unit_size_ml=1000),
    dict(name='Bread Loaf', category='Bakery', cost_price=25.0, selling_price=45.0, quantity=80, unit_of_measure='pieces', is_special_volume=0),
]
created = []
for it in demo_items:
    try:
        rec = items.create_item(**it)
        created.append(rec)
        print('Created item:', rec['item_id'], rec['name'])
    except Exception as e:
        print('Failed to create item', it['name'], e)

# Create demo sales
# Use first 3 items (if exists)
item_ids = [i['item_id'] for i in created]
if item_ids:
    try:
        # Sale 1: 2 bananas, 1 bread
        line_items = [
            {'item_id': item_ids[0], 'quantity': 2, 'price': 35.0},
        ]
        sale1 = pos.create_sale(line_items, payment=100.0)
        print('Created sale:', sale1)
    except Exception as e:
        print('Failed to create sale 1', e)

    try:
        # Sale 2: 1 liter milk (special volume)
        line_items = [
            {'item_id': item_ids[1], 'quantity': 1, 'price': 60.0},
        ]
        sale2 = pos.create_sale(line_items, payment=60.0)
        print('Created sale:', sale2)
    except Exception as e:
        print('Failed to create sale 2', e)

# Show dashboard summary
print('Today summary:', dashboard.get_today_summary())
print('Top products:', dashboard.get_top_products(5))
print('Low stock items:', dashboard.get_low_stock_items(10))
print('Recent sales:', dashboard.get_recent_sales(10))