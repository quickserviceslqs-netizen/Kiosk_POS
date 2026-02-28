import sys
import traceback
sys.path.append('.')
import tkinter as tk
from ui.order_history_fixed import OrderHistoryFrame


def run_test():
    root = tk.Tk()
    root.withdraw()
    frame = OrderHistoryFrame(root)

    try:
        # Apply narrow date range and call filter
        frame.start_date.set(frame.start_date.get())
        frame.end_date.set(frame.end_date.get())
        frame._filter_orders()
        print('Order history filter applied successfully; rows:', len(frame.tree.get_children()) if frame.tree else 'no-tree')
    except Exception as e:
        print('Order history filter test failed:', e)
        traceback.print_exc()

    root.destroy()

if __name__ == '__main__':
    run_test()
