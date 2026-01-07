import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, units_of_measure as uom

it = items.create_item(name='CartQtyDisplayTest', selling_price=40.0, unit_of_measure='liters', unit_size_ml=4, quantity=10)
entry = {'item_id': it['item_id'], 'price': it['selling_price'], 'quantity': 2}
# Expected qty_display "2 (8.00 L)"
unit_name = it['unit_of_measure']
uinfo = uom.get_unit_by_name(unit_name) or {}
abbr = uinfo.get('abbreviation') or unit_name
total_large = entry['quantity'] * float(it['unit_size_ml'])
expected = f"{entry['quantity']} ({total_large:.2f} {abbr})"
print('Expected qty display:', expected)
# cleanup
items.delete_item(it['item_id'])
print('Test completed')
