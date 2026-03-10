"""Enhanced Upgrade Manager UI with comprehensive features.

Includes:
- Cancellation support
- Security verification
- Progress tracking with cancellation
- Upgrade history viewing
- Rollback capabilities
- Dependency checking
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime

from modules import upgrades
from utils import set_window_icon
from utils.date_utils import format_date


def _get_status_color(status: str) -> str:
    """Get theme status color with safe fallback."""
    try:
        from utils.theme import get_status_color
        return get_status_color(status)
    except Exception:
        fallbacks = {
            'danger': '#ef4444', 'success': '#10b981', 'warning': '#f59e0b',
            'info': '#3b82f6', 'text_light': '#9ca3af'
        }
        return fallbacks.get(status, '#000000')


class StatusDialog(tk.Toplevel):
    """Status dialog for upgrade operations."""

    def __init__(self, parent, title="Operation Status", operation_type="Operation"):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.operation_type = operation_type
        self.success = None
        self.cancelled = False  # Track cancellation state

        # Set the app's custom icon
        set_window_icon(self)

        # Center the dialog
        self._center_dialog()

        # Build UI
        self._build_ui()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Ensure dialog is visible
        self.deiconify()
        self.lift()
        self.focus_force()
        self.update()

    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.update_idletasks()
        parent = self.master
        if parent:
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            dialog_width = self.winfo_width()
            dialog_height = self.winfo_height()

            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2

            self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Build the dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text=f"{self.operation_type} in Progress",
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 20))

        # Status label
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                     font=("Segoe UI", 10))
        self.status_label.pack(pady=(0, 10))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var,
                                           maximum=100, mode='determinate', length=400,
                                           style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(pady=(0, 20))

        # Current operation
        operation_frame = ttk.LabelFrame(main_frame, text="Current Operation", padding=10)
        operation_frame.pack(fill=tk.X, pady=(0, 20))

        self.operation_var = tk.StringVar(value="Preparing...")
        operation_label = ttk.Label(operation_frame, textvariable=self.operation_var,
                                   font=("Segoe UI", 9))
        operation_label.pack(anchor=tk.W)

        # Log area (compact)
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD,
                                                 font=("Consolas", 8))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=(10, 0))

        self.close_button = ttk.Button(button_frame, text="Close", command=self._on_close, state=tk.DISABLED)
        self.close_button.pack(side=tk.RIGHT)

    def update_status(self, message: str, progress: float = None):
        """Update the status message and progress."""
        self.status_var.set(message)
        if progress is not None:
            self.progress_var.set(progress)
        self.update_idletasks()

    def update_operation(self, operation: str):
        """Update the current operation."""
        self.operation_var.set(operation)
        self.update_idletasks()

    def add_log(self, message: str):
        """Add a message to the log."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.update_idletasks()

    def set_success(self, success: bool, message: str = None):
        """Set the final status."""
        self.success = success
        if success:
            self.status_var.set(message or f"{self.operation_type} completed successfully")
            self.progress_var.set(100)
            self.title(f"{self.operation_type} - Success")
        else:
            self.status_var.set(message or f"{self.operation_type} failed")
            self.title(f"{self.operation_type} - Failed")

        # Enable close button, disable cancel
        self.close_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.update_idletasks()

    def _cancel(self):
        """Cancel the operation."""
        if messagebox.askyesno("Cancel Operation", f"Are you sure you want to cancel the {self.operation_type.lower()}?"):
            self.status_var.set("Cancelling...")
            self.cancelled = True

    def _on_close(self):
        """Handle dialog close."""
        if self.success is None:  # Still running
            if messagebox.askyesno("Close Dialog", f"The {self.operation_type.lower()} is still running. Close anyway?"):
                self.destroy()
        else:
            self.destroy()


class UpgradeManagerFrame(ttk.Frame):
    """Enhanced upgrade manager with full feature set."""

    # Recent packages file
    RECENT_PACKAGES_FILE = "upgrade_recent.json"
    MAX_RECENT_PACKAGES = 5

    def __init__(self, master=None, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.pkg_path: Optional[Path] = None
        self.current_operation = None
        self.cancellation_token = threading.Event()
        self.signing_key: Optional[str] = None
        self.status_dialog: Optional[StatusDialog] = None
        self.package_info: Optional[Dict[str, Any]] = None
        self.recent_packages: list = []
        
        # Load recent packages
        self._load_recent_packages()
        
        # Setup custom styles
        self._setup_styles()
        
        self._build_ui()
        
        # Bind keyboard shortcuts
        self._bind_shortcuts()

    def _setup_styles(self):
        """Setup custom styles for the UI."""
        style = ttk.Style()
        try:
            from utils.theme import get_theme_colors
            _tc = get_theme_colors()
            _trough = _tc.get('background', '#f5f5f5')
            _success = _tc.get('success', '#10b981')
        except Exception:
            _trough = '#f5f5f5'
            _success = '#10b981'
        
        # Create a custom style for green progress bar
        style.configure("Green.Horizontal.TProgressbar",
                       troughcolor=_trough,
                       borderwidth=1,
                       lightcolor=_success,
                       darkcolor=_success,
                       bordercolor=_success,
                       background=_success)
        
        # This makes the progress bar fill green
        style.map("Green.Horizontal.TProgressbar",
                 background=[('active', _success)],
                 lightcolor=[('active', _success)],
                 darkcolor=[('active', _success)])

    def _build_ui(self):
        # Main notebook for different tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Upgrade tab
        upgrade_frame = ttk.Frame(self.notebook)
        self.notebook.add(upgrade_frame, text="Apply Upgrade")
        self._build_upgrade_tab(upgrade_frame)

        # History tab
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="Upgrade History")
        self._build_history_tab(history_frame)

        # Settings tab
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        self._build_settings_tab(settings_frame)

    def _build_upgrade_tab(self, parent):
        """Build the main upgrade application tab."""
        # Title with keyboard shortcut hint
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 12))
        
        ttk.Label(title_frame, text="System Upgrade Manager", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="Ctrl+O: Open | Ctrl+D: Dry Run | Ctrl+Enter: Apply", 
                 font=("Segoe UI", 8), foreground=_get_status_color("text_light")).pack(side=tk.RIGHT)

        # Package selection frame with recent packages
        pkg_frame = ttk.LabelFrame(parent, text="Upgrade Package", padding=10)
        pkg_frame.pack(fill=tk.X, pady=(0, 12))

        # Recent packages dropdown
        recent_frame = ttk.Frame(pkg_frame)
        recent_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(recent_frame, text="Recent:").pack(side=tk.LEFT)
        self.recent_combo = ttk.Combobox(recent_frame, state="readonly", width=50)
        self.recent_combo.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        self.recent_combo.bind("<<ComboboxSelected>>", self._on_recent_selected)
        self._update_recent_combo()

        # Current package display
        current_frame = ttk.Frame(pkg_frame)
        current_frame.pack(fill=tk.X)
        
        self.pkg_label = ttk.Label(current_frame, text="No package selected", foreground=_get_status_color("text_light"))
        self.pkg_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_frame = ttk.Frame(current_frame)
        btn_frame.pack(side=tk.RIGHT)

        self.select_btn = ttk.Button(btn_frame, text="📁 Browse...", command=self.choose_package, width=12)
        self.select_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.clear_btn = ttk.Button(btn_frame, text="✕", command=self._clear_package, width=3, state=tk.DISABLED)
        self.clear_btn.pack(side=tk.LEFT)

        # Package info panel (shows details after selection)
        self.info_frame = ttk.LabelFrame(parent, text="Package Information", padding=10)
        self.info_frame.pack(fill=tk.X, pady=(0, 12))
        
        # Info grid
        info_grid = ttk.Frame(self.info_frame)
        info_grid.pack(fill=tk.X)
        
        self.info_labels = {}
        info_fields = [("Version:", "version"), ("Description:", "description"), 
                       ("Steps:", "steps"), ("Status:", "status")]
        for i, (label, key) in enumerate(info_fields):
            ttk.Label(info_grid, text=label, font=("Segoe UI", 9, "bold")).grid(row=i, column=0, sticky=tk.W, pady=2)
            self.info_labels[key] = ttk.Label(info_grid, text="-", foreground=_get_status_color("text_light"))
            self.info_labels[key].grid(row=i, column=1, sticky=tk.W, padx=(8, 0), pady=2)
        
        info_grid.columnconfigure(1, weight=1)

        # Quick action buttons (more prominent)
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(0, 12))

        self.dry_run_btn = ttk.Button(action_frame, text="🔍 Validate & Dry Run (Ctrl+D)", 
                                      command=self.dry_run, state=tk.DISABLED, width=25)
        self.dry_run_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.apply_btn = ttk.Button(action_frame, text="⚡ Apply Upgrade (Ctrl+Enter)", 
                                    command=self.apply, state=tk.DISABLED, width=25)
        self.apply_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.cancel_btn = ttk.Button(action_frame, text="⏹️ Cancel", 
                                     command=self.cancel_operation, state=tk.DISABLED, width=12)
        self.cancel_btn.pack(side=tk.LEFT)

        # Progress frame (more compact)
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=8)
        progress_frame.pack(fill=tk.X, pady=(0, 12))

        progress_inner = ttk.Frame(progress_frame)
        progress_inner.pack(fill=tk.X)
        
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(progress_inner, textvariable=self.progress_var, width=50, anchor=tk.W)
        self.progress_label.pack(side=tk.LEFT)
        
        self.step_label = ttk.Label(progress_inner, text="", foreground=_get_status_color("text_light"))
        self.step_label.pack(side=tk.RIGHT)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', maximum=100,
                                     style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))

        # Log frame (collapsible style)
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD,
                                                 font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        control_frame = ttk.Frame(log_frame)
        control_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(control_frame, text="🗑️ Clear", command=self.clear_log, width=10).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(control_frame, text="💾 Save", command=self.save_log, width=10).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(control_frame, text="📋 Copy", command=self._copy_log, width=10).pack(side=tk.LEFT)

    def _build_history_tab(self, parent):
        """Build the upgrade history tab."""
        # Title
        title = ttk.Label(parent, text="Upgrade History", font=("Segoe UI", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 16))

        # Buttons at the top
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(btn_frame, text="🔄 Refresh", command=self.load_history).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="📋 View Details", command=self.view_history_details).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="↶ Rollback", command=self.rollback_upgrade).pack(side=tk.LEFT)

        # Use a paned window for history tree and details
        paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # History tree frame
        tree_frame = ttk.Frame(paned)
        paned.add(tree_frame, weight=1)

        columns = ("ID", "Version", "Applied At", "Success", "Description")
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)

        # Set column widths and properties for auto-fitting
        column_config = {
            "ID": {"width": 80, "minwidth": 60, "stretch": False},
            "Version": {"width": 120, "minwidth": 100, "stretch": False},
            "Applied At": {"width": 180, "minwidth": 150, "stretch": True},
            "Success": {"width": 100, "minwidth": 80, "stretch": False},
            "Description": {"width": 400, "minwidth": 200, "stretch": True}
        }

        for col in columns:
            config = column_config.get(col, {"width": 120, "minwidth": 80, "stretch": False})
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=config["width"], minwidth=config["minwidth"], stretch=config["stretch"])

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Details text area
        details_frame = ttk.LabelFrame(paned, text="Upgrade Details", padding=10)
        paned.add(details_frame, weight=1)

        self.details_text = scrolledtext.ScrolledText(details_frame, height=8, wrap=tk.WORD,
                                                     font=("Consolas", 9))
        self.details_text.pack(fill=tk.BOTH, expand=True)

        # Load initial history
        self.load_history()

    def _build_settings_tab(self, parent):
        """Build the settings tab with a scrollable canvas so all sections are reachable."""
        # ── Scrollable wrapper ────────────────────────────────────────────
        canvas = tk.Canvas(parent, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e):
            canvas.itemconfig(inner_id, width=e.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Use inner instead of parent for all content below
        parent = inner

        # Title
        title = ttk.Label(parent, text="Upgrade Settings", font=("Segoe UI", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 16), padx=10)

        # Backup settings (more prominent)
        backup_frame = ttk.LabelFrame(parent, text="Backup Settings", padding=10)
        backup_frame.pack(fill=tk.X, pady=(0, 12), padx=10)

        self.backup_db_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(backup_frame, text="Backup database before upgrade",
                       variable=self.backup_db_var).pack(anchor=tk.W)

        self.keep_backups_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(backup_frame, text="Keep backup files after successful upgrade",
                       variable=self.keep_backups_var).pack(anchor=tk.W)
        
        # Backup management buttons
        backup_btn_frame = ttk.Frame(backup_frame)
        backup_btn_frame.pack(fill=tk.X, pady=(8, 0))
        
        ttk.Button(backup_btn_frame, text="📂 View Backups", 
              command=self._view_backups).pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        ttk.Button(backup_btn_frame, text="🗑️ Cleanup Old Backups", 
              command=self._cleanup_backups).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Maintenance section
        maint_frame = ttk.LabelFrame(parent, text="Maintenance", padding=10)
        maint_frame.pack(fill=tk.X, pady=(0, 12), padx=10)

        maint_btn_frame = ttk.Frame(maint_frame)
        maint_btn_frame.pack(fill=tk.X)
        ttk.Button(maint_btn_frame, text="🗑️ Clear Recent Packages",
              command=self._clear_recent).pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        ttk.Button(maint_btn_frame, text="📋 Clear Upgrade History",
              command=self._clear_history).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── Automatic Update Check ────────────────────────────────────────
        upd_frame = ttk.LabelFrame(parent, text="🔔 Automatic Update Check", padding=10)
        upd_frame.pack(fill=tk.X, pady=(0, 12), padx=10)

        ttk.Label(upd_frame,
                  text="The app can silently check a URL on login and show a notification\n"
                       "when a newer version is available for download.",
                  font=("Segoe UI", 9), wraplength=520, justify=tk.LEFT
                  ).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))

        self._auto_check_var = tk.BooleanVar()
        ttk.Checkbutton(upd_frame,
                        text="Automatically check for updates on login",
                        variable=self._auto_check_var).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))

        ttk.Label(upd_frame, text="Update manifest URL:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self._update_url_entry = ttk.Entry(upd_frame, width=44)
        self._update_url_entry.grid(row=2, column=1, sticky=tk.EW, padx=(8, 4), pady=2)

        ttk.Button(upd_frame, text="💾 Save",
                   command=self._save_update_check_settings, width=8).grid(
            row=2, column=2, sticky=tk.W, pady=2)

        btn_row = ttk.Frame(upd_frame)
        btn_row.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))
        ttk.Button(btn_row, text="🔍 Check Now",
                   command=self._manual_update_check).pack(side=tk.LEFT, padx=(0, 8))

        self._update_status_var = tk.StringVar(value="")
        ttk.Label(btn_row, textvariable=self._update_status_var,
                  font=("Segoe UI", 9)).pack(side=tk.LEFT)

        upd_frame.columnconfigure(1, weight=1)

        # Load current values from DB
        self._load_update_check_settings()

    # ── Update-check helpers ──────────────────────────────────────────────

    def _load_update_check_settings(self) -> None:
        """Populate URL entry and auto-check checkbox from DB."""
        try:
            from modules.update_check import get_update_check_url, get_auto_check_enabled
            self._update_url_entry.delete(0, tk.END)
            self._update_url_entry.insert(0, get_update_check_url())
            self._auto_check_var.set(get_auto_check_enabled())
        except Exception:
            pass

    def _save_update_check_settings(self) -> None:
        """Persist URL + auto-check flag to DB."""
        try:
            from modules.update_check import set_update_check_url, set_auto_check_enabled
            url = self._update_url_entry.get().strip()
            set_update_check_url(url)
            set_auto_check_enabled(self._auto_check_var.get())
            self._update_status_var.set("✅ Saved")
            self.after(3000, lambda: self._update_status_var.set(""))
            self._append_log(f"Update check URL saved: {url or '(disabled)'}")
        except Exception as e:
            self._update_status_var.set(f"❌ {e}")

    def _manual_update_check(self) -> None:
        """Trigger an immediate update check and report the result in the UI."""
        from modules.update_check import check_for_updates, get_update_check_url
        import main as _main

        url = self._update_url_entry.get().strip() or get_update_check_url()
        if not url:
            self._update_status_var.set("⚠ No URL configured")
            return

        self._update_status_var.set("⏳ Checking…")
        self._append_log(f"Checking for updates at: {url}")

        def _on_result(info):
            def _show():
                if info:
                    v = info.get("version", "?")
                    self._update_status_var.set(f"⬆ Version {v} available!")
                    self._append_log(f"⬆ Update available: v{v}")
                    # If the shell is accessible, show the badge
                    root = self.winfo_toplevel()
                    shell = getattr(root, "shell", None)
                    if shell and hasattr(shell, "show_update_notification"):
                        shell.show_update_notification(info, lambda: _open_upgrade_mgr(root))
                else:
                    self._update_status_var.set("✅ Already up to date")
                    self._append_log("✅ Already up to date")
            self.after(0, _show)

        def _open_upgrade_mgr(root):
            try:
                _main.show_upgrade_manager(root)
            except Exception:
                pass

        check_for_updates(_main.APP_VERSION, url, _on_result)

    def choose_package(self):
        """Select an upgrade package file."""
        filename = filedialog.askopenfilename(
            title="Select Upgrade Package",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if filename:
            self._set_package(Path(filename))

    def _set_package(self, pkg_path: Path):
        """Set the current package and auto-validate."""
        self.pkg_path = pkg_path
        self.pkg_label.config(text=f"📦 {self.pkg_path.name}", foreground="")
        self._append_log(f"Selected package: {self.pkg_path}")

        # Enable buttons
        self.dry_run_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.NORMAL)
        
        # Add to recent packages
        self._add_to_recent(str(self.pkg_path))

        # Auto-validate and show package info
        self._auto_validate_package()

    def _auto_validate_package(self):
        """Auto-validate package and show info."""
        if not self.pkg_path:
            return
            
        def validate():
            try:
                # Quick validation
                manifest = upgrades.validate_package(str(self.pkg_path))
                self.package_info = manifest
                
                # Update info panel on main thread
                self.after(0, lambda: self._update_package_info(manifest, valid=True))
                
            except Exception as e:
                self.after(0, lambda: self._update_package_info(None, valid=False, error=str(e)))
        
        # Run validation in background
        threading.Thread(target=validate, daemon=True).start()

    def _update_package_info(self, manifest: Optional[Dict], valid: bool, error: str = None):
        """Update the package info panel."""
        if valid and manifest:
            self.info_labels["version"].config(text=manifest.get("version", "Unknown"), foreground="")
            self.info_labels["description"].config(text=manifest.get("description", "No description")[:80], foreground="")
            
            steps = manifest.get("steps", [])
            step_types = [s.get("type", "?") for s in steps]
            step_summary = f"{len(steps)} steps: {', '.join(step_types)}"
            self.info_labels["steps"].config(text=step_summary, foreground="")
            
            self.info_labels["status"].config(text="✓ Valid package", foreground=_get_status_color("success"))
            self._append_log(f"✓ Package validated: v{manifest.get('version')}, {len(steps)} steps")
        else:
            self.info_labels["version"].config(text="-", foreground=_get_status_color("text_light"))
            self.info_labels["description"].config(text="-", foreground=_get_status_color("text_light"))
            self.info_labels["steps"].config(text="-", foreground=_get_status_color("text_light"))
            self.info_labels["status"].config(text=f"✗ {error or 'Invalid'}", foreground=_get_status_color("danger"))
            self._append_log(f"✗ Validation failed: {error}")

    def _clear_package(self):
        """Clear the current package selection."""
        self.pkg_path = None
        self.package_info = None
        self.pkg_label.config(text="No package selected", foreground=_get_status_color("text_light"))
        
        # Disable buttons
        self.dry_run_btn.config(state=tk.DISABLED)
        self.apply_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.DISABLED)
        
        # Clear info panel
        for label in self.info_labels.values():
            label.config(text="-", foreground=_get_status_color("text_light"))
        
        self._append_log("Package selection cleared")

    def _on_recent_selected(self, event):
        """Handle recent package selection."""
        selection = self.recent_combo.get()
        if selection and Path(selection).exists():
            self._set_package(Path(selection))
        elif selection:
            messagebox.showwarning("File Not Found", f"Package file no longer exists:\n{selection}")
            self._remove_from_recent(selection)

    def _load_recent_packages(self):
        """Load recent packages from file."""
        try:
            recent_file = Path(__file__).parent.parent / "database" / self.RECENT_PACKAGES_FILE
            if recent_file.exists():
                with open(recent_file, 'r') as f:
                    self.recent_packages = json.load(f)
        except Exception:
            self.recent_packages = []

    def _save_recent_packages(self):
        """Save recent packages to file."""
        try:
            recent_file = Path(__file__).parent.parent / "database" / self.RECENT_PACKAGES_FILE
            with open(recent_file, 'w') as f:
                json.dump(self.recent_packages, f)
        except Exception:
            pass

    def _add_to_recent(self, path: str):
        """Add a package to recent list."""
        if path in self.recent_packages:
            self.recent_packages.remove(path)
        self.recent_packages.insert(0, path)
        self.recent_packages = self.recent_packages[:self.MAX_RECENT_PACKAGES]
        self._save_recent_packages()
        self._update_recent_combo()

    def _remove_from_recent(self, path: str):
        """Remove a package from recent list."""
        if path in self.recent_packages:
            self.recent_packages.remove(path)
            self._save_recent_packages()
            self._update_recent_combo()

    def _update_recent_combo(self):
        """Update the recent packages combobox."""
        if hasattr(self, 'recent_combo'):
            self.recent_combo['values'] = self.recent_packages if self.recent_packages else ["(No recent packages)"]
            if self.recent_packages:
                self.recent_combo.set("")
            else:
                self.recent_combo.set("(No recent packages)")

    def _clear_recent(self):
        """Clear recent packages list."""
        if messagebox.askyesno("Clear Recent", "Clear all recent packages?"):
            self.recent_packages = []
            self._save_recent_packages()
            self._update_recent_combo()
            self._append_log("Recent packages cleared")

    def _copy_log(self):
        """Copy log to clipboard."""
        log_content = self.log_text.get(1.0, tk.END)
        self.clipboard_clear()
        self.clipboard_append(log_content)
        self._append_log("Log copied to clipboard")

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        # Get the toplevel window
        top = self.winfo_toplevel()
        top.bind("<Control-o>", lambda e: self.choose_package())
        top.bind("<Control-d>", lambda e: self._shortcut_dry_run())
        top.bind("<Control-Return>", lambda e: self._shortcut_apply())

    def _shortcut_dry_run(self):
        """Keyboard shortcut for dry run."""
        if self.pkg_path and str(self.dry_run_btn['state']) != 'disabled':
            self.dry_run()

    def _shortcut_apply(self):
        """Keyboard shortcut for apply."""
        if self.pkg_path and str(self.apply_btn['state']) != 'disabled':
            self.apply()

    def _view_backups(self):
        """View backup files."""
        import tempfile
        backup_dir = Path(tempfile.gettempdir())
        backup_dirs = list(backup_dir.glob("upgrade_backup_*"))
        
        if not backup_dirs:
            messagebox.showinfo("Backups", "No backup directories found.")
            return
        
        # Show backup info
        info = "Backup directories found:\n\n"
        total_size = 0
        for bd in sorted(backup_dirs, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            size = sum(f.stat().st_size for f in bd.rglob("*") if f.is_file()) / 1024 / 1024
            total_size += size
            mtime = f"{format_date(datetime.fromtimestamp(bd.stat().st_mtime))} {datetime.fromtimestamp(bd.stat().st_mtime).strftime('%H:%M')}"
            info += f"• {bd.name} ({size:.1f} MB) - {mtime}\n"
        
        info += f"\nTotal: {len(backup_dirs)} directories, {total_size:.1f} MB"
        messagebox.showinfo("Backup Directories", info)

    def _cleanup_backups(self):
        """Clean up old backup directories."""
        import tempfile
        backup_dir = Path(tempfile.gettempdir())
        backup_dirs = list(backup_dir.glob("upgrade_backup_*"))
        
        if not backup_dirs:
            messagebox.showinfo("Cleanup", "No backup directories to clean up.")
            return
        
        if messagebox.askyesno("Cleanup Backups", 
                              f"Delete {len(backup_dirs)} backup directories?\n\n"
                              "Warning: This cannot be undone. You will lose the ability to manually restore from these backups."):
            deleted = 0
            for bd in backup_dirs:
                try:
                    import shutil
                    shutil.rmtree(bd)
                    deleted += 1
                except Exception:
                    pass
            
            self._append_log(f"Cleaned up {deleted} backup directories")
            messagebox.showinfo("Cleanup Complete", f"Deleted {deleted} backup directories.")

    def _clear_history(self):
        """Clear upgrade history from the database."""
        if messagebox.askyesno("Clear History",
                              "Clear all upgrade history?\n\nWarning: This will remove all records of applied upgrades."):
            try:
                from database.init_db import get_connection, get_default_db_path
                conn = get_connection(get_default_db_path())
                conn.execute("DELETE FROM upgrade_history")
                conn.commit()
                conn.close()
                self.load_history()
                self._append_log("Upgrade history cleared")
                messagebox.showinfo("Success", "Upgrade history cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history:\n{str(e)}")

    def dry_run(self):
        """Perform a dry run of the upgrade."""
        self._append_log("🔍 Starting dry run...")
        self.progress_var.set("Starting dry run...")

        # Create status dialog
        self.status_dialog = StatusDialog(self, "Dry Run", "Dry Run")

        # Ensure dialog is fully visible before starting background work
        self.status_dialog.update()
        self.update()

        self._run_upgrade(dry_run=True)

    def apply(self):
        """Apply the upgrade."""
        # Warn loudly if the package contains command steps (arbitrary shell execution)
        if self.package_info:
            cmd_steps = [s for s in self.package_info.get("steps", []) if s.get("type") == "command"]
            if cmd_steps:
                cmds = "\n".join(f"  \u2022 {s.get('cmd', '?')}" for s in cmd_steps)
                if not messagebox.askyesno(
                    "\u26a0\ufe0f Security Warning \u2014 Shell Commands Detected",
                    f"This package contains {len(cmd_steps)} shell command step(s) that will run "
                    f"on your system:\n\n{cmds}\n\n"
                    "Shell commands execute arbitrary code. Only proceed if you absolutely "
                    "trust the source of this package.\n\nContinue with upgrade?",
                    icon="warning"
                ):
                    return

        if messagebox.askyesno("Confirm Upgrade",
                              "Are you sure you want to apply this upgrade?\n\n"
                              "This will modify your system and database."):
            # Create status dialog
            self.status_dialog = StatusDialog(self, "System Upgrade", "Upgrade")

            # Ensure dialog is fully visible before starting background work
            self.status_dialog.update()
            self.update()

            self._run_upgrade(dry_run=False)

    def cancel_operation(self):
        """Cancel the current operation."""
        if self.current_operation and self.current_operation.is_alive():
            self.cancellation_token.set()
            self.cancel_btn.config(state=tk.DISABLED)
            self._append_log("Cancellation requested...")

    def _run_upgrade(self, dry_run: bool = False):
        """Run the upgrade in a background thread."""
        if not self.pkg_path:
            return

        # Reset cancellation token
        self.cancellation_token.clear()

        # Disable buttons
        self.select_btn.config(state=tk.DISABLED)
        self.dry_run_btn.config(state=tk.DISABLED)
        self.apply_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

        # Clear progress
        self.progress_bar.config(value=0)
        self.progress_var.set("Starting...")

        # Run in background thread
        def run_upgrade():
            try:
                result = upgrades.apply_package(
                    str(self.pkg_path),
                    dry_run=dry_run,
                    backup_db=self.backup_db_var.get(),
                    progress_callback=self._update_progress,
                    cancellation_token=self.cancellation_token,
                    signature=None,
                    signing_key=None
                )

                # Update UI on completion
                self.after(0, lambda: self._upgrade_completed(result))

            except Exception as e:
                self.after(0, lambda: self._upgrade_error(str(e)))

        self.current_operation = threading.Thread(target=run_upgrade, daemon=True)
        self.current_operation.start()

    def _update_progress(self, message: str, percentage: float):
        """Update progress from background thread."""
        def update():
            self.progress_var.set(message)
            self.progress_bar.config(value=percentage)
            
            # Update step label with percentage
            if hasattr(self, 'step_label'):
                self.step_label.config(text=f"{percentage:.0f}%")

            # Also update status dialog if it exists
            if self.status_dialog:
                self.status_dialog.update_status(message, percentage)
                self.status_dialog.update_operation(message)
                self.status_dialog.add_log(f"[{percentage:.0f}%] {message}")

        self.after(0, update)

    def _upgrade_completed(self, result: Dict[str, Any]):
        """Handle upgrade completion."""
        # Re-enable buttons
        self.select_btn.config(state=tk.NORMAL)
        self.dry_run_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.step_label.config(text="")

        # Update progress
        self.progress_var.set("Completed")
        self.progress_bar.config(value=100)

        # Log results to main UI
        for log_entry in result.get("logs", []):
            self._append_log(log_entry)

        # Update status dialog
        if self.status_dialog:
            # Add logs to dialog
            for log_entry in result.get("logs", []):
                self.status_dialog.add_log(log_entry)

            if result.get("success"):
                if result.get("dry_run", False):
                    success_msg = "Dry run completed successfully"
                    self._append_log("✅ DRY_RUN SUCCEEDED")
                    self.progress_var.set("Dry run completed successfully")
                    self.status_dialog.set_success(True, success_msg)
                    messagebox.showinfo("Dry Run Success", "Dry run completed successfully!\n\nThe upgrade package is valid and ready to apply.")
                else:
                    success_msg = "Upgrade completed successfully"
                    self._append_log("✅ UPGRADE APPLIED SUCCESSFULLY")
                    self.progress_var.set("Upgrade completed successfully")
                    self.status_dialog.set_success(True, success_msg)
                    messagebox.showinfo("Success", "Upgrade completed successfully!")
                    self.load_history()  # Refresh history
                    # Prompt user to restart — newly copied/patched modules are live only after restart
                    messagebox.showwarning(
                        "Restart Required",
                        "The upgrade has been applied.\n\n"
                        "Please restart the application for all changes to take full effect."
                    )
            else:
                if result.get("dry_run", False):
                    self._append_log("❌ DRY_RUN FAILED")
                    self.progress_var.set("Dry run failed")
                    self.status_dialog.set_success(False, "Dry run failed")
                else:
                    self._append_log("❌ UPGRADE FAILED")
                    self.progress_var.set("Upgrade failed")
                    self.status_dialog.set_success(False, "Upgrade failed")

                errors = result.get("errors", [])
                if errors:
                    error_text = "\n".join(errors)
                    messagebox.showerror("Upgrade Failed", f"Upgrade failed:\n\n{error_text}")
                else:
                    messagebox.showerror("Upgrade Failed", "Upgrade failed with unknown error")

    def _upgrade_error(self, error: str):
        """Handle upgrade error."""
        # Re-enable buttons
        self.select_btn.config(state=tk.NORMAL)
        self.dry_run_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)

        self.progress_var.set("Operation failed")
        self._append_log(f"❌ OPERATION FAILED: {error}")

        # Update status dialog if it exists
        if self.status_dialog:
            self.status_dialog.add_log(f"❌ OPERATION FAILED: {error}")
            self.status_dialog.set_success(False, "Operation failed")

        messagebox.showerror("Error", f"Operation failed:\n\n{error}")

    def _rollback_completed(self, result: Dict[str, Any]):
        """Handle rollback completion."""
        # Update progress
        self.progress_var.set("Completed")
        self.progress_bar.config(value=100)

        # Log results to main UI
        for log_entry in result.get("logs", []):
            self._append_log(log_entry)

        # Update status dialog
        if self.status_dialog:
            # Add logs to dialog
            for log_entry in result.get("logs", []):
                self.status_dialog.add_log(log_entry)

            if result.get("success"):
                success_msg = "Rollback completed successfully"
                self._append_log("✅ ROLLBACK COMPLETED SUCCESSFULLY")
                self.progress_var.set("Rollback completed successfully")
                self.status_dialog.set_success(True, success_msg)
                messagebox.showinfo("Success", "Rollback completed successfully!")
                self.load_history()  # Refresh history
            else:
                self._append_log("❌ ROLLBACK FAILED")
                self.progress_var.set("Rollback failed")
                self.status_dialog.set_success(False, "Rollback failed")

                errors = result.get("logs", [])
                if errors:
                    error_text = "\n".join(errors)
                    messagebox.showerror("Rollback Failed", f"Rollback failed:\n\n{error_text}")
                else:
                    messagebox.showerror("Rollback Failed", "Rollback failed with unknown error")

    def _rollback_error(self, error: str):
        """Handle rollback error."""
        self.progress_var.set("Rollback failed")
        self._append_log(f"❌ ROLLBACK FAILED: {error}")

        # Update status dialog if it exists
        if self.status_dialog:
            self.status_dialog.add_log(f"❌ ROLLBACK FAILED: {error}")
            self.status_dialog.set_success(False, "Rollback failed")

        messagebox.showerror("Error", f"Rollback failed:\n\n{error}")

    def clear_log(self):
        """Clear the log text."""
        self.log_text.delete(1.0, tk.END)

    def save_log(self):
        """Save the log to a file."""
        filename = filedialog.asksaveasfilename(
            title="Save Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Success", "Log saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log:\n{str(e)}")

    def load_history(self):
        """Load and display upgrade history."""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            history = upgrades.get_upgrade_history()

            for upgrade in reversed(history):  # Most recent first
                success_text = "✓ Success" if upgrade.success else "✗ Failed"
                applied_at = format_date(upgrade.applied_at, "%Y-%m-%d %H:%M")

                self.history_tree.insert("", tk.END, values=(
                    upgrade.id,
                    upgrade.version,
                    applied_at,
                    success_text,
                    upgrade.manifest.get("description", "")
                ))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load history:\n{str(e)}")

    def view_history_details(self):
        """View detailed information about selected upgrade."""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an upgrade from the history")
            return

        item = self.history_tree.item(selection[0])
        upgrade_id = item["values"][0]

        try:
            history = upgrades.get_upgrade_history()
            upgrade = next((h for h in history if h.id == upgrade_id), None)

            if upgrade:
                details = f"""Upgrade ID: {upgrade.id}
Version: {upgrade.version}
Applied: {format_date(upgrade.applied_at, '%Y-%m-%d %H:%M:%S')}
Success: {'Yes' if upgrade.success else 'No'}
Duration: {upgrade.manifest.get('duration_seconds', 'N/A')} seconds

Description: {upgrade.manifest.get('description', 'N/A')}

Logs:
{chr(10).join(upgrade.logs)}
"""
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(1.0, details)
            else:
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(1.0, f"Upgrade {upgrade_id} not found")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load details:\n{str(e)}")

    def rollback_upgrade(self):
        """Rollback the selected upgrade."""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an upgrade to rollback")
            return

        item = self.history_tree.item(selection[0])
        upgrade_id = item["values"][0]

        if not messagebox.askyesno("Confirm Rollback",
                                  f"Are you sure you want to rollback upgrade '{upgrade_id}'?\n\n"
                                  "This will undo the changes made by this upgrade."):
            return

        # Create status dialog
        self.status_dialog = StatusDialog(self, "Rollback Operation", "Rollback")

        # Ensure dialog is fully visible before starting background work
        self.status_dialog.update()
        self.update()

        # Run rollback in background thread
        def run_rollback():
            try:
                result = upgrades.rollback_upgrade(upgrade_id, progress_callback=self._update_progress)

                # Update UI on completion
                self.after(0, lambda: self._rollback_completed(result))

            except Exception as e:
                self.after(0, lambda: self._rollback_error(str(e)))

        self.current_operation = threading.Thread(target=run_rollback, daemon=True)
        self.current_operation.start()

    def _append_log(self, message: str):
        """Append a message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)  # Auto-scroll to bottom

    def _set_operation_status(self, message: str):
        """Set the operation status message."""
        self.progress_var.set(message)
        self.update_idletasks()
