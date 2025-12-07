"""Expense tracking UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from modules import expenses


class ExpensesFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.tree = None
        self.search_category = tk.StringVar(value="")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Expense Tracking", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="← Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Add Expense", command=self._add_expense).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="View Report", command=self._view_report).pack(side=tk.RIGHT, padx=4)

        # Filters
        filters = ttk.Frame(self)
        filters.grid(row=1, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(filters, text="Filter by Category:").pack(side=tk.LEFT, padx=4)
        ttk.Entry(filters, textvariable=self.search_category, width=20).pack(side=tk.LEFT, padx=4)
        ttk.Button(filters, text="Search", command=self.refresh).pack(side=tk.LEFT, padx=4)
        ttk.Button(filters, text="Clear", command=self._clear_filter).pack(side=tk.LEFT, padx=4)

        # Tree view
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=2, column=0, sticky=tk.NSEW, pady=(0, 8))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("date", "category", "amount", "description", "user"),
            show="headings",
            height=15
        )
        self.tree.heading("date", text="Date")
        self.tree.heading("category", text="Category")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("description", text="Description")
        self.tree.heading("user", text="Created By")
        self.tree.column("date", width=100, anchor=tk.W)
        self.tree.column("category", width=120, anchor=tk.W)
        self.tree.column("amount", width=100, anchor=tk.E)
        self.tree.column("description", width=250, anchor=tk.W)
        self.tree.column("user", width=120, anchor=tk.W)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscroll=scroll.set)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Button(btn_frame, text="Edit", command=self._edit_expense_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._delete_expense_checked).pack(side=tk.LEFT, padx=2)

        # Summary
        summary_frame = ttk.Frame(self)
        summary_frame.grid(row=4, column=0, sticky=tk.EW, pady=(8, 0))
        self.total_label = ttk.Label(summary_frame, text="Total Expenses: 0.00", font=("Segoe UI", 10, "bold"))
        self.total_label.pack(side=tk.LEFT, padx=4)
        self.count_label = ttk.Label(summary_frame, text="Count: 0")
        self.count_label.pack(side=tk.LEFT, padx=12)

    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        category_filter = self.search_category.get().strip() or None
        expense_list = expenses.list_expenses(category=category_filter)
        
        total = 0.0
        for exp in expense_list:
            user_display = exp.get("username", "N/A")
            created_at = exp.get("created_at", "")
            if created_at:
                # Show username with timestamp
                user_display = f"{user_display} ({created_at[:16]})"
            
            self.tree.insert(
                "",
                tk.END,
                iid=str(exp["expense_id"]),
                values=(
                    exp["date"],
                    exp["category"],
                    f"{exp['amount']:.2f}",
                    exp.get("description", ""),
                    user_display
                )
            )
            total += exp["amount"]
        
        self.total_label.config(text=f"Total Expenses: {total:.2f}")
        self.count_label.config(text=f"Count: {len(expense_list)}")

    def _clear_filter(self) -> None:
        self.search_category.set("")
        self.refresh()

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _add_expense(self) -> None:
        self._open_dialog(title="Add Expense", existing=None)

    def _check_admin(self) -> bool:
        """Check if current user is admin."""
        root = self.winfo_toplevel()
        user = getattr(root, "current_user", None)
        if not user or user.get("role") != "admin":
            messagebox.showerror("Access Denied", "Only administrators can edit or delete expenses.")
            return False
        return True

    def _edit_expense_checked(self) -> None:
        """Admin-only: Edit expense."""
        if self._check_admin():
            self._edit_expense()

    def _delete_expense_checked(self) -> None:
        """Admin-only: Delete expense."""
        if self._check_admin():
            self._delete_expense()

    def _edit_expense(self) -> None:
        expense_id = self._selected_id()
        if not expense_id:
            messagebox.showinfo("Edit", "Select an expense to edit")
            return
        record = expenses.get_expense(expense_id)
        self._open_dialog(title="Edit Expense", existing=record)

    def _delete_expense(self) -> None:
        expense_id = self._selected_id()
        if not expense_id:
            messagebox.showinfo("Delete", "Select an expense to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete this expense?"):
            return
        expenses.delete_expense(expense_id)
        self.refresh()

    def _open_dialog(self, *, title: str, existing: dict | None) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("450x250")

        # Get existing categories for dropdown
        categories = expenses.get_expense_categories()
        if not categories:
            categories = ["Rent", "Utilities", "Supplies", "Salaries", "Marketing", "Maintenance", "Other"]

        fields = {
            "date": tk.StringVar(value=existing.get("date", datetime.now().strftime("%Y-%m-%d")) if existing else datetime.now().strftime("%Y-%m-%d")),
            "category": tk.StringVar(value=existing.get("category", "") if existing else ""),
            "amount": tk.StringVar(value=str(existing.get("amount", 0)) if existing else "0"),
            "description": tk.StringVar(value=existing.get("description", "") if existing else ""),
        }

        # Fields
        ttk.Label(dialog, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, pady=8, padx=12)
        ttk.Entry(dialog, textvariable=fields["date"], width=20).grid(row=0, column=1, sticky=tk.W, pady=8, padx=12)

        ttk.Label(dialog, text="Category:").grid(row=1, column=0, sticky=tk.W, pady=8, padx=12)
        category_combo = ttk.Combobox(dialog, textvariable=fields["category"], values=categories, width=25)
        category_combo.grid(row=1, column=1, sticky=tk.EW, pady=8, padx=12)

        ttk.Label(dialog, text="Amount:").grid(row=2, column=0, sticky=tk.W, pady=8, padx=12)
        ttk.Entry(dialog, textvariable=fields["amount"], width=20).grid(row=2, column=1, sticky=tk.W, pady=8, padx=12)

        ttk.Label(dialog, text="Description:").grid(row=3, column=0, sticky=tk.W, pady=8, padx=12)
        ttk.Entry(dialog, textvariable=fields["description"], width=30).grid(row=3, column=1, sticky=tk.EW, pady=8, padx=12)

        def on_submit():
            try:
                amount = float(fields["amount"].get())
            except ValueError:
                messagebox.showerror("Invalid", "Enter a valid amount")
                return

            payload = {
                "date": fields["date"].get().strip(),
                "category": fields["category"].get().strip(),
                "amount": amount,
                "description": fields["description"].get().strip(),
            }

            if not payload["date"] or not payload["category"]:
                messagebox.showerror("Invalid", "Date and Category are required")
                return

            # Get current user info
            root = self.winfo_toplevel()
            user = getattr(root, "current_user", None)
            if user and not existing:
                # Only add user info for new expenses
                payload["user_id"] = user.get("user_id")
                payload["username"] = user.get("username")

            try:
                if existing:
                    expenses.update_expense(existing["expense_id"], **payload)
                else:
                    expenses.create_expense(**payload)
                self.refresh()
                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to save expense: {exc}")

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=16)
        ttk.Button(btn_frame, text="Save", command=on_submit).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    def _view_report(self) -> None:
        """Show expense report dialog."""
        report_dialog = tk.Toplevel(self)
        report_dialog.title("Expense Report")
        report_dialog.transient(self.winfo_toplevel())
        report_dialog.grab_set()
        report_dialog.geometry("600x500")

        ttk.Label(report_dialog, text="Expense Report", font=("Segoe UI", 12, "bold")).pack(pady=8)

        # Date range
        controls = ttk.Frame(report_dialog)
        controls.pack(pady=8)
        
        start_var = tk.StringVar(value=datetime.now().replace(day=1).strftime("%Y-%m-%d"))
        end_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Label(controls, text="Start:").grid(row=0, column=0, padx=4)
        ttk.Entry(controls, textvariable=start_var, width=12).grid(row=0, column=1, padx=4)
        ttk.Label(controls, text="End:").grid(row=0, column=2, padx=4)
        ttk.Entry(controls, textvariable=end_var, width=12).grid(row=0, column=3, padx=4)
        
        def generate():
            start = start_var.get()
            end = end_var.get()
            
            summary = expenses.get_expense_summary(start, end)
            by_category = expenses.get_expenses_by_category(start, end)
            
            report = f"EXPENSE REPORT\n"
            report += f"Period: {start} to {end}\n"
            report += "=" * 60 + "\n\n"
            report += f"Total Expenses: {summary.get('total_amount', 0) or 0:.2f}\n"
            report += f"Number of Expenses: {summary.get('total_count', 0) or 0}\n"
            report += f"Average Expense: {summary.get('avg_amount', 0) or 0:.2f}\n\n"
            report += "BY CATEGORY:\n"
            report += "-" * 60 + "\n"
            report += f"{'Category':<25} {'Count':<10} {'Total':<15}\n"
            report += "-" * 60 + "\n"
            
            for cat in by_category:
                report += f"{cat['category']:<25} {cat['count']:<10} {cat['total_amount']:<15.2f}\n"
            
            text.delete("1.0", tk.END)
            text.insert("1.0", report)
        
        ttk.Button(controls, text="Generate", command=generate).grid(row=0, column=4, padx=4)
        
        # Report display
        text_frame = ttk.Frame(report_dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        text = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 10))
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscroll=scroll.set)
        
        generate()  # Generate initial report
