import sys
sys.path.append('.')
from ui.reports import ModernReportsFrame
import tkinter as tk

root = tk.Tk()
root.geometry('1000x700')
frame = ModernReportsFrame(root)
frame.pack(fill=tk.BOTH, expand=True)
root.update()

# Force a report generation that previously caused the error (overview)
frame._generate_overview_data()
root.update()

print('Generated overview request; check logs for errors')

root.after(1000, root.destroy)
root.mainloop()