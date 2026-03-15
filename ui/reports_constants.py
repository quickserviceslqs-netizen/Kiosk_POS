"""Constants and configuration for the reports module."""

import os
from typing import Dict, Any

# Import theme colors - use lazy loading to avoid circular imports
def get_colors():
    """Get colors from the centralized theme system."""
    try:
        from utils.theme import get_theme_colors
        return get_theme_colors()
    except Exception:
        # Fallback to default colors if theme system not available
        return _DEFAULT_COLORS

# Fallback colors if theme system unavailable
_DEFAULT_COLORS = {
    'primary': '#2563EB',
    'primary_dark': '#1D4ED8',
    'primary_light': '#DBEAFE',
    'secondary': '#64748B',
    'accent': '#0EA5E9',
    'success': '#10B981',
    'success_light': '#D1FAE5',
    'warning': '#F59E0B',
    'warning_light': '#FEF3C7',
    'danger': '#EF4444',
    'danger_light': '#FEE2E2',
    'info': '#3B82F6',
    'info_light': '#DBEAFE',
    'background': '#F8FAFC',
    'surface': '#FFFFFF',
    'surface_alt': '#F1F5F9',
    'border': '#E2E8F0',
    'border_dark': '#CBD5E1',
    'text': '#1E293B',
    'text_secondary': '#475569',
    'text_light': '#64748B',
    'text_muted': '#94A3B8',
    'text_white': '#FFFFFF',
    'sidebar_bg': '#1E293B',
    'sidebar_text': '#E2E8F0',
    'sidebar_hover': '#334155',
    'sidebar_active': '#2563EB',
    'table_header': '#F1F5F9',
    'table_row_alt': '#F8FAFC',
    'table_row_hover': '#E0F2FE',
    'chart_1': '#2563EB',
    'chart_2': '#10B981',
    'chart_3': '#F59E0B',
    'chart_4': '#EF4444',
    'chart_5': '#8B5CF6',
    'chart_6': '#EC4899',
}

# UI Constants
WINDOW_PADDING = (20, 20, 20, 20)
HEADER_PADDING = (0, 15)
SIDEBAR_PADDING = (10, 10)
CARD_PADDING = (15, 15, 15, 15)
BUTTON_PADDING = 6
ACTION_BUTTON_PADDING = (10, 5)

# Layout Constants
SIDEBAR_WIDTH = 220
REPORT_HEIGHT = 400
MAX_RECORDS_DISPLAY = 100
MAX_RECORDS_EXPORT = 1000

# Font Sizes
FONT_SIZES = {
    'header': 18,
    'subheader': 13,
    'body': 10,
    'caption': 9,
    'large_value': 22,
    'sidebar_title': 11,
    'sidebar_item': 10
}

# Dynamic COLORS property that pulls from theme
class _ColorsProxy:
    """Proxy object that fetches colors from theme system dynamically."""
    def __getitem__(self, key):
        colors = get_colors()
        if key in colors:
            return colors[key]
        return _DEFAULT_COLORS.get(key, '#000000')
    
    def get(self, key, default=None):
        colors = get_colors()
        if key in colors:
            return colors[key]
        return _DEFAULT_COLORS.get(key, default)
    
    def __contains__(self, key):
        colors = get_colors()
        return key in colors or key in _DEFAULT_COLORS
    
    def keys(self):
        return _DEFAULT_COLORS.keys()
    
    def values(self):
        colors = get_colors()
        return [colors.get(k, v) for k, v in _DEFAULT_COLORS.items()]
    
    def items(self):
        colors = get_colors()
        return [(k, colors.get(k, v)) for k, v in _DEFAULT_COLORS.items()]

COLORS = _ColorsProxy()

# Style Names
STYLES = {
    # Frame styles
    'frame': 'TFrame',
    'card': 'Reports.Card.TLabelframe',
    'card_header': 'Reports.CardHeader.TFrame',
    'sidebar_frame': 'Reports.Sidebar.TFrame',
    'sidebar_card': 'Reports.Sidebar.TLabelframe',
    'content_frame': 'Reports.Content.TFrame',
    
    # Button styles
    'primary_button': 'Reports.Primary.TButton',
    'secondary_button': 'Reports.Secondary.TButton',
    'action_button': 'Reports.Action.TButton',
    'sidebar_button': 'Reports.Sidebar.TButton',
    'sidebar_button_active': 'Reports.SidebarActive.TButton',
    'icon_button': 'Reports.Icon.TButton',
    
    # Label styles
    'header_label': 'Reports.Header.TLabel',
    'subheader_label': 'Reports.Subheader.TLabel',
    'body_label': 'Reports.Body.TLabel',
    'caption_label': 'Reports.Caption.TLabel',
    'metric_value': 'Reports.MetricValue.TLabel',
    'metric_label': 'Reports.MetricLabel.TLabel',
    'sidebar_label': 'Reports.SidebarLabel.TLabel',
    'sidebar_title': 'Reports.SidebarTitle.TLabel',
    
    # Table styles
    'treeview': 'Reports.Treeview',
    'treeview_heading': 'Reports.Treeview.Heading',
}

# Report Categories with icons
REPORT_CATEGORIES = {
    'overview': {'icon': '📊', 'label': 'Overview', 'color': 'primary'},
    'sales': {'icon': '💰', 'label': 'Sales', 'color': 'success'},
    'financial': {'icon': '💼', 'label': 'Financial', 'color': 'info'},
    'inventory': {'icon': '📦', 'label': 'Inventory', 'color': 'warning'},
    'reconciliation': {'icon': '🔄', 'label': 'Reconciliation', 'color': 'secondary'},
    'purchase_orders': {'icon': '📋', 'label': 'Purchase Orders', 'color': 'info'},
}


# Date Range Presets
DATE_PRESETS = {
    'today': 'Today',
    'this_week': 'This Week',
    'this_month': 'This Month',
    'custom': 'Custom'
}

# Export Formats
EXPORT_FORMATS = {
    'csv': 'CSV files',
    'txt': 'Text files',
    'xlsx': 'Excel files',
    'pdf': 'PDF files'
}

# Grid Layout Constants
GRID_COLUMNS = {
    'sales_buttons': 4,
    'actions': 2
}

# Threading Constants
THREAD_TIMEOUT = 30  # seconds
UI_UPDATE_INTERVAL = 100  # milliseconds

# Error Messages
ERROR_MESSAGES = {
    'report_generation': 'Failed to generate report',
    'export_failed': 'Failed to export report',
    'no_data': 'No data found for this period',
    'invalid_dates': 'Invalid date range selected',
    'network_error': 'Network connection error',
    'database_error': 'Database connection error'
}

# File Extensions
FILE_EXTENSIONS = {
    'csv': '.csv',
    'txt': '.txt',
    'xlsx': '.xlsx',
    'pdf': '.pdf'
}

# Report Types with display names
REPORT_TYPES = {
    'overview': 'Dashboard Overview',
    'daily': 'Daily Sales',
    'range': 'Date Range Sales',
    'bestsellers': 'Best Sellers',
    'profit': 'Profit Analysis',
    'category': 'Category Sales',
    'payment_methods': 'Payment Methods',
    'voided': 'Voided Sales',
    'sales_log': 'Sales Log',
    'transactions': 'Transactions',
    'trends': 'Sales Trends',
    'reconciliation_summary': 'Reconciliation Summary',
    'reconciliation_details': 'Reconciliation Details',
    'inventory_stock_levels': 'Inventory Stock Levels',
    'inventory_low_stock': 'Low Stock Items',
    'inventory_value': 'Inventory Value',
    'inventory_stock_movement': 'Stock Movement Analysis',
    'po_summary': 'Purchase Order Summary',
    'po_by_supplier': 'Spending by Supplier',
    'po_items_detail': 'PO Items Detail',
}

# Report Limits (configurable)
REPORT_LIMITS = {
    'display': int(os.getenv('REPORT_DISPLAY_LIMIT', '100')),
    'export': int(os.getenv('REPORT_EXPORT_LIMIT', '1000')),
    'bestsellers': int(os.getenv('REPORT_BESTSELLERS_LIMIT', '20')),
    'reconciliation_sessions': int(os.getenv('REPORT_RECONCILIATION_LIMIT', '50')),
    'cache_size': int(os.getenv('REPORT_CACHE_SIZE', '50')),
    'cache_ttl': int(os.getenv('REPORT_CACHE_TTL', '300')),  # 5 minutes
}
