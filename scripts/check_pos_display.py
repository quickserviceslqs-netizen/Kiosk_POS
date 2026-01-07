import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, units_of_measure as uom

rows = items.list_items()
for r in rows:
    unit = (r.get('unit_of_measure') or '').lower()
    unit_size = float(r.get('unit_size_ml') or 1)
    price = float(r.get('selling_price') or 0)
    # fetch uom info
    u = uom.get_unit_by_name(r.get('unit_of_measure') or '') or {}
    abbr = u.get('abbreviation') or (r.get('unit_of_measure') or '')
    price_per_unit = price / unit_size if unit_size > 0 else price
    display = f"{price_per_unit:.2f}/{abbr}"
    print(r['item_id'], r['name'][:20].ljust(20), 'bulk=', f"{price:.2f}".rjust(6), '-> display', display)
