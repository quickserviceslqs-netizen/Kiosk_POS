import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, pos, refunds, reports
from database.init_db import get_connection
from datetime import datetime

# Create an item
it = items.create_item(name='ReportRefundTest', selling_price=10.0, unit_of_measure='pieces', unit_size_ml=1, quantity=10, cost_price=4.0)

# Get baseline revenue for today
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
base = reports.get_profit_analysis(today, today)
base_revenue = base['total_revenue']

# Create a sale with 2 units -> revenue 2*10 = 20
sale = pos.create_sale([{'item_id': it['item_id'], 'quantity': 2, 'price': 10.0}], payment=20.0)

# Refund 1 unit for this sale
sale_data = None
from modules import receipts
sale_data = receipts.get_sale_with_items(sale['sale_id'])
sale_item = sale_data['items'][0]
refund = refunds.create_refund(sale['sale_id'], [{'sale_item_id': sale_item['sale_item_id'], 'item_id': it['item_id'], 'quantity': 1}], 'Customer return')

# Compute profit for today
today = datetime.now().strftime('%Y-%m-%d')
res = reports.get_profit_analysis(today, today)
print('Profit report after refund:', res)

# Expected net revenue delta = sale revenue (20) - refunded (10) = 10
expected_delta = 10.0
actual_delta = res['total_revenue'] - base_revenue
assert abs(actual_delta - expected_delta) < 1e-6, f"Expected revenue delta {expected_delta}, got {actual_delta}"

# Cleanup
with get_connection() as conn:
    conn.execute('DELETE FROM refunds_items WHERE refund_id = ?', (refund['refund_id'],))
    conn.execute('DELETE FROM refunds WHERE refund_id = ?', (refund['refund_id'],))
    conn.execute('DELETE FROM sales_items WHERE sale_id = ?', (sale['sale_id'],))
    conn.execute('DELETE FROM sales WHERE sale_id = ?', (sale['sale_id'],))
items.delete_item(it['item_id'])
print('Test passed')