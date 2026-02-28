"""Stock Receiving UI for managing inventory purchases with lot tracking.

This module provides a user interface for:
- Receiving new stock with cost price input
- Viewing stock lots for items
- Managing inventory costing method settings
- Stock movement history
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import os

try:
    from tkcalendar import DateEntry as _DateEntry
    HAS_TKCALENDAR = True

    class TopDateEntry(_DateEntry):
        """DateEntry subclass that opens the calendar above the widget."""
        def drop_down(self):
            if self._calendar.winfo_ismapped():
                self._top_cal.withdraw()
            else:
                self._validate_date()
                date = self.parse_date(self.get())
                x = self.winfo_rootx()
                self.update_idletasks()
                cal_height = self._top_cal.winfo_reqheight() or 200
                y = self.winfo_rooty() - cal_height
                if y < 0:
                    y = self.winfo_rooty() + self.winfo_height()
                if self.winfo_toplevel().attributes('-topmost'):
                    self._top_cal.attributes('-topmost', True)
                else:
                    self._top_cal.attributes('-topmost', False)
                self._top_cal.geometry('+%i+%i' % (x, y))
                self._top_cal.deiconify()
                self._calendar.focus_set()
                self._calendar.selection_set(date)
except ImportError:
    HAS_TKCALENDAR = False

from database.init_db import get_connection
from modules import items as items_module
from modules.inventory_costing import (
    CostingMethod, get_costing_method, set_costing_method,
    get_stock_lots, get_inventory_valuation, get_stock_movements_history,
    get_lot_expiry_report, MovementType, record_stock_adjustment
)
from modules.stock_receiving import (
    receive_stock, get_recent_purchases, get_suppliers,
    get_item_stock_summary, calculate_reorder_suggestions,
    check_and_migrate_legacy_inventory
)
from utils.security import get_currency_code
from utils import set_window_icon
from utils.date_utils import format_date, get_date_format, parse_date_flexible

logger = logging.getLogger(__name__)


# Tab index constants for maintainability
class TabIndex:
    """Named constants for notebook tab indices."""
    RECEIVE = 0
    LOTS = 1
    PURCHASES = 2
    MOVEMENTS = 3
    ADJUSTMENTS = 4


class StockReceivingFrame(ttk.Frame):
    """Main frame for stock receiving operations."""
    
    def __init__(self, master: tk.Misc, user_id: Optional[int] = None, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.user_id = user_id
        self.currency = get_currency_code()
        self.selected_item_id = None
        self._item_list_visible = True  # Track item list visibility state
        self._build_ui()
        self._load_items()
        
        # Check and migrate legacy inventory on first load
        self.after(500, self._check_migration)
    
    def _check_migration(self):
        """Check if legacy inventory needs migration."""
        try:
            migrated = check_and_migrate_legacy_inventory(self.user_id)
            if migrated > 0:
                messagebox.showinfo(
                    "Inventory Migration",
                    f"Successfully migrated {migrated} items to lot-based tracking.\n\n"
                    "Your existing inventory has been converted to stock lots for "
                    "better cost tracking."
                )
                self._refresh_all()
        except Exception as e:
            logger.error(f"Migration check failed: {e}")
    
    def _build_ui(self):
        """Build the main UI layout."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 12))
        
        ttk.Label(
            header_frame, 
            text="📦 Stock Receiving", 
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)
        
        # Costing method selector
        method_frame = ttk.Frame(header_frame)
        method_frame.pack(side=tk.RIGHT)
        
        ttk.Label(method_frame, text="Costing Method:").pack(side=tk.LEFT, padx=(0, 5))
        self.costing_method_var = tk.StringVar()
        method_combo = ttk.Combobox(
            method_frame, 
            textvariable=self.costing_method_var,
            values=["FIFO", "LIFO", "WAC"],
            state="readonly",
            width=10
        )
        method_combo.pack(side=tk.LEFT)
        method_combo.bind("<<ComboboxSelected>>", self._on_costing_method_change)
        
        # Load current method
        current_method = get_costing_method()
        self.costing_method_var.set(current_method.value)
        
        # Main content - PanedWindow for resizable panels
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=8)
        
        # Left panel - Item selection
        self.left_frame = ttk.LabelFrame(self.paned, text="Select Item", padding=8)
        self.paned.add(self.left_frame, weight=1)
        
        # Search
        search_frame = ttk.Frame(self.left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_items())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        
        # Clear search button
        ttk.Button(search_frame, text="✕", width=3, 
                  command=lambda: self.search_var.set("")).pack(side=tk.LEFT)
        
        # Quick filters
        quick_filter_frame = ttk.Frame(self.left_frame)
        quick_filter_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(quick_filter_frame, text="Quick:", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_filter_frame, text="Low Stock", width=10,
                  command=self._filter_low_stock).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_filter_frame, text="All Items", width=10,
                  command=lambda: self.search_var.set("")).pack(side=tk.LEFT, padx=2)
        
        # Container frame for tree and scrollbars
        tree_container = ttk.Frame(self.left_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Items list
        columns = ("item_id", "name", "category", "quantity", "cost_price")
        self.items_tree = ttk.Treeview(
            tree_container, 
            columns=columns, 
            show="headings",
            selectmode="browse",
            height=20
        )
        
        self.items_tree.heading("item_id", text="ID")
        self.items_tree.heading("name", text="Item Name")
        self.items_tree.heading("category", text="Category")
        self.items_tree.heading("quantity", text="Stock")
        self.items_tree.heading("cost_price", text="Last Cost")
        
        # Autofit columns to available space
        self.items_tree.column("item_id", stretch=True)
        self.items_tree.column("name", stretch=True)
        self.items_tree.column("category", stretch=True)
        self.items_tree.column("quantity", stretch=True)
        self.items_tree.column("cost_price", stretch=True)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.items_tree.xview)
        self.items_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Grid layout for tree and scrollbars
        self.items_tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        h_scrollbar.grid(row=1, column=0, sticky=tk.EW)
        
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        self.items_tree.bind("<<TreeviewSelect>>", self._on_item_select)
        
        # Right panel - Notebook for different views
        self.right_frame = ttk.Frame(self.paned)
        self.paned.add(self.right_frame, weight=1)
        
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Receive Stock
        self._build_receive_tab()
        
        # Tab 2: Stock Lots
        self._build_lots_tab()
        
        # Tab 3: Recent Purchases
        self._build_purchases_tab()
        
        # Tab 4: Stock Movements
        self._build_movements_tab()
        
        # Tab 5: Stock Adjustments
        self._build_adjustments_tab()
        
        # Bind tab change event to show/hide item list as needed
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        # Ensure initial layout is correct after construction
        self.after(100, lambda: self._on_tab_changed(None))
        
        # Configure grid weights
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
    
    def _build_receive_tab(self):
        """Build the Receive Stock tab."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="📥 Receive Stock")
        
        # Item info display
        info_frame = ttk.LabelFrame(frame, text="Selected Item", padding=8)
        info_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.item_name_var = tk.StringVar(value="No item selected")
        self.item_stock_var = tk.StringVar(value="Current Stock: -")
        self.item_avg_cost_var = tk.StringVar(value="Avg Cost: -")
        
        ttk.Label(
            info_frame, 
            textvariable=self.item_name_var,
            font=("Segoe UI", 11, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Label(info_frame, textvariable=self.item_stock_var).grid(
            row=1, column=0, sticky=tk.W, pady=2
        )
        ttk.Label(info_frame, textvariable=self.item_avg_cost_var).grid(
            row=1, column=1, sticky=tk.W, pady=2, padx=(20, 0)
        )
        
        # ----- Top control buttons (always visible, directly under item info) -----
        top_btn_frame = ttk.Frame(frame)
        top_btn_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.receive_btn = ttk.Button(
            top_btn_frame,
            text="📥 Receive Stock (Ctrl+S)",
            command=self._receive_stock,
            style="Accent.TButton",
            state="disabled"  # disabled until an item is selected
        )
        self.receive_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Add helper text when button is disabled
        self.receive_help_var = tk.StringVar(value="← Select an item first")
        self.receive_help_label = ttk.Label(
            top_btn_frame,
            textvariable=self.receive_help_var,
            foreground="#666666",
            font=("Segoe UI", 9, "italic")
        )
        self.receive_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.clear_form_btn = ttk.Button(
            top_btn_frame,
            text="🔄 Clear Form",
            command=self._clear_form
        )
        self.clear_form_btn.pack(side=tk.LEFT)
        
        # "Receive More" quick action button (hidden until after first receipt)
        self.receive_more_btn = ttk.Button(
            top_btn_frame,
            text="➕ Receive More of Same",
            command=self._receive_more_same,
            style="Accent.TButton"
        )
        # Initially hidden - will show after successful receipt
        self._last_received_item_id = None
        
        # End top control buttons
        
        # Receive form
        form_frame = ttk.LabelFrame(frame, text="New Stock Details", padding=12)
        form_frame.pack(fill=tk.X, pady=(0, 12))
        
        row = 0
        
        # Quantity
        ttk.Label(form_frame, text="Quantity *:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.quantity_var = tk.StringVar()
        quantity_entry = ttk.Entry(form_frame, textvariable=self.quantity_var, width=15)
        quantity_entry.grid(row=row, column=1, sticky=tk.W, pady=4)
        
        # Quantity validation label
        self.quantity_error_var = tk.StringVar()
        self.quantity_error_label = ttk.Label(
            form_frame, 
            textvariable=self.quantity_error_var, 
            foreground="red", 
            font=("Segoe UI", 8)
        )
        self.quantity_error_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0))
        self.quantity_var.trace_add("write", lambda *a: self._validate_quantity())
        row += 1
        
        # Cost Price
        ttk.Label(form_frame, text=f"Cost Price ({self.currency}) *:").grid(
            row=row, column=0, sticky=tk.W, pady=4
        )
        self.cost_price_var = tk.StringVar()
        cost_entry = ttk.Entry(form_frame, textvariable=self.cost_price_var, width=15)
        cost_entry.grid(row=row, column=1, sticky=tk.W, pady=4)
        
        # Cost price validation label  
        self.cost_error_var = tk.StringVar()
        self.cost_error_label = ttk.Label(
            form_frame, 
            textvariable=self.cost_error_var, 
            foreground="red", 
            font=("Segoe UI", 8)
        )
        self.cost_error_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0))
        self.cost_price_var.trace_add("write", lambda *a: self._validate_cost_price())
        row += 1
        
        # Total cost display (new row for better visibility)
        ttk.Label(form_frame, text="Total Cost:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.total_cost_var = tk.StringVar(value="--")
        ttk.Label(form_frame, textvariable=self.total_cost_var, font=("Segoe UI", 10, "bold"), 
                 foreground="#0066cc").grid(row=row, column=1, sticky=tk.W, pady=4)
        row += 1
        
        # Supplier
        ttk.Label(form_frame, text="Supplier:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.supplier_var = tk.StringVar()
        supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var, width=25)
        supplier_combo.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=4)
        self._load_suppliers(supplier_combo)
        row += 1
        
        # Reference Number
        ttk.Label(form_frame, text="Reference/Invoice #:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.reference_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.reference_var, width=25).grid(
            row=row, column=1, columnspan=2, sticky=tk.W, pady=4
        )
        row += 1
        
        # Purchase Date
        ttk.Label(form_frame, text="Purchase Date:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.purchase_date_var = tk.StringVar(value=format_date(datetime.now()))
        if HAS_TKCALENDAR:
            self.purchase_date_entry = TopDateEntry(
                form_frame, 
                textvariable=self.purchase_date_var,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd'
            )
            self.purchase_date_entry.grid(row=row, column=1, sticky=tk.W, pady=4)
        else:
            ttk.Entry(form_frame, textvariable=self.purchase_date_var, width=15).grid(
                row=row, column=1, sticky=tk.W, pady=4
            )
        date_fmt_hint = get_date_format().replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD')
        ttk.Label(form_frame, text=f"({date_fmt_hint})", font=("Segoe UI", 8)).grid(
            row=row, column=1, sticky=tk.W, padx=(140, 0), pady=4
        )
        row += 1
        
        # Initialize notes variables
        self.notes_content = ""
        self.notes_indicator_var = tk.StringVar(value="")
        
        # Expiry Date
        ttk.Label(form_frame, text="Expiry Date:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.expiry_date_var = tk.StringVar()
        if HAS_TKCALENDAR:
            self.expiry_date_entry = TopDateEntry(
                form_frame, 
                textvariable=self.expiry_date_var,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd'
            )
            self.expiry_date_entry.grid(row=row, column=1, sticky=tk.W, pady=4)
        else:
            ttk.Entry(form_frame, textvariable=self.expiry_date_var, width=15).grid(
                row=row, column=1, sticky=tk.W, pady=4
            )
        ttk.Label(form_frame, text=f"(Optional, {date_fmt_hint})", font=("Segoe UI", 8)).grid(
            row=row, column=1, sticky=tk.W, padx=(140, 0), pady=4
        )
        
        # Add Notes button on same row as expiry date
        ttk.Button(
            form_frame, 
            text="📝 Add Notes", 
            command=self._open_notes_dialog,
            width=15
        ).grid(row=row, column=2, sticky=tk.W, pady=4)
        
        # Notes indicator next to the button
        ttk.Label(
            form_frame, 
            textvariable=self.notes_indicator_var,
            foreground="#0066cc",
            font=("Segoe UI", 8)
        ).grid(row=row, column=2, sticky=tk.W, padx=(110, 0), pady=4)
        
        row += 1
        
        # Ensure form columns can expand properly
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(2, weight=0)
    
    def _build_lots_tab(self):
        """Build the Stock Lots tab."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="📦 Stock Lots")
        
        # Lots treeview
        columns = ("lot_id", "date", "received", "remaining", "cost", "supplier", "expiry")
        self.lots_tree = ttk.Treeview(
            frame, 
            columns=columns, 
            show="headings",
            height=12
        )
        
        self.lots_tree.heading("lot_id", text="Lot ID")
        self.lots_tree.heading("date", text="Purchase Date")
        self.lots_tree.heading("received", text="Received")
        self.lots_tree.heading("remaining", text="Remaining")
        self.lots_tree.heading("cost", text=f"Cost ({self.currency})")
        self.lots_tree.heading("supplier", text="Supplier")
        self.lots_tree.heading("expiry", text="Expiry")
        
        self.lots_tree.column("lot_id", width=60, minwidth=50)
        self.lots_tree.column("date", width=100, minwidth=80)
        self.lots_tree.column("received", width=70, minwidth=60)
        self.lots_tree.column("remaining", width=70, minwidth=60)
        self.lots_tree.column("cost", width=80, minwidth=60)
        self.lots_tree.column("supplier", width=120, minwidth=80)
        self.lots_tree.column("expiry", width=90, minwidth=70)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.lots_tree.yview)
        self.lots_tree.configure(yscrollcommand=scrollbar.set)
        
        self.lots_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary at bottom
        summary_frame = ttk.Frame(frame)
        summary_frame.pack(fill=tk.X, pady=(8, 0))
        
        self.lots_summary_var = tk.StringVar(value="Select an item to view stock lots")
        ttk.Label(summary_frame, textvariable=self.lots_summary_var).pack(side=tk.LEFT)
    
    def _build_purchases_tab(self):
        """Build the Recent Purchases tab."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="📋 Recent Purchases")
        
        # Filter options
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(filter_frame, text="Show last:").pack(side=tk.LEFT)
        self.days_var = tk.StringVar(value="30")
        days_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.days_var,
            values=["7", "14", "30", "60", "90"],
            state="readonly",
            width=5
        )
        days_combo.pack(side=tk.LEFT, padx=4)
        ttk.Label(filter_frame, text="days").pack(side=tk.LEFT)
        
        ttk.Button(
            filter_frame, 
            text="Refresh",
            command=self._load_recent_purchases
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Purchases treeview
        columns = ("date", "item", "qty", "cost", "total", "supplier", "reference")
        self.purchases_tree = ttk.Treeview(
            frame, 
            columns=columns, 
            show="headings",
            height=12
        )
        
        self.purchases_tree.heading("date", text="Date")
        self.purchases_tree.heading("item", text="Item")
        self.purchases_tree.heading("qty", text="Qty")
        self.purchases_tree.heading("cost", text="Unit Cost")
        self.purchases_tree.heading("total", text="Total")
        self.purchases_tree.heading("supplier", text="Supplier")
        self.purchases_tree.heading("reference", text="Reference")
        
        self.purchases_tree.column("date", width=90, minwidth=80)
        self.purchases_tree.column("item", width=150, minwidth=100)
        self.purchases_tree.column("qty", width=50, minwidth=40)
        self.purchases_tree.column("cost", width=80, minwidth=60)
        self.purchases_tree.column("total", width=80, minwidth=60)
        self.purchases_tree.column("supplier", width=100, minwidth=80)
        self.purchases_tree.column("reference", width=100, minwidth=80)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.purchases_tree.yview)
        self.purchases_tree.configure(yscrollcommand=scrollbar.set)
        
        self.purchases_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load initial data
        self.after(100, self._load_recent_purchases)
    
    def _build_movements_tab(self):
        """Build the Stock Movements tab."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="📊 Movements")
        
        # Filter
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT)
        self.movement_type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.movement_type_var,
            values=["All", "purchase", "sale", "return", "adjustment", "waste"],
            state="readonly",
            width=12
        )
        type_combo.pack(side=tk.LEFT, padx=4)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._load_movements())
        
        ttk.Button(
            filter_frame,
            text="Refresh",
            command=self._load_movements
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Movements treeview
        columns = ("date", "type", "item", "qty", "cost", "lot", "notes")
        self.movements_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=12
        )
        
        self.movements_tree.heading("date", text="Date/Time")
        self.movements_tree.heading("type", text="Type")
        self.movements_tree.heading("item", text="Item")
        self.movements_tree.heading("qty", text="Qty")
        self.movements_tree.heading("cost", text="Unit Cost")
        self.movements_tree.heading("lot", text="Lot")
        self.movements_tree.heading("notes", text="Notes")
        
        self.movements_tree.column("date", width=130, minwidth=100)
        self.movements_tree.column("type", width=70, minwidth=60)
        self.movements_tree.column("item", width=140, minwidth=100)
        self.movements_tree.column("qty", width=50, minwidth=40)
        self.movements_tree.column("cost", width=70, minwidth=50)
        self.movements_tree.column("lot", width=50, minwidth=40)
        self.movements_tree.column("notes", width=150, minwidth=100)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.movements_tree.yview)
        self.movements_tree.configure(yscrollcommand=scrollbar.set)
        
        self.movements_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load initial data
        self.after(200, self._load_movements)
    
    def _build_adjustments_tab(self):
        """Build the Stock Adjustments tab for recording spoilage, theft, damage, etc."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="⚙️ Adjustments")
        
        # Adjustment reasons configuration
        self.adjustment_reasons = {
            "Spoiled": {"icon": "🔴", "color": "#fd7e14", "desc": "Mold, rot, spoilage"},
            "Damaged": {"icon": "💔", "color": "#dc3545", "desc": "Physical damage, breakage"},
            "Expired": {"icon": "⏰", "color": "#6c757d", "desc": "Past expiration date"},
            "Theft": {"icon": "🚨", "color": "#dc3545", "desc": "Missing/stolen items"},
            "Quality Issue": {"icon": "⚠️", "color": "#fd7e14", "desc": "Quality problems detected"},
            "Waste": {"icon": "♻️", "color": "#ffc107", "desc": "General waste/disposal"},
            "Correction": {"icon": "✏️", "color": "#0dcaf0", "desc": "Inventory correction"},
            "Breakage": {"icon": "💥", "color": "#dc3545", "desc": "Broken during handling"},
        }
        
        # PanedWindow for resizable split between form and history
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # LEFT PANEL - ADJUSTMENT FORM
        left_frame = ttk.LabelFrame(paned, text="Record Adjustment", padding=12)
        paned.add(left_frame, weight=1)
        
        # RIGHT PANEL - ADJUSTMENT HISTORY
        right_frame = ttk.LabelFrame(paned, text="Adjustment History", padding=12)
        paned.add(right_frame, weight=2)
        
        # ═══════════════════════════════════════════════════════════════════
        # LEFT PANEL - ADJUSTMENT FORM
        # ═══════════════════════════════════════════════════════════════════
        
        row = 0
        
        # Item selection (if not already selected)
        ttk.Label(left_frame, text="Item *:", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky=tk.W, pady=8
        )
        self.adj_item_var = tk.StringVar()
        item_combo = ttk.Combobox(left_frame, textvariable=self.adj_item_var, width=30, state="readonly")
        item_combo.grid(row=row, column=1, sticky=tk.EW, pady=8)
        item_combo.bind("<<ComboboxSelected>>", self._update_adj_lots)
        self.adj_item_combo = item_combo
        self._selected_adj_item_id = None
        row += 1
        
        # Reason selection
        ttk.Label(left_frame, text="Reason *:", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky=tk.W, pady=8
        )
        self.adj_reason_var = tk.StringVar()
        reason_combo = ttk.Combobox(
            left_frame,
            textvariable=self.adj_reason_var,
            values=list(self.adjustment_reasons.keys()),
            state="readonly",
            width=30
        )
        reason_combo.grid(row=row, column=1, sticky=tk.EW, pady=8)
        self.adj_reason_combo = reason_combo
        
        # Reason description
        self.adj_reason_desc_var = tk.StringVar()
        ttk.Label(left_frame, textvariable=self.adj_reason_desc_var, font=("Segoe UI", 8, "italic")).grid(
            row=row, column=1, sticky=tk.W, pady=(0, 8)
        )
        reason_combo.bind("<<ComboboxSelected>>", self._on_adj_reason_changed)
        row += 1
        
        # Quantity to remove
        ttk.Label(left_frame, text="Quantity to Remove *:", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky=tk.W, pady=8
        )
        self.adj_quantity_var = tk.StringVar(value="1")
        quantity_entry = ttk.Entry(left_frame, textvariable=self.adj_quantity_var, width=15)
        quantity_entry.grid(row=row, column=1, sticky=tk.W, pady=8)
        self.adj_quantity_entry = quantity_entry
        
        # Stock available indicator
        self.adj_avail_var = tk.StringVar(value="Available: -")
        ttk.Label(left_frame, textvariable=self.adj_avail_var, font=("Segoe UI", 9, "bold")).grid(
            row=row, column=1, sticky=tk.E, pady=8
        )
        row += 1
        
        # Specific lot selection (optional)
        ttk.Label(left_frame, text="Specific Lot (Optional):", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky=tk.W, pady=8
        )
        self.adj_lot_var = tk.StringVar()
        lot_combo = ttk.Combobox(left_frame, textvariable=self.adj_lot_var, width=30, state="readonly")
        lot_combo.grid(row=row, column=1, sticky=tk.EW, pady=8)
        self.adj_lot_combo = lot_combo
        row += 1
        
        # Expiration date (for expired items)
        ttk.Label(left_frame, text="Expiry Date (if expired):", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky=tk.W, pady=8
        )
        self.adj_expiry_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.adj_expiry_var, width=15).grid(
            row=row, column=1, sticky=tk.W, pady=8
        )
        ttk.Label(left_frame, text="(optional)", font=("Segoe UI", 8)).grid(
            row=row, column=1, sticky=tk.E, pady=8
        )
        row += 1
        
        # Notes
        ttk.Label(left_frame, text="Notes/Details:", font=("Segoe UI", 10)).grid(
            row=row, column=0, sticky=tk.NW, pady=8
        )
        self.adj_notes_text = tk.Text(left_frame, height=4, width=40)
        self.adj_notes_text.grid(row=row, column=1, sticky=tk.EW, pady=8)
        row += 1
        
        # Buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=12)
        
        ttk.Button(
            btn_frame,
            text="✅ Record Adjustment (Ctrl+S)",
            command=self._record_adjustment,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            btn_frame,
            text="🔄 Clear",
            command=self._clear_adjustment_form
        ).pack(side=tk.LEFT)
        
        # ═══════════════════════════════════════════════════════════════════
        # RIGHT PANEL - ADJUSTMENT HISTORY
        # ═══════════════════════════════════════════════════════════════════
        
        # Filter for history
        filter_frame = ttk.Frame(right_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 4))
        self.adj_filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.adj_filter_var,
            values=["All"] + list(self.adjustment_reasons.keys()),
            state="readonly",
            width=15
        )
        filter_combo.pack(side=tk.LEFT, padx=(0, 8))
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._load_adjustment_history())
        
        ttk.Button(
            filter_frame,
            text="Refresh",
            command=self._load_adjustment_history
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        # Export button
        ttk.Button(
            filter_frame,
            text="Export History",
            command=self._export_adjustments
        ).pack(side=tk.LEFT)
        
        # Container for tree and scrollbars
        tree_container = ttk.Frame(right_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # History tree with both scrollbars
        columns = ("date", "reason", "item", "qty", "notes")
        self.adjustments_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            height=20
        )
        
        self.adjustments_tree.heading("date", text="Date/Time")
        self.adjustments_tree.heading("reason", text="Reason")
        self.adjustments_tree.heading("item", text="Item Name")
        self.adjustments_tree.heading("qty", text="Qty")
        self.adjustments_tree.heading("notes", text="Details/Notes")
        
        # Better column widths for proper display
        self.adjustments_tree.column("date", width=140, minwidth=120, stretch=True)
        self.adjustments_tree.column("reason", width=100, minwidth=90, stretch=True)
        self.adjustments_tree.column("item", width=140, minwidth=120, stretch=True)
        self.adjustments_tree.column("qty", width=60, minwidth=50, stretch=False)
        self.adjustments_tree.column("notes", width=220, minwidth=150, stretch=True)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.adjustments_tree.yview)
        self.adjustments_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.adjustments_tree.xview)
        self.adjustments_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Grid layout for tree and scrollbars
        self.adjustments_tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        h_scrollbar.grid(row=1, column=0, sticky=tk.EW)
        
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        # Configure grid weights
        left_frame.columnconfigure(1, weight=1)
        
        # Load initial data
        self.after(100, self._refresh_adjustment_ui)
    
    def _on_adj_reason_changed(self, event=None):
        """Update reason description when reason changes."""
        reason = self.adj_reason_var.get()
        if reason in self.adjustment_reasons:
            desc = self.adjustment_reasons[reason]["desc"]
            self.adj_reason_desc_var.set(f"ℹ️  {desc}")
    
    def _refresh_adjustment_ui(self):
        """Refresh adjustment UI controls."""
        # Load items
        try:
            all_items = items_module.list_items()
            item_list = [(f"{i['name']} (Stock: {i.get('quantity', 0)})", i['item_id']) for i in all_items]
            self.adj_item_combo["values"] = [name for name, _ in item_list]
            self._item_lookup = {name: item_id for name, item_id in item_list}
        except Exception as e:
            logger.error(f"Failed to load items: {e}")
        
        # Load adjustment history
        self._load_adjustment_history()
    
    def _update_adj_lots(self, event=None):
        """Update lot dropdown when item is selected."""
        item_name = self.adj_item_var.get()
        if item_name and hasattr(self, '_item_lookup'):
            item_id = self._item_lookup.get(item_name)
            if item_id:
                self._selected_adj_item_id = item_id
                
                # Update available stock
                try:
                    item = items_module.get_item(item_id)
                    if item:
                        qty = item.get("quantity", 0)
                        self.adj_avail_var.set(f"Available: {qty}")
                except Exception:
                    pass
                
                # Load lots for this item
                try:
                    lots = get_stock_lots(item_id)  # Already filters quantity_remaining > 0
                    lot_labels = [
                        f"Lot {l.lot_id}: {l.quantity_remaining} units (Cost: {self.currency} {l.cost_price:.2f})"
                        for l in lots
                    ]
                    self.adj_lot_combo["values"] = lot_labels
                    self._lot_lookup = {label: l.lot_id for label, l in zip(lot_labels, lots)}
                except Exception as e:
                    logger.error(f"Failed to update adjustment lots: {e}")
    
    def _record_adjustment(self):
        """Record a stock adjustment."""
        # Validation
        item_name = self.adj_item_var.get()
        reason = self.adj_reason_var.get()
        qty_str = self.adj_quantity_var.get()
        
        if not item_name:
            messagebox.showerror("Error", "Please select an item")
            return
        
        if not reason:
            messagebox.showerror("Error", "Please select a reason")
            return
        
        if not qty_str or not qty_str.isdigit() or int(qty_str) <= 0:
            messagebox.showerror("Error", "Please enter a valid quantity")
            return
        
        quantity = int(qty_str)
        item_id = self._item_lookup.get(item_name)
        
        # Check available stock
        try:
            item = items_module.get_item(item_id)
            if not item or item.get("quantity", 0) < quantity:
                messagebox.showerror(
                    "Insufficient Stock",
                    f"Not enough stock. Available: {item.get('quantity', 0)}"
                )
                return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check stock: {e}")
            return
        
        # Build notes
        notes_text = self.adj_notes_text.get("1.0", tk.END).strip()
        expiry_date = self.adj_expiry_var.get().strip()
        
        # Build full reason with details
        full_reason = f"{reason}"
        if expiry_date:
            full_reason += f" (expired: {expiry_date})"
        if notes_text:
            full_reason += f" - {notes_text}"
        
        # Get lot if specified
        lot_id = None
        lot_label = self.adj_lot_var.get()
        if lot_label and hasattr(self, '_lot_lookup'):
            lot_id = self._lot_lookup.get(lot_label)
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Adjustment",
            f"Remove {quantity} units of '{item_name}'\n"
            f"Reason: {reason}\n\n"
            f"This will reduce inventory?"
        ):
            return
        
        # Record adjustment
        try:
            movement = record_stock_adjustment(
                item_id=item_id,
                quantity_change=-quantity,  # Negative for removal
                reason=full_reason,
                user_id=self.user_id,
                lot_id=lot_id,
                unit_cost=item.get("cost_price", 0)
            )
            
            messagebox.showinfo(
                "Success",
                f"Adjustment recorded successfully!\n\n"
                f"Item: {item_name}\n"
                f"Quantity Removed: {quantity}\n"
                f"Reason: {reason}"
            )
            
            # Refresh and clear form
            self._clear_adjustment_form()
            self._refresh_adjustment_ui()
            self._refresh_all()
            
        except Exception as e:
            logger.error(f"Failed to record adjustment: {e}")
            messagebox.showerror("Error", f"Failed to record adjustment: {e}")
    
    def _clear_adjustment_form(self):
        """Clear adjustment form."""
        self.adj_item_var.set("")
        self.adj_reason_var.set("")
        self.adj_quantity_var.set("1")
        self.adj_lot_var.set("")
        self.adj_expiry_var.set("")
        self.adj_notes_text.delete("1.0", tk.END)
        self.adj_avail_var.set("Available: -")
        self.adj_reason_desc_var.set("")
    
    def _load_adjustment_history(self):
        """Load adjustment history from movements table."""
        self.adjustments_tree.delete(*self.adjustments_tree.get_children())
        
        try:
            # Fetch adjustment and waste movements only
            adj_movements = get_stock_movements_history(
                movement_type=MovementType.ADJUSTMENT,
                limit=100
            )
            waste_movements = get_stock_movements_history(
                movement_type=MovementType.WASTE,
                limit=100
            )
            movements = sorted(
                adj_movements + waste_movements,
                key=lambda m: m.created_at or '',
                reverse=True
            )[:100]
            
            # Get item names
            item_names = {}
            with get_connection() as conn:
                conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                for row in conn.execute("SELECT item_id, name FROM items").fetchall():
                    item_names[row["item_id"]] = row["name"]
            
            filter_reason = self.adj_filter_var.get()
            
            for m in movements:
                item_name = item_names.get(m.item_id, f"Item {m.item_id}")
                notes = m.notes or ""
                
                # Extract reason from notes
                reason_text = notes.split(" -")[0] if notes else "Waste"
                
                # Filter by reason if specified
                if filter_reason != "All" and not reason_text.startswith(filter_reason):
                    continue
                
                # Color-code based on adjustment reason
                tags = ()
                if "Spoiled" in reason_text:
                    tags = ("spoiled",)
                elif "Expired" in reason_text:
                    tags = ("expired",)
                elif "Damaged" in reason_text or "Breakage" in reason_text:
                    tags = ("damaged",)
                elif "Theft" in reason_text:
                    tags = ("theft",)
                else:
                    tags = ("waste",)
                
                display_date = format_date(m.created_at) if m.created_at else "-"
                
                self.adjustments_tree.insert("", tk.END, values=(
                    display_date,
                    reason_text,
                    item_name,
                    abs(m.quantity),
                    notes.split(" - ", 1)[1] if " - " in notes else notes
                ), tags=tags)
            
            # Configure tags for color coding
            self.adjustments_tree.tag_configure("spoiled", background="#fff3cd", foreground="#856404")
            self.adjustments_tree.tag_configure("expired", background="#e2e3e5", foreground="#383d41")
            self.adjustments_tree.tag_configure("damaged", background="#f8d7da", foreground="#721c24")
            self.adjustments_tree.tag_configure("theft", background="#f5c6cb", foreground="#721c24")
            self.adjustments_tree.tag_configure("waste", background="#ffeaa7", foreground="#666")
            
        except Exception as e:
            logger.error(f"Failed to load adjustment history: {e}")
    
    def _export_adjustments(self):
        """Export adjustment history to CSV."""
        from tkinter import filedialog
        import csv
        
        try:
            adj_movements = get_stock_movements_history(
                movement_type=MovementType.ADJUSTMENT,
                limit=1000
            )
            waste_movements = get_stock_movements_history(
                movement_type=MovementType.WASTE,
                limit=1000
            )
            movements = sorted(
                adj_movements + waste_movements,
                key=lambda m: m.created_at or '',
                reverse=True
            )
            
            # Get item names
            item_names = {}
            with get_connection() as conn:
                conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                for row in conn.execute("SELECT item_id, name FROM items").fetchall():
                    item_names[row["item_id"]] = row["name"]
            
            # Prepare data
            data = []
            for m in movements:
                item_name = item_names.get(m.item_id, f"Item {m.item_id}")
                notes = m.notes or ""
                reason_text = notes.split(" -")[0] if notes else "Adjustment"
                
                data.append({
                    "date": format_date(m.created_at) if m.created_at else "-",
                    "reason": reason_text,
                    "item": item_name,
                    "quantity": abs(m.quantity),
                    "unit_cost": f"{m.unit_cost:.2f}" if m.unit_cost else "-",
                    "notes": notes.split(" - ", 1)[1] if " - " in notes else notes
                })
            
            if not data:
                messagebox.showinfo("Export", "No adjustment history to export")
                return
            
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Adjustment History",
                initialfile=f"adjustments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if not filename:
                return
            
            # Write CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["date", "reason", "item", "quantity", "unit_cost", "notes"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            messagebox.showinfo("Export Complete", f"Exported {len(data)} adjustments to:\n{filename}")
            
        except Exception as e:
            logger.error(f"Failed to export adjustments: {e}")
            messagebox.showerror("Export Error", f"Failed to export adjustments: {e}")
    
    def _load_items(self):
        """Load items into the tree."""
        self.items_tree.delete(*self.items_tree.get_children())
        
        try:
            all_items = items_module.list_items()
            for item in all_items:
                self.items_tree.insert("", tk.END, values=(
                    item["item_id"],
                    item["name"],
                    item.get("category", ""),
                    item.get("quantity", 0),
                    f"{self.currency} {item.get('cost_price', 0):.2f}"
                ))
        except Exception as e:
            logger.error(f"Failed to load items: {e}")
            messagebox.showerror("Error", f"Failed to load items: {e}")
    
    def _filter_items(self):
        """Filter items based on search."""
        search_text = self.search_var.get().lower()
        
        self.items_tree.delete(*self.items_tree.get_children())
        
        try:
            all_items = items_module.list_items()
            for item in all_items:
                if search_text in item["name"].lower() or search_text in (item.get("category", "") or "").lower():
                    self.items_tree.insert("", tk.END, values=(
                        item["item_id"],
                        item["name"],
                        item.get("category", ""),
                        item.get("quantity", 0),
                        f"{self.currency} {item.get('cost_price', 0):.2f}"
                    ))
        except Exception as e:
            logger.error(f"Failed to filter items: {e}")
    
    def _filter_low_stock(self):
        """Show only items with low stock."""
        self.items_tree.delete(*self.items_tree.get_children())
        
        try:
            all_items = items_module.list_items()
            for item in all_items:
                # Consider low stock if quantity < low_stock_threshold
                threshold = item.get("low_stock_threshold", 10)
                current_qty = item.get("quantity", 0)
                if current_qty < threshold:
                    self.items_tree.insert("", tk.END, values=(
                        item["item_id"],
                        item["name"],
                        item.get("category", ""),
                        current_qty,
                        f"{self.currency} {item.get('cost_price', 0):.2f}"
                    ), tags=("lowstock",))
            
            # Highlight low stock items
            self.items_tree.tag_configure("lowstock", background="#fff3cd", foreground="#856404")
            
            # Show count
            count = len(self.items_tree.get_children())
            if count == 0:
                messagebox.showinfo("Low Stock", "No items with low stock found!")
                # Reload all items
                self._load_items()
        except Exception as e:
            logger.error(f"Failed to filter low stock: {e}")
    
    def _on_item_select(self, event):
        """Handle item selection."""
        selection = self.items_tree.selection()
        if not selection:
            return
        
        values = self.items_tree.item(selection[0])["values"]
        self.selected_item_id = values[0]
        item_name = values[1]
        
        # Update item info display
        self.item_name_var.set(f"📦 {item_name}")
        
        # Enable receive button when an item is selected
        try:
            self.receive_btn.config(state="normal")
            self.receive_help_var.set("✓ Ready to receive stock")
        except Exception:
            pass
        
        # Get stock summary
        try:
            summary = get_item_stock_summary(self.selected_item_id)
            self.item_stock_var.set(f"Current Stock: {summary['total_quantity']}")
            self.item_avg_cost_var.set(f"Avg Cost: {self.currency} {summary['average_cost']:.2f}")
            
            # Pre-fill cost price with last purchase price if available
            if summary.get('lots') and len(summary['lots']) > 0:
                last_cost = summary['lots'][-1]['cost_price']
                self.cost_price_var.set(f"{last_cost:.2f}")
                logger.debug(f"Pre-filled cost price: {last_cost:.2f} from last purchase")
            else:
                # No previous purchases, leave empty for manual entry
                self.cost_price_var.set("")
            
            # Load lots for this item
            self._load_item_lots()
        except Exception as e:
            logger.error(f"Failed to get item summary: {e}")
            self.item_stock_var.set(f"Current Stock: {values[3]}")
            self.item_avg_cost_var.set(f"Avg Cost: {values[4]}")
            self.cost_price_var.set("")  # Clear on error
    
    def _load_item_lots(self):
        """Load stock lots for the selected item."""
        self.lots_tree.delete(*self.lots_tree.get_children())
        
        if not self.selected_item_id:
            self.lots_summary_var.set("Select an item to view stock lots")
            return
        
        try:
            lots = get_stock_lots(self.selected_item_id, include_empty=False)
            
            for lot in lots:
                # Highlight lots with low stock or near expiry
                tags = ()
                if lot.quantity_remaining <= 5:
                    tags = ("lowstock",)
                if lot.expiry_date:
                    try:
                        exp_date = parse_date_flexible(lot.expiry_date)
                        days_to_expiry = (exp_date - datetime.now()).days
                        if days_to_expiry < 30:
                            tags = ("expiring",)
                    except:
                        pass
                
                self.lots_tree.insert("", tk.END, values=(
                    lot.lot_id,
                    format_date(lot.purchase_date) if lot.purchase_date else "-",
                    lot.quantity_received,
                    lot.quantity_remaining,
                    f"{lot.cost_price:.2f}",
                    lot.supplier or "-",
                    format_date(lot.expiry_date) if lot.expiry_date else "-"
                ), tags=tags)
            
            # Configure tags
            self.lots_tree.tag_configure("lowstock", background="#fff3cd")
            self.lots_tree.tag_configure("expiring", background="#f8d7da")
            
            # Update summary
            summary = get_item_stock_summary(self.selected_item_id)
            self.lots_summary_var.set(
                f"Total: {summary['total_quantity']} units | "
                f"Lots: {summary['lot_count']} | "
                f"Value: {self.currency} {summary['total_quantity'] * summary['average_cost']:.2f}"
            )
        except Exception as e:
            logger.exception(f"Failed to load lots: {e}")
            self.lots_summary_var.set(f"Error loading lots: {e}")
    
    def _load_recent_purchases(self):
        """Load recent purchases."""
        self.purchases_tree.delete(*self.purchases_tree.get_children())
        
        try:
            days = int(self.days_var.get())
            purchases = get_recent_purchases(days=days)
            
            for p in purchases:
                self.purchases_tree.insert("", tk.END, values=(
                    format_date(p["purchase_date"]) if p["purchase_date"] else "-",
                    p["item_name"],
                    p["quantity_received"],
                    f"{p['cost_price']:.2f}",
                    f"{p['total_cost']:.2f}",
                    p.get("supplier") or "-",
                    p.get("reference_number") or "-"
                ))
        except Exception as e:
            logger.error(f"Failed to load purchases: {e}")
    
    def _load_movements(self):
        """Load stock movements."""
        self.movements_tree.delete(*self.movements_tree.get_children())
        
        try:
            type_filter = self.movement_type_var.get()
            movement_type = None
            if type_filter != "All":
                movement_type = MovementType(type_filter)
            
            # Get item ID filter if an item is selected
            item_filter = self.selected_item_id if self.selected_item_id else None
            
            movements = get_stock_movements_history(
                item_id=item_filter,
                movement_type=movement_type,
                limit=100
            )
            
            # Get item names
            item_names = {}
            with get_connection() as conn:
                conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                for row in conn.execute("SELECT item_id, name FROM items").fetchall():
                    item_names[row["item_id"]] = row["name"]
            
            for m in movements:
                item_name = item_names.get(m.item_id, f"Item {m.item_id}")
                
                # Color-code based on movement type
                tags = ()
                if m.movement_type == MovementType.SALE:
                    tags = ("sale",)
                elif m.movement_type == MovementType.PURCHASE:
                    tags = ("purchase",)
                elif m.movement_type == MovementType.WASTE:
                    tags = ("waste",)
                
                # Format datetime for display
                display_date = format_date(m.created_at) if m.created_at else "-"
                
                self.movements_tree.insert("", tk.END, values=(
                    display_date,
                    m.movement_type.value,
                    item_name,
                    m.quantity,
                    f"{m.unit_cost:.2f}" if m.unit_cost else "-",
                    m.lot_id or "-",
                    m.notes or "-"
                ), tags=tags)
            
            # Configure tags
            self.movements_tree.tag_configure("sale", foreground="#dc3545")
            self.movements_tree.tag_configure("purchase", foreground="#28a745")
            self.movements_tree.tag_configure("waste", foreground="#fd7e14")
            
        except Exception as e:
            logger.error(f"Failed to load movements: {e}")
    
    def _load_suppliers(self, combo):
        """Load suppliers into combo box."""
        try:
            suppliers = get_suppliers()
            combo["values"] = suppliers
        except Exception as e:
            logger.error(f"Failed to load suppliers: {e}")
    
    def _validate_quantity(self):
        """Validate quantity input in real-time."""
        value = self.quantity_var.get().strip()
        if not value:
            self.quantity_error_var.set("")
            self._update_total_cost()
            return
        
        try:
            qty = int(value)
            if qty <= 0:
                self.quantity_error_var.set("⚠ Must be > 0")
            elif qty > 100000:
                self.quantity_error_var.set("⚠ Unusually high")
            else:
                self.quantity_error_var.set("✓")
        except ValueError:
            self.quantity_error_var.set("⚠ Invalid number")
        
        self._update_total_cost()
    
    def _validate_cost_price(self):
        """Validate cost price input in real-time."""
        value = self.cost_price_var.get().strip()
        if not value:
            self.cost_error_var.set("")
            self._update_total_cost()
            return
        
        try:
            cost = float(value)
            if cost < 0:
                self.cost_error_var.set("⚠ Cannot be negative")
            elif cost == 0:
                self.cost_error_var.set("⚠ Warning: Zero cost")
            elif cost > 1000000:
                self.cost_error_var.set("⚠ Unusually high")
            else:
                self.cost_error_var.set("✓")
        except ValueError:
            self.cost_error_var.set("⚠ Invalid number")
        
        self._update_total_cost()
    
    def _update_total_cost(self):
        """Update total cost display."""
        try:
            qty = float(self.quantity_var.get() or 0)
            cost = float(self.cost_price_var.get() or 0)
            total = qty * cost
            if total > 0:
                self.total_cost_var.set(f"{self.currency} {total:,.2f}")
            else:
                self.total_cost_var.set("--")
        except ValueError:
            self.total_cost_var.set("--")
    
    def _receive_stock(self):
        """Receive stock for the selected item."""
        if not self.selected_item_id:
            messagebox.showwarning("Warning", "Please select an item first.")
            try:
                self.receive_btn.config(state="disabled")
            except Exception:
                pass
            return
        
        # Validate inputs
        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid quantity: {e}")
            return
        
        try:
            cost_price = float(self.cost_price_var.get())
            if cost_price < 0:
                raise ValueError("Cost price cannot be negative")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid cost price: {e}")
            return
        
        # Get optional fields
        supplier = self.supplier_var.get().strip() or None
        reference = self.reference_var.get().strip() or None
        purchase_date = self.purchase_date_var.get().strip() or None
        expiry_date = self.expiry_date_var.get().strip() or None
        notes = self.notes_content.strip() or None
        
        # Validate dates using flexible parser
        if purchase_date:
            try:
                parsed_purchase = parse_date_flexible(purchase_date)
                # Store in ISO format for database
                purchase_date = parsed_purchase.strftime("%Y-%m-%d")
            except ValueError:
                date_fmt_hint = get_date_format().replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD')
                messagebox.showerror("Error", f"Invalid purchase date format. Use {date_fmt_hint}")
                return
        
        if expiry_date:
            try:
                parsed_expiry = parse_date_flexible(expiry_date)
                # Store in ISO format for database
                expiry_date = parsed_expiry.strftime("%Y-%m-%d")
            except ValueError:
                date_fmt_hint = get_date_format().replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD')
                messagebox.showerror("Error", f"Invalid expiry date format. Use {date_fmt_hint}")
                return
        
        # Confirm
        item_name = self.item_name_var.get().replace("📦 ", "")
        if not messagebox.askyesno(
            "Confirm Stock Receipt",
            f"Receive {quantity} units of '{item_name}'\n"
            f"at {self.currency} {cost_price:.2f} each?\n\n"
            f"Total: {self.currency} {quantity * cost_price:.2f}"
        ):
            return
        
        # Receive the stock
        try:
            lot = receive_stock(
                item_id=self.selected_item_id,
                quantity=quantity,
                cost_price=cost_price,
                supplier=supplier,
                reference_number=reference,
                expiry_date=expiry_date,
                notes=notes,
                user_id=self.user_id,
                purchase_date=purchase_date
            )
            
            messagebox.showinfo(
                "Success",
                f"Stock received successfully!\n\n"
                f"Lot ID: {lot.lot_id}\n"
                f"Quantity: {quantity}\n"
                f"Cost: {self.currency} {cost_price:.2f}"
            )
            
            # Store last received item for quick "Receive More" action
            self._last_received_item_id = self.selected_item_id
            
            # Show "Receive More" button
            try:
                self.receive_more_btn.pack(side=tk.LEFT, padx=(8, 0))
            except Exception:
                pass
            
            # Refresh displays but keep the selected item
            saved_item_id = self.selected_item_id
            self._clear_form()
            self._refresh_all()
            
            # Reselect the same item for convenience
            if saved_item_id:
                for item in self.items_tree.get_children():
                    if self.items_tree.item(item)["values"][0] == saved_item_id:
                        self.items_tree.selection_set(item)
                        self.items_tree.see(item)
                        # Trigger selection event to update displays
                        self._on_item_select(None)
                        break
            
        except Exception as e:
            logger.error(f"Failed to receive stock: {e}")
            messagebox.showerror("Error", f"Failed to receive stock: {e}")
    
    def _clear_form(self):
        """Clear the receive form."""
        self.quantity_var.set("")
        # Don't clear cost_price - it may be pre-filled from last purchase
        # self.cost_price_var.set("")
        self.supplier_var.set("")
        self.reference_var.set("")
        
        self.purchase_date_var.set(format_date(datetime.now()))
        self.expiry_date_var.set("")
        
        # Clear notes content and indicator
        try:
            self.notes_content = ""
            self.notes_indicator_var.set("")
        except Exception:
            pass
        self.total_cost_var.set("Total: -")
    
    def _receive_more_same(self):
        """Quick action to receive more stock of the last received item."""
        if not self._last_received_item_id:
            messagebox.showinfo("No Recent Receipt", "Receive stock once first to use this feature.")
            return
        
        # Select the last received item
        for item in self.items_tree.get_children():
            if self.items_tree.item(item)["values"][0] == self._last_received_item_id:
                self.items_tree.selection_set(item)
                self.items_tree.see(item)
                self._on_item_select(None)
                # Focus on quantity field for quick entry
                try:
                    self.quantity_var.set("")
                    # Find the quantity entry widget and focus it
                    for child in self.winfo_children():
                        if isinstance(child, ttk.Entry):
                            child.focus_set()
                            break
                except Exception:
                    pass
                break
    
    def _refresh_all(self):
        """Refresh all displays."""
        self._load_items()
        self._load_item_lots()
        self._load_recent_purchases()
        self._load_movements()
        self._load_adjustment_history()  # Was missing - now included
        
        # Re-select the item if there was one selected
        if self.selected_item_id:
            for item in self.items_tree.get_children():
                if self.items_tree.item(item)["values"][0] == self.selected_item_id:
                    self.items_tree.selection_set(item)
                    break

    def _refresh_current_tab(self):
        """Refresh only the currently active tab's data to avoid unnecessary queries."""
        try:
            selected = self.notebook.index(self.notebook.select())
            if selected == TabIndex.RECEIVE:
                self._load_items()
                if self.selected_item_id:
                    self._load_item_lots()
            elif selected == TabIndex.LOTS:
                self._load_item_lots()
            elif selected == TabIndex.PURCHASES:
                self._load_recent_purchases()
            elif selected == TabIndex.MOVEMENTS:
                self._load_movements()
            elif selected == TabIndex.ADJUSTMENTS:
                self._load_adjustment_history()
        except Exception as e:
            logger.exception(f"Failed to refresh current tab: {e}")

    def _open_notes_dialog(self):
        """Open a modal dialog for editing notes in a larger editor."""
        try:
            dlg = tk.Toplevel(self)
            dlg.title("Add/Edit Notes")
            dlg.geometry("650x450")
            dlg.resizable(True, True)
            dlg.transient(self.winfo_toplevel())
            dlg.grab_set()
            
            # Set window attributes to ensure control buttons are visible
            dlg.attributes('-toolwindow', False)  # Ensure it's not a tool window
            dlg.overrideredirect(False)  # Ensure title bar is visible
            
            # Set custom icon
            try:
                icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'app_icon.ico')
                if os.path.exists(icon_path):
                    dlg.iconbitmap(icon_path)
                else:
                    # Fallback to PNG if ICO not found
                    png_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'logo.png')
                    if os.path.exists(png_path):
                        icon_img = tk.PhotoImage(file=png_path)
                        dlg.iconphoto(True, icon_img)
            except Exception as icon_e:
                logger.debug(f"Could not set dialog icon: {icon_e}")
            
            # Set minimum size
            dlg.minsize(500, 350)
            
            # Main frame with padding - use grid for better control
            main_frame = ttk.Frame(dlg, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(2, weight=1)  # Text editor row expands
            
            # Title label
            title_label = ttk.Label(main_frame, text="Stock Receiving Notes", 
                                  font=("", 12, "bold"))
            title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
            
            # Instructions
            instr_label = ttk.Label(main_frame, 
                                  text="Add any notes about this stock receipt (optional):",
                                  foreground="#666666")
            instr_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
            
            # Text editor frame
            text_frame = ttk.Frame(main_frame, relief="sunken", borderwidth=1)
            text_frame.grid(row=2, column=0, sticky=tk.NSEW, pady=(0, 10))
            
            # Text widget with scrollbar
            editor = tk.Text(text_frame, wrap=tk.WORD, font=("", 10),
                           padx=8, pady=8, undo=True)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=editor.yview)
            editor.configure(yscrollcommand=scrollbar.set)
            
            editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Insert current content
            editor.insert("1.0", self.notes_content)
            editor.focus_set()
            
            # Character counter
            counter_var = tk.StringVar()
            counter_label = ttk.Label(main_frame, textvariable=counter_var, 
                                    foreground="#666666", font=("", 9))
            counter_label.grid(row=3, column=0, sticky=tk.E, pady=(0, 8))
            
            # Update counter function
            def update_counter(event=None):
                content = editor.get("1.0", tk.END).rstrip()
                char_count = len(content)
                counter_var.set(f"{char_count} characters")
            
            # Bind counter update
            editor.bind("<KeyRelease>", update_counter)
            editor.bind("<Key>", update_counter)
            update_counter()  # Initial count
            
            # Separator
            sep_frame = ttk.Frame(main_frame)
            sep_frame.grid(row=4, column=0, sticky=tk.EW, pady=(6, 6))
            ttk.Separator(sep_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)
            
            # Bottom button area - fixed at bottom using grid
            btn_frame = ttk.Frame(main_frame)
            btn_frame.grid(row=5, column=0, sticky=tk.EW, pady=(0, 0))
            
            # Spacer to push buttons to the right
            ttk.Label(btn_frame).pack(side=tk.LEFT, expand=True)

            def _save_and_close(event=None):
                content = editor.get("1.0", tk.END).rstrip()
                self.notes_content = content
                
                # Update indicator to show if notes exist
                if content:
                    lines = content.splitlines()
                    preview = lines[0] if lines else ""
                    if len(preview) > 30:
                        preview = preview[:27] + "..."
                    self.notes_indicator_var.set(f"✓ {preview}")
                else:
                    self.notes_indicator_var.set("")
                
                dlg.destroy()

            def _clear_text(event=None):
                editor.delete("1.0", tk.END)
                update_counter()

            def _cancel(event=None):
                """Cancel editing notes without saving and close the dialog."""
                dlg.destroy()

            # Buttons - packed into btn_frame
            save_btn = ttk.Button(btn_frame, text="Save Notes", command=_save_and_close, 
                                style="Accent.TButton")
            save_btn.pack(side=tk.RIGHT)
            
            clear_btn = ttk.Button(btn_frame, text="Clear", command=_clear_text)
            clear_btn.pack(side=tk.RIGHT, padx=(0, 8))
            
            cancel_btn = ttk.Button(btn_frame, text="Cancel", command=_cancel)
            cancel_btn.pack(side=tk.RIGHT, padx=(0, 8))
            
            # Bind keyboard shortcuts
            dlg.bind("<Control-s>", lambda e: _save_and_close())
            dlg.bind("<Control-S>", lambda e: _save_and_close())
            dlg.bind("<Control-l>", lambda e: _clear_text())
            dlg.bind("<Control-L>", lambda e: _clear_text())
            dlg.bind("<Escape>", lambda e: _cancel())
            
            # Center dialog on parent
            dlg.update_idletasks()
            parent = self.winfo_toplevel()
            x = parent.winfo_rootx() + (parent.winfo_width() - dlg.winfo_reqwidth()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - dlg.winfo_reqheight()) // 2
            dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
            
            # Focus on editor
            editor.focus_set()
            editor.see("1.0")
            
            dlg.wait_window()
            
        except Exception as e:
            logger.exception(f"Failed to open notes dialog: {e}")
            messagebox.showerror("Error", f"Failed to open notes editor: {e}")
    
    def _on_costing_method_change(self, event):
        """Handle costing method change."""
        new_method = self.costing_method_var.get()
        
        if messagebox.askyesno(
            "Change Costing Method",
            f"Change inventory costing method to {new_method}?\n\n"
            "This will affect how cost of goods sold is calculated for future sales."
        ):
            try:
                set_costing_method(CostingMethod(new_method))
                messagebox.showinfo("Success", f"Costing method changed to {new_method}")
            except Exception as e:
                logger.error(f"Failed to change costing method: {e}")
                messagebox.showerror("Error", f"Failed to change costing method: {e}")
        else:
            # Revert to current method
            current = get_costing_method()
            self.costing_method_var.set(current.value)
    
    def _on_tab_changed(self, event):
        """Handle tab change to show/hide item list as needed.
        
        Uses state tracking instead of pane membership checks for reliability.
        Only the Receive Stock tab shows the item list.
        """
        try:
            selected = self.notebook.index(self.notebook.select())
            
            # Unbind previous Ctrl+S shortcut
            try:
                self.unbind_all("<Control-s>")
                self.unbind_all("<Control-S>")
            except:
                pass
            
            if selected == TabIndex.RECEIVE:
                # Show item list for receiving stock
                if not self._item_list_visible:
                    try:
                        self.paned.insert(0, self.left_frame, weight=1)
                        self._item_list_visible = True
                        logger.debug("Item list shown for Receive Stock tab")
                    except Exception as e:
                        logger.error(f"Failed to show item list: {e}")
                # Bind Ctrl+S to receive stock
                self.bind_all("<Control-s>", lambda e: self._receive_stock())
                self.bind_all("<Control-S>", lambda e: self._receive_stock())
            elif selected == TabIndex.LOTS:
                # Show item list for Stock Lots tab so user can select items
                if not self._item_list_visible:
                    try:
                        self.paned.insert(0, self.left_frame, weight=1)
                        self._item_list_visible = True
                        logger.debug("Item list shown for Stock Lots tab")
                    except Exception as e:
                        logger.error(f"Failed to show item list: {e}")
                # Refresh lots for currently selected item
                if self.selected_item_id:
                    self._load_item_lots()
            elif selected == TabIndex.ADJUSTMENTS:
                # Hide item list and bind Ctrl+S to record adjustment
                if self._item_list_visible:
                    try:
                        self.paned.forget(self.left_frame)
                        self._item_list_visible = False
                        logger.debug(f"Item list hidden for Adjustments tab")
                    except Exception as e:
                        logger.error(f"Failed to hide item list: {e}")
                self.bind_all("<Control-s>", lambda e: self._record_adjustment())
                self.bind_all("<Control-S>", lambda e: self._record_adjustment())
            else:
                # Hide item list for other tabs (Purchases, Movements)
                if self._item_list_visible:
                    try:
                        self.paned.forget(self.left_frame)
                        self._item_list_visible = False
                        logger.debug(f"Item list hidden for tab {selected}")
                    except Exception as e:
                        logger.error(f"Failed to hide item list: {e}")
            
            # Force geometry update for smooth layout transition
            self.update_idletasks()
            
        except Exception as e:
            logger.exception(f"Tab change handler failed: {e}")


class StockReceivingDialog(tk.Toplevel):
    """Standalone dialog for stock receiving."""
    
    def __init__(self, parent, user_id: Optional[int] = None):
        super().__init__(parent)
        self.title("Stock Receiving")
        self.geometry("1100x700")
        set_window_icon(self)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Add frame
        self.frame = StockReceivingFrame(self, user_id=user_id)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Footer controls
        footer = ttk.Frame(self)
        # Footer intentionally left minimal for layout
        # Buttons moved into respective tab forms for clarity
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")




def open_stock_receiving(parent, user_id: Optional[int] = None):
    """Open the stock receiving dialog."""
    dialog = StockReceivingDialog(parent, user_id)
    dialog.wait_window()
