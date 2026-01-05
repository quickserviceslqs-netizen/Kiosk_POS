import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, pos, refunds, receipts
from database.init_db import get_connection

# Create an item
it = items.create_item(name='RefundPartialTest', category='Uncategorized', cost_price=1.0, selling_price=5.0, quantity=10, unit_of_measure='pieces')

# Create a sale with one line of quantity 3
sale = pos.create_sale([
    {'item_id': it['item_id'], 'quantity': 3, 'price': 5.0},
], payment=15.0)

sale_data = receipts.get_sale_with_items(sale['sale_id'])
si = sale_data['items'][0]
sale_item_id = si['sale_item_id']
print('Sale item id', sale_item_id, 'qty', si['quantity'])

# First partial refund: refund 1
r1 = refunds.create_refund(sale['sale_id'], [{'sale_item_id': sale_item_id, 'item_id': it['item_id'], 'quantity': 1}], 'Partial 1')
print('Refund 1 created', r1)

# After first refund, sale should not be fully refunded
assert not refunds.is_sale_fully_refunded(sale['sale_id'])

# Second refund: refund remaining 2
r2 = refunds.create_refund(sale['sale_id'], [{'sale_item_id': sale_item_id, 'item_id': it['item_id'], 'quantity': 2}], 'Partial 2')
print('Refund 2 created', r2)

# Now sale should be fully refunded
assert refunds.is_sale_fully_refunded(sale['sale_id'])

# Clean up
with get_connection() as conn:
    conn.execute('DELETE FROM refunds_items WHERE refund_id IN (SELECT refund_id FROM refunds WHERE original_sale_id = ?)', (sale['sale_id'],))
    conn.execute('DELETE FROM refunds WHERE original_sale_id = ?', (sale['sale_id'],))
    conn.execute('DELETE FROM sales_items WHERE sale_id = ?', (sale['sale_id'],))
    conn.execute('DELETE FROM sales WHERE sale_id = ?', (sale['sale_id'],))
items.delete_item(it['item_id'])
print('Test passed')
