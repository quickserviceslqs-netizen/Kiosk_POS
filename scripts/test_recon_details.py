import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
from ui.reconciliation_ui import ReconciliationUI

root = tk.Tk()
root.geometry('1000x700')
ui = ReconciliationUI(root)
ui.pack(fill='both', expand=True)
try:
    ui._create_new_session()
except Exception as e:
    print('Note while creating session:', e)
root.update()
# Open details window
ui._open_details_window()
print('Details window opened:', ui._details_window is not None)
root.after(800, lambda: (ui._close_details_window(), root.destroy()))
root.mainloop()
print('Done')
