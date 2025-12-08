from __future__ import annotations
from utils.security import get_currency_code
"""Inventory management UI."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import os

from modules import items
from modules import vat_rates
from utils.images import validate_image_path, load_thumbnail
from utils.csv_io import export_inventory_csv, import_inventory_csv


class InventoryFrame(ttk.Frame):
    LOW_STOCK_THRESHOLD = 5

    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.search_var = tk.StringVar()
        self.tree = None
        self.preview_image = None  # keep reference to avoid GC
        self.preview_label = None
        self.low_stock_label = None
        self.count_var = tk.StringVar(value="Items: 0")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Inventory", font=("Segoe UI", 14, "bold"))
        header.grid(row=0, column=0, sticky=tk.W, pady=(0, 12))
        ttk.Label(self, textvariable=self.count_var).grid(row=0, column=1, sticky=tk.E)

        search_entry = ttk.Entry(self, textvariable=self.search_var)
        search_entry.grid(row=1, column=0, sticky=tk.EW, pady=4)
        search_entry.bind("<KeyRelease>", lambda _evt: self.refresh())

        btn_row = ttk.Frame(self)
        btn_row.grid(row=1, column=1, sticky=tk.E, padx=(8, 0))
        ttk.Button(btn_row, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Add Item", command=self._add_item_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Edit Item", command=self._edit_selected_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Delete Item", command=self._delete_selected_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Import CSV", command=self._import_csv_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Export Template", command=self._export_template).pack(side=tk.LEFT, padx=2)

        columns = ("name", "category", "currency", "cost_price", "selling_price", "quantity", "barcode")
        tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        tree.grid(row=2, column=0, sticky=tk.NSEW, pady=8)

        # Add horizontal scrollbar
        xscrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscroll=xscrollbar.set)
        xscrollbar.grid(row=3, column=0, sticky=tk.EW)

        headings = {
            "name": "Name",
            "category": "Category",
            "currency": "Currency",
            "cost_price": "Cost",
            "selling_price": "Price",
            "quantity": "Qty",
            "barcode": "Barcode",
        }
        for col, label in headings.items():
            tree.heading(col, text=label)
            tree.column(col, width=90, anchor=tk.W)
        tree.column("name", width=140)
        tree.column("category", width=120)
        tree.column("currency", width=80)
        tree.column("barcode", width=120)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky=tk.NS)

        # Preview panel
        preview = ttk.Frame(self, padding=(12, 0))
        preview.grid(row=2, column=2, sticky=tk.N)
        self.preview_label = ttk.Label(preview, text="(No image)", anchor=tk.CENTER)
        self.preview_label.pack()
        self.low_stock_label = ttk.Label(preview, foreground="red")
        self.low_stock_label.pack(pady=(8, 0))

        tree.bind("<<TreeviewSelect>>", lambda _evt: self._update_preview())

        self.tree = tree

        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(2, weight=1)

    def refresh(self) -> None:
        search = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = items.list_items(search=search if search else None)
        self.count_var.set(f"Items: {len(rows)}")
        from utils.security import get_currency_code
        global_currency = get_currency_code()
        for row in rows:
            tags = []
            if row["quantity"] <= self.LOW_STOCK_THRESHOLD:
                tags.append("low")
            cost = row["cost_price"] if isinstance(row["cost_price"], (int, float)) else 0.0
            price = row["selling_price"] if isinstance(row["selling_price"], (int, float)) else 0.0
            self.tree.insert(
                "",
                tk.END,
                iid=str(row["item_id"]),
                values=(row["name"], row.get("category", ""), global_currency, f"{cost:.2f}", f"{price:.2f}", row["quantity"], row.get("barcode", "")),
                tags=tuple(tags),
            )
        self.tree.tag_configure("low", foreground="red")
        self._update_preview()
        self._update_low_stock_label()

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _check_admin(self) -> bool:
        """Check if current user is admin."""
        root = self.winfo_toplevel()
        user = getattr(root, "current_user", None)
        if not user or user.get("role") != "admin":
            messagebox.showerror("Access Denied", "Only administrators can modify inventory items.")
            return False
        return True

    def _add_item_checked(self) -> None:
        """Admin-only: Add new item."""
        if self._check_admin():
            self._add_item_dialog()

    def _edit_selected_checked(self) -> None:
        """Admin-only: Edit selected item."""
        if self._check_admin():
            self._edit_selected()

    def _delete_selected_checked(self) -> None:
        """Admin-only: Delete selected item."""
        if self._check_admin():
            self._delete_selected()

    def _import_csv_checked(self) -> None:
        """Admin-only: Import from CSV."""
        if self._check_admin():
            self._import_csv()

    def _delete_selected(self) -> None:
        item_id = self._selected_id()
        if not item_id:
            messagebox.showinfo("Delete", "Select an item to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected item?"):
            return
        items.delete_item(item_id)
        self.refresh()

    def _edit_selected(self) -> None:
        item_id = self._selected_id()
        if not item_id:
            messagebox.showinfo("Edit", "Select an item to edit")
            return
        record = items.get_item(item_id)
        if not record:
            messagebox.showerror("Error", "Item not found")
            self.refresh()
            return
        self._open_item_dialog(title="Edit Item", existing=record)

    def _add_item_dialog(self) -> None:
        self._open_item_dialog(title="Add Item", existing=None)

    def _open_item_dialog(self, *, title: str, existing: dict | None) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(title)
        # Set the app's custom icon for the dialog (supports PyInstaller and source). If ICO doesn't work, use logo.png via iconphoto.
        try:
            import sys
            if hasattr(sys, "_MEIPASS"):
                icon_path = os.path.join(sys._MEIPASS, "assets", "app_icon.ico")
            else:
                icon_path = os.path.join(os.path.dirname(__file__), '../assets', 'app_icon.ico')
                icon_path = os.path.abspath(icon_path)
            if os.path.exists(icon_path):
                try:
                    dialog.iconbitmap(icon_path)
                except Exception:
                    pass
            # fallback to logo.png using iconphoto (works well on modern Windows)
            png_path = os.path.join(os.path.dirname(__file__), '../assets/logo.png')
            png_path = os.path.abspath(png_path)
            if os.path.exists(png_path):
                try:
                    img = tk.PhotoImage(file=png_path)
                    dialog.iconphoto(True, img)
                except Exception:
                    pass
        except Exception:
            pass
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        fields = {
            "name": tk.StringVar(value=existing.get("name", "") if existing else ""),
            "category": tk.StringVar(value=existing.get("category", "") if existing else ""),
            "cost_price": tk.StringVar(value=str(existing.get("cost_price", 0)) if existing else "0"),
            "selling_price": tk.StringVar(value=str(existing.get("selling_price", 0)) if existing else "0"),
            "quantity": tk.StringVar(value=str(existing.get("quantity", 0)) if existing else "0"),
            "barcode": tk.StringVar(value=existing.get("barcode", "") if existing else ""),
            "image_path": tk.StringVar(value=existing.get("image_path", "") if existing else ""),
            "vat_rate": tk.StringVar(value=str(existing.get("vat_rate", 16.0)) if existing else "16.0"),
            "low_stock_threshold": tk.StringVar(value=str(existing.get("low_stock_threshold", 10)) if existing else "10"),
        }

        def picker():
            filename = filedialog.askopenfilename(title="Select image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.gif"), ("All files", "*.*")])
            if filename:
                fields["image_path"].set(filename)

        labels = [
            ("Name", "name"),
            ("Category", "category"),
            ("Cost Price", "cost_price"),
            ("Selling Price", "selling_price"),
            ("Quantity", "quantity"),
            ("Barcode", "barcode"),
            ("Image Path", "image_path"),
        ]
        for idx, (label, key) in enumerate(labels):
            ttk.Label(dialog, text=label).grid(row=idx, column=0, sticky=tk.W, pady=4, padx=6)
            entry = ttk.Entry(dialog, textvariable=fields[key], width=32)
            entry.grid(row=idx, column=1, sticky=tk.EW, pady=4, padx=6)
            if key == "image_path":
                ttk.Button(dialog, text="Browse", command=picker).grid(row=idx, column=2, padx=4)

        ttk.Label(dialog, text="VAT Rate (%)").grid(row=len(labels), column=0, sticky=tk.W, pady=4, padx=6)
        # Load active VAT rates from database
        active_rates = vat_rates.get_active_rates_list()
        vat_values = [str(r) for r in active_rates] if active_rates else ["0", "16"]
        vat_combo = ttk.Combobox(dialog, textvariable=fields["vat_rate"], values=vat_values, width=10)
        vat_combo.grid(row=len(labels), column=1, sticky=tk.W, pady=4, padx=6)

        ttk.Label(dialog, text="Low Stock Threshold").grid(row=len(labels)+1, column=0, sticky=tk.W, pady=4, padx=6)
        ttk.Spinbox(dialog, from_=1, to=999, textvariable=fields["low_stock_threshold"], width=10).grid(row=len(labels)+1, column=1, sticky=tk.W, pady=4, padx=6)

        def on_submit():
            try:
                payload = {
                    "name": fields["name"].get().strip(),
                    "category": fields["category"].get().strip() or None,
                    "cost_price": float(fields["cost_price"].get() or 0),
                    "selling_price": float(fields["selling_price"].get() or 0),
                    "quantity": int(fields["quantity"].get() or 0),
                    "barcode": fields["barcode"].get().strip() or None,
                    "image_path": fields["image_path"].get().strip() or None,
                    "vat_rate": float(fields["vat_rate"].get() or 16.0),
                    "low_stock_threshold": int(fields["low_stock_threshold"].get() or 10),
                }
            except ValueError:
                messagebox.showerror("Invalid input", "Check numeric fields for valid numbers")
                return

            if not payload["name"]:
                messagebox.showerror("Invalid input", "Name is required")
                return

            if payload["image_path"] and not validate_image_path(payload["image_path"]):
                messagebox.showerror("Invalid image", "Selected image path is not valid")
                return

            if existing:
                items.update_item(existing["item_id"], **payload)
            else:
                items.create_item(**payload)
            self.refresh()
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=on_submit).grid(row=len(labels) + 1, column=0, columnspan=3, pady=12)

        for col in range(3):
            dialog.columnconfigure(col, weight=1)

        dialog.wait_window()

    def _update_preview(self) -> None:
        if not self.tree.get_children():
            self.preview_image = None
            self.preview_label.configure(text="(No items)", image="")
            return

        item_id = self._selected_id()
        if not item_id:
            self.preview_image = None
            self.preview_label.configure(text="(No image)", image="")
            return
        record = items.get_item(item_id)
        if record and record.get("image_path"):
            thumb = load_thumbnail(record["image_path"])
            if thumb:
                self.preview_image = thumb
                self.preview_label.configure(image=thumb, text="")
                return
        self.preview_image = None
        self.preview_label.configure(text="(No image)", image="")

    def _update_low_stock_label(self) -> None:
        lows = items.low_stock(self.LOW_STOCK_THRESHOLD)
        count = len(lows)
        if count:
            self.low_stock_label.configure(text=f"Low stock: {count} item(s) ≤ {self.LOW_STOCK_THRESHOLD}")
        else:
            self.low_stock_label.configure(text="")

    def _export_csv(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Export Inventory",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            count = export_inventory_csv(filename)
            messagebox.showinfo("Export", f"Exported {count} items to {filename}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))

    def _import_csv(self) -> None:
        filename = filedialog.askopenfilename(
            title="Import Inventory",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            count = import_inventory_csv(filename, skip_duplicates=True)
            messagebox.showinfo("Import", f"Imported {count} new items")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc))

    def _export_template(self):
        import tkinter.filedialog as fd
        import shutil
        import os
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'inventory_import_template.csv'))
        dest_path = fd.asksaveasfilename(
            title="Save Import Template",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile="inventory_import_template.csv"
        )
        if not dest_path:
            return
        try:
            shutil.copyfile(template_path, dest_path)
            messagebox.showinfo("Template Exported", f"Template saved to {dest_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export template: {e}")
