#!/usr/bin/env python3
"""
Test script to verify the reconciliation status dialog functionality.
"""
import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_dialog():
    """Test the status dialog functionality."""
    root = tk.Tk()
    root.title("Test Dialog")
    root.geometry("400x300")

    def show_test_dialog():
        """Show a test version of the reconcile status dialog."""
        # Create a popup dialog
        dialog = tk.Toplevel(root)
        dialog.title("Loading Reconciliation")
        dialog.geometry("350x120")
        dialog.resizable(False, False)

        # Center the dialog on screen
        dialog.transient(root)
        dialog.grab_set()

        # Calculate center position
        dialog.update_idletasks()  # Update to get correct dimensions
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        # Add content
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="🔄 Loading Reconciliation Data...",
                 font=("Arial", 10, "bold")).pack(pady=(0, 10))

        ttk.Label(frame, text="Please wait while we prepare your reconciliation session.",
                 wraplength=300).pack()

        # Progress bar
        progress = ttk.Progressbar(frame, mode='indeterminate')
        progress.pack(fill=tk.X, pady=(15, 0))
        progress.start()

        # Close dialog after 2 seconds
        def close_dialog():
            dialog.destroy()

        dialog.after(2000, close_dialog)

    # Test button
    ttk.Button(root, text="Test Dialog", command=show_test_dialog).pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    test_dialog()