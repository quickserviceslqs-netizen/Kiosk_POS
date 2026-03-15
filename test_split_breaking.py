#!/usr/bin/env python
"""Test the updated get_sales_by_payment_method that breaks splits into channels."""

from modules.reports import get_sales_by_payment_method

# Test with March reconciliation
start_date = '2026-03-01'
end_date = '2026-03-31'

print('=== BREAKING SPLITS TEST ===')
print('Period:', start_date, 'to', end_date)
print()

sales_data = get_sales_by_payment_method(start_date, end_date)
print('Sales by payment method (splits broken into channels):')
for row in sales_data:
    print('  ', row['payment_method'], ':', row['total_sales'])

if not sales_data:
    print('  No sales found')

print('\nNote: "Split" should NOT appear as a payment method.')
print('Instead, each channel should show its combined amount.')
