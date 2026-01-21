import tkinter as tk
from tkinter import ttk, messagebox
from database.init_db import get_connection
import pycountry

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
        self.currency_combo = ttk.Combobox(self, values=self.all_currencies, textvariable=self.currency_var, width=10)
        self.currency_combo.pack(pady=4)
        self.currency_combo.bind('<KeyRelease>', self._filter_currency_list)

        currency_entry = ttk.Entry(self, textvariable=self.currency_var, width=10)
        currency_entry.pack(pady=8)

        ttk.Button(self, text="Save Currency", command=self.save_currency).pack(pady=16)

        self.load_currency()

    def _filter_currency_list(self, event):
        typed = self.currency_combo.get().lower()
        filtered = [entry for entry in self.all_currencies if typed in entry.lower()]
        self.currency_combo['values'] = filtered if filtered else self.all_currencies

    def load_currency(self):
        with get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency_symbol'")
            row = cursor.fetchone()
            if row:
                self.currency_var.set(row['value'] if isinstance(row, dict) else row[0])

    def refresh(self):
        """Reload currency settings from database."""
        self.load_currency()

    def save_currency(self):
        symbol_entry = self.currency_var.get().strip()
        # Extract symbol from combobox selection if formatted
        if ' - ' in symbol_entry:
            symbol_entry = symbol_entry.split(' - ')[0].strip()
        
        # Check if it's a currency code (3 letters, uppercase)
        import pycountry
        currency_code = None
        currency_symbol = symbol_entry
        
        if len(symbol_entry) == 3 and symbol_entry.isupper():
            # It's a currency code, get the symbol
            try:
                currency = pycountry.currencies.get(alpha_3=symbol_entry)
                if currency:
                    currency_code = symbol_entry
                    # Try to get symbol from pycountry, fallback to manual mapping
                    if hasattr(currency, 'symbol') and currency.symbol:
                        currency_symbol = currency.symbol
                    else:
                        # Manual mapping for common currencies
                        symbol_map = {'USD': '$', 'EUR': '€', 'GBP': '£', 'KES': 'KSh', 'JPY': '¥', 'CNY': '¥'}
                        currency_symbol = symbol_map.get(symbol_entry, symbol_entry)
            except:
                pass
        
        if not currency_symbol:
            messagebox.showerror("Error", "Currency symbol cannot be empty.")
            return
            
        with get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("currency_symbol", currency_symbol))
            if currency_code:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("currency_code", currency_code))
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("currency", currency_code))  # For backward compatibility
            conn.commit()
        
        messagebox.showinfo("Saved", f"Currency set to {currency_symbol}")
        # Stay on the currency settings page and refresh the displayed value
        self.load_currency()

    def _go_home(self):
        root = self.winfo_toplevel()
        from main import show_home
        user = getattr(root, "current_user", {})
        show_home(root, user)
