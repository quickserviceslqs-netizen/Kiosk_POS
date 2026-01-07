import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items
from database import init_db

EPS = 1e-6

def get_multiplier(unit):
    return items._get_unit_multiplier(unit)

all_items = items.list_items()
problems = []
for it in all_items:
    item_id = it['item_id']
    name = it['name']
    unit = (it.get('unit_of_measure') or 'pieces').lower()
    unit_size = float(it.get('unit_size_ml') or 1)
    selling_price = float(it.get('selling_price') or 0)
    # UI logic: price per large unit (e.g., per L/kg/m) = selling_price / unit_size
    ui_price_per_large = selling_price / unit_size if unit_size > 0 else selling_price

    # DB stored selling_price_per_unit is small-unit based (per ml/g/cm) according to modules.items
    db_price_per_small = it.get('selling_price_per_unit')
    multiplier = get_multiplier(unit)
    # Convert DB small-unit price -> large unit price
    db_price_per_large = None
    if db_price_per_small is not None:
        db_price_per_large = db_price_per_small * multiplier

    # Decide expected value to compare: if db_price_per_large available compare to ui calc
    if db_price_per_large is not None:
        diff = abs(ui_price_per_large - db_price_per_large)
        if diff > max(EPS, 0.0001 * abs(ui_price_per_large)):
            problems.append((item_id, name, unit, unit_size, selling_price, ui_price_per_large, db_price_per_large, diff))
    else:
        # if DB value missing, compute via modules.items logic
        # simulate create_item calculation
        total_units = unit_size * multiplier
        db_sim_small = selling_price / total_units if total_units > 0 else None
        if db_sim_small is not None:
            db_sim_large = db_sim_small * multiplier
            diff = abs(ui_price_per_large - db_sim_large)
            if diff > max(EPS, 0.0001 * abs(ui_price_per_large)):
                problems.append((item_id, name, unit, unit_size, selling_price, ui_price_per_large, db_sim_large, diff))

# Report
if not problems:
    print('All conversions consistent across items.')
else:
    print('Conversion mismatches found:')
    for p in problems:
        print('ID', p[0], 'Name', p[1][:30].ljust(30), 'unit', p[2], 'unit_size', p[3], 'bulk', p[4], 'ui_per_large', f'{p[5]:.6f}', 'db_per_large', f'{p[6]:.6f}', 'diff', f'{p[7]:.6f}')
