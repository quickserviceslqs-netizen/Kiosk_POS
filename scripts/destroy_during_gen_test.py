import sys
sys.path.append('.')
from ui.reports import ModernReportsFrame
import tkinter as tk
import time

root = tk.Tk()
root.geometry('1000x700')
frame = ModernReportsFrame(root)
frame.pack(fill=tk.BOTH, expand=True)
root.update()

frame._generate_overview_data()
# destroy the frame immediately to simulate user closing window during generation
frame.destroy()

# allow some time for worker to finish
time.sleep(1.5)
print('Destroyed frame during generation; no crash should occur')
root.destroy()