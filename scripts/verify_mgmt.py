import sys
sys.path.append('.')
from ui.reports import ModernReportsFrame
from ui.reports_base import ReportData
import tkinter as tk

root = tk.Tk()
root.geometry('1000x700')
frame = ModernReportsFrame(root)
frame.pack(fill=tk.BOTH, expand=True)
root.update()

mock = ReportData('daily', '2026-02-01', '2026-02-01', [{'a':1}], {})
frame._display_report(mock)
root.update()

# check for Data Management label and Manage button
found_label = False
found_manage = False
for child in frame.content_frame.winfo_children():
    header = child
    break
for w in header.winfo_children():
    try:
        t = w.cget('text')
    except:
        t = ''
    if 'Data Management' in t:
        found_label = True
    if 'Manage' in t:
        found_manage = True
print('Data Management label present:', found_label)
print('Manage button present:', found_manage)

root.after(500, root.destroy)
root.mainloop()