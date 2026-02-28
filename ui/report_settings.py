import tkinter as tk
from tkinter import ttk, messagebox
from database.init_db import get_setting, set_setting

class ReportSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Configure report display and export preferences:").pack(pady=(0, 16))

        # Display settings
        display_group = ttk.LabelFrame(self, text="Display Settings", padding=10)
        display_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(display_group, text="Default items per page:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.items_per_page_var = tk.StringVar()
        self.items_per_page_spin = ttk.Spinbox(display_group, from_=10, to=1000,
                                             textvariable=self.items_per_page_var, width=10)
        self.items_per_page_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.show_charts_var = tk.BooleanVar()
        ttk.Checkbutton(display_group, text="Show charts in reports",
                       variable=self.show_charts_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.auto_refresh_var = tk.BooleanVar()
        ttk.Checkbutton(display_group, text="Auto-refresh reports",
                       variable=self.auto_refresh_var).grid(row=2, column=0, sticky=tk.W, pady=2)

        ttk.Label(display_group, text="Refresh interval (minutes):").grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        self.refresh_interval_var = tk.StringVar()
        self.refresh_spin = ttk.Spinbox(display_group, from_=1, to=60,
                                      textvariable=self.refresh_interval_var, width=5)
        self.refresh_spin.grid(row=2, column=2, sticky=tk.W, padx=(5, 0), pady=2)

        # Export settings
        export_group = ttk.LabelFrame(self, text="Export Settings", padding=10)
        export_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(export_group, text="Default export format:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.default_format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(export_group, textvariable=self.default_format_var,
                                       values=["CSV", "Excel", "PDF", "Text"],
                                       state="readonly", width=15)
        self.format_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.include_headers_var = tk.BooleanVar()
        ttk.Checkbutton(export_group, text="Include column headers in exports",
                       variable=self.include_headers_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.compress_exports_var = tk.BooleanVar()
        ttk.Checkbutton(export_group, text="Compress large exports (ZIP)",
                       variable=self.compress_exports_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Date range defaults
        date_group = ttk.LabelFrame(self, text="Date Range Defaults", padding=10)
        date_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(date_group, text="Default report period:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.default_period_var = tk.StringVar()
        self.period_combo = ttk.Combobox(date_group, textvariable=self.default_period_var,
                                       values=["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Month", "This Week"],
                                       state="readonly", width=15)
        self.period_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Button(self, text="Save Report Settings", command=self.save_settings).pack(pady=16)

        self.load_settings()

    def load_settings(self):
        """Load current report settings."""
        items_per_page = get_setting('report_items_per_page')
        self.items_per_page_var.set(items_per_page or "100")

        self.show_charts_var.set(get_setting('report_show_charts') != 'false')  # Default true
        self.auto_refresh_var.set(get_setting('report_auto_refresh') == 'true')

        refresh_interval = get_setting('report_refresh_interval')
        self.refresh_interval_var.set(refresh_interval or "5")

        self.default_format_var.set(get_setting('report_default_format') or "CSV")
        self.include_headers_var.set(get_setting('report_include_headers') != 'false')  # Default true
        self.compress_exports_var.set(get_setting('report_compress_exports') == 'true')
        self.default_period_var.set(get_setting('report_default_period') or "Last 30 Days")

    def refresh(self):
        """Reload report settings from database."""
        self.load_settings()

    def save_settings(self):
        """Save report settings."""
        try:
            set_setting('report_items_per_page', self.items_per_page_var.get())
            set_setting('report_show_charts', 'true' if self.show_charts_var.get() else 'false')
            set_setting('report_auto_refresh', 'true' if self.auto_refresh_var.get() else 'false')
            set_setting('report_refresh_interval', self.refresh_interval_var.get())
            set_setting('report_default_format', self.default_format_var.get())
            set_setting('report_include_headers', 'true' if self.include_headers_var.get() else 'false')
            set_setting('report_compress_exports', 'true' if self.compress_exports_var.get() else 'false')
            set_setting('report_default_period', self.default_period_var.get())

            messagebox.showinfo("Success", "Report settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")