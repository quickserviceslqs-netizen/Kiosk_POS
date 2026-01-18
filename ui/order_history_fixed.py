"""Order history and receipt viewing UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import tkcalendar
import logging
import os

from modules import receipts, refunds
from utils import set_window_icon
from utils.security import get_currency_code, subscribe_payment_methods, unsubscribe_payment_methods, get_payment_methods


# Setup audit logging
AUDIT_LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'order_history_audit.log')
os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)

audit_logger = logging.getLogger('order_history_audit')
audit_logger.setLevel(logging.INFO)
handler = logging.FileHandler(AUDIT_LOG_FILE)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
audit_logger.addHandler(handler)


def log_audit_action(action: str, sale_id: int, user: str = "Unknown", details: str = "") -> None:
    """Log an audit action for order history operations."""
    audit_logger.info(f"ACTION={action}, SALE_ID={sale_id}, USER={user}, DETAILS={details}")


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
        try:
            # Try to get position relative to widget
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        except:
            # Fallback position
            x, y = 100, 100
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class OrderHistoryFrame(ttk.Frame):
    """Display past orders with search, filtering, and receipt viewing."""
    
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.tree = None
        print("DEBUG: About to call _build_ui")
        self._build_ui()
        print("DEBUG: _build_ui completed, tree =", self.tree)
        # Populate dynamic filter lists
        self._load_filter_lists()
        # Defer refresh to ensure UI is fully built
        self.after_idle(self.refresh)
    
    def _build_ui(self):
        """Build the UI layout."""
        print("DEBUG: _build_ui started")
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
        self.start_date.trace("w", lambda *args: self.refresh())
        start_frame = ttk.Frame(filter_frame)
        start_frame.pack(side=tk.LEFT, padx=2)
        start_entry = ttk.Entry(start_frame, textvariable=self.start_date, width=12)
        start_entry.pack(side=tk.LEFT)
        ttk.Button(start_frame, text="📅", width=2, command=self._pick_start_date).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(filter_frame, text="To:").pack(side=tk.LEFT, padx=(8, 4))
        self.end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.end_date.trace("w", lambda *args: self.refresh())
        end_frame = ttk.Frame(filter_frame)
        end_frame.pack(side=tk.LEFT, padx=2)
        end_entry = ttk.Entry(end_frame, textvariable=self.end_date, width=12)
        end_entry.pack(side=tk.LEFT)
        ttk.Button(end_frame, text="📅", width=2, command=self._pick_end_date).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=(8, 4))
        self.search_term = tk.StringVar()
        self.search_term.trace("w", lambda *args: self.refresh())
        search_frame = ttk.Frame(filter_frame)
        search_frame.pack(side=tk.LEFT, padx=2)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_term, width=20)
        search_entry.pack(side=tk.LEFT)
        ToolTip(search_entry, "Search by receipt number, customer name, or cashier")
        ttk.Button(search_frame, text="×", width=2, command=self._clear_search).pack(side=tk.LEFT, padx=2)
        # Advanced filters: Payment method, Refund status, User (cashier), Customer
        self.payment_method_var = tk.StringVar(value="Any")
        ttk.Label(filter_frame, text="Payment:").pack(side=tk.LEFT, padx=(8, 2))
        values = ["Any"] + get_payment_methods()
        self.payment_method_cb = ttk.Combobox(filter_frame, textvariable=self.payment_method_var, values=values, width=10, state='readonly')
        # Subscribe to payment method changes so filter stays in sync
        subscribe_payment_methods(self._on_payment_methods_changed)
        self.bind("<Destroy>", lambda _e: unsubscribe_payment_methods(self._on_payment_methods_changed))
        self.payment_method_cb.pack(side=tk.LEFT, padx=2)
        self.payment_method_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        self.refund_status_var = tk.StringVar(value="Any")
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(8, 2))
        self.status_cb = ttk.Combobox(filter_frame, textvariable=self.refund_status_var, values=["Any", "Active", "Partially Refunded", "Fully Refunded", "Voided"], width=15, state='readonly')
        self.status_cb.pack(side=tk.LEFT, padx=2)
        self.status_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        self.user_var = tk.StringVar(value="Any")
        ttk.Label(filter_frame, text="Cashier:").pack(side=tk.LEFT, padx=(8, 2))
        self.user_cb = ttk.Combobox(filter_frame, textvariable=self.user_var, values=["Any"], width=12)
        self.user_cb.pack(side=tk.LEFT, padx=2)
        self.user_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        self.customer_var = tk.StringVar(value="Any")
        ttk.Label(filter_frame, text="Customer:").pack(side=tk.LEFT, padx=(8, 2))
        self.customer_cb = ttk.Combobox(filter_frame, textvariable=self.customer_var, values=["Any"], width=12)
        self.customer_cb.pack(side=tk.LEFT, padx=2)
        self.customer_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        
        ttk.Button(filter_frame, text="Apply", command=self._filter_orders).pack(side=tk.LEFT, padx=4)
        ttk.Button(filter_frame, text="Clear", command=self._clear_filter).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="📊 Generate Report", command=self._generate_report).pack(side=tk.LEFT, padx=4)
        
        # Action buttons
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Button(button_frame, text="📄 View Receipt", command=self._view_receipt, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="🖨️ Print Receipt", command=self._print_receipt, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="💰 Refund", command=self._refund_order, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="� Void Sale", command=self._void_sale, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="�💾 Export Receipt", command=self._export_receipt, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="📊 Export All", command=self._export_all_orders, width=15).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="📋 Order Details", command=self._view_order_details, width=15).pack(side=tk.LEFT, padx=4)
        
        # Order list table (include customer and cashier columns)
        columns = ("sale_id", "date", "time", "customer", "user", "total", "payment_method", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=25)
        print("DEBUG: tree created, self.tree =", self.tree)
        self.tree.heading("sale_id", text="Receipt #")
        self.tree.heading("date", text="Date")
        self.tree.heading("time", text="Time")
        self.tree.heading("customer", text="Customer")
        self.tree.heading("user", text="Cashier")
        self.tree.heading("total", text="Total")
        self.tree.heading("payment_method", text="Payment Method")
        self.tree.heading("status", text="Status")
        
        self.tree.column("sale_id", width=80, minwidth=60, anchor=tk.CENTER)
        self.tree.column("date", width=100, minwidth=80)
        self.tree.column("time", width=80, minwidth=70)
        self.tree.column("customer", width=140, minwidth=100)
        self.tree.column("user", width=100, minwidth=80)
        self.tree.column("total", width=100, minwidth=80, anchor=tk.E)
        self.tree.column("payment_method", width=120, minwidth=100)
        self.tree.column("status", width=100, minwidth=80, anchor=tk.CENTER)
        
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
        
        # Transaction type summaries
        ttk.Separator(bottom, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self.sales_label = ttk.Label(bottom, text="Sales: 0 (0.00)", font=("Segoe UI", 9))
        self.sales_label.pack(side=tk.LEFT, padx=8)
        self.refunds_label = ttk.Label(bottom, text="Refunds: 0 (0.00)", font=("Segoe UI", 9))
        self.refunds_label.pack(side=tk.LEFT, padx=8)
        self.voids_label = ttk.Label(bottom, text="Voids: 0 (0.00)", font=("Segoe UI", 9))
        self.voids_label.pack(side=tk.LEFT, padx=8)
    
    def _on_payment_methods_changed(self) -> None:
        try:
            vals = ["Any"] + get_payment_methods()
            cur = self.payment_method_var.get()
            self.payment_method_cb['values'] = vals
            if cur not in vals:
                self.payment_method_var.set("Any")
        except Exception:
            pass

    def refresh(self) -> None:
        """Refresh the order list."""
        # Refresh available filter lists (users/customers may change)
        self._load_filter_lists()
        self._filter_orders()
    
    def _filter_orders(self) -> None:
        """Filter and display orders."""
        if self.tree is None:
            return  # UI not fully initialized yet
        
        currency = get_currency_code()
        
        # Clear table
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start = self.start_date.get().strip() or None
        end = self.end_date.get().strip() or None
        search = self.search_term.get().strip() or None
        payment_filter = self.payment_method_var.get() if hasattr(self, 'payment_method_var') else 'Any'
        status_filter = self.refund_status_var.get() if hasattr(self, 'refund_status_var') else 'Any'
        user_filter = self.user_var.get() if hasattr(self, 'user_var') else 'Any'
        customer_filter = self.customer_var.get() if hasattr(self, 'customer_var') else 'Any'
        
        sales = receipts.list_sales_with_search(start, end, search, limit=500)
        
        total = 0.0
        displayed = 0
        sales_count = 0
        sales_total = 0.0
        refunds_count = 0
        refunds_total = 0.0
        voids_count = 0
        voids_total = 0.0
        
        for sale in sales:
            sid = sale["sale_id"]
            
            # Determine status (refund + void)
            if sale.get("voided"):
                sale_status = "Voided"
            elif refunds.is_sale_fully_refunded(sid):
                sale_status = "Fully Refunded"
            elif refunds.get_refunded_quantities_for_sale(sid):
                sale_status = "Partially Refunded"
            else:
                sale_status = "Active"
            
            # Apply payment method filter
            if payment_filter and payment_filter != 'Any' and sale.get('payment_method') != payment_filter:
                continue
            # Apply status filter
            if status_filter and status_filter != 'Any' and sale_status != status_filter:
                continue
            # Apply user filter
            if user_filter and user_filter != 'Any' and sale.get('username') != user_filter:
                continue
            # Apply customer filter
            if customer_filter and customer_filter != 'Any' and sale.get('customer_name') != customer_filter:
                continue
            
            receipt_num = sale.get("receipt_number", f"#{sale['sale_id']}")
            self.tree.insert(
                "",
                tk.END,
                iid=str(sale["sale_id"]),
                values=(
                    receipt_num,
                    sale["date"],
                    sale["time"],
                    sale.get("customer_name", ""),
                    sale.get("username", ""),
                    f"{currency} {sale['total']:.2f}",
                    sale.get("payment_method", "Cash"),
                    sale_status
                ),
                tags=("voided",) if sale_status == 'Voided' else ("refunded",) if sale_status == 'Fully Refunded' else ()
            )
            total += sale["total"]
            displayed += 1
            
            # Track transaction type counts and totals
            if sale_status == "Active":
                sales_count += 1
                sales_total += sale["total"]
            elif sale_status in ("Fully Refunded", "Partially Refunded"):
                refunds_count += 1
                refunds_total += sale["total"]
            elif sale_status == "Voided":
                voids_count += 1
                voids_total += sale["total"]
        
        self.tree.tag_configure("voided", background="#FFCCCC")
        self.tree.tag_configure("refunded", background="#FFE5E5")
        self.count_label.config(text=f"Orders: {displayed}")
        self.total_label.config(text=f"Total: {currency} {total:.2f}")
        self.sales_label.config(text=f"Sales: {sales_count} ({currency} {sales_total:.2f})")
        self.refunds_label.config(text=f"Refunds: {refunds_count} ({currency} {refunds_total:.2f})")
        self.voids_label.config(text=f"Voids: {voids_count} ({currency} {voids_total:.2f})")
    
    def _load_filter_lists(self) -> None:
        """Load dynamic filter lists for users and customers."""
        try:
            from database.init_db import get_connection
            
            with get_connection() as conn:
                # Load users (cashiers)
                users = conn.execute("SELECT username FROM users WHERE active = 1 ORDER BY username").fetchall()
            user_list = ["Any"] + [row[0] for row in users]
            if hasattr(self, 'user_cb'):
                self.user_cb['values'] = user_list
                if self.user_var.get() not in user_list:
                    self.user_var.set("Any")
            
            # Load customers
            customers = conn.execute("SELECT name FROM customers ORDER BY name").fetchall()
            customer_list = ["Any"] + [row[0] for row in customers]
            if hasattr(self, 'customer_cb'):
                self.customer_cb['values'] = customer_list
                if self.customer_var.get() not in customer_list:
                    self.customer_var.set("Any")
                    
        except Exception as e:
            # If loading fails, just use "Any" as fallback
            if hasattr(self, 'user_cb'):
                self.user_cb['values'] = ["Any"]
            if hasattr(self, 'customer_cb'):
                self.customer_cb['values'] = ["Any"]
    
    def _clear_filter(self) -> None:
        """Clear all filters."""
        self.start_date.set((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        self.end_date.set(datetime.now().strftime("%Y-%m-%d"))
        self.search_term.set("")
        if hasattr(self, 'payment_method_var'):
            self.payment_method_var.set("Any")
        if hasattr(self, 'refund_status_var'):
            self.refund_status_var.set("Any")
        if hasattr(self, 'user_var'):
            self.user_var.set("Any")
        if hasattr(self, 'customer_var'):
            self.customer_var.set("Any")
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
    
    def _export_all_orders(self) -> None:
        """Export all filtered orders to CSV with detailed line items."""
        try:
                # Get current filters
                start = self.start_date.get().strip() or None
                end = self.end_date.get().strip() or None
                search = self.search_term.get().strip() or None
                payment_filter = self.payment_method_var.get() if hasattr(self, 'payment_method_var') else 'Any'
                refund_filter = self.refund_status_var.get() if hasattr(self, 'refund_status_var') else 'Any'
                user_filter = self.user_var.get() if hasattr(self, 'user_var') else 'Any'
                customer_filter = self.customer_var.get() if hasattr(self, 'customer_var') else 'Any'
            
            # Get filtered sales
            sales = receipts.list_sales_with_search(start, end, search, limit=10000)  # Higher limit for export
            
            # Apply additional filters
            filtered_sales = []
            for sale in sales:
                sid = sale["sale_id"]
                # Determine refund status
                if refunds.is_sale_fully_refunded(sid):
                    refund_status = "Fully Refunded"
                elif refunds.get_refunded_quantities_for_sale(sid):
                    refund_status = "Partially Refunded"
                else:
                    refund_status = "Not Refunded"
                
                # Apply filters
                if payment_filter and payment_filter != 'Any' and sale.get('payment_method') != payment_filter:
                    continue
                if refund_filter and refund_filter != 'Any':
                    if refund_filter == 'Not Refunded' and refund_status != 'Not Refunded':
                        continue
                    if refund_filter == 'Fully Refunded' and refund_status != 'Fully Refunded':
                        continue
                    if refund_filter == 'Partially Refunded' and refund_status != 'Partially Refunded':
                        continue
                if user_filter and user_filter != 'Any' and sale.get('username') != user_filter:
                    continue
                if customer_filter and customer_filter != 'Any' and sale.get('customer_name') != customer_filter:
                    continue
                
                filtered_sales.append((sale, refund_status))
            
            if not filtered_sales:
                messagebox.showinfo("No Data", "No orders match the current filters")
                return
            
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                title="Export All Orders",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"orders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            if not filename:
                return
            
            # Generate CSV
            import csv
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    "Receipt Number", "Date", "Time", "Customer", "Cashier", 
                    "Item Name", "Category", "Quantity", "Unit Price", "Line Total",
                    "Payment Method", "Refund Status", "Order Total", "Subtotal", "VAT", "Discount"
                ])
                
                # Write each sale's line items
                for sale, refund_status in filtered_sales:
                    # Get full sale details with items
                    sale_details = receipts.get_sale_with_items(sale["sale_id"])
                    if not sale_details:
                        continue
                    
                    receipt_num = sale.get("receipt_number", f"#{sale['sale_id']}")
                    
                    # Write each line item
                    for item in sale_details["items"]:
                        writer.writerow([
                            receipt_num,
                            sale_details["date"],
                            sale_details["time"],
                            sale.get("customer_name", ""),
                            sale.get("username", ""),
                            item.get("name", "Unknown"),
                            item.get("category", ""),
                            item["quantity"],
                            item["price"],
                            item["price"] * item["quantity"],
                            sale_details.get("payment_method", "Cash"),
                            refund_status,
                            sale_details["total"],
                            sale_details.get("subtotal", 0),
                            sale_details.get("vat_amount", 0),
                            sale_details.get("discount_amount", 0)
                        ])
            
            messagebox.showinfo("Exported", f"Exported {len(filtered_sales)} orders to {filename}")
            
            # Log the bulk export action
            current_user = getattr(self.master, 'current_user', {}).get('username', 'Unknown')
            log_audit_action("EXPORT_BULK", 0, current_user, f"Orders: {len(filtered_sales)}, File: {filename}, Filters: payment={payment_filter}, refund={refund_filter}, user={user_filter}, customer={customer_filter}")
            
            except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export orders: {e}")
        
        def _view_order_details(self) -> None:
            """Show detailed order information in a popup dialog."""
            try:
            sale_id = self._selected_sale_id()
            if not sale_id:
                return
            
            # Get full sale details
            sale_data = receipts.get_sale_with_items(sale_id)
            if not sale_data:
                messagebox.showerror("Error", "Order not found")
                return
            
            # Create popup window
            popup = tk.Toplevel(self)
            popup.withdraw()  # Hide until fully built
            popup.title(f"Order Details - {sale_data.get('receipt_number', f'#{sale_id}')}")
            set_window_icon(popup)
            popup.transient(self.winfo_toplevel())
            popup.columnconfigure(0, weight=1)
            popup.rowconfigure(1, weight=1)
            
            currency = get_currency_code()
            
            # Header frame
            header_frame = ttk.Frame(popup, padding=10)
            header_frame.grid(row=0, column=0, sticky=tk.EW)
            
            ttk.Label(header_frame, text=f"Order #{sale_data.get('receipt_number', sale_id)}", 
                     font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
            
            # Order info
            ttk.Label(header_frame, text="Date:").grid(row=1, column=0, sticky=tk.W)
            ttk.Label(header_frame, text=f"{sale_data['date']} {sale_data['time']}").grid(row=1, column=1, sticky=tk.W, padx=(10, 20))
            
            ttk.Label(header_frame, text="Customer:").grid(row=1, column=2, sticky=tk.W)
            ttk.Label(header_frame, text=sale_data.get('customer_name', 'Walk-in')).grid(row=1, column=3, sticky=tk.W, padx=(10, 0))
            
            ttk.Label(header_frame, text="Cashier:").grid(row=2, column=0, sticky=tk.W)
            ttk.Label(header_frame, text=sale_data.get('username', 'Unknown')).grid(row=2, column=1, sticky=tk.W, padx=(10, 20))
            
            ttk.Label(header_frame, text="Payment:").grid(row=2, column=2, sticky=tk.W)
            ttk.Label(header_frame, text=sale_data.get('payment_method', 'Cash')).grid(row=2, column=3, sticky=tk.W, padx=(10, 0))
            
            # Items frame
            items_frame = ttk.Frame(popup, padding=10)
            items_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=10, pady=(0, 10))
            items_frame.columnconfigure(0, weight=1)
            items_frame.rowconfigure(0, weight=1)
            
            ttk.Label(items_frame, text="Items:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
            
            # Items treeview
            columns = ("item", "qty", "price", "total")
            items_tree = ttk.Treeview(items_frame, columns=columns, show="headings", height=8)
            items_tree.heading("item", text="Item")
            items_tree.heading("qty", text="Quantity")
            items_tree.heading("price", text="Unit Price")
            items_tree.heading("total", text="Total")
            
            items_tree.column("item", width=200, minwidth=150)
            items_tree.column("qty", width=80, minwidth=60, anchor=tk.CENTER)
            items_tree.column("price", width=100, minwidth=80, anchor=tk.E)
            items_tree.column("total", width=100, minwidth=80, anchor=tk.E)
            
            items_tree.grid(row=1, column=0, sticky=tk.NSEW)
            
            # Scrollbar for items
            items_scroll = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=items_tree.yview)
            items_scroll.grid(row=1, column=1, sticky=tk.NS)
            items_tree.configure(yscrollcommand=items_scroll.set)
            
            # Populate items
            for item in sale_data["items"]:
                item_name = item.get("name", "Unknown")
                qty = item["quantity"]
                price = item["price"]
                total = price * qty
                
                items_tree.insert("", tk.END, values=(
                    item_name,
                    f"{qty:.2f}",
                    f"{currency} {price:.2f}",
                    f"{currency} {total:.2f}"
                ))
            
            # Summary frame
            summary_frame = ttk.Frame(popup, padding=10)
            summary_frame.grid(row=2, column=0, sticky=tk.EW)
            
            ttk.Label(summary_frame, text="Order Summary:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
            
            # Summary details
            subtotal = sale_data.get("subtotal", sum(item["price"] * item["quantity"] for item in sale_data["items"]))
            vat_amount = sale_data.get("vat_amount", 0)
            discount_amount = sale_data.get("discount_amount", 0)
            total = sale_data["total"]
            
            ttk.Label(summary_frame, text="Subtotal:").grid(row=1, column=0, sticky=tk.W)
            ttk.Label(summary_frame, text=f"{currency} {subtotal:.2f}").grid(row=1, column=1, sticky=tk.E, padx=(10, 0))
            
            if vat_amount > 0:
                ttk.Label(summary_frame, text="VAT:").grid(row=2, column=0, sticky=tk.W)
                ttk.Label(summary_frame, text=f"{currency} {vat_amount:.2f}").grid(row=2, column=1, sticky=tk.E, padx=(10, 0))
            
            if discount_amount > 0:
                ttk.Label(summary_frame, text="Discount:").grid(row=3, column=0, sticky=tk.W)
                ttk.Label(summary_frame, text=f"{currency} {discount_amount:.2f}").grid(row=3, column=1, sticky=tk.E, padx=(10, 0))
            
            ttk.Label(summary_frame, text="Total:", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=(10, 0))
            ttk.Label(summary_frame, text=f"{currency} {total:.2f}", font=("Segoe UI", 10, "bold")).grid(row=4, column=1, sticky=tk.E, padx=(10, 0), pady=(10, 0))
            
            # Payment info
            ttk.Label(summary_frame, text="Amount Paid:").grid(row=5, column=0, sticky=tk.W)
            ttk.Label(summary_frame, text=f"{currency} {sale_data.get('payment_received', total):.2f}").grid(row=5, column=1, sticky=tk.E, padx=(10, 0))
            
            change = sale_data.get("change", 0)
            if change > 0:
                ttk.Label(summary_frame, text="Change:").grid(row=6, column=0, sticky=tk.W)
                ttk.Label(summary_frame, text=f"{currency} {change:.2f}").grid(row=6, column=1, sticky=tk.E, padx=(10, 0))
            
            # Status (Voided, Refunded, or Regular Sale)
            is_voided = sale_data.get("voided", 0) == 1
            sid = sale_data["sale_id"]
            
            if is_voided:
                order_status = "Voided"
                status_color = "red"
            elif refunds.is_sale_fully_refunded(sid):
                order_status = "Fully Refunded"
                status_color = "orange"
            elif refunds.get_refunded_quantities_for_sale(sid):
                order_status = "Partially Refunded"
                status_color = "orange"
            else:
                order_status = "Regular Sale"
                status_color = "green"
            
            ttk.Label(summary_frame, text="Status:").grid(row=7, column=0, sticky=tk.W, pady=(10, 0))
            status_label = ttk.Label(summary_frame, text=order_status, foreground=status_color)
            status_label.grid(row=7, column=1, sticky=tk.E, padx=(10, 0), pady=(10, 0))
            
            # Set geometry and show
            popup.update_idletasks()
            popup.geometry("700x600")
            popup.deiconify()
            
            except Exception as e:
            messagebox.showerror("Error", f"Failed to view order details: {e}")
        
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
                    
                    # Log the refund action
                    current_user = getattr(self.master, 'current_user', {}).get('username', 'Unknown')
                    log_audit_action("REFUND", sale_id, current_user, f"Amount: {currency} {refund_record['refund_amount']:.2f}, Reason: {reason}")
                    
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
            
            # Log the export action
            current_user = getattr(self.master, 'current_user', {}).get('username', 'Unknown')
            log_audit_action("EXPORT_RECEIPT", sale_id, current_user, f"File: {filename}")
            
            except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")
        
        def _void_sale(self) -> None:
            """Void a sale transaction."""
            try:
            sale_id = self._selected_sale_id()
            if not sale_id:
                return
            
            # Check if sale is already voided
            if receipts.is_sale_voided(sale_id):
                messagebox.showwarning("Already Voided", "This sale has already been voided")
                return
            
            # Check if sale has refunds
            if refunds.get_refunded_quantities_for_sale(sale_id):
                if not messagebox.askyesno("Confirm Void", 
                    "This sale has refunds. Voiding will cancel the entire transaction.\n\nContinue?"):
                    return
            
            # Get sale details
            sale_data = receipts.get_sale_with_items(sale_id)
            if not sale_data:
                messagebox.showerror("Error", "Sale not found")
                return
            
            # Check permissions
            root = self.winfo_toplevel()
            current_user = getattr(root, 'current_user', {})
            from modules import permissions
            if not permissions.has_permission(current_user, 'void_sales'):
                messagebox.showerror("Permission Denied", "You do not have permission to void sales")
                return
            
            # Show void confirmation dialog
            dialog = tk.Toplevel(self)
            dialog.withdraw()
            receipt_num = sale_data.get("receipt_number", f"#{sale_id}")
            dialog.title(f"Void Sale {receipt_num}")
            set_window_icon(dialog)
            dialog.transient(self.winfo_toplevel())
            dialog.grab_set()
            
            currency = get_currency_code()
            
            # Sale summary
            ttk.Label(dialog, text=f"Void Sale {receipt_num}", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=8, padx=12)
            ttk.Label(dialog, text=f"Amount: {currency} {sale_data['total']:.2f}").grid(row=1, column=0, sticky=tk.W, padx=12)
            ttk.Label(dialog, text=f"Date: {sale_data['date']} {sale_data['time']}").grid(row=1, column=1, sticky=tk.W)
            ttk.Label(dialog, text=f"Customer: {sale_data.get('customer_name', 'N/A')}").grid(row=2, column=0, sticky=tk.W, padx=12)
            ttk.Label(dialog, text=f"Cashier: {sale_data.get('username', 'N/A')}").grid(row=2, column=1, sticky=tk.W)
            
            # Warning
            warning_frame = ttk.Frame(dialog)
            warning_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=12, pady=8)
            ttk.Label(warning_frame, text="⚠️ WARNING: This will cancel the entire sale and restore all inventory!", 
                     foreground="red", font=("Segoe UI", 9, "bold")).pack()
            
            # Void reason
            ttk.Label(dialog, text="Void Reason:").grid(row=4, column=0, sticky=tk.W, padx=12, pady=(8, 0))
            reason_var = tk.StringVar()
            ttk.Combobox(
                dialog,
                textvariable=reason_var,
                values=["Data Entry Error", "Customer Cancelled", "System Error", "Management Override", "Other"],
                width=40
            ).grid(row=4, column=1, sticky=tk.W, padx=12, pady=(8, 0))
            
            # Buttons
            button_frame = ttk.Frame(dialog)
            button_frame.grid(row=5, column=0, columnspan=2, pady=12)
            
            def do_void():
                try:
                    reason = reason_var.get() or "Management Override"
                    
                    if not messagebox.askyesno("Confirm Void", 
                        f"Are you sure you want to void this sale?\n\nAmount: {currency} {sale_data['total']:.2f}\nReason: {reason}\n\nThis action cannot be undone!"):
                        return
                    
                    # Void the sale
                    success = receipts.void_sale(sale_id, reason, current_user['user_id'])
                    
                    if success:
                        messagebox.showinfo("Sale Voided", f"Sale {receipt_num} has been voided successfully")
                        
                        # Log the void action
                        log_audit_action("VOID", sale_id, current_user.get('username', 'Unknown'), f"Reason: {reason}")
                        
                        dialog.destroy()
                        self._filter_orders()
                    else:
                        messagebox.showerror("Void Failed", "Failed to void the sale")
                        
                except Exception as e:
                    messagebox.showerror("Error", f"Void failed: {e}")
            
            ttk.Button(button_frame, text="Void Sale", command=do_void, style="danger.TButton").pack(side=tk.LEFT, padx=4)
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)
            
            # Center dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
            y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
            dialog.geometry(f"+{x}+{y}")
            dialog.deiconify()
            
            except Exception as e:
            messagebox.showerror("Error", f"Failed to open void dialog: {e}")
        
        def _clear_search(self):
            """Clear the search field and refresh the order list."""
            self.search_term.set("")
            self.refresh()
        
        def _pick_start_date(self) -> None:
            """Open calendar picker for start date."""
            try:
            current = datetime.strptime(self.start_date.get(), "%Y-%m-%d")
            except ValueError:
            current = datetime.now()
            
            # Create a proper parent window
            root = self.winfo_toplevel()
            top = tk.Toplevel(root)
            top.title("Select Start Date")
            set_window_icon(top)
            top.geometry("350x350")
            top.resizable(True, True)
            # Make it modal
            top.transient(root)
            top.grab_set()
            
            cal = tkcalendar.Calendar(
            top, 
            year=current.year, 
            month=current.month, 
            day=current.day,
            date_pattern="yyyy-mm-dd"
            )
            cal.pack(fill="both", expand=True, padx=10, pady=10)
            
            def on_select():
            selected = cal.get_date()
            self.start_date.set(selected)
            top.destroy()
            self.refresh()
            
            button_frame = ttk.Frame(top)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="OK", command=on_select).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=5)
        
        def _pick_end_date(self) -> None:
            """Open calendar picker for end date."""
            try:
            current = datetime.strptime(self.end_date.get(), "%Y-%m-%d")
            except ValueError:
            current = datetime.now()
            
            # Create a proper parent window
            root = self.winfo_toplevel()
            top = tk.Toplevel(root)
            top.title("Select End Date")
            set_window_icon(top)
            top.geometry("350x350")
            top.resizable(True, True)
            # Make it modal
            top.transient(root)
            top.grab_set()
            
            cal = tkcalendar.Calendar(
            top, 
            year=current.year, 
            month=current.month, 
            day=current.day,
            date_pattern="yyyy-mm-dd"
            )
            cal.pack(fill="both", expand=True, padx=10, pady=10)
            
            def on_select():
            selected = cal.get_date()
            self.end_date.set(selected)
            top.destroy()
            self.refresh()
            
            button_frame = ttk.Frame(top)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="OK", command=on_select).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=5)
        
        def _generate_report(self) -> None:
            """Generate a report of the current filtered order history."""
            try:
            # Get current filter values
            start = self.start_date.get().strip() or None
            end = self.end_date.get().strip() or None
            search = self.search_term.get().strip() or None
            payment_filter = self.payment_method_var.get() if hasattr(self, 'payment_method_var') else 'Any'
            status_filter = self.refund_status_var.get() if hasattr(self, 'refund_status_var') else 'Any'
            user_filter = self.user_var.get() if hasattr(self, 'user_var') else 'Any'
            customer_filter = self.customer_var.get() if hasattr(self, 'customer_var') else 'Any'
            
            # Get filtered sales
            sales = receipts.list_sales_with_search(start, end, search, limit=10000)  # Higher limit for reports
            
            # Apply filters
            filtered_sales = []
            for sale in sales:
                sid = sale["sale_id"]
                
                # Determine status
                if sale.get("voided"):
                    sale_status = "Voided"
                elif refunds.is_sale_fully_refunded(sid):
                    sale_status = "Fully Refunded"
                elif refunds.get_refunded_quantities_for_sale(sid):
                    sale_status = "Partially Refunded"
                else:
                    sale_status = "Active"
                
                # Apply filters
                if payment_filter and payment_filter != 'Any' and sale.get('payment_method') != payment_filter:
                    continue
                if status_filter and status_filter != 'Any' and sale_status != status_filter:
                    continue
                if user_filter and user_filter != 'Any' and sale.get('username') != user_filter:
                    continue
                if customer_filter and customer_filter != 'Any' and sale.get('customer_name') != customer_filter:
                    continue
                
                filtered_sales.append((sale, sale_status))
            
            if not filtered_sales:
                messagebox.showinfo("No Data", "No orders found matching the current filters.")
                return
            
            # Generate CSV content
            currency = get_currency_code()
            import io
            output = io.StringIO()
            import csv
            
            writer = csv.writer(output)
            writer.writerow([
                "Receipt #", "Date", "Time", "Customer", "Cashier", 
                "Total", "Payment Method", "Status"
            ])
            
            total_amount = 0.0
            for sale, status in filtered_sales:
                receipt_num = sale.get("receipt_number", f"#{sale['sale_id']}")
                writer.writerow([
                    receipt_num,
                    sale["date"],
                    sale["time"],
                    sale.get("customer_name", ""),
                    sale.get("username", ""),
                    f"{currency} {sale['total']:.2f}",
                    sale.get("payment_method", "Cash"),
                    status
                ])
                total_amount += sale["total"]
            
            # Add summary
            writer.writerow([])
            writer.writerow(["Summary"])
            writer.writerow([f"Total Orders: {len(filtered_sales)}"])
            writer.writerow([f"Total Amount: {currency} {total_amount:.2f}"])
            
            csv_content = output.getvalue()
            
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save Order History Report"
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)
                messagebox.showinfo("Report Generated", f"Report saved to {filename}")
            
        except Exception as e:
        messagebox.showerror("Error", f"Failed to generate report: {e}")
