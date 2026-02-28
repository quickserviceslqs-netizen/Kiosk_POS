import sys
sys.path.append('.')
import tkinter as tk
from ui.reports import ModernReportsFrame
from ui.reports_service import ReportService
from datetime import datetime

root = tk.Tk()
root.geometry('900x700')
frame = ModernReportsFrame(root)
frame.pack(fill=tk.BOTH, expand=True)
root.update()
service = ReportService()
today = datetime.now().strftime('%Y-%m-%d')
gen = service.generators['inventory_stock_levels'](today, today)
rd = gen.generate_data()
print('Generated:', len(rd.data))
frame._display_report(rd)
root.update()

# find Text widgets
texts = []

def find_texts(w):
    if isinstance(w, tk.Text):
        return [w]
    out = []
    if hasattr(w, 'winfo_children'):
        for ch in w.winfo_children():
            out.extend(find_texts(ch))
    return out

texts = find_texts(frame.content_frame)
print('Found text widgets:', len(texts))
if texts:
    content = texts[0].get('1.0', tk.END).strip()
    print('Content length:', len(content))
    print('Preview:\n', content[:300])
else:
    print('No text widgets found')

root.destroy()
print('Done')