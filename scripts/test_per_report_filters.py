import sys
sys.path.append('.')
import tkinter as tk
from ui.reports import ModernReportsFrame
from ui.reports_service import ReportService
from datetime import datetime

root = tk.Tk()
root.withdraw()
frame = ModernReportsFrame(root)
service = ReportService()

today = datetime.now().strftime('%Y-%m-%d')

# Sales_log check
try:
    gen_sales = service.generators['sales_log'](today, today)
    rd_sales = gen_sales.generate_data()
    frame._display_report(rd_sales)
    has_sales_dates = 'sales_log' in frame._local_date_vars
    print('sales_log local dates present:', has_sales_dates)
    sv, ev = frame._local_date_vars.get('sales_log', (None, None))
    print('sales_log start:', sv.get() if sv else None, 'end:', ev.get() if ev else None)
except Exception as e:
    print('sales_log test error:', e)

# Reconciliation check
try:
    gen_recon = service.generators['reconciliation_summary'](today, today, 'all')
    rd_recon = gen_recon.generate_data()
    frame._display_report(rd_recon)
    has_recon_dates = 'reconciliation_summary' in frame._local_date_vars
    has_recon_status = 'reconciliation_summary' in frame._local_status_vars
    print('reconciliation local dates present:', has_recon_dates)
    print('reconciliation local status present:', has_recon_status)
    if has_recon_status:
        print('reconciliation status:', frame._local_status_vars['reconciliation_summary'].get())
except Exception as e:
    print('reconciliation test error:', e)

root.destroy()
