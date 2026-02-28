import sys
sys.path.append('.')
import tkinter as tk
from ui.reports import ModernReportsFrame
from ui.reports_service import ReportService
from datetime import datetime, timedelta

root = tk.Tk(); root.geometry('1000x700')
frame = ModernReportsFrame(root); frame.pack(fill=tk.BOTH, expand=True)
root.update()
service = ReportService()
start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
end = datetime.now().strftime('%Y-%m-%d')

# Sales log test
gen = service.generators['sales_log'](start, end)
rd = gen.generate_data()
print('Sales log rows:', len(rd.data))
frame._display_report(rd)
root.update()
from tkinter import ttk
found_sales_tree = False
for w in frame.content_frame.winfo_children():
    if isinstance(w, ttk.LabelFrame):
        for c in w.winfo_children():
            if isinstance(c, ttk.Treeview):
                found_sales_tree = True
                print('Found Treeview with', len(c.get_children()), 'rows')
                break
    if found_sales_tree:
        break

# Reconciliation details test
gen = service.generators['reconciliation_details'](start, end, 'all')
rd2 = gen.generate_data()
print('Reconciliation sessions:', len(rd2.data))
frame._display_report(rd2)
root.update()
found_recon_tree = False
for w in frame.content_frame.winfo_children():
    if isinstance(w, ttk.LabelFrame):
        for c in w.winfo_children():
            if isinstance(c, ttk.Treeview):
                found_recon_tree = True
                print('Found Treeview with', len(c.get_children()), 'rows')
                break
    if found_recon_tree:
        break

root.destroy()
print('Done')