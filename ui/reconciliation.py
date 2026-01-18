"""Reconciliation UI for financial reconciliation of sales data."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

from modules import reconciliation
from modules.reconciliation import ReconciliationSession, ReconciliationEntry
from utils import set_window_icon
from utils.i18n import get_currency_symbol

logger = logging.getLogger(__name__)


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
        self.dialog.transient(parent)

        # Set size and make resizable to show min/max buttons
        self.dialog.geometry("")  # Let widgets determine size
        self.dialog.resizable(True, True)  # Allow resizing to show min/max buttons
        self.dialog.minsize(900, 750)  # Increased minimum size to ensure content fits

        self._build_ui()
        self._show_dialog()

    def _build_ui(self) -> None:
        """Build the main UI."""
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

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
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="Load/Create Session", command=self._load_or_create_session).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="View History", command=self._show_history).pack(side=tk.LEFT, padx=2)

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

        # Entry controls below tree
        entry_frame = ttk.Frame(right_panel)
        entry_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(entry_frame, text="Actual Amount:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.actual_amount_var = tk.StringVar()
        ttk.Entry(entry_frame, textvariable=self.actual_amount_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)

        ttk.Label(entry_frame, text="Explanation:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.explanation_var = tk.StringVar()
        ttk.Entry(entry_frame, textvariable=self.explanation_var, width=40).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)

        ttk.Button(entry_frame, text="Update Selected", command=self._update_selected_entry).grid(row=0, column=2, rowspan=2, padx=(10, 0))

        # Bottom panel - Notes and Actions
        bottom_frame = ttk.LabelFrame(main_frame, text="Notes & Actions", padding=5)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        # Notes
        ttk.Label(bottom_frame, text="Notes:").pack(anchor=tk.W)
        self.notes_text = scrolledtext.ScrolledText(bottom_frame, height=3, wrap=tk.WORD)
        self.notes_text.pack(fill=tk.X, pady=(0, 10))

        # Action buttons
        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(fill=tk.X)

        ttk.Button(action_frame, text="Save Draft", command=self._save_draft).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Complete Reconciliation", command=self._complete_reconciliation).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Add Explanation", command=self._add_explanation).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Close", command=self._on_close).pack(side=tk.RIGHT, padx=2)

        # Bind tree selection
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

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
                messagebox.showinfo("Session Loaded", f"Loaded existing reconciliation session for {period_type} period.")
            else:
                # Create new session
                session_id = reconciliation.create_reconciliation_session(
                    date_str, period_type, start_date, end_date, self.user_id
                )
                self.current_session = reconciliation.get_reconciliation_session(session_id)
                messagebox.showinfo("Session Created", f"Created new reconciliation session for {period_type} period.")

            self._refresh_display()

        except Exception as e:
            logger.error(f"Error loading/creating session: {e}")
            messagebox.showerror("Error", f"Failed to load/create session: {e}")

    def _refresh_display(self) -> None:
        """Refresh the display with current session data."""
        if not self.current_session:
            return

        # Update summary
        self.summary_vars["period"].set(f"{self.current_session.start_date} to {self.current_session.end_date}")
        self.summary_vars["system_sales"].set(f"{self.currency_symbol}{self.current_session.total_system_sales:.2f}")
        self.summary_vars["actual_cash"].set(f"{self.currency_symbol}{self.current_session.total_actual_cash:.2f}")
        self.summary_vars["variance"].set(f"{self.currency_symbol}{self.current_session.total_variance:.2f}")

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add entries to tree
        for entry in self.current_session.entries:
            status = "✓" if abs(entry.variance) < 0.01 else "⚠"
            variance_color = "red" if entry.variance != 0 else "green"

            item_id = self.tree.insert("", tk.END, values=(
                entry.payment_method,
                f"{self.currency_symbol}{entry.system_amount:.2f}",
                f"{self.currency_symbol}{entry.actual_amount:.2f}",
                f"{self.currency_symbol}{entry.variance:.2f}",
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
                # Pre-fill actual amount and explanation
                actual_str = values[2].replace(self.currency_symbol, "").replace(",", "")
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
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.")
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a payment method to update.")
            return

        try:
            actual_amount = float(self.actual_amount_var.get() or 0)
            explanation = self.explanation_var.get().strip()

            item = self.tree.item(selection[0])
            payment_method = item['values'][0]

            reconciliation.update_reconciliation_entry(
                self.current_session.session_id,
                payment_method,
                actual_amount,
                explanation
            )

            # Reload session data
            self.current_session = reconciliation.get_reconciliation_session(self.current_session.session_id)
            self._refresh_display()

            messagebox.showinfo("Updated", f"Updated {payment_method} reconciliation entry.")

        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid number for the actual amount.")
        except Exception as e:
            logger.error(f"Error updating entry: {e}")
            messagebox.showerror("Error", f"Failed to update entry: {e}")

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

            messagebox.showinfo("Saved", "Reconciliation draft saved successfully.")
        except Exception as e:
            logger.error(f"Error saving draft: {e}")
            messagebox.showerror("Error", f"Failed to save draft: {e}")

    def _complete_reconciliation(self) -> None:
        """Complete the reconciliation."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.")
            return

        if abs(self.current_session.total_variance) > 0.01:
            result = messagebox.askyesno(
                "Variance Detected",
                f"There is a variance of {self.currency_symbol}{self.current_session.total_variance:.2f}. Do you want to complete the reconciliation anyway?"
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

            messagebox.showinfo("Completed", "Reconciliation completed successfully.")
            self._on_close()

        except Exception as e:
            logger.error(f"Error completing reconciliation: {e}")
            messagebox.showerror("Error", f"Failed to complete reconciliation: {e}")

    def _add_explanation(self) -> None:
        """Add a general explanation."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please load or create a reconciliation session first.")
            return

        dialog = ExplanationDialog(self.dialog, self.current_session.session_id, self.user_id)
        # Removed wait_window to prevent Tkinter window path errors

    def _show_history(self) -> None:
        """Show reconciliation history."""
        history_dialog = ReconciliationHistoryDialog(self.dialog)
        # Removed wait_window to prevent Tkinter window path errors

    def _on_close(self) -> None:
        """Handle dialog close."""
        self.dialog.destroy()

    def _show_dialog(self) -> None:
        """Show the dialog."""
        # Update geometry to fit content with adequate size
        self.dialog.update_idletasks()

        # Force a second update to ensure all widgets are properly sized
        self.dialog.update_idletasks()

        req_width = self.dialog.winfo_reqwidth()
        req_height = self.dialog.winfo_reqheight()

        # Ensure adequate dimensions to show all content with extra padding
        width = max(req_width + 50, 950)  # Add padding and minimum width
        height = max(req_height + 100, 800)  # Add more padding for bottom content

        self.dialog.geometry(f"{width}x{height}")

        self.dialog.deiconify()
        self.dialog.grab_set()
        self.dialog.wait_window()


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
                messagebox.showwarning("Missing Explanation", "Please enter an explanation.")
                return

            amount = 0.0
            if self.amount_var.get().strip():
                try:
                    amount = float(self.amount_var.get().strip())
                except ValueError:
                    messagebox.showerror("Invalid Amount", "Please enter a valid number for amount.")
                    return

            reconciliation.add_reconciliation_explanation(
                self.session_id,
                explanation_type,
                explanation,
                payment_method,
                amount,
                self.user_id
            )

            messagebox.showinfo("Saved", "Explanation added successfully.")
            self.dialog.destroy()

        except Exception as e:
            logger.error(f"Error saving explanation: {e}")
            messagebox.showerror("Error", f"Failed to save explanation: {e}")

    def _cancel(self) -> None:
        """Cancel the dialog."""
        self.dialog.destroy()

    def _show_dialog(self) -> None:
        """Show the dialog."""
        # Update geometry to fit content
        self.dialog.update_idletasks()
        self.dialog.update_idletasks()  # Force second update

        req_width = self.dialog.winfo_reqwidth()
        req_height = self.dialog.winfo_reqheight()

        # Ensure adequate dimensions with padding
        width = max(req_width + 30, 550)
        height = max(req_height + 50, 400)

        self.dialog.geometry(f"{width}x{height}")

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
            messagebox.showerror("Error", f"Failed to load reconciliation history: {e}")

    def _close(self) -> None:
        """Close the dialog."""
        self.dialog.destroy()

    def _show_dialog(self) -> None:
        """Show the dialog."""
        # Update geometry to fit content
        self.dialog.update_idletasks()
        self.dialog.update_idletasks()  # Force second update

        req_width = self.dialog.winfo_reqwidth()
        req_height = self.dialog.winfo_reqheight()

        # Ensure adequate dimensions with padding
        width = max(req_width + 50, 1100)
        height = max(req_height + 80, 700)

        self.dialog.geometry(f"{width}x{height}")

        self.dialog.deiconify()
        self.dialog.grab_set()
        self.dialog.wait_window()