from __future__ import annotations
from utils.security import get_currency_code
from utils import set_window_icon
"""Expense tracking UI."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
from datetime import datetime
import tkcalendar

from modules import expenses


class ExpensesFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.tree = None
        self.search_category = tk.StringVar(value="")
        self.search_text = tk.StringVar(value="")
        self.start_date = tk.StringVar(value="")
        self.end_date = tk.StringVar(value="")
        self.min_amount = tk.StringVar(value="")
        self.max_amount = tk.StringVar(value="")
        self.current_page = 0
        self.page_size = 50
        self.total_records = 0
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Configure grid for proper layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)  # Tree gets expansion
        self.grid_propagate(True)
        
        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Expenses", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="🏠 Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)

        # Advanced filter/search bar
        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 8))

        # Row 1: Category and text search
        ttk.Label(filter_frame, text="Category:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        category_combo = ttk.Combobox(filter_frame, textvariable=self.search_category, width=20)
        category_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        category_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Search:").grid(row=0, column=2, sticky=tk.W, padx=(0, 4))
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_text, width=25)
        search_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda e: self._schedule_refresh())

        ttk.Button(filter_frame, text="Clear Filters", command=self._clear_filters).grid(row=0, column=4, sticky=tk.W, padx=(0, 10))

        # Row 2: Date range
        ttk.Label(filter_frame, text="From:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        start_entry = ttk.Entry(filter_frame, textvariable=self.start_date, width=12)
        start_entry.grid(row=1, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        ttk.Label(filter_frame, text="To:").grid(row=1, column=2, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        end_entry = ttk.Entry(filter_frame, textvariable=self.end_date, width=12)
        end_entry.grid(row=1, column=3, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        # Row 3: Amount range
        ttk.Label(filter_frame, text="Min Amount:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        ttk.Entry(filter_frame, textvariable=self.min_amount, width=12).grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        ttk.Label(filter_frame, text="Max Amount:").grid(row=2, column=2, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        ttk.Entry(filter_frame, textvariable=self.max_amount, width=12).grid(row=2, column=3, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        # Buttons row
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Button(button_frame, text="➕ Add Expense", command=self._add_expense, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="✏️ Edit", command=self._edit_expense_checked, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="🗑️ Delete", command=self._delete_expense_checked, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="📊 Report", command=self._view_report, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="⚙️ Categories", command=self._manage_categories, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="📄 Export CSV", command=self._export_csv, width=15).pack(side=tk.LEFT, padx=4)

        # Table
        columns = ("date", "category", "amount", "description", "user")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=50)
        self.tree.heading("date", text="Date")
        self.tree.heading("category", text="Category")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("description", text="Description")
        self.tree.heading("user", text="User")
        self.tree.column("date", width=120, minwidth=90, stretch=True)
        self.tree.column("category", width=180, minwidth=120, stretch=True)
        self.tree.column("amount", width=120, minwidth=90, anchor=tk.E, stretch=True)
        self.tree.column("description", width=300, minwidth=160, stretch=True)
        self.tree.column("user", width=160, minwidth=120, stretch=True)
        self.tree.grid(row=3, column=0, sticky=tk.NSEW, pady=(0, 8))

        # Pagination controls
        pagination_frame = ttk.Frame(self)
        pagination_frame.grid(row=4, column=0, sticky=tk.EW, pady=(0, 8))

        ttk.Button(pagination_frame, text="◀◀ First", command=self._go_to_first_page).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pagination_frame, text="◀ Previous", command=self._go_to_previous_page).pack(side=tk.LEFT, padx=(0, 10))

        self.page_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_label.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(pagination_frame, text="Next ▶", command=self._go_to_next_page).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pagination_frame, text="Last ▶▶", command=self._go_to_last_page).pack(side=tk.LEFT)

        # Page size selector
        ttk.Label(pagination_frame, text="Show:").pack(side=tk.RIGHT, padx=(10, 0))
        self.page_size_var = tk.StringVar(value="50")
        page_size_combo = ttk.Combobox(pagination_frame, textvariable=self.page_size_var,
                                      values=["25", "50", "100", "200"], width=5)
        page_size_combo.pack(side=tk.RIGHT, padx=(0, 10))
        page_size_combo.bind("<<ComboboxSelected>>", self._change_page_size)

        # Totals and actions
        bottom = ttk.Frame(self)
        bottom.grid(row=5, column=0, sticky=tk.EW, pady=(0, 8))
        self.total_label = ttk.Label(bottom, text="Total Expenses: 0.00", font=("Segoe UI", 10, "bold"))
        self.total_label.pack(side=tk.LEFT, padx=8)
        self.count_label = ttk.Label(bottom, text="Count: 0", font=("Segoe UI", 10, "bold"))
        self.count_label.pack(side=tk.LEFT, padx=8)
    def refresh(self) -> None:
        """Refresh the expense list with current filters and pagination."""
        currency = get_currency_code()

        # Clear existing items
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Get filter values
        category_filter = self.search_category.get().strip() or None
        search_text = self.search_text.get().strip() or None
        start_date = self.start_date.get().strip() or None
        end_date = self.end_date.get().strip() or None

        try:
            min_amount = float(self.min_amount.get().strip()) if self.min_amount.get().strip() else None
        except ValueError:
            min_amount = None

        try:
            max_amount = float(self.max_amount.get().strip()) if self.max_amount.get().strip() else None
        except ValueError:
            max_amount = None

        # Get total count for pagination
        self.total_records = expenses.get_expenses_count(
            start_date=start_date,
            end_date=end_date,
            category=category_filter,
            min_amount=min_amount,
            max_amount=max_amount,
            search_text=search_text
        )

        # Get paginated results
        expense_list = expenses.list_expenses_advanced(
            start_date=start_date,
            end_date=end_date,
            category=category_filter,
            min_amount=min_amount,
            max_amount=max_amount,
            search_text=search_text,
            limit=self.page_size,
            offset=self.current_page * self.page_size
        )

        # Update pagination info
        total_pages = (self.total_records + self.page_size - 1) // self.page_size
        if total_pages == 0:
            total_pages = 1
        self.page_label.config(text=f"Page {self.current_page + 1} of {total_pages}")

        # Populate treeview
        total = 0.0
        for i, exp in enumerate(expense_list):
            user_display = exp.get("username", "N/A")
            created_at = exp.get("created_at", "")
            if created_at:
                # Show username with timestamp
                user_display = f"{user_display} ({created_at[:16]})"
            tags = []
            if i % 2 == 0:
                tags.append("even")
            else:
                tags.append("odd")
            self.tree.insert(
                "",
                tk.END,
                iid=str(exp["expense_id"]),
                values=(
                    exp["date"],
                    exp["category"],
                    f"{currency} {exp['amount']:.2f}",
                    exp.get("description", ""),
                    user_display
                ),
                tags=tuple(tags)
            )
            total += exp["amount"]

        self.tree.tag_configure("even", background="#F9F9F9")
        self.tree.tag_configure("odd", background="#FFFFFF")
        self.total_label.config(text=f"Total Expenses: {currency} {total:.2f}")
        self.count_label.config(text=f"Showing {len(expense_list)} of {self.total_records} expenses")

        # Update category dropdown
        self._update_category_dropdown()

    def _clear_filters(self) -> None:
        """Clear all filters and reset to first page."""
        self.search_category.set("")
        self.search_text.set("")
        self.start_date.set("")
        self.end_date.set("")
        self.min_amount.set("")
        self.max_amount.set("")
        self.current_page = 0
        self.refresh()

    def _schedule_refresh(self) -> None:
        """Schedule a refresh after a short delay to avoid too many refreshes during typing."""
        if hasattr(self, '_refresh_timer'):
            self.after_cancel(self._refresh_timer)
        self._refresh_timer = self.after(300, self.refresh)  # 300ms delay

    def _update_category_dropdown(self) -> None:
        """Update the category dropdown with current categories."""
        try:
            categories = expenses.get_expense_categories()
            # Find the combobox widget
            for child in self.winfo_children():
                if hasattr(child, 'winfo_children'):
                    for grandchild in child.winfo_children():
                        if hasattr(grandchild, 'config') and hasattr(grandchild, 'cget'):
                            try:
                                if grandchild.cget('textvariable') == self.search_category:
                                    grandchild['values'] = categories
                                    break
                            except:
                                pass
        except Exception:
            pass  # Ignore errors during category update

    # Pagination methods
    def _go_to_first_page(self) -> None:
        self.current_page = 0
        self.refresh()

    def _go_to_previous_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh()

    def _go_to_next_page(self) -> None:
        total_pages = (self.total_records + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.refresh()

    def _go_to_last_page(self) -> None:
        total_pages = (self.total_records + self.page_size - 1) // self.page_size
        self.current_page = max(0, total_pages - 1)
        self.refresh()

    def _change_page_size(self, event=None) -> None:
        """Change page size and reset to first page."""
        try:
            self.page_size = int(self.page_size_var.get())
            self.current_page = 0
            self.refresh()
        except ValueError:
            self.page_size = 50
            self.page_size_var.set("50")

    def _export_csv(self) -> None:
        """Export current filtered expenses to CSV."""
        from tkinter import filedialog
        import csv

        # Get current filter values
        category_filter = self.search_category.get().strip() or None
        search_text = self.search_text.get().strip() or None
        start_date = self.start_date.get().strip() or None
        end_date = self.end_date.get().strip() or None

        try:
            min_amount = float(self.min_amount.get().strip()) if self.min_amount.get().strip() else None
        except ValueError:
            min_amount = None

        try:
            max_amount = float(self.max_amount.get().strip()) if self.max_amount.get().strip() else None
        except ValueError:
            max_amount = None

        # Get all matching expenses (not paginated)
        expense_list = expenses.list_expenses_advanced(
            start_date=start_date,
            end_date=end_date,
            category=category_filter,
            min_amount=min_amount,
            max_amount=max_amount,
            search_text=search_text
        )

        if not expense_list:
            messagebox.showinfo("Export", "No expenses to export with current filters.")
            return

        # Ask for file location
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Expenses to CSV"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['expense_id', 'date', 'category', 'amount', 'description', 'username', 'created_at', 'currency_code']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for exp in expense_list:
                    writer.writerow(exp)

            messagebox.showinfo("Export Complete", f"Exported {len(expense_list)} expenses to {filename}")

            # Log audit event
            try:
                from utils.audit import audit_logger
                root = self.winfo_toplevel()
                user = getattr(root, "current_user", None)
                audit_logger.log_action(
                    action="EXPORT",
                    username=user.get("username") if user else "system",
                    table_name="expenses",
                    old_values=None,
                    new_values={"filename": filename, "count": len(expense_list)}
                )
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")

    def _clear_filter(self) -> None:
        currency = get_currency_code()
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
                    f"{currency} {exp['amount']:.2f}",
                    exp.get("description", ""),
                    user_display
                )
            )
            total += exp["amount"]
        self.total_label.config(text=f"Total Expenses: {currency} {total:.2f}")
        self.count_label.config(text=f"Count: {len(expense_list)}")

    def _manage_categories(self) -> None:
        """Open a simple manager to add/rename/delete categories."""
        dialog = tk.Toplevel(self)
        dialog.title("Manage Expense Categories")
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("380x360")
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Categories", font=("Segoe UI", 12, "bold")).pack(pady=(10, 6))

        listbox = tk.Listbox(dialog, height=12)
        listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        def reload_list():
            listbox.delete(0, tk.END)
            for cat in expenses.get_expense_categories():
                listbox.insert(tk.END, cat)

        def selected_category() -> str | None:
            sel = listbox.curselection()
            if not sel:
                return None
            return listbox.get(sel[0])

        def do_add():
            name = simpledialog.askstring("Add Category", "Category name:", parent=dialog)
            if not name:
                return
            try:
                expenses.add_expense_category(name.strip())
                reload_list()
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not add category: {exc}")

        def do_rename():
            current = selected_category()
            if not current:
                messagebox.showinfo("Rename", "Select a category to rename")
                return
            new_name = simpledialog.askstring("Rename Category", "New name:", initialvalue=current, parent=dialog)
            if not new_name:
                return
            try:
                expenses.rename_expense_category(current, new_name.strip())
                reload_list()
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not rename category: {exc}")

        def do_delete():
            current = selected_category()
            if not current:
                messagebox.showinfo("Delete", "Select a category to delete")
                return
            if not messagebox.askyesno("Delete Category", f"Delete '{current}' and reassign its expenses to 'Uncategorized'?"):
                return
            try:
                expenses.delete_expense_category(current, reassign_to="Uncategorized")
                reload_list()
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not delete category: {exc}")

        btns = ttk.Frame(dialog)
        btns.pack(pady=8)
        ttk.Button(btns, text="Add", width=10, command=do_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Rename", width=10, command=do_rename).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Delete", width=10, command=do_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Close", width=10, command=dialog.destroy).pack(side=tk.LEFT, padx=4)

        reload_list()

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
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
        dialog.withdraw()  # build offscreen to avoid blank flash
        dialog.title(title)
        set_window_icon(dialog)
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
        date_frame = ttk.Frame(dialog)
        date_frame.grid(row=0, column=1, sticky=tk.W, pady=8, padx=12)
        ttk.Entry(date_frame, textvariable=fields["date"], width=18).pack(side=tk.LEFT)

        def pick_date():
            """Open calendar picker for expense date."""
            try:
                current = datetime.strptime(fields["date"].get(), "%Y-%m-%d")
            except ValueError:
                current = datetime.now()

            cal_top = tk.Toplevel(dialog)
            cal_top.title("Select Date")
            set_window_icon(cal_top)
            cal_top.geometry("320x340")
            cal_top.resizable(False, False)
            cal_top.transient(dialog)
            cal_top.grab_set()

            cal = tkcalendar.Calendar(
                cal_top,
                year=current.year,
                month=current.month,
                day=current.day,
                date_pattern="yyyy-mm-dd"
            )
            cal.pack(fill="both", expand=True, padx=10, pady=10)

            def on_select():
                fields["date"].set(cal.get_date())
                cal_top.destroy()

            btns = ttk.Frame(cal_top)
            btns.pack(pady=8)
            ttk.Button(btns, text="OK", command=on_select).pack(side=tk.LEFT, padx=4)
            ttk.Button(btns, text="Cancel", command=cal_top.destroy).pack(side=tk.LEFT, padx=4)

        ttk.Button(date_frame, text="📅", width=3, command=pick_date).pack(side=tk.LEFT, padx=4)

        ttk.Label(dialog, text="Category:").grid(row=1, column=0, sticky=tk.W, pady=8, padx=12)
        category_combo = ttk.Combobox(dialog, textvariable=fields["category"], values=categories, width=25)
        category_combo.grid(row=1, column=1, sticky=tk.EW, pady=8, padx=12)

        def add_category_inline():
            """Prompt for a new category and update the list."""
            name = simpledialog.askstring("Add Category", "Category name:", parent=dialog)
            if not name:
                return
            name = name.strip()
            if not name:
                return
            try:
                expenses.add_expense_category(name)
                updated = expenses.get_expense_categories()
                category_combo["values"] = updated
                fields["category"].set(name)
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not add category: {exc}")

        ttk.Button(dialog, text="➕", width=4, command=add_category_inline).grid(row=1, column=2, sticky=tk.W, pady=8, padx=(0, 12))

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

        dialog.update_idletasks()
        dialog.deiconify()  # show after layout is ready

    def _view_report(self) -> None:
        """Show enhanced expense report dialog with trends and export."""
        report_dialog = tk.Toplevel(self)
        report_dialog.title("Expense Report & Analytics")
        set_window_icon(report_dialog)
        report_dialog.transient(self.winfo_toplevel())
        report_dialog.grab_set()
        report_dialog.geometry("800x600")

        ttk.Label(report_dialog, text="Expense Report & Analytics", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Controls frame
        controls = ttk.Frame(report_dialog)
        controls.pack(pady=8, fill=tk.X, padx=12)

        # Date range
        date_frame = ttk.Frame(controls)
        date_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))

        start_var = tk.StringVar(value=datetime.now().replace(day=1).strftime("%Y-%m-%d"))
        end_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(date_frame, text="Period:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(date_frame, text="From:").pack(side=tk.LEFT, padx=(0, 4))
        start_entry = ttk.Entry(date_frame, textvariable=start_var, width=12)
        start_entry.pack(side=tk.LEFT, padx=(0, 2))

        ttk.Label(date_frame, text="To:").pack(side=tk.LEFT, padx=(8, 4))
        end_entry = ttk.Entry(date_frame, textvariable=end_var, width=12)
        end_entry.pack(side=tk.LEFT, padx=(0, 2))

        # Report type selector
        ttk.Label(date_frame, text="Report Type:").pack(side=tk.LEFT, padx=(20, 4))
        report_type = tk.StringVar(value="summary")
        report_combo = ttk.Combobox(date_frame, textvariable=report_type,
                                   values=["summary", "trends", "categories", "detailed"], width=12)
        report_combo.pack(side=tk.LEFT, padx=(0, 8))

        # Buttons
        button_frame = ttk.Frame(date_frame)
        button_frame.pack(side=tk.RIGHT)

        def generate_report():
            generate()

        def export_report():
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Report"
            )
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(text.get("1.0", tk.END))
                    messagebox.showinfo("Export Complete", f"Report exported to {filename}")
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export: {e}")

        ttk.Button(button_frame, text="Generate", command=generate_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Export", command=export_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Close", command=report_dialog.destroy).pack(side=tk.LEFT, padx=2)

        # Report display
        text_frame = ttk.Frame(report_dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        text = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 10))
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscroll=scroll.set)

        def generate():
            start = start_var.get()
            end = end_var.get()
            rtype = report_type.get()

            try:
                if rtype == "summary":
                    report = generate_summary_report(start, end)
                elif rtype == "trends":
                    report = generate_trends_report(start, end)
                elif rtype == "categories":
                    report = generate_categories_report(start, end)
                elif rtype == "detailed":
                    report = generate_detailed_report(start, end)
                else:
                    report = "Invalid report type"

                text.delete("1.0", tk.END)
                text.insert("1.0", report)
            except Exception as e:
                text.delete("1.0", tk.END)
                text.insert("1.0", f"Error generating report: {e}")

        def generate_summary_report(start, end):
            summary = expenses.get_expense_summary(start, end)
            by_category = expenses.get_expenses_by_category(start, end)

            report = f"EXPENSE SUMMARY REPORT\n"
            report += f"Period: {start} to {end}\n"
            report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += "=" * 80 + "\n\n"

            report += "OVERVIEW:\n"
            report += "-" * 40 + "\n"
            report += f"Total Expenses:     {summary.get('total_amount', 0) or 0:.2f}\n"
            report += f"Number of Expenses: {summary.get('total_count', 0) or 0}\n"
            report += f"Average Expense:    {summary.get('avg_amount', 0) or 0:.2f}\n\n"

            if by_category:
                report += "TOP CATEGORIES:\n"
                report += "-" * 40 + "\n"
                report += f"{'Category':<25} {'Count':<8} {'Total':<12} {'Avg':<10}\n"
                report += "-" * 40 + "\n"

                for cat in sorted(by_category, key=lambda x: x['total_amount'], reverse=True)[:10]:
                    avg = cat['total_amount'] / cat['count'] if cat['count'] > 0 else 0
                    report += f"{cat['category']:<25} {cat['count']:<8} {cat['total_amount']:<12.2f} {avg:<10.2f}\n"

            return report

        def generate_trends_report(start, end):
            # Get monthly breakdown
            from collections import defaultdict
            import calendar

            all_expenses = expenses.list_expenses(start_date=start, end_date=end)
            monthly_totals = defaultdict(float)
            monthly_counts = defaultdict(int)

            for exp in all_expenses:
                month_key = exp['date'][:7]  # YYYY-MM
                monthly_totals[month_key] += exp['amount']
                monthly_counts[month_key] += 1

            report = f"EXPENSE TRENDS REPORT\n"
            report += f"Period: {start} to {end}\n"
            report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += "=" * 80 + "\n\n"

            if monthly_totals:
                report += "MONTHLY BREAKDOWN:\n"
                report += "-" * 50 + "\n"
                report += f"{'Month':<12} {'Expenses':<10} {'Count':<8} {'Average':<10}\n"
                report += "-" * 50 + "\n"

                for month in sorted(monthly_totals.keys()):
                    year, month_num = month.split('-')
                    month_name = calendar.month_name[int(month_num)][:3]
                    total = monthly_totals[month]
                    count = monthly_counts[month]
                    avg = total / count if count > 0 else 0
                    report += f"{month_name} {year:<6} {total:<10.2f} {count:<8} {avg:<10.2f}\n"

            return report

        def generate_categories_report(start, end):
            by_category = expenses.get_expenses_by_category(start, end)

            report = f"EXPENSE CATEGORIES REPORT\n"
            report += f"Period: {start} to {end}\n"
            report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += "=" * 80 + "\n\n"

            if by_category:
                # Calculate percentages
                total_amount = sum(cat['total_amount'] for cat in by_category)

                report += f"{'Category':<25} {'Count':<8} {'Total':<12} {'% of Total':<12}\n"
                report += "-" * 60 + "\n"

                for cat in sorted(by_category, key=lambda x: x['total_amount'], reverse=True):
                    percentage = (cat['total_amount'] / total_amount * 100) if total_amount > 0 else 0
                    report += f"{cat['category']:<25} {cat['count']:<8} {cat['total_amount']:<12.2f} {percentage:<12.1f}%\n"

            return report

        def generate_detailed_report(start, end):
            all_expenses = expenses.list_expenses(start_date=start, end_date=end)

            report = f"DETAILED EXPENSE REPORT\n"
            report += f"Period: {start} to {end}\n"
            report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += "=" * 120 + "\n\n"

            if all_expenses:
                report += f"{'Date':<12} {'Category':<20} {'Amount':<10} {'Description':<40} {'User':<15}\n"
                report += "-" * 120 + "\n"

                for exp in sorted(all_expenses, key=lambda x: x['date'], reverse=True):
                    desc = (exp.get('description', '') or '')[:37]
                    user = exp.get('username', 'N/A')[:14]
                    report += f"{exp['date']:<12} {exp['category']:<20} {exp['amount']:<10.2f} {desc:<40} {user:<15}\n"

            return report

        generate()  # Generate initial report
