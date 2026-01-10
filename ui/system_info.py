import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sqlite3

from database.init_db import get_default_db_path

class SystemInfoFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self._build_ui()

    def _build_ui(self):
        db_path = get_default_db_path()
        ttk.Label(self, text="System Information", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky=tk.W)
        info = ttk.Frame(self)
        info.grid(row=1, column=0, pady=(8,0), sticky=tk.NSEW)
        info.columnconfigure(1, weight=1)

        ttk.Label(info, text="Database path:").grid(row=0, column=0, sticky=tk.W, padx=(0,8))
        ttk.Label(info, text=str(db_path)).grid(row=0, column=1, sticky=tk.W)

        exists = db_path.exists()
        ttk.Label(info, text="Database exists:").grid(row=1, column=0, sticky=tk.W, padx=(0,8))
        ttk.Label(info, text=str(exists)).grid(row=1, column=1, sticky=tk.W)

        if exists:
            stats = db_path.stat()
            ttk.Label(info, text="Size (bytes):").grid(row=2, column=0, sticky=tk.W, padx=(0,8))
            ttk.Label(info, text=str(stats.st_size)).grid(row=2, column=1, sticky=tk.W)
            ttk.Label(info, text="Last modified:").grid(row=3, column=0, sticky=tk.W, padx=(0,8))
            ttk.Label(info, text=str(stats.st_mtime)).grid(row=3, column=1, sticky=tk.W)

            # Show quick DB summary
            try:
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                users = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM items")
                items = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM sales")
                sales = cur.fetchone()[0]
                conn.close()
                ttk.Label(info, text="Users:").grid(row=4, column=0, sticky=tk.W, padx=(0,8))
                ttk.Label(info, text=str(users)).grid(row=4, column=1, sticky=tk.W)
                ttk.Label(info, text="Items:").grid(row=5, column=0, sticky=tk.W, padx=(0,8))
                ttk.Label(info, text=str(items)).grid(row=5, column=1, sticky=tk.W)
                ttk.Label(info, text="Sales:").grid(row=6, column=0, sticky=tk.W, padx=(0,8))
                ttk.Label(info, text=str(sales)).grid(row=6, column=1, sticky=tk.W)
            except Exception:
                pass

        ttk.Label(self, text="\nTip: If the DB path or status looks incorrect, check installer logs or file permissions.").grid(row=10, column=0, sticky=tk.W, pady=(10,0))
