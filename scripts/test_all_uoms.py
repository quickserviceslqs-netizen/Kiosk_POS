import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from modules import units_of_measure as uom, items

units = uom.list_units(active_only=False)
errors = []
for unit in units:
    name = unit['name']
    abbr = unit.get('abbreviation')
    conv = float(unit.get('conversion_factor') or 1)
    # create ephemeral item: unit_size=1, selling_price=10
    it = items.create_item(name=f'Test_{name}', selling_price=10.0, unit_of_measure=name, unit_size_ml=1, is_special_volume=1)
    # UI price per large unit should be selling_price / unit_size
    ui_ppu = it['selling_price'] / it['unit_size_ml']
    # DB small-unit price should be selling_price / (unit_size * conv)
    db_small = it.get('selling_price_per_unit')
    if db_small is None:
        errors.append((name, 'missing selling_price_per_unit'))
    else:
        db_large = db_small * conv
        diff = abs(ui_ppu - db_large)
        if diff > 1e-6:
            errors.append((name, ui_ppu, db_large, diff))
    # cleanup
    items.delete_item(it['item_id'])

if not errors:
    print('All UoMs consistent:', [u['name'] for u in units])
else:
    print('Errors:')
    for e in errors:
        print(e)
