import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, pos, receipts
import tkinter as tk

# Create an item
it = items.create_item(name='RefundMultiTest', category='Uncategorized', cost_price=1.0, selling_price=5.0, quantity=10, unit_of_measure='pieces')

# Create a sale with two separate line items of the same product
sale = pos.create_sale([
    {'item_id': it['item_id'], 'quantity': 1, 'price': 5.0},
    {'item_id': it['item_id'], 'quantity': 1, 'price': 5.0},
], payment=10.0)

sale_data = receipts.get_sale_with_items(sale['sale_id'])
print('Sale items count:', len(sale_data['items']))
assert len(sale_data['items']) == 2, 'Expected two sale_items rows'

# Simulate the refund dialog vars keyed by sale_item_id
root = tk.Tk()
root.withdraw()
item_vars = {}
item_prices = {}
for item in sale_data['items']:
    sale_item_id = item.get('sale_item_id') or f"si_{id(item)}"
    var = tk.BooleanVar(value=True)
    item_vars[sale_item_id] = var
    item_prices[sale_item_id] = item['price'] * item['quantity']

# Deselect the first sale line
first_sid = sale_data['items'][0]['sale_item_id']
item_vars[first_sid].set(False)

# Compute total as UI would
total = sum(item_prices[sid] for sid, var in item_vars.items() if var.get())
print('Computed refund total after deselecting first line:', total)
assert total == 5.0, 'Expected refund total to be 5.0 after deselecting one of two identical items'

# Cleanup - remove sale rows then remove item
from database.init_db import get_connection
with get_connection() as conn:
    conn.execute("DELETE FROM sales_items WHERE sale_id = ?", (sale['sale_id'],))
    conn.execute("DELETE FROM sales WHERE sale_id = ?", (sale['sale_id'],))
items.delete_item(it['item_id'])
print('Test passed')
