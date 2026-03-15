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


def _get_tc():
    """Get theme colors with safe fallback."""
    try:
        from utils.theme import get_theme_colors, get_status_color
        return get_theme_colors()
    except Exception:
        return {'surface': '#FFFFFF', 'table_row_alt': '#f8f9fa', 'background': '#f5f5f5',
                'text': '#1f2937', 'text_secondary': '#6b7280',
                'warning': '#f59e0b', 'danger': '#ef4444',
                'field_bg': '#FFFFFF', 'field_text': '#1f2937'}


def _get_status_color(status: str) -> str:
    """Get theme status color with safe fallback."""
    try:
        from utils.theme import get_status_color
        return get_status_color(status)
    except Exception:
        fallbacks = {'blue': '#0ea5e9', 'green': '#10b981', 'red': '#ef4444', 'orange': '#f59e0b'}
        return fallbacks.get(status, '#000000')
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
from utils.security import get_username
from utils.i18n import get_currency_symbol
from utils import set_window_icon
from utils.date_utils import format_date, get_date_format, parse_date_flexible, get_tkcalendar_date_pattern
from modules import permissions

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
        self.currency = get_currency_symbol()
        self.selected_item_id = None
        self._item_list_visible = True  # Track item list visibility state
        self._form_state = {}  # Store form data per item for persistence
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
            text="Stock Receiving", 
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
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_items())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        
        # Clear search button
        ttk.Button(search_frame, text="X", width=3, 
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
        self.notebook.add(frame, text="Receive Stock")
        
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
            text="Receive Stock",
            command=self._receive_stock,
            style="Primary.TButton",
            state="disabled"  # disabled until an item is selected
        )
        self.receive_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Add helper text when button is disabled
        self.receive_help_var = tk.StringVar(value="<-- Select an item first")
        self.receive_help_label = ttk.Label(
            top_btn_frame,
            textvariable=self.receive_help_var,
            font=("Segoe UI", 9, "italic")
        )
        self.receive_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.clear_form_btn = ttk.Button(
            top_btn_frame,
            text="Clear Form",
            command=self._clear_form
        )
        self.clear_form_btn.pack(side=tk.LEFT)
        
        # Helper text for Ctrl+S shortcut
        ttk.Label(
            top_btn_frame,
            text="• Ctrl+S to Save",
            font=("Segoe UI", 9, "italic"),
            foreground=_get_tc().get('info', '#0066cc')
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        # End top control buttons
        
        # Create scrollable form container
        form_container = ttk.Frame(frame)
        form_container.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        # Create canvas with scrollbar
        form_canvas = tk.Canvas(form_container, highlightthickness=0, bg="white")
        form_scrollbar = ttk.Scrollbar(form_container, orient=tk.VERTICAL, command=form_canvas.yview)
        scrollable_frame = ttk.Frame(form_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all"))
        )
        
        form_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scrollbar.set)
        
        # Pack canvas and scrollbar
        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            form_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        form_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Receive form - now inside scrollable container
        form_frame = ttk.LabelFrame(scrollable_frame, text="New Stock Details", padding=12)
        form_frame.pack(fill=tk.X, padx=4, pady=4)
        
        row = 0
        
        # Quantity with unit of measure
        ttk.Label(form_frame, text="Quantity *:").grid(row=row, column=0, sticky=tk.W, pady=4)
        
        # Frame for quantity entry and unit label
        quantity_frame = ttk.Frame(form_frame)
        quantity_frame.grid(row=row, column=1, sticky=tk.W, pady=4)
        
        self.quantity_var = tk.StringVar()
        quantity_entry = ttk.Entry(quantity_frame, textvariable=self.quantity_var, width=15)
        quantity_entry.pack(side=tk.LEFT)
        
        # Unit label that will be updated when item is selected
        self.unit_label_var = tk.StringVar(value="")
        self.unit_label = ttk.Label(quantity_frame, textvariable=self.unit_label_var, font=("Segoe UI", 9))
        self.unit_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # Quantity validation label
        self.quantity_error_var = tk.StringVar()
        self.quantity_error_label = ttk.Label(
            form_frame, 
            textvariable=self.quantity_error_var, 
            foreground=_get_status_color('danger'), 
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
            foreground=_get_status_color('danger'), 
            font=("Segoe UI", 8)
        )
        self.cost_error_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0))
        self.cost_price_var.trace_add("write", lambda *a: self._validate_cost_price())
        row += 1
        
        # Total cost display (new row for better visibility)
        ttk.Label(form_frame, text="Total Cost:").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.total_cost_var = tk.StringVar(value="--")
        ttk.Label(form_frame, textvariable=self.total_cost_var, font=("Segoe UI", 10, "bold"), 
                 foreground=_get_tc().get('info', '#0066cc')).grid(row=row, column=1, sticky=tk.W, pady=4)
        row += 1
        
        # Selling Price (lot-specific) - REQUIRED
        self.selling_price_label_var = tk.StringVar(value=f"Selling Price ({self.currency}) *:")
        self.selling_price_label = ttk.Label(form_frame, textvariable=self.selling_price_label_var)
        self.selling_price_label.grid(row=row, column=0, sticky=tk.W, pady=4)
        self.selling_price_var = tk.StringVar()
        self.selling_entry = ttk.Entry(form_frame, textvariable=self.selling_price_var, width=15)
        self.selling_entry.grid(row=row, column=1, sticky=tk.W, pady=4)
        
        # Selling price validation label
        self.selling_error_var = tk.StringVar()
        self.selling_error_label = ttk.Label(
            form_frame, 
            textvariable=self.selling_error_var, 
            foreground=_get_status_color('danger'), 
            font=("Segoe UI", 8)
        )
        self.selling_error_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0))
        self.selling_price_var.trace_add("write", lambda *a: self._validate_selling_price())
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
            _tc = _get_tc()
            _accent = _tc.get('accent', _tc.get('primary', '#3b82f6'))
            _tw = _tc.get('text_white', '#ffffff')
            self.purchase_date_entry = TopDateEntry(
                form_frame, 
                textvariable=self.purchase_date_var,
                width=12,
                background=_accent,
                foreground=_tw,
                headersbackground=_accent,
                headersforeground=_tw,
                selectbackground=_accent,
                selectforeground=_tw,
                borderwidth=2,
                date_pattern=get_tkcalendar_date_pattern(),
                state='readonly'
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
            _tc = _get_tc()
            _accent = _tc.get('accent', _tc.get('primary', '#3b82f6'))
            _tw = _tc.get('text_white', '#ffffff')
            self.expiry_date_entry = TopDateEntry(
                form_frame, 
                textvariable=self.expiry_date_var,
                width=12,
                background=_accent,
                foreground=_tw,
                headersbackground=_accent,
                headersforeground=_tw,
                selectbackground=_accent,
                selectforeground=_tw,
                borderwidth=2,
                date_pattern=get_tkcalendar_date_pattern(),
                state='readonly'
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
            text="Add Notes", 
            command=self._open_notes_dialog,
            width=15
        ).grid(row=row, column=2, sticky=tk.W, pady=4)
        
        # Notes indicator next to the button
        ttk.Label(
            form_frame, 
            textvariable=self.notes_indicator_var,
            foreground=_get_tc().get('info', '#0066cc'),
            font=("Segoe UI", 8)
        ).grid(row=row, column=2, sticky=tk.W, padx=(110, 0), pady=4)
        
        row += 1
        
        # Ensure form columns can expand properly
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(2, weight=0)
    
    def _build_lots_tab(self):
        """Build the Stock Lots tab."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="Stock Lots")
        
        # Lots treeview
        columns = ("lot_id", "date", "received", "remaining", "cost", "selling", "supplier", "expiry")
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
        self.lots_tree.heading("selling", text=f"Selling ({self.currency})")
        self.lots_tree.heading("supplier", text="Supplier")
        self.lots_tree.heading("expiry", text="Expiry")
        
        self.lots_tree.column("lot_id", width=60, minwidth=50)
        self.lots_tree.column("date", width=100, minwidth=80)
        self.lots_tree.column("received", width=70, minwidth=60)
        self.lots_tree.column("remaining", width=70, minwidth=60)
        self.lots_tree.column("cost", width=80, minwidth=60)
        self.lots_tree.column("selling", width=80, minwidth=60)
        self.lots_tree.column("supplier", width=120, minwidth=80)
        self.lots_tree.column("expiry", width=90, minwidth=70)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.lots_tree.yview)
        self.lots_tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection event to show lot details
        self.lots_tree.bind("<<TreeviewSelect>>", self._on_lot_selected_in_table)
        
        self.lots_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Lot details panel at bottom
        self.details_frame = ttk.LabelFrame(frame, text="Selected Lot Details", padding=8)
        self.details_frame.pack(fill=tk.X, pady=(8, 0))
        
        # Create a grid for lot details (for regular items)
        ttk.Label(self.details_frame, text="Lot ID:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5)
        self.lot_detail_id_var = tk.StringVar(value="--")
        ttk.Label(self.details_frame, textvariable=self.lot_detail_id_var).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(self.details_frame, text="Cost Price:", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky=tk.W, padx=5)
        self.lot_detail_cost_var = tk.StringVar(value="--")
        ttk.Label(self.details_frame, textvariable=self.lot_detail_cost_var).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(self.details_frame, text="Selling Price:", font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky=tk.W, padx=5)
        self.lot_detail_selling_var = tk.StringVar(value="--")
        ttk.Label(self.details_frame, textvariable=self.lot_detail_selling_var).grid(row=0, column=5, sticky=tk.W, padx=5)
        
        ttk.Label(self.details_frame, text="Remaining Qty:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, padx=5)
        self.lot_detail_qty_var = tk.StringVar(value="--")
        ttk.Label(self.details_frame, textvariable=self.lot_detail_qty_var).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(self.details_frame, text="Supplier:", font=("Segoe UI", 9, "bold")).grid(row=1, column=2, sticky=tk.W, padx=5)
        self.lot_detail_supplier_var = tk.StringVar(value="--")
        ttk.Label(self.details_frame, textvariable=self.lot_detail_supplier_var).grid(row=1, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(self.details_frame, text="Expiry Date:", font=("Segoe UI", 9, "bold")).grid(row=1, column=4, sticky=tk.W, padx=5)
        self.lot_detail_expiry_var = tk.StringVar(value="--")
        ttk.Label(self.details_frame, textvariable=self.lot_detail_expiry_var).grid(row=1, column=5, sticky=tk.W, padx=5)
        
        # Portions breakdown table for special volume items (replaces regular details)
        self.portions_detail_frame = ttk.LabelFrame(frame, text="Portion Details for Lot", padding=8)
        self.portions_detail_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.portions_detail_frame.pack_forget()  # Hidden by default
        
        # Create treeview for portions details
        columns = ("portion_name", "cost_price", "selling_price", "margin")
        self.portions_detail_tree = ttk.Treeview(self.portions_detail_frame, columns=columns, show="headings", height=8)
        
        self.portions_detail_tree.heading("portion_name", text="Portion Name")
        self.portions_detail_tree.heading("cost_price", text=f"Cost Price ({self.currency})")
        self.portions_detail_tree.heading("selling_price", text=f"Selling Price ({self.currency})")
        self.portions_detail_tree.heading("margin", text="Margin (%)")
        
        self.portions_detail_tree.column("portion_name", width=150, anchor=tk.W)
        self.portions_detail_tree.column("cost_price", width=120, anchor=tk.E)
        self.portions_detail_tree.column("selling_price", width=120, anchor=tk.E)
        self.portions_detail_tree.column("margin", width=100, anchor=tk.E)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(self.portions_detail_frame, orient=tk.VERTICAL, command=self.portions_detail_tree.yview)
        self.portions_detail_tree.configure(yscroll=v_scroll.set)
        
        self.portions_detail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary at bottom
        summary_frame = ttk.Frame(frame)
        summary_frame.pack(fill=tk.X, pady=(8, 0))
        
        self.lots_summary_var = tk.StringVar(value="Select an item to view stock lots")
        ttk.Label(summary_frame, textvariable=self.lots_summary_var, font=("Segoe UI", 9, "italic")).pack(side=tk.LEFT)
    
    def _build_purchases_tab(self):
        """Build the Recent Purchases tab."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="Recent Purchases")
        
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
        self.notebook.add(frame, text="Movements")
        
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
        self.notebook.add(frame, text="Adjustments")
        
        # Adjustment reasons configuration
        self.adjustment_reasons = {
            "Spoiled": {"icon": "", "color": "#fd7e14", "desc": "Mold, rot, spoilage", "add": False},
            "Damaged": {"icon": "", "color": "#dc3545", "desc": "Physical damage, breakage", "add": False},
            "Expired": {"icon": "", "color": "#6c757d", "desc": "Past expiration date", "add": False},
            "Theft": {"icon": "", "color": "#dc3545", "desc": "Missing/stolen items", "add": False},
            "Quality Issue": {"icon": "", "color": "#fd7e14", "desc": "Quality problems detected", "add": False},
            "Waste": {"icon": "", "color": "#ffc107", "desc": "General waste/disposal", "add": False},
            "Correction": {"icon": "", "color": "#0dcaf0", "desc": "Inventory correction (both add/remove)", "add": False},
            "Breakage": {"icon": "", "color": "#dc3545", "desc": "Broken during handling", "add": False},
            "Stock Addition": {"icon": "", "color": "#10b981", "desc": "Add back stock (e.g., under-received items)", "add": True},
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
        
        # LEFT PANEL - ADJUSTMENT FORM
        
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
        if HAS_TKCALENDAR:
            _tc = _get_tc()
            _accent = _tc.get('accent', _tc.get('primary', '#3b82f6'))
            _tw = _tc.get('text_white', '#ffffff')
            self.adj_expiry_entry = TopDateEntry(
                left_frame, 
                textvariable=self.adj_expiry_var,
                width=12,
                background=_accent,
                foreground=_tw,
                headersbackground=_accent,
                headersforeground=_tw,
                selectbackground=_accent,
                selectforeground=_tw,
                borderwidth=2,
                date_pattern=get_tkcalendar_date_pattern(),
                state='readonly'
            )
            self.adj_expiry_entry.grid(row=row, column=1, sticky=tk.W, pady=8)
        else:
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
            text="Record Adjustment",
            command=self._record_adjustment,
            style="Primary.TButton"
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            btn_frame,
            text="Clear",
            command=self._clear_adjustment_form
        ).pack(side=tk.LEFT)
        
        # RIGHT PANEL - ADJUSTMENT HISTORY
        
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
            self.adj_reason_desc_var.set(f"- {desc}")
    
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
        """Record a stock adjustment (removal or addition)."""
        current_user = get_username()
        if not permissions.has_permission(current_user, 'adjust_stock'):
            messagebox.showerror("Permission Denied",
                                 "You do not have permission to adjust stock.")
            return

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
        
        # Determine if this is an addition or removal
        is_addition = self.adjustment_reasons.get(reason, {}).get("add", False)
        
        # Check available stock (for removals only)
        if not is_addition:
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
        
        # Build confirmation message
        action_text = "Add" if is_addition else "Remove"
        if is_addition:
            confirm_msg = (
                f"{action_text} {quantity} units of '{item_name}'\n"
                f"Reason: {reason}\n\n"
                f"This will increase inventory"
            )
        else:
            confirm_msg = (
                f"{action_text} {quantity} units of '{item_name}'\n"
                f"Reason: {reason}\n\n"
                f"This will reduce inventory"
            )
        
        # Confirm
        if not messagebox.askyesno("Confirm Adjustment", confirm_msg):
            return
        
        # Record adjustment
        try:
            # Positive for addition, negative for removal
            quantity_change = quantity if is_addition else -quantity
            
            movement = record_stock_adjustment(
                item_id=item_id,
                quantity_change=quantity_change,
                reason=full_reason,
                user_id=self.user_id,
                lot_id=lot_id,
                unit_cost=items_module.get_item(item_id).get("cost_price", 0) if not is_addition else 0
            )
            
            messagebox.showinfo(
                "Success",
                f"Adjustment recorded successfully!\n\n"
                f"Item: {item_name}\n"
                f"Quantity {action_text.lower()}ed: {quantity}\n"
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
            
            # Configure tags for color coding using theme colors
            _tc = _get_tc()
            self.adjustments_tree.tag_configure("spoiled", background=_tc.get('warning_bg', '#fff3cd'), foreground=_tc.get('warning', '#856404'))
            self.adjustments_tree.tag_configure("expired", background=_tc.get('neutral_bg', '#e2e3e5'), foreground=_tc.get('text_secondary', '#383d41'))
            self.adjustments_tree.tag_configure("damaged", background=_tc.get('danger_bg', '#f8d7da'), foreground=_tc.get('danger', '#721c24'))
            self.adjustments_tree.tag_configure("theft", background=_tc.get('danger_bg', '#f5c6cb'), foreground=_tc.get('danger', '#721c24'))
            self.adjustments_tree.tag_configure("waste", background=_tc.get('warning_bg', '#ffeaa7'), foreground=_tc.get('text_secondary', '#666'))
            
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
            _tc = _get_tc()
            self.items_tree.tag_configure("lowstock", background=_tc.get('warning_bg', '#fff3cd'), foreground=_tc.get('warning', '#856404'))
            
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
        
        # Save form state for the previously selected item before switching
        if self.selected_item_id:
            self._form_state[self.selected_item_id] = {
                'quantity': self.quantity_var.get(),
                'cost_price': self.cost_price_var.get(),
                'selling_price': self.selling_price_var.get(),
                'supplier': self.supplier_var.get(),
                'reference': self.reference_var.get(),
                'expiry_date': self.expiry_date_var.get(),
                'notes': self.notes_content if hasattr(self, 'notes_content') else "",
                'notes_indicator': self.notes_indicator_var.get()
            }
        
        values = self.items_tree.item(selection[0])["values"]
        self.selected_item_id = values[0]
        item_name = values[1]
        
        # Update item info display
        self.item_name_var.set(f"{item_name}")
        
        # Restore form state for this item if it was previously saved
        if self.selected_item_id in self._form_state:
            state = self._form_state[self.selected_item_id]
            self.quantity_var.set(state['quantity'])
            self.cost_price_var.set(state['cost_price'])
            self.selling_price_var.set(state['selling_price'])
            self.supplier_var.set(state['supplier'])
            self.reference_var.set(state['reference'])
            self.expiry_date_var.set(state['expiry_date'])
            self.notes_content = state['notes']
            self.notes_indicator_var.set(state['notes_indicator'])
            try:
                self._update_total_cost()  # Recalculate total cost with restored values
            except Exception as e:
                logger.debug(f"Could not recalculate total cost: {e}")
                self.total_cost_var.set("--")
        else:
            # First time with this item, populate with item master prices
            self.quantity_var.set("")
            self.selling_error_var.set("")
            self.supplier_var.set("")
            self.reference_var.set("")
            self.expiry_date_var.set("")
            self.notes_content = ""
            self.notes_indicator_var.set("")
            self.total_cost_var.set("--")
            
            # Load master prices from database and populate fields
            try:
                from database.init_db import get_connection
                with get_connection() as conn:
                    item = conn.execute(
                        "SELECT selling_price, cost_price, is_special_volume, unit_of_measure FROM items WHERE item_id = ?",
                        (self.selected_item_id,)
                    ).fetchone()
                    
                    if item:
                        is_special_volume = item[2]  # is_special_volume
                        unit_of_measure = item[3]  # unit_of_measure
                        
                        # Update unit label for measurable items
                        if unit_of_measure and unit_of_measure.lower() != "pieces":
                            self.unit_label_var.set(unit_of_measure)
                        else:
                            self.unit_label_var.set("")
                        
                        # For special volume items (sold in portions), selling price is optional
                        # since portions handle their own pricing
                        if is_special_volume:
                            self.selling_price_var.set("")  # Clear selling price for portioned items
                        elif item[0] and item[0] > 0:  # selling_price for regular items
                            self.selling_price_var.set(f"{item[0]:.2f}")
                        
                        # Populate cost price from item master if available (as default for future receives)
                        if item[1] and item[1] > 0:  # cost_price
                            self.cost_price_var.set(f"{item[1]:.2f}")
                            
                        # Store whether this item is special volume for validation
                        self._selected_item_is_special_volume = bool(is_special_volume)
                        
                        # Update selling price label and enable/disable field based on item type
                        if self._selected_item_is_special_volume:
                            self.selling_price_label_var.set(f"Selling Price ({self.currency}):")
                            self.selling_entry.config(state="disabled")
                            self.selling_price_var.set("")  # Clear any existing value
                        else:
                            self.selling_price_label_var.set(f"Selling Price ({self.currency}):")
                            self.selling_entry.config(state="normal")
            except Exception as e:
                logger.debug(f"Could not load master prices for item {self.selected_item_id}: {e}")
                self.selling_price_var.set("")
                self._selected_item_is_special_volume = False
                self.selling_price_label_var.set(f"Selling Price ({self.currency}):")
                self.selling_entry.config(state="normal")
                self.selling_entry.config(state="normal")
        
        # Enable receive button when an item is selected
        try:
            if self.receive_btn.winfo_exists():
                self.receive_btn.config(state="normal")
                self.receive_help_var.set("Ready to receive stock")
                logger.debug(f"Receive button enabled for item {self.selected_item_id}")
            else:
                logger.warning("Receive button widget does not exist")
        except Exception as e:
            logger.error(f"Failed to enable receive button: {e}")
        
        # Get stock summary
        try:
            summary = get_item_stock_summary(self.selected_item_id)
            self.item_stock_var.set(f"Current Stock: {summary['total_quantity']}")
            self.item_avg_cost_var.set(f"Avg Cost: {self.currency} {summary['average_cost']:.2f}")
            
            # Pre-fill cost price with last purchase price if available (only if not already set)
            if not self.cost_price_var.get():
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
                
                # For special volume items, show portion info for both cost and selling price
                if self._selected_item_is_special_volume:
                    from modules import portions
                    item_portions = portions.list_portions(self.selected_item_id, active_only=True)
                    if item_portions:
                        selling_display = f"{len(item_portions)} portions"
                        # Show average cost per portion or first portion cost
                        avg_cost = sum(float(p.get('cost_price', 0)) for p in item_portions) / len(item_portions) if item_portions else 0
                        cost_display = f"Avg: {avg_cost:.2f}"
                    else:
                        selling_display = "No portions"
                        cost_display = "-"
                else:
                    selling_display = f"{lot.selling_price:.2f}" if lot.selling_price else "-"
                    cost_display = f"{lot.cost_price:.2f}"
                
                self.lots_tree.insert("", tk.END, values=(
                    lot.lot_id,
                    format_date(lot.purchase_date) if lot.purchase_date else "-",
                    lot.quantity_received,
                    lot.quantity_remaining,
                    cost_display,
                    selling_display,
                    lot.supplier or "-",
                    format_date(lot.expiry_date) if lot.expiry_date else "-"
                ), tags=tags)
            
            # Configure tags
            _tc = _get_tc()
            self.lots_tree.tag_configure("lowstock", background=_tc.get('warning_bg', '#fff3cd'))
            self.lots_tree.tag_configure("expiring", background=_tc.get('danger_bg', '#f8d7da'))
            
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
    
    def _on_lot_selected_in_table(self, event):
        """Handle lot selection in the stock lots table."""
        selection = self.lots_tree.selection()
        
        if not selection:
            # Clear the details panel
            self.lot_detail_id_var.set("--")
            self.lot_detail_cost_var.set("--")
            self.lot_detail_selling_var.set("--")
            self.lot_detail_qty_var.set("--")
            self.lot_detail_supplier_var.set("--")
            self.lot_detail_expiry_var.set("--")
            # Hide portions frame
            self.portions_detail_frame.pack_forget()
            # Show regular details frame
            self.details_frame.pack(fill=tk.X, pady=(8, 0))
            return
        
        try:
            # Get the selected row values
            item_id = self.lots_tree.item(selection[0])["values"]
            
            if not item_id or not self.selected_item_id:
                return
            
            # Fetch the full lot details from database
            lots = get_stock_lots(self.selected_item_id, include_empty=False)
            
            # Find the selected lot by lot_id (first column is lot_id)
            selected_lot_id = item_id[0]  # lot_id is first column
            
            selected_lot = None
            for lot in lots:
                if lot.lot_id == selected_lot_id:
                    selected_lot = lot
                    break
            
            if selected_lot:
                # Update the details panel
                self.lot_detail_id_var.set(str(selected_lot.lot_id))
                
                # For special volume items, show portion breakdown instead of simple pricing
                if self._selected_item_is_special_volume:
                    from modules import portions
                    item_portions = portions.list_portions(self.selected_item_id, active_only=True)
                    
                    # Clear portions tree
                    for item in self.portions_detail_tree.get_children():
                        self.portions_detail_tree.delete(item)
                    
                    # Show portions details
                    if item_portions:
                        # Hide regular details frame
                        self.details_frame.pack_forget()
                        # Show portions details frame
                        self.portions_detail_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
                        
                        for portion in item_portions:
                            cost_price = float(portion.get('cost_price', 0))
                            selling_price = float(portion.get('selling_price', 0))
                            margin = ((selling_price - cost_price) / selling_price * 100) if selling_price > 0 else 0
                            
                            self.portions_detail_tree.insert("", tk.END, values=(
                                portion['portion_name'],
                                f"{self.currency} {cost_price:.2f}",
                                f"{self.currency} {selling_price:.2f}",
                                f"{margin:.1f}%" if selling_price > 0 else "N/A"
                            ))
                        
                        # Show lot info but minimal pricing
                        self.lot_detail_cost_var.set(f"Multiple portions - see breakdown below")
                        self.lot_detail_selling_var.set("Multiple portions - see breakdown below")
                    else:
                        # Hide portions frame and show regular details
                        self.portions_detail_frame.pack_forget()
                        self.details_frame.pack(fill=tk.X, pady=(8, 0))
                        self.lot_detail_cost_var.set("Portion-based (no portions set)")
                        self.lot_detail_selling_var.set("Portion-based (no portions set)")
                else:
                    # Hide portions frame for regular items
                    self.portions_detail_frame.pack_forget()
                    # Show regular details frame
                    self.details_frame.pack(fill=tk.X, pady=(8, 0))
                    self.lot_detail_cost_var.set(f"{self.currency} {selected_lot.cost_price:.2f}")
                    self.lot_detail_selling_var.set(f"{self.currency} {selected_lot.selling_price:.2f}" if selected_lot.selling_price else "--")
                
                self.lot_detail_qty_var.set(str(selected_lot.quantity_remaining))
                self.lot_detail_supplier_var.set(selected_lot.supplier or "--")
                self.lot_detail_expiry_var.set(format_date(selected_lot.expiry_date) if selected_lot.expiry_date else "--")
                
                logger.debug(f"Selected lot {selected_lot_id}: cost={selected_lot.cost_price}, selling={selected_lot.selling_price}")
                
        except Exception as e:
            logger.exception(f"Failed to display lot details: {e}")
            self.lot_detail_id_var.set("Error")
    
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
            _tc = _get_tc()
            self.movements_tree.tag_configure("sale", foreground=_tc.get('danger', '#dc3545'))
            self.movements_tree.tag_configure("purchase", foreground=_tc.get('success', '#28a745'))
            self.movements_tree.tag_configure("waste", foreground=_tc.get('warning', '#fd7e14'))
            
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
                self.quantity_error_var.set("Must be > 0")
            elif qty > 100000:
                self.quantity_error_var.set("Unusually high")
            else:
                self.quantity_error_var.set("")
        except ValueError:
            self.quantity_error_var.set("Invalid number")
        
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
                self.cost_error_var.set("Cannot be negative")
            elif cost == 0:
                self.cost_error_var.set("Warning: Zero cost")
            elif cost > 1000000:
                self.cost_error_var.set("Unusually high")
            else:
                self.cost_error_var.set("")
        except ValueError:
            self.cost_error_var.set("Invalid number")
        
        self._update_total_cost()
    
    def _validate_selling_price(self):
        """Validate selling price input in real-time."""
        value = self.selling_price_var.get().strip()
        
        # Skip validation for special volume items (selling price not required)
        if hasattr(self, '_selected_item_is_special_volume') and self._selected_item_is_special_volume:
            self.selling_error_var.set("")
            return
        
        if not value:
            self.selling_error_var.set("Required")
            return
        
        try:
            price = float(value)
            if price < 0:
                self.selling_error_var.set("Cannot be negative")
            elif price == 0:
                self.selling_error_var.set("Cannot be zero")
            elif price > 1000000:
                self.selling_error_var.set("Unusually high")
            else:
                self.selling_error_var.set("")
        except ValueError:
            self.selling_error_var.set("Invalid number")
    
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
    
    def _save_form_information(self):
        """Save the current form information without completing the stock receipt."""
        if not self.selected_item_id:
            messagebox.showwarning("Warning", "Please select an item first.")
            return
        
        # Validate required fields
        quantity_str = self.quantity_var.get().strip()
        if not quantity_str:
            messagebox.showerror("Error", "Quantity is required")
            return
        
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid quantity: {e}")
            return
        
        cost_str = self.cost_price_var.get().strip()
        if not cost_str:
            messagebox.showerror("Error", "Cost price is required")
            return
        
        try:
            cost_price = float(cost_str)
            if cost_price < 0:
                raise ValueError("Cost price cannot be negative")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid cost price: {e}")
            return
        
        # Validate selling price - only required for non-special volume items
        selling_str = self.selling_price_var.get().strip()
        if not self._selected_item_is_special_volume and not selling_str:
            messagebox.showerror("Error", "Selling price is required")
            return
        
        selling_price = None
        if not self._selected_item_is_special_volume and selling_str:
            try:
                selling_price = float(selling_str)
                if selling_price < 0:
                    raise ValueError("Selling price cannot be negative")
                if selling_price == 0:
                    raise ValueError("Selling price cannot be zero")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid selling price: {e}")
                return
        
        # Get optional fields
        item_name = self.item_name_var.get()
        supplier = self.supplier_var.get().strip() or "(Not specified)"
        reference = self.reference_var.get().strip() or "(Not specified)"
        
        # Build summary message
        if selling_price is not None:
            selling_price_display = f"{self.currency} {selling_price:.2f}"
        else:
            selling_price_display = "Not set (portion pricing)"
        
        summary = f"""Information Saved:

Item: {item_name}
Quantity: {quantity}
Cost Price: {self.currency} {cost_price:.2f}
Selling Price: {selling_price_display}
Supplier: {supplier}
Reference: {reference}

You can now:
• Continue editing the form
• Receive this stock by clicking 'Receive Stock'
• Clear and start with another item"""
        
        messagebox.showinfo("Information Saved", summary)
        
        # Restore button state after messagebox closes
        try:
            if self.receive_btn.winfo_exists():
                self.receive_btn.config(state="normal")
        except Exception as e:
            logger.error(f"Failed to restore button state after save: {e}")
    
    def _receive_stock(self):
        """Receive stock for the selected item."""
        logger.debug("Receive stock button clicked")
        
        current_user = get_username()
        if not permissions.has_permission(current_user, 'receive_stock'):
            messagebox.showerror("Permission Denied",
                                 "You do not have permission to receive stock.")
            return

        if not self.selected_item_id:
            logger.debug("No item selected")
            messagebox.showwarning("Warning", "Please select an item first.")
            try:
                if self.receive_btn.winfo_exists():
                    self.receive_btn.config(state="disabled")
                    self.receive_help_var.set("<-- Select an item first")
            except Exception as e:
                logger.error(f"Failed to disable receive button: {e}")
            return
        
        # Validate inputs
        quantity_str = self.quantity_var.get().strip()
        if not quantity_str:
            messagebox.showerror("Error", "Quantity is required")
            return
        
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid quantity: {e}")
            return
        
        cost_str = self.cost_price_var.get().strip()
        if not cost_str:
            messagebox.showerror("Error", "Cost price is required")
            return
        
        try:
            cost_price = float(cost_str)
            if cost_price < 0:
                raise ValueError("Cost price cannot be negative")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid cost price: {e}")
            return
        
        # Get selling price - only required for non-special volume items
        selling_str = self.selling_price_var.get().strip()
        if not self._selected_item_is_special_volume and not selling_str:
            messagebox.showerror("Error", "Selling price is required")
            return
        
        selling_price = None
        if not self._selected_item_is_special_volume and selling_str:
            try:
                selling_price = float(selling_str)
                if selling_price < 0:
                    raise ValueError("Selling price cannot be negative")
                if selling_price == 0:
                    raise ValueError("Selling price cannot be zero")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid selling price: {e}")
                return
        
        # Get optional fields
        supplier = self.supplier_var.get().strip() or "(Not specified)"
        reference = self.reference_var.get().strip() or "(Not specified)"
        purchase_date = self.purchase_date_var.get().strip()
        expiry_date = self.expiry_date_var.get().strip()
        notes = self.notes_content if hasattr(self, 'notes_content') else ""
        
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
        item_name = self.item_name_var.get()
        unit = self.unit_label_var.get() or "units"
        if selling_price is not None:
            confirm_msg = f"Receive {quantity} {unit} of '{item_name}'\nat {self.currency} {cost_price:.2f} each?\n\nTotal Cost: {self.currency} {quantity * cost_price:.2f}\nSelling Price: {self.currency} {selling_price:.2f} per unit"
        else:
            confirm_msg = f"Receive {quantity} {unit} of '{item_name}'\nat {self.currency} {cost_price:.2f} each?\n\nTotal Cost: {self.currency} {quantity * cost_price:.2f}\nSelling Price: Not set (portion pricing)"
        if not messagebox.askyesno(
            "Confirm Stock Receipt",
            confirm_msg
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
                purchase_date=purchase_date,
                selling_price=selling_price
            )
            
            if selling_price is not None:
                success_msg = f"Stock received successfully!\n\nLot ID: {lot.lot_id}\nQuantity: {quantity} {unit}\nCost: {self.currency} {cost_price:.2f}\nSelling Price: {self.currency} {selling_price:.2f}"
            else:
                success_msg = f"Stock received successfully!\n\nLot ID: {lot.lot_id}\nQuantity: {quantity} {unit}\nCost: {self.currency} {cost_price:.2f}\nSelling Price: Not set (portion pricing)"
            
            messagebox.showinfo("Success", success_msg)
            
            # Clear saved form state for this item since receipt is complete
            if self.selected_item_id in self._form_state:
                del self._form_state[self.selected_item_id]
            
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
        self.selling_price_var.set("")
        self.selling_error_var.set("")
        self.supplier_var.set("")
        self.reference_var.set("")
        
        self.purchase_date_var.set(format_date(datetime.now()))
        self.expiry_date_var.set("")
        
        # Reset selling price field state
        self.selling_price_label_var.set(f"Selling Price ({self.currency}):")
        self.selling_entry.config(state="normal")
        self._selected_item_is_special_volume = False
        
        # Clear notes content and indicator
        try:
            self.notes_content = ""
            self.notes_indicator_var.set("")
        except Exception:
            pass
        self.total_cost_var.set("--")
    
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
            dlg.withdraw()
            dlg.title("Add/Edit Notes")
            dlg.geometry("650x450")
            dlg.resizable(True, True)
            dlg.attributes('-toolwindow', False)
            dlg.overrideredirect(False)
            
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
                                  text="Add any notes about this stock receipt (optional):")
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
                                    font=("", 9))
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
                    self.notes_indicator_var.set(f"{preview}")
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
                                style="Primary.TButton")
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
            dlg.deiconify()
            dlg.lift()
            dlg.focus_force()
            dlg.grab_set()
            
            # Focus on editor
            editor.focus_set()
            editor.see("1.0")
            
            dlg.wait_window()
            
        except Exception as e:
            logger.exception(f"Failed to open notes dialog: {e}")
            messagebox.showerror("Error", f"Failed to open notes editor: {e}")
    
    def _on_costing_method_change(self, event):
        """Handle costing method change."""
        current_user = get_username()
        if not permissions.has_permission(current_user, 'manage_settings'):
            messagebox.showerror("Permission Denied",
                                 "You do not have permission to change inventory settings.")
            # Revert to current method
            current = get_costing_method()
            self.costing_method_var.set(current.value)
            return

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
                # Bind Ctrl+S to save information
                self.bind_all("<Control-s>", lambda e: self._save_form_information())
                self.bind_all("<Control-S>", lambda e: self._save_form_information())
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
