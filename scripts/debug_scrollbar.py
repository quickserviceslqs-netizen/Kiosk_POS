import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
from tkinter import ttk
from ui.inventory import InventoryFrame
root = tk.Tk()
root.withdraw()
frame = InventoryFrame(root)
root.update_idletasks()
print('tree_frame children:', frame.tree_frame.winfo_children())
for w in frame.tree_frame.winfo_children():
    print('WIDGET:', w, 'TYPE:', type(w))
    if isinstance(w, tk.Scrollbar) or isinstance(w, ttk.Scrollbar):
        try:
            print('  orient:', w.cget('orient'))
        except Exception as e:
            print('  orient: <error>', e)
    try:
        print('  grid_info:', w.grid_info())
    except Exception as e:
        print('  grid_info: <error>', e)
root.destroy()
