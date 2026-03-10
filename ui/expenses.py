from __future__ import annotations
from utils.i18n import get_currency_symbol
from utils import set_window_icon
"""Expense tracking UI."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
from datetime import datetime
import tkcalendar

from modules import expenses
from utils.date_utils import format_date, get_date_format, parse_date_flexible, get_tkcalendar_date_pattern


def _get_tc():
    """Get theme colors with safe fallback."""
    try:
        from utils.theme import get_theme_colors
        return get_theme_colors()
    except Exception:
        return {'surface': '#FFFFFF', 'table_row_alt': '#F9F9F9', 'background': '#f5f5f5',
                'text': '#1f2937', 'text_secondary': '#6b7280', 'border': '#e5e7eb',
                'danger': '#ef4444', 'warning': '#f59e0b', 'primary': '#2563eb',
                'field_bg': '#FFFFFF', 'field_text': '#1f2937'}


class ExpensesFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.tree = None
        self.search_category = tk.StringVar(value="")
        self.search_text = tk.StringVar(value="")
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
        # Ensure the tree row expands correctly
        self.rowconfigure(3, weight=1)  # Tree gets expansion (fixed index)
        self.grid_propagate(True)
        
        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Expenses", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)

        # Advanced filter/search bar
        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 8))

        # Track whether each date filter is actively set by the user
        self._start_date_active = False
        self._end_date_active = False

        # Row 0: Category and text search
        ttk.Label(filter_frame, text="Category:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self._category_combo = ttk.Combobox(filter_frame, textvariable=self.search_category, width=20, state="readonly")
        self._category_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self._category_combo.bind("<<ComboboxSelected>>", lambda e: self._on_filter_change())

        ttk.Label(filter_frame, text="Search:").grid(row=0, column=2, sticky=tk.W, padx=(0, 4))
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_text, width=25)
        search_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda e: self._schedule_refresh())

        # Clear Filters spans columns 4-5
        ttk.Button(filter_frame, text="Clear Filters", command=self._clear_filters).grid(
            row=0, column=4, columnspan=2, sticky=tk.W, padx=(0, 10))

        # Row 1: Date range — DateEntry and ✕ each in their own column (no overlap)
        ttk.Label(filter_frame, text="From:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        self._start_date_entry = tkcalendar.DateEntry(
            filter_frame, width=14,
            date_pattern=get_tkcalendar_date_pattern(),
            state="readonly"
        )
        self._start_date_entry.grid(row=1, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 2))
        self._start_date_entry.bind("<<DateEntrySelected>>", lambda e: self._activate_start_date())

        ttk.Button(filter_frame, text="✕", width=2,
                   command=lambda: self._clear_date_entry('start')).grid(
            row=1, column=2, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        ttk.Label(filter_frame, text="To:").grid(row=1, column=3, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        self._end_date_entry = tkcalendar.DateEntry(
            filter_frame, width=14,
            date_pattern=get_tkcalendar_date_pattern(),
            state="readonly"
        )
        self._end_date_entry.grid(row=1, column=4, sticky=tk.W, pady=(5, 0), padx=(0, 2))
        self._end_date_entry.bind("<<DateEntrySelected>>", lambda e: self._activate_end_date())

        ttk.Button(filter_frame, text="✕", width=2,
                   command=lambda: self._clear_date_entry('end')).grid(
            row=1, column=5, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        # Row 2: Amount range
        ttk.Label(filter_frame, text="Min Amount:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        ttk.Entry(filter_frame, textvariable=self.min_amount, width=12).grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        ttk.Label(filter_frame, text="Max Amount:").grid(row=2, column=3, sticky=tk.W, pady=(5, 0), padx=(0, 4))
        ttk.Entry(filter_frame, textvariable=self.max_amount, width=12).grid(row=2, column=4, sticky=tk.W, pady=(5, 0), padx=(0, 10))

        # Buttons row
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Button(button_frame, text="➕ Add Expense", command=self._add_expense, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="✏️ Edit", command=self._edit_expense_checked, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="🗑️ Delete", command=self._delete_expense_checked, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="📊 Report", command=self._view_report, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="⚙️ Categories", command=self._manage_categories, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="📄 Export CSV", command=self._export_csv, width=15).pack(side=tk.LEFT, padx=4)

        # Table with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=3, column=0, sticky=tk.NSEW, pady=(0, 8))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(1, weight=0)  # scrollbar column
        tree_frame.rowconfigure(1, weight=0)     # scrollbar row

        columns = ("date", "category", "amount", "payment_method", "description", "reference", "user")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("date", text="Date")
        self.tree.heading("category", text="Category")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("payment_method", text="Paid Via")
        self.tree.heading("description", text="Description")
        self.tree.heading("reference", text="Ref #")
        self.tree.heading("user", text="User")
        self.tree.column("date", width=100, minwidth=80, stretch=True)
        self.tree.column("category", width=150, minwidth=100, stretch=True)
        self.tree.column("amount", width=100, minwidth=80, anchor=tk.E, stretch=True)
        self.tree.column("payment_method", width=100, minwidth=80, stretch=True)
        self.tree.column("description", width=220, minwidth=120, stretch=True)
        self.tree.column("reference", width=100, minwidth=70, stretch=True)
        self.tree.column("user", width=130, minwidth=100, stretch=True)

        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_scroll.grid(row=0, column=1, sticky=tk.NS)
        # Make horizontal scrollbar span both columns so it aligns under the tree
        h_scroll.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(2, 0))

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
    def _activate_start_date(self) -> None:
        """Mark the start date filter as active and refresh."""
        self._start_date_active = True
        self._on_filter_change()

    def _activate_end_date(self) -> None:
        """Mark the end date filter as active and refresh."""
        self._end_date_active = True
        self._on_filter_change()

    def _clear_date_entry(self, which: str) -> None:
        """Clear a date filter (deactivate it) and refresh."""
        if which == 'start':
            self._start_date_active = False
        else:
            self._end_date_active = False
        self._on_filter_change()

    def _on_filter_change(self) -> None:
        """Reset to first page and refresh when a filter changes."""
        self.current_page = 0
        self.refresh()

    def _get_filter_date(self, entry: tkcalendar.DateEntry, which: str = None) -> str | None:
        """Return an ISO date string (YYYY-MM-DD) if the date filter is active, else None."""
        if which == 'start' and not getattr(self, '_start_date_active', False):
            return None
        if which == 'end' and not getattr(self, '_end_date_active', False):
            return None
        try:
            return entry.get_date().strftime("%Y-%m-%d")
        except Exception:
            return None

    def refresh(self) -> None:
        """Refresh the expense list with current filters and pagination."""
        currency = get_currency_symbol()

        # Clear existing items
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Get filter values
        category_filter = self.search_category.get().strip() or None
        search_text = self.search_text.get().strip() or None
        start_date = self._get_filter_date(self._start_date_entry, 'start') if hasattr(self, '_start_date_entry') else None
        end_date = self._get_filter_date(self._end_date_entry, 'end') if hasattr(self, '_end_date_entry') else None

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
                    format_date(exp["date"]),
                    exp["category"],
                    f"{currency} {exp['amount']:.2f}",
                    exp.get("payment_method", "Cash"),
                    exp.get("description", ""),
                    exp.get("reference_number", "") or "",
                    user_display
                ),
                tags=tuple(tags)
            )
            total += exp["amount"]

        _tc = _get_tc()
        _row_fg = _tc.get('text', '#1f2937')
        self.tree.tag_configure("even", background=_tc.get('table_row_alt', '#F9F9F9'), foreground=_row_fg)
        self.tree.tag_configure("odd", background=_tc.get('surface', '#FFFFFF'), foreground=_row_fg)
        self.total_label.config(text=f"Total Expenses: {currency} {total:.2f}")
        self.count_label.config(text=f"Showing {len(expense_list)} of {self.total_records} expenses")

        # Update category dropdown
        self._update_category_dropdown()

    def _clear_filters(self) -> None:
        """Clear all filters and reset to first page."""
        self.search_category.set("")
        self.search_text.set("")
        self._start_date_active = False
        self._end_date_active = False
        self.min_amount.set("")
        self.max_amount.set("")
        self.current_page = 0
        self.refresh()

    def _schedule_refresh(self) -> None:
        """Schedule a refresh after a short delay to avoid too many refreshes during typing."""
        if hasattr(self, '_refresh_timer'):
            self.after_cancel(self._refresh_timer)
        self._refresh_timer = self.after(300, self._on_filter_change)  # 300ms delay

    def _update_category_dropdown(self) -> None:
        """Update the category dropdown with current categories."""
        try:
            categories = expenses.get_expense_categories()
            all_values = [""] + categories  # empty = All
            self._category_combo["values"] = all_values
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
        start_date = self._get_filter_date(self._start_date_entry, 'start') if hasattr(self, '_start_date_entry') else None
        end_date = self._get_filter_date(self._end_date_entry, 'end') if hasattr(self, '_end_date_entry') else None

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
                fieldnames = ['expense_id', 'date', 'category', 'amount', 'payment_method',
                              'description', 'reference_number', 'user_id', 'username', 'created_at', 'currency_code']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
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

    def _manage_categories(self) -> None:
        """Open a simple manager to add/rename/delete categories."""
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title("Manage Expense Categories")
        set_window_icon(dialog)
        dialog.resizable(True, True)
        dialog.minsize(360, 320)

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
            # Check permissions
            root = self.winfo_toplevel()
            current_user = getattr(root, 'current_user', {})
            from modules import permissions
            if not permissions.has_permission(current_user, 'add_expense_categories'):
                messagebox.showerror("Permission Denied", "You do not have permission to add expense categories")
                return
                
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
            # Check permissions
            root = self.winfo_toplevel()
            current_user = getattr(root, 'current_user', {})
            from modules import permissions
            if not permissions.has_permission(current_user, 'edit_expenses'):
                messagebox.showerror("Permission Denied", "You do not have permission to rename expense categories")
                return
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
            # Check permissions
            root = self.winfo_toplevel()
            current_user = getattr(root, 'current_user', {})
            from modules import permissions
            if not permissions.has_permission(current_user, 'delete_expense_categories'):
                messagebox.showerror("Permission Denied", "You do not have permission to delete expense categories")
                return
                
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

        # Action buttons at the bottom
        action_frame = ttk.Frame(dialog)
        action_frame.pack(pady=8)
        ttk.Button(action_frame, text="Add", width=10, command=do_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Rename", width=10, command=do_rename).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text="Delete", width=10, command=do_delete).pack(side=tk.LEFT, padx=4)

        reload_list()

        dialog.update_idletasks()
        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        w, h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        dialog.geometry(f"+{(sw - w) // 2}+{max(30, (sh - h) // 2 - 40)}")
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _add_expense(self) -> None:
        self._open_dialog(title="Add Expense", existing=None)

    def _edit_expense_checked(self) -> None:
        """Edit expense with permission check."""
        root = self.winfo_toplevel()
        from modules import permissions
        if not permissions.has_permission(getattr(root, 'current_user', {}), 'edit_expenses'):
            messagebox.showerror("Permission Denied", "You do not have permission to edit expenses.")
            return
        self._edit_expense()

    def _delete_expense_checked(self) -> None:
        """Delete expense with permission check."""
        root = self.winfo_toplevel()
        from modules import permissions
        if not permissions.has_permission(getattr(root, 'current_user', {}), 'delete_expenses'):
            messagebox.showerror("Permission Denied", "You do not have permission to delete expenses.")
            return
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
        currency = get_currency_symbol()

        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title(title)
        set_window_icon(dialog)
        dialog.resizable(False, False)

        # ── Outer padding frame ────────────────────────────────────────────
        outer = ttk.Frame(dialog, padding=(16, 14, 16, 10))
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)

        # ── Data ──────────────────────────────────────────────────────────
        categories = expenses.get_expense_categories() or [
            "Meals & Refreshments", "Cleaning Supplies", "Rent",
            "Utilities", "Shop Supplies", "Miscellaneous"
        ]
        payment_methods = expenses.get_payment_methods()

        # Resolve initial date
        if existing and existing.get("date"):
            try:
                _init_date = parse_date_flexible(existing["date"])
            except Exception:
                _init_date = datetime.now()
        else:
            _init_date = datetime.now()

        # ── Section: Expense Details ───────────────────────────────────────
        sec1 = ttk.LabelFrame(outer, text="Expense Details", padding=(10, 8))
        sec1.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        sec1.columnconfigure(1, weight=1)

        # Date
        ttk.Label(sec1, text="Date *").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        date_entry = tkcalendar.DateEntry(
            sec1, width=16,
            date_pattern=get_tkcalendar_date_pattern(),
            state="readonly",
            year=_init_date.year, month=_init_date.month, day=_init_date.day
        )
        date_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        # Category row — combo + inline ➕
        ttk.Label(sec1, text="Category *").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        cat_frame = ttk.Frame(sec1)
        cat_frame.grid(row=1, column=1, sticky=tk.EW, pady=5)
        cat_frame.columnconfigure(0, weight=1)

        cat_var = tk.StringVar(value=existing.get("category", "") if existing else "")
        category_combo = ttk.Combobox(cat_frame, textvariable=cat_var, values=categories, width=24)
        category_combo.grid(row=0, column=0, sticky=tk.EW)

        def add_category_inline():
            root = dialog.winfo_toplevel()
            current_user = getattr(root, 'current_user', {})
            from modules import permissions
            if not permissions.has_permission(current_user, 'add_expense_categories'):
                messagebox.showerror("Permission Denied", "You do not have permission to add expense categories")
                return
            name = simpledialog.askstring("New Category", "Category name:", parent=dialog)
            if not name or not name.strip():
                return
            try:
                expenses.add_expense_category(name.strip())
                updated = expenses.get_expense_categories()
                category_combo["values"] = updated
                cat_var.set(name.strip())
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not add category: {exc}")

        ttk.Button(cat_frame, text="➕ New", command=add_category_inline).grid(
            row=0, column=1, sticky=tk.W, padx=(6, 0))

        # Amount
        ttk.Label(sec1, text=f"Amount ({currency}) *").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        amount_var = tk.StringVar(value=f"{existing['amount']:.2f}" if existing else "")
        amount_entry = ttk.Entry(sec1, textvariable=amount_var, width=18)
        amount_entry.grid(row=2, column=1, sticky=tk.W, pady=5)

        # Payment method
        ttk.Label(sec1, text="Paid Via").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        pm_var = tk.StringVar(value=existing.get("payment_method", "Cash") if existing else "Cash")
        ttk.Combobox(sec1, textvariable=pm_var, values=payment_methods, width=24,
                     state="readonly").grid(row=3, column=1, sticky=tk.EW, pady=5)

        # ── Section: Additional Info ───────────────────────────────────────
        sec2 = ttk.LabelFrame(outer, text="Additional Info", padding=(10, 8))
        sec2.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        sec2.columnconfigure(1, weight=1)

        ttk.Label(sec2, text="Description").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        desc_var = tk.StringVar(value=existing.get("description", "") if existing else "")
        ttk.Entry(sec2, textvariable=desc_var, width=34).grid(row=0, column=1, sticky=tk.EW, pady=5)

        ttk.Label(sec2, text="Reference #").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        ref_var = tk.StringVar(value=existing.get("reference_number", "") if existing else "")
        ttk.Entry(sec2, textvariable=ref_var, width=24).grid(row=1, column=1, sticky=tk.W, pady=5)

        # ── Required-field hint ────────────────────────────────────────────
        ttk.Label(outer, text="* Required fields", foreground="gray",
                  font=("Segoe UI", 8)).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        # ── Action buttons ─────────────────────────────────────────────────
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(4, 0))

        def on_submit():
            raw_amount = amount_var.get().strip()
            if not raw_amount:
                messagebox.showerror("Required", "Please enter an amount.", parent=dialog)
                amount_entry.focus_set()
                return
            try:
                amount = float(raw_amount)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Amount", "Amount must be a positive number.", parent=dialog)
                amount_entry.focus_set()
                return

            category = cat_var.get().strip()
            if not category:
                messagebox.showerror("Required", "Please select or enter a category.", parent=dialog)
                category_combo.focus_set()
                return

            try:
                expense_date = date_entry.get_date().strftime("%Y-%m-%d")
            except Exception:
                messagebox.showerror("Invalid Date", "Please select a valid date.", parent=dialog)
                return

            payload = {
                "date": expense_date,
                "category": category,
                "amount": amount,
                "payment_method": pm_var.get().strip() or "Cash",
                "description": desc_var.get().strip(),
                "reference_number": ref_var.get().strip() or None,
            }

            root = self.winfo_toplevel()
            user = getattr(root, "current_user", None)
            if user and not existing:
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
                messagebox.showerror("Error", f"Failed to save expense:\n{exc}", parent=dialog)

        save_btn = ttk.Button(btn_frame, text="💾  Save Expense", command=on_submit, width=18)
        save_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT)

        # ── Bind Enter key to save ─────────────────────────────────────────
        dialog.bind("<Return>", lambda e: on_submit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        # ── Centre and show ────────────────────────────────────────────────
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        w = dialog.winfo_reqwidth()
        h = dialog.winfo_reqheight()
        x = (sw - w) // 2
        y = max(30, (sh - h) // 2 - 40)
        dialog.geometry(f"+{x}+{y}")
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        amount_entry.focus_set() if not existing else None

    def _view_report(self) -> None:
        """Full-featured expense report dialog with tabs, date pickers, filters and export."""
        import calendar as _cal

        dlg = tk.Toplevel(self)
        dlg.withdraw()
        dlg.title("Expense Report & Analytics")
        set_window_icon(dlg)
        dlg.resizable(True, True)
        dlg.columnconfigure(0, weight=1)
        dlg.rowconfigure(1, weight=1)

        currency = get_currency_symbol()

        # ── Top controls bar ──────────────────────────────────────────────
        ctrl = ttk.LabelFrame(dlg, text="Filters & Period", padding=(8, 6))
        ctrl.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=(8, 4))
        ctrl.columnconfigure(0, weight=1)

        # Row 0 ── Quick period buttons ───────────────────────────────────
        qf = ttk.Frame(ctrl)
        qf.grid(row=0, column=0, sticky=tk.EW, pady=(0, 6))
        ttk.Label(qf, text="Quick:").pack(side=tk.LEFT, padx=(0, 4))

        now = datetime.now()

        def _set_period(start_dt, end_dt):
            _start_de.set_date(start_dt)
            _end_de.set_date(end_dt)
            _on_generate()

        def _qbtn(label, s, e):
            ttk.Button(qf, text=label,
                       command=lambda: _set_period(s, e)).pack(side=tk.LEFT, padx=2)

        import datetime as _dt
        _lm_end = now.replace(day=1) - _dt.timedelta(days=1)
        _3m = (now.replace(day=1) - _dt.timedelta(days=1)).replace(day=1)
        _3m = (_3m.replace(day=1) - _dt.timedelta(days=1)).replace(day=1)
        _q  = (now.month - 1) // 3
        _qstart = now.replace(month=_q * 3 + 1, day=1)

        _qbtn("This Month",    now.replace(day=1),       now)
        _qbtn("Last Month",    _lm_end.replace(day=1),   _lm_end)
        _qbtn("Last 3 Months", _3m,                      now)
        _qbtn("This Quarter",  _qstart,                  now)
        _qbtn("This Year",     now.replace(month=1, day=1), now)
        ttk.Button(qf, text="All Time",
                   command=lambda: _set_period(_dt.date(2000, 1, 1), now)).pack(side=tk.LEFT, padx=2)

        # Row 1 ── Filters ────────────────────────────────────────────────
        ff = ttk.Frame(ctrl)
        ff.grid(row=1, column=0, sticky=tk.EW)

        ttk.Label(ff, text="From:").pack(side=tk.LEFT, padx=(0, 4))
        _start_de = tkcalendar.DateEntry(ff, width=13,
                                         date_pattern=get_tkcalendar_date_pattern(),
                                         state="readonly")
        _start_de.set_date(now.replace(day=1))
        _start_de.pack(side=tk.LEFT, padx=(0, 10))
        _start_de.bind("<<DateEntrySelected>>", lambda e: _on_generate())

        ttk.Label(ff, text="To:").pack(side=tk.LEFT, padx=(0, 4))
        _end_de = tkcalendar.DateEntry(ff, width=13,
                                       date_pattern=get_tkcalendar_date_pattern(),
                                       state="readonly")
        _end_de.set_date(now)
        _end_de.pack(side=tk.LEFT, padx=(0, 16))
        _end_de.bind("<<DateEntrySelected>>", lambda e: _on_generate())

        ttk.Label(ff, text="Category:").pack(side=tk.LEFT, padx=(0, 4))
        _cat_var = tk.StringVar(value="All")
        _cat_combo = ttk.Combobox(ff, textvariable=_cat_var, width=18, state="readonly")
        _cat_combo.pack(side=tk.LEFT, padx=(0, 16))
        _cat_combo.bind("<<ComboboxSelected>>", lambda e: _on_generate())
        try:
            _cats = ["All"] + expenses.get_expense_categories()
        except Exception:
            _cats = ["All"]
        _cat_combo["values"] = _cats

        # Export/action buttons on the right of the same row
        ttk.Button(ff, text="🔄 Refresh",     command=lambda: _on_generate()).pack(side=tk.LEFT, padx=2)
        ttk.Button(ff, text="📄 Export CSV",  command=lambda: _export_csv()).pack(side=tk.LEFT, padx=2)
        ttk.Button(ff, text="📑 Export PDF",  command=lambda: _export_pdf()).pack(side=tk.LEFT, padx=2)
        ttk.Button(ff, text="📃 Export Text", command=lambda: _export_text()).pack(side=tk.LEFT, padx=2)
        ttk.Button(ff, text="✕ Close",        command=dlg.destroy).pack(side=tk.RIGHT, padx=(4, 0))

        # ── Notebook tabs ─────────────────────────────────────────────────
        nb = ttk.Notebook(dlg)
        nb.grid(row=1, column=0, sticky=tk.NSEW, padx=10, pady=(4, 8))

        # Helper: scrollable treeview frame
        def _make_tree(parent, cols, headings, widths):
            f = ttk.Frame(parent)
            f.columnconfigure(0, weight=1)
            f.rowconfigure(0, weight=1)
            tv = ttk.Treeview(f, columns=cols, show="headings")
            for c, h, w in zip(cols, headings, widths):
                tv.heading(c, text=h, anchor=tk.W)
                tv.column(c, width=w, minwidth=50, stretch=True, anchor=tk.W)
            vsb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=tv.yview)
            tv.configure(yscrollcommand=vsb.set)
            tv.grid(row=0, column=0, sticky=tk.NSEW)
            vsb.grid(row=0, column=1, sticky=tk.NS)
            return tv

        # ── Tab 1: Summary ────────────────────────────────────────────────
        tab_sum = ttk.Frame(nb, padding=10)
        nb.add(tab_sum, text="  Summary  ")
        tab_sum.columnconfigure(0, weight=1)
        tab_sum.columnconfigure(1, weight=1)

        _sum_labels = {}

        def _lrow(parent, r, label, key, col=0):
            ttk.Label(parent, text=label, font=("Segoe UI", 9)).grid(
                row=r, column=col*2, sticky=tk.W, padx=(8, 4), pady=3)
            lv = ttk.Label(parent, text="—", font=("Segoe UI", 9, "bold"))
            lv.grid(row=r, column=col*2+1, sticky=tk.W, padx=(0, 20), pady=3)
            _sum_labels[key] = lv

        sum_box = ttk.LabelFrame(tab_sum, text="Period Overview", padding=8)
        sum_box.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))
        sum_box.columnconfigure(1, weight=1); sum_box.columnconfigure(3, weight=1)
        _lrow(sum_box, 0, "Total Expenses:",   "total",   0)
        _lrow(sum_box, 0, "Number of Records:", "count",  1)
        _lrow(sum_box, 1, "Average Expense:",  "avg",     0)
        _lrow(sum_box, 1, "Largest Expense:",  "max",     1)
        _lrow(sum_box, 2, "Period:",            "period",  0)

        # Top-5 categories tree inside summary
        ttk.Label(tab_sum, text="Top Categories", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=(4, 2))
        ttk.Label(tab_sum, text="By Payment Method", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=1, sticky=tk.W, pady=(4, 2))
        tab_sum.rowconfigure(2, weight=1)

        _sum_cat_tree  = _make_tree(tab_sum, ("cat","total","pct"),
                                    ("Category", "Total", "% Share"), [160, 100, 80])
        _sum_cat_tree.master.grid(row=2, column=0, sticky=tk.NSEW, padx=(0, 4))

        _sum_pay_tree = _make_tree(tab_sum, ("method","count","total"),
                                   ("Payment Method", "Count", "Total"), [150, 70, 100])
        _sum_pay_tree.master.grid(row=2, column=1, sticky=tk.NSEW, padx=(4, 0))

        # ── Tab 2: By Category ────────────────────────────────────────────
        tab_cat = ttk.Frame(nb, padding=4)
        nb.add(tab_cat, text="  By Category  ")
        tab_cat.columnconfigure(0, weight=1)
        tab_cat.rowconfigure(0, weight=1)
        _cat_tree = _make_tree(tab_cat,
            ("category", "count", "total", "avg", "max", "pct"),
            ("Category", "Count", "Total", "Average", "Max", "% Share"),
            [180, 70, 110, 110, 110, 80])
        _cat_tree.master.grid(row=0, column=0, sticky=tk.NSEW)

        _cat_foot = ttk.Label(tab_cat, text="")
        _cat_foot.grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)

        # ── Tab 3: By Payment Method ──────────────────────────────────────
        tab_pay = ttk.Frame(nb, padding=4)
        nb.add(tab_pay, text="  By Payment  ")
        tab_pay.columnconfigure(0, weight=1)
        tab_pay.rowconfigure(0, weight=1)
        _pay_tree = _make_tree(tab_pay,
            ("method", "count", "total", "avg", "pct"),
            ("Payment Method", "Count", "Total", "Average", "% Share"),
            [180, 70, 120, 120, 80])
        _pay_tree.master.grid(row=0, column=0, sticky=tk.NSEW)

        # ── Tab 4: Monthly Trends ─────────────────────────────────────────
        tab_trend = ttk.Frame(nb, padding=4)
        nb.add(tab_trend, text="  Trends  ")
        tab_trend.columnconfigure(0, weight=1)
        tab_trend.rowconfigure(0, weight=1)
        _trend_tree = _make_tree(tab_trend,
            ("month", "count", "total", "avg"),
            ("Month", "Count", "Total", "Average"),
            [130, 80, 130, 130])
        _trend_tree.master.grid(row=0, column=0, sticky=tk.NSEW)

        # ── Tab 5: Detailed ───────────────────────────────────────────────
        tab_det = ttk.Frame(nb, padding=4)
        nb.add(tab_det, text="  Detailed  ")
        tab_det.columnconfigure(0, weight=1)
        tab_det.rowconfigure(0, weight=1)
        _det_tree = _make_tree(tab_det,
            ("date", "category", "amount", "method", "description", "ref", "user"),
            ("Date", "Category", "Amount", "Paid Via", "Description", "Ref #", "User"),
            [110, 140, 100, 110, 200, 100, 110])
        _det_tree.master.grid(row=0, column=0, sticky=tk.NSEW)
        _det_foot = ttk.Label(tab_det, text="")
        _det_foot.grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)

        # ── Status bar ────────────────────────────────────────────────────
        _status = ttk.Label(dlg, text="", anchor=tk.W, relief=tk.SUNKEN)
        _status.grid(row=2, column=0, sticky=tk.EW, padx=0)

        # ── Core generate function ────────────────────────────────────────
        def _on_generate():
            try:
                start_iso = _start_de.get_date().strftime("%Y-%m-%d")
                end_iso   = _end_de.get_date().strftime("%Y-%m-%d")
            except Exception:
                _status.config(text="Invalid date selection.")
                return

            cat_filter = _cat_var.get()
            if cat_filter == "All":
                cat_filter = None

            try:
                summary   = expenses.get_expense_summary(start_iso, end_iso)
                by_cat    = expenses.get_expenses_by_category(start_iso, end_iso)
                by_pay    = expenses.get_expenses_by_payment_method(start_iso, end_iso)
                by_month  = expenses.get_expenses_monthly_trend(start_iso, end_iso)
                detail    = expenses.list_expenses_advanced(
                    start_date=start_iso, end_date=end_iso,
                    category=cat_filter, limit=2000)
            except Exception as exc:
                _status.config(text=f"Error: {exc}")
                return

            total_amt = float(summary.get("total_amount") or 0)
            total_cnt = int(summary.get("total_count") or 0)
            avg_amt   = float(summary.get("avg_amount") or 0)

            # category-filtered max
            _max = max((e["amount"] for e in detail), default=0)

            # ── Summary tab ──
            start_disp = format_date(_start_de.get_date())
            end_disp   = format_date(_end_de.get_date())
            _sum_labels["total"].config(text=f"{currency} {total_amt:,.2f}")
            _sum_labels["count"].config(text=str(total_cnt))
            _sum_labels["avg"].config(text=f"{currency} {avg_amt:,.2f}")
            _sum_labels["max"].config(text=f"{currency} {_max:,.2f}")
            _sum_labels["period"].config(text=f"{start_disp}  →  {end_disp}")

            for tv in (_sum_cat_tree, _sum_pay_tree):
                tv.delete(*tv.get_children())

            # filter by_cat if category filter active
            _bc = [r for r in by_cat if cat_filter is None or r["category"] == cat_filter]
            _bc_total = sum(r["total_amount"] for r in _bc) or 1
            for row in _bc[:8]:
                pct = row["total_amount"] / _bc_total * 100
                _sum_cat_tree.insert("", tk.END, values=(
                    row["category"],
                    f"{currency} {row['total_amount']:,.2f}",
                    f"{pct:.1f}%"))

            _bp_total = sum(r["total_amount"] for r in by_pay) or 1
            for row in by_pay:
                pct = row["total_amount"] / _bp_total * 100
                _sum_pay_tree.insert("", tk.END, values=(
                    row["payment_method"],
                    row["count"],
                    f"{currency} {row['total_amount']:,.2f}"))

            # ── By Category tab ──
            _cat_tree.delete(*_cat_tree.get_children())
            _bc2_total = sum(r["total_amount"] for r in _bc) or 1
            for row in _bc:
                pct = row["total_amount"] / _bc2_total * 100
                _cat_tree.insert("", tk.END, values=(
                    row["category"],
                    row["count"],
                    f"{currency} {row['total_amount']:,.2f}",
                    f"{currency} {float(row.get('avg_amount') or 0):,.2f}",
                    f"{currency} {float(row.get('max_amount') or 0):,.2f}",
                    f"{pct:.1f}%"))
            _cat_foot.config(text=f"  {len(_bc)} categories   Total: {currency} {sum(r['total_amount'] for r in _bc):,.2f}")

            # ── By Payment tab ──
            _pay_tree.delete(*_pay_tree.get_children())
            for row in by_pay:
                pct = row["total_amount"] / _bp_total * 100
                _pay_tree.insert("", tk.END, values=(
                    row["payment_method"],
                    row["count"],
                    f"{currency} {row['total_amount']:,.2f}",
                    f"{currency} {float(row.get('avg_amount') or 0):,.2f}",
                    f"{pct:.1f}%"))

            # ── Trends tab ──
            _trend_tree.delete(*_trend_tree.get_children())
            for row in by_month:
                mon = row["month"]   # YYYY-MM
                try:
                    yr, mo = mon.split("-")
                    mon_disp = f"{_cal.month_abbr[int(mo)]} {yr}"
                except Exception:
                    mon_disp = mon
                _trend_tree.insert("", tk.END, values=(
                    mon_disp,
                    row["count"],
                    f"{currency} {float(row['total_amount']):,.2f}",
                    f"{currency} {float(row.get('avg_amount') or 0):,.2f}"))

            # ── Detailed tab ──
            _det_tree.delete(*_det_tree.get_children())
            for exp in detail:
                _det_tree.insert("", tk.END, values=(
                    format_date(exp["date"]),
                    exp.get("category", ""),
                    f"{currency} {exp['amount']:,.2f}",
                    exp.get("payment_method", ""),
                    (exp.get("description") or "")[:50],
                    exp.get("reference_number", ""),
                    exp.get("username", "")))
            _det_foot.config(text=f"  {len(detail)} records   Total: {currency} {sum(e['amount'] for e in detail):,.2f}")

            _status.config(text=f"  {total_cnt} expenses  |  Total: {currency} {total_amt:,.2f}  |  Period: {start_disp} → {end_disp}")

        # ── Export helpers ────────────────────────────────────────────────
        def _get_iso_dates():
            return (_start_de.get_date().strftime("%Y-%m-%d"),
                    _end_de.get_date().strftime("%Y-%m-%d"))

        def _export_csv():
            from tkinter import filedialog
            import csv
            start_iso, end_iso = _get_iso_dates()
            cat_filter = _cat_var.get() if _cat_var.get() != "All" else None
            data = expenses.list_expenses_advanced(
                start_date=start_iso, end_date=end_iso,
                category=cat_filter, limit=50000)
            fname = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"expenses_{start_iso}_{end_iso}.csv")
            if not fname:
                return
            try:
                with open(fname, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["Expense Report"])
                    w.writerow(["Period", f"{format_date(_start_de.get_date())} to {format_date(_end_de.get_date())}"])
                    w.writerow(["Generated", f"{format_date(datetime.now())} {datetime.now().strftime('%H:%M:%S')}"])
                    w.writerow([])
                    w.writerow(["Date", "Category", "Amount", "Payment Method", "Description", "Reference", "User"])
                    for exp in data:
                        w.writerow([
                            format_date(exp["date"]),
                            exp.get("category", ""),
                            f"{exp['amount']:.2f}",
                            exp.get("payment_method", ""),
                            exp.get("description", ""),
                            exp.get("reference_number", ""),
                            exp.get("username", "")])
                messagebox.showinfo("Exported", f"CSV saved to:\n{fname}", parent=dlg)
            except Exception as exc:
                messagebox.showerror("Export Error", str(exc), parent=dlg)

        def _export_text():
            from tkinter import filedialog
            start_iso, end_iso = _get_iso_dates()
            cat_filter = _cat_var.get() if _cat_var.get() != "All" else None
            summary    = expenses.get_expense_summary(start_iso, end_iso)
            by_cat     = expenses.get_expenses_by_category(start_iso, end_iso)
            by_pay     = expenses.get_expenses_by_payment_method(start_iso, end_iso)
            by_month   = expenses.get_expenses_monthly_trend(start_iso, end_iso)
            detail     = expenses.list_expenses_advanced(
                start_date=start_iso, end_date=end_iso,
                category=cat_filter, limit=50000)
            start_disp = format_date(_start_de.get_date())
            end_disp   = format_date(_end_de.get_date())
            W = 80
            sep  = "=" * W
            thin = "-" * W
            lines = [sep,
                     "EXPENSE REPORT".center(W),
                     f"Period: {start_disp}  to  {end_disp}".center(W),
                     f"Generated: {format_date(datetime.now())} {datetime.now().strftime('%H:%M:%S')}".center(W),
                     sep, ""]
            total_amt = float(summary.get("total_amount") or 0)
            lines += ["OVERVIEW", thin,
                      f"  Total Expenses  : {currency} {total_amt:,.2f}",
                      f"  Record Count    : {summary.get('total_count', 0)}",
                      f"  Average         : {currency} {float(summary.get('avg_amount') or 0):,.2f}",
                      ""]
            bc = [r for r in by_cat if cat_filter is None or r["category"] == cat_filter]
            bc_total = sum(r["total_amount"] for r in bc) or 1
            lines += ["BY CATEGORY", thin,
                      f"  {'Category':<24} {'Count':>6} {'Total':>12} {'Avg':>10} {'%':>6}", thin]
            for r in bc:
                pct = r["total_amount"] / bc_total * 100
                avg = float(r.get("avg_amount") or 0)
                lines.append(f"  {r['category']:<24} {r['count']:>6} {r['total_amount']:>12.2f} {avg:>10.2f} {pct:>6.1f}%")
            lines.append("")
            bp_total = sum(r["total_amount"] for r in by_pay) or 1
            lines += ["BY PAYMENT METHOD", thin,
                      f"  {'Method':<22} {'Count':>6} {'Total':>12} {'%':>6}", thin]
            for r in by_pay:
                pct = r["total_amount"] / bp_total * 100
                lines.append(f"  {r['payment_method']:<22} {r['count']:>6} {r['total_amount']:>12.2f} {pct:>6.1f}%")
            lines.append("")
            lines += ["MONTHLY TREND", thin,
                      f"  {'Month':<12} {'Count':>6} {'Total':>12} {'Avg':>10}", thin]
            for r in by_month:
                mon = r["month"]
                try:
                    yr, mo = mon.split("-"); mon_disp = f"{_cal.month_abbr[int(mo)]} {yr}"
                except Exception:
                    mon_disp = mon
                lines.append(f"  {mon_disp:<12} {r['count']:>6} {float(r['total_amount']):>12.2f} {float(r.get('avg_amount') or 0):>10.2f}")
            lines.append("")
            lines += ["DETAILED LIST", thin,
                      f"  {'Date':<12} {'Category':<20} {'Amount':>10} {'Description':<35}", thin]
            for exp in detail:
                desc = (exp.get("description") or "")[:33]
                lines.append(f"  {format_date(exp['date']):<12} {exp.get('category',''):<20} {exp['amount']:>10.2f} {desc:<35}")
            lines += ["", sep]
            txt = "\n".join(lines)
            fname = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"expenses_{start_iso}_{end_iso}.txt")
            if not fname:
                return
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(txt)
                messagebox.showinfo("Exported", f"Text report saved to:\n{fname}", parent=dlg)
            except Exception as exc:
                messagebox.showerror("Export Error", str(exc), parent=dlg)

        def _export_pdf():
            from tkinter import filedialog
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import cm
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.enums import TA_CENTER, TA_RIGHT
                from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                                Paragraph, Spacer, HRFlowable)
                from reportlab.lib.colors import HexColor
                import reportlab.lib.colors as _rlc
            except ImportError:
                messagebox.showerror("PDF Export", "ReportLab is not installed.\nInstall it with:  pip install reportlab", parent=dlg)
                return

            start_iso, end_iso = _get_iso_dates()
            cat_filter = _cat_var.get() if _cat_var.get() != "All" else None
            summary    = expenses.get_expense_summary(start_iso, end_iso)
            by_cat     = expenses.get_expenses_by_category(start_iso, end_iso)
            by_pay     = expenses.get_expenses_by_payment_method(start_iso, end_iso)
            by_month   = expenses.get_expenses_monthly_trend(start_iso, end_iso)
            detail     = expenses.list_expenses_advanced(
                start_date=start_iso, end_date=end_iso,
                category=cat_filter, limit=50000)

            fname = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=f"expenses_{start_iso}_{end_iso}.pdf")
            if not fname:
                return

            C_PRI  = HexColor("#2563eb"); C_DRK = HexColor("#1e3a5f")
            C_LGT  = HexColor("#eff6ff"); C_BDR = HexColor("#bfdbfe")
            C_TXD  = HexColor("#1f2937"); C_TXM = HexColor("#6b7280")
            PAGE_W, PAGE_H = A4
            MARGIN = 1.8 * cm
            start_disp = format_date(_start_de.get_date())
            end_disp   = format_date(_end_de.get_date())
            now_str    = f"{format_date(datetime.now())} {datetime.now().strftime('%H:%M:%S')}"

            try:
                from modules.settings import get_setting
                biz = get_setting("business_name") or "Kiosk POS"
            except Exception:
                biz = "Kiosk POS"

            class _Deco:
                def __call__(self_, canv, doc):
                    canv.saveState()
                    canv.setFillColor(C_PRI)
                    canv.rect(0, PAGE_H - 1.2*cm, PAGE_W, 1.2*cm, fill=True, stroke=False)
                    canv.setFillColor(_rlc.white); canv.setFont("Helvetica-Bold", 10)
                    canv.drawString(MARGIN, PAGE_H - 0.85*cm, biz)
                    canv.setFont("Helvetica", 9)
                    canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.85*cm, "Expense Report")
                    canv.setFillColor(C_DRK)
                    canv.rect(0, 0, PAGE_W, 1.0*cm, fill=True, stroke=False)
                    canv.setFillColor(_rlc.white); canv.setFont("Helvetica", 8)
                    canv.drawString(MARGIN, 0.35*cm, f"Generated {now_str}")
                    canv.drawRightString(PAGE_W - MARGIN, 0.35*cm, f"Page {doc.page}")
                    canv.restoreState()

            doc = SimpleDocTemplate(fname, pagesize=A4,
                leftMargin=MARGIN, rightMargin=MARGIN,
                topMargin=2.8*cm, bottomMargin=1.6*cm)

            ss = getSampleStyleSheet()
            s_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=20,
                                     textColor=C_PRI, spaceAfter=4)
            s_sub   = ParagraphStyle("sb", fontName="Helvetica", fontSize=10,
                                     textColor=C_TXM, spaceAfter=8)
            s_sec   = ParagraphStyle("sc", fontName="Helvetica-Bold", fontSize=11,
                                     textColor=C_PRI, spaceBefore=10, spaceAfter=4)
            s_lbl   = ParagraphStyle("sl", fontName="Helvetica-Bold", fontSize=9, textColor=C_TXM)
            s_val   = ParagraphStyle("sv", fontName="Helvetica",      fontSize=9, textColor=C_TXD)
            s_thdr  = ParagraphStyle("sh", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=_rlc.white, alignment=TA_CENTER)
            s_cell  = ParagraphStyle("ce", fontName="Helvetica", fontSize=8, textColor=C_TXD)
            s_cellr = ParagraphStyle("cr", fontName="Helvetica", fontSize=8,
                                     textColor=C_TXD, alignment=TA_RIGHT)
            cw = PAGE_W - 2*MARGIN

            elems = []
            elems.append(Paragraph("Expense Report", s_title))
            elems.append(Paragraph(f"{biz}  \u2022  Period: <b>{start_disp}</b> to <b>{end_disp}</b>", s_sub))
            elems.append(HRFlowable(width="100%", thickness=2, color=C_PRI, spaceAfter=4))
            elems.append(Spacer(1, 12))

            # Summary meta grid
            total_amt = float(summary.get("total_amount") or 0)
            mp = [("Total Expenses",   f"{currency} {total_amt:,.2f}"),
                  ("Record Count",     str(summary.get("total_count", 0))),
                  ("Average Expense",  f"{currency} {float(summary.get('avg_amount') or 0):,.2f}"),
                  ("Generated",        now_str)]
            meta_rows = []
            for i in range(0, len(mp), 2):
                row = []
                for lbl, val in mp[i:i+2]:
                    row += [Paragraph(f"<b>{lbl}</b>", s_lbl), Paragraph(val, s_val)]
                while len(row) < 4:
                    row += [Paragraph("", s_lbl), Paragraph("", s_val)]
                meta_rows.append(row)
            half = cw / 2
            mt = Table(meta_rows, colWidths=[2.5*cm, half-2.5*cm, 2.5*cm, half-2.5*cm])
            mt.setStyle(TableStyle([
                ("BACKGROUND", (0,0),(-1,-1), C_LGT),
                ("BOX",        (0,0),(-1,-1), 0.5, C_BDR),
                ("INNERGRID",  (0,0),(-1,-1), 0.25, C_BDR),
                ("TOPPADDING", (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("LEFTPADDING",(0,0),(-1,-1), 6),
                ("RIGHTPADDING",(0,0),(-1,-1), 6)]))
            elems += [mt, Spacer(1, 12)]

            def _section_table(title, header_row, data_rows, col_widths):
                elems.append(Paragraph(title, s_sec))
                tdata = [[Paragraph(h, s_thdr) for h in header_row]] + \
                        [[Paragraph(str(v), s_cellr if i > 0 else s_cell)
                          for i, v in enumerate(r)] for r in data_rows]
                t = Table(tdata, colWidths=col_widths, repeatRows=1)
                n = len(data_rows)
                t.setStyle(TableStyle([
                    ("BACKGROUND",       (0,0),  (-1,0),  C_PRI),
                    ("ROWBACKGROUNDS",   (0,1),  (-1,-1), [_rlc.white, C_LGT]),
                    ("GRID",             (0,0),  (-1,-1), 0.25, C_BDR),
                    ("TOPPADDING",       (0,0),  (-1,-1), 4),
                    ("BOTTOMPADDING",    (0,0),  (-1,-1), 4),
                    ("LEFTPADDING",      (0,0),  (-1,-1), 6),
                    ("RIGHTPADDING",     (0,0),  (-1,-1), 6),
                    ("VALIGN",           (0,0),  (-1,-1), "MIDDLE")]))
                elems.append(t)
                elems.append(Spacer(1, 8))

            # By category
            bc = [r for r in by_cat if cat_filter is None or r["category"] == cat_filter]
            bc_total = sum(r["total_amount"] for r in bc) or 1
            _section_table("By Category",
                ["Category", "Count", "Total", "Average", "% Share"],
                [(r["category"], r["count"],
                  f"{currency} {r['total_amount']:,.2f}",
                  f"{currency} {float(r.get('avg_amount') or 0):,.2f}",
                  f"{r['total_amount']/bc_total*100:.1f}%") for r in bc],
                [cw*0.35, cw*0.1, cw*0.2, cw*0.2, cw*0.15])

            # By payment
            bp_total = sum(r["total_amount"] for r in by_pay) or 1
            _section_table("By Payment Method",
                ["Payment Method", "Count", "Total", "Average", "% Share"],
                [(r["payment_method"], r["count"],
                  f"{currency} {r['total_amount']:,.2f}",
                  f"{currency} {float(r.get('avg_amount') or 0):,.2f}",
                  f"{r['total_amount']/bp_total*100:.1f}%") for r in by_pay],
                [cw*0.3, cw*0.1, cw*0.2, cw*0.2, cw*0.2])

            # Monthly trend
            trend_rows = []
            for r in by_month:
                mon = r["month"]
                try:
                    yr, mo = mon.split("-"); mon_disp = f"{_cal.month_abbr[int(mo)]} {yr}"
                except Exception:
                    mon_disp = mon
                trend_rows.append((mon_disp, r["count"],
                    f"{currency} {float(r['total_amount']):,.2f}",
                    f"{currency} {float(r.get('avg_amount') or 0):,.2f}"))
            _section_table("Monthly Trend",
                ["Month", "Count", "Total", "Average"],
                trend_rows,
                [cw*0.25, cw*0.15, cw*0.3, cw*0.3])

            # Detail table (capped at 200 rows in PDF)
            det_rows = [(format_date(e["date"]), e.get("category",""),
                         f"{currency} {e['amount']:,.2f}",
                         e.get("payment_method",""),
                         (e.get("description") or "")[:40]) for e in detail[:200]]
            _section_table(f"Detailed Transactions{'  (first 200 shown)' if len(detail)>200 else ''}",
                ["Date", "Category", "Amount", "Paid Via", "Description"],
                det_rows,
                [cw*0.15, cw*0.22, cw*0.15, cw*0.18, cw*0.30])

            try:
                doc.build(elems, onFirstPage=_Deco(), onLaterPages=_Deco())
                messagebox.showinfo("Exported", f"PDF saved to:\n{fname}", parent=dlg)
            except Exception as exc:
                messagebox.showerror("Export Error", str(exc), parent=dlg)

        # ── Initial generate and show ─────────────────────────────────────
        dlg.update_idletasks()
        # Size and centre, leaving room for taskbar (approx 48px) and title bar
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        taskbar   = 52   # conservative taskbar allowance
        title_bar = 32
        w = min(960, sw - 60)
        h = min(680, sh - taskbar - title_bar - 20)
        x = (sw - w) // 2
        y = max(10, (sh - taskbar - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.minsize(780, 480)
        dlg.deiconify()
        dlg.lift()
        dlg.focus_force()
        dlg.attributes('-topmost', True)
        dlg.after(200, lambda: dlg.attributes('-topmost', False))
        dlg.grab_set()
        dlg.after(80, _on_generate)
