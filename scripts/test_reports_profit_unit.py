import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import items, pos, reports, receipts
from database.init_db import get_connection

# Get baseline revenue for today
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
base = reports.get_profit_analysis(today, today)
base_revenue = base['total_revenue']

# Create non-special item: package size 4, bulk price 40 -> per unit 10
it1 = items.create_item(name='ReportProfitNonSpecial', selling_price=40.0, unit_of_measure='pieces', unit_size_ml=4, quantity=10, cost_price=20.0)
# Create sale with 2 units (per-unit price expected 10)
sale1 = pos.create_sale([{'item_id': it1['item_id'], 'quantity': 2, 'price': 10.0}], payment=20.0)

# Create special item (litre): selling_price 10 per L => price per ml = 0.01
it2 = items.create_item(name='ReportProfitSpecial', selling_price=10.0, unit_of_measure='liters', unit_size_ml=1, quantity=10, is_special_volume=1, cost_price=4.0)
price_per_ml = it2['selling_price'] / (float(it2['unit_size_ml'] or 1) * float(it2['unit_multiplier'] or 1))
# Sell 385 ml
sale2 = pos.create_sale([{'item_id': it2['item_id'], 'quantity': 385.0, 'price': price_per_ml, 'is_special_volume': True, 'qty_ml': 385.0, 'price_per_ml': price_per_ml}], payment=price_per_ml*385.0)

# Now fetch profit analysis for today
res = reports.get_profit_analysis(today, today)
print('Profit report:', res)

# Expected revenue (delta) = 2*10 + 385*0.01 = 20 + 3.85 = 23.85
expected_revenue_delta = 20 + round(385*price_per_ml, 6)
actual_delta = res['total_revenue'] - base_revenue
assert abs(actual_delta - expected_revenue_delta) < 1e-6, f"Expected revenue delta {expected_revenue_delta}, got {actual_delta}"

# Cleanup
with get_connection() as conn:
    conn.execute('DELETE FROM sales_items WHERE sale_id IN (?,?)', (sale1['sale_id'], sale2['sale_id']))
    conn.execute('DELETE FROM sales WHERE sale_id IN (?,?)', (sale1['sale_id'], sale2['sale_id']))
items.delete_item(it1['item_id'])
items.delete_item(it2['item_id'])
print('Test passed')
