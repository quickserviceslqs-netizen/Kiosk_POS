"""Reconciliation UI for financial reconciliation of sales data."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import csv
import os
import re

from utils.i18n import get_currency_symbol, format_currency
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from modules import reconciliation
from modules.reconciliation import ReconciliationSession, ReconciliationEntry
from utils import set_window_icon
from utils.i18n import get_currency_symbol

logger = logging.getLogger(__name__)


class ScrollableFrame(ttk.Frame):
    """A vertical scrollable frame to contain dialog content and allow scrolling on small screens."""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.vscroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vscroll.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)


class ReconciliationDialog:
    """Main dialog for reconciliation operations."""

    def __init__(self, parent: tk.Misc, user_id: int, user_role: str = "cashier"):
        self.parent = parent
        self.user_id = user_id
        self.user_role = user_role
        self.currency_symbol = get_currency_symbol()
        self.current_session: Optional[ReconciliationSession] = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.withdraw()
        self.dialog.title("Financial Reconciliation")
        set_window_icon(self.dialog)
        # Do not set transient(owner) so the OS can show standard window decorations (min/max buttons)

        # Set size and make resizable to show min/max buttons
        self.dialog.geometry("")  # Let widgets determine size
        self.dialog.resizable(True, True)  # Allow resizing to show min/max buttons
        self.dialog.minsize(900, 750)  # Increased minimum size to ensure content fits

        self._build_ui()
        self._show_dialog()

    def _build_ui(self) -> None:
        """Build the main UI."""
        # Top controls (moved outside scrollable area so they remain visible)
        top_controls_container = ttk.Frame(self.dialog)
        top_controls_container.pack(fill=tk.X, padx=10, pady=(10, 0))
        controls_frame = ttk.Frame(top_controls_container)
        controls_frame.pack(fill=tk.X)

        # Main container with scrollable content
        scrollable = ScrollableFrame(self.dialog)
        scrollable.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        main_frame = scrollable.scrollable_frame

        # Date selection
        date_frame = ttk.LabelFrame(controls_frame, text="Reconciliation Period", padding=5)
        date_frame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(date_frame, text="Date:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        date_entry = ttk.Entry(date_frame, textvariable=self.date_var, width=12)
        date_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(date_frame, text="Period:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.period_var = tk.StringVar(value="daily")
        period_combo = ttk.Combobox(
            date_frame,
            textvariable=self.period_var,
            values=["daily", "weekly", "monthly", "yearly"],
            state="readonly",
            width=10
        )
        period_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

        # Buttons
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text="Load/Create Session", command=self._load_or_create_session).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="View History", command=self._show_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=(8,2))
        ttk.Button(btn_frame, text="Download Template", command=self._download_csv_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Import CSV", command=self._import_csv).pack(side=tk.LEFT, padx=2)

        # Update controls (always visible on top)
        # Initialize vars used by update controls
        self.selected_method_var = tk.StringVar(value='--')
        self.actual_amount_var = tk.StringVar()
        self.explanation_var = tk.StringVar()

        update_frame = ttk.Frame(top_controls_container)
        update_frame.pack(side=tk.RIGHT, padx=(0, 10))

        ttk.Label(update_frame, text="Selected:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(update_frame, textvariable=self.selected_method_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=(5, 10))

        ttk.Label(update_frame, text="Actual:").grid(row=0, column=2, sticky=tk.W)
        self.actual_entry = ttk.Entry(update_frame, textvariable=self.actual_amount_var, width=12)
        self.actual_entry.grid(row=0, column=3, sticky=tk.W, padx=(5, 10))
        # Press Enter to save quick updates
        self.actual_entry.bind("<Return>", lambda e: self._update_selected_entry())

        ttk.Label(update_frame, text="Explanation:").grid(row=0, column=4, sticky=tk.W)
        self.explanation_entry = ttk.Entry(update_frame, textvariable=self.explanation_var, width=30)
        self.explanation_entry.grid(row=0, column=5, sticky=tk.W, padx=(5, 10))
        # Press Enter in explanation to also save
        self.explanation_entry.bind("<Return>", lambda e: self._update_selected_entry())

        ttk.Button(update_frame, text="Update Selected", command=self._update_selected_entry).grid(row=0, column=6, sticky=tk.E)

        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Sales Summary
        left_panel = ttk.LabelFrame(content_frame, text="Sales Summary", padding=5)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # Summary labels
        self.summary_vars = {}
        summary_fields = [
            ("Period", "period"),
            ("System Sales", "system_sales"),
            ("Actual Cash", "actual_cash"),
            ("Variance", "variance")
        ]

        for i, (label, key) in enumerate(summary_fields):
            ttk.Label(left_panel, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar(value="--")
            self.summary_vars[key] = var
            ttk.Label(left_panel, textvariable=var, font=("Segoe UI", 10, "bold")).grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Right panel - Payment Methods
        right_panel = ttk.LabelFrame(content_frame, text="Payment Method Breakdown", padding=5)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Treeview for payment methods
        columns = ("payment_method", "system_amount", "actual_amount", "variance", "status")
        self.tree = ttk.Treeview(right_panel, columns=columns, show="headings", height=15)
        self.tree.heading("payment_method", text="Payment Method")
        self.tree.heading("system_amount", text="System Amount")
        self.tree.heading("actual_amount", text="Actual Amount")
        self.tree.heading("variance", text="Variance")
        self.tree.heading("status", text="Status")

        self.tree.column("payment_method", width=150)
        self.tree.column("system_amount", width=120, anchor=tk.E)
        self.tree.column("actual_amount", width=120, anchor=tk.E)
        self.tree.column("variance", width=100, anchor=tk.E)
        self.tree.column("status", width=80, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Note: Entry controls were moved to the fixed top area so they remain visible
        # The controls previously defined here are intentionally removed to avoid duplication
        pass

        # Bottom panel - Notes and Actions (fixed footer)
        bottom_frame = ttk.LabelFrame(self.dialog, text="Notes & Actions", padding=5)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 10))

        # Notes
        ttk.Label(bottom_frame, text="Notes:").pack(anchor=tk.W)
        self.notes_text = scrolledtext.ScrolledText(bottom_frame, height=3, wrap=tk.WORD)
        self.notes_text.pack(fill=tk.X, pady=(0, 10))

        # Action buttons
        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(fill=tk.X)

        # Give the action buttons a bit of padding and allow wrap if needed
        ttk.Button(action_frame, text="Save Draft", command=self._save_draft).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(action_frame, text="Complete Reconciliation", command=self._complete_reconciliation).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(action_frame, text="Add Explanation", command=self._add_explanation).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(action_frame, text="Close", command=self._on_close).pack(side=tk.RIGHT, padx=4, pady=4)

        # Bind tree selection and double-click to edit
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _load_or_create_session(self) -> None:
        """Load existing session or create new one."""
        try:
            date_str = self.date_var.get()
            period_type = self.period_var.get()

            # Calculate date range
            start_date, end_date = reconciliation.calculate_date_range(period_type, date_str)

            # Check if session already exists
            existing_sessions = reconciliation.get_reconciliation_sessions(
                start_date=start_date,
                end_date=end_date,
                status=None
            )

            if existing_sessions:
                # Load the most recent session
                session_id = existing_sessions[0]['session_id']
                self.current_session = reconciliation.get_reconciliation_session(session_id)
                messagebox.showinfo("Session Loaded", f"Loaded existing reconciliation session for {period_type} period.", parent=self.dialog)
            else:
                # Create new session
                session_id = reconciliation.create_reconciliation_session(
                    date_str, period_type, start_date, end_date, self.user_id
                )
                self.current_session = reconciliation.get_reconciliation_session(session_id)
                messagebox.showinfo("Session Created", f"Created new reconciliation session for {period_type} period.", parent=self.dialog)

            self._refresh_display()

            # Auto-select the first payment method and pre-fill top update controls
            first = next(iter(self.tree.get_children()), None)
            if first:
                self.tree.selection_set(first)
                self.tree.see(first)
                self._on_tree_select(None)

        except Exception as e:
            logger.error(f"Error loading/creating session: {e}")
            messagebox.showerror("Error", f"Failed to load/create session: {e}", parent=self.dialog)

    def _refresh_display(self) -> None:
        """Refresh the display with current session data."""
        if not self.current_session:
            return

        # Update summary
        self.summary_vars["period"].set(f"{self.current_session.start_date} to {self.current_session.end_date}")
        self.summary_vars["system_sales"].set(format_currency(self.current_session.total_system_sales))
        self.summary_vars["actual_cash"].set(format_currency(self.current_session.total_actual_cash))
        self.summary_vars["variance"].set(format_currency(self.current_session.total_variance))

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add entries to tree
        for entry in self.current_session.entries:
            status = "✓" if abs(entry.variance) < 0.01 else "⚠"
            variance_color = "red" if entry.variance != 0 else "green"

            item_id = self.tree.insert("", tk.END, values=(
                entry.payment_method,
                format_currency(entry.system_amount),
                format_currency(entry.actual_amount),
                format_currency(entry.variance),
                status
            ))

            # Color the variance column
            if entry.variance != 0:
                self.tree.tag_configure(f"variance_{item_id}", foreground=variance_color)
                self.tree.item(item_id, tags=(f"variance_{item_id}",))

        # Update notes
        self.notes_text.delete(1.0, tk.END)
        if self.current_session.notes:
            self.notes_text.insert(1.0, self.current_session.notes)

    def _on_tree_select(self, event) -> None:
        """Handle tree selection."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            values = item['values']
            if len(values) >= 4:
                # Update selected payment method label
                self.selected_method_var.set(values[0])

                # Pre-fill actual amount and explanation
                # Remove any non-numeric characters to parse amount (handles different currency symbols/formats)
                actual_str = re.sub(r"[^\d\.\-]", "", str(values[2]))
                try:
                    actual_amount = float(actual_str)
                    self.actual_amount_var.set(f"{actual_amount:.2f}")
                except (ValueError, IndexError):
                    self.actual_amount_var.set("")

                # Find explanation for this payment method
                if self.current_session:
                    for entry in self.current_session.entries:
                        if entry.payment_method == values[0]:
                            self.explanation_var.set(entry.explanation)
                            break

    def _update_selected_entry(self) -> None:
        """Update the selected entry with new actual amount and explanation."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.", parent=self.dialog)
            return

        # Prefer selected_method_var if set, otherwise use tree selection
        payment_method = None
        if self.selected_method_var.get() and self.selected_method_var.get() != '--':
            payment_method = self.selected_method_var.get()
        else:
            selection = self.tree.selection()
            if selection:
                item = self.tree.item(selection[0])
                payment_method = item['values'][0]

        if not payment_method:
            messagebox.showwarning("No Selection", "Please select a payment method to update.", parent=self.dialog)
            return

        try:
            actual_amount = float(self.actual_amount_var.get() or 0)
            explanation = self.explanation_var.get().strip()

            reconciliation.update_reconciliation_entry(
                self.current_session.session_id,
                payment_method,
                actual_amount,
                explanation
            )

            # Reload session data and refresh UI
            self.current_session = reconciliation.get_reconciliation_session(self.current_session.session_id)
            self._refresh_display()

            # Keep the selection on the updated method
            for iid in self.tree.get_children():
                vals = self.tree.item(iid)['values']
                if vals and vals[0] == payment_method:
                    self.tree.selection_set(iid)
                    self.tree.see(iid)
                    break

            messagebox.showinfo("Updated", f"Updated {payment_method} reconciliation entry.", parent=self.dialog)

        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid number for the actual amount.", parent=self.dialog)
        except Exception as e:
            logger.error(f"Error updating entry: {e}")
            messagebox.showerror("Error", f"Failed to update entry: {e}", parent=self.dialog)

    def _export_csv(self) -> None:
        """Export current session entries to CSV."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.", parent=self.dialog)
            return

        suggested = f"reconciliation_{self.current_session.start_date}_{self.current_session.end_date}.csv"
        filename = filedialog.asksaveasfilename(parent=self.dialog, defaultextension='.csv', filetypes=[('CSV files', '*.csv')], initialfile=suggested)
        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['payment_method', 'system_amount', 'actual_amount', 'variance', 'explanation'])
                for entry in self.current_session.entries:
                    writer.writerow([
                        entry.payment_method,
                        f"{entry.system_amount:.2f}",
                        f"{entry.actual_amount:.2f}",
                        f"{entry.variance:.2f}",
                        entry.explanation or ''
                    ])
            messagebox.showinfo("Exported", f"Reconciliation exported to {os.path.basename(filename)}", parent=self.dialog)
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            messagebox.showerror("Error", f"Failed to export CSV: {e}", parent=self.dialog)

    def _import_csv(self) -> None:
        """Import actual amounts from CSV and update session entries.

        Expects CSV with columns: payment_method, actual_amount, explanation (optional)
        """
        if not self.current_session:
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.", parent=self.dialog)
            return

        filename = filedialog.askopenfilename(parent=self.dialog, filetypes=[('CSV files', '*.csv')])
        if not filename:
            return

        updated = 0
        skipped = 0
        errors = []
        preview_rows = []

        try:
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pm = (row.get('payment_method') or '').strip()
                    amt_str = (row.get('actual_amount') or '').strip()
                    expl = (row.get('explanation') or '').strip()
                    preview_rows.append({'payment_method': pm, 'actual_amount': amt_str, 'explanation': expl})

            # Ask user to confirm import (show count and sample)
            total_rows = len(preview_rows)
            sample = "\n".join([f"{r['payment_method']}: {r['actual_amount']} ({r['explanation']})" for r in preview_rows[:5]])
            confirm = messagebox.askyesno("Confirm Import", f"Found {total_rows} rows in CSV. Sample:\n\n{sample}\n\nProceed to import?", parent=self.dialog)
            if not confirm:
                return

            # Proceed with applying the rows
            for r in preview_rows:
                pm = r['payment_method']
                amt_str = r['actual_amount']
                expl = r['explanation']

                if not pm:
                    skipped += 1
                    continue
                try:
                    actual_amount = float(amt_str) if amt_str != '' else 0.0
                except ValueError:
                    errors.append(f"Invalid amount for {pm}: '{amt_str}'")
                    continue

                exists = any(e.payment_method == pm for e in self.current_session.entries)
                if exists:
                    reconciliation.update_reconciliation_entry(self.current_session.session_id, pm, actual_amount, expl)
                    updated += 1
                else:
                    skipped += 1

            # Refresh session
            self.current_session = reconciliation.get_reconciliation_session(self.current_session.session_id)
            self._refresh_display()

            msg_parts = [f"Updated: {updated}", f"Skipped: {skipped}"]
            if errors:
                msg_parts.append("Errors:\n" + "\n".join(errors))
            messagebox.showinfo("Import Complete", "\n".join(msg_parts), parent=self.dialog)
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            messagebox.showerror("Error", f"Failed to import CSV: {e}", parent=self.dialog)

    def _download_csv_template(self) -> None:
        """Write a CSV template file with headers and examples."""
        suggested = "reconciliation_template.csv"
        filename = filedialog.asksaveasfilename(parent=self.dialog, defaultextension='.csv', filetypes=[('CSV files', '*.csv')], initialfile=suggested)
        if not filename:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                # Write guidance as commented header lines for user clarity
                f.write('# CSV Import Guidelines\n')
                f.write('# Columns: payment_method (required), system_amount (informational), actual_amount (required), explanation (optional)\n')
                f.write('# Currency: {}\n'.format(get_currency_symbol()))
                f.write('# Ensure payment_method matches the payment methods in the current session.\n')
                f.write('# actual_amount should be numeric (decimals allowed). Leave blank for 0.\n')
                f.write('# Rows with unknown payment_method will be skipped during import.\n')
                f.write('# Example row follows the header.\n\n')

                writer = csv.writer(f)
                writer.writerow(['payment_method', 'system_amount', 'actual_amount', 'explanation'])
                # Example rows (system_amount should match system breakdown; actual_amount is what user will fill)
                writer.writerow(['Cash', '1500.00', '1500.00', 'Counted cash at close'])
                writer.writerow(['Card - Visa', '1200.00', '1198.00', 'Net after fees'])
                writer.writerow(['Mobile Pay', '200.00', '200.00', ''])
            messagebox.showinfo("Template Saved", f"CSV template saved to {os.path.basename(filename)}", parent=self.dialog)
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            messagebox.showerror("Error", f"Failed to save template: {e}", parent=self.dialog)



    def _save_draft(self) -> None:
        """Save the current session as draft."""
        if not self.current_session:
            return

        try:
            notes = self.notes_text.get(1.0, tk.END).strip()
            # Update notes in database
            with reconciliation.get_connection() as conn:
                conn.execute(
                    "UPDATE reconciliation_sessions SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (notes, self.current_session.session_id)
                )
                conn.commit()

            messagebox.showinfo("Saved", "Reconciliation draft saved successfully.", parent=self.dialog)
        except Exception as e:
            logger.error(f"Error saving draft: {e}")
            messagebox.showerror("Error", f"Failed to save draft: {e}", parent=self.dialog)

    def _complete_reconciliation(self) -> None:
        """Complete the reconciliation."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.", parent=self.dialog)
            return

        if abs(self.current_session.total_variance) > 0.01:
            result = messagebox.askyesno(
                "Variance Detected",
                f"There is a variance of {format_currency(self.current_session.total_variance)}. Do you want to complete the reconciliation anyway?",
                parent=self.dialog
            )
            if not result:
                return

        try:
            notes = self.notes_text.get(1.0, tk.END).strip()
            reconciliation.complete_reconciliation_session(
                self.current_session.session_id,
                self.user_id,
                notes
            )

            messagebox.showinfo("Completed", "Reconciliation completed successfully.", parent=self.dialog)
            self._on_close()

        except Exception as e:
            logger.error(f"Error completing reconciliation: {e}")
            messagebox.showerror("Error", f"Failed to complete reconciliation: {e}", parent=self.dialog)

    def _add_explanation(self) -> None:
        """Add a general explanation."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.", parent=self.dialog)
            return

        dialog = ExplanationDialog(self.dialog, self.current_session.session_id, self.user_id)
        # Removed wait_window to prevent Tkinter window path errors

    def _on_tree_double_click(self, event) -> None:
        """Open an edit dialog for the double-clicked payment method."""
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])
        values = item['values']
        if not values:
            return
        payment_method = values[0]

        # Find existing entry
        entry = None
        if self.current_session:
            for e in self.current_session.entries:
                if e.payment_method == payment_method:
                    entry = e
                    break

        # Open edit dialog
        edit = EditEntryDialog(self.dialog, self.current_session.session_id, payment_method, entry.actual_amount if entry else 0.0, entry.explanation if entry else "", on_save=self._on_edit_saved)

    def _on_edit_saved(self, payment_method: str) -> None:
        """Callback after an edit dialog saves - reload session and refresh UI."""
        try:
            self.current_session = reconciliation.get_reconciliation_session(self.current_session.session_id)
            self._refresh_display()
            # Set selection to the updated row
            for iid in self.tree.get_children():
                vals = self.tree.item(iid)['values']
                if vals and vals[0] == payment_method:
                    self.tree.selection_set(iid)
                    self.tree.see(iid)
                    break
            messagebox.showinfo("Updated", f"Updated {payment_method} reconciliation entry.", parent=self.dialog)
        except Exception as e:
            logger.error(f"Error refreshing after edit: {e}")
            messagebox.showerror("Error", f"Failed to refresh after editing entry: {e}", parent=self.dialog)

    def _show_history(self) -> None:
        """Show reconciliation history."""
        history_dialog = ReconciliationHistoryDialog(self.dialog)
        # Removed wait_window to prevent Tkinter window path errors

    def _on_close(self) -> None:
        """Handle dialog close."""
        self.dialog.destroy()

    def _show_dialog(self) -> None:
        """Show the dialog and center it on screen."""
        # Ensure all widgets are fully realized
        self.dialog.update()

        req_width = self.dialog.winfo_reqwidth()
        req_height = self.dialog.winfo_reqheight()

        # Add padding and minimum sizes
        width = max(req_width + 60, 950)
        height = max(req_height + 120, 800)

        # Clamp to screen size with margins
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        margin = 80
        width = min(width, screen_w - margin)
        height = min(height, screen_h - margin)

        # Center the dialog
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

        self.dialog.deiconify()
        self.dialog.grab_set()
        # Do not block UI loop in tests; wait_window will be handled by callers when appropriate
        try:
            self.dialog.wait_window()
        except tk.TclError:
            # In certain test contexts window path may be destroyed before wait_window returns
            pass


class ExplanationDialog:
    """Dialog for adding explanations to reconciliation."""

    def __init__(self, parent: tk.Misc, session_id: int, user_id: int):
        self.parent = parent
        self.session_id = session_id
        self.user_id = user_id

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Explanation")
        set_window_icon(self.dialog)
        self.dialog.transient(parent)
        self.dialog.resizable(True, True)  # Allow resizing to show min/max buttons
        self.dialog.minsize(550, 400)  # Increased minimum size

        self._build_ui()
        self._show_dialog()


class EditEntryDialog:
    """Small dialog to edit actual amount and explanation for a payment method."""

    def __init__(self, parent: tk.Misc, session_id: int, payment_method: str, actual_amount: float = 0.0, explanation: str = "", on_save=None):
        self.parent = parent
        self.session_id = session_id
        self.payment_method = payment_method
        self.on_save = on_save

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit: {payment_method}")
        set_window_icon(self.dialog)
        # Make this dialog transient and modal to the parent reconciliation dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.minsize(420, 140)

        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"Payment Method:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame, text=payment_method).grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        ttk.Label(frame, text="Actual Amount:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.actual_var = tk.StringVar(value=f"{actual_amount:.2f}")
        self.actual_entry = ttk.Entry(frame, textvariable=self.actual_var, width=20)
        self.actual_entry.grid(row=1, column=1, sticky=tk.W, pady=(8, 0), padx=(5, 0))

        ttk.Label(frame, text="Explanation:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self.expl_var = tk.StringVar(value=explanation)
        self.expl_entry = ttk.Entry(frame, textvariable=self.expl_var, width=40)
        self.expl_entry.grid(row=2, column=1, sticky=tk.W, pady=(8, 0), padx=(5, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(12, 0), sticky=tk.EW)
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=(0, 4))
        ttk.Button(btn_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)

        # Bind Enter to save, Escape to cancel
        self.actual_entry.bind("<Return>", lambda e: self._save())
        self.expl_entry.bind("<Return>", lambda e: self._save())
        self.dialog.bind("<Escape>", lambda e: self._cancel())

        # Focus the actual entry
        self.actual_entry.focus_set()

        self._show_dialog()

    def _save(self) -> None:
        """Save the edited actual and explanation."""
        try:
            # Validate amount
            try:
                actual_amount = float(self.actual_var.get() or 0)
            except ValueError:
                messagebox.showerror("Invalid Amount", "Please enter a valid number for actual amount.", parent=self.dialog)
                return

            explanation = self.expl_var.get().strip()

            reconciliation.update_reconciliation_entry(
                self.session_id,
                self.payment_method,
                actual_amount,
                explanation
            )

            # Close dialog and callback
            self.dialog.destroy()
            if callable(self.on_save):
                # Notify parent
                self.on_save(self.payment_method)
        except Exception as e:
            logger.error(f"Error saving edited entry: {e}")
            messagebox.showerror("Error", f"Failed to save entry: {e}", parent=self.dialog)

    def _cancel(self) -> None:
        """Cancel the edit dialog."""
        self.dialog.destroy()

    def _build_ui(self) -> None:
        """Build the explanation dialog UI."""
        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Explanation Type:").pack(anchor=tk.W, pady=(0, 5))
        self.type_var = tk.StringVar(value="general")
        type_combo = ttk.Combobox(
            frame,
            textvariable=self.type_var,
            values=["general", "payment_method", "variance"],
            state="readonly"
        )
        type_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Payment Method (optional):").pack(anchor=tk.W, pady=(0, 5))
        self.payment_method_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.payment_method_var).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Amount (optional):").pack(anchor=tk.W, pady=(0, 5))
        self.amount_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.amount_var).pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Explanation:").pack(anchor=tk.W, pady=(0, 5))
        self.explanation_text = scrolledtext.ScrolledText(frame, height=5, wrap=tk.WORD)
        self.explanation_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)

    def _save(self) -> None:
        """Save the explanation."""
        try:
            explanation_type = self.type_var.get()
            payment_method = self.payment_method_var.get().strip() or None
            explanation = self.explanation_text.get(1.0, tk.END).strip()

            if not explanation:
                messagebox.showwarning("Missing Explanation", "Please enter an explanation.", parent=self.dialog)
                return

            amount = 0.0
            if self.amount_var.get().strip():
                try:
                    amount = float(self.amount_var.get().strip())
                except ValueError:
                    messagebox.showerror("Invalid Amount", "Please enter a valid number for amount.", parent=self.dialog)
                    return

            reconciliation.add_reconciliation_explanation(
                self.session_id,
                explanation_type,
                explanation,
                payment_method,
                amount,
                self.user_id
            )

            messagebox.showinfo("Saved", "Explanation added successfully.", parent=self.dialog)
            self.dialog.destroy()

        except Exception as e:
            logger.error(f"Error saving explanation: {e}")
            messagebox.showerror("Error", f"Failed to save explanation: {e}", parent=self.dialog)

    def _cancel(self) -> None:
        """Cancel the dialog."""
        self.dialog.destroy()

    def _show_dialog(self) -> None:
        """Show the dialog and center it on screen."""
        # Ensure all widgets are fully realized
        self.dialog.update()

        req_width = self.dialog.winfo_reqwidth()
        req_height = self.dialog.winfo_reqheight()

        # Add padding and minimum sizes
        width = max(req_width + 30, 550)
        height = max(req_height + 50, 400)

        # Clamp to screen size with margins
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        margin = 80
        width = min(width, screen_w - margin)
        height = min(height, screen_h - margin)

        # Center the dialog
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

        self.dialog.deiconify()
        self.dialog.grab_set()
        self.dialog.wait_window()


class ReconciliationHistoryDialog:
    """Dialog to show reconciliation history."""

    def __init__(self, parent: tk.Misc):
        self.parent = parent

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Reconciliation History")
        set_window_icon(self.dialog)
        self.dialog.transient(parent)
        self.dialog.resizable(True, True)  # Allow resizing to show min/max buttons
        self.dialog.minsize(1100, 700)  # Increased minimum size

        self._build_ui()
        self._load_history()
        self._show_dialog()

    def _build_ui(self) -> None:
        """Build the history dialog UI."""
        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Filters
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="Start Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.start_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        ttk.Entry(filter_frame, textvariable=self.start_date_var, width=12).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(filter_frame, text="End Date:").pack(side=tk.LEFT, padx=(0, 5))
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(filter_frame, textvariable=self.end_date_var, width=12).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        self.status_var = tk.StringVar(value="")
        status_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.status_var,
            values=["", "draft", "completed", "approved"],
            state="readonly",
            width=10
        )
        status_combo.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(filter_frame, text="Filter", command=self._load_history).pack(side=tk.LEFT)

        # Treeview
        columns = ("date", "period", "system_sales", "actual_cash", "variance", "status", "reconciled_by")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        self.tree.heading("date", text="Date")
        self.tree.heading("period", text="Period")
        self.tree.heading("system_sales", text="System Sales")
        self.tree.heading("actual_cash", text="Actual Cash")
        self.tree.heading("variance", text="Variance")
        self.tree.heading("status", text="Status")
        self.tree.heading("reconciled_by", text="Reconciled By")

        self.tree.column("date", width=100)
        self.tree.column("period", width=100)
        self.tree.column("system_sales", width=120, anchor=tk.E)
        self.tree.column("actual_cash", width=120, anchor=tk.E)
        self.tree.column("variance", width=100, anchor=tk.E)
        self.tree.column("status", width=100, anchor=tk.CENTER)
        self.tree.column("reconciled_by", width=120)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Close button
        ttk.Button(frame, text="Close", command=self._close).pack(pady=(10, 0))

    def _load_history(self) -> None:
        """Load reconciliation history."""
        try:
            start_date = self.start_date_var.get() or None
            end_date = self.end_date_var.get() or None
            status = self.status_var.get() or None

            sessions = reconciliation.get_reconciliation_sessions(
                start_date=start_date,
                end_date=end_date,
                status=status if status else None
            )

            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)

            currency_symbol = get_currency_symbol()

            # Add sessions to tree
            for session in sessions:
                status_display = session['status'].title()
                variance_color = "red" if session['total_variance'] != 0 else "green"

                item_id = self.tree.insert("", tk.END, values=(
                    session['reconciliation_date'],
                    f"{session['period_type'].title()} ({session['start_date']} - {session['end_date']})",
                    f"{currency_symbol}{session['total_system_sales']:.2f}",
                    f"{currency_symbol}{session['total_actual_cash']:.2f}",
                    f"{currency_symbol}{session['total_variance']:.2f}",
                    status_display,
                    session.get('reconciled_by_name', 'Unknown')
                ))

                # Color variance column
                if session['total_variance'] != 0:
                    self.tree.tag_configure(f"variance_{item_id}", foreground=variance_color)
                    self.tree.item(item_id, tags=(f"variance_{item_id}",))

        except Exception as e:
            logger.error(f"Error loading history: {e}")
            messagebox.showerror("Error", f"Failed to load reconciliation history: {e}", parent=self.dialog)

    def _close(self) -> None:
        """Close the dialog."""
        self.dialog.destroy()

    def _show_dialog(self) -> None:
        """Show the dialog and center it on screen."""
        # Ensure all widgets are fully realized
        self.dialog.update()

        req_width = self.dialog.winfo_reqwidth()
        req_height = self.dialog.winfo_reqheight()

        # Add padding and minimum sizes
        width = max(req_width + 50, 1100)
        height = max(req_height + 80, 700)

        # Clamp to screen size with margins
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        margin = 80
        width = min(width, screen_w - margin)
        height = min(height, screen_h - margin)

        # Center the dialog
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

        self.dialog.deiconify()
        self.dialog.grab_set()
        self.dialog.wait_window()