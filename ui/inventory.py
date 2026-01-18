from __future__ import annotations
from utils.security import get_currency_code
from utils import set_window_icon
"""Inventory management UI."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, Menu
from tkinter import font as tkfont
import json
import shutil
import os

import logging
from modules import items
from modules import vat_rates
from modules import units_of_measure as uom
from utils.images import validate_image_path, load_thumbnail
from utils.csv_io import export_inventory_csv, import_inventory_csv

logger = logging.getLogger(__name__)


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event):
        if self.tooltip:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class InventoryFrame(ttk.Frame):
    LOW_STOCK_THRESHOLD = 5
    # Auto-fit configuration
    AUTOFIT_PADDING = 10
    AUTOFIT_MAX_COL_WIDTH = 600
    COLUMN_MAX_WIDTHS = {
        "name": 500,
        "category": 300,
        "barcode": 300,
        "selling_price": 250,
        "cost_price": 250,
    }
    # Recommended visible columns used for restore defaults
    DEFAULT_VISIBLE_COLUMNS = ("name", "selling_price", "quantity", "category")

    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.search_var = tk.StringVar()
        self.items_tree = None
        self.parents_tree = None
        self.notebook = None
        self.preview_image = None  # keep reference to avoid GC
        self.preview_label = None
        self.low_stock_label = None
        self.count_var = tk.StringVar(value="Items: 0")
        self.preview_visible = tk.BooleanVar(value=True)
        self.category_var = tk.StringVar(value="All")
        self.stock_var = tk.StringVar(value="All")
        self.loading_var = tk.StringVar()
        self.sort_column = None
        self.sort_reverse = False
        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.configure("Red.TButton", foreground="red")

        header = ttk.Label(self, text="Inventory", font=("Segoe UI", 14, "bold"))
        header.grid(row=0, column=0, sticky=tk.W, pady=(0, 12))
        ttk.Label(self, textvariable=self.count_var).grid(row=0, column=1, sticky=tk.E)
        loading_label = ttk.Label(self, textvariable=self.loading_var)
        loading_label.grid(row=0, column=2, sticky=tk.E)

        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=4)
        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT)
        category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, state="readonly")
        categories = items.get_categories()
        category_combo['values'] = ["All"] + categories
        category_combo.set("All")
        category_combo.pack(side=tk.LEFT, padx=(0,10))
        category_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        ttk.Label(filter_frame, text="Stock:").pack(side=tk.LEFT)
        stock_combo = ttk.Combobox(filter_frame, textvariable=self.stock_var, values=["All", "In Stock", "Low Stock", "Out of Stock"], state="readonly")
        stock_combo.pack(side=tk.LEFT, padx=(0,10))
        stock_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0,5))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh())
        ToolTip(search_entry, "Search by name, category, or barcode")
        
        # Clear search button
        clear_btn = ttk.Button(filter_frame, text="×", width=2, command=self._clear_search)
        clear_btn.pack(side=tk.LEFT, padx=(0,10))
        ToolTip(clear_btn, "Clear search")

        # Actions menu
        actions_menu = Menu(filter_frame, tearoff=0)
        item_menu = Menu(actions_menu, tearoff=0)
        item_menu.add_command(label="Add Item", command=self._add_item_checked)
        item_menu.add_command(label="Edit Item", command=self._edit_selected_checked)
        item_menu.add_command(label="Delete Item", command=self._delete_selected_checked)
        item_menu.add_command(label="Manage Variants", command=self._manage_variants_checked)
        actions_menu.add_cascade(label="Item Management", menu=item_menu)
        
        data_menu = Menu(actions_menu, tearoff=0)
        data_menu.add_command(label="Export CSV", command=self._export_csv)
        data_menu.add_command(label="Import CSV", command=self._import_csv_checked)
        data_menu.add_command(label="Download Categories", command=self._download_categories)
        data_menu.add_command(label="Export Template", command=self._export_template)
        actions_menu.add_cascade(label="Data", menu=data_menu)
        
        settings_menu = Menu(actions_menu, tearoff=0)
        settings_menu.add_command(label="Refresh", command=self.refresh)
        settings_menu.add_command(label="Manage Categories", command=self._manage_categories)
        settings_menu.add_command(label="Customize Columns", command=self._open_columns_dialog)
        actions_menu.add_cascade(label="Settings", menu=settings_menu)
        
        actions_btn = ttk.Menubutton(filter_frame, text="Actions", menu=actions_menu)
        actions_btn.pack(side=tk.LEFT, padx=(10,0))
        ToolTip(actions_btn, "Inventory actions menu")

        preview_toggle = ttk.Checkbutton(self, text="Show Preview", variable=self.preview_visible, command=self._toggle_preview)
        preview_toggle.grid(row=2, column=1, sticky=tk.W, padx=(8,0))
        
        # Create tabs for Items and Parents
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, pady=(8, 0))
        
        # Items tab - regular items without variants
        items_frame = ttk.Frame(self.notebook)
        self.notebook.add(items_frame, text="Items")
        
        # Parents tab - items with variants
        parents_frame = ttk.Frame(self.notebook)
        self.notebook.add(parents_frame, text="Parents")
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh())
        
        self.columns = ("name", "category", "unit", "cost_price", "selling_price", "quantity", "barcode")
        
        # Create tree widgets for both tabs
        self._create_tree_widget(items_frame, "items_tree")
        self._create_tree_widget(parents_frame, "parents_tree")
        
        # Set initial focus on items tab
        self.notebook.select(0)

        # Preview panel
        preview = ttk.Frame(self, padding=(12, 0))
        preview.grid(row=3, column=2, sticky=tk.N, padx=(8, 0))
        self.preview = preview
        self.preview_label = ttk.Label(preview, text="(No image)", anchor=tk.CENTER)
        self.preview_label.pack()
        self.low_stock_label = ttk.Label(preview, foreground="red")
        self.low_stock_label.pack(pady=(8, 0))

        # Bind tree selection events
        self.items_tree.bind("<<TreeviewSelect>>", lambda _evt: self._update_preview())
        self.parents_tree.bind("<<TreeviewSelect>>", lambda _evt: self._update_preview())

        # Bind resize to auto-fit (bind both the tree_frame and the top-level window)
        try:
            toplevel = self.winfo_toplevel()
            try:
                # add='+' to avoid clobbering other bindings when supported
                toplevel.bind('<Configure>', self._on_tree_frame_configure, add='+')
            except:
                toplevel.bind('<Configure>', self._on_tree_frame_configure)
        except:
            pass

        # Configure grid weights for proper resizing
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Initial refresh
        self.refresh()

    def _create_tree_widget(self, parent_frame: ttk.Frame, tree_name: str) -> None:
        """Create a tree widget with scrollbars in the given parent frame."""
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=8)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings")
        tree.grid(row=0, column=0, sticky=tk.NSEW)
        
        # Set tree reference
        if tree_name == "items_tree":
            self.items_tree = tree
        elif tree_name == "parents_tree":
            self.parents_tree = tree

        # Vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=vsb.set)
        vsb.grid(row=0, column=1, sticky=tk.NS)

        # Horizontal scrollbar
        xscrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscroll=xscrollbar.set)
        xscrollbar.grid(row=1, column=0, sticky=tk.EW, columnspan=1, pady=(4, 0))

        # Configure columns
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
            tree.column(col, width=120, minwidth=80, anchor=tk.W, stretch=False)
        
        # Make important columns wider
        tree.column("name", width=280, minwidth=140, anchor=tk.W, stretch=True)
        tree.column("category", width=160, minwidth=100, anchor=tk.W, stretch=True)
        tree.column("unit", width=90, minwidth=50, anchor=tk.W, stretch=False)
        tree.column("cost_price", width=100, minwidth=70, anchor=tk.E, stretch=False)
        tree.column("selling_price", width=100, minwidth=70, anchor=tk.E, stretch=False)
        tree.column("quantity", width=80, minwidth=50, anchor=tk.E, stretch=False)
        tree.column("barcode", width=180, minwidth=80, anchor=tk.W, stretch=False)

        # Configure tag colors
        tree.tag_configure("low", foreground="red")
        tree.tag_configure("even", background="#F9F9F9")
        tree.tag_configure("odd", background="#FFFFFF")

        # Bind sorting
        for col in self.columns:
            tree.heading(col, command=lambda c=col: self._sort_by_column(c))

        parent_frame.rowconfigure(0, weight=1)
        parent_frame.columnconfigure(0, weight=1)
        self.bind("<Delete>", lambda e: self._delete_selected_checked())
        self.focus_set()

    def _toggle_preview(self):
        if self.preview_visible.get():
            self.preview.grid(row=3, column=2, sticky=tk.N, padx=(8, 0))
        else:
            self.preview.grid_forget()

    def _clear_search(self):
        """Clear the search field and refresh the inventory."""
        self.search_var.set("")
        self.refresh()

    def _sort_by_column(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        self.refresh()

    def refresh(self) -> None:
        if not hasattr(self, 'items_tree') or not hasattr(self, 'parents_tree'):
            return  # UI not built yet
        
        self.loading_var.set("Loading...")
        
        # Determine which tab is active
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Items tab
            tree = self.items_tree
            show_parents_only = False
            show_variants_inline = True  # Show variants as individual rows in Items tab
        else:  # Parents tab
            tree = self.parents_tree
            show_parents_only = True
            show_variants_inline = False  # Show variants as children in Parents tab
        
        search = self.search_var.get().strip()
        
        # Clear the tree
        for row in tree.get_children():
            tree.delete(row)
        
        rows = items.list_items(search=search if search else None)
        
        # Apply filters
        filtered_rows = []
        for row in rows:
            cat = self.category_var.get()
            if cat != "All" and row.get("category") != cat:
                continue
            
            stock = self.stock_var.get()
            qty = row["quantity"]
            low_thresh = row.get("low_stock_threshold") or self.LOW_STOCK_THRESHOLD
            if stock == "Low Stock":
                if row.get("is_special_volume"):
                    unit_size = float(row.get("unit_size_ml") or 1)
                    actual_volume = qty * unit_size
                    if actual_volume > low_thresh:
                        continue
                elif qty > low_thresh:
                    continue
            elif stock == "Out of Stock":
                if qty > 0:
                    continue
            elif stock == "In Stock":
                if qty <= 0:
                    continue
            
            # Filter based on tab
            from modules import variants as variants_module
            has_variants = variants_module.has_variants(row["item_id"])
            if show_parents_only and not has_variants:
                continue  # Parents tab: only show items with variants
            elif not show_parents_only and not show_variants_inline and has_variants:
                continue  # Items tab without inline variants: only show items without variants
            # For Items tab with inline variants, show all items (variants will be handled in display logic)
            
            filtered_rows.append(row)
        
        rows = filtered_rows
        
        # Sort
        if self.sort_column:
            def sort_key(r):
                val = r.get(self.sort_column, "")
                if self.sort_column in ["cost_price", "selling_price", "quantity"]:
                    try:
                        return float(val) if isinstance(val, str) else val
                    except:
                        return 0
                elif isinstance(val, str):
                    return val.lower()
                return val
            rows.sort(key=sort_key, reverse=self.sort_reverse)
        
        self.count_var.set(f"Items: {len(rows)}")
        from utils.security import get_currency_code
        global_currency = get_currency_code()

        for i, row in enumerate(rows):
            tags = []
            # Skip low stock check for catalog-only items (parents with variants)
            if not row.get("is_catalog_only"):
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

            unit = row.get("unit_of_measure", "pieces")

            # For Parents tab, show parent with variants as children
            if show_parents_only:
                from modules import variants as variants_module
                vars_list = variants_module.list_variants(row["item_id"])
                
                # Calculate aggregated quantity
                agg_qty = 0
                agg_volume = 0.0
                for v in vars_list:
                    q = int(v.get("quantity") or 0)
                    agg_qty += q
                    if row.get("is_special_volume"):
                        unit_size = float(row.get("unit_size_ml") or 1)
                        agg_volume += q * unit_size

                # Choose qty display (respecting special volume)
                if row.get("is_special_volume"):
                    qty_display = f"{agg_volume}"
                else:
                    qty_display = str(agg_qty)

                parent_iid = f"parent-{row['item_id']}"
                tree.insert(
                    "",
                    tk.END,
                    iid=parent_iid,
                    values=(row["name"], row.get("category", ""), unit, "", "", qty_display, ""),
                    tags=tuple(tags),
                )

                # Insert each variant as child row
                for v in vars_list:
                    v_qty = int(v.get("quantity") or 0)
                    v_cost = v.get("cost_price") if isinstance(v.get("cost_price"), (int, float)) else 0.0
                    v_price = v.get("selling_price") if isinstance(v.get("selling_price"), (int, float)) else 0.0
                    v_name = f"{row.get('name')} — {v.get('variant_name')}"
                    variant_iid = f"variant-{row['item_id']}-{v.get('variant_id')}"
                    
                    # Check variant low stock
                    variant_tags = []
                    v_threshold = v.get("low_stock_threshold") or self.LOW_STOCK_THRESHOLD
                    if v_qty <= v_threshold:
                        variant_tags.append("low")
                    if i % 2 == 0:
                        variant_tags.append("even")
                    else:
                        variant_tags.append("odd")
                    
                    tree.insert(
                        parent_iid,
                        tk.END,
                        iid=variant_iid,
                        values=(v_name, row.get("category", ""), unit, f"{global_currency} {v_cost:.4f}", f"{global_currency} {v_price:.4f}", str(v_qty), ""),
                        tags=tuple(variant_tags),
                    )
                continue

            # For Items tab with inline variants, show variants as individual rows
            if show_variants_inline and has_variants:
                from modules import variants as variants_module
                vars_list = variants_module.list_variants(row["item_id"])

                # If parent is catalog-only, show variants as top-level rows
                if row.get("is_catalog_only"):
                    for v in vars_list:
                        v_qty = int(v.get("quantity") or 0)
                        v_cost = v.get("cost_price") if isinstance(v.get("cost_price"), (int, float)) else 0.0
                        v_price = v.get("selling_price") if isinstance(v.get("selling_price"), (int, float)) else 0.0
                        v_name = f"{row.get('name')} — {v.get('variant_name')}"
                        variant_iid = f"variant-{row['item_id']}-{v.get('variant_id')}"
                        
                        # Check variant low stock
                        variant_tags = []
                        v_threshold = v.get("low_stock_threshold") or self.LOW_STOCK_THRESHOLD
                        if v_qty <= v_threshold:
                            variant_tags.append("low")
                        if i % 2 == 0:
                            variant_tags.append("even")
                        else:
                            variant_tags.append("odd")
                        
                        tree.insert(
                            "",
                            tk.END,
                            iid=variant_iid,
                            values=(v_name, row.get("category", ""), unit, f"{global_currency} {v_cost:.4f}", f"{global_currency} {v_price:.4f}", str(v_qty), ""),
                            tags=tuple(variant_tags),
                        )
                    continue
                else:
                    # Show parent item first, then variants
                    # Calculate aggregated quantity for parent
                    agg_qty = 0
                    agg_volume = 0.0
                    for v in vars_list:
                        q = int(v.get("quantity") or 0)
                        agg_qty += q
                        if row.get("is_special_volume"):
                            unit_size = float(row.get("unit_size_ml") or 1)
                            agg_volume += q * unit_size

                    # Choose qty display (respecting special volume)
                    if row.get("is_special_volume"):
                        qty_display = f"{agg_volume}"
                    else:
                        qty_display = str(agg_qty)

                    parent_iid = f"parent-{row['item_id']}"
                    tree.insert(
                        "",
                        tk.END,
                        iid=parent_iid,
                        values=(row["name"], row.get("category", ""), unit, "", "", qty_display, ""),
                        tags=tuple(tags),
                    )

                    # Insert each variant as child row
                    for v in vars_list:
                        v_qty = int(v.get("quantity") or 0)
                        v_cost = v.get("cost_price") if isinstance(v.get("cost_price"), (int, float)) else 0.0
                        v_price = v.get("selling_price") if isinstance(v.get("selling_price"), (int, float)) else 0.0
                        v_name = f"{row.get('name')} — {v.get('variant_name')}"
                        variant_iid = f"variant-{row['item_id']}-{v.get('variant_id')}"
                        
                        # Check variant low stock
                        variant_tags = []
                        v_threshold = v.get("low_stock_threshold") or self.LOW_STOCK_THRESHOLD
                        if v_qty <= v_threshold:
                            variant_tags.append("low")
                        if i % 2 == 0:
                            variant_tags.append("even")
                        else:
                            variant_tags.append("odd")
                        
                        tree.insert(
                            parent_iid,
                            tk.END,
                            iid=variant_iid,
                            values=(v_name, row.get("category", ""), unit, f"{global_currency} {v_cost:.4f}", f"{global_currency} {v_price:.4f}", str(v_qty), ""),
                            tags=tuple(variant_tags),
                        )
                    continue

            # For Items tab without inline variants, show regular items only
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
                    cost_per_unit = (row["cost_price"] / unit_size) if unit_size > 0 else row["cost_price"]
                    price_per_unit = (row["selling_price"] / unit_size) if unit_size > 0 else row["selling_price"]
                else:
                    cost_per_unit = row["cost_price"]
                    price_per_unit = row["selling_price"]
            except Exception:
                cost_per_unit = row["cost_price"]
                price_per_unit = row["selling_price"]
            
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
            
            tree.insert(
                "",
                tk.END,
                iid=str(row["item_id"]),
                values=(row["name"], row.get("category", ""), unit, f"{global_currency} {cost_per_unit:.4f}{unit_label}", f"{global_currency} {price_per_unit:.4f}{unit_label}", qty_display, row.get("barcode", "")),
                tags=tuple(tags),
            )
        
        # Configure tag colors
        tree.tag_configure("low", foreground="red")
        tree.tag_configure("even", background="#F9F9F9")
        tree.tag_configure("odd", background="#FFFFFF")
        
        # Apply saved column visibility (if any)
        try:
            vis = self._load_visible_columns()
            if not vis:
                vis = list(self.DEFAULT_VISIBLE_COLUMNS)
            self._apply_visible_columns(vis)
        except Exception:
            pass
        
        # Auto-fit columns to contents
        try:
            self._autofit_columns()
        except Exception:
            pass
        
        self.loading_var.set("")
        if hasattr(self, 'preview_label') and self.preview_label:
            self._update_preview()
        self._update_low_stock_label()

    def _selected_id(self) -> int | None:
        # Determine which tab is active
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Items tab
            tree = self.items_tree
        else:  # Parents tab
            tree = self.parents_tree
        
        sel = tree.selection()
        if not sel:
            return None
        sid = sel[0]
        # Handle new iid formats: numeric, parent-<id>, variant-<itemid>-<variantid>
        try:
            return int(sid)
        except Exception:
            try:
                if isinstance(sid, str) and sid.startswith("parent-"):
                    return int(sid.split("-")[1])
                if isinstance(sid, str) and sid.startswith("variant-"):
                    # variant-<itemid>-<variantid>
                    parts = sid.split("-")
                    return int(parts[1])
            except Exception:
                return None
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
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected item?"):
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
        
        # Check if editing a variant (only applies to Parents tab)
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 1:  # Parents tab - check for variant selection
            tree = self.parents_tree
            sel = tree.selection()
            if sel and sel[0].startswith("variant-"):
                parts = sel[0].split("-")
                if len(parts) >= 3:
                    variant_id = int(parts[2])
                    from modules import variants as variants_module
                    variant = variants_module.get_variant(variant_id)
                    if variant:
                        # Create pseudo record for variant editing
                        record = {
                            'item_id': record['item_id'],
                            'name': f"{record['name']} — {variant['variant_name']}",
                            'category': record['category'],
                            'unit_of_measure': record['unit_of_measure'],
                            'cost_price': variant.get('cost_price', 0),
                            'selling_price': variant.get('selling_price', 0),
                            'quantity': variant.get('quantity', 0),
                            'barcode': variant.get('barcode', ''),
                            'low_stock_threshold': variant.get('low_stock_threshold', 5),
                            'is_catalog_only': record.get('is_catalog_only', False),
                            'variant_id': variant_id,  # Flag for dialog to save as variant
                        }
        
        self._open_item_dialog(title="Edit Item", existing=record)

    def _add_item_dialog(self) -> None:
        self._open_item_dialog(title="Add Item", existing=None)

    def _open_item_dialog(self, *, title: str, existing: dict | None) -> None:
        """Open simplified item dialog for creating/editing items."""
        from ui.simplified_item_dialog import SimplifiedItemDialog

        # Determine user role for price editing permissions
        root = self.winfo_toplevel()
        user = getattr(root, "current_user", None)
        is_admin = user and user.get("role") == "admin"

        # Create and show the simplified dialog
        dialog = SimplifiedItemDialog(self, existing=existing, is_admin=is_admin)
        dialog.show()

        # Refresh the inventory list after dialog closes
        self.refresh()

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
            # Check permissions
            root = self.winfo_toplevel()
            current_user = getattr(root, 'current_user', {})
            from modules import permissions
            if not permissions.has_permission(current_user, 'add_categories'):
                messagebox.showerror("Permission Denied", "You do not have permission to add categories")
                return
                
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
            # Check permissions
            root = self.winfo_toplevel()
            current_user = getattr(root, 'current_user', {})
            from modules import permissions
            if not permissions.has_permission(current_user, 'delete_categories'):
                messagebox.showerror("Permission Denied", "You do not have permission to delete categories")
                return
                
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
        if not hasattr(self, 'preview_label') or not self.preview_label:
            return  # UI not fully built yet
        
        # Determine which tab is active
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Items tab
            tree = self.items_tree
        else:  # Parents tab
            tree = self.parents_tree
        
        if not tree.get_children():
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

    # Column visibility persistence and helpers
    def _load_visible_columns(self) -> list[str] | None:
        try:
            from database.init_db import get_setting
            val = get_setting("inventory.columns.visible")
            if not val:
                return None
            return json.loads(val)
        except Exception:
            return None

    def _save_visible_columns(self, visible: list[str]) -> None:
        try:
            from database.init_db import set_setting
            set_setting("inventory.columns.visible", json.dumps(visible))
        except Exception:
            pass

    def _apply_visible_columns(self, visible: list[str]) -> None:
        # Ensure columns preserve ordering defined in self.columns
        ordered = [c for c in self.columns if c in visible]
        if not ordered:
            ordered = list(self.columns)
        try:
            # Apply to both trees
            for tree in [self.items_tree, self.parents_tree]:
                tree['displaycolumns'] = ordered
                # Force geometry update and reset horizontal view so scrollbar matches
                try:
                    tree.update_idletasks()
                except Exception:
                    pass
                try:
                    tree.xview_moveto(0)
                except Exception:
                    pass
        except Exception:
            # Fallback: set headings visible via column widths
            for col in self.columns:
                if col in ordered:
                    self.tree.column(col, stretch=True)
                else:
                    self.tree.column(col, stretch=False, width=0, minwidth=0)

        # Show a hint when only one column is visible to help users recover
        try:
            if len(ordered) < 2:
                self.columns_hint.configure(text="Only 1 column visible — open Columns… to show more")
            else:
                self.columns_hint.configure(text="")
        except Exception:
            pass
    def _restore_recommended_columns(self) -> None:
        """Restore recommended visible columns and persist the change."""
        visible = list(self.DEFAULT_VISIBLE_COLUMNS)
        self._save_visible_columns(visible)
        self._apply_visible_columns(visible)
        try:
            self._autofit_columns()
        except Exception:
            pass
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            # Reset scroll position for both trees
            self.items_tree.xview_moveto(0)
            self.parents_tree.xview_moveto(0)
        except Exception:
            pass

    def _open_columns_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.transient(self.winfo_toplevel())
        dialog.title("Inventory Columns")
        set_window_icon(dialog)
        dialog.grab_set()

        current = set(self._load_visible_columns() or list(self.columns))
        vars_map = {}
        for col in self.columns:
            v = tk.BooleanVar(value=(col in current))
            vars_map[col] = v
            ttk.Checkbutton(dialog, text=col.capitalize(), variable=v).pack(anchor=tk.W, padx=12, pady=6)

        def do_save():
            visible = [c for c, var in vars_map.items() if var.get()]
            if not visible:
                messagebox.showerror("Columns", "At least one column must be visible")
                return
            self._save_visible_columns(visible)
            self._apply_visible_columns(visible)
            self._autofit_columns()
            try:
                self.update_idletasks()
            except Exception:
                pass
            try:
                self.tree.xview_moveto(0)
            except Exception:
                pass
            dialog.destroy()

        def do_reset():
            for c, var in vars_map.items():
                var.set(c in self.columns)

        def do_restore():
            # Restore defaults and update checkboxes
            visible = list(self.DEFAULT_VISIBLE_COLUMNS)
            for c, var in vars_map.items():
                var.set(c in visible)
            # Persist and apply
            self._restore_recommended_columns()
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, pady=(8, 12))
        ttk.Button(btns, text="Save", command=do_save).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Reset", command=do_reset).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Restore recommended", command=do_restore).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=8)

    def _autofit_columns(self, max_rows: int = 200, padding: int | None = None) -> None:
        try:
            # Determine which tab is active
            current_tab = self.notebook.index(self.notebook.select())
            if current_tab == 0:  # Items tab
                tree = self.items_tree
                tree_frame = self.items_tree.master  # The frame containing the tree
            else:  # Parents tab
                tree = self.parents_tree
                tree_frame = self.parents_tree.master  # The frame containing the tree
            
            font = tkfont.Font()
            pad = padding if padding is not None else self.AUTOFIT_PADDING
            # Determine items to sample (header + first N visible rows)
            visible = list(tree['displaycolumns'] or list(self.columns))
            rows = list(tree.get_children())[:max_rows]

            widths: dict[str, int] = {}
            for col in visible:
                # header width
                hdr = tree.heading(col, option='text') or col
                maxw = font.measure(str(hdr))
                # sample cell widths
                for r in rows:
                    try:
                        val = tree.set(r, col)
                    except Exception:
                        val = ''
                    w = font.measure(str(val))
                    if w > maxw:
                        maxw = w
                minw = int(tree.column(col, option='minwidth') or 20)
                col_cap = self.COLUMN_MAX_WIDTHS.get(col, self.AUTOFIT_MAX_COL_WIDTH)
                neww = max(minw, maxw + pad)
                neww = min(neww, col_cap)
                widths[col] = neww

            # If there is extra available space, distribute to stretchable columns
            try:
                avail = int(tree_frame.winfo_width() or tree.winfo_width() or 0)
            except Exception:
                avail = int(tree.winfo_width() or 0)
            total = sum(widths.values())
            if avail and avail > total:
                extra = avail - total
                stretch_cols = [c for c in visible if tree.column(c, option='stretch')]
                if not stretch_cols:
                    stretch_cols = ['name'] if 'name' in visible else visible[:1]
                weight_total = sum(max(1, widths.get(c, 1)) for c in stretch_cols)
                for c in stretch_cols:
                    add = int(extra * (max(1, widths.get(c, 1)) / weight_total))
                    widths[c] = widths.get(c, 0) + add
                # fix any rounding differences
                remaining = avail - sum(widths.values())
                if remaining > 0 and stretch_cols:
                    widths[stretch_cols[0]] += remaining

            # Apply computed widths
            for col, w in widths.items():
                tree.column(col, width=int(w))
        except Exception:
            # Keep original widths on failure
            pass

    def _on_tree_frame_configure(self, _evt=None) -> None:
        # Debounced resize handler -> auto-fit columns after user stops resizing
        try:
            if hasattr(self, '_resize_after_id') and self._resize_after_id:
                self.after_cancel(self._resize_after_id)
        except Exception:
            pass
        self._resize_after_id = self.after(300, lambda: self._autofit_columns())


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
        
        # Check if selected item is a variant - variants cannot have their own variants
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 1:  # Parents tab - check for variant selection
            tree = self.parents_tree
            sel = tree.selection()
            if sel and sel[0].startswith("variant-"):
                messagebox.showerror("Error", "Variants cannot have their own variants. Select the parent item instead.")
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
