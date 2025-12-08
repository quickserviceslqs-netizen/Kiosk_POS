"""POS cart UI skeleton."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import items
from ui.checkout import CheckoutDialog
from utils.security import get_currency_code


class PosFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.search_var = tk.StringVar()
        self.barcode_var = tk.StringVar()
        self.payment_var = tk.StringVar(value="0")
        self.vat_rate = 0.16  # 16% VAT
        self.vat_var = tk.StringVar(value="0.00")
        self.discount_var = tk.StringVar(value="0")
        self.payment_method_var = tk.StringVar(value="Cash")
        self.cart = []  # list of dicts: item_id, name, price, qty
        self.suspended_carts = []  # list of saved carts
        self.tree = None
        self.total_var = tk.StringVar(value="0.00")
        self.subtotal_var = tk.StringVar(value="0.00")
        self.change_var = tk.StringVar(value="0.00")
        self.currency_symbol = get_currency_code()
        self._build_ui()
        self._refresh_items()

    def _build_ui(self) -> None:
        # grid layout to avoid bottom clipping
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # cart area grows

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 6))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Search").grid(row=0, column=0, padx=4, sticky=tk.W)
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=32)
        search_entry.grid(row=0, column=1, padx=4, sticky=tk.EW)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_items())

        ttk.Label(top, text="Barcode").grid(row=0, column=2, padx=4, sticky=tk.W)
        barcode_entry = ttk.Entry(top, textvariable=self.barcode_var, width=20)
        barcode_entry.grid(row=0, column=3, padx=4, sticky=tk.W)
        barcode_entry.bind("<Return>", lambda _e: self._add_by_barcode())

        # Items list with scrollbar
        items_frame = ttk.Frame(self)
        items_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 8))
        items_frame.columnconfigure(0, weight=1)
        self.items_list = ttk.Treeview(items_frame, columns=("name", "price", "qty"), show="headings", height=8)
        self.items_list.heading("name", text="Item")
        self.items_list.heading("price", text="Price")
        self.items_list.heading("qty", text="Stock")
        self.items_list.column("name", width=200, anchor=tk.W)
        self.items_list.column("price", width=80, anchor=tk.E)
        self.items_list.column("qty", width=60, anchor=tk.E)
        self.items_list.grid(row=0, column=0, sticky=tk.NSEW)
        items_scroll = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_list.yview)
        items_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.items_list.configure(yscroll=items_scroll.set)
        self.items_list.bind("<Double-1>", lambda _e: self._add_selected_item())

        # Cart section
        ttk.Label(self, text="Cart", font=("Segoe UI", 12, "bold")).grid(row=2, column=0, sticky=tk.W, pady=(4, 4))
        cart_frame = ttk.Frame(self)
        cart_frame.grid(row=3, column=0, sticky=tk.NSEW, pady=(0, 6))
        cart_frame.columnconfigure(0, weight=1)
        cart_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(cart_frame, columns=("name", "price", "qty", "line_total"), show="headings", height=8)
        for col, txt, width, anchor in [
            ("name", "Item", 200, tk.W),
            ("price", "Price", 80, tk.E),
            ("qty", "Qty", 60, tk.E),
            ("line_total", "Total", 90, tk.E),
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=width, anchor=anchor)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        cart_scroll = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.tree.yview)
        cart_scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscroll=cart_scroll.set)
        self.tree.bind("<Double-1>", lambda _e: self._double_click_cart())

        cart_btns = ttk.Frame(self)
        cart_btns.grid(row=4, column=0, sticky=tk.W, pady=(4, 6))
        ttk.Button(cart_btns, text="Qty +", width=6, command=lambda: self._adjust_qty(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_btns, text="Qty -", width=6, command=lambda: self._adjust_qty(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_btns, text="Remove Item", command=self._remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_btns, text="Clear Cart", command=self._clear_cart).pack(side=tk.LEFT, padx=2)

        totals = ttk.Frame(self)
        totals.grid(row=5, column=0, sticky=tk.EW, pady=(4, 6))
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

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=6, column=0, sticky=tk.W, pady=(6, 4))
        ttk.Button(btn_frame, text="Checkout / Save Sale", command=self._checkout).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Suspend Cart", command=self._suspend_cart).pack(side=tk.LEFT, padx=2)
        self.resume_btn = ttk.Button(btn_frame, text="Resume Cart", command=self._resume_cart)
        self.resume_btn.pack(side=tk.LEFT, padx=2)
        self._update_resume_btn()

    def _update_resume_btn(self):
        if self.suspended_carts:
            self.resume_btn.state(["!disabled"])
        else:
            self.resume_btn.state(["disabled"])

    # Items search/add
    def _refresh_items(self) -> None:
        search = self.search_var.get().strip()
        for row in self.items_list.get_children():
            self.items_list.delete(row)
        rows = items.list_items(search=search if search else None)
        for row in rows:
            self.items_list.insert("", tk.END, iid=str(row["item_id"]), values=(row["name"], f"{self.currency_symbol} {row['selling_price']:.2f}", row["quantity"]))

    def _add_selected_item(self) -> None:
        sel = self.items_list.selection()
        if not sel:
            return
        item_id = int(sel[0])
        record = items.get_item(item_id)
        if record:
            self._add_to_cart(record)

    def _add_by_barcode(self) -> None:
        code = self.barcode_var.get().strip()
        if not code:
            return
        matches = [i for i in items.list_items(search=code) if i.get("barcode") == code]
        if not matches:
            messagebox.showinfo("Barcode", "No matching item")
            return
        self._add_to_cart(matches[0])
        self.barcode_var.set("")

    # Cart operations
    def _add_to_cart(self, item: dict) -> None:
        for entry in self.cart:
            if entry["item_id"] == item["item_id"]:
                entry["quantity"] += 1
                self._refresh_cart()
                return
        self.cart.append(
            {
                "item_id": item["item_id"],
                "name": item["name"],
                "price": item["selling_price"],
                "quantity": 1,
                "vat_rate": item.get("vat_rate", 16.0),
            }
        )
        self._refresh_cart()

    def _refresh_cart(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        subtotal = 0.0
        for entry in self.cart:
            line_total = entry["price"] * entry["quantity"]
            subtotal += line_total
            self.tree.insert(
                "",
                tk.END,
                iid=str(entry["item_id"]),
                values=(entry["name"], f"{self.currency_symbol} {entry['price']:.2f}", entry["quantity"], f"{self.currency_symbol} {line_total:.2f}"),
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
            line_subtotal = entry["price"] * entry["quantity"]
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
        item_id = int(sel[0])
        for entry in self.cart:
            if entry["item_id"] == item_id:
                return entry
        return None

    def _adjust_qty(self, delta: int) -> None:
        entry = self._selected_cart_item()
        if not entry:
            return
        entry["quantity"] = max(1, entry["quantity"] + delta)
        self._refresh_cart()

    def _remove_selected(self) -> None:
        entry = self._selected_cart_item()
        if not entry:
            return
        self.cart = [e for e in self.cart if e["item_id"] != entry["item_id"]]
        self._refresh_cart()

    def _double_click_cart(self) -> None:
        """On double-click, subtract one from the selected cart item's quantity; remove if zero."""
        entry = self._selected_cart_item()
        if not entry:
            return
        if entry["quantity"] > 1:
            entry["quantity"] -= 1
        else:
            self.cart = [e for e in self.cart if e["item_id"] != entry["item_id"]]
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
        self.cart = self.suspended_carts.pop()
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
            payment_method="",  # Provide a default or actual payment method here
        )

        if dialog.result:
            self._clear_cart()
            self._refresh_items()

    def refresh(self) -> None:
        currency = get_currency_code()
        # Update currency symbol in case it has changed
        self.currency_symbol = currency
        self.total_var.set(f"{currency} {float(self.total_var.get()):.2f}")
        self.subtotal_var.set(f"{currency} {float(self.subtotal_var.get()):.2f}")
        self.vat_var.set(f"{currency} {float(self.vat_var.get()):.2f}")
        self.change_var.set(f"{currency} {float(self.change_var.get()):.2f}")
