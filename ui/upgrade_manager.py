"""A simple Tkinter-based Upgrade Manager UI.

This is a minimal admin screen to select an upgrade package, preview steps,
perform a dry-run, and apply the upgrade while showing logs.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional

from modules import upgrades


class UpgradeManager(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Upgrade Manager")
        self.geometry("700x480")
        self.pkg_path: Optional[Path] = None
        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        row = 0
        ttk.Button(frm, text="Choose package...", command=self.choose_package).grid(column=0, row=row, sticky=tk.W)
        self.pkg_label = ttk.Label(frm, text="No package selected")
        self.pkg_label.grid(column=1, row=row, sticky=tk.W)

        row += 1
        ttk.Button(frm, text="Preview", command=self.preview).grid(column=0, row=row, sticky=tk.W)
        ttk.Button(frm, text="Dry run", command=self.dry_run).grid(column=1, row=row, sticky=tk.W)
        ttk.Button(frm, text="Apply", command=self.apply).grid(column=2, row=row, sticky=tk.W)

        row += 1
        self.log = tk.Text(frm, height=20, wrap=tk.NONE)
        self.log.grid(column=0, row=row, columnspan=3, sticky=tk.NSEW)

        # Make grid expand
        frm.rowconfigure(row, weight=1)
        frm.columnconfigure(2, weight=1)

    def choose_package(self):
        p = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if p:
            self.pkg_path = Path(p)
            self.pkg_label.config(text=str(self.pkg_path))
            self._append_log(f"Selected package: {p}")

    def _append_log(self, msg: str):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def preview(self):
        if not self.pkg_path:
            messagebox.showwarning("No package", "Choose an upgrade package first")
            return
        try:
            steps = upgrades.preview_package(str(self.pkg_path))
            self._append_log(f"Manifest steps ({len(steps)}):")
            for i, s in enumerate(steps, 1):
                self._append_log(f"{i}. {s}")
        except Exception as e:
            self._append_log(f"Preview failed: {e}")

    def dry_run(self):
        if not self.pkg_path:
            messagebox.showwarning("No package", "Choose an upgrade package first")
            return
        res = upgrades.apply_package(str(self.pkg_path), dry_run=True, backup_db=True)
        for l in res.get('logs', []):
            self._append_log(l)
        self._append_log(f"DRY RUN success: {res.get('success')}")

    def apply(self):
        if not self.pkg_path:
            messagebox.showwarning("No package", "Choose an upgrade package first")
            return
        if not messagebox.askokcancel("Confirm Apply", "Applying an upgrade may change the database and files. Proceed?"):
            return
        res = upgrades.apply_package(str(self.pkg_path), dry_run=False, backup_db=True)
        for l in res.get('logs', []):
            self._append_log(l)
        self._append_log(f"APPLY success: {res.get('success')}")


if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    dlg = UpgradeManager(root)
    root.mainloop()
