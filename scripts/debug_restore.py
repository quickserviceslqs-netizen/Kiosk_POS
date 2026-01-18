import sys, os, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
from database import init_db
from ui.inventory import InventoryFrame

root=tk.Tk()
root.withdraw()
frame=InventoryFrame(root)
print('initial displaycolumns:', tuple(frame.tree['displaycolumns']))
frame._save_visible_columns(['name'])
frame.refresh()
print('after save name only displaycolumns:', tuple(frame.tree['displaycolumns']))
print('columns_hint:', frame.columns_hint.cget('text'))
frame._restore_recommended_columns()
print('after restore displaycolumns:', tuple(frame.tree['displaycolumns']))
print('settings stored:', init_db.get_setting('inventory.columns.visible'))
root.destroy()