"""
Theme Settings UI for Kiosk POS.
Allows users to select and preview different color themes.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.theme import (
    THEMES, get_available_themes, get_current_theme_name,
    get_theme_colors, set_theme, apply_theme_to_root, get_status_color
)


class ThemeSettingsFrame(ttk.Frame):
    """UI for selecting and previewing application themes."""
    
    def __init__(self, parent):
        super().__init__(parent, padding=20)
        self.parent = parent
        self.current_theme = get_current_theme_name()
        self.selected_theme = tk.StringVar(value=self.current_theme)
        self._build_ui()
    
    def _build_ui(self):
        """Build the theme settings interface."""
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        # Apply themed radiobutton style
        colors = get_theme_colors()
        style = ttk.Style(self)
        style.configure("Theme.TRadiobutton",
                        background=colors.get('background', '#f5f5f5'),
                        foreground=colors.get('text', '#1f2937'),
                        indicatorcolor=colors.get('surface', '#ffffff'),
                        font=("Segoe UI", 10))
        style.map("Theme.TRadiobutton",
                  background=[("!disabled", colors.get('background', '#f5f5f5'))],
                  foreground=[("!disabled", colors.get('text', '#1f2937'))],
                  indicatorcolor=[
                      ("selected", colors.get('sidebar_active', '#475569')),
                      ("!selected", colors.get('surface', '#ffffff')),
                  ])
        
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="🎨 Theme Settings", 
                 font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(header_frame, text="Select a color theme for the application",
                 font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(5, 0))
        
        # === Action buttons FIRST (always visible at top) ===
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Left side - Reset
        ttk.Button(button_frame, text="🔄 Reset to Default",
                  command=self._reset_theme, width=20).pack(side=tk.LEFT)
        
        # Right side - Save buttons
        ttk.Button(button_frame, text="💾 Save & Restart", 
                  command=self._save_and_restart, width=18).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="✅ Apply Theme", 
                  command=self._apply_theme, width=18).pack(side=tk.RIGHT)
        
        # Tip
        ttk.Label(self, text="💡 Tip: Click 'Apply Theme' to preview, or 'Save & Restart' for full effect.",
                 font=("Segoe UI", 9), foreground=get_status_color("text_light")).pack(fill=tk.X, pady=(0, 10))
        
        # Separator
        ttk.Separator(self, orient='horizontal').pack(fill=tk.X, pady=(0, 10))
        
        # Main content area (scrollable part below buttons)
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=2)
        
        # Left side - Theme selection
        selection_frame = ttk.LabelFrame(content_frame, text="Available Themes", padding=10)
        selection_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 15), pady=(0, 15))
        
        themes = get_available_themes()
        for i, (theme_id, theme_name) in enumerate(themes.items()):
            rb = ttk.Radiobutton(selection_frame, text=theme_name,
                                variable=self.selected_theme, value=theme_id,
                                command=self._on_theme_selected,
                                style="Theme.TRadiobutton")
            rb.pack(anchor=tk.W, pady=5)
            
            # Mark current theme
            if theme_id == self.current_theme:
                ttk.Label(selection_frame, text="(Current)", 
                         font=("Segoe UI", 8)).pack(anchor=tk.W, padx=(25, 0))
        
        # Right side - Preview
        self.preview_frame = ttk.LabelFrame(content_frame, text="Preview", padding=15)
        self.preview_frame.grid(row=0, column=1, sticky=tk.NSEW, pady=(0, 15))
        
        self._update_preview()
        
        # Color palette display
        palette_frame = ttk.LabelFrame(content_frame, text="Color Palette", padding=10)
        palette_frame.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 15))
        
        self.palette_container = ttk.Frame(palette_frame)
        self.palette_container.pack(fill=tk.X)
        
        self._update_palette()
    
    def _on_theme_selected(self):
        """Handle theme selection change."""
        self._update_preview()
        self._update_palette()
    
    def _update_preview(self):
        """Update the preview panel with selected theme colors."""
        # Clear existing preview
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        theme_id = self.selected_theme.get()
        colors = get_theme_colors(theme_id)
        theme_name = THEMES[theme_id]["name"]
        
        # Preview container
        preview = tk.Frame(self.preview_frame, bg=colors['background'], 
                          relief='solid', borderwidth=1)
        preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Header preview
        header = tk.Frame(preview, bg=colors['sidebar_bg'], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text=f"🏪 {theme_name} Theme", 
                bg=colors['sidebar_bg'], fg=colors['sidebar_text'],
                font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=10, pady=8)
        
        # Content preview
        content = tk.Frame(preview, bg=colors['background'])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sample card
        card = tk.Frame(content, bg=colors['surface'], relief='solid', borderwidth=1,
                       highlightbackground=colors['border'], highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 10))
        
        card_inner = tk.Frame(card, bg=colors['surface'])
        card_inner.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(card_inner, text="Sample Card", bg=colors['surface'],
                fg=colors['text'], font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        tk.Label(card_inner, text="This is secondary text", bg=colors['surface'],
                fg=colors['text_secondary'], font=("Segoe UI", 9)).pack(anchor=tk.W)
        
        # Sample buttons
        btn_frame = tk.Frame(content, bg=colors['background'])
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Primary button
        primary_btn = tk.Label(btn_frame, text="Primary", bg=colors['primary'],
                              fg=colors['text_white'], font=("Segoe UI", 9),
                              padx=12, pady=4, cursor='hand2')
        primary_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Success button
        success_btn = tk.Label(btn_frame, text="Success", bg=colors['success'],
                              fg=colors['text_white'], font=("Segoe UI", 9),
                              padx=12, pady=4, cursor='hand2')
        success_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Danger button
        danger_btn = tk.Label(btn_frame, text="Danger", bg=colors['danger'],
                             fg=colors['text_white'], font=("Segoe UI", 9),
                             padx=12, pady=4, cursor='hand2')
        danger_btn.pack(side=tk.LEFT)
    
    def _update_palette(self):
        """Update the color palette display."""
        # Clear existing
        for widget in self.palette_container.winfo_children():
            widget.destroy()
        
        theme_id = self.selected_theme.get()
        colors = get_theme_colors(theme_id)
        
        # Key colors to display
        key_colors = [
            ("Primary", colors['primary']),
            ("Secondary", colors['secondary']),
            ("Background", colors['background']),
            ("Surface", colors['surface']),
            ("Success", colors['success']),
            ("Warning", colors['warning']),
            ("Danger", colors['danger']),
            ("Info", colors['info']),
            ("Sidebar", colors['sidebar_bg']),
            ("Accent", colors['accent']),
        ]
        
        row_frame = ttk.Frame(self.palette_container)
        row_frame.pack(fill=tk.X)
        
        for i, (name, color) in enumerate(key_colors):
            color_frame = ttk.Frame(row_frame)
            color_frame.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Color swatch
            swatch = tk.Frame(color_frame, bg=color, width=40, height=40,
                            relief='solid', borderwidth=1)
            swatch.pack()
            swatch.pack_propagate(False)
            
            # Color label
            ttk.Label(color_frame, text=name, font=("Segoe UI", 8)).pack()
            ttk.Label(color_frame, text=color, font=("Segoe UI", 7)).pack()
    
    def _apply_theme(self):
        """Apply the selected theme."""
        theme_id = self.selected_theme.get()
        
        if set_theme(theme_id):
            self.current_theme = theme_id
            
            # Apply to root window
            root = self.winfo_toplevel()
            apply_theme_to_root(root, theme_id)
            
            # Try to refresh the shell's nav buttons if AppShell exists
            try:
                from ui.shell import AppShell
                for child in root.winfo_children():
                    if isinstance(child, AppShell):
                        child.refresh_theme()
                        break
            except Exception:
                pass  # Shell refresh is optional
            
            messagebox.showinfo("Theme Applied", 
                              f"Theme '{THEMES[theme_id]['name']}' has been applied.\n\n"
                              "Some changes may require restarting the application.")
            
            # Refresh the frame
            self._build_ui()
        else:
            messagebox.showerror("Error", "Failed to apply theme.")
    
    def _save_and_restart(self):
        """Save the selected theme and restart the application."""
        theme_id = self.selected_theme.get()
        
        if set_theme(theme_id):
            if messagebox.askyesno("Restart Required", 
                                  f"Theme '{THEMES[theme_id]['name']}' has been saved.\n\n"
                                  "Restart the application now to apply all changes?"):
                # Restart the application
                from main import restart_application
                root = self.winfo_toplevel()
                restart_application(root)
        else:
            messagebox.showerror("Error", "Failed to save theme.")
    
    def _reset_theme(self):
        """Reset to default theme."""
        self.selected_theme.set("default")
        self._on_theme_selected()
    
    def refresh(self):
        """Refresh the settings from database."""
        self.current_theme = get_current_theme_name()
        self.selected_theme.set(self.current_theme)
        self._update_preview()
        self._update_palette()
