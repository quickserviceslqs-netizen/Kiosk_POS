"""POS cart UI skeleton."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import items
from modules import portions
from modules import units_of_measure as uom
from ui.checkout import CheckoutDialog
from utils.security import get_currency_code
from utils.images import load_thumbnail


class PosFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, *, cart_state: dict | None = None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.search_var = tk.StringVar()
        self.barcode_var = tk.StringVar()
        self.payment_var = tk.StringVar(value="0")
        self.vat_rate = 0.16  # 16% VAT
        self.vat_var = tk.StringVar(value="0.00")
        self.discount_var = tk.StringVar(value="0")
        self.payment_method_var = tk.StringVar(value="Cash")
        self.cart_state = cart_state or {"items": [], "suspended": []}
        self.cart = self.cart_state.setdefault("items", [])
        self.suspended_carts = self.cart_state.setdefault("suspended", [])
        # Seed cart id sequence so resumed carts get unique rows
        self._cart_seq = max((e.get("cart_id", 0) for e in self.cart), default=0)
        self.tree = None
        self.total_var = tk.StringVar(value="0.00")
        self.subtotal_var = tk.StringVar(value="0.00")
        self.change_var = tk.StringVar(value="0.00")
        self.currency_symbol = get_currency_code()
        self._build_ui()
        # Populate once on startup; further refreshes are debounced.
        self._refresh_items()
        self._preview_cache: dict[int, tk.PhotoImage] = {}
        self._refreshing = False
        self._ensure_after_id = None
        # Refresh when the frame becomes visible again.
        self.bind("<Map>", lambda _e: self.ensure_populated())
        self.bind("<FocusIn>", lambda _e: self.ensure_populated())
        self.bind("<Visibility>", lambda _e: self.ensure_populated())

    def _build_ui(self) -> None:
        # grid layout to avoid bottom clipping; two-column layout (left: catalog, right: cart)
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self.grid_propagate(True)  # Allow frame to expand

        top = ttk.Frame(self)
        top.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 6))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Search").grid(row=0, column=0, padx=4, sticky=tk.W)
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=32)
        search_entry.grid(row=0, column=1, padx=4, sticky=tk.EW)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_items())

        ttk.Label(top, text="Barcode").grid(row=0, column=2, padx=4, sticky=tk.W)
        barcode_entry = ttk.Entry(top, textvariable=self.barcode_var, width=20)
        barcode_entry.grid(row=0, column=3, padx=4, sticky=tk.W)
        barcode_entry.bind("<Return>", lambda _e: self._add_by_barcode())

        # Left: Items list with scrollbar
        items_frame = ttk.Frame(self)
        items_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 8), padx=(0, 8))
        items_frame.columnconfigure(0, weight=1)
        items_frame.columnconfigure(1, weight=0)
        items_frame.rowconfigure(0, weight=1)
        self.items_list = ttk.Treeview(items_frame, columns=("name", "price", "qty"), show="headings", height=18)
        self.items_list.heading("name", text="Item")
        self.items_list.heading("price", text="Price")
        self.items_list.heading("qty", text="Stock")
        self.items_list.column("name", width=260, minwidth=160, anchor=tk.W, stretch=True)
        self.items_list.column("price", width=110, minwidth=80, anchor=tk.E, stretch=True)
        self.items_list.column("qty", width=80, minwidth=60, anchor=tk.E, stretch=True)
        self.items_list.grid(row=0, column=0, sticky=tk.NSEW)
        items_scroll = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_list.yview)
        items_scroll.grid(row=0, column=1, sticky=tk.NS)
        xscroll = ttk.Scrollbar(items_frame, orient=tk.HORIZONTAL, command=self.items_list.xview)
        xscroll.grid(row=1, column=0, sticky=tk.EW)
        self.items_list.configure(yscroll=items_scroll.set, xscroll=xscroll.set)
        self.items_list.bind("<Double-1>", lambda _e: self._add_selected_item())
        self.items_list.bind("<<TreeviewSelect>>", lambda _e: self._update_item_preview())

        # Catalog preview panel
        self.item_preview = ttk.Frame(items_frame, padding=(10, 0))
        self.item_preview.grid(row=0, column=2, sticky=tk.N, padx=(8, 0))
        self.item_preview_label = ttk.Label(self.item_preview, text="(No image)", anchor=tk.CENTER)
        self.item_preview_label.pack()
        self.item_preview_meta = ttk.Label(self.item_preview, text="", foreground="gray")
        self.item_preview_meta.pack(pady=(6, 0))

        # Right: Cart section
        cart_container = ttk.Frame(self)
        cart_container.grid(row=1, column=1, sticky=tk.NSEW)
        cart_container.columnconfigure(0, weight=1)
        cart_container.rowconfigure(1, weight=1)

        ttk.Label(cart_container, text="Cart", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        cart_frame = ttk.Frame(cart_container)
        cart_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 6))
        cart_frame.columnconfigure(0, weight=1)
        cart_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(cart_frame, columns=("name", "price", "qty", "line_total"), show="headings", height=14)
        for col, txt, width, anchor in [
            ("name", "Item", 180, tk.W),
            ("price", "Price", 80, tk.E),
            ("qty", "Qty", 60, tk.E),
            ("line_total", "Total", 90, tk.E),
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=width, anchor=anchor, stretch=True)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        cart_scroll = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.tree.yview)
        cart_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscroll=cart_scroll.set)
        self.tree.bind("<Double-1>", lambda _e: self._double_click_cart())

        cart_btns = ttk.Frame(cart_container)
        cart_btns.grid(row=2, column=0, sticky=tk.W, pady=(4, 6))
        ttk.Button(cart_btns, text="Qty +", width=6, command=lambda: self._adjust_qty(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_btns, text="Qty -", width=6, command=lambda: self._adjust_qty(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_btns, text="Remove Item", command=self._remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_btns, text="Clear Cart", command=self._clear_cart).pack(side=tk.LEFT, padx=2)

        totals = ttk.Frame(cart_container)
        totals.grid(row=3, column=0, sticky=tk.EW, pady=(4, 6))
        totals.columnconfigure(1, weight=1)
        ttk.Label(totals, text="Subtotal:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(totals, textvariable=self.subtotal_var, font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

        ttk.Label(totals, text="VAT:").grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        ttk.Label(totals, textvariable=self.vat_var).grid(row=1, column=1, sticky=tk.W, padx=(8, 0))

        ttk.Label(totals, text="Discount (%):").grid(row=2, column=0, sticky=tk.W, pady=(2, 0))
        discount_entry = ttk.Entry(totals, textvariable=self.discount_var, width=8)
        discount_entry.grid(row=2, column=1, sticky=tk.W, padx=(8, 0))
        discount_entry.bind("<KeyRelease>", lambda _e: self._refresh_cart())

        ttk.Label(totals, text="Payment Method:").grid(row=3, column=0, sticky=tk.W, pady=(2, 0))
        payment_combo = ttk.Combobox(totals, textvariable=self.payment_method_var, values=["Cash", "M-Pesa", "Card"], width=10, state="readonly")
        payment_combo.grid(row=3, column=1, sticky=tk.W, padx=(8, 0))

        ttk.Label(totals, text="Total:").grid(row=4, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Label(totals, textvariable=self.total_var, font=("Segoe UI", 12, "bold")).grid(row=4, column=1, sticky=tk.W, padx=(8, 0))

        btn_frame = ttk.Frame(cart_container)
        btn_frame.grid(row=4, column=0, sticky=tk.W, pady=(6, 4))
        ttk.Button(btn_frame, text="Checkout / Save Sale", command=self._checkout).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Suspend Cart", command=self._suspend_cart).pack(side=tk.LEFT, padx=2)
        self.resume_btn = ttk.Button(btn_frame, text="Resume Cart", command=self._resume_cart)
        self.resume_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Open Cart", command=self._goto_cart).pack(side=tk.LEFT, padx=2)
        self._update_resume_btn()

    def _update_resume_btn(self):
        if self.suspended_carts:
            self.resume_btn.state(["!disabled"])
        else:
            self.resume_btn.state(["disabled"])

    def _thumb_for_item(self, item: dict) -> tk.PhotoImage | None:
        item_id = item.get("item_id")
        if not item_id:
            return None
        if item_id in self._preview_cache:
            return self._preview_cache[item_id]
        thumb = load_thumbnail(item.get("image_path")) if item.get("image_path") else None
        if thumb:
            self._preview_cache[item_id] = thumb
        return thumb

    # Items search/add
    def _refresh_items(self) -> None:
        search = self.search_var.get().strip()
        for row in self.items_list.get_children():
            self.items_list.delete(row)
        rows = items.list_items(search=search if search else None)
        for row in rows:
            unit = (row.get("unit_of_measure") or "").lower()
            is_special = row.get("is_special_volume", 0)
            unit_size = float(row.get("unit_size_ml") or 1)  # Size in base units (e.g., 1 = 1L)
            cost = row["cost_price"] if isinstance(row["cost_price"], (int, float)) else 0.0
            price = row["selling_price"] if isinstance(row["selling_price"], (int, float)) else 0.0
            
            # Use configured conversion factor and abbreviation for display
            try:
                unit_info = uom.get_unit_by_name(unit) or {}
                conv_factor = float(unit_info.get("conversion_factor", 1) or 1)
                abbr = unit_info.get("abbreviation") or ""
                base_unit = (unit_info.get("base_unit") or "").lower()
            except Exception:
                conv_factor = items._get_unit_multiplier(unit)
                abbr = ""
                base_unit = ""

            # Price per large unit = bulk price / package_size
            if unit_size > 0:
                price_per_unit = price / unit_size
            else:
                price_per_unit = price

            # Always show price per large unit (e.g., per L/kg/m or per pcs)
            suffix = abbr or unit or "unit"
            price_display = f"{self.currency_symbol} {price_per_unit:.2f}/{suffix}"

            # Match Inventory display: for fractional items, show total in base units (e.g., 5.0 L, 500 ml)
            if is_special:
                try:
                    unit_lower = unit.lower()
                    # Use unit_size and conv_factor to compute small unit total
                    total_small = row["quantity"] * unit_size * conv_factor
                    # Liters -> ml/L
                    if unit_lower in ("litre", "liter", "liters", "litres", "l"):
                        if total_small >= 1000:
                            qty_display = f"{total_small / 1000:.1f} L"
                        else:
                            qty_display = f"{total_small:.0f} ml"
                    # Kilograms -> g/kg
                    elif unit_lower in ("kilogram", "kilograms", "kg", "kgs"):
                        if total_small >= 1000:
                            qty_display = f"{total_small / 1000:.1f} kg"
                        else:
                            qty_display = f"{total_small:.0f} g"
                    # Meters -> cm/m
                    elif unit_lower in ("meter", "meters", "metre", "metres", "m"):
                        if total_small >= 100:
                            qty_display = f"{total_small / 100:.1f} m"
                        else:
                            qty_display = f"{total_small:.0f} cm"
                    else:
                        qty_display = str(row["quantity"])
                except Exception:
                    qty_display = str(row["quantity"])
            else:
                qty_display = str(row["quantity"])
            
            self.items_list.insert("", tk.END, iid=str(row["item_id"]), values=(row["name"], price_display, qty_display))
        self._update_item_preview()

    def _add_selected_item(self) -> None:
        sel = self.items_list.selection()
        if not sel:
            return
        item_id = int(sel[0])
        record = items.get_item(item_id)
        if record:
            # Check if item has variants
            from modules import variants
            if variants.has_variants(item_id):
                self._show_variant_picker(record)
            elif record.get("is_special_volume"):
                self._sell_special_dialog(record)
            else:
                self._add_to_cart(record)
                self._update_item_preview(record)

    def _show_variant_picker(self, item: dict) -> None:
        """Show dialog to select variant when adding item with variants to cart."""
        from modules import variants
        from utils import set_window_icon
        
        variant_list = variants.list_variants(item["item_id"])
        if not variant_list:
            # Fallback if no variants found
            self._add_to_cart(item)
            return
        
        dialog = tk.Toplevel(self)
        dialog.withdraw()  # Hide until fully built
        dialog.title(f"Select Variant - {item['name']}")
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Select variant for: {item['name']}", font=("Segoe UI", 11, "bold")).pack(pady=(10, 6))
        
        # Variant list
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        
        columns = ("variant_name", "price")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree.heading("variant_name", text="Variant")
        tree.heading("price", text="Price")
        tree.column("variant_name", width=250)
        tree.column("price", width=150)
        
        for v in variant_list:
            if v.get("is_active", 1):
                tree.insert("", tk.END, iid=str(v["variant_id"]), 
                           values=(v["variant_name"], f"{self.currency_symbol} {v['selling_price']:.2f}"))
        
        def add_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Select Variant", "Please select a variant")
                return
            variant_id = int(sel[0])
            variant = next((v for v in variant_list if v["variant_id"] == variant_id), None)
            if variant:
                # Add variant to cart (with variant info)
                self._add_variant_to_cart(item, variant)
                dialog.destroy()
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Add to Cart", width=15, command=add_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", width=15, command=dialog.destroy).pack(side=tk.LEFT, padx=4)
        
        tree.bind("<Double-1>", lambda _e: add_selected())
        
        # Set geometry and show dialog after content is built
        dialog.update_idletasks()
        dialog.geometry("500x400")
        dialog.deiconify()  # Show after fully built

    def _sell_special_dialog(self, item: dict) -> None:
        """Prompt for preset portion or custom cash amount for fractional-sale items."""
        from utils import set_window_icon
        from modules import portions

        fresh = items.get_item(item["item_id"]) or item
        unit_of_measure = fresh.get("unit_of_measure", "pieces")
        unit_size = float(fresh.get("unit_size_ml") or 1)  # Size in base units (e.g., 20 = 20 liters)
        
        # Use stored price per smallest unit (e.g., price per ml)
        price_per_small = float(fresh.get("selling_price_per_unit") or fresh.get("price_per_ml") or 0)
        stock_containers = float(fresh.get("quantity", 0) or 0)  # Number of containers
        
        # Determine conversion and display units
        unit_lower = unit_of_measure.lower()
        conversions = {
            # Liters variations: multiplier from L to ml
            "liters": (1000, "ml", "L"), "litre": (1000, "ml", "L"), 
            "liter": (1000, "ml", "L"), "litres": (1000, "ml", "L"), "l": (1000, "ml", "L"),
            # Kilograms variations: multiplier from kg to g
            "kilograms": (1000, "g", "kg"), "kilogram": (1000, "g", "kg"), 
            "kg": (1000, "g", "kg"), "kgs": (1000, "g", "kg"),
            # Meters variations: multiplier from m to cm
            "meters": (100, "cm", "m"), "meter": (100, "cm", "m"),
            "metre": (100, "cm", "m"), "metres": (100, "cm", "m"), "m": (100, "cm", "m"),
        }
        multiplier, small_unit, base_unit = conversions.get(unit_lower, (1, unit_of_measure, unit_of_measure))
        
        # Calculate available stock in small units (ml/g/cm)
        available_small = max(0.0, stock_containers * unit_size * multiplier)
        available_base = available_small / multiplier if multiplier > 0 else available_small
        
        # Calculate price per base unit (L/kg/m) for display
        price_per_base = price_per_small * multiplier if multiplier > 0 else price_per_small
        
        # Get preset portions for this item
        preset_portions = portions.list_portions(fresh["item_id"])

        dialog = tk.Toplevel(self)
        dialog.withdraw()  # Hide until fully built
        dialog.title(f"Sell - {fresh['name']}")
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)

        main_frame = ttk.Frame(dialog, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info section
        ttk.Label(main_frame, text=f"Price per {base_unit}: {self.currency_symbol} {price_per_base:.2f}").pack(anchor=tk.W)
        ttk.Label(main_frame, text=f"Available: {available_base:.2f} {base_unit} ({available_small:.0f} {small_unit})").pack(anchor=tk.W, pady=(0, 8))

        # Preset portions section (if any exist)
        if preset_portions:
            ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
            ttk.Label(main_frame, text="Quick Select:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
            
            portions_frame = ttk.Frame(main_frame)
            portions_frame.pack(fill=tk.X, pady=(4, 8))
            
            # Configure columns to expand equally
            num_cols = min(len(preset_portions), 4)
            for col in range(num_cols):
                portions_frame.columnconfigure(col, weight=1)
            
            def add_preset(portion):
                if portion["portion_ml"] > available_small:
                    messagebox.showerror("Insufficient Stock", f"Not enough stock for {portion['portion_name']}")
                    return
                # Add preset portion to cart
                self._add_special_sale(
                    fresh, 
                    portion["portion_ml"], 
                    portion["selling_price"] / portion["portion_ml"],  # Price per ml for this portion
                    small_unit, 
                    multiplier,
                    preset_name=portion["portion_name"],
                    preset_price=portion["selling_price"],
                    portion_id=portion["portion_id"]
                )
                dialog.destroy()
            
            for i, portion in enumerate(preset_portions):
                btn_text = f"{portion['portion_name']}\n{self.currency_symbol} {portion['selling_price']:.0f}"
                btn = ttk.Button(
                    portions_frame, 
                    text=btn_text,
                    command=lambda p=portion: add_preset(p)
                )
                btn.grid(row=i // 4, column=i % 4, padx=3, pady=2, sticky="ew")

        # Custom amount section
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(main_frame, text="Custom Amount:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        amount_var = tk.StringVar(value="")
        qty_var = tk.StringVar(value="0")

        form = ttk.Frame(main_frame)
        form.pack(fill=tk.X, pady=(4, 8))
        ttk.Label(form, text="Cash amount:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        amt_entry = ttk.Entry(form, textvariable=amount_var, width=16)
        amt_entry.grid(row=0, column=1, sticky=tk.W)
        amt_entry.focus_set()

        ttk.Label(form, text="Will dispense:").grid(row=1, column=0, sticky=tk.W, padx=(0, 6), pady=(8, 0))
        qty_label = ttk.Label(form, textvariable=qty_var)
        qty_label.grid(row=1, column=1, sticky=tk.W, pady=(8, 0))

        def recompute(*_args):
            try:
                amt = float(amount_var.get() or 0)
                qty_small = amt / price_per_small if price_per_small else 0
                qty_small = min(qty_small, available_small)
                qty_var.set(f"{qty_small:.0f} {small_unit}" if qty_small >= 1 else f"{qty_small:.2f} {small_unit}")
            except ValueError:
                qty_var.set(f"0 {small_unit}")

        amount_var.trace_add("write", recompute)
        recompute()

        def on_confirm():
            if available_small <= 0:
                messagebox.showerror("Out of stock", "No stock available for this item")
                return
            try:
                amt = float(amount_var.get() or 0)
            except ValueError:
                messagebox.showerror("Invalid", "Enter a valid amount")
                return
            if amt <= 0:
                messagebox.showerror("Invalid", "Amount must be greater than zero")
                return
            if price_per_small <= 0:
                messagebox.showerror("Invalid", f"Price per {small_unit} is not set for this item")
                return

            qty_small = amt / price_per_small
            qty_small = min(qty_small, available_small)
            if qty_small <= 0:
                messagebox.showerror("Invalid", "Quantity to sell is zero")
                return

            self._add_special_sale(fresh, qty_small, price_per_small, small_unit, multiplier)
            dialog.destroy()

        btns = ttk.Frame(dialog, padding=12)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Add Custom", command=on_confirm).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)
        
        # Calculate dialog size based on content
        num_rows = (len(preset_portions) + 3) // 4 if preset_portions else 0
        height = 280 if not preset_portions else 320 + num_rows * 50
        width = 500 if preset_portions else 400
        dialog.update_idletasks()
        dialog.geometry(f"{width}x{height}")
        dialog.deiconify()  # Show after fully built

    def _add_by_barcode(self) -> None:
        code = self.barcode_var.get().strip()
        if not code:
            return
        matches = [i for i in items.list_items(search=code) if i.get("barcode") == code]
        if not matches:
            messagebox.showinfo("Barcode", "No matching item")
            return
        item = matches[0]
        if item.get("is_special_volume"):
            self._sell_special_dialog(item)
        else:
            self._add_to_cart(item)
            self._update_item_preview(item)
        self.barcode_var.set("")

    def _next_cart_id(self) -> int:
        if self._cart_seq == 0 and self.cart:
            self._cart_seq = max((e.get("cart_id", 0) for e in self.cart), default=0)
        self._cart_seq += 1
        return self._cart_seq

    # Cart operations
    def _add_to_cart(self, item: dict) -> None:
        # Check if item already exists in cart (non-special items only)
        for entry in self.cart:
            if entry["item_id"] == item["item_id"] and not entry.get("is_special_volume"):
                entry["quantity"] += 1
                self._refresh_cart()
                return
        
        # Item not in cart, add new entry
        cart_id = self._next_cart_id()
        self.cart.append(
            {
                "cart_id": cart_id,
                "item_id": item["item_id"],
                "name": item["name"],
                "price": item["selling_price"],
                "quantity": 1,
                "vat_rate": item.get("vat_rate", 16.0),
                "image_path": item.get("image_path"),
            }
        )
        self._refresh_cart()

    def _add_special_sale(self, item: dict, qty_small: float, price_per_unit: float, display_unit: str, multiplier: float = 1, preset_name: str = None, preset_price: float = None, portion_id: int = None) -> None:
        if qty_small <= 0:
            messagebox.showerror("Invalid", "Quantity invalid")
            return
        
        # Use preset price if provided, otherwise calculate from price_per_unit
        if preset_price is not None:
            total_price = preset_price
            effective_price_per_unit = preset_price / qty_small if qty_small > 0 else price_per_unit
        else:
            if price_per_unit <= 0:
                messagebox.showerror("Invalid", "Price per unit invalid")
                return
            total_price = qty_small * price_per_unit
            effective_price_per_unit = price_per_unit
        
        # Use stored cost_price_per_unit if available, otherwise calculate
        cost_per_unit = item.get("cost_price_per_unit")
        if cost_per_unit is None:
            try:
                unit_size = float(item.get("unit_size_ml", 1) or 1)
                cost_per_unit = float(item.get("cost_price", 0)) / (unit_size * multiplier)
            except Exception:
                cost_per_unit = 0.0

        # Display name: use preset name if available
        if preset_name:
            display_name = f"{item['name']} ({preset_name})"
        else:
            display_name = f"{item['name']} ({qty_small:.0f} {display_unit})"

        cart_id = self._next_cart_id()
        self.cart.append(
            {
                "cart_id": cart_id,
                "item_id": item["item_id"],
                "name": display_name,
                "price": effective_price_per_unit,
                "quantity": qty_small,
                "vat_rate": item.get("vat_rate", 16.0),
                "image_path": item.get("image_path"),
                "is_special_volume": True,
                "qty_ml": qty_small,
                "price_per_ml": effective_price_per_unit,
                "cost_price_override": cost_per_unit,
                "unit_size_ml": item.get("unit_size_ml") or 1,
                "unit_multiplier": multiplier,
                "display_unit": display_unit,
                "preset_name": preset_name,
                "preset_price": preset_price,
                "portion_id": portion_id,
            }
        )
        self._refresh_cart()

    def _add_variant_to_cart(self, item: dict, variant: dict) -> None:
        """Add a specific variant to cart."""
        from modules import variants
        
        # Check stock for the variant
        if variant["quantity"] <= 0:
            messagebox.showerror("Out of Stock", f"Variant '{variant['variant_name']}' is out of stock")
            return
        
        # Check if this exact variant is already in cart
        for entry in self.cart:
            if entry["item_id"] == item["item_id"] and entry.get("variant_id") == variant["variant_id"]:
                # Check if we have enough stock for additional quantity
                total_qty = entry["quantity"] + 1
                if total_qty > variant["quantity"]:
                    messagebox.showerror("Insufficient Stock", f"Not enough stock for variant '{variant['variant_name']}'. Available: {variant['quantity']}")
                    return
                entry.setdefault("cart_id", self._next_cart_id())
                entry["quantity"] += 1
                self._refresh_cart()
                return
        
        # Add new variant entry
        self.cart.append(
            {
                "cart_id": self._next_cart_id(),
                "item_id": item["item_id"],
                "variant_id": variant["variant_id"],
                "name": f"{item['name']} ({variant['variant_name']})",
                "price": variant["selling_price"],
                "quantity": 1,
                "vat_rate": item.get("vat_rate", 16.0),
                "image_path": item.get("image_path"),
            }
        )
        self._refresh_cart()

    def _refresh_cart(self) -> None:
        # Ensure every entry has a unique cart_id for the tree iid
        for entry in self.cart:
            if "cart_id" not in entry:
                entry["cart_id"] = self._next_cart_id()

        for row in self.tree.get_children():
            self.tree.delete(row)
        subtotal = 0.0
        for entry in self.cart:
            # Determine item record for contextual data
            try:
                item_record = items.get_item(entry['item_id']) if entry.get('item_id') else None
            except Exception:
                item_record = None

            # Compute canonical line total
            if entry.get("is_special_volume"):
                # For fractional items: price is per small unit (e.g., per ml), quantity is in small units
                line_total = entry["price"] * entry["quantity"]
            else:
                # For non-special items: entry['price'] is bulk/package price, entry['quantity'] is number of individual units
                unit_size = 1
                try:
                    if item_record:
                        unit_size = float(item_record.get('unit_size_ml') or 1)
                except Exception:
                    unit_size = 1
                per_unit_price = entry["price"] / unit_size if unit_size > 0 else entry["price"]
                line_total = per_unit_price * entry["quantity"]

            # Persist line_total locally so VAT calc can reuse it
            entry['_line_total'] = line_total
            subtotal += line_total

            # Prepare display strings
            if entry.get("is_special_volume"):
                # For fractional items: show price per small unit (e.g., per ml) on the cart
                # entry['price'] is stored as price per small unit and entry['display_unit'] should be that small unit
                small_unit = entry.get('display_unit')
                if not small_unit:
                    try:
                        uinfo = uom.get_unit_by_name(item_record.get('unit_of_measure') if item_record else '') or {}
                        base_u = (uinfo.get('base_unit') or '').lower()
                        if 'mill' in base_u:
                            small_unit = 'ml'
                        elif 'gram' in base_u:
                            small_unit = 'g'
                        elif 'cent' in base_u:
                            small_unit = 'cm'
                        else:
                            small_unit = base_u or 'unit'
                    except Exception:
                        small_unit = entry.get('display_unit', 'unit')

                price_per_small = entry.get('price') or 0
                # Use more precision for small-unit prices (e.g., 0.012345/ml)
                price_display = f"{self.currency_symbol} {price_per_small:.6f}/{small_unit}"
                qty_display = f"{entry['quantity']:.2f} {small_unit}".strip()
            else:
                unit_name = item_record.get('unit_of_measure') if item_record else ''
                try:
                    uinfo = uom.get_unit_by_name(unit_name) or {}
                    abbr = uinfo.get('abbreviation') or unit_name or 'unit'
                except Exception:
                    abbr = unit_name or 'unit'
                price_per_large = entry['price'] / (float(item_record.get('unit_size_ml') or 1) if item_record else 1) if entry.get('price') else 0
                price_display = f"{self.currency_symbol} {price_per_large:.2f}/{abbr}"
                try:
                    if unit_name and unit_name.lower() in ("litre", "liter", "liters", "litres", "l", "kilogram", "kilograms", "kg", "kgs", "meter", "meters", "metre", "metres", "m"):
                        total_large = entry['quantity'] * float(item_record.get('unit_size_ml') or 1)
                        qty_display = f"{entry['quantity']} ({total_large:.2f} {abbr})"
                    else:
                        qty_display = str(entry["quantity"])
                except Exception:
                    qty_display = str(entry["quantity"])
            self.tree.insert(
                "",
                tk.END,
                iid=str(entry["cart_id"]),
                values=(entry["name"], price_display, qty_display, f"{self.currency_symbol} {line_total:.2f}"),
            )
        
        # Compute VAT based on each item's VAT rate and discount
        try:
            discount_pct = float(self.discount_var.get() or 0) / 100.0
        except ValueError:
            discount_pct = 0.0
        
        discount_amt = subtotal * discount_pct
        vat_base = subtotal - discount_amt
        
        # VAT with per-item rates
        vat_amt = 0.0
        for entry in self.cart:
            line_subtotal = entry.get('_line_total', entry.get("price", 0) * entry.get("quantity", 0))
            # Apply discount proportionally to this item
            item_discount = line_subtotal * discount_pct
            item_vat_base = line_subtotal - item_discount
            item_vat_rate = entry.get("vat_rate", 16.0) / 100.0
            vat_amt += item_vat_base * item_vat_rate
        
        total = vat_base + vat_amt  # Ensure subtotal already includes the discount adjustment
        
        self.subtotal_var.set(f"{self.currency_symbol} {subtotal:.2f}")
        self.vat_var.set(f"{self.currency_symbol} {vat_amt:.2f}")
        self.total_var.set(f"{self.currency_symbol} {total:.2f}")
        self._update_change()

    def _selected_cart_item(self):
        sel = self.tree.selection()
        if not sel:
            return None
        cart_id = int(sel[0])
        for entry in self.cart:
            if entry.get("cart_id") == cart_id:
                return entry
        return None

    def _update_item_preview(self, record: dict | None = None) -> None:
        if record is None:
            sel = self.items_list.selection()
            record = items.get_item(int(sel[0])) if sel else None
        if not record:
            self.item_preview_label.configure(text="(No image)", image="")
            self.item_preview_meta.configure(text="")
            return
        thumb = self._thumb_for_item(record)
        if thumb:
            self.item_preview_label.configure(image=thumb, text="")
            self.item_preview_label.image = thumb
        else:
            self.item_preview_label.configure(text="(No image)", image="")
            self.item_preview_label.image = None
        
        # Display stock in base units (not fractional)
        stock_display = str(record.get('quantity', 0))
        unit_of_measure = record.get('unit_of_measure', 'pieces')
        
        # For special volume items, show converted units (L, kg, m) - based on base_unit not fractional
        if record.get('is_special_volume'):
            unit_size = float(record.get('unit_size_ml') or 1)
            quantity = float(record.get('quantity') or 0)
            unit_lower = unit_of_measure.lower()
            
            if unit_lower in ('liters', 'litre', 'liter', 'litres', 'l'):
                total_liters = quantity * unit_size  # unit_size is in liters
                stock_display = f"{total_liters:.2f} L"
            elif unit_lower in ('kilograms', 'kilogram', 'kg', 'kgs'):
                total_kg = quantity * unit_size  # unit_size is in kg
                stock_display = f"{total_kg:.2f} kg"
            elif unit_lower in ('meters', 'meter', 'metre', 'metres', 'm'):
                total_m = quantity * unit_size  # unit_size is in meters
                stock_display = f"{total_m:.2f} m"
        
        # Show price per large/base unit (e.g., per L/kg/m or per piece)
        try:
            unit_info = uom.get_unit_by_name(unit_of_measure) or {}
            abbr = unit_info.get('abbreviation') or unit_of_measure
        except Exception:
            abbr = unit_of_measure
        item_sell = float(record.get('selling_price') or 0)
        unit_size = float(record.get('unit_size_ml') or 1)
        price_per_large = item_sell / unit_size if unit_size > 0 else item_sell
        meta = f"Stock: {stock_display}\nPrice: {self.currency_symbol} {price_per_large:.2f}/{abbr}"
        self.item_preview_meta.configure(text=meta)

    def _adjust_qty(self, delta: int) -> None:
        entry = self._selected_cart_item()
        if not entry:
            return
        if entry.get("is_special_volume"):
            messagebox.showinfo("Special item", "Adjust quantity by removing and re-adding the special volume item")
            return
        entry["quantity"] = max(1, entry["quantity"] + delta)
        self._refresh_cart()

    def _remove_selected(self) -> None:
        entry = self._selected_cart_item()
        if not entry:
            return
        self.cart[:] = [e for e in self.cart if e.get("cart_id") != entry.get("cart_id")]
        self._refresh_cart()

    def _double_click_cart(self) -> None:
        """On double-click, subtract one from the selected cart item's quantity; remove if zero."""
        entry = self._selected_cart_item()
        if not entry:
            return
        if entry.get("is_special_volume"):
            messagebox.showinfo("Special item", "Remove and re-add to adjust measured sales")
            return
        if entry["quantity"] > 1:
            entry["quantity"] -= 1
        else:
            self.cart[:] = [e for e in self.cart if e.get("cart_id") != entry.get("cart_id")]
        self._refresh_cart()

    def _clear_cart(self) -> None:
        self.cart.clear()
        self._refresh_cart()

    def _update_change(self) -> None:
        try:
            total = float(self.total_var.get())
            payment = float(self.payment_var.get() or 0)
        except ValueError:
            self.change_var.set("-")
            return
        self.change_var.set(f"{payment - total:.2f}")

    def _suspend_cart(self) -> None:
        if not self.cart:
            messagebox.showinfo("Suspend", "Cart is empty")
            return
        self.suspended_carts.append(self.cart[:])
        self.cart.clear()
        self._refresh_cart()
        self._update_resume_btn()
        messagebox.showinfo("Suspend", f"Cart suspended (total: {len(self.suspended_carts)} suspended)")

    def _resume_cart(self) -> None:
        if not self.suspended_carts:
            messagebox.showinfo("Resume", "No suspended carts")
            self._update_resume_btn()
            return
        recovered = self.suspended_carts.pop()
        self.cart.clear()
        self.cart.extend(recovered)
        self._refresh_cart()
        self._update_resume_btn()
        messagebox.showinfo("Resume", "Cart restored")

    def _checkout(self) -> None:
        if not self.cart:
            messagebox.showinfo("Checkout", "Cart is empty")
            return

        subtotal_str = self.subtotal_var.get()
        try:
            subtotal = float(subtotal_str.replace(self.currency_symbol, '').strip())
        except ValueError:
            messagebox.showerror("Checkout Error", f"Invalid subtotal value: {subtotal_str}")
            return

        discount_str = self.discount_var.get()
        try:
            discount_pct = float(discount_str.strip() or 0) / 100.0
        except ValueError:
            messagebox.showerror("Checkout Error", f"Invalid discount value: {discount_str}")
            return
        discount_amt = subtotal * discount_pct
        subtotal -= discount_amt

        vat_str = self.vat_var.get()
        try:
            vat_amt = float(vat_str.replace(self.currency_symbol, '').strip())
        except ValueError:
            messagebox.showerror("Checkout Error", f"Invalid VAT value: {vat_str}")
            return

        total = subtotal + vat_amt  # Ensure subtotal already includes the discount adjustment

        dialog = CheckoutDialog(
            self.winfo_toplevel(),
            cart=self.cart,
            subtotal=subtotal,
            vat_amount=vat_amt,
            total=total,
            discount=discount_amt,
            payment_method=self.payment_method_var.get(),
        )

        if dialog.result:
            self._clear_cart()
            self._refresh_items()

    def _goto_cart(self) -> None:
        root = self.winfo_toplevel()
        shell = getattr(root, "shell", None)
        if shell and hasattr(shell, "on_nav"):
            shell.on_nav("cart")
        elif shell and hasattr(shell, "_nav"):
            shell._nav("cart")
        else:
            messagebox.showinfo("Cart", "Cart view is not available")

    def refresh(self) -> None:
        currency = get_currency_code()
        # Update currency symbol in case it has changed
        self.currency_symbol = currency
        self.total_var.set(f"{currency} {float(self.total_var.get()):.2f}")
        self.subtotal_var.set(f"{currency} {float(self.subtotal_var.get()):.2f}")
        self.vat_var.set(f"{currency} {float(self.vat_var.get()):.2f}")
        self.change_var.set(f"{currency} {float(self.change_var.get()):.2f}")

    def refresh_all(self) -> None:
        """Refresh catalog and cart to prevent blank states when revisiting POS."""
        self._refresh_items()
        self._refresh_cart()

    def ensure_populated(self, *, force: bool = False) -> None:
        """Populate list if empty (used when returning from other views)."""
        if force:
            # Direct refresh with no timers to avoid second clicks.
            self._refreshing = True
            self._do_refresh(True)
            return

        if self._refreshing:
            return

        needs_items = not self.items_list.get_children()
        needs_cart = self.cart and (not self.tree.get_children())
        if not (needs_items or needs_cart):
            return

        self._refreshing = True
        self._do_refresh(needs_cart)

    def _do_refresh(self, refresh_cart: bool) -> None:
        try:
            self._refresh_items()
            if refresh_cart or (self.cart and not self.tree.get_children()):
                self._refresh_cart()
        finally:
            self._refreshing = False
            if self._ensure_after_id:
                try:
                    self.after_cancel(self._ensure_after_id)
                except Exception:
                    pass
            self._ensure_after_id = None
