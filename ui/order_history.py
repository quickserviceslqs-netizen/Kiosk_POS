"""Order history and receipt viewing UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import tkcalendar

from modules import receipts, refunds
from utils import set_window_icon
from utils.security import get_currency_code


class OrderHistoryFrame(ttk.Frame):
    """Display past orders with search, filtering, and receipt viewing."""
    
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.tree = None
        self._build_ui()
        self.refresh()
    
    def _build_ui(self):
        """Build the UI layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.grid_propagate(True)
        
        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Order History", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="🏠 Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)
        
        # Date range filters
        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 8))
        
        ttk.Label(filter_frame, text="From:").pack(side=tk.LEFT, padx=(0, 4))
        self.start_date = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        ttk.Entry(filter_frame, textvariable=self.start_date, width=12).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(filter_frame, text="To:").pack(side=tk.LEFT, padx=(8, 4))
        self.end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(filter_frame, textvariable=self.end_date, width=12).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(filter_frame, text="Search Receipt #:").pack(side=tk.LEFT, padx=(8, 4))
        self.search_term = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_term, width=12).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(filter_frame, text="🔍 Filter", command=self._filter_orders).pack(side=tk.LEFT, padx=4)
        ttk.Button(filter_frame, text="Clear", command=self._clear_filter).pack(side=tk.LEFT, padx=2)
        
        # Action buttons
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Button(button_frame, text="📄 View Receipt", command=self._view_receipt, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="🖨️ Print Receipt", command=self._print_receipt, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="💰 Refund", command=self._refund_order, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="💾 Export", command=self._export_receipt, width=15).pack(side=tk.LEFT, padx=4)
        
        # Order list table
        columns = ("sale_id", "date", "time", "total", "payment_method", "refunded")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=25)
        self.tree.heading("sale_id", text="Receipt #")
        self.tree.heading("date", text="Date")
        self.tree.heading("time", text="Time")
        self.tree.heading("total", text="Total")
        self.tree.heading("payment_method", text="Payment Method")
        self.tree.heading("refunded", text="Status")
        
        self.tree.column("sale_id", width=80, minwidth=60, anchor=tk.CENTER)
        self.tree.column("date", width=100, minwidth=80)
        self.tree.column("time", width=80, minwidth=70)
        self.tree.column("total", width=100, minwidth=80, anchor=tk.E)
        self.tree.column("payment_method", width=120, minwidth=100)
        self.tree.column("refunded", width=80, minwidth=70, anchor=tk.CENTER)
        
        self.tree.grid(row=3, column=0, sticky=tk.NSEW, pady=(0, 8))
        
        # Scrollbar
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=3, column=1, sticky=tk.NS, pady=(0, 8))
        self.tree.configure(yscroll=scroll.set)
        
        # Status bar
        bottom = ttk.Frame(self)
        bottom.grid(row=4, column=0, sticky=tk.EW)
        self.count_label = ttk.Label(bottom, text="Orders: 0", font=("Segoe UI", 10, "bold"))
        self.count_label.pack(side=tk.LEFT, padx=8)
        self.total_label = ttk.Label(bottom, text="Total: 0.00", font=("Segoe UI", 10, "bold"))
        self.total_label.pack(side=tk.LEFT, padx=8)
    
    def refresh(self) -> None:
        """Refresh the order list."""
        self._filter_orders()
    
    def _filter_orders(self) -> None:
        """Filter and display orders."""
        currency = get_currency_code()
        
        # Clear table
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start = self.start_date.get().strip() or None
        end = self.end_date.get().strip() or None
        search = self.search_term.get().strip() or None
        
        sales = receipts.list_sales_with_search(start, end, search, limit=500)
        
        total = 0.0
        for sale in sales:
            sid = sale["sale_id"]
            if refunds.is_sale_fully_refunded(sid):
                refund_status = "✓ Refunded"
            elif refunds.get_refunded_quantities_for_sale(sid):
                refund_status = "Partially Refunded"
            else:
                refund_status = "Paid"
            receipt_num = sale.get("receipt_number", f"#{sale['sale_id']}")
            self.tree.insert(
                "",
                tk.END,
                iid=str(sale["sale_id"]),
                values=(
                    receipt_num,
                    sale["date"],
                    sale["time"],
                    f"{currency} {sale['total']:.2f}",
                    sale.get("payment_method", "Cash"),
                    refund_status
                ),
                tags=("refunded",) if refund_status.startswith("✓") else ()
            )
            total += sale["total"]
        
        self.tree.tag_configure("refunded", background="#FFE5E5")
        self.count_label.config(text=f"Orders: {len(sales)}")
        self.total_label.config(text=f"Total: {currency} {total:.2f}")
    
    def _clear_filter(self) -> None:
        """Clear all filters."""
        self.start_date.set((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        self.end_date.set(datetime.now().strftime("%Y-%m-%d"))
        self.search_term.set("")
        self._filter_orders()
    
    def _selected_sale_id(self) -> int | None:
        """Get selected sale ID."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Order", "Please select an order")
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None
    
    def _view_receipt(self, return_popup: bool = False) -> tk.Toplevel | None:
        """View receipt details."""
        try:
            sale_id = self._selected_sale_id()
            if not sale_id:
                return None
            
            receipt_text = receipts.get_receipt_by_id(sale_id)
            if not receipt_text:
                messagebox.showerror("Error", "Receipt not found")
                return None
            
            # Create popup window with size set before showing
            popup = tk.Toplevel(self)
            popup.withdraw()  # Hide until fully built
            popup.title(f"Receipt #{sale_id}")
            set_window_icon(popup)
            
            text = tk.Text(popup, wrap=tk.WORD, font=("Courier", 10))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert("1.0", receipt_text)
            text.config(state=tk.DISABLED)
            
            scroll = ttk.Scrollbar(text, command=text.yview)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            text.config(yscrollcommand=scroll.set)
            
            # Set geometry and show
            popup.update_idletasks()
            popup.geometry("600x500")
            popup.deiconify()  # Show after fully built
            
            if return_popup:
                return popup
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view receipt: {e}")
            return None
    
    def _print_receipt(self) -> None:
        """Print receipt using system print dialog."""
        import tempfile
        import os
        import subprocess
        
        try:
            sale_id = self._selected_sale_id()
            if not sale_id:
                return
            
            receipt_text = receipts.get_receipt_by_id(sale_id)
            if not receipt_text:
                messagebox.showerror("Error", "Receipt not found")
                return
            
            # Create temp file for printing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(receipt_text)
                temp_path = f.name
            
            # Try to print using Windows notepad (silent print)
            try:
                # Open print dialog via notepad
                subprocess.Popen(['notepad', '/p', temp_path], shell=True)
            except Exception:
                # Fallback: just open the file
                os.startfile(temp_path, 'print')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print: {e}")
    
    def _export_receipt(self) -> None:
        """Export receipt as text file."""
        try:
            sale_id = self._selected_sale_id()
            if not sale_id:
                return
            
            receipt_text = receipts.get_receipt_by_id(sale_id)
            if not receipt_text:
                messagebox.showerror("Error", "Receipt not found")
                return
            
            filename = filedialog.asksaveasfilename(
                title="Save Receipt",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"Receipt_{sale_id}.txt"
            )
            if not filename:
                return
            
            with open(filename, 'w') as f:
                f.write(receipt_text)
            messagebox.showinfo("Exported", f"Receipt saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
    
    def _refund_order(self) -> None:
        """Process a refund for selected order."""
        try:
            sale_id = self._selected_sale_id()
            if not sale_id:
                return
            
            # If the sale is fully refunded, block further refunds; otherwise allow partial/multiple refunds
            if refunds.is_sale_fully_refunded(sale_id):
                last = refunds.get_last_refund_for_sale(sale_id)
                if last:
                    messagebox.showwarning("Already Refunded", f"This order was already fully refunded on {last['created_at']}")
                else:
                    messagebox.showwarning("Already Refunded", "This order was already fully refunded")
                return
            
            # Get sale details
            sale_data = receipts.get_sale_with_items(sale_id)
            if not sale_data:
                messagebox.showerror("Error", "Sale not found")
                return
            
            # Show refund confirmation dialog
            dialog = tk.Toplevel(self)
            dialog.withdraw()  # Hide until fully built
            receipt_num = sale_data.get("receipt_number", f"#{sale_id}")
            dialog.title(f"Refund {receipt_num}")
            set_window_icon(dialog)
            dialog.transient(self.winfo_toplevel())
            dialog.grab_set()
            dialog.columnconfigure(0, weight=1)
            dialog.rowconfigure(2, weight=1)
            
            currency = get_currency_code()
            
            # Order summary
            ttk.Label(dialog, text=f"Refund {receipt_num}", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=8)
            ttk.Label(dialog, text=f"Amount: {currency} {sale_data['total']:.2f}").grid(row=1, column=0, sticky=tk.W, padx=12)
            ttk.Label(dialog, text=f"Date: {sale_data['date']} {sale_data['time']}").grid(row=1, column=1, sticky=tk.W)
            
            # Items to refund
            ttk.Label(dialog, text="Select items to refund:", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=12, pady=(12, 4))
            
            # Items frame with scrollbar
            items_frame = ttk.Frame(dialog)
            items_frame.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, padx=12, pady=4)
            items_frame.columnconfigure(0, weight=1)
            
            canvas = tk.Canvas(items_frame, highlightthickness=0)
            scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Item checkboxes with prices and per-line refundable quantities
            # Use sale_item_id (unique per sales_items row) as the key so we handle repeated item_ids correctly
            item_vars = {}
            item_qty_vars = {}
            item_prices = {}

            # Get refunded quantities map to compute what's still refundable
            refunded_map = refunds.get_refunded_quantities_for_sale(sale_id)

            for item in sale_data["items"]:
                sale_item_id = item.get("sale_item_id") or f"si_{id(item)}"
                already_refunded = refunded_map.get(item.get("sale_item_id"), 0.0)
                available_qty = max(0.0, float(item["quantity"]) - float(already_refunded))

                # Boolean var: disabled if nothing to refund
                var = tk.BooleanVar(value=(available_qty > 0))
                item_vars[sale_item_id] = var

                # Quantity to refund var (defaults to available_qty)
                qty_var = tk.StringVar(value=f"{available_qty:.2f}" if available_qty % 1 else f"{int(available_qty)}")
                item_qty_vars[sale_item_id] = qty_var

                # Price per unit (sales_items.price is per unit / per-small-unit already)
                price_per_unit = float(item.get("price") or 0)
                item_prices[sale_item_id] = price_per_unit * available_qty

                item_frame = ttk.Frame(scrollable_frame)
                item_frame.pack(fill=tk.X, padx=8, pady=4)

                # Build label text showing sold qty and available to refund
                label_text = f"{item['name']} sold x{item['quantity']}"
                if available_qty <= 0:
                    label_text += " (already refunded)"
                else:
                    label_text += f" - refund available: {available_qty} @ {currency} {price_per_unit:.2f} = {currency} {price_per_unit * available_qty:.2f}"

                cb = ttk.Checkbutton(
                    item_frame,
                    text=label_text,
                    variable=var,
                    state=("!disabled" if available_qty > 0 else "disabled")
                )
                cb.pack(side=tk.LEFT)

                # If available_qty > 0, allow specifying partial refund quantity (Entry)
                if available_qty > 0:
                    qty_entry = ttk.Entry(item_frame, textvariable=qty_var, width=8)
                    qty_entry.pack(side=tk.LEFT, padx=(8, 0))

                    def _qty_changed(sid=sale_item_id, pv=price_per_unit):
                        try:
                            q = float(item_qty_vars[sid].get() or 0)
                        except Exception:
                            q = 0
                        item_prices[sid] = pv * q
                        # Update amount display
                        update_refund_amount()

                    qty_var.trace_add("write", lambda *_a, sid=sale_item_id: _qty_changed(sid))
                
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Refund amount display
            ttk.Label(dialog, text="Refund Amount:", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky=tk.W, padx=12, pady=(8, 0))
            refund_amount_label = ttk.Label(dialog, text=f"{currency} {sale_data['total']:.2f}", font=("Segoe UI", 11, "bold"), foreground="green")
            refund_amount_label.grid(row=4, column=1, sticky=tk.W, padx=12, pady=(8, 0))
            
            def update_refund_amount(*args):
                total = sum(item_prices[item_id] for item_id, var in item_vars.items() if var.get())
                refund_amount_label.config(text=f"{currency} {total:.2f}")
            
            for var in item_vars.values():
                var.trace("w", update_refund_amount)
            # Initialize computed refund amount
            update_refund_amount()
            
            # Reason
            ttk.Label(dialog, text="Refund Reason:").grid(row=5, column=0, sticky=tk.W, padx=12, pady=(8, 0))
            reason_var = tk.StringVar()
            ttk.Combobox(
                dialog,
                textvariable=reason_var,
                values=["Customer Request", "Damaged Item", "Wrong Item", "No Longer Wanted", "Other"],
                width=40
            ).grid(row=5, column=1, sticky=tk.W, padx=12, pady=(8, 0))
            
            # Buttons
            button_frame = ttk.Frame(dialog)
            button_frame.grid(row=6, column=0, columnspan=2, pady=12)
            
            def do_refund():
                try:
                    # Get selected items
                    selected_items = []
                    for item in sale_data["items"]:
                        sid = item.get("sale_item_id") or f"si_{id(item)}"
                        if not item_vars.get(sid) or not item_vars[sid].get():
                            continue
                        # Read requested quantity from qty var (default to remaining available)
                        qvar = item_qty_vars.get(sid)
                        try:
                            q = float(qvar.get()) if qvar else float(item.get("quantity"))
                        except Exception:
                            q = float(item.get("quantity"))
                        selected_items.append({
                            "sale_item_id": item.get("sale_item_id"),
                            "item_id": item["item_id"],
                            "quantity": q
                        })
                    
                    if not selected_items:
                        messagebox.showwarning("No Items", "Please select at least one item to refund")
                        return
                    
                    # Calculate refund amount
                    refund_amount = sum(item_prices[item_id] for item_id, var in item_vars.items() if var.get())
                    
                    reason = reason_var.get() or "Customer Request"
                    refund_record = refunds.create_refund(sale_id, selected_items, reason, refund_amount)
                    messagebox.showinfo("Refund Processed", f"Refund of {currency} {refund_record['refund_amount']:.2f} processed successfully")
                    dialog.destroy()
                    self._filter_orders()
                except refunds.RefundError as e:
                    messagebox.showerror("Refund Error", str(e))
                except Exception as e:
                    messagebox.showerror("Error", f"Refund failed: {e}")
            
            ttk.Button(button_frame, text="Process Refund", command=do_refund).pack(side=tk.LEFT, padx=4)
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)
            
            # Set geometry and show dialog after content is built
            dialog.update_idletasks()
            dialog.geometry("600x500")
            dialog.deiconify()  # Show after fully built
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process refund: {e}")
