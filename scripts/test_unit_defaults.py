import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items

# Create a pieces item without specifying unit_size_ml
p = items.create_item(name='UT Test Pieces', selling_price=5.0, unit_of_measure='pieces')
print('pieces:', p['item_id'], p['unit_of_measure'], p['unit_size_ml'], 'selling_price', p['selling_price'])
# Create a liters item without specifying unit_size_ml
l = items.create_item(name='UT Test Litre', selling_price=10.0, unit_of_measure='liters')
print('liters:', l['item_id'], l['unit_of_measure'], l['unit_size_ml'], 'selling_price', l['selling_price'])

# Check computed per-base price (selling_price_per_unit) is correct
print('pieces price per base:', p.get('selling_price_per_unit'))
print('litre price per base:', l.get('selling_price_per_unit'))

# Cleanup
items.delete_item(p['item_id'])
items.delete_item(l['item_id'])
print('cleanup done')
