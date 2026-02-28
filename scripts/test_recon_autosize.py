import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
from ui.reconciliation_ui import ReconciliationUI

root = tk.Tk()
root.geometry('900x600')
root.title('Autosize Test')
ui = ReconciliationUI(root)
ui.pack(fill='both', expand=True)
# Create a session
try:
    ui._create_new_session()
except Exception as e:
    print('Warning while creating session:', e)
root.update()
print('System tree columns:', ui.system_tree['columns'])
print('System tree column widths:', [ui.system_tree.column(c,'width') for c in ui.system_tree['columns']])
print('Manual tree column widths:', [ui.manual_tree.column(c,'width') for c in ui.manual_tree['columns']])
root.after(500, root.destroy)
root.mainloop()
print('Done')
