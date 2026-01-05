import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, pos, refunds, receipts
from database.init_db import get_connection

# Create an item
it = items.create_item(name='RefundMultiLineTest', category='Uncategorized', cost_price=1.0, selling_price=5.0, quantity=10, unit_of_measure='pieces')

# Create a sale with two separate lines of same product
sale = pos.create_sale([
    {'item_id': it['item_id'], 'quantity': 1, 'price': 5.0},
    {'item_id': it['item_id'], 'quantity': 1, 'price': 5.0},
], payment=10.0)

sale_data = receipts.get_sale_with_items(sale['sale_id'])
print('Sale items:', [(s['sale_item_id'], s['item_id'], s['quantity']) for s in sale_data['items']])

# Refund first sale_item
sid1 = sale_data['items'][0]['sale_item_id']
r1 = refunds.create_refund(sale['sale_id'], [{'sale_item_id': sid1, 'item_id': it['item_id'], 'quantity': 1}], 'Line 1')
print('Refund 1', r1)
# Refund second sale_item
sid2 = sale_data['items'][1]['sale_item_id']
r2 = refunds.create_refund(sale['sale_id'], [{'sale_item_id': sid2, 'item_id': it['item_id'], 'quantity': 1}], 'Line 2')
print('Refund 2', r2)

assert refunds.is_sale_fully_refunded(sale['sale_id'])

# Clean up
with get_connection() as conn:
    conn.execute('DELETE FROM refunds_items WHERE refund_id IN (SELECT refund_id FROM refunds WHERE original_sale_id = ?)', (sale['sale_id'],))
    conn.execute('DELETE FROM refunds WHERE original_sale_id = ?', (sale['sale_id'],))
    conn.execute('DELETE FROM sales_items WHERE sale_id = ?', (sale['sale_id'],))
    conn.execute('DELETE FROM sales WHERE sale_id = ?', (sale['sale_id'],))
items.delete_item(it['item_id'])
print('Test passed')
