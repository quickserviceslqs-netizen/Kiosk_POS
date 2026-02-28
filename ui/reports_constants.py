"""Constants and configuration for the reports module."""

import os
from typing import Dict, Any

# UI Constants
WINDOW_PADDING = (20, 20, 20, 20)
HEADER_PADDING = (0, 20)
SIDEBAR_PADDING = (0, 20)
CARD_PADDING = (15, 15, 15, 15)
BUTTON_PADDING = 6
ACTION_BUTTON_PADDING = (10, 5)

# Layout Constants
SIDEBAR_WIDTH = 250
REPORT_HEIGHT = 400
MAX_RECORDS_DISPLAY = 100
MAX_RECORDS_EXPORT = 1000

# Font Sizes
FONT_SIZES = {
    'header': 16,
    'subheader': 12,
    'body': 10,
    'caption': 9,
    'large_value': 18
}

# Colors (matching main app)
COLORS = {
    'primary': '#1976D2',
    'primary_light': '#BBDEFB',
    'secondary': '#757575',
    'success': '#4CAF50',
    'warning': '#FF9800',
    'danger': '#F44336',
    'background': '#F5F5F5',
    'surface': '#FFFFFF',
    'text': '#212121',
    'text_light': '#757575',
    'border': '#E0E0E0',
    'selected': '#E3F2FD'
}

# Style Names
STYLES = {
    # Use the default frame style so the reports UI matches other modules
    'frame': 'TFrame',
    'card': 'Card.TLabelframe',
    # Sidebar-specific card style so the categories area can inherit the
    # shared app background (keeps other cards white)
    'sidebar_card': 'Reports.Sidebar.TLabelframe',
    'primary_button': 'Primary.TButton',
    'secondary_button': 'Secondary.TButton',
    'action_button': 'Action.TButton',
    'header_label': 'Header.TLabel',
    'subheader_label': 'Subheader.TLabel',
    'body_label': 'Body.TLabel',
    'caption_label': 'Caption.TLabel'
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
    'inventory_value': 'Inventory Value'
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
