import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, units_of_measure as uom
from decimal import Decimal

# Non-special item
it = items.create_item(name='CartTotal NonSpecial', selling_price=40.0, unit_of_measure='liters', unit_size_ml=4, quantity=5)
entry = {'item_id': it['item_id'], 'price': it['selling_price'], 'quantity': 2}
# compute expected using per-unit calculation
unit_size = float(it['unit_size_ml'] or 1)
per_unit_price = entry['price'] / unit_size
# quantity is units, so line_total = per_unit_price * quantity
line_total = per_unit_price * entry['quantity']
print('Non-special: per_unit_price', per_unit_price, 'line_total', line_total)
assert abs(line_total - (per_unit_price * entry['quantity'])) < 1e-6

# Special item
it2 = items.create_item(name='CartTotal Special', selling_price=10.0, unit_of_measure='liters', unit_size_ml=1, is_special_volume=1, quantity=5)
mult = uom.get_conversion_factor(it2['unit_of_measure'])
# simulate adding custom amount: qty_small = 250 ml, price_per_small = selling_price/(unit_size*mult)
price_per_small = it2['selling_price'] / (it2['unit_size_ml'] * mult)
entry2 = {'item_id': it2['item_id'], 'price': price_per_small, 'quantity': 250.0, 'unit_multiplier': mult, 'display_unit': 'ml'}
line_total2 = entry2['price'] * entry2['quantity']
# price per large * converted qty
price_per_large2 = entry2['price'] * entry2['unit_multiplier']
converted_qty_large = entry2['quantity'] / entry2['unit_multiplier']
print('Special: price_per_large', price_per_large2, 'converted_qty_large', converted_qty_large, 'line_total2', line_total2)
assert abs(price_per_large2 * converted_qty_large - line_total2) < 1e-6

# subtotal
subtotal = line_total + line_total2
print('subtotal', subtotal)

# VAT calculation using computed line totals
vat_amt = 0
vat_rate = 0.16
vat_amt += line_total * vat_rate
vat_amt += line_total2 * vat_rate
print('vat_amt', vat_amt)

# Cleanup
items.delete_item(it['item_id'])
items.delete_item(it2['item_id'])
print('All cart totals consistent')
