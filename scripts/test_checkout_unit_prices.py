import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from modules import items, pos, receipts

# Create item with package size 4 (bulk price 40 -> per-unit 10)
it = items.create_item(name='CheckoutUnitPriceTest', selling_price=40.0, unit_of_measure='pieces', unit_size_ml=4, quantity=10)

# Simulate cart entry as created by POS UI (bulk price stored in entry)
cart_entry = {'item_id': it['item_id'], 'price': it['selling_price'], 'quantity': 2}

# Simulate CheckoutDialog building sale_lines
try:
    unit_size = float(it.get('unit_size_ml') or 1)
except Exception:
    unit_size = 1
per_unit = cart_entry['price'] / unit_size if unit_size else cart_entry['price']

sale = pos.create_sale([{'item_id': cart_entry['item_id'], 'quantity': cart_entry['quantity'], 'price': per_unit}], payment=per_unit * cart_entry['quantity'])

# Fetch sale items and assert price stored equals per_unit
sale_data = receipts.get_sale_with_items(sale['sale_id'])
line = sale_data['items'][0]
print('Stored sales_items price:', line['price'], 'expected:', per_unit)
assert abs(line['price'] - per_unit) < 1e-6, 'Sale item price not stored as per-unit price'

# Cleanup
from database.init_db import get_connection
with get_connection() as conn:
    conn.execute('DELETE FROM sales_items WHERE sale_id = ?', (sale['sale_id'],))
    conn.execute('DELETE FROM sales WHERE sale_id = ?', (sale['sale_id'],))
items.delete_item(it['item_id'])
print('Test passed')
