import tkinter as tk
from tkinter import ttk, messagebox
from database.init_db import get_setting, set_setting
from datetime import datetime

class DateFormatSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Select your preferred date format:").pack(pady=(0, 16))

        # Common date formats
        self.date_formats = [
            ("%Y-%m-%d", "YYYY-MM-DD (2026-01-15)"),
            ("%d/%m/%Y", "DD/MM/YYYY (15/01/2026)"),
            ("%m/%d/%Y", "MM/DD/YYYY (01/15/2026)"),
            ("%d-%m-%Y", "DD-MM-YYYY (15-01-2026)"),
            ("%m-%d-%Y", "MM-DD-YYYY (01-15-2026)"),
            ("%d.%m.%Y", "DD.MM.YYYY (15.01.2026)"),
            ("%m.%d.%Y", "MM.DD.YYYY (01.15.2026)"),
        ]

        self.format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(self, values=[desc for _, desc in self.date_formats],
                                        textvariable=self.format_var, state="readonly", width=30)
        self.format_combo.pack(pady=4)

        # Preview label
        self.preview_label = ttk.Label(self, text="Preview: ", foreground="gray")
        self.preview_label.pack(pady=(10, 0))

        # Bind selection change to update preview
        self.format_combo.bind('<<ComboboxSelected>>', self._update_preview)

        ttk.Button(self, text="Save Date Format", command=self.save_date_format).pack(pady=16)

        self.load_date_format()

    def _update_preview(self, event=None):
        """Update the preview label with the selected format."""
        selected_desc = self.format_var.get()
        for fmt, desc in self.date_formats:
            if desc == selected_desc:
                try:
                    preview = datetime.now().strftime(fmt)
                    self.preview_label.config(text=f"Preview: {preview}")
                except:
                    self.preview_label.config(text="Preview: Invalid format")
                break

    def load_date_format(self):
        """Load current date format setting."""
        current_format = get_setting('date_format')
        if current_format:
            # Find the description for the current format
            for fmt, desc in self.date_formats:
                if fmt == current_format:
                    self.format_var.set(desc)
                    self._update_preview()
                    break
        else:
            # Default to first option
            self.format_var.set(self.date_formats[0][1])
            self._update_preview()

    def refresh(self):
        """Reload date format settings from database."""
        self.load_date_format()

    def save_date_format(self):
        """Save the selected date format."""
        selected_desc = self.format_var.get()
        if not selected_desc:
            messagebox.showerror("Error", "Please select a date format")
            return

        # Find the format code for the selected description
        selected_format = None
        for fmt, desc in self.date_formats:
            if desc == selected_desc:
                selected_format = fmt
                break

        if selected_format:
            set_setting('date_format', selected_format)
            messagebox.showinfo("Success", "Date format saved successfully!")
            self._update_preview()
        else:
            messagebox.showerror("Error", "Invalid date format selected")