"""
Simple Excel-like Reconciliation UI

This provides a minimal, spreadsheet-style interface for reconciliation:
- Direct cell editing like Excel
- Simple table with payment methods, expected, actual, variance
- Basic operations: add row, delete row, save/load
- Automatic calculations
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkFont
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Union
from utils.date_utils import format_date
import csv
import os
import logging

from modules.reconciliation_core import ReconciliationSession, ReconciliationItem
from utils.i18n import get_currency_symbol

logger = logging.getLogger(__name__)


class SimpleReconciliationUI(ttk.Frame):
    """Simple Excel-like reconciliation interface."""

    def __init__(self, parent: tk.Misc, *, on_home: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.currency_symbol = get_currency_symbol()
        self.current_session: Optional[ReconciliationSession] = None
        self.on_home = on_home

        # Get user info
        root = parent.winfo_toplevel()
        self.current_user = getattr(root, "current_user", {})
        self.user_id = self.current_user.get('user_id', 1)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the simple Excel-like UI."""
        self.configure(padding=10)

        # Initialize status variable
        self.status_var = tk.StringVar(value="Ready")

        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text="Payment Reconciliation",
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

        # Simple toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Left side - basic operations
        left_tools = ttk.Frame(toolbar)
        left_tools.pack(side=tk.LEFT)

        ttk.Button(left_tools, text="New", command=self._new_session).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_tools, text="Load", command=self._load_session).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_tools, text="Save", command=self._save_session).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_tools, text="Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=(0, 10))

        # Right side - session info
        right_tools = ttk.Frame(toolbar)
        right_tools.pack(side=tk.RIGHT)

        ttk.Label(right_tools, text="Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.date_var = tk.StringVar(value=format_date(datetime.now()))
        ttk.Entry(right_tools, textvariable=self.date_var, width=10).pack(side=tk.LEFT, padx=(0, 10))

        # Main table area
        self._build_table()

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var,
                              font=("Segoe UI", 8), foreground="gray")
        status_bar.pack(fill=tk.X, pady=(10, 0), anchor=tk.W)

    def _build_table(self) -> None:
        """Build the main Excel-like table."""
        # Table frame
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview with spreadsheet-like appearance
        columns = ("payment_method", "expected", "actual", "variance")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

        # Configure columns
        self.tree.heading("payment_method", text="Payment Method")
        self.tree.heading("expected", text=f"Expected ({self.currency_symbol})")
        self.tree.heading("actual", text=f"Actual ({self.currency_symbol})")
        self.tree.heading("variance", text=f"Variance ({self.currency_symbol})")

        self.tree.column("payment_method", width=200, minwidth=150)
        self.tree.column("expected", width=120, minwidth=100, anchor='e')
        self.tree.column("actual", width=120, minwidth=100, anchor='e')
        self.tree.column("variance", width=120, minwidth=100, anchor='e')

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack table and scrollbars
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Bind events for Excel-like editing
        self.tree.bind('<Double-1>', self._on_double_click)
        self.tree.bind('<Return>', self._on_enter_key)
        self.tree.bind('<Delete>', self._on_delete_key)

        # Table controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, pady=(10, 0))

        # Left controls
        left_controls = ttk.Frame(controls_frame)
        left_controls.pack(side=tk.LEFT)

        ttk.Button(left_controls, text="Add Row", command=self._add_row).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_controls, text="Delete Row", command=self._delete_row).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_controls, text="Clear All", command=self._clear_all).pack(side=tk.LEFT, padx=(0, 10))

        # Right controls - totals
        totals_frame = ttk.Frame(controls_frame)
        totals_frame.pack(side=tk.RIGHT)

        ttk.Label(totals_frame, text="Total Expected:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.total_expected_var = tk.StringVar(value="0.00")
        ttk.Label(totals_frame, textvariable=self.total_expected_var,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky=tk.E, padx=(0, 15))

        ttk.Label(totals_frame, text="Total Actual:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.total_actual_var = tk.StringVar(value="0.00")
        ttk.Label(totals_frame, textvariable=self.total_actual_var,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky=tk.E, padx=(0, 15))

        ttk.Label(totals_frame, text="Total Variance:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.total_variance_var = tk.StringVar(value="0.00")
        variance_label = ttk.Label(totals_frame, textvariable=self.total_variance_var,
                                  font=("Segoe UI", 9, "bold"))
        variance_label.grid(row=0, column=5, sticky=tk.E)

        # Initialize with empty table
        self._update_totals()

    def _on_double_click(self, event) -> None:
        """Handle double-click to edit cell."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        if not item:
            return

        # Get column index
        col_idx = int(column[1:]) - 1  # #0 is payment_method, #1 is expected, etc.

        # Only allow editing actual amounts (column 2)
        if col_idx != 2:
            return

        self._edit_cell(item, col_idx)

    def _on_enter_key(self, event) -> None:
        """Handle Enter key to move to next cell or add row."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        # Move to actual column if in payment method column
        current_col = self.tree.focus()
        if current_col and current_col.startswith('#1'):  # expected column
            self.tree.focus(f"{item}#2")  # move to actual column
            self.tree.selection_set(item)
            return

        # If in actual column, add new row
        if current_col and current_col.startswith('#2'):  # actual column
            self._add_row()
            return

    def _on_delete_key(self, event) -> None:
        """Handle Delete key to clear cell or delete row."""
        selection = self.tree.selection()
        if not selection:
            return

        # If Shift+Delete, delete row; otherwise clear actual amount
        if event.state & 0x1:  # Shift key
            self._delete_row()
        else:
            item = selection[0]
            self.tree.set(item, "actual", "0.00")
            self._update_row_variance(item)
            self._update_totals()

    def _edit_cell(self, item: str, col_idx: int) -> None:
        """Edit a cell in place."""
        # Get current value
        current_value = self.tree.set(item, self.tree['columns'][col_idx])

        # Create entry widget
        x, y, width, height = self.tree.bbox(item, col_idx)
        entry = ttk.Entry(self.tree, justify='right' if col_idx > 0 else 'left')

        if col_idx > 0:  # numeric columns
            # Remove currency symbol for editing
            clean_value = current_value.replace(self.currency_symbol, '').replace(',', '').strip()
            entry.insert(0, clean_value)
        else:
            entry.insert(0, current_value)

        entry.select_range(0, tk.END)
        entry.focus()

        entry.place(x=x, y=y, width=width, height=height)

        def save_edit(event=None):
            new_value = entry.get().strip()

            if col_idx > 0:  # numeric columns
                try:
                    # Parse as float
                    num_value = float(new_value) if new_value else 0.0
                    # Format with currency
                    display_value = f"{self.currency_symbol}{num_value:,.2f}"
                    self.tree.set(item, self.tree['columns'][col_idx], display_value)

                    if col_idx == 2:  # actual column
                        self._update_row_variance(item)

                except ValueError:
                    messagebox.showerror("Invalid Input", "Please enter a valid number.")
                    entry.destroy()
                    return
            else:  # payment method column
                self.tree.set(item, self.tree['columns'][col_idx], new_value)

            entry.destroy()
            self._update_totals()

        def cancel_edit(event=None):
            entry.destroy()

        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', save_edit)

    def _update_row_variance(self, item: str) -> None:
        """Update variance for a row."""
        try:
            expected_str = self.tree.set(item, "expected").replace(self.currency_symbol, '').replace(',', '').strip()
            actual_str = self.tree.set(item, "actual").replace(self.currency_symbol, '').replace(',', '').strip()

            expected = float(expected_str) if expected_str else 0.0
            actual = float(actual_str) if actual_str else 0.0

            variance = actual - expected
            variance_str = f"{self.currency_symbol}{variance:,.2f}"
            self.tree.set(item, "variance", variance_str)

            # Color coding
            if abs(variance) < 0.01:
                self.tree.tag_configure(f"variance_{item}", background="lightgreen")
            elif variance > 0:
                self.tree.tag_configure(f"variance_{item}", background="lightyellow")
            else:
                self.tree.tag_configure(f"variance_{item}", background="lightcoral")

            self.tree.item(item, tags=(f"variance_{item}",))

        except (ValueError, TypeError):
            self.tree.set(item, "variance", f"{self.currency_symbol}0.00")

    def _update_totals(self) -> None:
        """Update total calculations."""
        total_expected = 0.0
        total_actual = 0.0
        total_variance = 0.0

        for item in self.tree.get_children():
            try:
                expected_str = self.tree.set(item, "expected").replace(self.currency_symbol, '').replace(',', '').strip()
                actual_str = self.tree.set(item, "actual").replace(self.currency_symbol, '').replace(',', '').strip()

                expected = float(expected_str) if expected_str else 0.0
                actual = float(actual_str) if actual_str else 0.0

                total_expected += expected
                total_actual += actual
                total_variance += (actual - expected)
            except (ValueError, TypeError):
                pass

        self.total_expected_var.set(f"{self.currency_symbol}{total_expected:,.2f}")
        self.total_actual_var.set(f"{self.currency_symbol}{total_actual:,.2f}")
        self.total_variance_var.set(f"{self.currency_symbol}{total_variance:,.2f}")

        # Update status
        if abs(total_variance) < 0.01:
            self.status_var.set("✓ Reconciled")
        else:
            self.status_var.set(f"Unreconciled - Variance: {self.currency_symbol}{total_variance:,.2f}")

    def _add_row(self) -> None:
        """Add a new row to the table."""
        # Common payment methods
        payment_methods = ["Cash", "Credit Card", "Debit Card", "Digital Wallet", "Check", "Gift Card"]

        # Find next available payment method
        existing_methods = [self.tree.set(item, "payment_method") for item in self.tree.get_children()]

        for method in payment_methods:
            if method not in existing_methods:
                break
        else:
            method = f"Payment Method {len(self.tree.get_children()) + 1}"

        item = self.tree.insert("", tk.END, values=(
            method,
            f"{self.currency_symbol}0.00",
            f"{self.currency_symbol}0.00",
            f"{self.currency_symbol}0.00"
        ))

        # Select the new row
        self.tree.selection_set(item)
        self._update_totals()

    def _delete_row(self) -> None:
        """Delete selected row."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a row to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Delete the selected row?"):
            for item in selection:
                self.tree.delete(item)
            self._update_totals()

    def _clear_all(self) -> None:
        """Clear all data."""
        if messagebox.askyesno("Confirm Clear", "Clear all data? This cannot be undone."):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self._update_totals()
            self.status_var.set("Data cleared")

    def _new_session(self) -> None:
        """Start a new session."""
        if self.tree.get_children() and not messagebox.askyesno("Confirm New", "Start a new session? Current data will be lost."):
            return

        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add default rows
        default_methods = ["Cash", "Credit Card", "Debit Card"]
        for method in default_methods:
            self.tree.insert("", tk.END, values=(
                method,
                f"{self.currency_symbol}0.00",
                f"{self.currency_symbol}0.00",
                f"{self.currency_symbol}0.00"
            ))

        self.date_var.set(format_date(datetime.now()))
        self._update_totals()
        self.status_var.set("New session started")

    def _load_session(self) -> None:
        """Load session from CSV."""
        file_path = filedialog.askopenfilename(
            title="Load Reconciliation",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)

            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    payment_method = row.get('Payment Method', row.get('payment_method', ''))
                    expected = row.get('Expected', row.get('expected', '0'))
                    actual = row.get('Actual', row.get('actual', '0'))

                    # Clean numeric values
                    try:
                        expected_val = float(expected.replace(self.currency_symbol, '').replace(',', '').strip())
                        actual_val = float(actual.replace(self.currency_symbol, '').replace(',', '').strip())
                        variance_val = actual_val - expected_val
                    except (ValueError, TypeError):
                        expected_val = actual_val = variance_val = 0.0

                    self.tree.insert("", tk.END, values=(
                        payment_method,
                        f"{self.currency_symbol}{expected_val:,.2f}",
                        f"{self.currency_symbol}{actual_val:,.2f}",
                        f"{self.currency_symbol}{variance_val:,.2f}"
                    ))

            self._update_totals()
            self.status_var.set(f"Loaded from {os.path.basename(file_path)}")

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load file: {str(e)}")

    def _save_session(self) -> None:
        """Save session to CSV."""
        file_path = filedialog.asksaveasfilename(
            title="Save Reconciliation",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Payment Method', 'Expected', 'Actual', 'Variance', 'Date'])

                for item in self.tree.get_children():
                    payment_method = self.tree.set(item, "payment_method")
                    expected = self.tree.set(item, "expected")
                    actual = self.tree.set(item, "actual")
                    variance = self.tree.set(item, "variance")

                    writer.writerow([payment_method, expected, actual, variance, self.date_var.get()])

            self.status_var.set(f"Saved to {os.path.basename(file_path)}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file: {str(e)}")

    def _export_csv(self) -> None:
        """Export current data to CSV."""
        self._save_session()