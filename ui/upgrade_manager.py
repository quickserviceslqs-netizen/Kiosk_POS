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

from modules import upgrades
from utils import set_window_icon


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

        # Set the app's custom icon
        set_window_icon(self)

        # Create custom green progress bar style
        self._setup_progress_style()

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

    def _setup_progress_style(self):
        """Setup custom green progress bar style."""
        style = ttk.Style()
        
        # Create a custom style for green progress bar
        style.configure("Green.Horizontal.TProgressbar",
                       troughcolor='#f0f0f0',
                       borderwidth=1,
                       lightcolor='#4CAF50',
                       darkcolor='#4CAF50',
                       bordercolor='#4CAF50',
                       background='#4CAF50')
        
        # This makes the progress bar fill green
        style.map("Green.Horizontal.TProgressbar",
                 background=[('active', '#4CAF50')],
                 lightcolor=[('active', '#4CAF50')],
                 darkcolor=[('active', '#4CAF50')])

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

    def __init__(self, master=None, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.pkg_path: Optional[Path] = None
        self.current_operation = None
        self.cancellation_token = threading.Event()
        self.signing_key: Optional[str] = None
        self.status_dialog: Optional[StatusDialog] = None
        
        # Setup custom styles
        self._setup_styles()
        
        self._build_ui()

    def _setup_styles(self):
        """Setup custom styles for the UI."""
        style = ttk.Style()
        
        # Create a custom style for green progress bar
        style.configure("Green.Horizontal.TProgressbar",
                       troughcolor='#f0f0f0',
                       borderwidth=1,
                       lightcolor='#4CAF50',
                       darkcolor='#4CAF50',
                       bordercolor='#4CAF50',
                       background='#4CAF50')
        
        # This makes the progress bar fill green
        style.map("Green.Horizontal.TProgressbar",
                 background=[('active', '#4CAF50')],
                 lightcolor=[('active', '#4CAF50')],
                 darkcolor=[('active', '#4CAF50')])

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
        # Title
        title = ttk.Label(parent, text="System Upgrade Manager", font=("Segoe UI", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 16))

        # Package selection frame
        pkg_frame = ttk.LabelFrame(parent, text="Upgrade Package", padding=10)
        pkg_frame.pack(fill=tk.X, pady=(0, 16))

        self.pkg_label = ttk.Label(pkg_frame, text="No package selected", foreground="gray")
        self.pkg_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_frame = ttk.Frame(pkg_frame)
        btn_frame.pack(side=tk.RIGHT)

        self.select_btn = ttk.Button(btn_frame, text="📁 Select Package", command=self.choose_package)
        self.select_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.preview_btn = ttk.Button(btn_frame, text="👁️ Preview", command=self.preview, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT)

        # Security frame
        security_frame = ttk.LabelFrame(parent, text="Security", padding=10)
        security_frame.pack(fill=tk.X, pady=(0, 16))

        ttk.Label(security_frame, text="Signing Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.key_entry = ttk.Entry(security_frame, show="*")
        self.key_entry.grid(row=0, column=1, sticky=tk.EW, padx=(8, 0), pady=2)

        self.verify_sig_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(security_frame, text="Verify package signature",
                       variable=self.verify_sig_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        security_frame.columnconfigure(1, weight=1)

        # Action buttons frame
        action_frame = ttk.LabelFrame(parent, text="Actions", padding=10)
        action_frame.pack(fill=tk.X, pady=(0, 16))

        self.dry_run_btn = ttk.Button(action_frame, text="🔍 Dry Run", command=self.dry_run, state=tk.DISABLED)
        self.dry_run_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.apply_btn = ttk.Button(action_frame, text="⚡ Apply Upgrade", command=self.apply, state=tk.DISABLED)
        self.apply_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.cancel_btn = ttk.Button(action_frame, text="⏹️ Cancel", command=self.cancel_operation, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT)

        # Progress frame
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 16))

        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.pack(anchor=tk.W)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', maximum=100,
                                     style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))

        # Log frame
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Create text widget with scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(text_frame, height=15, wrap=tk.WORD,
                                                 font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        control_frame = ttk.Frame(log_frame)
        control_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(control_frame, text="🗑️ Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(control_frame, text="💾 Save Log", command=self.save_log).pack(side=tk.LEFT)

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
        """Build the settings tab."""
        # Title
        title = ttk.Label(parent, text="Upgrade Settings", font=("Segoe UI", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 16))

        # Security settings
        security_frame = ttk.LabelFrame(parent, text="Security Settings", padding=10)
        security_frame.pack(fill=tk.X, pady=(0, 16))

        ttk.Label(security_frame, text="Master Signing Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.master_key_entry = ttk.Entry(security_frame, show="*")
        self.master_key_entry.grid(row=0, column=1, sticky=tk.EW, padx=(8, 0), pady=2)

        ttk.Button(security_frame, text="🔑 Generate New Key",
                  command=self.generate_key).grid(row=1, column=0, pady=8)
        ttk.Button(security_frame, text="💾 Save Key",
                  command=self.save_key).grid(row=1, column=1, pady=8)

        security_frame.columnconfigure(1, weight=1)

        # Backup settings
        backup_frame = ttk.LabelFrame(parent, text="Backup Settings", padding=10)
        backup_frame.pack(fill=tk.X, pady=(0, 16))

        self.backup_db_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(backup_frame, text="Backup database before upgrade",
                       variable=self.backup_db_var).pack(anchor=tk.W)

        self.keep_backups_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(backup_frame, text="Keep backup files after successful upgrade",
                       variable=self.keep_backups_var).pack(anchor=tk.W)

        # Advanced settings
        advanced_frame = ttk.LabelFrame(parent, text="Advanced Settings", padding=10)
        advanced_frame.pack(fill=tk.X, pady=(0, 16))

        ttk.Label(advanced_frame, text="Timeout (seconds):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.timeout_entry = ttk.Entry(advanced_frame)
        self.timeout_entry.insert(0, "300")
        self.timeout_entry.grid(row=0, column=1, sticky=tk.EW, padx=(8, 0), pady=2)

        advanced_frame.columnconfigure(1, weight=1)

    def choose_package(self):
        """Select an upgrade package file."""
        filename = filedialog.askopenfilename(
            title="Select Upgrade Package",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if filename:
            self.pkg_path = Path(filename)
            self.pkg_label.config(text=f"📦 {self.pkg_path.name}", foreground="black")
            self._append_log(f"Selected package: {self.pkg_path}")

            # Enable action buttons
            self.preview_btn.config(state=tk.NORMAL)
            self.dry_run_btn.config(state=tk.NORMAL)
            self.apply_btn.config(state=tk.NORMAL)

    def preview(self):
        """Preview the upgrade package contents."""
        if not self.pkg_path:
            return

        # Create status dialog
        self.status_dialog = StatusDialog(self, "Package Preview", "Preview")

        # Ensure dialog is fully visible before starting background work
        self.status_dialog.update()
        self.update()

        def run_preview():
            try:
                self.status_dialog.update_status("Loading package contents...")
                steps = upgrades.preview_package(str(self.pkg_path))

                self.status_dialog.update_status(f"Found {len(steps)} steps")
                self.status_dialog.add_log(f"📋 Package Preview ({len(steps)} steps):")
                self.status_dialog.add_log("=" * 50)

                for i, step in enumerate(steps, 1):
                    stype = step.get("type", "unknown")
                    desc = step.get("description", f"Step {i}")
                    emoji = {
                        "dependency_check": "❓",
                        "sql": "🗄️",
                        "python": "🐍",
                        "copy": "📁",
                        "command": "⚡"
                    }.get(stype, "📄")
                    self.status_dialog.add_log(f" {i}. {emoji} {stype.upper()}: {desc}")
                    self.status_dialog.update_operation(f"Processing step {i}/{len(steps)}")
                    time.sleep(0.1)  # Brief pause for visual feedback

                self.status_dialog.add_log("=" * 50)
                self.status_dialog.update_operation("Preview completed")
                self.status_dialog.set_success(True, "Package preview completed successfully")

                # Show success popup
                messagebox.showinfo("Preview Success", "Package preview completed successfully!\n\nThe upgrade package is valid and contains all necessary components.")

                # Also update main UI
                self._append_log("✅ Package preview completed successfully")
                self.progress_var.set("Preview completed")

            except Exception as e:
                error_msg = f"Preview failed: {str(e)}"
                self.status_dialog.add_log(f"❌ {error_msg}")
                self.status_dialog.set_success(False, error_msg)

                # Show error popup
                messagebox.showerror("Preview Failed", f"Package preview failed:\n\n{str(e)}")

                # Also update main UI
                self._append_log(f"❌ Preview failed: {str(e)}")
                self.progress_var.set("Preview failed")

        # Run in background thread
        preview_thread = threading.Thread(target=run_preview, daemon=True)
        preview_thread.start()

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
        self.preview_btn.config(state=tk.DISABLED)
        self.dry_run_btn.config(state=tk.DISABLED)
        self.apply_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

        # Clear progress
        self.progress_bar.config(value=0)
        self.progress_var.set("Starting...")

        # Get settings
        signature = None
        signing_key = None

        if self.verify_sig_var.get():
            key_text = self.key_entry.get().strip()
            if key_text:
                signing_key = key_text
                try:
                    signature = upgrades.UpgradeSigner.sign_package(str(self.pkg_path), signing_key)
                except Exception as e:
                    self._append_log(f"Failed to sign package: {e}")
                    return

        # Run in background thread
        def run_upgrade():
            try:
                result = upgrades.apply_package(
                    str(self.pkg_path),
                    dry_run=dry_run,
                    backup_db=self.backup_db_var.get(),
                    progress_callback=self._update_progress,
                    cancellation_token=self.cancellation_token,
                    signature=signature,
                    signing_key=signing_key
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

            # Also update status dialog if it exists
            if self.status_dialog:
                self.status_dialog.update_status(message, percentage)
                self.status_dialog.update_operation(message)

        self.after(0, update)

    def _upgrade_completed(self, result: Dict[str, Any]):
        """Handle upgrade completion."""
        # Re-enable buttons
        self.select_btn.config(state=tk.NORMAL)
        self.preview_btn.config(state=tk.NORMAL)
        self.dry_run_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)

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
        self.preview_btn.config(state=tk.NORMAL)
        self.dry_run_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)
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
                applied_at = upgrade.applied_at.strftime("%Y-%m-%d %H:%M")

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
Applied: {upgrade.applied_at.strftime('%Y-%m-%d %H:%M:%S')}
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

    def generate_key(self):
        """Generate a new signing key."""
        key = upgrades.UpgradeSigner.generate_key()
        self.master_key_entry.delete(0, tk.END)
        self.master_key_entry.insert(0, key)
        messagebox.showinfo("Key Generated", "New signing key generated.\n\nSave this key securely!")

    def save_key(self):
        """Save the signing key to a file."""
        key = self.master_key_entry.get().strip()
        if not key:
            messagebox.showwarning("No Key", "Please generate or enter a key first")
            return

        filename = filedialog.asksaveasfilename(
            title="Save Signing Key",
            defaultextension=".key",
            filetypes=[("Key files", "*.key"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(key)
                messagebox.showinfo("Success", "Key saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save key:\n{str(e)}")

    def _append_log(self, message: str):
        """Append a message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)  # Auto-scroll to bottom

    def choose_package(self):
        """Select an upgrade package file."""
        filename = filedialog.askopenfilename(
            title="Select Upgrade Package",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if filename:
            self.pkg_path = Path(filename)
            self.pkg_label.config(text=f"📦 {self.pkg_path.name}", foreground="black")
            self._append_log(f"Selected package: {self.pkg_path}")

            # Enable action buttons
            self.preview_btn.config(state=tk.NORMAL)
            self.dry_run_btn.config(state=tk.NORMAL)
            self.apply_btn.config(state=tk.NORMAL)

    def _set_operation_status(self, message: str):
        """Set the operation status message."""
        self.progress_var.set(message)
        self.update_idletasks()

# Legacy Toplevel version for backward compatibility
class UpgradeManager(tk.Toplevel):
    """Legacy Toplevel version for backward compatibility."""

    def __init__(self, master=None):
        super().__init__(master)
        self.title("Upgrade Manager")
        self.geometry("700x480")
        self.resizable(True, True)
        
        # Set the app's custom icon
        set_window_icon(self)
        
        self.pkg_path: Optional[Path] = None
        self._build_ui()

    def _build_ui(self):
        frame = UpgradeManagerFrame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
