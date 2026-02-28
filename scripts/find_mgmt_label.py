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

found = []

def find_text(widget):
    try:
        if hasattr(widget, 'cget'):
            t = widget.cget('text')
            if t and 'Data Management' in t:
                found.append((type(widget).__name__, repr(t)))
    except:
        pass
    for c in widget.winfo_children():
        find_text(c)

find_text(frame.content_frame)
print('Found entries:', found)

root.after(500, root.destroy)
root.mainloop()