import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, units_of_measure as uom

# Non-special item
it = items.create_item(name='CartUnitTest NonSpecial', selling_price=20.0, unit_of_measure='liters', unit_size_ml=1, quantity=5)
# Simulate cart entry
entry = {'item_id': it['item_id'], 'price': it['selling_price'], 'quantity': 2}
unit_size = float(it.get('unit_size_ml') or 1)
expected_price_per_large = entry['price'] / unit_size
uinfo = uom.get_unit_by_name(it['unit_of_measure']) or {}
abbr = uinfo.get('abbreviation') or it['unit_of_measure']
print('Non-special expected', f"{expected_price_per_large:.2f}/{abbr}")

# Special item: price per small unit
it2 = items.create_item(name='CartUnitTest Special', selling_price=10.0, unit_of_measure='liters', unit_size_ml=1, is_special_volume=1, quantity=5)
# Let's say price per ml is selling_price / (unit_size*multiplier)
multiplier = uom.get_conversion_factor(it2['unit_of_measure'])
pp_small = it2['selling_price'] / (it2['unit_size_ml'] * multiplier)
# add special cart entry
entry2 = {'item_id': it2['item_id'], 'price': pp_small, 'quantity': 250.0, 'unit_multiplier': multiplier, 'display_unit': 'ml'}
expected_price_per_large2 = entry2['price'] * multiplier
abbr2 = uom.get_unit_by_name(it2['unit_of_measure']).get('abbreviation')
print('Special expected', f"{expected_price_per_large2:.2f}/{abbr2}")

# cleanup
items.delete_item(it['item_id'])
items.delete_item(it2['item_id'])
print('Test completed')
