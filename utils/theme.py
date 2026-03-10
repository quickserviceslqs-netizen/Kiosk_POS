"""
Theme management for Kiosk POS application.
Provides centralized theming with predefined color schemes.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
from database.init_db import get_connection
import logging

logger = logging.getLogger(__name__)

# Default theme name
DEFAULT_THEME = "default"

# Theme definitions
THEMES: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "Default",
        "background": "#f5f5f5",
        "surface": "#ffffff",
        "primary": "#2563eb",
        "primary_light": "#dbeafe",
        "primary_dark": "#1e40af",
        "secondary": "#64748b",
        "success": "#10b981",
        "success_bg": "#d1fae5",
        "warning": "#f59e0b",
        "warning_bg": "#fef3c7",
        "danger": "#ef4444",
        "danger_bg": "#fee2e2",
        "info": "#0ea5e9",
        "info_bg": "#e0f2fe",
        "neutral_bg": "#e5e7eb",
        "text": "#1f2937",
        "text_secondary": "#6b7280",
        "text_light": "#9ca3af",
        "text_white": "#ffffff",
        "border": "#e5e7eb",
        "sidebar_bg": "#1e293b",
        "sidebar_text": "#e2e8f0",
        "sidebar_hover": "#334155",
        "sidebar_active": "#475569",
        "table_header": "#f1f5f9",
        "table_row_alt": "#f8fafc",
        "accent": "#8b5cf6",
        "field_bg": "#ffffff",
        "field_text": "#1f2937",
        "chart_bar": "#2563eb",
        "chart_bar_edge": "#1e40af",
        "chart_bar_alt": "#f59e0b",
        "chart_bar_alt_edge": "#d97706",
        "chart_text_muted": "#6b7280",
        "chart_palette": "#2563eb,#10b981,#f59e0b,#ef4444,#8b5cf6,#0ea5e9,#64748b,#ec4899,#14b8a6,#f97316",
        "tooltip_bg": "#fef3c7",
        "disabled_bg": "#e5e7eb",
    },
    "dark": {
        "name": "Dark",
        "background": "#1a1a2e",
        "surface": "#16213e",
        "primary": "#4f46e5",
        "primary_light": "#312e81",
        "primary_dark": "#6366f1",
        "secondary": "#64748b",
        "success": "#059669",
        "success_bg": "#064e3b",
        "warning": "#d97706",
        "warning_bg": "#78350f",
        "danger": "#dc2626",
        "danger_bg": "#7f1d1d",
        "info": "#0284c7",
        "info_bg": "#0c4a6e",
        "neutral_bg": "#374151",
        "text": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_light": "#64748b",
        "text_white": "#ffffff",
        "border": "#334155",
        "sidebar_bg": "#0f172a",
        "sidebar_text": "#e2e8f0",
        "sidebar_hover": "#1e293b",
        "sidebar_active": "#334155",
        "table_header": "#1e293b",
        "table_row_alt": "#0f172a",
        "accent": "#a78bfa",
        "field_bg": "#1e293b",
        "field_text": "#f1f5f9",
        "chart_bar": "#6366f1",
        "chart_bar_edge": "#4f46e5",
        "chart_bar_alt": "#f59e0b",
        "chart_bar_alt_edge": "#d97706",
        "chart_text_muted": "#94a3b8",
        "chart_palette": "#6366f1,#34d399,#fbbf24,#f87171,#a78bfa,#38bdf8,#94a3b8,#f472b6,#2dd4bf,#fb923c",
        "tooltip_bg": "#78350f",
        "disabled_bg": "#374151",
    },
    "light": {
        "name": "Light",
        "background": "#ffffff",
        "surface": "#f8fafc",
        "primary": "#3b82f6",
        "primary_light": "#eff6ff",
        "primary_dark": "#1d4ed8",
        "secondary": "#71717a",
        "success": "#22c55e",
        "success_bg": "#dcfce7",
        "warning": "#eab308",
        "warning_bg": "#fef9c3",
        "danger": "#f43f5e",
        "danger_bg": "#ffe4e6",
        "info": "#06b6d4",
        "info_bg": "#cffafe",
        "neutral_bg": "#e4e4e7",
        "text": "#18181b",
        "text_secondary": "#52525b",
        "text_light": "#a1a1aa",
        "text_white": "#ffffff",
        "border": "#e4e4e7",
        "sidebar_bg": "#f4f4f5",
        "sidebar_text": "#27272a",
        "sidebar_hover": "#e4e4e7",
        "sidebar_active": "#eff6ff",
        "table_header": "#fafafa",
        "table_row_alt": "#f4f4f5",
        "accent": "#8b5cf6",
        "field_bg": "#ffffff",
        "field_text": "#18181b",
        "chart_bar": "#3b82f6",
        "chart_bar_edge": "#1d4ed8",
        "chart_bar_alt": "#eab308",
        "chart_bar_alt_edge": "#ca8a04",
        "chart_text_muted": "#71717a",
        "chart_palette": "#3b82f6,#22c55e,#eab308,#f43f5e,#8b5cf6,#06b6d4,#71717a,#ec4899,#14b8a6,#f97316",
        "tooltip_bg": "#fef9c3",
        "disabled_bg": "#e4e4e7",
    },
    "blue": {
        "name": "Ocean Blue",
        "background": "#f0f9ff",
        "surface": "#ffffff",
        "primary": "#0284c7",
        "primary_light": "#e0f2fe",
        "primary_dark": "#0369a1",
        "secondary": "#64748b",
        "success": "#059669",
        "success_bg": "#d1fae5",
        "warning": "#d97706",
        "warning_bg": "#fef3c7",
        "danger": "#dc2626",
        "danger_bg": "#fee2e2",
        "info": "#0ea5e9",
        "info_bg": "#e0f2fe",
        "neutral_bg": "#e5e7eb",
        "text": "#0c4a6e",
        "text_secondary": "#0369a1",
        "text_light": "#7dd3fc",
        "text_white": "#ffffff",
        "border": "#bae6fd",
        "sidebar_bg": "#0c4a6e",
        "sidebar_text": "#f0f9ff",
        "sidebar_hover": "#075985",
        "sidebar_active": "#0ea5e9",
        "table_header": "#e0f2fe",
        "table_row_alt": "#f0f9ff",
        "accent": "#6366f1",
        "field_bg": "#ffffff",
        "field_text": "#0c4a6e",
        "chart_bar": "#0284c7",
        "chart_bar_edge": "#0369a1",
        "chart_bar_alt": "#d97706",
        "chart_bar_alt_edge": "#b45309",
        "chart_text_muted": "#64748b",
        "chart_palette": "#0284c7,#059669,#d97706,#dc2626,#6366f1,#0ea5e9,#64748b,#ec4899,#14b8a6,#f97316",
        "tooltip_bg": "#fef3c7",
        "disabled_bg": "#e5e7eb",
    },
    "green": {
        "name": "Forest Green",
        "background": "#f0fdf4",
        "surface": "#ffffff",
        "primary": "#059669",
        "primary_light": "#dcfce7",
        "primary_dark": "#047857",
        "secondary": "#64748b",
        "success": "#22c55e",
        "success_bg": "#dcfce7",
        "warning": "#eab308",
        "warning_bg": "#fef9c3",
        "danger": "#ef4444",
        "danger_bg": "#fee2e2",
        "info": "#0ea5e9",
        "info_bg": "#e0f2fe",
        "neutral_bg": "#e5e7eb",
        "text": "#14532d",
        "text_secondary": "#166534",
        "text_light": "#86efac",
        "text_white": "#ffffff",
        "border": "#bbf7d0",
        "sidebar_bg": "#14532d",
        "sidebar_text": "#f0fdf4",
        "sidebar_hover": "#166534",
        "sidebar_active": "#22c55e",
        "table_header": "#dcfce7",
        "table_row_alt": "#f0fdf4",
        "accent": "#a78bfa",
        "field_bg": "#ffffff",
        "field_text": "#14532d",
        "chart_bar": "#059669",
        "chart_bar_edge": "#047857",
        "chart_bar_alt": "#eab308",
        "chart_bar_alt_edge": "#ca8a04",
        "chart_text_muted": "#64748b",
        "chart_palette": "#059669,#3b82f6,#eab308,#ef4444,#a78bfa,#0ea5e9,#64748b,#ec4899,#14b8a6,#f97316",
        "tooltip_bg": "#fef9c3",
        "disabled_bg": "#e5e7eb",
    },
    "purple": {
        "name": "Royal Purple",
        "background": "#faf5ff",
        "surface": "#ffffff",
        "primary": "#7c3aed",
        "primary_light": "#ede9fe",
        "primary_dark": "#6d28d9",
        "secondary": "#64748b",
        "success": "#10b981",
        "success_bg": "#d1fae5",
        "warning": "#f59e0b",
        "warning_bg": "#fef3c7",
        "danger": "#ef4444",
        "danger_bg": "#fee2e2",
        "info": "#0ea5e9",
        "info_bg": "#e0f2fe",
        "neutral_bg": "#e5e7eb",
        "text": "#581c87",
        "text_secondary": "#6b21a8",
        "text_light": "#c4b5fd",
        "text_white": "#ffffff",
        "border": "#ddd6fe",
        "sidebar_bg": "#581c87",
        "sidebar_text": "#faf5ff",
        "sidebar_hover": "#6b21a8",
        "sidebar_active": "#a855f7",
        "table_header": "#ede9fe",
        "table_row_alt": "#faf5ff",
        "accent": "#ec4899",
        "field_bg": "#ffffff",
        "field_text": "#581c87",
        "chart_bar": "#7c3aed",
        "chart_bar_edge": "#6d28d9",
        "chart_bar_alt": "#f59e0b",
        "chart_bar_alt_edge": "#d97706",
        "chart_text_muted": "#64748b",
        "chart_palette": "#7c3aed,#10b981,#f59e0b,#ef4444,#ec4899,#0ea5e9,#64748b,#3b82f6,#14b8a6,#f97316",
        "tooltip_bg": "#fef3c7",
        "disabled_bg": "#e5e7eb",
    },
    "high_contrast": {
        "name": "High Contrast",
        "background": "#ffffff",
        "surface": "#ffffff",
        "primary": "#000000",
        "primary_light": "#f0f0f0",
        "primary_dark": "#000000",
        "secondary": "#333333",
        "success": "#006400",
        "success_bg": "#90EE90",
        "warning": "#cc7000",
        "warning_bg": "#FFE4B5",
        "danger": "#cc0000",
        "danger_bg": "#FFB6C1",
        "info": "#0066cc",
        "info_bg": "#ADD8E6",
        "neutral_bg": "#d0d0d0",
        "text": "#000000",
        "text_secondary": "#333333",
        "text_light": "#666666",
        "text_white": "#ffffff",
        "border": "#000000",
        "sidebar_bg": "#000000",
        "sidebar_text": "#ffffff",
        "sidebar_hover": "#333333",
        "sidebar_active": "#0066cc",
        "table_header": "#e0e0e0",
        "table_row_alt": "#f0f0f0",
        "accent": "#0066cc",
        "field_bg": "#ffffff",
        "field_text": "#000000",
        "chart_bar": "#000000",
        "chart_bar_edge": "#333333",
        "chart_bar_alt": "#cc7000",
        "chart_bar_alt_edge": "#994800",
        "chart_text_muted": "#666666",
        "chart_palette": "#000000,#006400,#cc7000,#cc0000,#0066cc,#333333,#666666,#994800,#004040,#990000",
        "tooltip_bg": "#FFE4B5",
        "disabled_bg": "#d0d0d0",
    },
}

# Current active theme cache
_current_theme: Optional[str] = None
_current_colors: Optional[Dict[str, str]] = None


def get_available_themes() -> Dict[str, str]:
    """Return dict of theme_id -> theme_name."""
    return {k: v["name"] for k, v in THEMES.items()}


def get_current_theme_name() -> str:
    """Get the current theme name from database."""
    global _current_theme
    if _current_theme:
        return _current_theme
    
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'theme'")
            row = cursor.fetchone()
            if row:
                theme = row['value'] if isinstance(row, dict) else row[0]
                if theme in THEMES:
                    _current_theme = theme
                    return theme
    except Exception as e:
        logger.debug(f"Could not load theme from database: {e}")
    
    _current_theme = DEFAULT_THEME
    return DEFAULT_THEME


def get_theme_colors(theme_name: Optional[str] = None) -> Dict[str, str]:
    """Get colors for a theme. If no theme specified, use current theme."""
    global _current_colors
    
    if theme_name is None:
        theme_name = get_current_theme_name()
    
    if theme_name == _current_theme and _current_colors:
        return _current_colors
    
    colors = THEMES.get(theme_name, THEMES[DEFAULT_THEME]).copy()
    
    if theme_name == get_current_theme_name():
        _current_colors = colors
    
    return colors


def set_theme(theme_name: str) -> bool:
    """Set the current theme and save to database."""
    global _current_theme, _current_colors
    
    if theme_name not in THEMES:
        logger.warning(f"Unknown theme: {theme_name}")
        return False
    
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("theme", theme_name)
            )
            conn.commit()
        
        _current_theme = theme_name
        _current_colors = THEMES[theme_name].copy()
        return True
    except Exception as e:
        logger.exception(f"Failed to save theme: {e}")
        return False


def apply_theme_to_root(root: tk.Tk, theme_name: Optional[str] = None) -> None:
    """Apply theme colors to the root window and ttk styles."""
    colors = get_theme_colors(theme_name)
    
    # Configure root window
    root.configure(bg=colors['background'])
    
    # Configure ttk styles
    style = ttk.Style()
    
    # Frame styles
    style.configure('TFrame', background=colors['background'])
    style.configure('TLabelframe', background=colors['background'])
    style.configure('TLabelframe.Label', background=colors['background'], foreground=colors['text'])
    
    # Label styles
    style.configure('TLabel', background=colors['background'], foreground=colors['text'])
    
    # Button styles - pure white/surface, neutral text + border.
    style.configure('TButton', 
                   background=colors['surface'],
                   foreground=colors['text'],
                   font=('Segoe UI', 10),
                   padding=6,
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['border'],
                   lightcolor=colors['surface'],
                   darkcolor=colors['border'])
    style.map('TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors['surface'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])],
             bordercolor=[('disabled', colors['border']),
                          ('!disabled', colors['border'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors['border'])])
    
    # Primary button style - white surface, neutral text, bold
    style.configure('Primary.TButton',
                   background=colors['surface'],
                   foreground=colors['text'],
                   font=('Segoe UI', 10, 'bold'),
                   padding=(10, 6),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['border'],
                   lightcolor=colors['surface'],
                   darkcolor=colors['border'])
    style.map('Primary.TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors['surface'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])],
             bordercolor=[('!disabled', colors['border'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors['border'])])
    
    # Secondary/neutral button style - light neutral
    style.configure('Secondary.TButton',
                   background=colors.get('neutral_bg', colors['border']),
                   foreground=colors['text'],
                   font=('Segoe UI', 10),
                   padding=(10, 6),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['border'],
                   lightcolor=colors['surface'],
                   darkcolor=colors.get('neutral_bg', colors['border']))
    style.map('Secondary.TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors.get('neutral_bg', colors['border']))],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors.get('neutral_bg', colors['border']))])
    
    # Success button style - pure white/surface with success text
    style.configure('Success.TButton',
                   background=colors['surface'],
                   foreground=colors['success'],
                   font=('Segoe UI', 10),
                   padding=(10, 6),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['success'],
                   lightcolor=colors['surface'],
                   darkcolor=colors['surface'])
    style.map('Success.TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors['surface'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['success'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors['surface'])])
    
    # Danger/Red button style - pure white/surface with danger text
    style.configure('Danger.TButton',
                   background=colors['surface'],
                   foreground=colors['danger'],
                   font=('Segoe UI', 10),
                   padding=(10, 6),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['danger'],
                   lightcolor=colors['surface'],
                   darkcolor=colors['surface'])
    style.map('Danger.TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors['surface'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['danger'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors['surface'])])
    style.configure('Red.TButton',
                   foreground=colors['danger'])
    style.map('Red.TButton',
             foreground=[('active', colors['danger']), ('pressed', colors['danger'])])
    
    # Warning button style - pure white/surface with warning text
    style.configure('Warning.TButton',
                   background=colors['surface'],
                   foreground=colors['warning'],
                   font=('Segoe UI', 10),
                   padding=(10, 6),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['warning'],
                   lightcolor=colors['surface'],
                   darkcolor=colors['surface'])
    style.map('Warning.TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors['surface'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['warning'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors['surface'])])
    
    # Accent button style - white surface, neutral text, bold
    style.configure('Accent.TButton',
                   background=colors['surface'],
                   foreground=colors['text'],
                   font=('Segoe UI', 10, 'bold'),
                   padding=(10, 6),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['border'],
                   lightcolor=colors['surface'],
                   darkcolor=colors['border'])
    style.map('Accent.TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors['surface'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors['border'])])
    
    # Action button style (compact) - white surface, neutral text, smaller font
    style.configure('Action.TButton',
                   background=colors['surface'],
                   foreground=colors['text'],
                   font=('Segoe UI', 9),
                   padding=(8, 4),
                   relief='raised',
                   borderwidth=1,
                   focuscolor='none',
                   bordercolor=colors['border'],
                   lightcolor=colors['surface'],
                   darkcolor=colors['border'])
    style.map('Action.TButton',
             background=[('disabled', colors.get('disabled_bg', colors['border'])),
                         ('!disabled', colors['surface'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])],
             bordercolor=[('!disabled', colors['border'])],
             lightcolor=[('!disabled', colors['surface'])],
             darkcolor=[('!disabled', colors['border'])])
    
    # Entry styles
    style.configure('TEntry',
                   fieldbackground=colors.get('field_bg', colors['surface']),
                   foreground=colors.get('field_text', colors['text']),
                   insertcolor=colors.get('field_text', colors['text']),
                   bordercolor=colors['border'])
    
    # Combobox styles
    style.configure('TCombobox',
                   fieldbackground=colors.get('field_bg', colors['surface']),
                   foreground=colors.get('field_text', colors['text']),
                   background=colors['surface'],
                   selectbackground=colors['primary'],
                   selectforeground=colors['text_white'],
                   insertcolor=colors.get('field_text', colors['text']),
                   bordercolor=colors['border'],
                   arrowcolor=colors['text'],
                   lightcolor=colors.get('field_bg', colors['surface']),
                   darkcolor=colors['border'])
    style.map('TCombobox',
             fieldbackground=[('readonly', colors.get('field_bg', colors['surface'])),
                              ('!disabled', colors.get('field_bg', colors['surface']))],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors.get('field_text', colors['text']))],
             selectbackground=[('!disabled', colors['primary'])],
             selectforeground=[('!disabled', colors['text_white'])],
             bordercolor=[('!disabled', colors['border'])],
             arrowcolor=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])])
    # Style the dropdown popup listbox (plain tk widget inside ttk.Combobox)
    root.option_add('*TCombobox*Listbox.background', colors.get('field_bg', colors['surface']))
    root.option_add('*TCombobox*Listbox.foreground', colors.get('field_text', colors['text']))
    root.option_add('*TCombobox*Listbox.selectBackground', colors['primary'])
    root.option_add('*TCombobox*Listbox.selectForeground', colors['text_white'])
    root.option_add('*TCombobox*Listbox.font', 'TkDefaultFont')

    # ── Global tk (non-ttk) widget defaults ─────────────────────────────────
    # These apply to ALL windows (including Toplevels) unless a widget is
    # explicitly configured with a different color.
    bg        = colors['background']
    fg        = colors['text']
    field_bg  = colors.get('field_bg', colors['surface'])
    field_fg  = colors.get('field_text', fg)
    sel_bg    = colors.get('primary_light', colors['primary'])
    sel_fg    = fg
    root.option_add('*Toplevel.Background',       bg)
    root.option_add('*Frame.Background',         bg)
    root.option_add('*Label.Background',         bg)
    root.option_add('*Label.Foreground',         fg)
    root.option_add('*Canvas.Background',        bg)
    root.option_add('*Scrollbar.Background',     bg)
    root.option_add('*Scrollbar.Troughcolor',    colors.get('neutral_bg', colors['border']))
    root.option_add('*Scrollbar.ActiveBackground', colors.get('border', '#e5e7eb'))
    root.option_add('*Listbox.Background',       field_bg)
    root.option_add('*Listbox.Foreground',       field_fg)
    root.option_add('*Listbox.selectBackground', sel_bg)
    root.option_add('*Listbox.selectForeground', sel_fg)
    root.option_add('*Entry.Background',         field_bg)
    root.option_add('*Entry.Foreground',         field_fg)
    root.option_add('*Entry.insertBackground',   field_fg)
    root.option_add('*Text.Background',          field_bg)
    root.option_add('*Text.Foreground',          field_fg)
    root.option_add('*Text.insertBackground',    field_fg)
    root.option_add('*Text.selectBackground',    colors['primary'])
    root.option_add('*Text.selectForeground',    colors['text_white'])

    # Treeview styles
    style.configure('Treeview',
                   background=colors['surface'],
                   foreground=colors['text'],
                   fieldbackground=colors['surface'],
                   rowheight=28)
    style.configure('Treeview.Heading',
                   background=colors['table_header'],
                   foreground=colors['text'])
    style.map('Treeview',
             background=[('selected', colors['primary_light'])],
             foreground=[('selected', colors['text'])])
    
    # Spinbox styles
    style.configure('TSpinbox',
                   fieldbackground=colors.get('field_bg', colors['surface']),
                   foreground=colors.get('field_text', colors['text']),
                   insertcolor=colors.get('field_text', colors['text']))
    
    # Notebook styles - white surface, neutral text, no color highlights
    style.configure('TNotebook', background=colors['background'])
    style.configure('TNotebook.Tab',
                   background=colors['surface'],
                   foreground=colors['text'],
                   padding=[12, 6])
    style.map('TNotebook.Tab',
             background=[('selected', colors['surface'])],
             foreground=[('selected', colors['text'])])

    # Checkbutton / Radiobutton styles
    style.configure('TCheckbutton',
                   background=colors['background'],
                   foreground=colors['text'],
                   focuscolor='none')
    style.map('TCheckbutton',
             background=[('active', colors['background']),
                         ('!disabled', colors['background'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])])
    style.configure('TRadiobutton',
                   background=colors['background'],
                   foreground=colors['text'],
                   focuscolor='none')
    style.map('TRadiobutton',
             background=[('active', colors['background']),
                         ('!disabled', colors['background'])],
             foreground=[('disabled', colors['text_light']),
                         ('!disabled', colors['text'])])

    # PanedWindow styles
    style.configure('TPanedwindow', background=colors['background'])
    style.configure('Sash', sashthickness=5, sashpad=2,
                   background=colors.get('border', colors['background']))

    # Plain tk Checkbutton / Radiobutton option defaults
    root.option_add('*Checkbutton.Background',       colors['background'])
    root.option_add('*Checkbutton.Foreground',       colors['text'])
    root.option_add('*Checkbutton.activeBackground', colors['background'])
    root.option_add('*Checkbutton.activeForeground', colors['text'])
    root.option_add('*Checkbutton.selectColor',      colors.get('surface', '#ffffff'))
    root.option_add('*Radiobutton.Background',       colors['background'])
    root.option_add('*Radiobutton.Foreground',       colors['text'])
    root.option_add('*Radiobutton.activeBackground', colors['background'])
    root.option_add('*Radiobutton.activeForeground', colors['text'])
    root.option_add('*Radiobutton.selectColor',      colors.get('primary', '#2563eb'))


def apply_theme_to_window(win, colors: Optional[Dict[str, str]] = None) -> None:
    """Apply theme background/foreground to a Toplevel (or any tk widget).

    Call this immediately after creating a ``tk.Toplevel`` and before adding
    any child widgets so the window chrome and all descendant plain-tk widgets
    pick up the current theme colours.

    Args:
        win:    The ``tk.Toplevel`` or other container to theme.
        colors: Optional pre-fetched colour dict; fetched automatically when
                omitted.
    """
    if colors is None:
        colors = get_theme_colors()
    bg       = colors['background']
    fg       = colors['text']
    field_bg = colors.get('field_bg', colors['surface'])
    field_fg = colors.get('field_text', fg)
    sel_bg   = colors.get('primary_light', colors['primary'])

    try:
        win.configure(bg=bg)
    except Exception:
        pass

    # Override option database for widgets created inside this window
    win.option_add('*Frame.Background',         bg)
    win.option_add('*Label.Background',         bg)
    win.option_add('*Label.Foreground',         fg)
    win.option_add('*Canvas.Background',        bg)
    win.option_add('*Scrollbar.Background',     bg)
    win.option_add('*Scrollbar.Troughcolor',    colors.get('neutral_bg', colors['border']))
    win.option_add('*Listbox.Background',       field_bg)
    win.option_add('*Listbox.Foreground',       field_fg)
    win.option_add('*Listbox.selectBackground', sel_bg)
    win.option_add('*Listbox.selectForeground', fg)
    win.option_add('*Entry.Background',         field_bg)
    win.option_add('*Entry.Foreground',         field_fg)
    win.option_add('*Entry.insertBackground',   field_fg)
    win.option_add('*Text.Background',          field_bg)
    win.option_add('*Text.Foreground',          field_fg)
    win.option_add('*Text.insertBackground',    field_fg)
    win.option_add('*Text.selectBackground',    colors['primary'])
    win.option_add('*Text.selectForeground',    colors['text_white'])
    win.option_add('*Checkbutton.Background',       colors['background'])
    win.option_add('*Checkbutton.Foreground',       colors['text'])
    win.option_add('*Checkbutton.activeBackground', colors['background'])
    win.option_add('*Checkbutton.activeForeground', colors['text'])
    win.option_add('*Checkbutton.selectColor',      colors.get('surface', '#ffffff'))
    win.option_add('*Radiobutton.Background',       colors['background'])
    win.option_add('*Radiobutton.Foreground',       colors['text'])
    win.option_add('*Radiobutton.activeBackground', colors['background'])
    win.option_add('*Radiobutton.activeForeground', colors['text'])


def clear_theme_cache() -> None:
    """Clear the cached theme to force reload from database."""
    global _current_theme, _current_colors
    _current_theme = None
    _current_colors = None


def get_status_color(status: str) -> str:
    """
    Get theme-aware color for status/semantic color names.
    Maps common color names to theme colors.
    
    Args:
        status: Color name ('blue', 'green', 'red', 'orange', 'gray', 'success', 'danger', 'warning', 'info', etc.)
    
    Returns:
        Theme-appropriate hex color value
    """
    colors = get_theme_colors()
    
    # Map common color names to theme colors
    status_map = {
        'blue': colors.get('info', colors.get('primary', '#0ea5e9')),
        'green': colors.get('success', '#10b981'),
        'red': colors.get('danger', '#ef4444'),
        'orange': colors.get('warning', '#f59e0b'),
        'gray': colors.get('text_light', '#9ca3af'),
        'success': colors.get('success', '#10b981'),
        'danger': colors.get('danger', '#ef4444'),
        'warning': colors.get('warning', '#f59e0b'),
        'info': colors.get('info', '#0ea5e9'),
        'primary': colors.get('primary', '#2563eb'),
        'secondary': colors.get('secondary', '#64748b'),
        'accent': colors.get('accent', '#8b5cf6'),
        'text': colors.get('text', '#1f2937'),
        'text_light': colors.get('text_light', '#9ca3af'),
    }
    
    return status_map.get(status.lower(), colors.get('text_light', '#9ca3af'))
