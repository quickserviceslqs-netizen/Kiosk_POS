import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, portions
import traceback

# Create a temporary test item
item = items.create_item(name='Test Item for Portions', category='Uncategorized', cost_price=0, selling_price=10.0, quantity=10, unit_of_measure='liters', is_special_volume=1, unit_size_ml=1000)
print('CREATED ITEM', item['item_id'])
try:
    # Emulate UI behavior: default cost to 0.0 if unknown
    p = portions.create_portion(item['item_id'], 'Test Default Cost', 100, 1.23, 0.0)
    print('CREATED PORTION', p)
    # Now test update to ensure updates with zero cost succeed
    updated = portions.update_portion(p['portion_id'], portion_name='Test Updated', portion_ml=150, selling_price=1.23*1.5, cost_price=0.0)
    print('UPDATED PORTION', updated)
    # Test creating default portions
    created_defaults = portions.create_default_portions(item['item_id'], price_per_liter=10.0, cost_per_liter=0.0)
    print('CREATED DEFAULTS', created_defaults)
except Exception:
    traceback.print_exc()