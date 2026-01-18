"""Enhanced cart view with loyalty points integration."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import json
from typing import Optional

from ui.checkout import CheckoutDialog
from utils.security import get_currency_code
from utils.images import load_thumbnail
from database.init_db import get_connection


class CartFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, *, cart_state: dict, on_back, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.cart_state = cart_state
        self.cart = self.cart_state.setdefault("items", [])
        self.suspended_carts = self.cart_state.setdefault("suspended", [])
        self.on_back = on_back
        self.currency_symbol = get_currency_code()

        # Loyalty points state
        self.loyalty_customer = None
        self.available_points = 0
        self.points_to_redeem = 0
        self.points_earned = 0

        # Load loyalty configuration
        self.loyalty_config = self._load_loyalty_config()

        self.subtotal_var = tk.StringVar(value="0.00")
        self.vat_var = tk.StringVar(value="0.00")
        self.total_var = tk.StringVar(value="0.00")
        self.discount_var = tk.StringVar(value="0")
        self.payment_var = tk.StringVar(value="0")
        self.payment_method_var = tk.StringVar(value="Cash")
        self.change_var = tk.StringVar(value="0.00")

        # Loyalty points variables
        self.customer_var = tk.StringVar(value="No customer selected")
        self.points_var = tk.StringVar(value="0 points available")
        self.redeem_var = tk.StringVar(value="0")
        self.earned_var = tk.StringVar(value="0")

        self._preview_cache: dict[int, tk.PhotoImage] = {}

        self._build_ui()
        self._refresh_cart()

    def _load_loyalty_config(self) -> dict:
        """Load loyalty points configuration."""
        config_path = self.winfo_toplevel().winfo_toplevel().attributes("-alpha")  # Get app root
        # For now, use default config
        return {
            "enabled": True,
            "points_per_dollar": 1,
            "redemption_rate": 100,  # 100 points = $1.00
            "min_points_redemption": 100
        }

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
        self.tree = ttk.Treeview(cart_frame, columns=("name", "price", "qty", "line_total"), show="headings", height=15)
        for col, txt, width, anchor in [
            ("name", "Item", 220, tk.W),
            ("price", f"Price ({self.currency_symbol})", 80, tk.E),
            ("qty", "Qty", 50, tk.E),
            ("line_total", f"Total ({self.currency_symbol})", 80, tk.E),
        ]:
            self.tree.heading(col, text=txt, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor)
        scrollbar = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        # Cart actions
        actions = ttk.Frame(cart_frame)
        actions.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(4, 0))
        ttk.Button(actions, text="Remove", command=self._remove).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Suspend", command=self._suspend).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Resume", command=self._resume).pack(side=tk.LEFT, padx=4)

        # Loyalty points section
        loyalty_frame = ttk.LabelFrame(self, text="Loyalty Points", padding=8)
        loyalty_frame.grid(row=1, column=1, sticky=tk.NW, pady=(0, 8))
        loyalty_frame.configure(width=250)

        # Customer selection
        ttk.Label(loyalty_frame, text="Customer:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(loyalty_frame, textvariable=self.customer_var, foreground="blue").grid(row=0, column=1, sticky=tk.W, pady=2)
        ttk.Button(loyalty_frame, text="Select", command=self._select_customer).grid(row=0, column=2, padx=(4, 0), pady=2)

        # Points display
        ttk.Label(loyalty_frame, text="Available Points:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(loyalty_frame, textvariable=self.points_var, foreground="green").grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=2)

        # Points redemption
        ttk.Label(loyalty_frame, text="Redeem Points:").grid(row=2, column=0, sticky=tk.W, pady=2)
        redeem_entry = ttk.Entry(loyalty_frame, textvariable=self.redeem_var, width=8)
        redeem_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        redeem_entry.bind("<KeyRelease>", self._on_redeem_change)
        ttk.Button(loyalty_frame, text="Apply", command=self._apply_redemption).grid(row=2, column=2, padx=(4, 0), pady=2)

        # Points to be earned
        ttk.Label(loyalty_frame, text="Points to Earn:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Label(loyalty_frame, textvariable=self.earned_var, foreground="orange").grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=2)

        # Totals section
        totals_frame = ttk.LabelFrame(self, text="Order Totals", padding=8)
        totals_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

        # Subtotal, VAT, Total
        ttk.Label(totals_frame, text="Subtotal:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(totals_frame, textvariable=self.subtotal_var).grid(row=0, column=1, sticky=tk.E, pady=2)

        ttk.Label(totals_frame, text="VAT:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(totals_frame, textvariable=self.vat_var).grid(row=1, column=1, sticky=tk.E, pady=2)

        ttk.Label(totals_frame, text="Discount (%):").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(totals_frame, textvariable=self.discount_var, width=8).grid(row=2, column=1, sticky=tk.E, pady=2)

        ttk.Label(totals_frame, text="Total:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Label(totals_frame, textvariable=self.total_var, font=("Segoe UI", 10, "bold")).grid(row=3, column=1, sticky=tk.E, pady=2)

        # Payment section
        payment_frame = ttk.LabelFrame(self, text="Payment", padding=8)
        payment_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

        ttk.Label(payment_frame, text="Method:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(payment_frame, textvariable=self.payment_method_var,
                     values=["Cash", "Card", "Mobile"], state="readonly", width=10).grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(payment_frame, text="Amount:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(payment_frame, textvariable=self.payment_var, width=12).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(payment_frame, text="Change:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Label(payment_frame, textvariable=self.change_var).grid(row=2, column=1, sticky=tk.E, pady=2)

        # Checkout button
        ttk.Button(self, text="Complete Order", command=self._checkout, style="Accent.TButton").grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(12, 0))

    def _select_customer(self):
        """Select a loyalty customer."""
        # Simple customer selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Select Loyalty Customer")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Search Customer:").pack(pady=8)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(dialog, textvariable=search_var)
        search_entry.pack(fill=tk.X, padx=20)

        # Customer list
        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        def search_customers():
            search_term = search_var.get().strip()
            listbox.delete(0, tk.END)

            if len(search_term) >= 2:
                try:
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id, customer_name, phone, available_points
                            FROM loyalty_customers
                            WHERE (customer_name LIKE ? OR phone LIKE ?) AND status = 'active'
                            ORDER BY customer_name
                            LIMIT 20
                        """, (f"%{search_term}%", f"%{search_term}%"))

                        for row in cursor.fetchall():
                            customer_id, name, phone, points = row
                            display_text = f"{name} ({phone or 'No phone'}) - {points} points"
                            listbox.insert(tk.END, display_text)
                            listbox.itemconfig(tk.END, {'tags': (str(customer_id),)})

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to search customers: {e}")

        search_entry.bind("<KeyRelease>", lambda e: search_customers())

        def select_customer():
            selection = listbox.curselection()
            if selection:
                item_tags = listbox.itemcget(selection[0], 'tags')
                if item_tags:
                    customer_id = int(item_tags[0])
                    self._set_loyalty_customer(customer_id)
                    dialog.destroy()

        ttk.Button(dialog, text="Select", command=select_customer).pack(pady=8)

        # Initial search
        search_customers()

    def _set_loyalty_customer(self, customer_id: int):
        """Set the selected loyalty customer."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, customer_name, phone, available_points
                    FROM loyalty_customers
                    WHERE id = ? AND status = 'active'
                """, (customer_id,))

                row = cursor.fetchone()
                if row:
                    self.loyalty_customer = {
                        'id': row[0],
                        'name': row[1],
                        'phone': row[2],
                        'available_points': row[3]
                    }
                    self.customer_var.set(f"{row[1]} ({row[2] or 'No phone'})")
                    self.points_var.set(f"{row[3]} points available")
                    self.available_points = row[3]
                    self._refresh_cart()
                else:
                    messagebox.showerror("Error", "Customer not found")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load customer: {e}")

    def _on_redeem_change(self, event=None):
        """Handle points redemption input change."""
        try:
            points = int(self.redeem_var.get() or 0)
            if points > self.available_points:
                points = self.available_points
                self.redeem_var.set(str(points))
            self.points_to_redeem = points
            self._refresh_cart()
        except ValueError:
            self.redeem_var.set("0")
            self.points_to_redeem = 0
            self._refresh_cart()

    def _apply_redemption(self):
        """Apply points redemption."""
        if not self.loyalty_customer:
            messagebox.showwarning("No Customer", "Please select a loyalty customer first")
            return

        if self.points_to_redeem > self.available_points:
            messagebox.showerror("Insufficient Points", "Customer doesn't have enough points")
            return

        if self.points_to_redeem < (self.loyalty_config.get('min_points_redemption', 100)):
            min_points = self.loyalty_config.get('min_points_redemption', 100)
            messagebox.showwarning("Minimum Points", f"Minimum redemption is {min_points} points")
            return

        self._refresh_cart()
        messagebox.showinfo("Points Applied", f"{self.points_to_redeem} points will be redeemed at checkout")

    def _refresh_cart(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)

        subtotal = 0.0
        for entry in self.cart:
            line_total = entry.get("price", 0) * entry.get("quantity", 0)
            subtotal += line_total
            self.tree.insert("", tk.END, iid=str(entry["item_id"]), values=(
                entry["name"],
                f"{entry['price']:.2f}",
                entry["quantity"],
                f"{line_total:.2f}"
            ))

        # Calculate points to be earned
        self.points_earned = int(subtotal * self.loyalty_config.get('points_per_dollar', 1))
        self.earned_var.set(str(self.points_earned))

        # Apply discount from points redemption
        redemption_rate = self.loyalty_config.get('redemption_rate', 100)  # points per dollar
        discount_from_points = self.points_to_redeem / redemption_rate if redemption_rate > 0 else 0

        try:
            discount_pct = float(self.discount_var.get() or 0) / 100.0
        except ValueError:
            discount_pct = 0.0

        discount_amt = subtotal * discount_pct + discount_from_points
        vat_base = subtotal - discount_amt
        vat_amt = 0.0

        for entry in self.cart:
            line_subtotal = entry.get("price", 0) * entry.get("quantity", 0)
            item_discount = line_subtotal * discount_pct
            item_points_discount = (line_subtotal / subtotal) * discount_from_points if subtotal > 0 else 0
            item_vat_base = line_subtotal - item_discount - item_points_discount
            item_vat_rate = entry.get("vat_rate", 16.0) / 100.0
            vat_amt += item_vat_base * item_vat_rate

        total = vat_base + vat_amt

        self.subtotal_var.set(f"{self.currency_symbol} {subtotal:.2f}")
        self.vat_var.set(f"{self.currency_symbol} {vat_amt:.2f}")
        self.total_var.set(f"{self.currency_symbol} {total:.2f}")
        self._update_preview()

    def _update_preview(self):
        """Update payment preview."""
        try:
            total = float(self.total_var.get().replace(self.currency_symbol, '').strip())
            payment = float(self.payment_var.get() or 0)
            change = payment - total
            self.change_var.set(f"{self.currency_symbol} {change:.2f}" if change >= 0 else "Insufficient")
        except ValueError:
            self.change_var.set("0.00")

    def _remove(self) -> None:
        item = self._selected()
        if item:
            self.cart.remove(item)
            self._refresh_cart()

    def _clear(self) -> None:
        self.cart.clear()
        self.loyalty_customer = None
        self.available_points = 0
        self.points_to_redeem = 0
        self.customer_var.set("No customer selected")
        self.points_var.set("0 points available")
        self.redeem_var.set("0")
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

        # Calculate points discount
        redemption_rate = self.loyalty_config.get('redemption_rate', 100)
        discount_from_points = self.points_to_redeem / redemption_rate if redemption_rate > 0 else 0

        discount_amt = subtotal * discount_pct + discount_from_points
        total = subtotal - discount_amt + vat_amt

        dialog = CheckoutDialog(
            self.winfo_toplevel(),
            cart=self.cart,
            subtotal=subtotal - discount_amt,
            vat_amount=vat_amt,
            total=total,
            discount=discount_amt,
            payment_method=self.payment_method_var.get(),
            loyalty_customer=self.loyalty_customer,
            points_earned=self.points_earned,
            points_redeemed=self.points_to_redeem
        )

        if dialog.result:
            self._clear()

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = int(sel[0])
        for entry in self.cart:
            if entry.get("item_id") == item_id:
                return entry
        return None

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