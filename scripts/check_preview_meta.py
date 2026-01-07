import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, units_of_measure as uom

rows = items.list_items()
for r in rows:
    unit = r.get('unit_of_measure') or 'pieces'
    unit_size = float(r.get('unit_size_ml') or 1)
    sell = float(r.get('selling_price') or 0)
    u = uom.get_unit_by_name(unit) or {}
    abbr = u.get('abbreviation') or unit
    price_per_large = sell / unit_size if unit_size > 0 else sell
    print(r['item_id'], r['name'][:20].ljust(20), 'stock', r.get('quantity'), 'preview:', f"{price_per_large:.2f}/{abbr}")
