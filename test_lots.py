from modules.inventory_costing import get_stock_lots

lots = get_stock_lots(55)
print(f'Available lots for item 55: {len(lots)}')
for lot in lots:
    print(f'  Lot {lot.lot_id}: remaining {lot.quantity_remaining}, expiry {lot.expiry_date}')