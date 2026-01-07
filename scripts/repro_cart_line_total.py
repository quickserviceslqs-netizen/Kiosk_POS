import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items

# Create a non-special item with package size >1
it = items.create_item(name='Repro NonSpecial', selling_price=40.0, unit_of_measure='liters', unit_size_ml=4, quantity=100)
# Simulate adding two units (units, not packages)
entry = {'item_id': it['item_id'], 'price': it['selling_price'], 'quantity': 2}
# Expected: per_unit = 40/4 = 10; line_total = 10*2 = 20
unit_size = float(it['unit_size_ml'])
per_unit = it['selling_price'] / unit_size
expected = per_unit * entry['quantity']
print('Expected line total:', expected)
# Direct compute to verify
line_total = (entry['price'] / unit_size) * entry['quantity']
print('Computed line total:', line_total)

# cleanup
items.delete_item(it['item_id'])
