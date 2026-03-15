"""Modern Sales Reporting UI with Enhanced Design."""

from __future__ import annotations
from typing import Dict, Any
from utils.security import get_username
from utils.i18n import get_currency_symbol
from utils import set_window_icon
from utils.date_utils import format_date, format_date_storage, get_tkcalendar_date_pattern
from modules import permissions

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import tkcalendar
import threading
import logging
import os
import json

from .reports_constants import (
    WINDOW_PADDING, HEADER_PADDING, CARD_PADDING, BUTTON_PADDING, ACTION_BUTTON_PADDING,
    COLORS, STYLES, REPORT_TYPES, DATE_PRESETS, EXPORT_FORMATS, FILE_EXTENSIONS,
    GRID_COLUMNS, FONT_SIZES, ERROR_MESSAGES, SIDEBAR_WIDTH, REPORT_CATEGORIES, SIDEBAR_PADDING
)
from .reports_controller import ReportController as ReportService
from .reports_export import ExportManager
from .reports_pagination import ReportPaginator
from .reports_formatters import (
    SalesTextFormatter, ProfitTextFormatter, CategoryTextFormatter,
    PaymentMethodsTextFormatter, VoidedSalesTextFormatter, SalesLogTextFormatter,
    TransactionsTextFormatter, TrendsTextFormatter
)
from .reports_reconciliation_formatters import (
    ReconciliationSummaryTextFormatter, ReconciliationDetailsTextFormatter
)
from .reports_inventory_formatters import (
    InventoryStockLevelsTextFormatter, InventoryLowStockTextFormatter, InventoryValueTextFormatter,
    InventoryStockMovementTextFormatter
)

from .reports_base import ReportData, BaseReportFrame

# Set up logging
logger = logging.getLogger(__name__)


def setup_report_styles(style: ttk.Style) -> None:
    """Configure all custom styles for the reports module."""
    # Frame styles
    style.configure('Reports.Card.TLabelframe', 
                   background=COLORS['surface'],
                   borderwidth=1,
                   relief='solid')
    style.configure('Reports.Card.TLabelframe.Label',
                   background=COLORS['surface'],
                   foreground=COLORS['text'],
                   font=('Segoe UI', FONT_SIZES['subheader'], 'bold'))
    
    style.configure('Reports.Sidebar.TFrame',
                   background=COLORS['sidebar_bg'])
    
    style.configure('Reports.Content.TFrame',
                   background=COLORS['background'])
    
    # Button styles - white surface, neutral text + border
    style.configure('Reports.Primary.TButton',
                   background=COLORS['surface'],
                   foreground=COLORS['text'],
                   font=('Segoe UI', 10),
                   padding=(12, 6),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=COLORS['border'],
                   lightcolor=COLORS['surface'],
                   darkcolor=COLORS['border'])
    style.map('Reports.Primary.TButton',
             background=[('disabled', COLORS.get('disabled_bg', COLORS['border'])),
                         ('!disabled', COLORS['surface'])],
             foreground=[('disabled', COLORS.get('text_light', '#9ca3af')),
                         ('!disabled', COLORS['text'])],
             bordercolor=[('!disabled', COLORS['border'])],
             lightcolor=[('!disabled', COLORS['surface'])],
             darkcolor=[('!disabled', COLORS['border'])])
    
    style.configure('Reports.Secondary.TButton',
                   background=COLORS.get('neutral_bg', COLORS['border']),
                   foreground=COLORS['text'],
                   font=('Segoe UI', 10),
                   padding=(10, 5),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=COLORS['border'],
                   lightcolor=COLORS['surface'],
                   darkcolor=COLORS.get('neutral_bg', COLORS['border']))
    style.map('Reports.Secondary.TButton',
             background=[('disabled', COLORS.get('disabled_bg', COLORS['border'])),
                         ('!disabled', COLORS.get('neutral_bg', COLORS['border']))],
             foreground=[('disabled', COLORS.get('text_light', '#9ca3af')),
                         ('!disabled', COLORS['text'])],
             lightcolor=[('!disabled', COLORS['surface'])],
             darkcolor=[('!disabled', COLORS.get('neutral_bg', COLORS['border']))])
    
    style.configure('Reports.Action.TButton',
                   background=COLORS['surface'],
                   foreground=COLORS['text'],
                   font=('Segoe UI', 9),
                   padding=(8, 4),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=COLORS['border'],
                   lightcolor=COLORS['surface'],
                   darkcolor=COLORS['border'])
    style.map('Reports.Action.TButton',
             background=[('disabled', COLORS.get('disabled_bg', COLORS['border'])),
                         ('!disabled', COLORS['surface'])],
             foreground=[('disabled', COLORS.get('text_light', '#9ca3af')),
                         ('!disabled', COLORS['text'])],
             bordercolor=[('!disabled', COLORS['border'])],
             lightcolor=[('!disabled', COLORS['surface'])],
             darkcolor=[('!disabled', COLORS['border'])])
    
    style.configure('Reports.Sidebar.TButton',
                   background=COLORS['sidebar_bg'],
                   foreground=COLORS['sidebar_text'],
                   font=('Segoe UI', FONT_SIZES['sidebar_item']),
                   padding=(12, 8),
                   anchor='w',
                   bordercolor=COLORS['sidebar_bg'],
                   lightcolor=COLORS['sidebar_hover'],
                   darkcolor=COLORS['sidebar_bg'])
    style.map('Reports.Sidebar.TButton',
             background=[('pressed', COLORS['sidebar_hover']),
                         ('active', COLORS['sidebar_hover']),
                         ('!disabled', COLORS['sidebar_bg'])],
             foreground=[('!disabled', COLORS['sidebar_text'])],
             lightcolor=[('!disabled', COLORS['sidebar_hover'])],
             darkcolor=[('!disabled', COLORS['sidebar_bg'])])
    
    style.configure('Reports.SidebarActive.TButton',
                   background=COLORS['sidebar_active'],
                   foreground=COLORS['sidebar_text'],
                   font=('Segoe UI', FONT_SIZES['sidebar_item'], 'bold'),
                   padding=(12, 8),
                   anchor='w',
                   bordercolor=COLORS['sidebar_active'],
                   lightcolor=COLORS['sidebar_hover'],
                   darkcolor=COLORS['sidebar_active'])
    style.map('Reports.SidebarActive.TButton',
             background=[('pressed', COLORS['sidebar_hover']),
                         ('active', COLORS['sidebar_hover']),
                         ('!disabled', COLORS['sidebar_active'])],
             foreground=[('!disabled', COLORS['sidebar_text'])],
             lightcolor=[('!disabled', COLORS['sidebar_hover'])],
             darkcolor=[('!disabled', COLORS['sidebar_active'])])
    
    # Label styles
    style.configure('Reports.Header.TLabel',
                   font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                   foreground=COLORS['text'])
    
    style.configure('Reports.Subheader.TLabel',
                   font=('Segoe UI', FONT_SIZES['subheader'], 'bold'),
                   foreground=COLORS['text'])
    
    style.configure('Reports.Body.TLabel',
                   font=('Segoe UI', FONT_SIZES['body']),
                   foreground=COLORS['text'])
    
    style.configure('Reports.Caption.TLabel',
                   font=('Segoe UI', FONT_SIZES['caption']),
                   foreground=COLORS['text_light'])
    
    style.configure('Reports.MetricValue.TLabel',
                   font=('Segoe UI', FONT_SIZES['large_value'], 'bold'),
                   foreground=COLORS['primary'])
    
    style.configure('Reports.MetricLabel.TLabel',
                   font=('Segoe UI', FONT_SIZES['caption']),
                   foreground=COLORS['text_secondary'])
    
    style.configure('Reports.SidebarLabel.TLabel',
                   font=('Segoe UI', FONT_SIZES['sidebar_item']),
                   foreground=COLORS['sidebar_text'],
                   background=COLORS['sidebar_bg'])
    
    style.configure('Reports.SidebarTitle.TLabel',
                   font=('Segoe UI', FONT_SIZES['sidebar_title'], 'bold'),
                   foreground=COLORS['sidebar_text'],
                   background=COLORS['sidebar_bg'])
    
    # Treeview styles
    style.configure('Reports.Treeview',
                   font=('Segoe UI', FONT_SIZES['body']),
                   rowheight=28,
                   background=COLORS['surface'],
                   fieldbackground=COLORS['surface'],
                   foreground=COLORS['text'])
    
    style.configure('Reports.Treeview.Heading',
                   font=('Segoe UI', FONT_SIZES['body'], 'bold'),
                   background=COLORS['table_header'],
                   foreground=COLORS['text'])
    
    style.map('Reports.Treeview',
             background=[('selected', COLORS['primary_light'])],
             foreground=[('selected', COLORS['text'])])


class ModernReportsFrame(BaseReportFrame):
    """Modern reports UI frame (card-based)."""

    def __init__(self, parent: tk.Misc, *, on_home: callable | None = None, **kwargs):
        # store before base call since header building may reference it
        self.on_home = on_home
        # call base which sets up service, vars, frames etc - skip default UI
        super().__init__(parent, service=ReportService(), skip_default_ui=True, **kwargs)
        
        # Setup custom styles
        style = ttk.Style()
        setup_report_styles(style)

        # Default date range: last 30 days
        self.start_date.set(format_date(datetime.now() - timedelta(days=30)))
        self.end_date.set(format_date(datetime.now()))

        self.selected_category = tk.StringVar(value='overview')
        self.report_type = tk.StringVar(value='overview')
        self.reconciliation_status = tk.StringVar(value='all')
        self._date_preset_popup = None
        self._modal_dialogs: set = set()
        self._popup_page = None
        self._sidebar_buttons: dict = {}

        # Frame padding and initial UI build
        self.configure(padding=WINDOW_PADDING)
        self.columnconfigure(0, minsize=SIDEBAR_WIDTH)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        
        self._build_header()
        self._build_sidebar(self)
        self._build_report_area(self)

    def _build_sidebar(self, parent) -> None:
        """Build the sidebar navigation panel."""
        # Create sidebar container
        self.sidebar_frame = tk.Frame(parent, bg=COLORS['sidebar_bg'], width=SIDEBAR_WIDTH)
        self.sidebar_frame.grid(row=1, column=0, sticky=tk.NS, padx=(0, 15))
        self.sidebar_frame.grid_propagate(False)
        
        # Sidebar title
        title_frame = tk.Frame(self.sidebar_frame, bg=COLORS['sidebar_bg'])
        title_frame.pack(fill=tk.X, padx=SIDEBAR_PADDING[0], pady=(15, 20))
        
        tk.Label(title_frame, text="📊 Reports", 
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['sidebar_bg'], fg=COLORS['sidebar_text']).pack(anchor=tk.W)
        
        # Separator
        sep = tk.Frame(self.sidebar_frame, bg=COLORS['sidebar_hover'], height=1)
        sep.pack(fill=tk.X, padx=SIDEBAR_PADDING[0], pady=(0, 10))
        
        # Category buttons
        categories = [
            ('overview', '📊', 'Overview', self._show_overview),
            ('sales', '💰', 'Sales Reports', self._show_sales_category),
            ('financial', '💼', 'Financial', self._show_financial_category),
            ('inventory', '📦', 'Inventory', self._show_inventory_category),
            ('reconciliation', '🔄', 'Reconciliation', self._show_reconciliation_category),
            ('purchase_orders', '📋', 'Purchase Orders', self._show_purchase_orders_category),
        ]
        
        self._sidebar_buttons = {}
        
        for cat_id, icon, label, command in categories:
            btn_frame = tk.Frame(self.sidebar_frame, bg=COLORS['sidebar_bg'])
            btn_frame.pack(fill=tk.X, padx=SIDEBAR_PADDING[0], pady=2)
            
            is_selected = self.selected_category.get() == cat_id
            bg_color = COLORS['sidebar_active'] if is_selected else COLORS['sidebar_bg']
            fg_color = COLORS['text_white'] if is_selected else COLORS['sidebar_text']
            
            btn = tk.Label(btn_frame, text=f"  {icon}  {label}",
                          font=('Segoe UI', FONT_SIZES['sidebar_item'], 'bold' if is_selected else 'normal'),
                          bg=bg_color, fg=fg_color,
                          anchor='w', padx=10, pady=8, cursor='hand2')
            btn.pack(fill=tk.X)
            
            # Bind events
            def on_enter(e, b=btn, c=cat_id):
                if self.selected_category.get() != c:
                    b.configure(bg=COLORS['sidebar_hover'], fg=COLORS['sidebar_text'])
            
            def on_leave(e, b=btn, c=cat_id):
                if self.selected_category.get() != c:
                    b.configure(bg=COLORS['sidebar_bg'], fg=COLORS['sidebar_text'])
                else:
                    b.configure(bg=COLORS['sidebar_active'], fg=COLORS['text_white'])
            
            def on_click(e, c=cat_id, cmd=command):
                self._select_category(c, cmd)
            
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
            btn.bind('<Button-1>', on_click)
            
            self._sidebar_buttons[cat_id] = btn
        
        # Add some spacing before the help section
        spacer = tk.Frame(self.sidebar_frame, bg=COLORS['sidebar_bg'])
        spacer.pack(fill=tk.BOTH, expand=True)
        
        # Help/Info section at bottom
        help_frame = tk.Frame(self.sidebar_frame, bg=COLORS['sidebar_hover'])
        help_frame.pack(fill=tk.X, padx=SIDEBAR_PADDING[0], pady=SIDEBAR_PADDING[1], side=tk.BOTTOM)
        
        tk.Label(help_frame, text="💡 Tip: Click a report button",
                font=('Segoe UI', 8), bg=COLORS['sidebar_hover'], 
                fg=COLORS['text_muted']).pack(anchor=tk.W, padx=8, pady=4)
        tk.Label(help_frame, text="to select date range options",
                font=('Segoe UI', 8), bg=COLORS['sidebar_hover'], 
                fg=COLORS['text_muted']).pack(anchor=tk.W, padx=8, pady=(0, 4))

    def _update_sidebar_selection(self) -> None:
        """Update sidebar button styles based on current selection."""
        selected = self.selected_category.get()
        for cat_id, btn in self._sidebar_buttons.items():
            if cat_id == selected:
                btn.configure(bg=COLORS['sidebar_active'], fg=COLORS['text_white'],
                            font=('Segoe UI', FONT_SIZES['sidebar_item'], 'bold'))
            else:
                btn.configure(bg=COLORS['sidebar_bg'], fg=COLORS['sidebar_text'],
                            font=('Segoe UI', FONT_SIZES['sidebar_item'], 'normal'))

    def _build_report_area(self, parent) -> None:
        """Build the main report display area."""
        self.report_container = ttk.Frame(parent, style=STYLES['frame'])
        self.report_container.grid(row=1, column=1, sticky=tk.NSEW)
        self.report_container.columnconfigure(0, weight=1)
        self.report_container.rowconfigure(0, weight=1)

        # Loading indicator
        self.loading_frame = ttk.Frame(self.report_container, style=STYLES['frame'])
        self.loading_label = ttk.Label(self.loading_frame, text="⏳ Loading report...",
                                     style=STYLES['subheader_label'])
        self.progress_bar = ttk.Progressbar(self.loading_frame, mode='indeterminate')

        # Report content area
        self.content_frame = ttk.Frame(self.report_container, style=STYLES['frame'])
        self.content_frame.grid(row=0, column=0, sticky=tk.NSEW)

        # Initialize with overview
        self._show_overview()

    def _select_category(self, category: str, command) -> None:
        """Handle category selection."""
        # Check if there are any open modal dialogs
        if self._has_open_modal_dialogs():
            # Don't allow category switching while modals are open
            return
        
        # Close any open date popup when switching pages
        self._clear_date_popup_tracking()
        self.selected_category.set(category)
        self._rebuild_sidebar()
        command()

    def _rebuild_sidebar(self) -> None:
        """Update sidebar to reflect current selection."""
        self._update_sidebar_selection()

    def _show_overview(self) -> None:
        """Show the overview dashboard with key metrics."""
        self._clear_report_area()
        self._generate_overview_data()

    def _create_overview_header(self) -> None:
        """Create the overview header section."""
        header = tk.Frame(self.content_frame, bg=COLORS['background'])
        header.pack(fill=tk.X, pady=(0, 20))
        
        # Title with welcome message
        title_frame = tk.Frame(header, bg=COLORS['background'])
        title_frame.pack(fill=tk.X)
        
        tk.Label(title_frame, text="📈 Business Overview", 
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(side=tk.LEFT)
        
        # Current date
        date_label = tk.Label(title_frame, text=format_date(datetime.now()),
                             font=('Segoe UI', FONT_SIZES['body']),
                             bg=COLORS['background'], fg=COLORS['text_secondary'])
        date_label.pack(side=tk.RIGHT)

    def _create_overview_metrics_container(self) -> None:
        """Create the container for overview metrics cards."""
        self.metrics_frame = tk.Frame(self.content_frame, bg=COLORS['background'])
        self.metrics_frame.pack(fill=tk.X, pady=(0, 20))

    def _generate_overview_data(self) -> None:
        """Generate and display overview data asynchronously."""
        # Generate overview data and let the polling loop deliver the result on the main thread
        from utils.date_utils import format_date_db
        today = format_date_db(datetime.now())
        request_id = self.service.generate_report_async('overview', today, today, None)
        # track active request so the poller will deliver it
        self.current_request_id = request_id

        # Check immediately for cached results
        self._poll_report_results()

    def _display_overview_metrics(self, metadata: Dict[str, Any]) -> None:
        """Display the overview metrics in modern cards."""
        # Clear any remaining loading widgets
        self._clear_report_area()
        
        # Create header and metrics container
        self._create_overview_header()
        
        # Key Metrics section header
        metrics_header = tk.Frame(self.content_frame, bg=COLORS['background'])
        metrics_header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(metrics_header, text="📊 Key Metrics",
                font=('Segoe UI', FONT_SIZES['subheader'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(anchor=tk.W)
        
        self._create_overview_metrics_container()
        
        currency_symbol = get_currency_symbol()

        today_revenue = metadata.get('today_revenue', 0)
        today_transactions = metadata.get('today_transactions', 0)
        week_revenue = metadata.get('week_revenue', 0)
        growth_rate = metadata.get('growth_rate', 0)
        
        # Determine growth color
        growth_color = COLORS['success'] if growth_rate >= 0 else COLORS['danger']

        # Create 4-column grid for metrics
        metrics = [
            ("💵", "Today's Revenue", f"{currency_symbol}{today_revenue:,.2f}", COLORS['success']),
            ("🛒", "Transactions", str(today_transactions), COLORS['info']),
            ("📊", "Week Revenue", f"{currency_symbol}{week_revenue:,.2f}", COLORS['primary']),
            ("📈", "Growth Rate", f"{growth_rate:+.1f}%", growth_color),
        ]
        
        for i, (icon, title, value, color) in enumerate(metrics):
            self._create_metric_card(self.metrics_frame, icon, title, value, color, 0, i)

        # Quick Actions section
        actions_container = tk.Frame(self.content_frame, bg=COLORS['background'])
        actions_container.pack(fill=tk.X, pady=(10, 0))
        
        # Section header
        tk.Label(actions_container, text="⚡ Quick Actions",
                font=('Segoe UI', FONT_SIZES['subheader'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(anchor=tk.W, pady=(0, 15))

        # Actions grid
        actions_frame = tk.Frame(actions_container, bg=COLORS['background'])
        actions_frame.pack(fill=tk.X)

        actions = [
            ("📊", "Sales Report", "daily", COLORS['primary']),
            ("💰", "Profit Analysis", "profit", COLORS['success']),
            ("📦", "Inventory Status", "inventory_stock_levels", COLORS['warning']),
            ("🔄", "Reconciliation", "reconciliation_summary", COLORS['info']),
        ]

        for i, (icon, text, report_type, color) in enumerate(actions):
            btn_frame = tk.Frame(actions_frame, bg=COLORS['surface'], 
                               relief='flat', borderwidth=1,
                               highlightbackground=COLORS['border'],
                               highlightthickness=1)
            btn_frame.grid(row=0, column=i, sticky=tk.NSEW, padx=(0, 15) if i < 3 else 0)
            btn_frame.configure(cursor='hand2')
            
            inner = tk.Frame(btn_frame, bg=COLORS['surface'])
            inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
            
            tk.Label(inner, text=icon, font=('Segoe UI', 20),
                    bg=COLORS['surface'], fg=color).pack(anchor=tk.W)
            tk.Label(inner, text=text, font=('Segoe UI', FONT_SIZES['body'], 'bold'),
                    bg=COLORS['surface'], fg=COLORS['text']).pack(anchor=tk.W, pady=(5, 0))
            
            # Bind click events to the frame and all children
            def bind_click(widget, rt=report_type):
                widget.bind('<Button-1>', lambda e, r=rt: self._on_action_click(r))
                widget.bind('<Enter>', lambda e, w=btn_frame: w.configure(bg=COLORS['primary_light']))
                widget.bind('<Leave>', lambda e, w=btn_frame: w.configure(bg=COLORS['surface']))
                for child in widget.winfo_children():
                    bind_click(child, rt)
            
            bind_click(btn_frame, report_type)
            
        for i in range(4):
            actions_frame.grid_columnconfigure(i, weight=1)

    def _on_action_click(self, report_type: str) -> None:
        """Handle quick action button click."""
        self._show_date_preset_popup(report_type)

    def _create_metric_card(self, parent, icon: str, title: str, value: str, 
                           accent_color: str, row: int, col: int) -> None:
        """Create a modern metric card with accent color."""
        # Card container
        card = tk.Frame(parent, bg=COLORS['surface'], relief='flat',
                       highlightbackground=COLORS['border'], highlightthickness=1)
        card.grid(row=row, column=col, sticky=tk.NSEW, 
                 padx=(0, 15) if col < 3 else 0, pady=5)
        
        # Inner content with padding
        inner = tk.Frame(card, bg=COLORS['surface'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        # Icon and title row
        header_frame = tk.Frame(inner, bg=COLORS['surface'])
        header_frame.pack(fill=tk.X)
        
        tk.Label(header_frame, text=icon, font=('Segoe UI', 16),
                bg=COLORS['surface'], fg=accent_color).pack(side=tk.LEFT)
        tk.Label(header_frame, text=title, font=('Segoe UI', FONT_SIZES['caption']),
                bg=COLORS['surface'], fg=COLORS['text_secondary']).pack(side=tk.LEFT, padx=(8, 0))
        
        # Value
        tk.Label(inner, text=value, font=('Segoe UI', FONT_SIZES['large_value'], 'bold'),
                bg=COLORS['surface'], fg=accent_color).pack(anchor=tk.W, pady=(8, 0))
        
        parent.grid_columnconfigure(col, weight=1)

    def _create_report_button_card(self, parent, icon: str, title: str, 
                                    report_type: str, description: str = "",
                                    accent_color: str = None) -> tk.Frame:
        """Create a modern report button card."""
        if accent_color is None:
            accent_color = COLORS['primary']
        
        card = tk.Frame(parent, bg=COLORS['surface'], relief='flat',
                       highlightbackground=COLORS['border'], highlightthickness=1,
                       cursor='hand2')
        
        inner = tk.Frame(card, bg=COLORS['surface'])
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        # Icon
        tk.Label(inner, text=icon, font=('Segoe UI', 24),
                bg=COLORS['surface'], fg=accent_color).pack(anchor=tk.W)
        
        # Title
        tk.Label(inner, text=title, font=('Segoe UI', FONT_SIZES['body'], 'bold'),
                bg=COLORS['surface'], fg=COLORS['text']).pack(anchor=tk.W, pady=(8, 2))
        
        # Description
        if description:
            tk.Label(inner, text=description, font=('Segoe UI', FONT_SIZES['caption']),
                    bg=COLORS['surface'], fg=COLORS['text_muted'],
                    wraplength=150).pack(anchor=tk.W)
        
        # Hover effects
        def on_enter(e):
            card.configure(highlightbackground=accent_color, highlightthickness=2)
        
        def on_leave(e):
            card.configure(highlightbackground=COLORS['border'], highlightthickness=1)
        
        def on_click(e):
            self._show_date_preset_popup(report_type)
        
        # Bind to card and all children
        def bind_events(widget):
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
            widget.bind('<Button-1>', on_click)
            for child in widget.winfo_children():
                bind_events(child)
        
        bind_events(card)
        return card

    def _show_sales_category(self) -> None:
        """Show sales-related reports."""
        self._clear_report_area()
        
        # Header
        header = tk.Frame(self.content_frame, bg=COLORS['background'])
        header.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(header, text="💰 Sales Reports",
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(side=tk.LEFT)
        
        tk.Label(header, text="Track and analyze your sales performance",
                font=('Segoe UI', FONT_SIZES['body']),
                bg=COLORS['background'], fg=COLORS['text_secondary']).pack(side=tk.RIGHT)

        # Reports grid
        reports_frame = tk.Frame(self.content_frame, bg=COLORS['background'])
        reports_frame.pack(fill=tk.BOTH, expand=True)

        sales_reports = [
            ("📅", "Daily Sales", "daily", "View today's sales", COLORS['primary']),
            ("📆", "Date Range", "range", "Sales by date range", COLORS['info']),
            ("🏆", "Best Sellers", "bestsellers", "Top selling items", COLORS['success']),
            ("📊", "By Category", "category", "Sales by category", COLORS['warning']),
            ("💳", "Payment Methods", "payment_methods", "Payment breakdown", COLORS['accent']),
            ("📈", "Trends", "trends", "Sales trends over time", COLORS['chart_5']),
            ("❌", "Voided Sales", "voided", "Cancelled transactions", COLORS['danger']),
            ("📝", "Sales Log", "sales_log", "Detailed transaction log", COLORS['secondary']),
        ]

        for i, (icon, title, report_type, desc, color) in enumerate(sales_reports):
            row, col = divmod(i, 4)
            card = self._create_report_button_card(reports_frame, icon, title, 
                                                   report_type, desc, color)
            card.grid(row=row, column=col, sticky=tk.NSEW, 
                     padx=(0, 15) if col < 3 else 0, pady=(0, 15))
        
        for col in range(4):
            reports_frame.grid_columnconfigure(col, weight=1)
        for row in range(2):
            reports_frame.grid_rowconfigure(row, weight=1)

    def _show_financial_category(self) -> None:
        """Show financial reports."""
        self._clear_report_area()
        
        # Header
        header = tk.Frame(self.content_frame, bg=COLORS['background'])
        header.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(header, text="💼 Financial Reports",
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(side=tk.LEFT)
        
        tk.Label(header, text="Financial analysis and profit tracking",
                font=('Segoe UI', FONT_SIZES['body']),
                bg=COLORS['background'], fg=COLORS['text_secondary']).pack(side=tk.RIGHT)

        # Reports grid
        reports_frame = tk.Frame(self.content_frame, bg=COLORS['background'])
        reports_frame.pack(fill=tk.BOTH, expand=True)

        financial_reports = [
            ("💰", "Profit Analysis", "profit", "Revenue & profit margins", COLORS['success']),
            ("📊", "Transactions", "transactions", "All transactions summary", COLORS['primary']),
            ("📈", "Revenue Trends", "trends", "Trend analysis over time", COLORS['info']),
        ]

        for i, (icon, title, report_type, desc, color) in enumerate(financial_reports):
            card = self._create_report_button_card(reports_frame, icon, title,
                                                   report_type, desc, color)
            card.grid(row=0, column=i, sticky=tk.NSEW, 
                     padx=(0, 15) if i < 2 else 0, pady=(0, 15))
        
        for col in range(3):
            reports_frame.grid_columnconfigure(col, weight=1)

    def _show_inventory_category(self) -> None:
        """Show inventory reports."""
        self._clear_report_area()
        
        # Header
        header = tk.Frame(self.content_frame, bg=COLORS['background'])
        header.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(header, text="📦 Inventory Reports",
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(side=tk.LEFT)
        
        tk.Label(header, text="Monitor stock levels and inventory value",
                font=('Segoe UI', FONT_SIZES['body']),
                bg=COLORS['background'], fg=COLORS['text_secondary']).pack(side=tk.RIGHT)

        # Reports grid
        reports_frame = tk.Frame(self.content_frame, bg=COLORS['background'])
        reports_frame.pack(fill=tk.BOTH, expand=True)

        inventory_reports = [
            ("📊", "Stock Levels", "inventory_stock_levels", "Current stock quantities", COLORS['primary']),
            ("⚠️", "Low Stock", "inventory_low_stock", "Items below threshold", COLORS['warning']),
            ("💰", "Inventory Value", "inventory_value", "Total inventory valuation", COLORS['success']),
            ("📈", "Stock Movement", "inventory_stock_movement", "How items are selling", COLORS['info']),
        ]

        for i, (icon, title, report_type, desc, color) in enumerate(inventory_reports):
            card = self._create_report_button_card(reports_frame, icon, title,
                                                   report_type, desc, color)
            card.grid(row=0, column=i, sticky=tk.NSEW, 
                     padx=(0, 15) if i < 2 else 0, pady=(0, 15))
        
        for col in range(3):
            reports_frame.grid_columnconfigure(col, weight=1)

    def _show_reconciliation_category(self) -> None:
        """Show reconciliation reports."""
        self._clear_report_area()
        
        # Header
        header = tk.Frame(self.content_frame, bg=COLORS['background'])
        header.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(header, text="🔄 Reconciliation Reports",
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(side=tk.LEFT)
        
        tk.Label(header, text="Cash and sales reconciliation tracking",
                font=('Segoe UI', FONT_SIZES['body']),
                bg=COLORS['background'], fg=COLORS['text_secondary']).pack(side=tk.RIGHT)

        # Reports grid
        reports_frame = tk.Frame(self.content_frame, bg=COLORS['background'])
        reports_frame.pack(fill=tk.BOTH, expand=True)

        reconciliation_reports = [
            ("📋", "Summary", "reconciliation_summary", "Overview of reconciliations", COLORS['primary']),
            ("📄", "Details", "reconciliation_details", "Detailed session data", COLORS['info']),
        ]

        for i, (icon, title, report_type, desc, color) in enumerate(reconciliation_reports):
            card = self._create_report_button_card(reports_frame, icon, title,
                                                   report_type, desc, color)
            card.grid(row=0, column=i, sticky=tk.NSEW, 
                     padx=(0, 15) if i < 1 else 0, pady=(0, 15))
        
        for col in range(2):
            reports_frame.grid_columnconfigure(col, weight=1)

    def _show_purchase_orders_category(self) -> None:
        """Show Purchase Order reports."""
        self._clear_report_area()

        header = tk.Frame(self.content_frame, bg=COLORS['background'])
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(header, text="📋 Purchase Order Reports",
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text']).pack(side=tk.LEFT)

        tk.Label(header, text="Analyze supplier spending and order history",
                font=('Segoe UI', FONT_SIZES['body']),
                bg=COLORS['background'], fg=COLORS['text_secondary']).pack(side=tk.RIGHT)

        reports_frame = tk.Frame(self.content_frame, bg=COLORS['background'])
        reports_frame.pack(fill=tk.BOTH, expand=True)

        po_reports = [
            ("📄", "PO Summary", "po_summary", "All orders with status & totals", COLORS['primary']),
            ("🏭", "By Supplier", "po_by_supplier", "Spending aggregated per supplier", COLORS['success']),
            ("📦", "Items Detail", "po_items_detail", "Line-by-line breakdown of all POs", COLORS['info']),
        ]

        for i, (icon, title, report_type, desc, color) in enumerate(po_reports):
            card = self._create_report_button_card(reports_frame, icon, title,
                                                   report_type, desc, color)
            card.grid(row=0, column=i, sticky=tk.NSEW,
                     padx=(0, 15) if i < 2 else 0, pady=(0, 15))

        for col in range(3):
            reports_frame.grid_columnconfigure(col, weight=1)

    def _next_page(self) -> None:
        """Go to next page and refresh display."""
        if self.paginator.next_page():
            self._refresh_current_report()

    def _prev_page(self) -> None:
        """Go to previous page and refresh display."""
        if self.paginator.prev_page():
            self._refresh_current_report()

    def _refresh_current_report(self) -> None:
        """Refresh the current report display with current pagination."""
        if self.current_report_data is not None:
            self._display_report(self.current_report_data, reset_pagination=False)
        else:
            # Fallback to regenerating if no stored data
            self._generate_report()

    def _poll_report_results(self) -> None:
        """Poll the service result queue and deliver results on the main thread."""
        try:
            while not self.service.result_queue.empty():
                try:
                    req_id, result = self.service.result_queue.get_nowait()
                except Exception:
                    break

                # Deliver result only if it matches the active request, otherwise ignore
                if getattr(self, 'current_request_id', None) and req_id == self.current_request_id:
                    try:
                        # Overview reports are special and render metrics
                        if result.report_type == 'overview':
                            self.hide_loading()
                            if result.metadata.get('error'):
                                self._show_error(result.metadata['error'])
                            else:
                                self._display_overview_metrics(result.metadata)
                        else:
                            self._display_report(result)
                    except Exception as e:
                        logger.exception(f"Failed to deliver report {req_id} from queue: {e}")
                    finally:
                        # Clear current request id since it has been handled
                        if getattr(self, 'current_request_id', None) == req_id:
                            self.current_request_id = None
                else:
                    # Fallback: if current_request_id is not set (or mismatched), try to match
                    # queued results to the UI's active report parameters (report type + date range).
                    try:
                        from utils.date_utils import parse_date_flexible, format_date_storage
                        ui_report_type = self.report_type.get()
                        # Convert UI display dates to ISO date strings for comparison
                        try:
                            ui_iso_start = format_date_storage(parse_date_flexible(self.start_date.get()).date())
                            ui_iso_end = format_date_storage(parse_date_flexible(self.end_date.get()).date())
                        except Exception:
                            ui_iso_start = ui_iso_end = None

                        # If the queued result matches the UI's active report and date range, deliver it
                        if result.report_type == ui_report_type and (ui_iso_start is None or (result.start_date == ui_iso_start and result.end_date == ui_iso_end)):
                            try:
                                if result.report_type == 'overview':
                                    self.hide_loading()
                                    if result.metadata.get('error'):
                                        self._show_error(result.metadata['error'])
                                    else:
                                        self._display_overview_metrics(result.metadata)
                                else:
                                    self._display_report(result)
                            except Exception as e:
                                logger.exception(f"Failed to deliver matched queued report {req_id}: {e}")
                            finally:
                                if getattr(self, 'current_request_id', None) == req_id:
                                    self.current_request_id = None
                        else:
                            logger.debug(f"Queued report {req_id} does not match current UI filters; ignoring for now")
                    except Exception:
                        logger.debug(f"Queued report {req_id} does not match current_request_id; ignoring for now")
        except Exception as e:
            logger.exception(f"Error while polling report results: {e}")
        finally:
            # Continue polling periodically
            try:
                self.after(200, self._poll_report_results)
            except Exception:
                # If scheduling fails, we can't poll; log and stop
                logger.exception("Failed to schedule report poll; stopping polling loop")

    # Click helpers: single click shows date preset popup, report generates after user selects preset
    def _on_report_click(self, event, report_type: str, widget) -> None:
        """On single click, open the date preset popup except for 'daily' reports.

        'daily' reports always use today's date so they generate immediately.
        """
        if report_type == 'daily':
            # Use today's date and generate immediately (no popup)
            self._set_today()
            self._generate_report_type(report_type)
            return

        # For other reports, show presets
        self._show_date_preset_popup(report_type)

    def _on_report_double_click(self, event, report_type: str) -> None:
        """Double-click behavior: for 'daily' generate immediately, otherwise show presets."""
        if report_type == 'daily':
            self._set_today()
            self._generate_report_type(report_type)
            return

        self._show_date_preset_popup(report_type)

    def _clear_report_area(self) -> None:
        """Clear the current report display area."""
        # More thorough clearing to ensure all widgets are destroyed
        for widget in self.content_frame.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass  # Ignore errors if widget is already destroyed

    def _generate_report_type(self, report_type: str) -> None:
        """Generate a specific report type."""
        self.report_type.set(report_type)
        self._generate_report()

    def _quick_generate_report(self, report_type: str) -> None:
        """Quick generate a report from overview."""
        self.report_type.set(report_type)
        self._generate_report()

    def _generate_report(self) -> None:
        """Generate the selected report with modern loading UI."""
        self.show_loading()

        # Generate report using controller
        report_type = self.report_type.get()
        
        # Set appropriate default date ranges for different report types
        historical_reports = ('reconciliation_summary', 'reconciliation_details', 'range', 'bestsellers', 
                            'profit', 'category', 'payment_methods', 'voided', 'sales_log', 
                            'transactions', 'trends', 'inventory_stock_levels', 'inventory_low_stock', 
                            'inventory_value', 'inventory_stock_movement', 'po_summary', 'po_by_supplier', 'po_items_detail')
        if report_type in historical_reports:
            # Historical reports default to last 30 days
            if not self._local_date_vars.get(report_type):
                today = datetime.now()
                start_date = format_date(today - timedelta(days=29))
                end_date = format_date(today)
                self.start_date.set(start_date)
                self.end_date.set(end_date)
        
        # Prefer per-report local dates/status when available
        local_dates = self._local_date_vars.get(report_type)
        start = local_dates[0].get() if local_dates else self.start_date.get()
        end = local_dates[1].get() if local_dates else self.end_date.get()
        status_var = self._local_status_vars.get(report_type)
        status_filter = status_var.get() if status_var else self.reconciliation_status.get()

        # Convert display dates to ISO format for processing
        from utils.date_utils import parse_date_flexible, format_date_storage
        try:
            start_dt = parse_date_flexible(start)
            end_dt = parse_date_flexible(end)
            iso_start = format_date_storage(start_dt.date())
            iso_end = format_date_storage(end_dt.date())
        except ValueError as e:
            self._show_error(f"Invalid date format: {e}")
            self.hide_loading()
            return

        def on_report_complete(report_data):
            """Callback when report generation is complete."""
            # Schedule UI updates on the main thread to avoid calling tkinter from worker threads
            def _deliver():
                # Guard against the frame/window being destroyed while the report generated
                if not getattr(self, 'winfo_exists', lambda: False)():
                    logger.debug("Report frame no longer exists; ignoring completed report callback.")
                    return
                try:
                    self._display_report(report_data)
                except Exception as e:
                    logger.exception(f"Failed to display report on main thread: {e}")
            try:
                self.after(0, _deliver)
            except Exception as e:
                logger.exception(f"Failed to schedule report display: {e}")

        try:
            self.current_request_id = self.service.generate_report_async(
                report_type, iso_start, iso_end, on_report_complete, status_filter
            )
        except Exception as e:
            logger.error(f"Error starting report generation: {e}")
            self._show_error(f"Failed to start report generation: {e}")

    def _generate_report_with_params(self, report_type: str, start_date: str, end_date: str, status_filter: str = "all") -> None:
        """Generate a report using explicit date/status parameters (per-report scope)."""
        self.show_loading()

        # Convert display dates to ISO format for processing
        from utils.date_utils import parse_date_flexible, format_date_storage
        try:
            start_dt = parse_date_flexible(start_date)
            end_dt = parse_date_flexible(end_date)
            iso_start = format_date_storage(start_dt.date())
            iso_end = format_date_storage(end_dt.date())
        except ValueError as e:
            self._show_error(f"Invalid date format: {e}")
            self.hide_loading()
            return

        def on_report_complete(report_data):
            # Schedule UI updates on the main thread to avoid calling tkinter from worker threads
            def _deliver():
                # Guard against the frame/window being destroyed while the report generated
                if not getattr(self, 'winfo_exists', lambda: False)():
                    logger.debug("Report frame no longer exists; ignoring completed report callback.")
                    return
                try:
                    self._display_report(report_data)
                except Exception as e:
                    logger.exception(f"Failed to display report on main thread: {e}")
            try:
                self.after(0, _deliver)
            except Exception as e:
                logger.exception(f"Failed to schedule report display: {e}")

        try:
            self.current_request_id = self.service.generate_report_async(
                report_type, iso_start, iso_end, on_report_complete, status_filter
            )
        except Exception as e:
            logger.error(f"Error starting report generation: {e}")
            self._show_error(f"Failed to start report generation: {e}")

    def _display_report(self, report_data, reset_pagination: bool = True) -> None:
        """Display the generated report with pagination support."""
        self.hide_loading()

        if report_data.metadata.get('error'):
            self._show_error(report_data.metadata['error'])
            return

        # Store current report data for refresh operations
        self.current_report_data = report_data

        # Clear current content
        self._clear_report_area()

        # Modern report header with title and date range
        header = tk.Frame(self.content_frame, bg=COLORS['background'])
        header.pack(fill=tk.X, pady=(0, 15))
        
        # Left side - Title and date range
        title_frame = tk.Frame(header, bg=COLORS['background'])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)

        report_title = REPORT_TYPES.get(report_data.report_type, report_data.report_type.title())
        title_label = tk.Label(title_frame, text=f"📊 {report_title}",
                font=('Segoe UI', FONT_SIZES['header'], 'bold'),
                bg=COLORS['background'], fg=COLORS['text'])
        title_label.pack(anchor=tk.W)
        
        # Date range subtitle – format ISO dates using the system date format setting
        try:
            _start_disp = format_date(report_data.start_date)
            _end_disp   = format_date(report_data.end_date)
        except Exception:
            _start_disp = report_data.start_date
            _end_disp   = report_data.end_date
        date_range_text = f"Period: {_start_disp} to {_end_disp}"
        tk.Label(title_frame, text=date_range_text,
                font=('Segoe UI', FONT_SIZES['body']),
                bg=COLORS['background'], fg=COLORS['text_secondary']).pack(anchor=tk.W)
        
        # Record count
        record_text = f"{report_data.record_count} records found"
        tk.Label(title_frame, text=record_text,
                font=('Segoe UI', FONT_SIZES['caption']),
                bg=COLORS['background'], fg=COLORS['text_light']).pack(anchor=tk.W, pady=(2, 0))

        # Data Management section (right-aligned) - Export and management actions
        if report_data.report_type != 'overview':
            mgmt_frame = tk.Frame(header, bg=COLORS['background'])
            mgmt_frame.pack(side=tk.RIGHT, anchor=tk.N)

            # Export menu button (CSV/Excel/PDF/Text)
            try:
                export_btn = tk.Menubutton(
                    mgmt_frame, text="📤 Export ▾", relief="raised",
                    font=('Segoe UI', 10),
                    bg=COLORS.get('neutral_bg', COLORS['border']),
                    fg=COLORS['text'],
                    activebackground=COLORS['border'],
                    activeforeground=COLORS['text'],
                    padx=10, pady=5, cursor='hand2',
                    bd=1,
                )
                export_menu = tk.Menu(
                    export_btn, tearoff=0,
                    bg=COLORS.get('surface', '#ffffff'),
                    fg=COLORS['text'],
                    activebackground=COLORS.get('neutral_bg', COLORS['border']),
                    activeforeground=COLORS['text'],
                    font=('Segoe UI', 10),
                )
                export_menu.add_command(label="CSV", command=lambda rd=report_data: self._export_report(rd, 'csv'))
                export_menu.add_command(label="Excel", command=lambda rd=report_data: self._export_report(rd, 'xlsx'))
                export_menu.add_command(label="PDF", command=lambda rd=report_data: self._export_report(rd, 'pdf'))
                export_menu.add_command(label="Text", command=lambda rd=report_data: self._export_report(rd, 'txt'))
                export_btn.config(menu=export_menu)
                export_btn.pack(side=tk.LEFT, padx=(0, 8))
            except Exception:
                # Fallback to simple buttons if Menubutton/menu unsupported
                ttk.Button(mgmt_frame, text="CSV", style=STYLES['action_button'], command=lambda rd=report_data: self._export_report(rd, 'csv')).pack(side=tk.LEFT, padx=(0, 4))
                ttk.Button(mgmt_frame, text="Excel", style=STYLES['action_button'], command=lambda rd=report_data: self._export_report(rd, 'xlsx')).pack(side=tk.LEFT, padx=(0, 4))
                ttk.Button(mgmt_frame, text="PDF", style=STYLES['action_button'], command=lambda rd=report_data: self._export_report(rd, 'pdf')).pack(side=tk.LEFT, padx=(0, 4))

            # Schedule export (opens scheduling dialog)
            ttk.Button(mgmt_frame, text="Schedule", style=STYLES['secondary_button'], command=lambda rd=report_data: self._open_schedule_dialog(rd)).pack(side=tk.LEFT, padx=(6,0))

            # Manage schedules
            ttk.Button(mgmt_frame, text="Manage", style=STYLES['secondary_button'], command=self._manage_schedules_dialog).pack(side=tk.LEFT, padx=(6,0))


        # Per-report filter area (status/date) for supported reports
        if report_data.report_type in ('reconciliation_summary', 'reconciliation_details'):
            filter_frame = ttk.Frame(self.content_frame, style=STYLES['frame'])
            filter_frame.pack(fill=tk.X, pady=(6, 8))

            # Status combobox (local to this report)
            status_var = tk.StringVar(value=report_data.metadata.get('status_filter', 'all') or 'all')
            self._local_status_vars[report_data.report_type] = status_var
            ttk.Label(filter_frame, text="Filter by Status:", style=STYLES['body_label']).pack(side=tk.LEFT, padx=(0, 10))
            status_combo = ttk.Combobox(filter_frame, textvariable=status_var,
                                        values=["all", "draft", "completed", "approved"],
                                        state="readonly", width=15)
            status_combo.pack(side=tk.LEFT)
            # regenerate when status changes; will use current report dates
            def _on_status_change(e, rt=report_data.report_type, sv=status_var, rd=report_data):
                self._generate_report_with_params(rt, rd.start_date, rd.end_date, sv.get())
            status_combo.bind('<<ComboboxSelected>>', _on_status_change)

            # Date range controls (per-report) - display only
            ttk.Label(filter_frame, text="Date Range:", style=STYLES['body_label']).pack(side=tk.LEFT, padx=(10, 4))
            try:
                from utils.date_utils import parse_date_flexible as _parse_date_flex
                start_display = format_date(_parse_date_flex(report_data.start_date))
                end_display = format_date(_parse_date_flex(report_data.end_date))
                date_range_text = f"{start_display} to {end_display}"
            except Exception:
                date_range_text = f"{report_data.start_date} to {report_data.end_date}"
            ttk.Label(filter_frame, text=date_range_text, style=STYLES['body_label'],
                     foreground=COLORS['text_light']).pack(side=tk.LEFT, padx=(0, 6))

        # Create report details card immediately so content is visible without extra clicks
        report_card = ttk.LabelFrame(self.content_frame, text=" Report Details ", style=STYLES['card'])
        report_card.pack(fill=tk.BOTH, expand=True)
        report_card.configure(padding=CARD_PADDING)

        # Attach report_card to the label so header handlers can toggle it
        title_label.report_card = report_card

        # Set up pagination and paginated data
        if reset_pagination:
            self.paginator.set_data(report_data.data)
        page_info = self.paginator.get_page_info()
        paginated_data = self.paginator.get_page(report_data.data)

        # if report type has custom UI, handle below; otherwise use generic table
        special_reports = ('inventory_stock_levels', 'sales_log', 'reconciliation_details')
        if report_data.report_type not in special_reports:
            # generic render inside report_card
            self.render_table(report_card, report_data.data)
            return

        # Pagination controls (only show if needed)
        if page_info['total_pages'] > 1:
            pagination_frame = ttk.Frame(report_card, style=STYLES['frame'])
            pagination_frame.pack(fill=tk.X, pady=(0, 10))

            # Determine appropriate label for total count based on report type
            if report_data.report_type in ('daily', 'range', 'bestsellers', 'sales_log'):
                # For sales reports, show both records and total units
                total_units = report_data.metadata.get('total_items', page_info['total_items'])
                current_records = len(paginated_data)
                display_text = f"Page {page_info['current_page']} of {page_info['total_pages']} (showing {current_records} of {page_info['total_items']} records, {total_units} total units)"
            else:
                total_count = page_info['total_items']
                total_label = "total items"
                current_items = len(paginated_data)
                display_text = f"Page {page_info['current_page']} of {page_info['total_pages']} (showing {current_items} of {total_count} {total_label})"
            
            ttk.Label(pagination_frame, text=display_text,
                      style=STYLES['caption_label']).pack(side=tk.LEFT)

            # Navigation buttons
            nav_frame = ttk.Frame(pagination_frame, style=STYLES['frame'])
            nav_frame.pack(side=tk.RIGHT)

            prev_btn = ttk.Button(nav_frame, text="◀ Prev", style=STYLES['action_button'],
                                command=self._prev_page, state=tk.NORMAL if page_info['has_prev'] else tk.DISABLED)
            prev_btn.pack(side=tk.LEFT, padx=(0, 5))

            next_btn = ttk.Button(nav_frame, text="Next ▶", style=STYLES['action_button'],
                                command=self._next_page, state=tk.NORMAL if page_info['has_next'] else tk.DISABLED)
            next_btn.pack(side=tk.LEFT)

        # Paged tabular views for certain large reports
        if report_data.report_type == 'inventory_stock_levels':
            # Create a Treeview table
            columns = ('item_id', 'name', 'category', 'quantity', 'unit', 'inventory_value', 'is_low_stock')
            tree = ttk.Treeview(report_card, columns=columns, show='headings', height=12)
            for col in columns:
                tree.heading(col, text=col.replace('_', ' ').title())
                tree.column(col, anchor=tk.W, width=120)
            tree.pack(fill=tk.BOTH, expand=True)

            # Paging controls (keyset pagination)
            paging_frame = ttk.Frame(report_card, style=STYLES['frame'])
            paging_frame.pack(fill=tk.X, pady=(6, 0))

            prev_btn = ttk.Button(paging_frame, text='◀ Prev', state=tk.DISABLED)
            prev_btn.pack(side=tk.LEFT)
            next_btn = ttk.Button(paging_frame, text='Next ▶')
            next_btn.pack(side=tk.LEFT, padx=(6, 0))
            page_info_label = ttk.Label(paging_frame, text='')
            page_info_label.pack(side=tk.LEFT, padx=(10, 0))

            # Paging state: history for keyset prev, current cursor, page size
            self._paging_state = {'cursor': None, 'page_size': 20, 'total': None, 'history': []}

            def load_page(cursor=None, push_history: bool = False):
                try:
                    rows, next_cursor, meta = self.service.generate_report_page(
                        report_data.report_type, report_data.start_date, report_data.end_date,
                        page_size=self._paging_state['page_size'], cursor=cursor, use_keyset=True
                    )

                    # update total
                    if 'total_items' in meta:
                        self._paging_state['total'] = meta['total_items']

                    # clear tree
                    for r in tree.get_children():
                        tree.delete(r)
                    for r in rows:
                        tree.insert('', tk.END, values=(r['item_id'], r['name'], r['category'], r['quantity'], r['unit'], f"{r['inventory_value']:.2f}", '⚠' if r['is_low_stock'] else ''))

                    # update history and cursor
                    if push_history:
                        # push previous cursor onto history for prev navigation
                        self._paging_state['history'].append(self._paging_state['cursor'])

                    self._paging_state['cursor'] = cursor

                    # configure buttons
                    prev_btn.config(state=tk.NORMAL if len(self._paging_state['history']) > 0 else tk.DISABLED)
                    next_btn.config(state=tk.NORMAL if next_cursor else tk.DISABLED)

                    # page info (keyset pagination shows page number approximate)
                    page_num = len(self._paging_state['history']) + 1
                    page_text = f"Page {page_num} ({len(rows)} rows) of {self._paging_state.get('total', '?')}"
                    page_info_label.config(text=page_text)

                    # attach next cursor token to next button
                    next_btn._next_cursor = next_cursor
                except Exception as e:
                    logger.error(f"Error loading inventory page: {e}")

            def on_next():
                # push current cursor to history and load next
                load_page(next_btn._next_cursor, push_history=True)

            def on_prev():
                # pop last cursor and load it
                prev_cursor = None
                if self._paging_state['history']:
                    prev_cursor = self._paging_state['history'].pop()
                load_page(prev_cursor, push_history=False)

            prev_btn.config(command=on_prev)
            next_btn.config(command=on_next)

            # Load first page (no history)
            load_page(None)

        elif report_data.report_type == 'sales_log':
            columns = ('transaction_id', 'receipt_number', 'date', 'time', 'amount', 'payment_method', 'items_summary')
            tree = ttk.Treeview(report_card, columns=columns, show='headings', height=12)
            for col in columns:
                tree.heading(col, text=col.replace('_', ' ').title())
                tree.column(col, anchor=tk.W, width=140)
            tree.pack(fill=tk.BOTH, expand=True)

            paging_frame = ttk.Frame(report_card, style=STYLES['frame'])
            paging_frame.pack(fill=tk.X, pady=(6, 0))

            prev_btn = ttk.Button(paging_frame, text='◀ Prev', state=tk.DISABLED)
            prev_btn.pack(side=tk.LEFT)
            next_btn = ttk.Button(paging_frame, text='Next ▶')
            next_btn.pack(side=tk.LEFT, padx=(6, 0))
            page_info_label = ttk.Label(paging_frame, text='')
            page_info_label.pack(side=tk.LEFT, padx=(10, 0))

            self._sales_paging = {'cursor': None, 'page_size': 20, 'history': [], 'total': None}

            def load_sales(cursor=None, push_history: bool = False):
                try:
                    rows, next_cursor, meta = self.service.generate_report_page(
                        'sales_log', report_data.start_date, report_data.end_date,
                        page_size=self._sales_paging['page_size'], cursor=cursor, use_keyset=True
                    )
                    # clear tree
                    for r in tree.get_children():
                        tree.delete(r)
                    for r in rows:
                        tree.insert('', tk.END, values=(r.get('transaction_id'), r.get('receipt_number'), format_date(r.get('date')), r.get('time'), f"{r.get('amount',0):.2f}" if r.get('amount') is not None else '', r.get('payment_method'), r.get('items_summary')))

                    if push_history:
                        self._sales_paging['history'].append(self._sales_paging['cursor'])

                    self._sales_paging['cursor'] = cursor
                    prev_btn.config(state=tk.NORMAL if len(self._sales_paging['history']) > 0 else tk.DISABLED)
                    next_btn.config(state=tk.NORMAL if next_cursor else tk.DISABLED)
                    next_btn._next_cursor = next_cursor

                    page_num = len(self._sales_paging['history']) + 1
                    page_info_label.config(text=f"Page {page_num} ({len(rows)} rows)")
                except Exception as e:
                    logger.error(f"Error loading sales page: {e}")

            prev_btn.config(command=lambda: load_sales(self._sales_paging['history'].pop() if self._sales_paging['history'] else None))
            next_btn.config(command=lambda: load_sales(next_btn._next_cursor, push_history=True))

            load_sales(None)

        elif report_data.report_type == 'reconciliation_details':
            columns = ('session_id', 'reconciliation_date', 'status', 'total_system_sales', 'total_actual_cash', 'total_variance')
            tree = ttk.Treeview(report_card, columns=columns, show='headings', height=12)
            for col in columns:
                tree.heading(col, text=col.replace('_', ' ').title())
                tree.column(col, anchor=tk.W, width=140)
            tree.pack(fill=tk.BOTH, expand=True)

            paging_frame = ttk.Frame(report_card, style=STYLES['frame'])
            paging_frame.pack(fill=tk.X, pady=(6, 0))

            prev_btn = ttk.Button(paging_frame, text='◀ Prev', state=tk.DISABLED)
            prev_btn.pack(side=tk.LEFT)
            next_btn = ttk.Button(paging_frame, text='Next ▶')
            next_btn.pack(side=tk.LEFT, padx=(6, 0))
            page_info_label = ttk.Label(paging_frame, text='')
            page_info_label.pack(side=tk.LEFT, padx=(10, 0))

            self._recon_paging = {'cursor': None, 'page_size': 20}

            # Message & action to display when no sessions match the selected filters (updated dynamically)
            no_data_frame = ttk.Frame(report_card, style=STYLES['frame'])
            no_data_label = ttk.Label(no_data_frame, text="", style=STYLES['body_label'])
            no_data_label.pack(side=tk.LEFT, padx=(0, 8))
            def _clear_filters_and_reload():
                # reset the metadata status filter to 'all' and reload current page
                report_data.metadata['status_filter'] = 'all'
                try:
                    load_recon(None)
                except Exception:
                    # If load_recon not yet defined, fallback to regenerating report
                    self._generate_report_with_params(report_data.report_type, report_data.start_date, report_data.end_date, 'all')
            clear_btn = ttk.Button(no_data_frame, text="Clear Filters", style=STYLES['secondary_button'], command=_clear_filters_and_reload)
            clear_btn.pack(side=tk.LEFT)

            def load_recon(cursor=None):
                try:
                    status_filter = report_data.metadata.get('status_filter', 'all')
                    rows, next_cursor, meta = self.service.generate_report_page(
                        'reconciliation_details', report_data.start_date, report_data.end_date,
                        page_size=self._recon_paging['page_size'], cursor=cursor, status_filter=status_filter, use_keyset=False
                    )

                    # Clear previous rows
                    for r in tree.get_children():
                        tree.delete(r)

                    # If rows empty, show friendly message and disable paging
                    if not rows:
                        # Ensure tree is hidden and message shown
                        try:
                            tree.pack_forget()
                        except Exception:
                            pass
                        from utils.date_utils import parse_date_flexible, format_date
                        try:
                            start_display = format_date(parse_date_flexible(report_data.start_date))
                            end_display = format_date(parse_date_flexible(report_data.end_date))
                            msg = f"No reconciliation sessions found for {start_display} to {end_display} with status '{status_filter}'."
                        except Exception:
                            msg = f"No reconciliation sessions found for {report_data.start_date} to {report_data.end_date} with status '{status_filter}'."
                        no_data_label.config(text=msg)
                        logger.info(msg)
                        if not no_data_frame.winfo_ismapped():
                            no_data_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))

                        prev_btn.config(state=tk.DISABLED)
                        next_btn.config(state=tk.DISABLED)
                        page_info_label.config(text="No sessions to display")

                        # Update paging state to reflect empty dataset
                        self._recon_paging['cursor'] = cursor
                        prev_btn._prev_cursor = None
                        next_btn._next_cursor = None
                        return

                    # We have rows: ensure table visible and message hidden
                    if no_data_frame.winfo_ismapped():
                        try:
                            no_data_frame.pack_forget()
                        except Exception:
                            pass
                    if not tree.winfo_ismapped():
                        tree.pack(fill=tk.BOTH, expand=True)

                    # Insert rows
                    for r in rows:
                        tree.insert('', tk.END, values=(r.session_id, format_date(r.reconciliation_date), r.status, f"{r.total_system_sales:.2f}", f"{r.total_actual_cash:.2f}", f"{r.total_variance:.2f}"))

                    # Update pagination controls
                    prev_btn.config(state=tk.NORMAL if cursor and cursor.isdigit() and int(cursor) > 0 else tk.DISABLED)
                    next_btn.config(state=tk.NORMAL if next_cursor else tk.DISABLED)
                    self._recon_paging['cursor'] = cursor
                    page_info_label.config(text=f"Showing {cursor or 0} - {int(cursor or 0) + len(rows)}")
                    prev_btn._prev_cursor = str(max(0, int(cursor or 0) - self._recon_paging['page_size'])) if cursor and cursor.isdigit() else None
                    next_btn._next_cursor = next_cursor
                except Exception as e:
                    logger.error(f"Error loading reconciliation page: {e}")
                    # On error, ensure the UI shows the table placeholder and an error message
                    try:
                        if no_data_label.winfo_ismapped():
                            no_data_label.pack_forget()
                    except Exception:
                        pass
                    try:
                        if not tree.winfo_ismapped():
                            tree.pack(fill=tk.BOTH, expand=True)
                    except Exception:
                        pass
                    prev_btn.config(state=tk.DISABLED)
                    next_btn.config(state=tk.DISABLED)
                    page_info_label.config(text="Error loading sessions")

            prev_btn.config(command=lambda: load_recon(prev_btn._prev_cursor))
            next_btn.config(command=lambda: load_recon(next_btn._next_cursor))

            load_recon(None)

        else:
            # Modern, parsed report rendering (replaces raw text widget)
            # - Removes ASCII boxing/separators
            # - Renders KPIs as cards, tabular sections as Treeviews and clean paragraphs
            text_frame = ttk.Frame(report_card, style=STYLES['frame'])
            text_frame.pack(fill=tk.BOTH, expand=True)

            # Scrollable canvas to host variable report content
            canvas = tk.Canvas(text_frame, bg=COLORS['background'], highlightthickness=0)
            vsb = ttk.Scrollbar(text_frame, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vsb.set)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            inner = tk.Frame(canvas, bg=COLORS['background'])
            canvas_window = canvas.create_window((0, 0), window=inner, anchor='nw')

            def _on_frame_configure(event):
                canvas.configure(scrollregion=canvas.bbox('all'))
            inner.bind('<Configure>', _on_frame_configure)

            # Helper: create KPI cards
            def _add_kpi_row(kvs):
                row = tk.Frame(inner, bg=COLORS['background'])
                row.pack(fill=tk.X, pady=(0, 12))
                for i, (k, v) in enumerate(kvs):
                    # Create a simple card-like frame
                    card = tk.Frame(row, bg=COLORS['surface'], relief='raised', borderwidth=1)
                    card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 10))

                    tk.Label(card, text=k, font=('Segoe UI', FONT_SIZES['caption'], 'bold'),
                            bg=COLORS['surface'], fg=COLORS['text_light']).pack(anchor=tk.W, padx=8, pady=(8, 0))

                    val_text = ''
                    if isinstance(v, (int, float)) and 'sales' in k.lower():
                        val_text = f"{report_data.currency_symbol}{v:,.2f}"
                    else:
                        val_text = str(v)

                    tk.Label(card, text=val_text, font=('Segoe UI', FONT_SIZES['large_value'], 'bold'),
                            bg=COLORS['surface'], fg=COLORS['primary']).pack(anchor=tk.W, padx=8, pady=(4, 8))

            # Helper: create a simple Treeview table
            def _add_table(title, columns, rows, col_widths=None, numeric_cols=None):
                if title:
                    tk.Label(inner, text=title, font=('Segoe UI', FONT_SIZES['subheader'], 'bold'),
                            bg=COLORS['background'], fg=COLORS['text']).pack(anchor=tk.W, pady=(6, 6))

                # Create treeview with proper styling
                tree = ttk.Treeview(inner, columns=columns, show='headings', height=min(len(rows) or 5, 12))

                # Configure columns
                for idx, col in enumerate(columns):
                    tree.heading(col, text=col)
                    width = 100  # default width
                    if col_widths and idx < len(col_widths):
                        width = col_widths[idx]
                    anchor = tk.E if numeric_cols and col in numeric_cols else tk.W
                    tree.column(col, anchor=anchor, width=width)

                tree.pack(fill=tk.BOTH, expand=True)

                # Populate data
                for r in rows:
                    tree.insert('', tk.END, values=r)

                # Add alternating row colors
                try:
                    tree.tag_configure('odd', background=COLORS['surface'])
                    tree.tag_configure('even', background=COLORS['background'])
                    for i, iid in enumerate(tree.get_children()):
                        tree.item(iid, tags=('odd' if i % 2 == 0 else 'even',))
                except Exception:
                    pass

            # Build UI from structured ReportData where possible (preferred)
            try:
                # Create a temporary report data object with paginated data
                paginated_report_data = ReportData(
                    report_data.report_type,
                    report_data.start_date,
                    report_data.end_date,
                    paginated_data,
                    {**report_data.metadata, 'page_info': page_info}
                )

                # SALES / FINANCIAL / CATEGORY / RECONCILIATION views get richer widget layouts
                if report_data.report_type in ('daily', 'range', 'sales', 'profit', 'category', 'payment_methods', 'voided', 'sales_log', 'reconciliation_summary', 'reconciliation_details'):
                    md = report_data.metadata or {}

                    # Different KPI sets based on report type
                    if report_data.report_type in ('reconciliation_summary', 'reconciliation_details'):
                        # Reconciliation KPIs
                        kpis = [
                            ('Total Sessions', md.get('session_count', 0)),
                            ('Completed Sessions', md.get('completed_sessions', 0)),
                            ('Sessions with Variance', md.get('sessions_with_variance', 0)),
                            ('Review Completion Rate', f"{md.get('reviewed_sessions', 0) / max(md.get('session_count', 1), 1) * 100:.1f}%")
                        ]
                        _add_kpi_row(kpis)

                        # Financial summary for reconciliation
                        if report_data.report_type == 'reconciliation_summary':
                            fin_kpis = [
                                ('Total System Amount', md.get('total_system', 0)),
                                ('Total Actual Amount', md.get('total_actual', 0)),
                                ('Total Variance', md.get('total_variance', 0)),
                                ('Unexplained Variance', md.get('unexplained_variance_total', 0))
                            ]
                            _add_kpi_row(fin_kpis)

                        # Sessions table
                        if paginated_data:
                            rows = []
                            for session in paginated_data:
                                if isinstance(session, dict):
                                    date_raw = session.get('created_at') or session.get('reconciliation_date')
                                    if isinstance(date_raw, str) and 'T' in date_raw:
                                        date = format_date(date_raw.split('T')[0])
                                    else:
                                        date = format_date(date_raw) if date_raw else 'N/A'

                                    status_name = (session.get('status') or '').title()
                                    system_amt = session.get('total_system_sales') or session.get('total_system') or 0
                                    actual_amt = session.get('total_actual_cash') or session.get('total_actual') or 0
                                    variance = session.get('total_variance') or 0
                                else:
                                    date = format_date(session.created_at.date()) if getattr(session, 'created_at', None) else 'N/A'
                                    status_name = session.status.title() if getattr(session, 'status', None) else ''
                                    system_amt = getattr(session, 'total_system_amount', 0) or 0
                                    actual_amt = getattr(session, 'total_actual_amount', 0) or 0
                                    variance = getattr(session, 'total_variance', 0) or 0

                                rows.append((date, status_name, f"{report_data.currency_symbol}{system_amt:.2f}",
                                           f"{report_data.currency_symbol}{actual_amt:.2f}", f"{report_data.currency_symbol}{variance:.2f}"))

                            _add_table('Reconciliation Sessions', ['Date', 'Status', 'System Amount', 'Actual Amount', 'Variance'], rows,
                                     col_widths=[100, 100, 120, 120, 120], numeric_cols=['System Amount', 'Actual Amount', 'Variance'])

                    else:
                        # Sales/Financial KPIs
                        kpis = [
                            ('Total Sales', md.get('total_sales', 0)),
                            ('Total Units', md.get('total_items', 0)),
                            ('Transactions', md.get('unique_transactions', 0)),
                            ('Records', page_info.get('total_items', 0))
                        ]
                        _add_kpi_row(kpis)

                        # Top items table (if present)
                        top_items = md.get('top_items') or []
                        if top_items:
                            rows = []
                            for i, it in enumerate(top_items, 1):
                                rows.append((i, it.get('name', ''), it.get('quantity', 0), f"{report_data.currency_symbol}{it.get('total', 0):.2f}"))
                            _add_table('Top Items Sold', ['#', 'Item Name', 'Qty', 'Total'], rows,
                                     col_widths=[40, 250, 60, 100], numeric_cols=['Qty', 'Total'])

                        # Detailed records as table
                        if paginated_data:
                            rows = []
                            for it in paginated_data:
                                timestamp = f"{format_date(it.get('date',''))} {it.get('time','')}"[:19]
                                rows.append((timestamp, it.get('receipt_number','N/A'), it.get('item_name',''),
                                           it.get('quantity',0), f"{report_data.currency_symbol}{it.get('price',0):.2f}",
                                           f"{report_data.currency_symbol}{it.get('total',0):.2f}"))
                            _add_table('Detailed Records', ['Time', 'Receipt', 'Item', 'Qty', 'Price', 'Total'], rows,
                                     col_widths=[140, 100, 200, 60, 100, 100], numeric_cols=['Qty','Price','Total'])

                else:
                    # Fallback: parse formatter text and render clean labels/tables (strip ASCII separators)
                    formatter = self._get_formatter_for_report(paginated_report_data)
                    content = formatter.format_report()
                    lines = [ln for ln in content.split('\n') if not all(c in '-=|_+ \\t' for c in ln)]

                    current_table = None
                    table_headers = None
                    table_rows = []

                    for ln in lines:
                        ln = ln.rstrip()
                        if not ln:
                            # flush any pending table
                            if table_headers and table_rows:
                                _add_table(None, table_headers, table_rows)
                                table_headers = None
                                table_rows = []
                            continue

                        # Section headers
                        if ln.isupper() and len(ln.split()) <= 6:
                            tk.Label(inner, text=ln.title(), font=('Segoe UI', FONT_SIZES['subheader'], 'bold'),
                                    bg=COLORS['background'], fg=COLORS['text']).pack(anchor=tk.W, pady=(8, 4))
                            continue

                        # Key-value lines
                        if ':' in ln and len(ln.split(':', 1)[0]) < 30:
                            k, v = ln.split(':', 1)
                            fr = tk.Frame(inner, bg=COLORS['background'])
                            fr.pack(fill=tk.X, pady=(0, 2))
                            tk.Label(fr, text=k.strip()+':', font=('Segoe UI', FONT_SIZES['caption'], 'bold'),
                                    bg=COLORS['background'], fg=COLORS['text_light']).pack(side=tk.LEFT)
                            tk.Label(fr, text=v.strip(), font=('Segoe UI', FONT_SIZES['body']),
                                    bg=COLORS['background'], fg=COLORS['text']).pack(side=tk.LEFT, padx=(8,0))
                            continue

                        # Table detection — header with multiple columns separated by 2+ spaces
                        parts = [p for p in ln.split('  ') if p.strip()]
                        if len(parts) > 1 and all(len(p.strip()) > 0 for p in parts):
                            if not table_headers:
                                table_headers = [p.strip() for p in parts]
                                table_rows = []
                            else:
                                # row
                                row_cells = [p.strip() for p in parts]
                                # pad to header length
                                while len(row_cells) < len(table_headers):
                                    row_cells.append('')
                                table_rows.append(tuple(row_cells))
                            continue

                        # Plain paragraph
                        tk.Label(inner, text=ln, font=('Segoe UI', FONT_SIZES['body']),
                                bg=COLORS['background'], fg=COLORS['text'], wraplength=800, justify=tk.LEFT).pack(anchor=tk.W, pady=(0,2))

                    # flush any remaining table
                    if table_headers and table_rows:
                        _add_table(None, table_headers, table_rows)

            except Exception as e:
                logger.exception(f"Error rendering modern report view: {e}")
                # Fallback to simple cleaned text
                fallback = tk.Frame(inner, bg=COLORS['background'])
                fallback.pack(fill=tk.BOTH, expand=True)
                try:
                    formatter = self._get_formatter_for_report(ReportData(report_data.report_type, report_data.start_date, report_data.end_date, paginated_data, {**report_data.metadata, 'page_info': page_info}))
                    content = formatter.format_report()
                    cleaned = '\n'.join([ln for ln in content.split('\n') if not all(c in '-=|_+ \\t' for c in ln)])
                    tk.Label(fallback, text=cleaned, font=('Segoe UI', FONT_SIZES['body']),
                            bg=COLORS['background'], fg=COLORS['text'], wraplength=800, justify=tk.LEFT).pack(anchor=tk.W)
                except Exception:
                    tk.Label(fallback, text="Unable to render report.", font=('Segoe UI', FONT_SIZES['body']),
                            bg=COLORS['background'], fg=COLORS['text']).pack(anchor=tk.W)

        # Header click bindings: single click for date presets/special-case, double-click toggles details
        title_label.bind("<Button-1>", lambda e, rt=report_data.report_type: self._on_header_click(rt))
        title_label.bind("<Double-Button-1>", lambda e, rd=report_data: self._on_header_double_click(e.widget, rd))

    def _on_header_click(self, report_type: str) -> None:
        """Handle header single-click: same semantics as single report click."""
        # Delegate to same behavior as clicking a report button
        if report_type == 'daily':
            self._set_today()
            self._generate_report_type(report_type)
            return
        self._show_date_preset_popup(report_type)

    def _on_header_double_click(self, widget, report_data: ReportData) -> None:
        """Handle header double-click: special-case daily reports, otherwise toggle details."""
        # If this header corresponds to a 'daily' report type, honor immediate generation
        self._on_header_click(report_data.report_type)

        # Toggle visibility of the attached report card
        report_card = getattr(widget, 'report_card', None)
        try:
            if report_card and report_card.winfo_ismapped():
                report_card.pack_forget()
            elif report_card:
                report_card.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            logger.debug(f"Error toggling report details: {e}")
            # If toggling fails, ensure details are visible
            try:
                if report_card:
                    report_card.pack(fill=tk.BOTH, expand=True)
            except Exception:
                pass


    def _show_error(self, message: str) -> None:
        """Show error message in the report area."""
        self._clear_report_area()

        error_frame = ttk.Frame(self.content_frame, style=STYLES['frame'])
        error_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(error_frame, text="❌ Error", style=STYLES['subheader_label'],
                foreground=COLORS['danger']).pack(pady=(20, 10))

        ttk.Label(error_frame, text=message, style=STYLES['body_label']).pack(pady=(0, 20))

        ttk.Button(error_frame, text="Try Again", style=STYLES['secondary_button'],
                 command=self._generate_report).pack()

    def _refresh_current_view(self) -> None:
        """Refresh the current view."""
        category = self.selected_category.get()
        if category == "overview":
            self._show_overview()
        elif category == "sales":
            self._show_sales_category()
        elif category == "financial":
            self._show_financial_category()
        elif category == "inventory":
            self._show_inventory_category()
        elif category == "reconciliation":
            self._show_reconciliation_category()

    def _get_date_range_text(self) -> str:
        """Get formatted date range text."""
        start = self.start_date.get()
        end = self.end_date.get()
        if start == end:
            return f"Date: {start}"
        else:
            return f"Range: {start} to {end}"

    # Date helper methods
    def _set_today(self) -> None:
        today = format_date(datetime.now())
        self.start_date.set(today)
        self.end_date.set(today)
        if hasattr(self, 'date_display'):
            self.date_display.config(text=self._get_date_range_text())

    def _set_this_week(self) -> None:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        self.start_date.set(format_date(start_of_week))
        self.end_date.set(format_date(end_of_week))
        if hasattr(self, 'date_display'):
            self.date_display.config(text=self._get_date_range_text())

    def _set_this_month(self) -> None:
        today = datetime.now()
        start_of_month = today.replace(day=1)
        next_month = start_of_month.replace(month=start_of_month.month % 12 + 1, day=1)
        end_of_month = next_month - timedelta(days=1)
        self.start_date.set(format_date(start_of_month))
        self.end_date.set(format_date(end_of_month))
        if hasattr(self, 'date_display'):
            self.date_display.config(text=self._get_date_range_text())

    def _set_last_7_days(self) -> None:
        today = datetime.now()
        start_date = today - timedelta(days=6)
        self.start_date.set(format_date(start_date))
        self.end_date.set(format_date(today))
        if hasattr(self, 'date_display'):
            self.date_display.config(text=self._get_date_range_text())

    def _set_last_30_days(self) -> None:
        today = datetime.now()
        start_date = today - timedelta(days=29)
        self.start_date.set(format_date(start_date))
        self.end_date.set(format_date(today))
        if hasattr(self, 'date_display'):
            self.date_display.config(text=self._get_date_range_text())

    def _set_last_90_days(self) -> None:
        today = datetime.now()
        start_date = today - timedelta(days=89)
        self.start_date.set(format_date(start_date))
        self.end_date.set(format_date(today))
        if hasattr(self, 'date_display'):
            self.date_display.config(text=self._get_date_range_text())

    def _show_date_preset_popup(self, report_type: str) -> None:
        """Show quick date preset popup for reports (not used for 'daily')."""
        if report_type == 'daily':
            # Daily already uses today, so just set and generate
            self._set_today()
            self._generate_report_type(report_type)
            return

        # Check if a popup is already open
        if self._date_preset_popup is not None and self._date_preset_popup.winfo_exists():
            # If popup exists but is for a different page, close it first
            if self._popup_page != self.selected_category.get():
                try:
                    self._date_preset_popup.destroy()
                except:
                    pass
                self._date_preset_popup = None
                self._popup_page = None
            else:
                # Same page popup already exists, don't open another
                return

        # Create a simple popup using tk widgets
        popup = tk.Toplevel(self)
        self._date_preset_popup = popup  # Track the popup
        self._popup_page = self.selected_category.get()  # Track the page
        
        # Register as modal dialog
        self._register_modal_dialog(popup)
        
        set_window_icon(popup)
        popup.title("Quick Date Filter")
        popup.geometry("200x240")
        popup.resizable(True, True)
        popup.configure(bg=COLORS['background'])
        
        # Keep popup hidden until fully constructed to avoid mapping/jump
        # Position popup near the mouse; flip above pointer if there's not enough space below (avoid taskbar)
        popup.update_idletasks()
        x = max(0, self.winfo_pointerx() - popup.winfo_reqwidth() // 2)
        pointer_y = self.winfo_pointery()
        screen_h = self.winfo_screenheight()
        popup_h = popup.winfo_reqheight()
        taskbar_margin = 48  # safe margin to keep popup above taskbar
        # Prefer showing below pointer if space permits, otherwise show above
        if pointer_y + popup_h + taskbar_margin <= screen_h:
            y = max(0, pointer_y + 10)
        else:
            y = max(0, pointer_y - popup_h - 10)
        popup.geometry(f"+{x}+{y}")

        # Handle popup destruction to clear tracking
        def on_popup_destroy():
            if self._date_preset_popup == popup:
                self._date_preset_popup = None
                self._popup_page = None
            self._unregister_modal_dialog(popup)
        
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), on_popup_destroy()))
        popup.bind("<Destroy>", lambda e: on_popup_destroy() if e.widget == popup else None)

        # Title
        title_label = tk.Label(popup, text="Select Date Range", bg=COLORS['background'], 
                              fg=COLORS['text'], font=('Segoe UI', 10, 'bold'))
        title_label.pack(pady=(10, 5))

        # Preset buttons - use consistent presets for all reports
        presets = [
            ("This Week", lambda rt=report_type: (self._set_this_week(), self._generate_report_type(rt))),
            ("This Month", lambda rt=report_type: (self._set_this_month(), self._generate_report_type(rt))),
            ("Last 7 Days", lambda rt=report_type: (self._set_last_7_days(), self._generate_report_type(rt))),
            ("Last 30 Days", lambda rt=report_type: (self._set_last_30_days(), self._generate_report_type(rt))),
            ("Last 90 Days", lambda rt=report_type: (self._set_last_90_days(), self._generate_report_type(rt))),
            ("Custom", lambda rt=report_type: (self._clear_date_popup_tracking(), self._show_date_picker(rt)))
        ]

        for text, command in presets:
            def preset_action(cmd=command, rt=report_type):
                # Clear popup tracking before destroying
                if self._date_preset_popup == popup:
                    self._date_preset_popup = None
                    self._popup_page = None
                popup.destroy()
                cmd(rt)

            btn = tk.Button(popup, text=text, bg=COLORS['primary'], fg=COLORS['text_white'],
                           font=('Segoe UI', 9), command=preset_action)
            btn.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Show the popup only after it's fully built to avoid visual jumping
        popup.update_idletasks()
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        popup.attributes('-topmost', True)

    def _clear_date_popup_tracking(self) -> None:
        """Clear date popup tracking when switching to different popup types."""
        if self._date_preset_popup is not None:
            try:
                if self._date_preset_popup.winfo_exists():
                    self._date_preset_popup.destroy()
                else:
                    # If already destroyed, just clean up tracking
                    self._unregister_modal_dialog(self._date_preset_popup)
            except:
                pass
        self._date_preset_popup = None
        self._popup_page = None

    def _register_modal_dialog(self, dialog) -> None:
        """Register a modal dialog to prevent tab switching."""
        self._modal_dialogs.add(dialog)

    def _unregister_modal_dialog(self, dialog) -> None:
        """Unregister a modal dialog when it's closed."""
        self._modal_dialogs.discard(dialog)

    def _has_open_modal_dialogs(self) -> bool:
        """Check if there are any open modal dialogs."""
        # Clean up any destroyed dialogs
        self._modal_dialogs = {d for d in self._modal_dialogs if d.winfo_exists()}
        return len(self._modal_dialogs) > 0

    def _show_date_picker(self, report_type: str | None = None) -> None:
        """Show custom date picker dialog.

        If report_type is provided, the report will be generated after applying dates.
        """
        # Store the report type for the Apply button
        self._report_type_for_picker = report_type
        # Create a popup window for date selection
        popup = tk.Toplevel(self)
        
        # Register as modal dialog
        self._register_modal_dialog(popup)
        
        set_window_icon(popup)
        popup.title("Select Custom Date Range")
        popup.geometry("400x250")
        popup.resizable(True, True)
        popup.transient(self)
        popup.grab_set()

        # Center the popup
        popup.geometry("+{}+{}".format(
            self.winfo_rootx() + self.winfo_width()//2 - 200,
            self.winfo_rooty() + self.winfo_height()//2 - 125
        ))

        # Configure popup styling (safely)
        try:
            style = ttk.Style()
            # Only configure if styles don't exist - use system default backgrounds
            if not style.lookup('Popup.TFrame', 'background'):
                style.configure('Popup.TFrame')
            if not style.lookup('Popup.TLabelframe', 'background'):
                style.configure('Popup.TLabelframe', borderwidth=2, relief="raised",
                               padding=CARD_PADDING)
        except Exception as e:
            print(f"Warning: Could not configure popup styles: {e}")
            # Continue without custom styling

        # Handle popup destruction to unregister modal
        def on_popup_destroy():
            self._unregister_modal_dialog(popup)
        
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), on_popup_destroy()))
        popup.bind("<Destroy>", lambda e: on_popup_destroy() if e.widget == popup else None)

        # Main frame
        main_frame = ttk.Frame(popup, padding=WINDOW_PADDING)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main_frame, text="Select Date Range", style=STYLES['header_label']).pack(pady=(0, 20))

        # Date selection frame
        date_frame = ttk.Frame(main_frame)
        date_frame.pack(fill=tk.X, pady=(0, 20))

        # Start date
        start_frame = ttk.Frame(date_frame)
        start_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(start_frame, text="Start Date:", style=STYLES['body_label']).pack(side=tk.LEFT, padx=(0, 10))

        start_var = tk.StringVar(value=self.start_date.get())
        start_entry = ttk.Entry(start_frame, textvariable=start_var, width=12)
        start_entry.pack(side=tk.LEFT, padx=(0, 5))

        def pick_start_date():
            def on_date_select(date):
                start_var.set(format_date(date))
                start_picker.destroy()

            start_picker = tk.Toplevel(popup)
            set_window_icon(start_picker)
            start_picker.title("Select Start Date")
            start_picker.geometry("300x250")
            start_picker.transient(popup)
            start_picker.withdraw()
            start_picker.resizable(True, True)

            # Position above the parent popup to avoid taskbar
            start_picker.geometry("+{}+{}".format(
                popup.winfo_rootx() + popup.winfo_width()//2 - 150,
                popup.winfo_rooty() - 270  # Position above the popup
            ))

            try:
                # Respect the current end date as a max constraint, if parseable
                from utils.date_utils import parse_date_flexible
                from datetime import date as _date
                maxdate = _date.today()
                try:
                    # Re-parse the current end date value from the text field
                    end_dt = parse_date_flexible(end_var.get())
                    # Cap the max date to end date, but never allow future dates
                    maxdate = min(end_dt.date(), _date.today())
                except Exception:
                    # If end parsing fails, allow up to today
                    maxdate = _date.today()

                # Try to set the initial date to the current start date value
                initial_date = None
                try:
                    current_start = parse_date_flexible(start_var.get())
                    initial_date = current_start.date()
                    # Ensure initial date is within constraints
                    if maxdate and initial_date > maxdate:
                        initial_date = maxdate
                    if initial_date > _date.today():
                        initial_date = _date.today()
                except Exception:
                    initial_date = _date.today()

                cal = tkcalendar.Calendar(start_picker, selectmode='day',
                                        date_pattern=get_tkcalendar_date_pattern(), maxdate=maxdate,
                                        year=initial_date.year, month=initial_date.month, day=initial_date.day)
                cal.pack(pady=20)

                ttk.Button(start_picker, text="Select", command=lambda: on_date_select(cal.selection_get())).pack(pady=(0, 10))
                ttk.Button(start_picker, text="Cancel", command=start_picker.destroy).pack()

                # Show picker only after fully built to avoid 'ballooning' animation
                start_picker.update_idletasks()
                start_picker.deiconify()
                start_picker.grab_set()

            except Exception as e:
                messagebox.showerror("Error", f"Could not open calendar: {e}")
                start_picker.destroy()

        ttk.Button(start_frame, text="📅", width=3, command=pick_start_date).pack(side=tk.LEFT)

        # End date
        end_frame = ttk.Frame(date_frame)
        end_frame.pack(fill=tk.X)

        ttk.Label(end_frame, text="End Date:", style=STYLES['body_label']).pack(side=tk.LEFT, padx=(0, 10))

        end_var = tk.StringVar(value=self.end_date.get())
        end_entry = ttk.Entry(end_frame, textvariable=end_var, width=12)
        end_entry.pack(side=tk.LEFT, padx=(0, 5))

        def pick_end_date():
            def on_date_select(date):
                end_var.set(format_date(date))
                end_picker.destroy()

            end_picker = tk.Toplevel(popup)
            set_window_icon(end_picker)
            end_picker.title("Select End Date")
            end_picker.geometry("300x250")
            end_picker.transient(popup)
            end_picker.withdraw()
            end_picker.resizable(True, True)

            # Position above the parent popup to avoid taskbar
            end_picker.geometry("+{}+{}".format(
                popup.winfo_rootx() + popup.winfo_width()//2 - 150,
                popup.winfo_rooty() - 270  # Position above the popup
            ))

            try:
                # Respect the current start date as a min constraint, if parseable
                from utils.date_utils import parse_date_flexible
                from datetime import date as _date
                mindate = None
                try:
                    # Re-parse the current start date value from the text field
                    start_dt = parse_date_flexible(start_var.get())
                    mindate = start_dt.date()
                except Exception:
                    mindate = None

                # Always prevent future dates by capping max to today
                maxdate = _date.today()

                # Ensure mindate doesn't exceed maxdate (prevent no selectable dates)
                if mindate and mindate > maxdate:
                    mindate = maxdate

                # Try to set the initial date to the current end date value
                initial_date = None
                try:
                    current_end = parse_date_flexible(end_var.get())
                    initial_date = current_end.date()
                    # Ensure initial date is within constraints
                    if maxdate and initial_date > maxdate:
                        initial_date = maxdate
                    if mindate and initial_date < mindate:
                        initial_date = mindate
                except Exception:
                    initial_date = _date.today()

                cal = tkcalendar.Calendar(end_picker, selectmode='day',
                                        date_pattern=get_tkcalendar_date_pattern(), mindate=mindate, maxdate=maxdate,
                                        year=initial_date.year, month=initial_date.month, day=initial_date.day)
                cal.pack(pady=20)

                ttk.Button(end_picker, text="Select", command=lambda: on_date_select(cal.selection_get())).pack(pady=(0, 10))
                ttk.Button(end_picker, text="Cancel", command=end_picker.destroy).pack()

                # Show picker only after fully built to avoid 'ballooning' animation
                end_picker.update_idletasks()
                end_picker.deiconify()
                end_picker.grab_set()

            except Exception as e:
                messagebox.showerror("Error", f"Could not open calendar: {e}")
                end_picker.destroy()

        ttk.Button(end_frame, text="📅", width=3, command=pick_end_date).pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        def apply_dates():
            # Update the main date variables and generate report
            self.start_date.set(start_var.get())
            self.end_date.set(end_var.get())
            popup.destroy()
            # Generate report with selected dates
            if hasattr(self, '_report_type_for_picker') and self._report_type_for_picker:
                self._generate_report_type(self._report_type_for_picker)
            else:
                self._generate_report()

        ttk.Button(button_frame, text="Apply", style=STYLES['primary_button'], command=apply_dates).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", style=STYLES['secondary_button'], command=popup.destroy).pack(side=tk.LEFT)

    def _get_formatter_for_report(self, report_data: ReportData) -> 'TextReportFormatter':
        """Get the appropriate formatter for the report type."""
        formatters = {
            'daily': SalesTextFormatter,
            'range': SalesTextFormatter,
            'bestsellers': SalesTextFormatter,
            'profit': ProfitTextFormatter,
            'category': CategoryTextFormatter,
            'payment_methods': PaymentMethodsTextFormatter,
            'voided': VoidedSalesTextFormatter,
            'sales_log': SalesLogTextFormatter,
            'transactions': TransactionsTextFormatter,
            'trends': TrendsTextFormatter,
            'reconciliation_summary': ReconciliationSummaryTextFormatter,
            'reconciliation_details': ReconciliationDetailsTextFormatter,
            'inventory_stock_levels': InventoryStockLevelsTextFormatter,
            'inventory_low_stock': InventoryLowStockTextFormatter,
            'inventory_value': InventoryValueTextFormatter,
            'inventory_stock_movement': InventoryStockMovementTextFormatter,
        }
        
        formatter_class = formatters.get(report_data.report_type)
        if formatter_class:
            return formatter_class(report_data)
        
        # Fallback for unknown report types
        return SalesTextFormatter(report_data)

    def _download_report(self) -> None:
        """Download the current report as CSV or text file."""
        try:
            # Ask user for file location and format
            file_path = filedialog.asksaveasfilename(
                defaultextension=FILE_EXTENSIONS['csv'],
                filetypes=[
                    (EXPORT_FORMATS['csv'], f"*{FILE_EXTENSIONS['csv']}"),
                    (EXPORT_FORMATS['xlsx'], f"*{FILE_EXTENSIONS['xlsx']}"),
                    (EXPORT_FORMATS['pdf'], f"*{FILE_EXTENSIONS['pdf']}"),
                    (EXPORT_FORMATS['txt'], f"*{FILE_EXTENSIONS['txt']}"),
                    ("All files", "*.*")
                ],
                title="Save Report As"
            )

            if not file_path:
                return

            # Generate the report data
            report_type = self.report_type.get()
            local_dates = self._local_date_vars.get(report_type)
            start = local_dates[0].get() if local_dates else self.start_date.get()
            end = local_dates[1].get() if local_dates else self.end_date.get()
            status_var = self._local_status_vars.get(report_type)
            status_filter = status_var.get() if status_var else self.reconciliation_status.get()

            # For large tabular reports we can stream directly to CSV to avoid memory pressure
            if file_path.lower().endswith(FILE_EXTENSIONS['csv']) and report_type in ('sales_log', 'reconciliation_details', 'inventory_stock_levels'):
                use_keyset = True if report_type in ('sales_log', 'inventory_stock_levels') else False
                success = self.export_manager.export_report_streaming(report_type, start, end, file_path, page_size=500, use_keyset=use_keyset, status_filter=status_filter)
                if success:
                    messagebox.showinfo("Export Complete", f"Report exported successfully to:\n{file_path}")
                else:
                    messagebox.showerror("Export Failed", "Failed to export the report.")
                return

            report_data = self.service.generate_report_sync(
                report_type, start, end, status_filter
            )

            if report_data.metadata.get('error'):
                messagebox.showerror("Report Error", report_data.metadata['error'])
                return

            # Export the report
            success = self.export_manager.export_report(report_data, file_path)
            if success:
                messagebox.showinfo("Export Complete", f"Report exported successfully to:\n{file_path}")
            else:
                messagebox.showerror("Export Failed", "Failed to export the report.")

        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            messagebox.showerror("Export Error", f"Failed to export report: {e}")

    def _export_report(self, report_data: ReportData, format_type: str) -> None:
        """Export a specific report in the given format."""
        # Check permission for export
        current_user = get_username()
        if not permissions.has_permission(current_user, 'export_reports'):
            messagebox.showerror("Permission Denied", "You do not have permission to export reports")
            return
        
        try:
            # Determine file extension
            ext = FILE_EXTENSIONS.get(format_type, '.txt')
            
            # Ask user for file location
            file_path = filedialog.asksaveasfilename(
                defaultextension=ext,
                filetypes=[(EXPORT_FORMATS.get(format_type, format_type.upper()), f"*{ext}")],
                title=f"Save {format_type.upper()} Report As"
            )

            if not file_path:
                return

            # Ensure correct extension
            if not file_path.lower().endswith(ext):
                file_path += ext

            # For large tabular reports we can stream directly to CSV to avoid memory pressure
            if format_type == 'csv' and report_data.report_type in ('sales_log', 'reconciliation_details', 'inventory_stock_levels'):
                use_keyset = True if report_data.report_type in ('sales_log', 'inventory_stock_levels') else False
                status_filter = report_data.metadata.get('status_filter', 'all')
                success = self.export_manager.export_report_streaming(
                    report_data.report_type, 
                    report_data.start_date, 
                    report_data.end_date, 
                    file_path, 
                    page_size=500, 
                    use_keyset=use_keyset, 
                    status_filter=status_filter
                )
                if success:
                    messagebox.showinfo("Export Complete", f"Report exported successfully to:\n{file_path}")
                else:
                    messagebox.showerror("Export Failed", "Failed to export the report.")
                return

            # Export the report
            success = self.export_manager.export_report(report_data, file_path)
            if success:
                messagebox.showinfo("Export Complete", f"Report exported successfully to:\n{file_path}")
            else:
                messagebox.showerror("Export Failed", "Failed to export the report.")

        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            messagebox.showerror("Export Error", f"Failed to export report: {e}")

        except Exception as e:
            logger.error(f"Error in export: {e}")
            messagebox.showerror("Export Error", f"Failed to export report: {e}")

    # --- Scheduling helpers ---
    def _schedules_file_path(self) -> str:
        return os.path.join(os.path.abspath(os.getcwd()), 'export_schedules.json')

    def _load_schedules(self) -> list:
        path = self._schedules_file_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
            return []

    def _save_schedules(self, schedules: list) -> None:
        path = self._schedules_file_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(schedules, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def _open_schedule_dialog(self, report_data: ReportData) -> None:
        """Open dialog to schedule an export for the given report."""
        popup = tk.Toplevel(self)
        
        # Register as modal dialog
        self._register_modal_dialog(popup)
        
        set_window_icon(popup)
        popup.title("Schedule Export")
        popup.geometry('420x260')
        popup.resizable(True, True)
        popup.transient(self)
        popup.grab_set()

        # Center the popup
        popup.geometry("+{}+{}".format(
            self.winfo_rootx() + self.winfo_width()//2 - 210,
            self.winfo_rooty() + self.winfo_height()//2 - 130
        ))

        # Handle popup destruction to unregister modal
        def on_popup_destroy():
            self._unregister_modal_dialog(popup)
        
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), on_popup_destroy()))
        popup.bind("<Destroy>", lambda e: on_popup_destroy() if e.widget == popup else None)

        ttk.Label(popup, text=f"Schedule export for: {REPORT_TYPES.get(report_data.report_type, report_data.report_type)}", style=STYLES['subheader_label']).pack(pady=(10, 8))

        body = ttk.Frame(popup, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        ttk.Label(body, text="Format:", style=STYLES['body_label']).grid(row=0, column=0, sticky=tk.W)
        format_var = tk.StringVar(value='csv')
        ttk.Combobox(body, textvariable=format_var, values=['csv', 'xlsx', 'pdf', 'txt'], state='readonly', width=12).grid(row=0, column=1, padx=(8,0), sticky=tk.W)

        ttk.Label(body, text="Frequency:", style=STYLES['body_label']).grid(row=1, column=0, sticky=tk.W, pady=(6,0))
        freq_var = tk.StringVar(value='Daily')
        ttk.Combobox(body, textvariable=freq_var, values=['Once', 'Daily', 'Weekly', 'Monthly'], state='readonly', width=12).grid(row=1, column=1, padx=(8,0), sticky=tk.W)

        ttk.Label(body, text="Time (HH:MM):", style=STYLES['body_label']).grid(row=2, column=0, sticky=tk.W, pady=(6,0))
        time_var = tk.StringVar(value='02:00')
        ttk.Entry(body, textvariable=time_var, width=12).grid(row=2, column=1, padx=(8,0), sticky=tk.W)

        ttk.Label(body, text="Start Date:", style=STYLES['body_label']).grid(row=3, column=0, sticky=tk.W, pady=(6,0))
        start_var = tk.StringVar(value=report_data.start_date)
        ttk.Entry(body, textvariable=start_var, width=12).grid(row=3, column=1, padx=(8,0), sticky=tk.W)

        ttk.Label(body, text="End Date:", style=STYLES['body_label']).grid(row=4, column=0, sticky=tk.W, pady=(6,0))
        end_var = tk.StringVar(value=report_data.end_date)
        ttk.Entry(body, textvariable=end_var, width=12).grid(row=4, column=1, padx=(8,0), sticky=tk.W)

        def save_schedule():
            sched = {
                'report_type': report_data.report_type,
                'format': format_var.get(),
                'frequency': freq_var.get(),
                'time': time_var.get(),
                'start_date': start_var.get(),
                'end_date': end_var.get(),
                'created_at': datetime.now().isoformat()
            }
            schedules = self._load_schedules()
            schedules.append(sched)
            self._save_schedules(schedules)
            messagebox.showinfo('Scheduled', 'Export scheduled successfully.')
            popup.destroy()

        button_frame = ttk.Frame(body)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(12,0))
        ttk.Button(button_frame, text='Save', style=STYLES['primary_button'], command=save_schedule).pack(side=tk.LEFT, padx=(0,8))
        ttk.Button(button_frame, text='Cancel', style=STYLES['secondary_button'], command=popup.destroy).pack(side=tk.LEFT)

    def _manage_schedules_dialog(self) -> None:
        """Show existing schedules and allow removal."""
        schedules = self._load_schedules()
        popup = tk.Toplevel(self)
        
        # Register as modal dialog
        self._register_modal_dialog(popup)
        
        set_window_icon(popup)
        popup.title('Manage Export Schedules')
        popup.geometry('520x320')
        popup.resizable(True, True)
        popup.transient(self)
        popup.grab_set()

        # Center the popup
        popup.geometry("+{}+{}".format(
            self.winfo_rootx() + self.winfo_width()//2 - 260,
            self.winfo_rooty() + self.winfo_height()//2 - 160
        ))

        # Handle popup destruction to unregister modal
        def on_popup_destroy():
            self._unregister_modal_dialog(popup)
        
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), on_popup_destroy()))
        popup.bind("<Destroy>", lambda e: on_popup_destroy() if e.widget == popup else None)

        listbox = tk.Listbox(popup, width=80, height=12)
        listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        for s in schedules:
            desc = f"{s.get('report_type')} | {s.get('format')} | {s.get('frequency')} @ {s.get('time')} ({s.get('start_date')} to {s.get('end_date')})"
            listbox.insert(tk.END, desc)

        def remove_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if messagebox.askyesno('Confirm', 'Remove selected schedule?'):
                schedules.pop(idx)
                self._save_schedules(schedules)
                listbox.delete(idx)

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text='Remove', style=STYLES['secondary_button'], command=remove_selected).pack(side=tk.LEFT, padx=(0,8))
        ttk.Button(btn_frame, text='Close', style=STYLES['primary_button'], command=popup.destroy).pack(side=tk.LEFT)

    def _on_report_click(self, event, report_type: str, button_widget) -> None:
        """Handle single click on report button - show date preset popup."""
        self._show_date_preset_popup(report_type)

    def _on_report_double_click(self, event, report_type: str) -> None:
        """Handle double click on report button - generate report immediately."""
        # Set default dates (last 30 days) and generate
        self._set_last_30_days()
        self._generate_report_type(report_type)

    def _generate_report_type(self, report_type: str) -> None:
        """Generate a report for the given type using current date settings."""
        start_date = self.start_date.get()
        end_date = self.end_date.get()
        status_filter = self.reconciliation_status.get()
        
        self._generate_report_with_params(report_type, start_date, end_date, status_filter)

    # Legacy methods for compatibility
    def _on_report_type_change(self, *args) -> None:
        """Legacy method for backwards compatibility."""
        pass

    def _pick_start_date(self) -> None:
        """Legacy date picker."""
        pass

    def _pick_end_date(self) -> None:
        """Legacy date picker."""
        pass

    def refresh(self) -> None:
        """Legacy refresh method."""
        self._refresh_current_view()

    def _build_header(self) -> None:
        """Build the modern header with navigation and actions."""
        header = ttk.Frame(self, style=STYLES['frame'])
        header.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=HEADER_PADDING)
        header.columnconfigure(1, weight=1)

        # Title and navigation
        title_frame = ttk.Frame(header, style=STYLES['frame'])
        title_frame.grid(row=0, column=0, sticky=tk.W)

        ttk.Label(title_frame, text="📊", font=('Segoe UI', 20)).grid(row=0, column=0, padx=(0, 10))
        ttk.Label(title_frame, text="Reports Dashboard", style=STYLES['header_label']).grid(row=0, column=1, sticky=tk.W)

        # Action buttons
        actions_frame = ttk.Frame(header, style=STYLES['frame'])
        actions_frame.grid(row=0, column=2, sticky=tk.E)

        if self.on_home:
            pass

        ttk.Button(actions_frame, text="🔄 Refresh", style=STYLES['action_button'],
                  command=self._refresh_current_view).pack(side=tk.LEFT, padx=(0, 10))


# Backwards compatibility
ReportsFrame = ModernReportsFrame
