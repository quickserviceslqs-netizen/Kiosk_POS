import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, pos, refunds

# Create a test item
item = items.create_item(name='Refund Test Item', category='Uncategorized', cost_price=1.0, selling_price=5.0, quantity=10, unit_of_measure='pieces')
print('Item created', item['item_id'])

# Create a sale
sale = pos.create_sale([{'item_id': item['item_id'], 'quantity': 2, 'price': 5.0}], payment=10.0)
print('Sale created', sale)

# Attempt refund
refund = refunds.create_refund(original_sale_id=sale['sale_id'], refund_items=[{'item_id': item['item_id'], 'quantity': 2}], reason='Test refund')
print('Refund created', refund)
