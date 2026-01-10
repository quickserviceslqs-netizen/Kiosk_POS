from __future__ import annotations
from utils.security import get_currency_code
from utils import set_window_icon
"""Inventory management UI."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import shutil
import os

import logging
from modules import items
from modules import vat_rates
from modules import units_of_measure as uom
from utils.images import validate_image_path, load_thumbnail
from utils.csv_io import export_inventory_csv, import_inventory_csv

logger = logging.getLogger(__name__)


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
        ttk.Button(btn_row, text="Variants", command=self._manage_variants_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Delete Item", command=self._delete_selected_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Import CSV", command=self._import_csv_checked).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Download Categories", command=self._download_categories).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Export Template", command=self._export_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="⚙️ Categories", command=self._manage_categories).pack(side=tk.LEFT, padx=2)

        columns = ("name", "category", "unit", "cost_price", "selling_price", "quantity", "barcode")
        # Host the table across two columns to give it room; preview sits in col 2.
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW, pady=8)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=24)
        tree.grid(row=0, column=0, sticky=tk.NSEW)

        # Vertical scrollbar attached to frame
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=vsb.set)
        vsb.grid(row=0, column=1, sticky=tk.NS)

        # Add horizontal scrollbar under the tree_frame
        xscrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscroll=xscrollbar.set)
        xscrollbar.grid(row=3, column=0, columnspan=2, sticky=tk.EW)

        headings = {
            "name": "Name",
            "category": "Category",
            "unit": "Unit",
            "cost_price": "Cost",
            "selling_price": "Price",
            "quantity": "Qty",
            "barcode": "Barcode",
        }
        for col, label in headings.items():
            tree.heading(col, text=label)
            # Provide balanced minimum widths and allow columns to stretch with tree width
            tree.column(col, width=120, minwidth=80, anchor=tk.W, stretch=True)
        # Make important columns wider by default
        tree.column("name", width=320, minwidth=160)
        tree.column("category", width=180, minwidth=120)
        tree.column("unit", width=100, minwidth=60)
        tree.column("barcode", width=220, minwidth=100)

        # Note: vertical scrollbar moved inside tree_frame and assigned to variable 'vsb'

        # Preview panel
        preview = ttk.Frame(self, padding=(12, 0))
        preview.grid(row=2, column=2, sticky=tk.N, padx=(8, 0))
        self.preview_label = ttk.Label(preview, text="(No image)", anchor=tk.CENTER)
        self.preview_label.pack()
        self.low_stock_label = ttk.Label(preview, foreground="red")
        self.low_stock_label.pack(pady=(8, 0))

        tree.bind("<<TreeviewSelect>>", lambda _evt: self._update_preview())

        self.tree = tree

        # Ensure the tree area expands to fill the available width; preview panel remains fixed
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(2, weight=1)
        self.grid_propagate(True)  # Allow frame to expand

    def refresh(self) -> None:
        search = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = items.list_items(search=search if search else None)
        self.count_var.set(f"Items: {len(rows)}")
        from utils.security import get_currency_code
        global_currency = get_currency_code()
        for i, row in enumerate(rows):
            tags = []
            # For fractional items, check actual volume against threshold
            if row.get("is_special_volume"):
                unit_size = float(row.get("unit_size_ml") or 1)
                low_threshold = float(row.get("low_stock_threshold") or 10)
                actual_volume = row["quantity"] * unit_size
                if actual_volume <= low_threshold:
                    tags.append("low")
            elif row["quantity"] <= (row.get("low_stock_threshold") or self.LOW_STOCK_THRESHOLD):
                tags.append("low")
            if i % 2 == 0:
                tags.append("even")
            else:
                tags.append("odd")
            cost = row["cost_price"] if isinstance(row["cost_price"], (int, float)) else 0.0
            price = row["selling_price"] if isinstance(row["selling_price"], (int, float)) else 0.0
            unit = row.get("unit_of_measure", "pieces")
            
            # Calculate per-unit prices based on base unit of measure
            unit_lower = unit.lower()
            unit_size = float(row.get("unit_size_ml") or 1)

            # Use configured conversion factor and abbreviation from units_of_measure
            try:
                unit_info = uom.get_unit_by_name(unit) or {}
                conv_factor = float(unit_info.get("conversion_factor", 1) or 1)
                abbr = unit_info.get("abbreviation") or ""
                base_unit = (unit_info.get("base_unit") or "").lower()
            except Exception:
                conv_factor = items._get_unit_multiplier(unit)
                abbr = ""
                base_unit = ""

            # Friendly unit label (use abbreviation if present)
            unit_label = f"/{abbr}" if abbr else ""

            # Price per large unit (e.g., per L/kg/m) = bulk price / package_size
            try:
                if abbr:
                    cost_per_unit = (cost / unit_size) if unit_size > 0 else cost
                    price_per_unit = (price / unit_size) if unit_size > 0 else price
                else:
                    cost_per_unit = cost
                    price_per_unit = price
            except Exception:
                cost_per_unit = cost
                price_per_unit = price
            
            # For fractional sales items, show available volume/weight/length instead of just container count
            qty_display = row["quantity"]
            if row.get("is_special_volume"):
                unit_size = float(row.get("unit_size_ml") or 1)
                # total in small units (e.g., ml, g, cm)
                try:
                    total_small = row["quantity"] * unit_size * conv_factor
                except Exception:
                    total_small = row["quantity"] * unit_size
                # Choose small unit abbreviation
                if "mill" in base_unit:
                    small_abbr = "ml"
                elif "gram" in base_unit:
                    small_abbr = "g"
                elif "cent" in base_unit:
                    small_abbr = "cm"
                else:
                    small_abbr = base_unit or "units"

                # If we know a large unit abbreviation (abbr), show large unit when appropriate
                if abbr:
                    if total_small >= conv_factor:
                        qty_display = f"{total_small/conv_factor:.1f} {abbr}"
                    else:
                        qty_display = f"{int(total_small)} {small_abbr}"
                else:
                    # Fallback: show package count
                    qty_display = f"{row['quantity']}"            
            self.tree.insert(
                "",
                tk.END,
                iid=str(row["item_id"]),
                values=(row["name"], row.get("category", ""), unit, f"{global_currency} {cost_per_unit:.4f}{unit_label}", f"{global_currency} {price_per_unit:.4f}{unit_label}", qty_display, row.get("barcode", "")),
                tags=tuple(tags),
            )
        self.tree.tag_configure("low", foreground="red")
        self.tree.tag_configure("even", background="#F9F9F9")
        self.tree.tag_configure("odd", background="#FFFFFF")
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
        dialog.withdraw()  # Hide dialog until fully configured
        dialog.title(title)
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        
        # Get screen dimensions for proper sizing
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        
        # Calculate size (80% of screen, max 800x700)
        dialog_width = min(800, int(screen_width * 0.8))
        dialog_height = min(700, int(screen_height * 0.8))
        
        # Center the dialog
        x_pos = (screen_width - dialog_width) // 2
        y_pos = (screen_height - dialog_height) // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x_pos}+{y_pos}")
        dialog.resizable(True, True)

        # Header at top
        header = ttk.Frame(dialog, relief="solid", borderwidth=1)
        header.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(header, text=f"{title} - Item Details", font=("Segoe UI", 12, "bold")).pack(padx=12, pady=8)

        # Button frame at bottom (pack before form so it stays at bottom)
        button_frame = ttk.Frame(dialog, relief="solid", borderwidth=1)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        ttk.Button(button_frame, text="Save", width=15).pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=4, pady=8)
        
        # Add "Manage Portions" button for existing fractional items (admin only)
        portions_btn = None
        if existing and existing.get("is_special_volume"):
            portions_btn = ttk.Button(button_frame, text="Manage Portions", width=18)
            portions_btn.pack(side=tk.RIGHT, padx=8, pady=8)

        # Scrollable form in the middle (takes remaining space)
        form_container = ttk.Frame(dialog)
        form_container.pack(fill=tk.BOTH, expand=True, side=tk.TOP, padx=10, pady=5)
        
        canvas = tk.Canvas(form_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_container, orient=tk.VERTICAL, command=canvas.yview)
        
        inner_frame = ttk.Frame(canvas)
        inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Create window and store the id for width updates
        canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Make inner_frame stretch to fill canvas width
        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Mousewheel scrolling
        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        inner_frame.columnconfigure(1, weight=1)

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
            "unit_of_measure": tk.StringVar(value=existing.get("unit_of_measure", "pieces") if existing else "pieces"),
            "is_special_volume": tk.BooleanVar(value=bool(existing.get("is_special_volume", 0)) if existing else False),
            "unit_size_ml": tk.StringVar(value=str(existing.get("unit_size_ml", 1)) if existing else "1"),
            "price_per_ml": tk.StringVar(value=str(existing.get("selling_price_per_unit") or existing.get("price_per_ml", "")) if existing else ""),
            "cost_price_per_unit": tk.StringVar(value=str(existing.get("cost_price_per_unit", "")) if existing else ""),
        }

        def picker():
            filename = filedialog.askopenfilename(title="Select image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.gif"), ("All files", "*.*")])
            if filename:
                fields["image_path"].set(filename)

        # Basic info section
        row = 0
        labels = [
            ("Name", "name"),
            ("Category", "category"),
            ("Cost Price (bulk/package)", "cost_price"),
            ("Selling Price (bulk/package)", "selling_price"),
            ("Quantity (in units)", "quantity"),
            ("Barcode", "barcode"),
        ]
        categories = items.get_categories()
        for label, key in labels:
            ttk.Label(inner_frame, text=label, font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
            if key == "category":
                cat_frame = ttk.Frame(inner_frame)
                cat_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
                cat_combo = ttk.Combobox(cat_frame, textvariable=fields[key], values=categories, width=35)
                cat_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

                def add_category_inline():
                    name = simpledialog.askstring("Add Category", "Category name:", parent=dialog)
                    if not name:
                        return
                    try:
                        items.add_category(name)
                        updated = items.get_categories()
                        cat_combo["values"] = updated
                        fields[key].set(name)
                    except Exception as exc:
                        messagebox.showerror("Category Error", f"Could not add category: {exc}")

                ttk.Button(cat_frame, text="➕", width=3, command=add_category_inline).pack(side=tk.LEFT, padx=4)
            else:
                entry = ttk.Entry(inner_frame, textvariable=fields[key], width=35)
                entry.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
            row += 1

        # Image row
        ttk.Label(inner_frame, text="Image Path", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        img_frame = ttk.Frame(inner_frame)
        img_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
        img_entry = ttk.Entry(img_frame, textvariable=fields["image_path"], width=25)
        img_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(img_frame, text="Browse", command=picker, width=12).pack(side=tk.LEFT, padx=4)
        row += 1

        # VAT and Low Stock
        ttk.Label(inner_frame, text="VAT Rate (%)", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        vat_combo = ttk.Combobox(inner_frame, textvariable=fields["vat_rate"], values=["0", "8", "16", "18"], width=35, state="readonly")
        vat_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
        row += 1

        ttk.Label(inner_frame, text="Low Stock Threshold", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        ttk.Spinbox(inner_frame, textvariable=fields["low_stock_threshold"], from_=1, to=1000, width=35).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
        row += 1

        # Unit of measure section
        sep = ttk.Separator(inner_frame, orient=tk.HORIZONTAL)
        sep.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=8, padx=12)
        row += 1

        ttk.Label(inner_frame, text="Unit of Measure", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        uom_values = uom.get_unit_names(active_only=True)
        uom_combo = ttk.Combobox(inner_frame, textvariable=fields["unit_of_measure"], values=uom_values, width=35, state="readonly")
        uom_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
        row += 1

        ttk.Label(inner_frame, text="Enable Fractional Sales", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        ttk.Checkbutton(inner_frame, variable=fields["is_special_volume"]).grid(row=row, column=1, sticky=tk.W, pady=5, padx=12)
        row += 1

        ttk.Label(inner_frame, text="Package Size (in units)", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        ttk.Spinbox(inner_frame, textvariable=fields["unit_size_ml"], from_=1, to=100000, width=35).grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
        row += 1

        # Check if user is admin for direct price editing
        root = self.winfo_toplevel()
        user = getattr(root, "current_user", None)
        is_admin = user and user.get("role") == "admin"
        price_state = "normal" if is_admin else "readonly"

        ttk.Label(inner_frame, text="Selling Price per Unit", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        ppm_entry = ttk.Entry(inner_frame, textvariable=fields["price_per_ml"], width=35, state=price_state)
        ppm_entry.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
        row += 1

        ttk.Label(inner_frame, text="Cost Price per Unit", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=12)
        cpp_entry = ttk.Entry(inner_frame, textvariable=fields["cost_price_per_unit"], width=35, state=price_state)
        cpp_entry.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=12)
        row += 1

        # Track which field was edited to prevent loops
        _updating = {"bulk": False, "unit": False}

        # Auto-calculate listed price per large unit from bulk price
        def auto_price_per_unit(*_args):
            if _updating["unit"]:
                return
            _updating["bulk"] = True
            try:
                selling = float(fields["selling_price"].get() or 0)
                cost = float(fields["cost_price"].get() or 0)
                size = float(fields["unit_size_ml"].get() or 0)
                unit = fields["unit_of_measure"].get().lower()
                if size > 0:
                    # Listed price per large unit = bulk / package_size
                    if selling > 0:
                        fields["price_per_ml"].set(f"{selling / size:.6f}")
                    if cost > 0:
                        fields["cost_price_per_unit"].set(f"{cost / size:.6f}")
            except ValueError:
                pass
            finally:
                _updating["bulk"] = False

        # Auto-calculate bulk price from listed price per large unit
        def auto_bulk_from_unit(*_args):
            if _updating["bulk"]:
                return
            _updating["unit"] = True
            try:
                ppm = float(fields["price_per_ml"].get() or 0)
                cpp = float(fields["cost_price_per_unit"].get() or 0)
                size = float(fields["unit_size_ml"].get() or 0)
                if size > 0:
                    if ppm > 0:
                        fields["selling_price"].set(f"{ppm * size:.2f}")
                    if cpp > 0:
                        fields["cost_price"].set(f"{cpp * size:.2f}")
            except ValueError:
                pass
            finally:
                _updating["unit"] = False

        fields["selling_price"].trace_add("write", auto_price_per_unit)
        fields["cost_price"].trace_add("write", auto_price_per_unit)
        fields["unit_size_ml"].trace_add("write", auto_price_per_unit)

        def on_unit_change(*_args):
            # Only adjust defaults for new items (don't override existing item's stored size)
            if existing:
                return
            unit = fields["unit_of_measure"].get().lower()
            if unit in ("liters","litre","liter","litres","l","kilograms","kilogram","kg","kgs"):
                fields["unit_size_ml"].set("1000")
            elif unit in ("meters","meter","metre","metres","m"):
                fields["unit_size_ml"].set("100")
            else:
                fields["unit_size_ml"].set("1")

        fields["unit_of_measure"].trace_add("write", on_unit_change)
        fields["unit_of_measure"].trace_add("write", auto_price_per_unit)
        # Only add reverse calculation trace for admin users
        if is_admin:
            fields["price_per_ml"].trace_add("write", auto_bulk_from_unit)
            fields["cost_price_per_unit"].trace_add("write", auto_bulk_from_unit)

        def on_submit():
            try:
                # For fractional items, quantity can be decimal
                is_fractional = fields["is_special_volume"].get()
                qty_str = fields["quantity"].get() or "0"
                quantity = float(qty_str) if is_fractional else int(float(qty_str))
                
                payload = {
                    "name": fields["name"].get().strip(),
                    "category": fields["category"].get().strip() or None,
                    "cost_price": float(fields["cost_price"].get() or 0),
                    "selling_price": float(fields["selling_price"].get() or 0),
                    "quantity": quantity,
                    "barcode": fields["barcode"].get().strip() or None,
                    "image_path": fields["image_path"].get().strip() or None,
                    "vat_rate": float(fields["vat_rate"].get() or 16.0),
                    "low_stock_threshold": int(float(fields["low_stock_threshold"].get() or 10)),
                    "unit_of_measure": fields["unit_of_measure"].get().strip() or "pieces",
                    "is_special_volume": 1 if is_fractional else 0,
                    # unit_size: number of large units per package (e.g., 1 = 1L)
                    "unit_size_ml": int(float(fields["unit_size_ml"].get() or 1)),
                }

                # Interpret the UI 'price_per_ml' field as the listed price per large unit
                # and convert to stored small-unit values when saving.
                listed_ppu = fields["price_per_ml"].get()
                listed_cpu = fields["cost_price_per_unit"].get()
                if listed_ppu:
                    multiplier = items._get_unit_multiplier(payload["unit_of_measure"])
                    ppu = float(listed_ppu)
                    payload["selling_price"] = ppu * float(payload["unit_size_ml"])
                    # price_per_ml stores small-unit price (e.g., per ml/g/cm)
                    payload["price_per_ml"] = ppu / multiplier
                else:
                    payload["price_per_ml"] = None

                if listed_cpu:
                    multiplier = items._get_unit_multiplier(payload["unit_of_measure"])
                    cpu = float(listed_cpu)
                    payload["cost_price"] = cpu * float(payload["unit_size_ml"])
                # If the admin provided selling/cost per unit, we use those to compute bulk price
            except ValueError as e:
                messagebox.showerror("Invalid input", f"Check numeric fields for valid numbers: {e}")
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

        def open_portions_dialog():
            """Open dialog to manage preset portions for this item."""
            from modules import portions
            logger.debug("Opening portions dialog for item_id=%s", existing.get("item_id"))

            pdialog = tk.Toplevel(dialog)
            pdialog.withdraw()
            pdialog.title(f"Manage Portions - {existing['name']}")
            set_window_icon(pdialog)
            pdialog.transient(dialog)
            pdialog.geometry("550x500")
            pdialog.resizable(True, True)

            # Get unit info for labels
            unit = existing.get("unit_of_measure", "pieces").lower()
            conversions = {
                "liters": ("ml", "L"), "litre": ("ml", "L"), "liter": ("ml", "L"), "litres": ("ml", "L"), "l": ("ml", "L"),
                "kilograms": ("g", "kg"), "kilogram": ("g", "kg"), "kg": ("g", "kg"), "kgs": ("g", "kg"),
                "meters": ("cm", "m"), "meter": ("cm", "m"), "metre": ("cm", "m"), "metres": ("cm", "m"), "m": ("cm", "m"),
            }
            small_unit, base_unit = conversions.get(unit, (unit, unit))

            # Header
            pheader = ttk.Frame(pdialog, relief="solid", borderwidth=1)
            pheader.pack(fill=tk.X, side=tk.TOP)
            ttk.Label(pheader, text="Preset Portions", font=("Segoe UI", 11, "bold")).pack(padx=10, pady=6)

            # Buttons at bottom (pack before list so they stay at bottom)
            btn_frame = ttk.Frame(pdialog, relief="solid", borderwidth=1)
            btn_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)
            
            # Entry form (pack before list, will appear after list visually)
            form_frame = ttk.LabelFrame(pdialog, text="Add/Edit Portion", padding=8)
            form_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=6)

            # Calculate base unit prices for automatic pricing (must happen before we reference item prices)
            unit_size_ml = existing.get("unit_size_ml", 1)  # Default 1 (will be 1000 for litre/kg items where applicable)
            item_sell_price = existing.get("selling_price", 0)
            item_cost_price = existing.get("cost_price", 0)
            # Price per base unit (ml/g/cm or per piece)
            price_per_unit = item_sell_price / unit_size_ml if unit_size_ml > 0 else 0
            cost_per_unit = item_cost_price / unit_size_ml if unit_size_ml > 0 else 0

            # Info label about automatic pricing
            ttk.Label(form_frame, text=f"Prices calculated automatically from item price (${item_sell_price:.2f} per {base_unit})", 
                     font=("Segoe UI", 8), foreground="blue").grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0,8))
            
            # List frame (takes remaining space)
            list_frame = ttk.Frame(pdialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
            
            # Treeview for portions
            cols = ("Name", f"Amount ({small_unit})", "Selling Price", "Cost Price", "Active")
            tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=90)
            tree.column("Name", width=100)
            
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            def load_portions():
                tree.delete(*tree.get_children())
                plist = portions.list_portions(existing["item_id"])
                for p in plist:
                    active = "Yes" if p["is_active"] else "No"
                    tree.insert("", tk.END, iid=str(p["portion_id"]), values=(
                        p["portion_name"], 
                        f"{p['portion_ml']:.0f}", 
                        f"{p['selling_price']:.2f}",
                        f"{p.get('cost_price', 0):.2f}" if p.get('cost_price') else "-",
                        active
                    ))
            
            load_portions()
            
            # Calculate base unit prices for automatic pricing
            unit_size_ml = existing.get("unit_size_ml", 1000)  # Default 1000ml for liquids
            item_sell_price = existing.get("selling_price", 0)
            item_cost_price = existing.get("cost_price", 0)
            
            # Price per base unit (ml/g/cm)
            price_per_unit = item_sell_price / unit_size_ml if unit_size_ml > 0 else 0
            cost_per_unit = item_cost_price / unit_size_ml if unit_size_ml > 0 else 0
            
            # Form fields (form_frame already packed above)
            pname_var = tk.StringVar()
            pml_var = tk.StringVar()
            pprice_var = tk.StringVar()
            pcost_var = tk.StringVar()
            pactive_var = tk.BooleanVar(value=True)
            editing_id = tk.IntVar(value=0)
            
            ttk.Label(form_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, padx=4)
            ttk.Entry(form_frame, textvariable=pname_var, width=15).grid(row=1, column=1, padx=4)
            ttk.Label(form_frame, text=f"{small_unit}:").grid(row=1, column=2, sticky=tk.W, padx=4)
            ml_entry = ttk.Entry(form_frame, textvariable=pml_var, width=10)
            ml_entry.grid(row=1, column=3, padx=4)
            ttk.Label(form_frame, text="Sell Price:").grid(row=1, column=4, sticky=tk.W, padx=4)
            price_entry = ttk.Entry(form_frame, textvariable=pprice_var, width=10, state="readonly")
            price_entry.grid(row=1, column=5, padx=4)
            
            ttk.Label(form_frame, text="Cost:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=(4,0))
            cost_entry = ttk.Entry(form_frame, textvariable=pcost_var, width=10, state="readonly")
            cost_entry.grid(row=2, column=1, padx=4, pady=(4,0))
            ttk.Checkbutton(form_frame, text="Active", variable=pactive_var).grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=4, pady=(4,0))
            
            # Auto-calculate prices when amount changes
            def update_prices(*args):
                try:
                    ml = float(pml_var.get() or 0)
                    if ml > 0:
                        calc_sell = price_per_unit * ml
                        calc_cost = cost_per_unit * ml
                        pprice_var.set(f"{calc_sell:.2f}")
                        pcost_var.set(f"{calc_cost:.2f}" if calc_cost > 0 else "")
                except ValueError:
                    pass
            
            pml_var.trace_add("write", update_prices)
            
            def on_select(event):
                sel = tree.selection()
                if sel:
                    pid = int(sel[0])
                    plist = portions.list_portions(existing["item_id"])
                    for p in plist:
                        if p["portion_id"] == pid:
                            pname_var.set(p["portion_name"])
                            pml_var.set(f"{p['portion_ml']:.0f}")
                            # Prices will auto-calculate from the ml value
                            pactive_var.set(bool(p["is_active"]))
                            editing_id.set(pid)
                            break
            
            tree.bind("<<TreeviewSelect>>", on_select)
            
            def save_portion():
                name = pname_var.get().strip()
                if not name:
                    messagebox.showerror("Error", "Name is required")
                    return
                try:
                    ml = float(pml_var.get() or 0)
                except ValueError:
                    messagebox.showerror("Error", "Invalid amount value")
                    return
                if ml <= 0:
                    messagebox.showerror("Error", "Amount must be greater than zero")
                    return
                
                # Calculate prices based on current item pricing
                calc_sell = price_per_unit * ml
                # Ensure cost is numeric; if cost_per_unit is zero or unknown, default to 0.0 to satisfy NOT NULL DB constraint
                calc_cost = (cost_per_unit * ml) if (cost_per_unit and cost_per_unit > 0) else 0.0

                if editing_id.get():
                    portions.update_portion(editing_id.get(), portion_name=name, portion_ml=ml, 
                                           selling_price=calc_sell, cost_price=calc_cost, is_active=1 if pactive_var.get() else 0)
                else:
                    portions.create_portion(existing["item_id"], name, ml, calc_sell, calc_cost)
                
                clear_form()
                load_portions()
            
            def delete_portion():
                if not editing_id.get():
                    return
                if messagebox.askyesno("Confirm", "Delete this portion?"):
                    portions.delete_portion(editing_id.get())
                    clear_form()
                    load_portions()
            
            def clear_form():
                pname_var.set("")
                pml_var.set("")
                pprice_var.set("")
                pcost_var.set("")
                pactive_var.set(True)
                editing_id.set(0)
                tree.selection_remove(tree.selection())
            
            def create_defaults():
                if messagebox.askyesno("Create Defaults", "Create default portions (1/4L, 1/2L, 3/4L, 1L)?\nYou can edit prices afterward."):
                    # Get price per small unit and calculate price per liter
                    price_per_small = float(existing.get("selling_price_per_unit") or existing.get("price_per_ml") or 0)
                    cost_per_small = float(existing.get("cost_price_per_unit") or 0)
                    
                    # Convert to price per liter (1000 ml)
                    unit = existing.get("unit_of_measure", "pieces").lower()
                    conversions = {
                        "liters": 1000, "litre": 1000, "liter": 1000, "litres": 1000, "l": 1000,
                        "kilograms": 1000, "kilogram": 1000, "kg": 1000, "kgs": 1000,
                        "meters": 100, "meter": 100, "metre": 100, "metres": 100, "m": 100,
                    }
                    multiplier = conversions.get(unit, 1)
                    
                    price_per_base = price_per_small * multiplier
                    cost_per_base = cost_per_small * multiplier
                    
                    portions.create_default_portions(existing["item_id"], price_per_base, cost_per_base)
                    load_portions()
            
            # Add buttons to btn_frame (already packed above)
            ttk.Button(btn_frame, text="Save", command=save_portion, width=10).pack(side=tk.LEFT, padx=6, pady=8)
            ttk.Button(btn_frame, text="Delete", command=delete_portion, width=10).pack(side=tk.LEFT, padx=4, pady=8)
            ttk.Button(btn_frame, text="Clear", command=clear_form, width=10).pack(side=tk.LEFT, padx=4, pady=8)
            ttk.Button(btn_frame, text="Create Defaults", command=create_defaults, width=14).pack(side=tk.LEFT, padx=4, pady=8)
            ttk.Button(btn_frame, text="Close", command=pdialog.destroy, width=10).pack(side=tk.RIGHT, padx=6, pady=8)
            
            pdialog.deiconify()
            pdialog.grab_set()

        # Connect Save button to on_submit
        for child in button_frame.winfo_children():
            if child.cget("text") == "Save":
                child.configure(command=on_submit)
                break
        
        # Connect Manage Portions button if it exists
        if portions_btn:
            def _on_portions_click():
                # Debug helper - write to disk so automated tests can detect the click
                try:
                    with open(r'c:\Users\ADMIN\Kiosk_Pos\portions_click.log', 'a', encoding='utf-8') as f:
                        f.write('Manage Portions clicked for item_id=%s\n' % (existing.get('item_id'),))
                except Exception:
                    pass
                logger.debug("Manage Portions button clicked for item_id=%s", existing.get("item_id"))
                try:
                    open_portions_dialog()
                except Exception as e:
                    logger.exception("Error while opening portions dialog: %s", e)
                    try:
                        messagebox.showerror("Portions Error", f"Could not open Manage Portions: {e}")
                    except Exception:
                        pass
            portions_btn.configure(command=_on_portions_click)

        # Show dialog after everything is configured
        dialog.deiconify()
        dialog.grab_set()
        dialog.wait_window()

    def _manage_categories(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.withdraw()  # Hide until configured
        dialog.title("Inventory Categories")
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        
        # Get screen dimensions for proper sizing
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        
        # Calculate size (50% of screen, min 450x400)
        dialog_width = max(450, min(550, int(screen_width * 0.4)))
        dialog_height = max(400, min(500, int(screen_height * 0.5)))
        
        # Center the dialog
        x_pos = (screen_width - dialog_width) // 2
        y_pos = (screen_height - dialog_height) // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x_pos}+{y_pos}")
        dialog.resizable(True, True)

        # Header
        header = ttk.Frame(dialog, relief="solid", borderwidth=1)
        header.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(header, text="Manage Categories", font=("Segoe UI", 12, "bold")).pack(padx=12, pady=8)
        
        # Listbox in middle (expands)
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        listbox = tk.Listbox(list_frame, font=("Segoe UI", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def reload_list():
            listbox.delete(0, tk.END)
            for cat in items.get_categories():
                listbox.insert(tk.END, cat)

        def selected() -> str | None:
            sel = listbox.curselection()
            if not sel:
                return None
            return listbox.get(sel[0])

        def do_add():
            name = simpledialog.askstring("Add Category", "Category name:", parent=dialog)
            if not name:
                return
            try:
                items.add_category(name)
                reload_list()
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not add category: {exc}")

        def do_rename():
            current = selected()
            if not current:
                messagebox.showinfo("Rename", "Select a category to rename")
                return
            new_name = simpledialog.askstring("Rename Category", "New name:", initialvalue=current, parent=dialog)
            if not new_name:
                return
            try:
                items.rename_category(current, new_name)
                reload_list()
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not rename category: {exc}")

        def do_delete():
            current = selected()
            if not current:
                messagebox.showinfo("Delete", "Select a category to delete")
                return
            if not messagebox.askyesno("Delete Category", f"Delete '{current}' and reassign its items to 'Uncategorized'?"):
                return
            try:
                items.delete_category(current, reassign_to="Uncategorized")
                reload_list()
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Category Error", f"Could not delete category: {exc}")

        # Button frame at bottom
        btns = ttk.Frame(dialog, relief="solid", borderwidth=1)
        btns.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        ttk.Button(btns, text="Add", width=12, command=do_add).pack(side=tk.LEFT, padx=6, pady=8)
        ttk.Button(btns, text="Rename", width=12, command=do_rename).pack(side=tk.LEFT, padx=4, pady=8)
        ttk.Button(btns, text="Delete", width=12, command=do_delete).pack(side=tk.LEFT, padx=4, pady=8)
        ttk.Button(btns, text="Close", width=12, command=dialog.destroy).pack(side=tk.LEFT, padx=4, pady=8)

        reload_list()
        
        # Show dialog after configured
        dialog.deiconify()
        dialog.grab_set()

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

    def _download_categories(self) -> None:
        """Download all categories to a CSV file."""
        filename = filedialog.asksaveasfilename(
            title="Download Categories",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            import csv
            all_items = items.list_items()
            categories = sorted(set(item.get("category", "Uncategorized") for item in all_items if item.get("category")))
            
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Category"])
                for category in categories:
                    writer.writerow([category])
            
            messagebox.showinfo("Download", f"Downloaded {len(categories)} categories to {filename}")
        except Exception as exc:
            messagebox.showerror("Download Error", str(exc))

    def _manage_variants_checked(self) -> None:
        """Admin-only: Manage variants for selected item."""
        if self._check_admin():
            self._manage_variants()

    def _manage_variants(self) -> None:
        """Show variant management dialog for selected item."""
        item_id = self._selected_id()
        if not item_id:
            messagebox.showinfo("Variants", "Select an item to manage variants")
            return
        
        item = items.get_item(item_id)
        if not item:
            messagebox.showerror("Error", "Item not found")
            return
        
        from modules import variants
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Variants - {item['name']}")
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("720x520")
        
        ttk.Label(dialog, text=f"Variants for: {item['name']}", font=("Segoe UI", 12, "bold")).pack(pady=(10, 6))
        
        # Pack buttons first at bottom so they don't get pushed off screen
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, pady=(8, 12), fill=tk.X, padx=12)
        
        # Variants list
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 8))
        
        columns = ("variant_name", "selling_price", "cost_price", "quantity", "unit", "vat_rate")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        headings = {
            "variant_name": "Variant",
            "selling_price": "Price",
            "cost_price": "Cost",
            "quantity": "Qty",
            "unit": "Unit",
            "vat_rate": "VAT %"
        }
        for col, label in headings.items():
            tree.heading(col, text=label)
            tree.column(col, width=100)
        tree.column("variant_name", width=150)
        
        def reload_variants():
            for row in tree.get_children():
                tree.delete(row)
            variant_list = variants.list_variants(item_id)
            unit = item.get("unit_of_measure", "pieces")
            for v in variant_list:
                tree.insert("", tk.END, iid=str(v["variant_id"]), 
                           values=(v["variant_name"], f"{v['selling_price']:.2f}", 
                                   f"{v['cost_price']:.2f}", v.get("quantity", 0), unit, f"{v.get('vat_rate', 16.0):.1f}"))
        
        def selected_variant_id():
            sel = tree.selection()
            if not sel:
                return None
            try:
                return int(sel[0])
            except:
                return None
        
        def add_variant():
            # Disable the button to prevent double-clicks
            add_btn.config(state="disabled")
            try:
                var_dialog = tk.Toplevel(dialog)
                var_dialog.title("Add Variant")
                set_window_icon(var_dialog)
                var_dialog.transient(dialog)
                var_dialog.grab_set()
                var_dialog.withdraw()  # Hide initially to prevent flicker
                
                # Show parent item's unit
                unit_label = ttk.Label(var_dialog, text=f"Unit of Measure: {item.get('unit_of_measure', 'pieces')}", 
                                       font=("Segoe UI", 9, "italic"), foreground="gray")
                unit_label.grid(row=0, column=0, columnspan=2, pady=(8, 4), padx=6)
                
                fields = {
                    "variant_name": tk.StringVar(),
                    "selling_price": tk.StringVar(value=str(item.get("selling_price", 0))),
                    "cost_price": tk.StringVar(value=str(item.get("cost_price", 0))),
                    "quantity": tk.StringVar(value="0"),
                    "barcode": tk.StringVar(),
                    "sku": tk.StringVar(),
                    "vat_rate": tk.StringVar(value=str(item.get("vat_rate", 16.0))),
                    "low_stock_threshold": tk.StringVar(value=str(item.get("low_stock_threshold", 10))),
                }
                
                labels = [
                    ("Variant Name (e.g. Small, Large)", "variant_name"),
                    ("Selling Price", "selling_price"),
                    ("Cost Price", "cost_price"),
                    ("Quantity", "quantity"),
                    ("Barcode", "barcode"),
                    ("SKU", "sku"),
                    ("VAT Rate (%)", "vat_rate"),
                    ("Low Stock Threshold", "low_stock_threshold"),
                ]
                for idx, (label, key) in enumerate(labels):
                    ttk.Label(var_dialog, text=label).grid(row=idx+1, column=0, sticky=tk.W, pady=4, padx=6)
                    ttk.Entry(var_dialog, textvariable=fields[key], width=32).grid(row=idx+1, column=1, sticky=tk.EW, pady=4, padx=6)
                
                def save_variant():
                    try:
                        name = fields["variant_name"].get().strip()
                        if not name:
                            messagebox.showerror("Error", "Variant name is required")
                            return
                        variants.create_variant(
                            item_id=item_id,
                            variant_name=name,
                            selling_price=float(fields["selling_price"].get() or 0),
                            cost_price=float(fields["cost_price"].get() or 0),
                            quantity=int(fields["quantity"].get() or 0),
                            barcode=fields["barcode"].get().strip() or None,
                            sku=fields["sku"].get().strip() or None,
                            vat_rate=float(fields["vat_rate"].get() or 16.0),
                            low_stock_threshold=int(fields["low_stock_threshold"].get() or 10)
                        )
                        reload_variants()
                        var_dialog.destroy()
                    except ValueError:
                        messagebox.showerror("Error", "Invalid numeric value")
                    except Exception as exc:
                        messagebox.showerror("Error", f"Could not create variant: {exc}")
                
                ttk.Button(var_dialog, text="Save", command=save_variant).grid(row=len(labels)+1, column=0, columnspan=2, pady=12)
                var_dialog.columnconfigure(1, weight=1)
                
                # Force layout update before showing
                var_dialog.update_idletasks()
                
                # Show the dialog after all widgets are added
                var_dialog.deiconify()
                var_dialog.focus_set()
                
                # Re-enable button when dialog closes
                def on_dialog_close():
                    add_btn.config(state="normal")
                    var_dialog.destroy()
                var_dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
                
            except Exception:
                add_btn.config(state="normal")
                raise
        
        def edit_variant():
            variant_id = selected_variant_id()
            if not variant_id:
                messagebox.showinfo("Edit", "Select a variant to edit")
                return
            
            variant = variants.get_variant(variant_id)
            if not variant:
                messagebox.showerror("Error", "Variant not found")
                return
            
            var_dialog = tk.Toplevel(dialog)
            var_dialog.title("Edit Variant")
            set_window_icon(var_dialog)
            var_dialog.transient(dialog)
            var_dialog.grab_set()
            
            # Show parent item's unit
            unit_label = ttk.Label(var_dialog, text=f"Unit of Measure: {item.get('unit_of_measure', 'pieces')}", 
                                   font=("Segoe UI", 9, "italic"), foreground="gray")
            unit_label.grid(row=0, column=0, columnspan=2, pady=(8, 4), padx=6)
            
            fields = {
                "variant_name": tk.StringVar(value=variant["variant_name"]),
                "selling_price": tk.StringVar(value=str(variant["selling_price"])),
                "cost_price": tk.StringVar(value=str(variant["cost_price"])),
                "quantity": tk.StringVar(value=str(variant.get("quantity", 0))),
                "barcode": tk.StringVar(value=variant.get("barcode", "")),
                "sku": tk.StringVar(value=variant.get("sku", "")),
                "vat_rate": tk.StringVar(value=str(variant.get("vat_rate", 16.0))),
                "low_stock_threshold": tk.StringVar(value=str(variant.get("low_stock_threshold", 10))),
            }
            
            labels = [
                ("Variant Name", "variant_name"),
                ("Selling Price", "selling_price"),
                ("Cost Price", "cost_price"),
                ("Quantity", "quantity"),
                ("Barcode", "barcode"),
                ("SKU", "sku"),
                ("VAT Rate (%)", "vat_rate"),
                ("Low Stock Threshold", "low_stock_threshold"),
            ]
            for idx, (label, key) in enumerate(labels):
                ttk.Label(var_dialog, text=label).grid(row=idx+1, column=0, sticky=tk.W, pady=4, padx=6)
                ttk.Entry(var_dialog, textvariable=fields[key], width=32).grid(row=idx+1, column=1, sticky=tk.EW, pady=4, padx=6)
            
            def save_changes():
                try:
                    name = fields["variant_name"].get().strip()
                    if not name:
                        messagebox.showerror("Error", "Variant name is required")
                        return
                    variants.update_variant(
                        variant_id=variant_id,
                        variant_name=name,
                        selling_price=float(fields["selling_price"].get() or 0),
                        cost_price=float(fields["cost_price"].get() or 0),
                        quantity=int(fields["quantity"].get() or 0),
                        barcode=fields["barcode"].get().strip() or None,
                        sku=fields["sku"].get().strip() or None,
                        vat_rate=float(fields["vat_rate"].get() or 16.0),
                        low_stock_threshold=int(fields["low_stock_threshold"].get() or 10)
                    )
                    reload_variants()
                    var_dialog.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Invalid numeric value")
                except Exception as exc:
                    messagebox.showerror("Error", f"Could not update variant: {exc}")
            
            ttk.Button(var_dialog, text="Save", command=save_changes).grid(row=len(labels)+1, column=0, columnspan=2, pady=12)
            var_dialog.columnconfigure(1, weight=1)
        
        def delete_variant():
            variant_id = selected_variant_id()
            if not variant_id:
                messagebox.showinfo("Delete", "Select a variant to delete")
                return
            if not messagebox.askyesno("Confirm", "Delete this variant?"):
                return
            try:
                variants.delete_variant(variant_id)
                reload_variants()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not delete variant: {exc}")
        
        # Buttons were already packed at top before list_frame
        add_btn = ttk.Button(btn_frame, text="Add Variant", width=15, command=add_variant)
        add_btn.pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Edit Variant", width=15, command=edit_variant).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete Variant", width=15, command=delete_variant).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Close", width=15, command=dialog.destroy).pack(side=tk.LEFT, padx=4)
        
        reload_variants()
