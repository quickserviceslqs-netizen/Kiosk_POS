import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
import tkinter as tk
from modules import items
import time

# Ensure an item exists with is_special_volume
it = items.list_items()
item = None
for i in it:
    if i.get('is_special_volume'):
        item = i
        break
if not item:
    item = items.create_item(name='AutoPortions Test', category='Uncategorized', cost_price=0, selling_price=10.0, quantity=10, unit_of_measure='liters', is_special_volume=1, unit_size_ml=1000)

root = tk.Tk()
root.withdraw()

from ui.inventory import InventoryFrame
frame = InventoryFrame(root)
frame.pack()

# Open dialog after loop starts
def open_edit():
    frame._open_item_dialog(title='Edit Item', existing=item)

# After dialog opens, find the Manage Portions button and click it
def click_manage_portions():
    # iterate all toplevel children and print hierarchy
    def dump_children(w, depth=0, max_depth=4):
        indent = '  ' * depth
        try:
            txt = ''
            if hasattr(w, 'cget'):
                try:
                    txt = w.cget('text')
                except Exception:
                    txt = ''
            print(f"{indent}{w.__class__.__name__}: text={txt}")
            if depth < max_depth:
                for child in w.winfo_children():
                    dump_children(child, depth+1, max_depth)
        except Exception as e:
            print('dump error', e)

    for w in root.winfo_children():
        dump_children(w)

    # now try to find and click
    for w in root.winfo_children():
        try:
            for child in w.winfo_children():
                for gc in child.winfo_children():
                    if hasattr(gc, 'cget') and gc.cget('text') == 'Manage Portions':
                        print('Found nested button, invoking')
                        gc.invoke()
                        return
                if hasattr(child, 'cget') and child.cget('text') == 'Manage Portions':
                    print('Found child button, invoking')
                    child.invoke()
                    return
            if hasattr(w, 'cget') and w.cget('text') == 'Manage Portions':
                print('Found top widget button, invoking')
                w.invoke()
                return
        except Exception as e:
            print('Error scanning children', e)

    # Give UI a moment and dump children again to see if dialog appeared
    import time
    time.sleep(0.5)
    print('\nAfter click:')
    for w in root.winfo_children():
        dump_children(w)
    # wait briefly to allow dialog to be fully created
    time.sleep(1)

# Schedule
root.after(200, open_edit)
root.after(800, click_manage_portions)

# End after a short period
root.after(3000, root.destroy)
root.mainloop()
print('Done')