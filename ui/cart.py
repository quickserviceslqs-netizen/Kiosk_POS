"""Dedicated cart view for review and checkout."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ui.checkout import CheckoutDialog
from utils.security import get_currency_code, get_cart_vat_enabled, get_cart_discount_enabled, get_cart_suspend_enabled, get_payment_methods, subscribe_payment_methods, unsubscribe_payment_methods
from utils.cart_pubsub import subscribe_cart_changed, unsubscribe_cart_changed, notify_cart_changed
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

        # Store references to conditionally shown widgets
        self.vat_label = None
        self.vat_display = None
        self.discount_label = None
        self.discount_entry = None
        self.suspend_button = None
        self.resume_button = None

        # Store references to totals frame and actions frame for dynamic updates
        self.totals_frame = None
        self.actions_frame = None

        self._build_ui()
        self._refresh_cart()

        # Subscribe to payment method changes so combobox updates live
        subscribe_payment_methods(self._on_payment_methods_changed)
        # Ensure we unsubscribe when frame is destroyed
        self.bind("<Destroy>", lambda _e: unsubscribe_payment_methods(self._on_payment_methods_changed))

        # Subscribe to cart change notifications so other frames' mutations refresh this view
        subscribe_cart_changed(self._refresh_cart)
        self.bind("<Destroy>", lambda _e: unsubscribe_cart_changed(self._refresh_cart))

    def _on_payment_methods_changed(self) -> None:
        """Refresh the payment methods combobox when settings change."""
        try:
            methods = get_payment_methods()
            current = self.payment_method_var.get()
            self.pay_combo['values'] = methods
            if current not in methods:
                self.payment_method_var.set(methods[0] if methods else "")
        except Exception:
            pass

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
        vscroll = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.tree.yview)
        vscroll.grid(row=0, column=1, sticky=tk.NS)
        hscroll = ttk.Scrollbar(cart_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        hscroll.grid(row=1, column=0, sticky=tk.EW)
        self.tree.configure(yscroll=vscroll.set, xscroll=hscroll.set)
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

        # Totals section
        self.totals_frame = ttk.Frame(side, padding=(0, 8))
        self.totals_frame.pack(fill=tk.X)
        self.totals_frame.columnconfigure(1, weight=1)
        ttk.Label(self.totals_frame, text="Subtotal:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(self.totals_frame, textvariable=self.subtotal_var, font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

        # VAT display - will be shown/hidden dynamically
        self.vat_label = ttk.Label(self.totals_frame, text="VAT:")
        self.vat_display = ttk.Label(self.totals_frame, textvariable=self.vat_var)

        # Discount input - will be shown/hidden dynamically
        self.discount_label = ttk.Label(self.totals_frame, text="Discount (%):")
        self.discount_entry = ttk.Entry(self.totals_frame, textvariable=self.discount_var, width=8)
        self.discount_entry.bind("<KeyRelease>", lambda _e: self._refresh_cart())

        # Payment method and total (always shown)
        self.payment_label = ttk.Label(self.totals_frame, text="Payment Method:")
        from utils.security import get_payment_methods
        self.pay_combo = ttk.Combobox(self.totals_frame, textvariable=self.payment_method_var, values=get_payment_methods(), width=10, state="readonly")
        self.total_label = ttk.Label(self.totals_frame, text="Total:")
        self.total_display = ttk.Label(self.totals_frame, textvariable=self.total_var, font=("Segoe UI", 12, "bold"))

        # Actions section
        self.actions_frame = ttk.Frame(side)
        self.actions_frame.pack(pady=(6, 0))
        ttk.Button(self.actions_frame, text="Checkout / Save Sale", command=self._checkout).pack(side=tk.LEFT, padx=4)

        # Suspend/Resume buttons - will be shown/hidden dynamically
        self.suspend_button = ttk.Button(self.actions_frame, text="Suspend", command=self._suspend)
        self.resume_button = ttk.Button(self.actions_frame, text="Resume", command=self._resume)

    def _update_ui_layout(self) -> None:
        """Update the UI layout based on current cart settings."""
        # Clear existing grid layout
        for widget in self.totals_frame.winfo_children():
            widget.grid_forget()

        # Clear existing pack layout for actions
        for widget in self.actions_frame.winfo_children():
            widget.pack_forget()

        # Always show subtotal
        ttk.Label(self.totals_frame, text="Subtotal:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(self.totals_frame, textvariable=self.subtotal_var, font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))

        row_idx = 1

        # VAT display - conditionally shown
        if get_cart_vat_enabled():
            self.vat_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(2, 0))
            self.vat_display.grid(row=row_idx, column=1, sticky=tk.W, padx=(8, 0))
            row_idx += 1
        else:
            self.vat_label.grid_forget()
            self.vat_display.grid_forget()

        # Discount input - conditionally shown
        if get_cart_discount_enabled():
            self.discount_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(2, 0))
            self.discount_entry.grid(row=row_idx, column=1, sticky=tk.W, padx=(8, 0))
            row_idx += 1
        else:
            self.discount_label.grid_forget()
            self.discount_entry.grid_forget()

        # Payment method (always shown)
        self.payment_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(2, 0))
        self.pay_combo.grid(row=row_idx, column=1, sticky=tk.W, padx=(8, 0))
        row_idx += 1

        # Total (always shown)
        self.total_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(4, 0))
        self.total_display.grid(row=row_idx, column=1, sticky=tk.W, padx=(8, 0))

        # Actions - always show checkout button
        ttk.Button(self.actions_frame, text="Checkout / Save Sale", command=self._checkout).pack(side=tk.LEFT, padx=4)

        # Suspend/Resume buttons - conditionally shown
        if get_cart_suspend_enabled():
            self.suspend_button.pack(side=tk.LEFT, padx=4)
            self.resume_button.pack(side=tk.LEFT, padx=4)
        else:
            self.suspend_button.pack_forget()
            self.resume_button.pack_forget()

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
        # Update UI layout based on current settings
        self._update_ui_layout()

        for row in self.tree.get_children():
            self.tree.delete(row)
        subtotal = 0.0
        for entry in self.cart:
            line_total = entry.get("price", 0) * entry.get("quantity", 0)
            subtotal += line_total
            self.tree.insert("", tk.END, iid=str(entry["item_id"]), values=(entry["name"], f"{self.currency_symbol} {entry['price']:.2f}", entry["quantity"], f"{self.currency_symbol} {line_total:.2f}"))

        # Check settings for VAT and discount functionality
        vat_enabled = get_cart_vat_enabled()
        discount_enabled = get_cart_discount_enabled()

        discount_amt = 0.0
        if discount_enabled:
            try:
                discount_pct = float(self.discount_var.get() or 0) / 100.0
            except ValueError:
                discount_pct = 0.0
            discount_amt = subtotal * discount_pct

        vat_base = subtotal - discount_amt
        vat_amt = 0.0
        if vat_enabled:
            for entry in self.cart:
                line_subtotal = entry.get("price", 0) * entry.get("quantity", 0)
                item_discount = line_subtotal * (discount_amt / subtotal if subtotal > 0 else 0) if discount_enabled else 0
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
        notify_cart_changed()

    def _remove(self) -> None:
        entry = self._selected()
        if not entry:
            return
        self.cart[:] = [e for e in self.cart if e.get("item_id") != entry.get("item_id")]
        self._refresh_cart()
        notify_cart_changed()

    def _double_click(self) -> None:
        entry = self._selected()
        if not entry:
            return
        if entry.get("quantity", 1) > 1:
            entry["quantity"] -= 1
        else:
            self.cart[:] = [e for e in self.cart if e.get("item_id") != entry.get("item_id")]
        self._refresh_cart()
        notify_cart_changed()

    def _clear(self) -> None:
        self.cart.clear()
        self._refresh_cart()
        notify_cart_changed()

    def _suspend(self) -> None:
        if not self.cart:
            messagebox.showinfo("Suspend", "Cart is empty")
            return
        self.suspended_carts.append(self.cart[:])
        self.cart.clear()
        self._refresh_cart()
        notify_cart_changed()
        messagebox.showinfo("Suspend", f"Cart suspended (total: {len(self.suspended_carts)} suspended)")

    def _resume(self) -> None:
        if not self.suspended_carts:
            messagebox.showinfo("Resume", "No suspended carts")
            return
        recovered = self.suspended_carts.pop()
        self.cart.clear()
        self.cart.extend(recovered)
        self._refresh_cart()
        notify_cart_changed()
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
