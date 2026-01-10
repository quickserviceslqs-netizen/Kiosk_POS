"""Utilities package for Kiosk POS."""

import tkinter as tk
import os
import sys


def set_window_icon(window: tk.Toplevel | tk.Tk) -> None:
    """Set the app's custom icon for a window (supports both .ico and .png formats).
    
    Handles PyInstaller bundles and source installations.
    Tries .ico format first, falls back to .png if needed.
    """
    try:
        # Determine icon path based on installation type
        if hasattr(sys, "_MEIPASS"):
            # PyInstaller bundle
            icon_path = os.path.join(sys._MEIPASS, "assets", "app_icon.ico")
            png_path = os.path.join(sys._MEIPASS, "assets", "logo.png")
        else:
            # Source installation
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
            png_path = os.path.join(base_dir, "assets", "logo.png")
        
        # Try ICO format first
        if os.path.exists(icon_path):
            try:
                window.iconbitmap(icon_path)
                # Also try PNG fallback for better cross-platform support
                if os.path.exists(png_path):
                    try:
                        img = tk.PhotoImage(file=png_path)
                        window.iconphoto(True, img)
                    except Exception:
                        pass
                return
            except Exception:
                pass
        
        # Fall back to PNG format
        if os.path.exists(png_path):
            try:
                img = tk.PhotoImage(file=png_path)
                window.iconphoto(True, img)
            except Exception:
                pass
    except Exception:
        pass  # Silently fail if icon cannot be set
