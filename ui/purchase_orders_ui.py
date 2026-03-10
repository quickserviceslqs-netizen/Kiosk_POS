"""Purchase Orders (LPO/PO) UI — create, preview, and manage purchase orders."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
from typing import List, Dict, Any, Optional

from modules import purchase_orders as po_module
from utils.security import get_username
from utils.i18n import get_currency_symbol
from utils import set_window_icon

STATUSES = ["draft", "sent", "partial", "received", "cancelled"]


class PurchaseOrdersFrame(ttk.Frame):
    """Purchase Order management — create, view, and manage LPOs/POs."""

    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        po_module.ensure_po_tables()
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  Top-level layout                                                    #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        hdr = ttk.Frame(self)
        hdr.grid(row=0, column=0, sticky=tk.EW, pady=(0, 12))
        ttk.Label(hdr, text="Purchase Orders (LPO / PO)", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)

        self.nb = ttk.Notebook(self)
        self.nb.grid(row=1, column=0, sticky=tk.NSEW)

        create_tab = ttk.Frame(self.nb, padding=8)
        history_tab = ttk.Frame(self.nb, padding=8)
        self.nb.add(create_tab, text="  ✏️  Create PO  ")
        self.nb.add(history_tab, text="  📋  PO History  ")

        self._build_create_tab(create_tab)
        self._build_history_tab(history_tab)

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event=None) -> None:
        if self.nb.index(self.nb.select()) == 1:
            self._refresh_history()

    # ------------------------------------------------------------------ #
    #  Create tab                                                          #
    # ------------------------------------------------------------------ #

    def _build_create_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        # Supplier / Notes row
        top = ttk.Frame(frame)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=2)

        ttk.Label(top, text="Supplier:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.supplier_var = tk.StringVar()
        self._supplier_cb = ttk.Combobox(top, textvariable=self.supplier_var, width=24)
        self._supplier_cb.grid(row=0, column=1, sticky=tk.EW, padx=(0, 16))
        self._refresh_suppliers()

        ttk.Label(top, text="Notes:").grid(row=0, column=2, sticky=tk.W, padx=(0, 6))
        self.notes_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.notes_var).grid(row=0, column=3, sticky=tk.EW)

        # Action buttons row
        btn_row = ttk.Frame(frame)
        btn_row.grid(row=1, column=0, sticky=tk.EW, pady=(0, 6))

        # Action buttons row — grid with two cells prevents left/right buttons squeezing each other
        btn_row = ttk.Frame(frame)
        btn_row.grid(row=1, column=0, sticky=tk.EW, pady=(0, 6))
        btn_row.columnconfigure(0, weight=1)  # left group expands; right group is fixed

        # Left group
        left_btns = ttk.Frame(btn_row)
        left_btns.grid(row=0, column=0, sticky=tk.W)
        ttk.Button(left_btns, text="⚡ Auto-fill Low Stock", command=self._autofill_low_stock).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(left_btns, text="➕ Add Item",            command=self._add_blank_row).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(left_btns, text="✏️ Edit Row",            command=self._edit_selected_row).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(left_btns, text="🗑 Remove Row",          command=self._remove_selected_row).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(left_btns, text="🔄 Clear All",           command=self._clear_create_form).pack(side=tk.LEFT, padx=(0, 6))

        # Right group
        right_btns = ttk.Frame(btn_row)
        right_btns.grid(row=0, column=1, sticky=tk.E)
        self.total_label = ttk.Label(right_btns, text="Total: 0.00", font=("Segoe UI", 11, "bold"))
        self.total_label.pack(side=tk.LEFT, padx=(0, 16))
        ttk.Button(right_btns, text="💾 Save Draft",         command=lambda: self._save_po(status="draft")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(right_btns, text="✅ Save & Mark Sent",   command=lambda: self._save_po(status="sent")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(right_btns, text="👁 Preview / Print",   command=self._preview_po).pack(side=tk.LEFT, padx=(0, 0))

        # Items treeview
        tf = ttk.Frame(frame)
        tf.grid(row=2, column=0, sticky=tk.NSEW)
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        cols = ("item_name", "qty", "unit_cost", "line_total")
        self.create_tree = ttk.Treeview(tf, columns=cols, show="headings", height=18, selectmode="browse")
        self.create_tree.heading("item_name", text="Item Name")
        self.create_tree.heading("qty", text="Qty Ordered")
        self.create_tree.heading("unit_cost", text="Unit Cost")
        self.create_tree.heading("line_total", text="Line Total")
        self.create_tree.column("item_name", width=340, minwidth=200)
        self.create_tree.column("qty", width=100, minwidth=70, anchor=tk.CENTER)
        self.create_tree.column("unit_cost", width=130, minwidth=90, anchor=tk.E)
        self.create_tree.column("line_total", width=130, minwidth=90, anchor=tk.E)
        self.create_tree.grid(row=0, column=0, sticky=tk.NSEW)
        self.create_tree.bind("<Double-1>", lambda e: self._edit_selected_row())

        vsb = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.create_tree.yview)
        vsb.grid(row=0, column=1, sticky=tk.NS)
        self.create_tree.configure(yscrollcommand=vsb.set)

        ttk.Label(tf, text="Double-click a row to edit", font=("Segoe UI", 8), foreground="gray").grid(
            row=1, column=0, sticky=tk.W, pady=(2, 0)
        )

        # Internal data store
        self._po_items: List[Dict[str, Any]] = []

    def _refresh_suppliers(self) -> None:
        try:
            from modules.stock_receiving import get_suppliers
            self._supplier_cb["values"] = get_suppliers()
        except Exception:
            pass

    def _autofill_low_stock(self) -> None:
        try:
            suggestions = po_module.get_low_stock_suggestions()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load low stock items: {exc}")
            return
        if not suggestions:
            messagebox.showinfo("No Items", "No items are currently at or below their reorder threshold.")
            return

        added = 0
        existing_ids = {i.get("item_id") for i in self._po_items if i.get("item_id")}
        for sug in suggestions:
            if sug["item_id"] in existing_ids:
                continue
            self._po_items.append({
                "item_id": sug["item_id"],
                "item_name": sug["name"],
                "quantity_ordered": float(max(sug.get("suggested_quantity") or 1, 1)),
                "unit_cost": float(sug.get("average_cost") or 0),
            })
            added += 1

        self._refresh_create_tree()
        if added:
            messagebox.showinfo("Auto-filled", f"Added {added} low-stock item(s) to the PO.\nAdjust quantities and costs as needed before saving.")
        else:
            messagebox.showinfo("No New Items", "All low-stock items are already in the PO.")

    def _add_blank_row(self) -> None:
        self._open_item_picker()

    def _edit_selected_row(self) -> None:
        sel = self.create_tree.selection()
        if not sel:
            messagebox.showinfo("Select Row", "Please select a row to edit.")
            return
        try:
            idx = int(sel[0])
        except ValueError:
            return
        if 0 <= idx < len(self._po_items):
            self._open_item_picker(existing=self._po_items[idx], row_index=idx)

    def _open_item_picker(self, existing: Dict[str, Any] = None, row_index: int = None) -> None:
        """Dialog to add or edit a PO line item."""
        try:
            from modules import items as items_module
            all_items = items_module.list_items()
        except Exception:
            all_items = []

        dialog = tk.Toplevel(self)
        dialog.title("Add Item" if existing is None else "Edit Item")
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(True, True)

        item_labels = [f"{i['name']} (ID:{i['item_id']})" for i in all_items]
        item_map = {f"{i['name']} (ID:{i['item_id']})": i for i in all_items}

        row_y = 0

        ttk.Label(dialog, text="Select Item:").grid(row=row_y, column=0, sticky=tk.W, padx=10, pady=6)
        item_var = tk.StringVar()
        item_cb = ttk.Combobox(dialog, textvariable=item_var, values=item_labels, width=38, state="readonly")
        item_cb.grid(row=row_y, column=1, sticky=tk.EW, padx=10, pady=6)
        row_y += 1

        ttk.Label(dialog, text="— OR custom name —", font=("Segoe UI", 8), foreground="gray").grid(
            row=row_y, column=0, columnspan=2, pady=0
        )
        row_y += 1

        ttk.Label(dialog, text="Custom Name:").grid(row=row_y, column=0, sticky=tk.W, padx=10, pady=4)
        custom_var = tk.StringVar(value=existing.get("item_name", "") if existing else "")
        ttk.Entry(dialog, textvariable=custom_var, width=32).grid(row=row_y, column=1, sticky=tk.EW, padx=10, pady=4)
        row_y += 1

        ttk.Label(dialog, text="Quantity:").grid(row=row_y, column=0, sticky=tk.W, padx=10, pady=4)
        qty_var = tk.StringVar(value=f"{existing['quantity_ordered']:.0f}" if existing else "1")
        ttk.Entry(dialog, textvariable=qty_var, width=14).grid(row=row_y, column=1, sticky=tk.W, padx=10, pady=4)
        row_y += 1

        ttk.Label(dialog, text="Unit Cost:").grid(row=row_y, column=0, sticky=tk.W, padx=10, pady=4)
        cost_var = tk.StringVar(value=f"{existing['unit_cost']:.2f}" if existing else "0.00")
        ttk.Entry(dialog, textvariable=cost_var, width=14).grid(row=row_y, column=1, sticky=tk.W, padx=10, pady=4)
        row_y += 1

        # Auto-fill unit cost when item is selected
        def on_item_selected(event=None):
            key = item_var.get()
            if key and key in item_map:
                it = item_map[key]
                if not custom_var.get().strip():
                    custom_var.set(it["name"])
                # Use average cost from stock lots if available, else item cost_price
                try:
                    from database.init_db import get_connection
                    import sqlite3
                    with get_connection() as conn:
                        conn.row_factory = sqlite3.Row
                        r = conn.execute(
                            "SELECT AVG(cost_price) as avg FROM stock_lots WHERE item_id = ?",
                            (it["item_id"],)
                        ).fetchone()
                        avg = r["avg"] if r and r["avg"] is not None else it.get("cost_price", 0)
                except Exception:
                    avg = it.get("cost_price", 0)
                cost_var.set(f"{avg:.2f}")

        item_cb.bind("<<ComboboxSelected>>", on_item_selected)

        def on_save():
            try:
                qty = float(qty_var.get())
                cost = float(cost_var.get())
            except ValueError:
                messagebox.showerror("Invalid", "Quantity and Unit Cost must be numbers.", parent=dialog)
                return
            if qty <= 0:
                messagebox.showerror("Invalid", "Quantity must be greater than zero.", parent=dialog)
                return

            selected_key = item_var.get()
            name = custom_var.get().strip()
            item_id = None

            if selected_key and selected_key in item_map:
                item_id = item_map[selected_key]["item_id"]
                if not name:
                    name = item_map[selected_key]["name"]
            
            if not name:
                messagebox.showerror("Invalid", "Please select an item or enter a custom name.", parent=dialog)
                return

            entry = {"item_id": item_id, "item_name": name, "quantity_ordered": qty, "unit_cost": cost}
            if row_index is not None:
                self._po_items[row_index] = entry
            else:
                self._po_items.append(entry)
            self._refresh_create_tree()
            dialog.destroy()

        ttk.Button(dialog, text="Save" if existing else "Add to PO", command=on_save).grid(
            row=row_y, column=0, columnspan=2, pady=12
        )
        dialog.columnconfigure(1, weight=1)
        dialog.wait_window()

    def _remove_selected_row(self) -> None:
        sel = self.create_tree.selection()
        if not sel:
            messagebox.showinfo("Select Row", "Please select a row to remove.")
            return
        try:
            idx = int(sel[0])
        except ValueError:
            return
        if 0 <= idx < len(self._po_items):
            self._po_items.pop(idx)
            self._refresh_create_tree()

    def _refresh_create_tree(self) -> None:
        currency = get_currency_symbol()
        for row in self.create_tree.get_children():
            self.create_tree.delete(row)
        total = 0.0
        for idx, item in enumerate(self._po_items):
            qty = float(item.get("quantity_ordered", 0))
            cost = float(item.get("unit_cost", 0))
            line = qty * cost
            total += line
            self.create_tree.insert("", tk.END, iid=str(idx), values=(
                item["item_name"],
                f"{qty:.0f}",
                f"{currency} {cost:.2f}",
                f"{currency} {line:.2f}",
            ))
        self.total_label.config(text=f"Total: {currency} {total:.2f}")

    def _clear_create_form(self) -> None:
        self.supplier_var.set("")
        self.notes_var.set("")
        self._po_items.clear()
        self._refresh_create_tree()

    def _save_po(self, status: str = "draft") -> None:
        if not self._po_items:
            messagebox.showwarning("Empty PO", "Please add at least one item before saving.")
            return
        supplier = self.supplier_var.get().strip() or None
        notes = self.notes_var.get().strip() or None
        username = get_username()
        try:
            po_id = po_module.create_po(
                items=self._po_items,
                supplier=supplier,
                notes=notes,
                created_by=username,
            )
            if status != "draft":
                po_module.update_po_status(po_id, status)
            po = po_module.get_po(po_id)
            messagebox.showinfo(
                "Saved",
                f"Purchase Order {po['po_number']} saved as {status.upper()}."
            )
            self._clear_create_form()
            self.nb.select(1)  # Switch to history tab
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save PO: {exc}")

    def _preview_po(self, po: Dict[str, Any] = None) -> None:
        """Show a formatted, printable LPO preview."""
        currency = get_currency_symbol()
        saved_po = po  # None means it's an unsaved draft from the create tab
        if po is None:
            if not self._po_items:
                messagebox.showwarning("Empty PO", "Please add at least one item to preview.")
                return
            po = {
                "po_number": "(Draft — Not Saved)",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "supplier": self.supplier_var.get().strip() or "N/A",
                "status": "draft",
                "notes": self.notes_var.get().strip(),
                "created_by": get_username(),
                "items": self._po_items,
                "total_amount": sum(
                    float(i.get("quantity_ordered", 0)) * float(i.get("unit_cost", 0))
                    for i in self._po_items
                ),
            }

        try:
            from database.init_db import get_setting
            company = get_setting("company_name") or get_setting("business_name") or ""
        except Exception:
            company = ""

        text = po_module.format_po_text(po, company_name=company, currency=currency)
        self._show_preview_window(text, po.get("po_number", "PO"), po=saved_po)

    def _show_preview_window(self, text: str, po_number: str, po: Dict[str, Any] = None) -> None:
        win = tk.Toplevel(self)
        win.title(f"LPO Preview — {po_number}")
        set_window_icon(win)
        win.transient(self.winfo_toplevel())
        win.resizable(True, True)

        # ── Button bar (pack BOTTOM first so it is always visible) ──────────
        bf = ttk.Frame(win)
        bf.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(4, 8))

        def _get_company():
            try:
                from database.init_db import get_setting
                return get_setting("company_name") or get_setting("business_name") or ""
            except Exception:
                return ""

        def export_txt():
            filename = filedialog.asksaveasfilename(
                title="Save LPO as Text", defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"{po_number}.txt", parent=win,
            )
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo("Saved", f"LPO saved to:\n{filename}", parent=win)

        def export_csv():
            if po is None:
                messagebox.showwarning("Not available", "Save the PO first to export as CSV.", parent=win)
                return
            filename = filedialog.asksaveasfilename(
                title="Save LPO as CSV", defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"{po_number}.csv", parent=win,
            )
            if filename:
                try:
                    po_module.export_po_csv(po, filename, currency=get_currency_symbol())
                    messagebox.showinfo("Saved", f"LPO exported to:\n{filename}", parent=win)
                except Exception as exc:
                    messagebox.showerror("Export Error", f"Failed to export CSV:\n{exc}", parent=win)

        def export_pdf():
            if po is None:
                messagebox.showwarning("Not available", "Save the PO first to export as PDF.", parent=win)
                return
            filename = filedialog.asksaveasfilename(
                title="Save LPO as PDF", defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=f"{po_number}.pdf", parent=win,
            )
            if filename:
                try:
                    po_module.export_po_pdf(po, filename,
                                            company_name=_get_company(),
                                            currency=get_currency_symbol())
                    messagebox.showinfo("Saved", f"LPO exported to:\n{filename}", parent=win)
                except Exception as exc:
                    messagebox.showerror("Export Error", f"Failed to export PDF:\n{exc}", parent=win)

        ttk.Button(bf, text="📄 Export PDF",  command=export_pdf).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="📊 Export CSV",  command=export_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="💾 Export Text", command=export_txt).pack(side=tk.LEFT, padx=4)
        ttk.Button(bf, text="✖ Close",        command=win.destroy).pack(side=tk.RIGHT, padx=4)

        ttk.Separator(win, orient=tk.HORIZONTAL).pack(side=tk.BOTTOM, fill=tk.X)

        # ── Text area + scrollbars (fill remaining space) ───────────────────
        text_frame = ttk.Frame(win)
        text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        txt = tk.Text(text_frame, font=("Courier New", 10), wrap=tk.NONE, padx=10, pady=10)
        vsb = ttk.Scrollbar(text_frame, orient=tk.VERTICAL,   command=txt.yview)
        hsb = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=txt.xview)
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        txt.pack(side=tk.LEFT,   fill=tk.BOTH, expand=True)

        txt.insert("1.0", text)
        txt.config(state=tk.DISABLED)

        # ── Auto-size to content, capped at 90 % of screen ───────────────────
        win.update_idletasks()
        # Measure content: count lines & max line width in characters
        lines      = text.split("\n")
        char_width = 8   # approx pixels per Courier New 10 char
        line_h     = 18  # approx pixels per line
        want_w     = min(max(len(l) for l in lines) * char_width + 60, int(win.winfo_screenwidth()  * 0.90))
        want_h     = min(len(lines) * line_h + 110,                    int(win.winfo_screenheight() * 0.85))
        want_w     = max(want_w, 600)
        want_h     = max(want_h, 420)
        # Centre on parent
        root       = self.winfo_toplevel()
        px, py     = root.winfo_x(), root.winfo_y()
        pw, ph     = root.winfo_width(), root.winfo_height()
        x          = px + (pw  - want_w) // 2
        y          = py + (ph  - want_h) // 2
        win.geometry(f"{want_w}x{want_h}+{x}+{y}")

    # ------------------------------------------------------------------ #
    #  History tab                                                         #
    # ------------------------------------------------------------------ #

    def _build_history_tab(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # Filter / button row
        flt = ttk.Frame(frame)
        flt.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))

        ttk.Label(flt, text="Status:").pack(side=tk.LEFT, padx=(0, 4))
        self.hist_status_var = tk.StringVar(value="All")
        status_values = ["All"] + [s.title() for s in STATUSES]
        ttk.Combobox(
            flt, textvariable=self.hist_status_var, values=status_values, width=12, state="readonly"
        ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(flt, text="🔄 Refresh", command=self._refresh_history).pack(side=tk.LEFT, padx=(4, 10))
        ttk.Button(flt, text="👁 View / Print", command=self._view_selected_po).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(flt, text="📝 Update Status", command=self._update_selected_status).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(flt, text="✅ Mark Received", command=self._mark_received).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(flt, text="🗑 Delete Draft", command=self._delete_selected_po).pack(side=tk.LEFT, padx=(0, 4))

        # History treeview
        tf = ttk.Frame(frame)
        tf.grid(row=1, column=0, sticky=tk.NSEW)
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        cols = ("po_number", "date", "supplier", "items", "total", "status", "created_by")
        self.hist_tree = ttk.Treeview(tf, columns=cols, show="headings", height=22, selectmode="browse")
        self.hist_tree.heading("po_number", text="PO Number")
        self.hist_tree.heading("date", text="Date")
        self.hist_tree.heading("supplier", text="Supplier")
        self.hist_tree.heading("items", text="Lines")
        self.hist_tree.heading("total", text="Total")
        self.hist_tree.heading("status", text="Status")
        self.hist_tree.heading("created_by", text="Created By")
        self.hist_tree.column("po_number", width=155, minwidth=120)
        self.hist_tree.column("date", width=100, minwidth=85)
        self.hist_tree.column("supplier", width=165, minwidth=100)
        self.hist_tree.column("items", width=55, minwidth=45, anchor=tk.CENTER)
        self.hist_tree.column("total", width=115, minwidth=85, anchor=tk.E)
        self.hist_tree.column("status", width=90, minwidth=70, anchor=tk.CENTER)
        self.hist_tree.column("created_by", width=115, minwidth=80)
        self.hist_tree.grid(row=0, column=0, sticky=tk.NSEW)
        self.hist_tree.bind("<Double-1>", lambda e: self._view_selected_po())

        vsb = ttk.Scrollbar(tf, orient=tk.VERTICAL, command=self.hist_tree.yview)
        vsb.grid(row=0, column=1, sticky=tk.NS)
        self.hist_tree.configure(yscrollcommand=vsb.set)

        self._refresh_history()

    def _refresh_history(self) -> None:
        currency = get_currency_symbol()
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)

        status_raw = self.hist_status_var.get().lower()
        status_filter = None if status_raw == "all" else status_raw

        try:
            pos = po_module.list_pos_with_item_count(status=status_filter)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load purchase orders: {exc}")
            return

        status_colors = {
            "draft": "#6b7280",
            "sent": "#2563eb",
            "partial": "#d97706",
            "received": "#16a34a",
            "cancelled": "#dc2626",
        }

        for po in pos:
            status = po.get("status", "draft")
            self.hist_tree.insert("", tk.END, iid=str(po["po_id"]), values=(
                po["po_number"],
                str(po.get("created_at", ""))[:10],
                po.get("supplier") or "—",
                po.get("item_count", 0),
                f"{currency} {float(po.get('total_amount', 0)):.2f}",
                status.title(),
                po.get("created_by") or "—",
            ), tags=(status,))

        for status, color in status_colors.items():
            self.hist_tree.tag_configure(status, foreground=color)

    def _selected_po_id(self) -> Optional[int]:
        sel = self.hist_tree.selection()
        if not sel:
            messagebox.showinfo("Select PO", "Please select a purchase order first.")
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _view_selected_po(self) -> None:
        po_id = self._selected_po_id()
        if po_id is None:
            return
        try:
            po = po_module.get_po(po_id)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load PO: {exc}")
            return
        self._preview_po(po=po)

    def _update_selected_status(self) -> None:
        po_id = self._selected_po_id()
        if po_id is None:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Update PO Status")
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(True, True)

        ttk.Label(dialog, text="New Status:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        status_var = tk.StringVar(value="sent")
        ttk.Combobox(
            dialog, textvariable=status_var,
            values=[s.title() for s in STATUSES],
            width=16, state="readonly"
        ).grid(row=0, column=1, sticky=tk.EW, padx=10, pady=10)

        def on_save():
            new = status_var.get().lower()
            try:
                po_module.update_po_status(po_id, new)
                self._refresh_history()
                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to update: {exc}", parent=dialog)

        ttk.Button(dialog, text="Update", command=on_save).grid(row=1, column=0, columnspan=2, pady=10)
        dialog.columnconfigure(1, weight=1)
        dialog.wait_window()

    def _mark_received(self) -> None:
        po_id = self._selected_po_id()
        if po_id is None:
            return
        if not messagebox.askyesno(
            "Mark as Received",
            "Mark this PO as Received?\n\nThis updates the status only. "
            "Use Stock Receiving to record the actual inventory.",
        ):
            return
        try:
            po_module.update_po_status(po_id, "received")
            self._refresh_history()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to update: {exc}")

    def _delete_selected_po(self) -> None:
        po_id = self._selected_po_id()
        if po_id is None:
            return
        try:
            po = po_module.get_po(po_id)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load PO: {exc}")
            return
        if po["status"] != "draft":
            messagebox.showerror(
                "Cannot Delete",
                f"Only Draft POs can be deleted.\nThis PO has status: {po['status'].title()}"
            )
            return
        if not messagebox.askyesno("Delete PO", f"Permanently delete {po['po_number']}?\nThis cannot be undone."):
            return
        try:
            po_module.delete_po(po_id)
            self._refresh_history()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to delete: {exc}")
