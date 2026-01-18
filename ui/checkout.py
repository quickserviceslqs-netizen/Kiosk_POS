"""Checkout dialog for POS."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import pos, items
from utils import set_window_icon


class CheckoutDialog:
    def __init__(
        self,
        parent: tk.Misc,
        cart: list,
        subtotal: float,
        vat_amount: float,
        total: float,
        payment_method: str,
        discount: float,
    ):
        self.result = False
        self.sale_id = None

        dialog = tk.Toplevel(parent)
        dialog.withdraw()  # Hide until fully built
        dialog.title("Checkout")
        set_window_icon(dialog)
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(True, True)

        # Recalculate VAT and totals based on canonical per-item line totals
        # Prefer stored '_line_total' (set by POS refresh); fall back to computed values.
        gross_subtotal = 0.0
        for e in cart:
            lt = e.get('_line_total')
            if lt is None:
                if e.get('is_special_volume'):
                    lt = float(e.get('price', 0)) * float(e.get('quantity', 0))
                else:
                    # Try to determine unit_size from item record; default to 1
                    try:
                        it = items.get_item(e.get('item_id'))
                        unit_size = float(it.get('unit_size_ml') or 1)
                    except Exception:
                        unit_size = 1
                    per_unit = float(e.get('price', 0)) / unit_size if unit_size else float(e.get('price', 0))
                    lt = per_unit * float(e.get('quantity', 0))
            gross_subtotal += lt

        discount_pct = (discount / gross_subtotal) if gross_subtotal else 0
        recalc_vat = 0.0
        for item in cart:
            lt = item.get('_line_total')
            if lt is None:
                if item.get('is_special_volume'):
                    lt = float(item.get('price', 0)) * float(item.get('quantity', 0))
                else:
                    try:
                        it = items.get_item(item.get('item_id'))
                        unit_size = float(it.get('unit_size_ml') or 1)
                    except Exception:
                        unit_size = 1
                    per_unit = float(item.get('price', 0)) / unit_size if unit_size else float(item.get('price', 0))
                    lt = per_unit * float(item.get('quantity', 0))
            item_discount = lt * discount_pct
            item_vat_rate = item.get('vat_rate', 16.0) / 100.0
            recalc_vat += max(0.0, lt - item_discount) * item_vat_rate

        net_subtotal = gross_subtotal - discount
        recalc_total = net_subtotal + recalc_vat

        # Summary with scrollable area for long cart lists
        summary = ttk.Frame(dialog, padding=12)
        summary.pack(fill=tk.BOTH, expand=True)
        ttk.Label(summary, text="Order Summary", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        def _display_qty(entry: dict) -> str:
            if entry.get("is_special_volume"):
                display_unit = entry.get("display_unit", "unit")
                return f"{entry['quantity']:.2f} {display_unit}"
            return f"x{entry['quantity']}"

        def _display_price(entry: dict) -> str:
            # Show price per small unit for special items; per unit price for non-special
            if entry.get("is_special_volume"):
                return f"{entry.get('price', 0):.6f}"
            try:
                it = items.get_item(entry.get('item_id'))
                unit_size = float(it.get('unit_size_ml') or 1)
            except Exception:
                unit_size = 1
            per_unit = float(entry.get('price', 0)) / unit_size if unit_size else float(entry.get('price', 0))
            return f"{per_unit:.2f}"

        # Build cart text using the canonical line totals where possible
        lines = []
        for e in cart:
            try:
                lt = e.get('_line_total')
                if lt is None:
                    if e.get('is_special_volume'):
                        lt = float(e.get('price', 0)) * float(e.get('quantity', 0))
                    else:
                        it = items.get_item(e.get('item_id'))
                        unit_size = float(it.get('unit_size_ml') or 1)
                        per_unit = float(e.get('price', 0)) / unit_size if unit_size else float(e.get('price', 0))
                        lt = per_unit * float(e.get('quantity', 0))
            except Exception:
                lt = float(e.get('price', 0)) * float(e.get('quantity', 0))
            lines.append(f"  {e['name']} {_display_qty(e)} @ {_display_price(e)} = {lt:.2f}" + (f" (VAT: {e.get('vat_rate', 16.0):.0f}%)" if e.get('vat_rate', 16.0) > 0 else " (VAT-exempt)"))
        cart_text = "\n".join(lines)
        
        # Use scrollable text widget for long item lists
        cart_frame = ttk.Frame(summary)
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        
        cart_lines = len(cart)
        display_height = min(cart_lines + 1, 8)  # Max 8 lines visible, scroll for more
        
        cart_display = tk.Text(cart_frame, wrap=tk.WORD, font=("Courier", 9), height=display_height, width=60)
        cart_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cart_display.insert("1.0", cart_text)
        cart_display.config(state=tk.DISABLED)
        
        if cart_lines > 8:
            cart_scroll = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=cart_display.yview)
            cart_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            cart_display.config(yscrollcommand=cart_scroll.set)

        # Include discount in the summary
        discount_label = ttk.Label(dialog, text=f"Discount: -{discount:.2f}")
        discount_label.pack()

        # Totals
        totals = ttk.Frame(dialog, padding=12)
        totals.pack(fill=tk.X)
        ttk.Label(totals, text="Subtotal:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(totals, text=f"{net_subtotal:.2f}", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=tk.E, padx=12)

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
                # Build sale payload using per-unit prices for non-special items and price-per-small-unit for special items
                sale_lines = []
                for e in cart:
                    line_item = {'item_id': e['item_id']}
                    
                    # Include variant_id if present
                    if e.get('variant_id'):
                        line_item['variant_id'] = e['variant_id']
                    
                    # Include portion_id if present
                    if e.get('portion_id'):
                        line_item['portion_id'] = e['portion_id']
                    
                    if e.get('is_special_volume'):
                        line_item.update({
                            'quantity': e.get('qty_ml') or e.get('quantity'),
                            'price': e.get('price_per_ml') or e.get('price'),
                        })
                    else:
                        try:
                            it = items.get_item(e.get('item_id'))
                            unit_size = float(it.get('unit_size_ml') or 1)
                        except Exception:
                            unit_size = 1
                        per_unit = float(e.get('price', 0)) / unit_size if unit_size else float(e.get('price', 0))
                        line_item.update({
                            'quantity': e.get('quantity', 1), 
                            'price': per_unit
                        })
                    
                    sale_lines.append(line_item)

                sale_result = pos.create_sale(
                    sale_lines,
                    payment=payment,
                    change=payment - recalc_total,
                    payment_method=payment_method,
                    vat_amount=recalc_vat,
                    discount_amount=discount,
                )
                self.sale_id = sale_result.get("sale_id")
                receipt_number = sale_result.get("receipt_number", "")
                self.result = True
                messagebox.showinfo("Success", f"Receipt {receipt_number or '#'+str(self.sale_id)} completed")
                dialog.destroy()
            except pos.InsufficientStock as exc:
                messagebox.showerror("Stock Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Error", f"Checkout failed: {exc}")

        ttk.Button(btn_frame, text="Complete Sale", command=on_complete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)

        # Set geometry and show dialog after content is built - auto-size to fit content
        dialog.update_idletasks()
        req_width = dialog.winfo_reqwidth()
        req_height = dialog.winfo_reqheight()
        # Ensure dialog fits on screen with buttons visible; set reasonable limits
        final_width = min(max(req_width + 20, 550), 800)
        final_height = min(max(req_height + 20, 420), 700)
        dialog.geometry(f"{final_width}x{final_height}")
        dialog.deiconify()  # Show after fully built
        
        dialog.wait_window()
