from modules import reconciliation
from datetime import datetime

# Test basic functionality
try:
    start_date, end_date = reconciliation.calculate_date_range('daily', '2026-01-18')
    print(f'Date range: {start_date} to {end_date}')

    # Test getting sales data
    sales_data = reconciliation.get_sales_by_payment_method_for_period(start_date, end_date)
    print(f'Sales data found: {len(sales_data)} payment methods')
    for entry in sales_data:
        print(f'  {entry["payment_method"]}: {entry["total_sales"]:.2f} ({entry["transaction_count"]} transactions)')

    print('Reconciliation module working correctly')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()