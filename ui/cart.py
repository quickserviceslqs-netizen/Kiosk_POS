"""Dedicated cart view for review and checkout."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ui.checkout import CheckoutDialog
from utils.security import get_currency_code
from utils.images import load_thumbnail


class CartFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, *, cart_state: dict, on_back, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.cart_state = cart_state
        self.cart = self.cart_state.setdefault("items", [])
        self.suspended_carts = self.cart_state.setdefault("suspended", [])
        self.on_back = on_back
        self.currency_symbol = get_currency_code()

        self.subtotal_var = tk.StringVar(value="0.00")
        self.vat_var = tk.StringVar(value="0.00")
        self.total_var = tk.StringVar(value="0.00")
        self.discount_var = tk.StringVar(value="0")
        self.payment_var = tk.StringVar(value="0")
        self.payment_method_var = tk.StringVar(value="Cash")
        self.change_var = tk.StringVar(value="0.00")
        self._preview_cache: dict[int, tk.PhotoImage] = {}

        self._build_ui()
        self._refresh_cart()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Cart", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Back to POS", command=self.on_back).pack(side=tk.RIGHT)

        # Cart table
        cart_frame = ttk.Frame(self)
        cart_frame.grid(row=1, column=0, sticky=tk.NSEW)
        cart_frame.columnconfigure(0, weight=1)
        cart_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(cart_frame, columns=("name", "price", "qty", "line_total"), show="headings", height=18)
        for col, txt, width, anchor in [
            ("name", "Item", 220, tk.W),
            ("price", "Price", 90, tk.E),
            ("qty", "Qty", 70, tk.E),
            ("line_total", "Total", 110, tk.E),
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=width, anchor=anchor, stretch=True)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        scroll = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscroll=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._update_preview())
        self.tree.bind("<Double-1>", lambda _e: self._double_click())

        # Preview + controls column
        side = ttk.Frame(self, padding=(10, 0))
        side.grid(row=1, column=1, sticky=tk.N)
        self.preview_label = ttk.Label(side, text="(No image)", anchor=tk.CENTER)
        self.preview_label.pack()
        self.preview_meta = ttk.Label(side, text="", foreground="gray")
        self.preview_meta.pack(pady=(6, 0))

        btns = ttk.Frame(side)
        btns.pack(pady=(8, 6))
        ttk.Button(btns, text="Qty +", width=6, command=lambda: self._adjust_qty(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Qty -", width=6, command=lambda: self._adjust_qty(-1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Remove", width=10, command=self._remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Clear", width=8, command=self._clear).pack(side=tk.LEFT, padx=2)

        totals = ttk.Frame(side, padding=(0, 8))
        totals.pack(fill=tk.X)
        totals.columnconfigure(1, weight=1)
        ttk.Label(totals, text="Subtotal:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(totals, textvariable=self.subtotal_var, font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))
        ttk.Label(totals, text="VAT:").grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        ttk.Label(totals, textvariable=self.vat_var).grid(row=1, column=1, sticky=tk.W, padx=(8, 0))
        ttk.Label(totals, text="Discount (%):").grid(row=2, column=0, sticky=tk.W, pady=(2, 0))
        disc = ttk.Entry(totals, textvariable=self.discount_var, width=8)
        disc.grid(row=2, column=1, sticky=tk.W, padx=(8, 0))
        disc.bind("<KeyRelease>", lambda _e: self._refresh_cart())
        ttk.Label(totals, text="Payment Method:").grid(row=3, column=0, sticky=tk.W, pady=(2, 0))
        pay_combo = ttk.Combobox(totals, textvariable=self.payment_method_var, values=["Cash", "M-Pesa", "Card"], width=10, state="readonly")
        pay_combo.grid(row=3, column=1, sticky=tk.W, padx=(8, 0))
        ttk.Label(totals, text="Total:").grid(row=4, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Label(totals, textvariable=self.total_var, font=("Segoe UI", 12, "bold")).grid(row=4, column=1, sticky=tk.W, padx=(8, 0))

        actions = ttk.Frame(side)
        actions.pack(pady=(6, 0))
        ttk.Button(actions, text="Checkout / Save Sale", command=self._checkout).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Suspend", command=self._suspend).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Resume", command=self._resume).pack(side=tk.LEFT, padx=4)

    def _thumb(self, item: dict) -> tk.PhotoImage | None:
        item_id = item.get("item_id")
        if not item_id:
            return None
        if item_id in self._preview_cache:
            return self._preview_cache[item_id]
        thumb = load_thumbnail(item.get("image_path")) if item.get("image_path") else None
        if thumb:
            self._preview_cache[item_id] = thumb
        return thumb

    def _refresh_cart(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        subtotal = 0.0
        for entry in self.cart:
            line_total = entry.get("price", 0) * entry.get("quantity", 0)
            subtotal += line_total
            self.tree.insert("", tk.END, iid=str(entry["item_id"]), values=(entry["name"], f"{self.currency_symbol} {entry['price']:.2f}", entry["quantity"], f"{self.currency_symbol} {line_total:.2f}"))

        try:
            discount_pct = float(self.discount_var.get() or 0) / 100.0
        except ValueError:
            discount_pct = 0.0
        discount_amt = subtotal * discount_pct
        vat_base = subtotal - discount_amt
        vat_amt = 0.0
        for entry in self.cart:
            line_subtotal = entry.get("price", 0) * entry.get("quantity", 0)
            item_discount = line_subtotal * discount_pct
            item_vat_base = line_subtotal - item_discount
            item_vat_rate = entry.get("vat_rate", 16.0) / 100.0
            vat_amt += item_vat_base * item_vat_rate
        total = vat_base + vat_amt

        self.subtotal_var.set(f"{self.currency_symbol} {subtotal:.2f}")
        self.vat_var.set(f"{self.currency_symbol} {vat_amt:.2f}")
        self.total_var.set(f"{self.currency_symbol} {total:.2f}")
        self._update_preview()

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = int(sel[0])
        for entry in self.cart:
            if entry.get("item_id") == item_id:
                return entry
        return None

    def _update_preview(self) -> None:
        entry = self._selected()
        if not entry:
            self.preview_label.configure(text="(No image)", image="")
            self.preview_meta.configure(text="")
            return
        thumb = self._thumb(entry)
        if thumb:
            self.preview_label.configure(image=thumb, text="")
            self.preview_label.image = thumb
        else:
            self.preview_label.configure(text="(No image)", image="")
            self.preview_label.image = None
        meta = f"Qty: {entry.get('quantity', 0)}\nPrice: {self.currency_symbol} {entry.get('price', 0):.2f}"
        self.preview_meta.configure(text=meta)

    def _adjust_qty(self, delta: int) -> None:
        entry = self._selected()
        if not entry:
            return
        entry["quantity"] = max(1, entry.get("quantity", 1) + delta)
        self._refresh_cart()

    def _remove(self) -> None:
        entry = self._selected()
        if not entry:
            return
        self.cart[:] = [e for e in self.cart if e.get("item_id") != entry.get("item_id")]
        self._refresh_cart()

    def _double_click(self) -> None:
        entry = self._selected()
        if not entry:
            return
        if entry.get("quantity", 1) > 1:
            entry["quantity"] -= 1
        else:
            self.cart[:] = [e for e in self.cart if e.get("item_id") != entry.get("item_id")]
        self._refresh_cart()

    def _clear(self) -> None:
        self.cart.clear()
        self._refresh_cart()

    def _suspend(self) -> None:
        if not self.cart:
            messagebox.showinfo("Suspend", "Cart is empty")
            return
        self.suspended_carts.append(self.cart[:])
        self.cart.clear()
        self._refresh_cart()
        messagebox.showinfo("Suspend", f"Cart suspended (total: {len(self.suspended_carts)} suspended)")

    def _resume(self) -> None:
        if not self.suspended_carts:
            messagebox.showinfo("Resume", "No suspended carts")
            return
        recovered = self.suspended_carts.pop()
        self.cart.clear()
        self.cart.extend(recovered)
        self._refresh_cart()
        messagebox.showinfo("Resume", "Cart restored")

    def _checkout(self) -> None:
        if not self.cart:
            messagebox.showinfo("Checkout", "Cart is empty")
            return
        try:
            subtotal = float(self.subtotal_var.get().replace(self.currency_symbol, '').strip())
            vat_amt = float(self.vat_var.get().replace(self.currency_symbol, '').strip())
        except ValueError:
            messagebox.showerror("Checkout Error", "Totals are invalid")
            return
        try:
            discount_pct = float(self.discount_var.get().strip() or 0) / 100.0
        except ValueError:
            discount_pct = 0.0
        discount_amt = subtotal * discount_pct
        total = subtotal - discount_amt + vat_amt

        dialog = CheckoutDialog(
            self.winfo_toplevel(),
            cart=self.cart,
            subtotal=subtotal - discount_amt,
            vat_amount=vat_amt,
            total=total,
            discount=discount_amt,
            payment_method=self.payment_method_var.get(),
        )
        if dialog.result:
            self._clear()
