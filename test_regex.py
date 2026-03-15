import re
from modules.inventory_costing import get_stock_lots
from modules import portions

# Test dropdown parsing
lots = get_stock_lots(55)
if lots:
    first_lot = lots[0]
    dropdown_text = f'Lot {first_lot.lot_id} - {first_lot.purchase_date or "No Date"} (Qty: {first_lot.quantity_remaining})'
    print(f'Dropdown text: "{dropdown_text}"')

    match = re.match(r'Lot (\d+)', dropdown_text)
    if match:
        lot_id = int(match.group(1))
        print(f'Parsed lot_id: {lot_id}')
    else:
        print('Regex failed to match')

# Test portions
item_portions = portions.list_portions(55, active_only=True)
print(f'\nTotal portions for item 55: {len(item_portions)}')
for p in item_portions:
    print(f'  {p["portion_name"]}: lot_id={p.get("lot_id")}')

# Test filtering
if item_portions:
    filtered = [p for p in item_portions if p.get('lot_id') == 60]
    print(f'\nPortions for lot 60: {len(filtered)}')
    for p in filtered:
        print(f'  {p["portion_name"]}')