import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items
from database.init_db import get_connection

count = 0
with get_connection() as conn:
    conn.row_factory = __import__('sqlite3').Row
    rows = conn.execute('SELECT item_id, selling_price, cost_price, unit_of_measure, unit_size_ml FROM items').fetchall()
    for r in rows:
        item_id = r['item_id']
        selling = float(r['selling_price'] or 0)
        cost = float(r['cost_price'] or 0)
        uom = r['unit_of_measure'] or 'pieces'
        unit_size = float(r['unit_size_ml'] or 1)
        multiplier = items._get_unit_multiplier(uom)
        total_units = unit_size * multiplier
        if total_units > 0:
            sp_per_small = selling / total_units
            cp_per_small = cost / total_units
        else:
            sp_per_small = None
            cp_per_small = None
        conn.execute('UPDATE items SET selling_price_per_unit = ?, cost_price_per_unit = ? WHERE item_id = ?', (sp_per_small, cp_per_small, item_id))
        count += 1
    conn.commit()
print('Recalculated per-unit prices for', count, 'items')
