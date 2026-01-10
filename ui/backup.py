"""Backup and restore UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from modules import backup
from utils import set_window_icon


class BackupFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.grid_propagate(True)  # Allow frame to expand

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Database Backup & Restore", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="🏠 Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)

        # Controls
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, sticky=tk.EW, pady=(0, 12))
        
        ttk.Button(controls, text="📁 Create Backup", command=self._create_backup, width=20).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="↻ Restore Backup", command=self._restore_backup, width=20).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="🗑 Delete Backup", command=self._delete_backup, width=20).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="🔄 Refresh List", command=self._refresh_list, width=20).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="⚙ Auto-Backup Settings", command=self._show_auto_backup_settings, width=22).pack(side=tk.LEFT, padx=4)

        # Backup list
        list_frame = ttk.LabelFrame(self, text="Available Backups", padding=8)
        list_frame.grid(row=2, column=0, sticky=tk.NSEW)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Treeview
        columns = ("name", "size", "created")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode=tk.BROWSE, height=50)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)

        self.tree.heading("name", text="Backup Name")
        self.tree.heading("size", text="Size (MB)")
        self.tree.heading("created", text="Created")

        self.tree.column("name", width=350)
        self.tree.column("size", width=100)
        self.tree.column("created", width=150)

        # Scrollbar
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscroll=scroll.set)

        # Info label
        self.info_label = ttk.Label(self, text="", foreground="gray")
        self.info_label.grid(row=3, column=0, sticky=tk.W, pady=(8, 0))

        # Load backups
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Refresh the backup list."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load backups
        try:
            backups = backup.list_backups()
            for bak in backups:
                size_mb = bak["size"] / (1024 * 1024)
                self.tree.insert("", tk.END, values=(
                    bak["name"],
                    f"{size_mb:.2f}",
                    bak["created"]
                ), tags=(str(bak["path"]),))
            
            self.info_label.config(text=f"Total backups: {len(backups)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load backups: {e}")

    def _create_backup(self) -> None:
        """Create a new backup."""
        # Ask for custom name (optional)
        dialog = tk.Toplevel(self)
        dialog.title("Create Backup")
        set_window_icon(dialog)
        dialog.geometry("420x200+200+120")
        dialog.minsize(380, 180)
        dialog.transient(self)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)

        ttk.Label(dialog, text="Backup Name (optional):", padding=12).pack(fill=tk.X)
        name_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        entry.pack(padx=12, pady=8, fill=tk.X)
        entry.focus()

        ttk.Label(dialog, text="Leave empty for auto-generated timestamp name", 
             foreground="gray", font=("Segoe UI", 8)).pack(fill=tk.X)

        def do_backup():
            try:
                custom_name = name_var.get().strip() or None
                backup_path = backup.create_backup(custom_name)
                messagebox.showinfo("Success", f"Backup created successfully!\n\n{backup_path.name}")
                dialog.destroy()
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create backup: {e}")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="Create", width=12, command=do_backup).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", width=12, command=dialog.destroy).pack(side=tk.LEFT, padx=6)

        dialog.bind("<Return>", lambda e: do_backup())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _restore_backup(self) -> None:
        """Restore from selected backup."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a backup to restore")
            return

        item = self.tree.item(selection[0])
        backup_path = Path(item["tags"][0])
        backup_name = item["values"][0]

        # Confirm
        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"Are you sure you want to restore from this backup?\n\n"
            f"{backup_name}\n\n"
            f"⚠ WARNING: This will replace your current database!\n"
            f"A safety backup of the current database will be created automatically.",
            icon="warning"
        )

        if not confirm:
            return

        try:
            backup.restore_backup(backup_path)
            messagebox.showinfo(
                "Success",
                "Database restored successfully!\n\n"
                "Please restart the application for changes to take effect."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore backup: {e}")

    def _delete_backup(self) -> None:
        """Delete selected backup."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a backup to delete")
            return

        item = self.tree.item(selection[0])
        backup_path = Path(item["tags"][0])
        backup_name = item["values"][0]

        # Confirm
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this backup?\n\n{backup_name}\n\n"
            f"This action cannot be undone!",
            icon="warning"
        )

        if not confirm:
            return

        try:
            backup.delete_backup(backup_path)
            messagebox.showinfo("Success", f"Backup deleted: {backup_name}")
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete backup: {e}")

    def _show_auto_backup_settings(self) -> None:
        """Show auto-backup settings dialog."""
        dialog = tk.Toplevel(self)
        dialog.title("Auto-Backup Settings")
        set_window_icon(dialog)
        dialog.geometry("520x360+220+140")
        dialog.minsize(480, 320)
        dialog.transient(self)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)

        # Load current config
        config = backup.get_backup_config()

        ttk.Label(dialog, text="Automatic Backup Settings", 
             font=("Segoe UI", 12, "bold"), padding=12).pack(fill=tk.X)

        # Enabled checkbox
        frame1 = ttk.Frame(dialog, padding=12)
        frame1.pack(fill=tk.X)
        enabled_var = tk.BooleanVar(value=config["auto_backup_enabled"])
        ttk.Checkbutton(frame1, text="Enable automatic backups", 
                       variable=enabled_var).pack(anchor=tk.W)

        # Interval
        frame2 = ttk.Frame(dialog, padding=12)
        frame2.pack(fill=tk.X)
        ttk.Label(frame2, text="Backup interval (hours):").pack(side=tk.LEFT)
        interval_var = tk.IntVar(value=config["backup_interval_hours"])
        ttk.Spinbox(frame2, from_=1, to=168, textvariable=interval_var, width=10).pack(side=tk.LEFT, padx=8)

        # Max backups
        frame3 = ttk.Frame(dialog, padding=12)
        frame3.pack(fill=tk.X)
        ttk.Label(frame3, text="Maximum auto-backups to keep:").pack(side=tk.LEFT)
        max_var = tk.IntVar(value=config["max_backups_to_keep"])
        ttk.Spinbox(frame3, from_=1, to=100, textvariable=max_var, width=10).pack(side=tk.LEFT, padx=8)

        # Last backup info
        frame4 = ttk.Frame(dialog, padding=12)
        frame4.pack(fill=tk.X)
        last_backup = config.get("last_auto_backup")
        if last_backup:
            from datetime import datetime
            last_time = datetime.fromisoformat(last_backup).strftime("%Y-%m-%d %H:%M:%S")
            ttk.Label(frame4, text=f"Last auto-backup: {last_time}", 
                     foreground="gray").pack()
        else:
            ttk.Label(frame4, text="No auto-backups created yet", 
                     foreground="gray").pack()

        def save_settings():
            config["auto_backup_enabled"] = enabled_var.get()
            config["backup_interval_hours"] = interval_var.get()
            config["max_backups_to_keep"] = max_var.get()
            backup.save_backup_config(config)
            messagebox.showinfo("Success", "Auto-backup settings saved!")
            dialog.destroy()

        # Buttons
        btn_frame = ttk.Frame(dialog, padding=12)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Save", width=12, command=save_settings).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", width=12, command=dialog.destroy).pack(side=tk.LEFT, padx=6)

