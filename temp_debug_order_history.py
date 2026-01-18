import traceback
try:
    from ui.order_history import OrderHistoryFrame
    import tkinter as tk
    root = tk.Tk()
    frame = OrderHistoryFrame(root)
    print('OrderHistoryFrame initialized, tree is', frame.tree)
    if frame.tree:
        print('Tree has children:', len(frame.tree.get_children()))
    root.destroy()
except Exception:
    traceback.print_exc()
    raise
