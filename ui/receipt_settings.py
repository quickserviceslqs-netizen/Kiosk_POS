import tkinter as tk
from tkinter import ttk, messagebox
from database.init_db import get_setting, set_setting

class ReceiptSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Configure receipt printing settings:").pack(pady=(0, 16))

        # Printer settings
        printer_group = ttk.LabelFrame(self, text="Printer Settings", padding=10)
        printer_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(printer_group, text="Default Printer:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(printer_group, textvariable=self.printer_var,
                                        values=["Default Printer", "Thermal Printer", "Laser Printer"],
                                        state="readonly", width=20)
        self.printer_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(printer_group, text="Paper Size:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.paper_size_var = tk.StringVar()
        self.paper_size_combo = ttk.Combobox(printer_group, textvariable=self.paper_size_var,
                                           values=["80mm Thermal", "A4", "Letter", "Custom"],
                                           state="readonly", width=20)
        self.paper_size_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Receipt content settings
        content_group = ttk.LabelFrame(self, text="Receipt Content", padding=10)
        content_group.pack(fill=tk.X, pady=(0, 10))

        self.show_logo_var = tk.BooleanVar()
        ttk.Checkbutton(content_group, text="Show business logo on receipts",
                       variable=self.show_logo_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.show_barcode_var = tk.BooleanVar()
        ttk.Checkbutton(content_group, text="Show receipt barcode",
                       variable=self.show_barcode_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.show_tax_details_var = tk.BooleanVar()
        ttk.Checkbutton(content_group, text="Show detailed tax breakdown",
                       variable=self.show_tax_details_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Footer message
        ttk.Label(content_group, text="Footer Message:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.footer_message = tk.Text(content_group, height=3, width=40, wrap=tk.WORD)
        self.footer_message.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Button(self, text="Save Receipt Settings", command=self.save_settings).pack(pady=16)

        self.load_settings()

    def load_settings(self):
        """Load current receipt settings."""
        self.printer_var.set(get_setting('receipt_printer') or "Default Printer")
        self.paper_size_var.set(get_setting('receipt_paper_size') or "80mm Thermal")
        self.show_logo_var.set(get_setting('receipt_show_logo') == 'true')
        self.show_barcode_var.set(get_setting('receipt_show_barcode') == 'true')
        self.show_tax_details_var.set(get_setting('receipt_show_tax_details') == 'true')

        footer_msg = get_setting('receipt_footer_message') or "Thank you for your business!"
        self.footer_message.delete(1.0, tk.END)
        self.footer_message.insert(1.0, footer_msg)

    def refresh(self):
        """Reload receipt settings from database."""
        self.load_settings()

    def save_settings(self):
        """Save receipt settings."""
        try:
            set_setting('receipt_printer', self.printer_var.get())
            set_setting('receipt_paper_size', self.paper_size_var.get())
            set_setting('receipt_show_logo', 'true' if self.show_logo_var.get() else 'false')
            set_setting('receipt_show_barcode', 'true' if self.show_barcode_var.get() else 'false')
            set_setting('receipt_show_tax_details', 'true' if self.show_tax_details_var.get() else 'false')
            set_setting('receipt_footer_message', self.footer_message.get(1.0, tk.END).strip())

            messagebox.showinfo("Success", "Receipt settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")