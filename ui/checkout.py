"""Checkout dialog for POS."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import pos, items
from utils import set_window_icon
from utils.theme import get_status_color


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
        from utils.security import get_cart_vat_enabled
        vat_enabled = get_cart_vat_enabled()
        if vat_enabled:
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
            lines.append(f"  {e['name']} {_display_qty(e)} @ {_display_price(e)} = {lt:.2f}" + (f" (VAT: {e.get('vat_rate', 16.0):.0f}%)" if vat_enabled and e.get('vat_rate', 16.0) > 0 else ""))
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

        current_row = 1
        if vat_enabled:
            ttk.Label(totals, text="VAT:", font=("Segoe UI", 10)).grid(row=current_row, column=0, sticky=tk.W, pady=(4, 0))
            ttk.Label(totals, text=f"{recalc_vat:.2f}", font=("Segoe UI", 10, "bold")).grid(row=current_row, column=1, sticky=tk.E, padx=12)
            current_row += 1

        ttk.Separator(totals, orient=tk.HORIZONTAL).grid(row=current_row, column=0, columnspan=2, sticky=tk.EW, pady=8)
        current_row += 1

        ttk.Label(totals, text="Total:", font=("Segoe UI", 12, "bold")).grid(row=current_row, column=0, sticky=tk.W)
        ttk.Label(totals, text=f"{recalc_total:.2f}", font=("Segoe UI", 12, "bold"), foreground=get_status_color('success')).grid(row=current_row, column=1, sticky=tk.E, padx=12)

        # ── Buttons (packed at BOTTOM first so they always stay visible) ────────
        btn_frame = ttk.Frame(dialog, padding=(12, 4, 12, 12))
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # ── Summary strip (also anchored at bottom, above buttons) ──────────────
        sf = ttk.Frame(dialog, padding=(12, 6, 12, 0))
        sf.pack(side=tk.BOTTOM, fill=tk.X)
        paid_var      = tk.StringVar(value="0.00")
        remaining_var = tk.StringVar(value=f"{recalc_total:.2f}")
        change_var    = tk.StringVar(value="0.00")
        ttk.Label(sf, text="Total Due:",  font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(sf, text=f"{recalc_total:.2f}", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=tk.W, padx=8)
        ttk.Label(sf, text="Paid:",       font=("Segoe UI", 10)).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Label(sf, textvariable=paid_var, font=("Segoe UI", 10, "bold"),
                  foreground="green").grid(row=0, column=3, sticky=tk.W, padx=8)
        ttk.Label(sf, text="Remaining:",  font=("Segoe UI", 10)).grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Label(sf, textvariable=remaining_var, font=("Segoe UI", 10, "bold"),
                  foreground="red").grid(row=1, column=1, sticky=tk.W, padx=8, pady=(4, 0))
        ttk.Label(sf, text="Change:",     font=("Segoe UI", 10)).grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=(4, 0))
        ttk.Label(sf, textvariable=change_var, font=("Segoe UI", 10, "bold")).grid(row=1, column=3, sticky=tk.W, padx=8, pady=(4, 0))

        # ── Split / Multi-payment section (fills remaining middle space) ─────────
        pf = ttk.LabelFrame(dialog, text=" Payment ", padding=10)
        pf.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 0))

        from utils.security import get_payment_methods
        available_methods = get_payment_methods()

        # List of active payment rows; each entry is a dict with tkinter vars & frame
        payment_rows: list[dict] = []
        complete_btn_ref: list = []   # filled after button is created

        # Scrollbar on far right of pf, spanning full height (packed first)
        rows_scrollbar = ttk.Scrollbar(pf, orient=tk.VERTICAL)
        rows_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Left side: header row + canvas
        left_frame = ttk.Frame(pf)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Column headers + "Add Payment Method" button
        hdr = ttk.Frame(left_frame)
        hdr.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(hdr, text="Payment Method", font=("Segoe UI", 9, "bold"), width=16).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(hdr, text="Amount", font=("Segoe UI", 9, "bold"), width=12).pack(side=tk.LEFT)
        ttk.Button(hdr, text="＋ Add Payment Method",
                   command=lambda: _add_row()).pack(side=tk.RIGHT)

        # Scrollable rows canvas
        rows_canvas = tk.Canvas(left_frame, highlightthickness=0)
        rows_canvas.configure(yscrollcommand=rows_scrollbar.set)
        rows_scrollbar.configure(command=rows_canvas.yview)
        rows_canvas.pack(fill=tk.BOTH, expand=True)
        rows_container = ttk.Frame(rows_canvas)
        _rows_win = rows_canvas.create_window((0, 0), window=rows_container, anchor=tk.NW)

        def _on_rows_resize(event=None):
            rows_canvas.configure(scrollregion=rows_canvas.bbox("all"))
            h = min(rows_container.winfo_reqheight(), 160)
            rows_canvas.configure(height=max(h, 32))

        rows_container.bind("<Configure>", _on_rows_resize)
        rows_canvas.bind("<Configure>", lambda e: rows_canvas.itemconfig(_rows_win, width=e.width))

        def _refresh_summary(*_):
            try:
                total_paid = sum(float(r["amount_var"].get() or 0) for r in payment_rows)
            except ValueError:
                total_paid = 0.0
            rem    = recalc_total - total_paid
            chg    = max(0.0, -rem)
            paid_var.set(f"{total_paid:.2f}")
            remaining_var.set(f"{max(0.0, rem):.2f}")
            change_var.set(f"{chg:.2f}")
            if complete_btn_ref:
                complete_btn_ref[0].config(state=tk.NORMAL if total_paid >= recalc_total - 0.005 else tk.DISABLED)

        def _remove_row(rd):
            rd["row_frame"].destroy()
            payment_rows.remove(rd)
            _refresh_summary()
            if not payment_rows:
                _add_row(payment_method)

        def _set_exact(rd):
            """Fill this row with exactly the remaining unpaid balance."""
            try:
                others = sum(float(r["amount_var"].get() or 0) for r in payment_rows if r is not rd)
            except ValueError:
                others = 0.0
            rd["amount_var"].set(f"{max(0.0, recalc_total - others):.2f}")
            _refresh_summary()

        def _add_row(default_method: str = "", default_amount: str = ""):
            rframe = ttk.Frame(rows_container)
            rframe.pack(fill=tk.X, pady=2)

            m_var = tk.StringVar(value=default_method)
            a_var = tk.StringVar(value=default_amount)

            ttk.Combobox(rframe, textvariable=m_var, values=available_methods,
                         state="readonly", width=14).pack(side=tk.LEFT, padx=(0, 6))

            amt_entry = ttk.Entry(rframe, textvariable=a_var, width=12)
            amt_entry.pack(side=tk.LEFT, padx=(0, 4))
            a_var.trace("w", _refresh_summary)

            rd = {"method_var": m_var, "amount_var": a_var, "row_frame": rframe}
            payment_rows.append(rd)

            ttk.Button(rframe, text="Exact", width=6,
                       command=lambda r=rd: _set_exact(r)).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Button(rframe, text="✕", width=3,
                       command=lambda r=rd: _remove_row(r)).pack(side=tk.LEFT)

            _refresh_summary()
            amt_entry.focus_set()
            return rd

        # Pre-load first row blank - operator must choose
        _add_row(payment_method)
        _refresh_summary()

        # ── Buttons ─────────────────────────────────────────────────────────────
        # (btn_frame and summary strip already created and packed at the bottom above)

        def on_complete():
            valid_rows = []
            for r in payment_rows:
                try:
                    amt = float(r["amount_var"].get() or 0)
                except ValueError:
                    messagebox.showerror("Invalid Input", "Enter a valid numeric amount for each payment row.")
                    return
                if amt < 0:
                    messagebox.showerror("Invalid Input", "Payment amounts must be positive.")
                    return
                if amt > 0:
                    method = r["method_var"].get()
                    if not method:
                        messagebox.showerror("Missing Payment Method", "Please select a payment method for each payment row.")
                        return
                    valid_rows.append({"method": method, "amount": amt})

            if not valid_rows:
                messagebox.showerror("No Payment", "Enter at least one payment amount.")
                return

            total_paid = sum(r["amount"] for r in valid_rows)
            if total_paid < recalc_total - 0.005:
                messagebox.showerror("Insufficient Payment",
                                     f"Total paid ({total_paid:.2f}) is less than order total ({recalc_total:.2f}).")
                return

            is_split     = len(valid_rows) > 1
            single_method = valid_rows[0]["method"] if not is_split else None
            change_amt    = max(0.0, total_paid - recalc_total)

            try:
                sale_lines = []
                for e in cart:
                    line_item = {'item_id': e['item_id']}
                    if e.get('variant_id'):
                        line_item['variant_id'] = e['variant_id']
                    if e.get('portion_id'):
                        line_item['portion_id'] = e['portion_id']
                    if e.get('is_special_volume'):
                        line_item.update({
                            'quantity': e.get('qty_ml') or e.get('quantity'),
                            'price':    e.get('price_per_ml') or e.get('price'),
                        })
                    else:
                        try:
                            it = items.get_item(e.get('item_id'))
                            unit_size = float(it.get('unit_size_ml') or 1)
                        except Exception:
                            unit_size = 1
                        per_unit = float(e.get('price', 0)) / unit_size if unit_size else float(e.get('price', 0))
                        line_item.update({'quantity': e.get('quantity', 1), 'price': per_unit})
                    sale_lines.append(line_item)

                sale_result = pos.create_sale(
                    sale_lines,
                    payment=total_paid,
                    change=change_amt,
                    payment_method=single_method,
                    split_payments=valid_rows if is_split else None,
                    vat_amount=recalc_vat,
                    discount_amount=discount,
                )
                self.sale_id = sale_result.get("sale_id")
                receipt_number = sale_result.get("receipt_number", "")
                self.result = True
                messagebox.showinfo("Sale Complete",
                                    f"Receipt {receipt_number or '#' + str(self.sale_id)} completed.\n"
                                    + (f"Change: {change_amt:.2f}" if change_amt > 0 else ""))
                dialog.destroy()
            except pos.InsufficientStock as exc:
                messagebox.showerror("Stock Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Checkout Error", f"Checkout failed:\n{exc}")

        complete_btn = ttk.Button(btn_frame, text="Complete Sale", command=on_complete)
        complete_btn.pack(side=tk.LEFT, padx=4)
        complete_btn_ref.append(complete_btn)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)

        # Size and show dialog
        dialog.update_idletasks()
        req_w = dialog.winfo_reqwidth()
        req_h = dialog.winfo_reqheight()
        dialog.geometry(f"{min(max(req_w + 20, 580), 820)}x{min(max(req_h + 20, 460), 740)}")
        dialog.deiconify()
        dialog.wait_window()
