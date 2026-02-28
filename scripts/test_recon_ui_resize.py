import os
import sys
# Ensure project root is on sys.path when running this script directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from ui.reconciliation_ui import ReconciliationUI
import time

sizes=[(600,400),(1024,768),(1440,900)]
for w,h in sizes:
    root=tk.Tk()
    root.geometry(f"{w}x{h}")
    ui=ReconciliationUI(root)
    ui.pack(fill=tk.BOTH,expand=True)
    # create session
    try:
        ui._create_new_session()
    except Exception as e:
        print(f"Size {w}x{h}: session creation error: {e}")
        root.destroy()
        continue

    # add many manual entries to force scrolling
    for i in range(20):
        ui.add_payment_var.set(f"Manual{i}")
        ui.add_actual_var.set(str(i*10))
        try:
            ui._on_add_manual_entry()
        except Exception as e:
            print(f"Size {w}x{h}: add entry error: {e}")

    ui._refresh_display()
    root.update()
    time.sleep(0.2)

    manual_children=ui.manual_tree.get_children()
    system_children=ui.system_tree.get_children()
    manual_count=len(manual_children)
    system_count=len(system_children)
    overflow=False
    if manual_children:
        last=manual_children[-1]
        bbox=ui.manual_tree.bbox(last)
        tree_h=ui.manual_tree.winfo_height()
        overflow = bool(bbox and (bbox[1]+bbox[3] > tree_h))
    print(f"Size {w}x{h}: manual={manual_count}, system={system_count}, manual_overflow={overflow}")
    root.destroy()

print("Resize checks complete")
