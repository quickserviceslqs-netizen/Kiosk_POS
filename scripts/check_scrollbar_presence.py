import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
from tkinter import ttk
from ui.inventory import InventoryFrame
root = tk.Tk()
root.withdraw()
frame = InventoryFrame(root)
root.update_idletasks()
found = False
print('tk.HORIZONTAL:', repr(tk.HORIZONTAL), 'type:', type(tk.HORIZONTAL))
for w in frame.tree_frame.winfo_children():
    try:
        print('child:', repr(w), 'type:', type(w), 'orient:', end=' ')
        try:
            print(w.cget('orient'))
        except Exception as e:
            print('<no orient>', e)
        is_scrollbar = isinstance(w, ttk.Scrollbar)
        print('is_scrollbar:', is_scrollbar)
        try:
            val = w.cget('orient')
            print('  orient repr:', repr(val), 'tk.HORIZONTAL repr:', repr(tk.HORIZONTAL))
            print('  equals:', val == tk.HORIZONTAL)
        except Exception:
            print('  equals: <error>')
        if is_scrollbar and w.cget('orient') == tk.HORIZONTAL:
            found = True
            print('Found horizontal scrollbar:', w)
    except Exception as e:
        print('error', e)
print('found==', found)
root.destroy()
