import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
import tkinter as tk
from ui.pos import PosFrame
from modules import items, units_of_measure as uom

# Create a small Tk context (withdrawn to avoid popping a window)
root = tk.Tk()
root.withdraw()
pos = PosFrame(root)

# Create special (fractional) item
it = items.create_item(name='CartSpecialPriceDisplay', selling_price=10.0, unit_of_measure='liters', unit_size_ml=1, is_special_volume=1, quantity=5)
multiplier = uom.get_conversion_factor(it['unit_of_measure'])
pp_small = it['selling_price'] / (float(it['unit_size_ml'] or 1) * multiplier)

# Add 385 ml to cart
pos._add_special_sale(it, qty_small=385.0, price_per_unit=pp_small, display_unit='ml', multiplier=multiplier)

children = pos.tree.get_children()
if not children:
    print('FAIL: no cart rows found')
else:
    last = children[-1]
    vals = pos.tree.item(last, 'values')
    price_display = vals[1]
    print('Cart price display:', price_display)
    expected = f"{pos.currency_symbol} {pp_small:.6f}/ml"
    if price_display.startswith(expected):
        print('PASS: price shown per small unit')
    else:
        print('FAIL: expected', expected)

# Cleanup
items.delete_item(it['item_id'])
print('Done')
