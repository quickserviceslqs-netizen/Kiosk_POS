"""Checkout dialog for POS."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import pos


class CheckoutDialog:
    def __init__(
        self,
        parent: tk.Misc,
        cart: list,
        subtotal: float,
        vat_amount: float,
        total: float,
        payment_method: str,
    ):
        self.result = False
        self.sale_id = None

        dialog = tk.Toplevel(parent)
        dialog.title("Checkout")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.geometry("500x400")

        # Recalculate VAT based on per-item VAT rates
        recalc_vat = 0.0
        for item in cart:
            item_subtotal = item["price"] * item["quantity"]
            item_vat_rate = item.get("vat_rate", 16.0) / 100.0
            recalc_vat += item_subtotal * item_vat_rate
        
        recalc_total = subtotal + recalc_vat

        # Summary
        summary = ttk.Frame(dialog, padding=12)
        summary.pack(fill=tk.X)
        ttk.Label(summary, text="Order Summary", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        cart_text = "\n".join([
            f"  {e['name']} x{e['quantity']} @ {e['price']:.2f} = {e['price']*e['quantity']:.2f}" + 
            (f" (VAT: {e.get('vat_rate', 16.0):.0f}%)" if e.get('vat_rate', 16.0) > 0 else " (VAT-exempt)")
            for e in cart
        ])
        ttk.Label(summary, text=cart_text, justify=tk.LEFT, font=("Courier", 9)).pack(anchor=tk.W, pady=(4, 8))

        # Totals
        totals = ttk.Frame(dialog, padding=12)
        totals.pack(fill=tk.X)
        ttk.Label(totals, text="Subtotal:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(totals, text=f"{subtotal:.2f}", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=tk.E, padx=12)

        ttk.Label(totals, text="VAT:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Label(totals, text=f"{recalc_vat:.2f}", font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky=tk.E, padx=12)

        ttk.Separator(totals, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=8)

        ttk.Label(totals, text="Total:", font=("Segoe UI", 12, "bold")).grid(row=3, column=0, sticky=tk.W)
        ttk.Label(totals, text=f"{recalc_total:.2f}", font=("Segoe UI", 12, "bold"), foreground="darkgreen").grid(row=3, column=1, sticky=tk.E, padx=12)

        # Payment
        payment_frame = ttk.Frame(dialog, padding=12)
        payment_frame.pack(fill=tk.X)
        ttk.Label(payment_frame, text="Payment Method:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(payment_frame, text=payment_method, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=tk.W, padx=12)

        ttk.Label(payment_frame, text="Amount Paid:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        payment_var = tk.StringVar(value="0")
        payment_entry = ttk.Entry(payment_frame, textvariable=payment_var, font=("Segoe UI", 10), width=16)
        payment_entry.grid(row=1, column=1, sticky=tk.W, padx=12, pady=(8, 0))
        payment_entry.focus_set()

        change_var = tk.StringVar(value="0.00")

        def on_payment_change(*args):
            try:
                payment = float(payment_var.get() or 0)
                change = max(0, payment - recalc_total)
            except ValueError:
                change = 0
            change_var.set(f"{change:.2f}")

        payment_var.trace("w", on_payment_change)

        ttk.Label(payment_frame, text="Change:", font=("Segoe UI", 10)).grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Label(payment_frame, textvariable=change_var, font=("Segoe UI", 10, "bold")).grid(row=2, column=1, sticky=tk.W, padx=12, pady=(8, 0))

        # Buttons
        btn_frame = ttk.Frame(dialog, padding=12)
        btn_frame.pack(fill=tk.X)

        def on_complete():
            try:
                payment = float(payment_var.get() or 0)
            except ValueError:
                messagebox.showerror("Invalid", "Enter valid payment amount")
                return
            if payment < recalc_total:
                messagebox.showerror("Insufficient", "Payment is less than total")
                return

            try:
                self.sale_id = pos.create_sale(
                    [{"item_id": e["item_id"], "quantity": e["quantity"], "price": e["price"]} for e in cart],
                    payment=payment,
                    change=payment - recalc_total,
                )
                self.result = True
                messagebox.showinfo("Success", f"Sale #{self.sale_id} completed")
                dialog.destroy()
            except pos.InsufficientStock as exc:
                messagebox.showerror("Stock Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Error", f"Checkout failed: {exc}")

        ttk.Button(btn_frame, text="Complete Sale", command=on_complete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)

        dialog.wait_window()
