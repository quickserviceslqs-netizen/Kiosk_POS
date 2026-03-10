#!/usr/bin/env python3
"""Standalone Upgrade Manager Application."""

import tkinter as tk
from tkinter import ttk
from ui.upgrade_manager import UpgradeManagerFrame
from utils import set_window_icon


def main():
    # Ensure the database and schema (including upgrade_history table) exist
    from database.init_db import initialize_database
    initialize_database()

    root = tk.Tk()
    root.title("Kiosk POS - Upgrade Manager")
    root.geometry("1200x800")
    root.resizable(True, True)

    # Set the app's custom icon
    set_window_icon(root)

    # Create the upgrade manager frame
    upgrade_manager = UpgradeManagerFrame(root)
    upgrade_manager.pack(fill=tk.BOTH, expand=True)

    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()