import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items

ids = [1,2,3,4,5,6]
for i in ids:
    it = items.get_item(i)
    if not it:
        continue
    unit = (it.get('unit_of_measure') or 'pieces').lower()
    unit_size = float(it.get('unit_size_ml') or 1)
    selling_price = float(it.get('selling_price') or 0)
    selling_price_per_unit = it.get('selling_price_per_unit')
    print('ID', it['item_id'], it['name'][:30].ljust(30), 'unit', unit, 'unit_size', unit_size, 'bulk', selling_price, 'db_small', selling_price_per_unit)
