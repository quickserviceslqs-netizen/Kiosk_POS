import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items
rows = items.list_items()
for r in rows[-5:]:
    unit = r.get('unit_of_measure','pieces')
    price = r.get('selling_price',0)
    unit_size = float(r.get('unit_size_ml') or 1)
    # Price per large base unit (e.g., per L/kg/m) should be price / unit_size
    price_per_base = price / unit_size if unit_size > 0 else price
    print(r['item_id'], r['name'][:30].ljust(30), unit.ljust(8), f'bulk={price:8.2f}', f'unit_size={unit_size:8.2f}', f'price_per_base={price_per_base:8.4f}')