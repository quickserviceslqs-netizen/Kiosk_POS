import sys
sys.path.append('.')
from ui.reports_service import ReportService
from datetime import datetime

s = ReportService()
start = end = datetime.now().strftime('%Y-%m-%d')
print('Testing sales_log keyset paging')
cursor = None
page = 1
while True:
    rows, next_cursor, meta = s.generate_report_page('sales_log', start, end, page_size=3, cursor=cursor, use_keyset=True)
    print(f'Page {page}: {len(rows)} rows, next={next_cursor}')
    if not next_cursor:
        break
    cursor = next_cursor
    page += 1

print('\nTesting reconciliation_details offset paging')
cursor = None
page = 1
while True:
    rows, next_cursor, meta = s.generate_report_page('reconciliation_details', start, end, page_size=10, cursor=cursor, use_keyset=False)
    print(f'Page {page}: {len(rows)} rows, next={next_cursor}')
    if not next_cursor:
        break
    cursor = next_cursor
    page += 1
