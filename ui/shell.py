from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def _get_shell_colors():
    """Get colors for the shell from the theme system."""
    try:
        from utils.theme import get_theme_colors
        tc = get_theme_colors()
        return {
            'nav_bg': tc.get('background', '#f5f5f5'),
            'nav_fg': tc.get('text', '#1f2937'),
            'nav_btn_bg': tc.get('surface', '#ffffff'),
            'nav_active': tc.get('sidebar_active', '#475569'),
            'nav_active_fg': tc.get('text_white', '#ffffff') if tc.get('sidebar_text', '#e2e8f0').startswith('#e') or tc.get('sidebar_text', '#e2e8f0').startswith('#f') or tc.get('sidebar_text', '#e2e8f0').startswith('#c') else tc.get('sidebar_text', '#27272a'),
            'nav_brand_fg': tc.get('text', '#1f2937'),
            'nav_user_fg': tc.get('text_secondary', '#6b7280'),
            'header_bg': tc.get('surface', '#FFFFFF'),
            'header_fg': tc.get('text', '#1f2937'),
            'header_sub_fg': tc.get('text_secondary', '#6b7280'),
            'body_bg': tc.get('background', '#f5f5f5'),
            'border': tc.get('border', '#e5e7eb'),
            'accent': tc.get('primary', '#2563eb'),
            'accent_hover': tc.get('primary_dark', '#1e40af'),
            'logout_bg': tc.get('background', '#f5f5f5'),
        }
    except Exception:
        # Fallback colors matching default theme
        return {
            'nav_bg': '#f5f5f5', 'nav_fg': '#1f2937', 'nav_btn_bg': '#ffffff',
            'nav_active': '#475569', 'nav_active_fg': '#ffffff', 'nav_brand_fg': '#1f2937', 'nav_user_fg': '#6b7280',
            'header_bg': '#FFFFFF', 'header_fg': '#1f2937', 'header_sub_fg': '#6b7280',
            'body_bg': '#f5f5f5', 'border': '#e5e7eb', 'accent': '#2563eb', 'accent_hover': '#1e40af',
            'logout_bg': '#f5f5f5',
        }


class AppShell(ttk.Frame):
    """App-wide shell with persistent nav, header, and content host."""

    def __init__(self, master: tk.Misc, *, user: dict, on_nav, on_logout, **kwargs):
        super().__init__(master, padding=0, **kwargs)
        self.user = user
        self.on_nav = on_nav
        self.on_logout = on_logout
        self.current_content = None
        self.content_area: ttk.Frame | None = None
        self.nav_buttons: dict[str, ttk.Button] = {}
        self.active_key: str = "dashboard"
        self.title_var = tk.StringVar(value="")
        self.subtitle_var = tk.StringVar(value="")
        self.nav_history: list[str] = ["dashboard"]  # Track navigation history
        self.cached_frames: dict[str, tk.Widget] = {}  # Cache frames by nav key
        self.colors = _get_shell_colors()
        self._update_banner: tk.Frame | None = None  # Update notification banner

        self._init_styles()
        self._build_ui()

    def _init_styles(self) -> None:
        c = self.colors
        style = ttk.Style(self)
        style.configure("Shell.Header.TFrame", background=c['header_bg'])
        style.configure("Shell.Body.TFrame", background=c['body_bg'])
        style.configure("Shell.Title.TLabel", font=("Segoe UI", 18, "bold"), background=c['header_bg'], foreground=c['header_fg'])
        style.configure("Shell.Subtitle.TLabel", font=("Segoe UI", 10), background=c['header_bg'], foreground=c['header_sub_fg'])
        style.configure("Shell.Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 6), background=c.get('header_bg', '#ffffff'), foreground=c.get('header_fg', '#1f2937'), relief='raised', borderwidth=1, focuscolor='none', bordercolor=c.get('border', '#e5e7eb'), lightcolor=c.get('header_bg', '#ffffff'), darkcolor=c.get('border', '#e5e7eb'))
        style.map(
            "Shell.Primary.TButton",
            background=[("!disabled", c.get('header_bg', '#ffffff'))],
            foreground=[("disabled", c.get('header_sub_fg', '#9ca3af')), ("!disabled", c.get('header_fg', '#1f2937'))],
            lightcolor=[("!disabled", c.get('header_bg', '#ffffff'))],
            darkcolor=[("!disabled", c.get('border', '#e5e7eb'))],
        )

    def _build_ui(self) -> None:
        c = self.colors
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)

        self.nav_frame = tk.Frame(self, background=c['nav_bg'])
        self.nav_frame.grid(row=0, column=0, rowspan=2, sticky=tk.NS)

        # Thin separator between nav and content
        from utils.theme import get_theme_colors as _gtc
        _border_col = _gtc().get('border', '#e5e7eb')
        tk.Frame(self, background=_border_col, width=1).grid(row=0, column=1, rowspan=2, sticky=tk.NS)

        brand = ttk.Label(self.nav_frame, text="Kiosk POS", foreground=c['nav_brand_fg'], background=c['nav_bg'], font=("Segoe UI", 12, "bold"))
        brand.pack(fill=tk.X, padx=12, pady=(12, 6))
        user_label = ttk.Label(
            self.nav_frame,
            text=f"{self.user.get('username', 'User')}",
            foreground=c['nav_user_fg'],
            background=c['nav_bg'],
            font=("Segoe UI", 9),
            justify=tk.LEFT,
        )
        user_label.pack(fill=tk.X, padx=12, pady=(0, 8))

        # Demo mode banner — amber strip shown only when launched with --demo
        import sys as _sys
        if '--demo' in _sys.argv:
            demo_bar = tk.Frame(self.nav_frame, bg='#f59e0b')
            demo_bar.pack(fill=tk.X)
            tk.Label(
                demo_bar,
                text='🧪  DEMO MODE',
                bg='#f59e0b', fg='#1c1917',
                font=('Segoe UI', 9, 'bold'),
                pady=4,
            ).pack()
            tk.Label(
                demo_bar,
                text='Not your live data',
                bg='#f59e0b', fg='#44403c',
                font=('Segoe UI', 8),
                pady=2,
            ).pack()
            tk.Frame(demo_bar, bg='#d97706', height=2).pack(fill=tk.X)

            # Switch / Set-Up Live Store button
            import subprocess as _sp, json as _json
            from pathlib import Path as _Path
            _app_dir = _Path(__file__).parent.parent
            _config  = _app_dir / 'config.json'

            def _live_store_ready() -> bool:
                """True when a configured live database with at least one user exists."""
                import sqlite3 as _sqlite3
                try:
                    if not _config.exists():
                        return False
                    _db = _Path(_json.loads(_config.read_text()).get('db_path', ''))
                    if not _db.exists():
                        return False
                    with _sqlite3.connect(_db) as _c:
                        return _c.execute(
                            "SELECT COUNT(*) FROM users WHERE active=1"
                        ).fetchone()[0] > 0
                except Exception:
                    return False

            _live_ready = _live_store_ready()
            _switch_text = '→ Live Store' if _live_ready else '→ Set Up Live Store'
            _switch_tip  = 'Switch to your live store' if _live_ready else 'Configure your real store'

            def _go_live():
                _sp.Popen([_sys.executable,
                           str(_app_dir / 'main.py')])
                self.winfo_toplevel().after(400,
                    lambda: self.winfo_toplevel().destroy())

            switch_btn = tk.Button(
                demo_bar,
                text=_switch_text,
                bg='#1c1917', fg='#fef3c7',
                activebackground='#292524', activeforeground='#fef9c3',
                font=('Segoe UI', 8, 'bold'),
                relief=tk.FLAT, pady=4,
                cursor='hand2',
                command=_go_live,
            )
            switch_btn.pack(fill=tk.X, padx=6, pady=(4, 6))

        import sys as _sys_nav
        nav_items = [
            ("dashboard", "Home"),
            ("pos", "Point of Sale"),
            ("inventory", "Inventory"),
            ("stock_receiving", "Stock Receiving"),
            ("purchase_orders", "Purchase Orders"),
            ("reports", "Reports"),
            ("order_history", "Order History"),
            ("expenses", "Expenses"),
            ("reconciliation", "Payment Reconciliation"),
            ("stock_recon", "Stock Reconciliation"),
            ("backup", "Backup"),
            *([("reset_demo", "Reset Demo")] if '--demo' in _sys_nav.argv else []),
            ("settings", "Settings"),
        ]

        # ── Bottom section: update banner + logout (packed first so it stays visible) ──
        bottom_nav = tk.Frame(self.nav_frame, bg=c['nav_bg'])
        bottom_nav.pack(fill=tk.X, side=tk.BOTTOM)

        # Update notification placeholder (populated by show_update_notification)
        self._update_banner_holder = tk.Frame(bottom_nav, bg=c['nav_bg'])
        self._update_banner_holder.pack(fill=tk.X, padx=8, pady=(0, 4))

        tk.Button(
            bottom_nav,
            text="⏻ Logout",
            anchor="w",
            padx=10,
            pady=8,
            relief=tk.FLAT,
            bd=0,
            bg=c['logout_bg'],
            fg=c['nav_fg'],
            activebackground=c['nav_active'],
            activeforeground=c['nav_active_fg'],
            highlightthickness=0,
            command=self.on_logout,
        ).pack(fill=tk.X, pady=(0, 8))

        # ── Nav items — grid with equal row weights so items fill available space ──
        nav_inner = tk.Frame(self.nav_frame, bg=c['nav_bg'])
        nav_inner.pack(fill=tk.BOTH, expand=True)
        nav_inner.columnconfigure(0, weight=1)

        for i, (key, label) in enumerate(nav_items):
            nav_inner.rowconfigure(i, weight=1)
            btn = tk.Button(
                nav_inner,
                text=label,
                anchor="w",
                padx=10,
                pady=0,
                relief=tk.FLAT,
                bd=0,
                bg=c['nav_btn_bg'],
                fg=c['nav_fg'],
                activebackground=c['nav_active'],
                activeforeground=c['nav_active_fg'],
                highlightthickness=0,
                command=lambda k=key: self._nav(k),
            )
            btn.grid(row=i, column=0, sticky=tk.NSEW)
            self.nav_buttons[key] = btn

        header = ttk.Frame(self, style="Shell.Header.TFrame", padding=(18, 12))
        header.grid(row=0, column=2, sticky=tk.EW)
        header.columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self.title_var, style="Shell.Title.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(header, textvariable=self.subtitle_var, style="Shell.Subtitle.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        self.header_button = ttk.Button(header, text="🏠 Home", style="Shell.Primary.TButton", command=lambda: self._nav("dashboard"))
        self.header_button.grid(row=0, column=1, rowspan=2, sticky=tk.E, padx=(12, 0))

        body = ttk.Frame(self, style="Shell.Body.TFrame", padding=(18, 12))
        body.grid(row=1, column=2, sticky=tk.NSEW)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.content_area = ttk.Frame(body, padding=0, style="Shell.Body.TFrame")
        self.content_area.grid(row=0, column=0, sticky=tk.NSEW)
        self.content_area.columnconfigure(0, weight=1)
        self.content_area.rowconfigure(0, weight=1)

    def _nav(self, key: str) -> None:
        if self.on_nav:
            self.on_nav(key)

    def _active_key(self) -> str:
        return self.active_key

    def activate_nav(self, key: str) -> None:
        # Only track navigation history if we're within Settings
        # For main menu pages, reset the history
        if key not in ["settings", "user_mgmt", "vat_settings", "email_settings", "currency_settings"]:
            # Main menu navigation - reset history
            self.nav_history = [key]
        else:
            # Settings navigation - track history
            if key != self.active_key:
                self.nav_history.append(key)
        
        c = self.colors
        self.active_key = key
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(bg=c['nav_active'], fg=c['nav_active_fg'])
            else:
                btn.configure(bg=c['nav_btn_bg'], fg=c['nav_fg'])

    def go_back(self) -> str | None:
        """Go back to the previous page. Returns the previous page key or None."""
        if len(self.nav_history) > 1:
            self.nav_history.pop()  # Remove current
            prev_key = self.nav_history[-1]  # Get previous
            return prev_key
        return None

    def set_content(self, frame: tk.Widget, *, title: str, subtitle: str | None = None, cache_key: str | None = None) -> None:
        # Hide current content quickly
        if self.current_content:
            try:
                self.current_content.grid_remove()
            except Exception:
                pass

        # If caching is enabled and key provided, store/retrieve from cache
        from_cache = False
        if cache_key:
            if cache_key in self.cached_frames:
                # Use cached frame
                frame = self.cached_frames[cache_key]
                from_cache = True
            else:
                # Cache the new frame
                self.cached_frames[cache_key] = frame

        self.current_content = frame
        frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.title_var.set(title)
        self.subtitle_var.set(subtitle or "")

        # Data loading happens silently without any UI trace - frames handle their own loading when needed

    def set_header_button(self, text: str, command) -> None:
        """Update the header button text and action."""
        self.header_button.configure(text=text, command=command)
        self.header_button_action = command

    def refresh_theme(self) -> None:
        """Refresh shell colors when theme changes."""
        self.colors = _get_shell_colors()
        c = self.colors
        
        # Update nav frame background
        self.nav_frame.configure(background=c['nav_bg'])
        
        # Update all nav buttons
        for key, btn in self.nav_buttons.items():
            if key == self.active_key:
                btn.configure(
                    bg=c['nav_active'],
                    fg=c['nav_brand_fg'],
                    activebackground=c['nav_active'],
                    activeforeground=c['nav_brand_fg']
                )
            else:
                btn.configure(
                    bg=c['nav_btn_bg'],
                    fg=c['nav_fg'],
                    activebackground=c['nav_active'],
                    activeforeground=c['nav_brand_fg']
                )
        
        # Re-init ttk styles
        self._init_styles()

    def show_update_notification(self, info: dict, on_click) -> None:
        """Display an update-available badge at the bottom of the nav bar.

        Args:
            info:     Manifest dict from the update server (must contain 'version').
            on_click: Callable invoked when the user clicks the badge (e.g. open Upgrade Manager).
        """
        self.hide_update_notification()  # remove any previous banner

        version = info.get("version", "?")
        c = self.colors

        # Use warning/success accent colours if present, else fallback
        try:
            from utils.theme import get_theme_colors
            _tc = get_theme_colors()
            bg  = _tc.get("warning", "#f59e0b")
            fg  = "#1f2937"
        except Exception:
            bg, fg = "#f59e0b", "#1f2937"

        banner = tk.Frame(self._update_banner_holder, bg=bg,
                          highlightthickness=1,
                          highlightbackground=bg)
        banner.pack(fill=tk.X)
        self._update_banner = banner

        # Main clickable area
        inner = tk.Frame(banner, bg=bg, cursor="hand2")
        inner.pack(fill=tk.X, padx=6, pady=6)

        tk.Label(inner, text="⬆ Update Available",
                 font=("Segoe UI", 9, "bold"),
                 bg=bg, fg=fg).pack(anchor="w")
        tk.Label(inner, text=f"Version {version} ready to install",
                 font=("Segoe UI", 8),
                 bg=bg, fg=fg).pack(anchor="w")

        inner.bind("<Button-1>", lambda e: on_click())
        for child in inner.winfo_children():
            child.bind("<Button-1>", lambda e: on_click())

        # Dismiss button
        tk.Button(banner, text="✕",
                  font=("Segoe UI", 8), relief=tk.FLAT, bd=0,
                  bg=bg, fg=fg, cursor="hand2",
                  activebackground=bg, activeforeground=fg,
                  command=self.hide_update_notification).pack(anchor="ne", padx=4, pady=2)

        # Also highlight the Settings nav button
        if "settings" in self.nav_buttons:
            orig_text = self.nav_buttons["settings"].cget("text")
            if "●" not in str(orig_text):
                self.nav_buttons["settings"].configure(text="⚙ Settings  ●")

    def hide_update_notification(self) -> None:
        """Remove the update badge from the nav bar."""
        if self._update_banner:
            try:
                self._update_banner.destroy()
            except Exception:
                pass
            self._update_banner = None

        # Restore settings button text
        if "settings" in self.nav_buttons:
            self.nav_buttons["settings"].configure(text="⚙ Settings")

    def update_user(self, user: dict) -> None:
        self.user = user
