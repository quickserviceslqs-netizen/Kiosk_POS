import sys
sys.path.append('.')
import tkinter as tk
from ui.inventory import InventoryFrame
from database.init_db import initialize_database, get_connection
from modules import items, variants

initialize_database()

# Create deterministic data
conn = get_connection()
cur = conn.cursor()
cur.execute("DELETE FROM item_variants")
cur.execute("DELETE FROM items")
conn.commit()

item = items.create_item(name="Grouped Item", category="Food", selling_price=5.0, cost_price=2.0, quantity=0, low_stock_threshold=5)
item_id = item['item_id']
variants.create_variant(item_id, 'One', 5.0, 2.0, quantity=1)
variants.create_variant(item_id, 'Two', 6.0, 3.0, quantity=10)

root = tk.Tk()
root.withdraw()
frame = InventoryFrame(root)
frame.refresh()

for parent in frame.tree.get_children():
    print('Parent:', parent, frame.tree.item(parent, 'values'))
    children = frame.tree.get_children(parent)
    for c in children:
        print('  Child:', c, frame.tree.item(c, 'values'))

root.destroy()