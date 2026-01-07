import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items

# Create a fractional item by specifying listed price per large unit (UI semantics)
unit = 'liters'
unit_size = 1  # 1L per package
listed_ppu = 12.5  # $12.5 per L
multiplier = items._get_unit_multiplier(unit)  # 1000
# Convert to bulk & small-unit price
bulk_price = listed_ppu * unit_size
small_unit_price = listed_ppu / multiplier

it = items.create_item(name='ListedPriceTest', category='Test', cost_price=0, selling_price=bulk_price, quantity=5, unit_of_measure=unit, is_special_volume=1, unit_size_ml=unit_size, price_per_ml=small_unit_price)
print('Created:', it['item_id'], it['name'], 'unit_size', it['unit_size_ml'], 'selling_price', it['selling_price'], 'selling_price_per_unit', it['selling_price_per_unit'], 'price_per_ml', it['price_per_ml'])

# Check that UI would display listed_ppu as selling_price / unit_size
ui_display_ppu = it['selling_price'] / it['unit_size_ml'] if it['unit_size_ml'] else None
print('UI listed ppu', ui_display_ppu, 'expected', listed_ppu)
assert abs(ui_display_ppu - listed_ppu) < 1e-6

# Cleanup
items.delete_item(it['item_id'])
print('Passed')
