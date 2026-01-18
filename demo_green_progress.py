#!/usr/bin/env python3
"""
Demo script to show the green progress bar in StatusDialog.
"""

import tkinter as tk
from tkinter import ttk
import time
import threading
import ui.upgrade_manager

def demo_green_progress():
    """Demo the green progress bar in StatusDialog."""
    root = tk.Tk()
    root.title("Demo: Green Progress Bar")
    root.geometry("400x200")

    def show_status_dialog():
        # Create StatusDialog
        dialog = ui.upgrade_manager.StatusDialog(root, "Demo Operation", "Demo")

        # Simulate progress updates
        def update_progress():
            for i in range(0, 101, 10):
                dialog.update_status(f"Processing step {i//10 + 1}/11", i)
                dialog.update_operation(f"Working on item {i//10 + 1}")
                dialog.add_log(f"Completed step {i//10 + 1}")
                time.sleep(0.5)

            dialog.set_success(True, "Demo completed successfully!")

        # Run in thread
        thread = threading.Thread(target=update_progress, daemon=True)
        thread.start()

    # Button to show dialog
    btn = ttk.Button(root, text="Show Green Progress Bar Demo",
                    command=show_status_dialog)
    btn.pack(pady=50, padx=50)

    root.mainloop()

if __name__ == "__main__":
    demo_green_progress()