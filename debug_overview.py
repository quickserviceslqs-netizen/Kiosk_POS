#!/usr/bin/env python3
"""Test script to debug overview report loading issue."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import tkinter as tk
from ui.reports import ModernReportsFrame
from datetime import datetime

print('Testing overview generation in UI...')

root = tk.Tk()
root.geometry('800x600')

frame = ModernReportsFrame(root)
frame.pack(fill=tk.BOTH, expand=True)

root.update()

print('Calling _generate_overview_data...')
frame._generate_overview_data()

def check_status():
    try:
        print(f'current_request_id: {getattr(frame, "current_request_id", None)}')
        print(f'Loading visible: {frame.loading_label.winfo_ismapped() if hasattr(frame, "loading_label") else "No loading_label"}')

        # Check metrics frame
        if hasattr(frame, 'metrics_frame'):
            try:
                children = frame.metrics_frame.winfo_children()
                print(f'Metrics displayed: {len(children)} cards')
            except:
                print('Metrics frame destroyed')
        else:
            print('No metrics displayed')
    except Exception as e:
        print(f'Error checking status: {e}')


root.after(3000, check_status)
root.mainloop()
print('Test completed')