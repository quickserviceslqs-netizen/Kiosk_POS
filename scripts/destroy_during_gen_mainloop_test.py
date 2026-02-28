import sys
sys.path.append('.')
from ui.reports import ModernReportsFrame
import tkinter as tk

root = tk.Tk()
root.geometry('1000x700')
frame = ModernReportsFrame(root)
frame.pack(fill=tk.BOTH, expand=True)

# Schedule report generation in 100ms, then destroy frame in 500ms
root.after(100, frame._generate_overview_data)
root.after(500, frame.destroy)

# Stop the loop after 1500ms
root.after(1500, root.destroy)
print('Starting mainloop test...')
root.mainloop()
print('Test completed')