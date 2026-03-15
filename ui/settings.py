import tkinter as tk
from tkinter import ttk, messagebox
from database.init_db import get_connection
import pycountry
from utils.i18n import get_default_currency_symbol_for_code
from utils.currency_notifications import set_currency_settings, subscribe_to_currency_changes, unsubscribe_from_currency_changes

class CurrencySettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Select or enter your preferred currency symbol:").pack(pady=(0, 16))

        # Use only currency codes in the dropdown
        import pycountry
        self.all_currencies = []
        for currency in pycountry.currencies:
            self.all_currencies.append(currency.alpha_3)
        self.currency_var = tk.StringVar()
        self.symbol_var = tk.StringVar()
        self.currency_combo = ttk.Combobox(self, values=self.all_currencies, textvariable=self.currency_var, width=10)
        self.currency_combo.pack(pady=4)
        self.currency_combo.bind('<KeyRelease>', self._filter_currency_list)
        self.currency_combo.bind('<<ComboboxSelected>>', self._on_currency_selected)

        ttk.Label(self, text="Currency Symbol:").pack(pady=(8, 0))
        currency_entry = ttk.Entry(self, textvariable=self.symbol_var, width=10)
        currency_entry.pack(pady=8)

        ttk.Button(self, text="Save Currency", command=self.save_currency).pack(pady=16)

        self.load_currency()

    def _filter_currency_list(self, event):
        typed = self.currency_combo.get().lower()
        filtered = [entry for entry in self.all_currencies if typed in entry.lower()]
        self.currency_combo['values'] = filtered if filtered else self.all_currencies

    def _on_currency_selected(self, event):
        """Auto-populate symbol when currency code is selected."""
        code = self.currency_var.get().strip().upper()
        if code:
            try:
                currency = pycountry.currencies.get(alpha_3=code)
                if currency:
                    # Try to get symbol from pycountry, fallback to common symbols
                    # Use the comprehensive currency symbol mapping from utils.i18n
                    symbol = get_default_currency_symbol_for_code(code)
                    self.symbol_var.set(symbol)
            except Exception:
                pass  # Keep current symbol if lookup fails

    def load_currency(self):
        with get_connection() as conn:
            # Load currency code (legacy key is 'currency' if present)
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency_code'")
            row = cursor.fetchone()
            if row:
                code = row['value'] if isinstance(row, dict) else row[0]
            else:
                # try legacy key for older upgrades
                cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency'")
                row = cursor.fetchone()
                if row:
                    code = row['value'] if isinstance(row, dict) else row[0]
                else:
                    code = 'USD'
            self.currency_var.set(code)

            # Load currency symbol
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency_symbol'")
            row = cursor.fetchone()
            if row:
                self.symbol_var.set(row['value'] if isinstance(row, dict) else row[0])
            else:
                # Use default symbol for the code
                default_symbol = get_default_currency_symbol_for_code(code)
                self.symbol_var.set(default_symbol)

    def refresh(self):
        """Reload currency settings from database."""
        self.load_currency()

    def save_currency(self):
        code = self.currency_var.get().strip().upper()
        symbol = self.symbol_var.get().strip()
        
        if not code:
            messagebox.showerror("Error", "Currency code cannot be empty.")
            return
        if not symbol:
            messagebox.showerror("Error", "Currency symbol cannot be empty.")
            return
        
        try:
            # Use the centralized currency setting system (handles encoding and notifications)
            set_currency_settings(code, symbol)
            messagebox.showinfo("Saved", f"Currency set to {code} ({symbol})")
            # Refresh the displayed value
            self.load_currency()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save currency settings: {e}")

    def _go_home(self):
        root = self.winfo_toplevel()
        from main import show_home
        user = getattr(root, "current_user", {})
        show_home(root, user)
