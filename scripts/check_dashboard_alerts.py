import sys
sys.path.append('.')
import tkinter as tk
from ui.dashboard import DashboardFrame

root = tk.Tk()
root.withdraw()
frame = DashboardFrame(root)
frame._refresh_data()

children = frame.alerts_tree.get_children()
print('Number of alerts in dashboard:', len(children))
for cid in children:
    vals = frame.alerts_tree.item(cid, 'values')
    print('  ', vals)

root.destroy()
