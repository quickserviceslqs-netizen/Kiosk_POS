import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.init_db import initialize_database, get_connection
from modules import items, variants
import tkinter as tk

initialize_database()
# Clean existing items and variants
conn = get_connection()
cur = conn.cursor()
cur.execute('PRAGMA foreign_keys = OFF')
cur.execute('DELETE FROM item_variants')
cur.execute('DELETE FROM items')
conn.commit()
cur.execute('PRAGMA foreign_keys = ON')
conn.commit()

item = items.create_item(name='Grouped Item', category='Food', selling_price=5.0, cost_price=2.0, quantity=0, low_stock_threshold=5)
item_id = item['item_id']
variants.create_variant(item_id, 'One', 5.0, 2.0, quantity=1)
variants.create_variant(item_id, 'Two', 6.0, 3.0, quantity=10)
root = tk.Tk()
root.withdraw()
from ui.inventory import InventoryFrame
frame = InventoryFrame(root)
frame.refresh()
print('tree children:', frame.tree.get_children())
for c in frame.tree.get_children():
    print('iid:', c, 'values:', frame.tree.item(c, 'values'))
root.destroy()