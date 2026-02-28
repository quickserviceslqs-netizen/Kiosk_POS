import sys
sys.path.append('.')
import tkinter as tk
from ui.reports import ModernReportsFrame
from ui.reports_service import ReportService
from datetime import datetime, timedelta

root = tk.Tk()
root.geometry('1000x800')
frame = ModernReportsFrame(root)
frame.pack(fill=tk.BOTH, expand=True)
root.update()
service = ReportService()

start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
end = datetime.now().strftime('%Y-%m-%d')

report_types = ['daily','range','bestsellers','profit','category','payment_methods','voided','sales_log','transactions','trends','inventory_stock_levels','reconciliation_summary']

for r in report_types:
    try:
        if 'reconciliation' in r:
            gen = service.generators[r](start, end, 'all')
        else:
            gen = service.generators[r](start, end)
        rd = gen.generate_data()
        print(f'{r}: data {len(rd.data)}')
        frame._display_report(rd)
        root.update()
        # find text
        def find_texts(w):
            if isinstance(w, tk.Text):
                return [w]
            out = []
            if hasattr(w, 'winfo_children'):
                for ch in w.winfo_children():
                    out.extend(find_texts(ch))
            return out
        texts = find_texts(frame.content_frame)
        print('  Text widgets:', len(texts))
        if texts:
            print('  Content preview length:', len(texts[0].get('1.0', tk.END)))
    except Exception as e:
        print(f'  Error for {r}: {e}')

root.destroy()
print('Done')