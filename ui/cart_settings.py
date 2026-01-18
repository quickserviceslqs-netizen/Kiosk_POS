"""Cart management settings UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from database.init_db import get_connection
from utils.security import set_payment_methods


def set_dialog_icon(dialog: tk.Toplevel) -> None:
    """Set the custom application icon for a dialogue window."""
    try:
        dialog.iconbitmap("assets/app_icon.ico")
    except tk.TclError:
        pass  # Icon not found or not supported


class CartSettingsFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_home = on_home
        self._build_ui()
        self.load_settings()

    def _create_setting_card(self, parent, title, subtitle):
        """Create a modern card-style frame for settings."""
        card = ttk.Frame(parent, relief="raised", borderwidth=1)
        # Remove pack_propagate(False) to allow the card to resize with its contents

        # Title
        title_label = ttk.Label(card, text=title, font=("Segoe UI", 14, "bold"))
        title_label.pack(anchor=tk.W, pady=(15, 5), padx=15)

        # Subtitle
        if subtitle:
            subtitle_label = ttk.Label(card, text=subtitle, foreground="gray", font=("Segoe UI", 9))
            subtitle_label.pack(anchor=tk.W, padx=15, pady=(0, 10))

        return card

    def _build_ui(self):
        # Main container with better spacing
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(main_frame, text="Cart Management Settings", font=("Segoe UI", 18, "bold"))
        title_label.pack(pady=(0, 30))

        # Scrollable content area
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Content inside scrollable frame
        content_frame = ttk.Frame(scrollable_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # VAT Settings Card
        vat_card = self._create_setting_card(content_frame, "VAT Functionality", "Enable VAT calculation and display")
        vat_card.pack(fill=tk.X, pady=(0, 20))

        self.vat_enabled_var = tk.BooleanVar()
        vat_check = ttk.Checkbutton(
            vat_card,
            text="Enable VAT calculation and display",
            variable=self.vat_enabled_var,
            command=self._on_vat_toggle
        )
        vat_check.pack(anchor=tk.W, pady=(10, 5))

        vat_desc = ttk.Label(
            vat_card,
            text="When disabled, VAT will not be calculated or shown in cart totals.",
            foreground="gray",
            wraplength=500,
            justify=tk.LEFT
        )
        vat_desc.pack(anchor=tk.W, pady=(0, 10))

        # Discount Settings Card
        discount_card = self._create_setting_card(content_frame, "Discount Functionality", "Enable discount application")
        discount_card.pack(fill=tk.X, pady=(0, 20))

        self.discount_enabled_var = tk.BooleanVar()
        discount_check = ttk.Checkbutton(
            discount_card,
            text="Enable discount application",
            variable=self.discount_enabled_var,
            command=self._on_discount_toggle
        )
        discount_check.pack(anchor=tk.W, pady=(10, 5))

        discount_desc = ttk.Label(
            discount_card,
            text="When disabled, discount fields will be hidden and no discounts applied.",
            foreground="gray",
            wraplength=500,
            justify=tk.LEFT
        )
        discount_desc.pack(anchor=tk.W, pady=(0, 10))

        # Cart Suspension Settings Card
        suspend_card = self._create_setting_card(content_frame, "Cart Suspension", "Enable cart suspend/resume functionality")
        suspend_card.pack(fill=tk.X, pady=(0, 20))

        self.suspend_enabled_var = tk.BooleanVar()
        suspend_check = ttk.Checkbutton(
            suspend_card,
            text="Enable cart suspend/resume functionality",
            variable=self.suspend_enabled_var,
            command=self._on_suspend_toggle
        )
        suspend_check.pack(anchor=tk.W, pady=(10, 5))

        suspend_desc = ttk.Label(
            suspend_card,
            text="When disabled, suspend/resume buttons will be hidden.",
            foreground="gray",
            wraplength=500,
            justify=tk.LEFT
        )
        suspend_desc.pack(anchor=tk.W, pady=(0, 10))

        # Payment Methods Card
        pm_card = self._create_setting_card(content_frame, "Payment Methods", "Manage available payment methods")
        pm_card.pack(fill=tk.X, pady=(0, 20))

        # Payment methods list with modern design
        pm_list_frame = ttk.Frame(pm_card)
        pm_list_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 10))

        # Header for list
        list_header = ttk.Label(pm_list_frame, text="Configured Payment Methods", font=("Segoe UI", 11, "bold"))
        list_header.pack(anchor=tk.W, pady=(0, 10))

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(pm_list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        self.pm_listbox = tk.Listbox(
            listbox_frame,
            height=8,
            selectmode=tk.SINGLE,
            font=("Segoe UI", 10),
            bg="white",
            relief="flat",
            borderwidth=1
        )
        self.pm_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        pm_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.pm_listbox.yview)
        pm_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pm_listbox.config(yscrollcommand=pm_scrollbar.set)

        # Action buttons in a horizontal layout
        button_frame = ttk.Frame(pm_list_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="➕ Add", command=self._add_payment_method).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✏️ Edit", command=self._edit_payment_method).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑️ Delete", command=self._delete_payment_method).pack(side=tk.LEFT)

        # Save button at bottom
        save_frame = ttk.Frame(content_frame)
        save_frame.pack(fill=tk.X, pady=(30, 0))

        ttk.Button(save_frame, text="💾 Save All Settings", command=self.save_settings, style="Accent.TButton").pack(side=tk.RIGHT)

        # Update canvas scrollregion after content is built
        self.after_idle(lambda: canvas.configure(scrollregion=canvas.bbox("all")))

    def load_settings(self):
        """Load current settings from database."""
        with get_connection() as conn:
            cursor = conn.execute("""
                SELECT key, value FROM settings
                WHERE key IN ('vat_enabled', 'discount_enabled', 'suspend_enabled', 'payment_methods')
            """)
            rows = cursor.fetchall()
            settings = {}
            for row in rows:
                if isinstance(row, dict):
                    key, value = row['key'], row['value']
                else:
                    key, value = row[0], row[1]
                settings[key] = value

        # Set defaults if not configured
        self.vat_enabled_var.set(settings.get('vat_enabled', 'true').lower() == 'true')
        self.discount_enabled_var.set(settings.get('discount_enabled', 'true').lower() == 'true')
        self.suspend_enabled_var.set(settings.get('suspend_enabled', 'true').lower() == 'true')

        # Load payment methods
        pm_raw = settings.get('payment_methods')
        methods = []
        if pm_raw:
            try:
                import json
                loaded = json.loads(pm_raw)
                if isinstance(loaded, list):
                    methods = [str(m) for m in loaded]
            except Exception:
                methods = []
        if not methods:
            from utils.security import get_payment_methods
            methods = get_payment_methods()

        # Populate listbox
        self.pm_listbox.delete(0, tk.END)
        for m in methods:
            self.pm_listbox.insert(tk.END, m)

    def save_settings(self):
        """Save settings to database."""
        with get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        ("vat_enabled", "true" if self.vat_enabled_var.get() else "false"))
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        ("discount_enabled", "true" if self.discount_enabled_var.get() else "false"))
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        ("suspend_enabled", "true" if self.suspend_enabled_var.get() else "false"))

            # Persist payment methods via helper (which will also notify listeners)
            methods = list(self.pm_listbox.get(0, tk.END))
            set_payment_methods(methods)
            # Other settings already committed above


        messagebox.showinfo("Saved", "Cart management settings saved successfully!")

    def _on_vat_toggle(self):
        """Handle VAT toggle - could add validation here if needed."""
        pass

    def _on_discount_toggle(self):
        """Handle discount toggle - could add validation here if needed."""
        pass

    def _on_suspend_toggle(self):
        """Handle suspend toggle - could add validation here if needed."""
        pass

    # Payment methods management
    def _add_payment_method(self):
        def on_ok():
            name = entry_var.get().strip()
            if not name:
                messagebox.showerror("Invalid", "Enter a name for the payment method")
                return
            # Check duplicates
            existing = list(self.pm_listbox.get(0, tk.END))
            if name in existing:
                messagebox.showerror("Duplicate", "Payment method already exists")
                return
            self.pm_listbox.insert(tk.END, name)
            dlg.destroy()

        dlg = tk.Toplevel(self)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        dlg.title("Add Payment Method")
        set_dialog_icon(dlg)
        entry_var = tk.StringVar()
        ttk.Label(dlg, text="Method name:").pack(padx=12, pady=(12, 4))
        ttk.Entry(dlg, textvariable=entry_var).pack(padx=12, pady=(0, 12))
        btns = ttk.Frame(dlg)
        btns.pack(pady=(0, 12))
        ttk.Button(btns, text="Add", command=on_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=6)

    def _edit_payment_method(self):
        sel = self.pm_listbox.curselection()
        if not sel:
            messagebox.showinfo("Edit", "Select a payment method to edit")
            return
        index = sel[0]
        current = self.pm_listbox.get(index)

        def on_ok():
            name = entry_var.get().strip()
            if not name:
                messagebox.showerror("Invalid", "Enter a name for the payment method")
                return
            existing = list(self.pm_listbox.get(0, tk.END))
            existing.pop(index)  # Remove current item for duplicate check
            if name in existing:
                messagebox.showerror("Duplicate", "Payment method already exists")
                return
            self.pm_listbox.delete(index)
            self.pm_listbox.insert(index, name)
            dlg.destroy()

        dlg = tk.Toplevel(self)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        dlg.title("Edit Payment Method")
        set_dialog_icon(dlg)
        entry_var = tk.StringVar(value=current)
        ttk.Label(dlg, text="Method name:").pack(padx=12, pady=(12, 4))
        ttk.Entry(dlg, textvariable=entry_var).pack(padx=12, pady=(0, 12))
        btns = ttk.Frame(dlg)
        btns.pack(pady=(0, 12))
        ttk.Button(btns, text="Save", command=on_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=6)

    def _delete_payment_method(self):
        sel = self.pm_listbox.curselection()
        if not sel:
            messagebox.showinfo("Delete", "Select a payment method to delete")
            return
        index = sel[0]
        name = self.pm_listbox.get(index)
        if messagebox.askyesno("Delete", f"Delete payment method '{name}'?"):
            self.pm_listbox.delete(index)

    def refresh(self):
        """Reload settings from database."""
        self.load_settings()