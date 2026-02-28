import sys
sys.path.append('.')
from ui.reports_export import ExportManager
from datetime import datetime

em = ExportManager()
start = end = datetime.now().strftime('%Y-%m-%d')
print('Streaming sales_log to /tmp/sales_log.csv')
ok = em.export_report_streaming('sales_log', start, end, 'test_sales_log.csv', page_size=2, use_keyset=True)
print('sales_log export ok?', ok)
print('Streaming reconciliation_details to test_recon.csv')
ok2 = em.export_report_streaming('reconciliation_details', start, end, 'test_recon.csv', page_size=10, use_keyset=False)
print('reconciliation export ok?', ok2)
