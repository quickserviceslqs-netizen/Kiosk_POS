import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items
rows = items.list_items()
if not rows:
    print('no items')
else:
    for r in rows[-10:]:
        unit = r.get('unit_of_measure','pieces')
        price = r.get('selling_price',0)
        unit_size = float(r.get('unit_size_ml') or 1)
        conversions = {'litre':1000,'liter':1000,'liters':1000,'litres':1000,'l':1000,'kilogram':1000,'kilograms':1000,'kg':1000,'kgs':1000,'meter':100,'meters':100,'metre':100,'metres':100,'m':100}
        base_mult = conversions.get(unit.lower(),1)
        price_per_base = price*base_mult/unit_size if unit_size>0 else price
        print(r['item_id'], r['name'][:30].ljust(30), unit.ljust(8), f'bulk={price:8.2f}', f'unit_size={unit_size:8.2f}', f'price_per_base={price_per_base:8.4f}')