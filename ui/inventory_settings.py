import tkinter as tk
from tkinter import ttk, messagebox
from database.init_db import get_setting, set_setting

class InventorySettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Configure inventory management and alert settings:").pack(pady=(0, 16))

        # Alert thresholds
        alerts_group = ttk.LabelFrame(self, text="Stock Alert Thresholds", padding=10)
        alerts_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(alerts_group, text="Low stock threshold:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.low_stock_var = tk.StringVar()
        self.low_stock_spin = ttk.Spinbox(alerts_group, from_=0, to=1000,
                                        textvariable=self.low_stock_var, width=10)
        self.low_stock_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        ttk.Label(alerts_group, text="units").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=2)

        ttk.Label(alerts_group, text="Critical stock threshold:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.critical_stock_var = tk.StringVar()
        self.critical_stock_spin = ttk.Spinbox(alerts_group, from_=0, to=500,
                                             textvariable=self.critical_stock_var, width=10)
        self.critical_stock_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        ttk.Label(alerts_group, text="units").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=2)

        ttk.Label(alerts_group, text="Overstock threshold:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.overstock_var = tk.StringVar()
        self.overstock_spin = ttk.Spinbox(alerts_group, from_=100, to=10000,
                                        textvariable=self.overstock_var, width=10)
        self.overstock_spin.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        ttk.Label(alerts_group, text="units").grid(row=2, column=2, sticky=tk.W, padx=(5, 0), pady=2)

        # Alert settings
        alert_settings_group = ttk.LabelFrame(self, text="Alert Settings", padding=10)
        alert_settings_group.pack(fill=tk.X, pady=(0, 10))

        self.low_stock_alerts_var = tk.BooleanVar()
        ttk.Checkbutton(alert_settings_group, text="Enable low stock email alerts",
                       variable=self.low_stock_alerts_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.critical_stock_alerts_var = tk.BooleanVar()
        ttk.Checkbutton(alert_settings_group, text="Enable critical stock email alerts",
                       variable=self.critical_stock_alerts_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.overstock_alerts_var = tk.BooleanVar()
        ttk.Checkbutton(alert_settings_group, text="Enable overstock warnings",
                       variable=self.overstock_alerts_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.auto_reorder_var = tk.BooleanVar()
        ttk.Checkbutton(alert_settings_group, text="Enable automatic reorder suggestions",
                       variable=self.auto_reorder_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Inventory behavior
        behavior_group = ttk.LabelFrame(self, text="Inventory Behavior", padding=10)
        behavior_group.pack(fill=tk.X, pady=(0, 10))

        self.negative_stock_var = tk.BooleanVar()
        ttk.Checkbutton(behavior_group, text="Allow negative stock levels",
                       variable=self.negative_stock_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.track_expiry_var = tk.BooleanVar()
        ttk.Checkbutton(behavior_group, text="Track item expiry dates",
                       variable=self.track_expiry_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(behavior_group, text="Expiry warning (days):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.expiry_warning_var = tk.StringVar()
        self.expiry_spin = ttk.Spinbox(behavior_group, from_=1, to=365,
                                     textvariable=self.expiry_warning_var, width=10)
        self.expiry_spin.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Default units
        ttk.Label(behavior_group, text="Default unit of measure:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.default_unit_var = tk.StringVar()
        self.unit_combo = ttk.Combobox(behavior_group, textvariable=self.default_unit_var,
                                     values=["pieces", "kg", "liters", "meters", "boxes"],
                                     state="readonly", width=15)
        self.unit_combo.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Button(self, text="Save Inventory Settings", command=self.save_settings).pack(pady=16)

        self.load_settings()

    def load_settings(self):
        """Load current inventory settings."""
        self.low_stock_var.set(get_setting('inventory_low_stock_threshold') or "10")
        self.critical_stock_var.set(get_setting('inventory_critical_stock_threshold') or "5")
        self.overstock_var.set(get_setting('inventory_overstock_threshold') or "1000")

        self.low_stock_alerts_var.set(get_setting('inventory_low_stock_alerts') == 'true')
        self.critical_stock_alerts_var.set(get_setting('inventory_critical_stock_alerts') == 'true')
        self.overstock_alerts_var.set(get_setting('inventory_overstock_alerts') == 'true')
        self.auto_reorder_var.set(get_setting('inventory_auto_reorder') == 'true')

        self.negative_stock_var.set(get_setting('inventory_allow_negative') == 'true')
        self.track_expiry_var.set(get_setting('inventory_track_expiry') == 'true')
        self.expiry_warning_var.set(get_setting('inventory_expiry_warning_days') or "30")
        self.default_unit_var.set(get_setting('inventory_default_unit') or "pieces")

    def refresh(self):
        """Reload inventory settings from database."""
        self.load_settings()

    def save_settings(self):
        """Save inventory settings."""
        try:
            set_setting('inventory_low_stock_threshold', self.low_stock_var.get())
            set_setting('inventory_critical_stock_threshold', self.critical_stock_var.get())
            set_setting('inventory_overstock_threshold', self.overstock_var.get())

            set_setting('inventory_low_stock_alerts', 'true' if self.low_stock_alerts_var.get() else 'false')
            set_setting('inventory_critical_stock_alerts', 'true' if self.critical_stock_alerts_var.get() else 'false')
            set_setting('inventory_overstock_alerts', 'true' if self.overstock_alerts_var.get() else 'false')
            set_setting('inventory_auto_reorder', 'true' if self.auto_reorder_var.get() else 'false')

            set_setting('inventory_allow_negative', 'true' if self.negative_stock_var.get() else 'false')
            set_setting('inventory_track_expiry', 'true' if self.track_expiry_var.get() else 'false')
            set_setting('inventory_expiry_warning_days', self.expiry_warning_var.get())
            set_setting('inventory_default_unit', self.default_unit_var.get())

            messagebox.showinfo("Success", "Inventory settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")