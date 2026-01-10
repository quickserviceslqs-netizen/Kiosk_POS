from __future__ import annotations

import tkinter as tk
from tkinter import ttk


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

        self._init_styles()
        self._build_ui()

    def _init_styles(self) -> None:
        accent = "#0C90A0"
        dark = "#0A2B30"
        light_bg = "#F6F7FB"
        style = ttk.Style(self)
        style.configure("Shell.Header.TFrame", background="#FFFFFF")
        style.configure("Shell.Body.TFrame", background=light_bg)
        style.configure("Shell.Title.TLabel", font=("Segoe UI", 18, "bold"), background="#FFFFFF", foreground="#1E1E1E")
        style.configure("Shell.Subtitle.TLabel", font=("Segoe UI", 10), background="#FFFFFF", foreground="#6B7280")
        style.configure("Shell.Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(10, 6), background=accent, foreground="#FFFFFF")
        style.map(
            "Shell.Primary.TButton",
            background=[("active", "#0DA7B8"), ("pressed", "#0DA7B8")],
            foreground=[("disabled", "#E5E7EB")],
        )

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        nav_frame = tk.Frame(self, background="#0A2B30", width=220)
        nav_frame.grid(row=0, column=0, rowspan=2, sticky=tk.NS)
        nav_frame.grid_propagate(False)

        brand = ttk.Label(nav_frame, text="Kiosk POS", foreground="#FFFFFF", background="#0A2B30", font=("Segoe UI", 14, "bold"))
        brand.pack(fill=tk.X, padx=18, pady=(18, 10))
        user_label = ttk.Label(
            nav_frame,
            text=f"{self.user.get('username', 'User')}",
            foreground="#B8CFD2",
            background="#0A2B30",
            font=("Segoe UI", 10),
            justify=tk.LEFT,
        )
        user_label.pack(fill=tk.X, padx=18, pady=(0, 16))

        nav_items = [
            ("dashboard", "🏠 Dashboard"),
            ("pos", "🛒 Point of Sale"),
            ("cart", "🧾 Cart"),
            ("inventory", "📦 Inventory"),
            ("reports", "📈 Reports"),
            ("order_history", "📜 Order History"),
            ("expenses", "💸 Expenses"),
            ("backup", "🗄 Backup"),
            ("settings", "⚙ Settings"),
        ]
        nav_bg = "#0F3C44"
        nav_active = "#0C90A0"
        nav_fg = "#E8F1F2"
        for key, label in nav_items:
            btn = tk.Button(
                nav_frame,
                text=label,
                anchor="w",
                padx=16,
                pady=10,
                relief=tk.FLAT,
                bd=0,
                bg=nav_bg,
                fg=nav_fg,
                activebackground=nav_active,
                activeforeground="#FFFFFF",
                highlightthickness=0,
                command=lambda k=key: self._nav(k),
            )
            btn.pack(fill=tk.X)
            self.nav_buttons[key] = btn

        tk.Button(
            nav_frame,
            text="⏻ Logout",
            anchor="w",
            padx=16,
            pady=10,
            relief=tk.FLAT,
            bd=0,
            bg="#082126",
            fg=nav_fg,
            activebackground="#0F3C44",
            activeforeground="#FFFFFF",
            highlightthickness=0,
            command=self.on_logout,
        ).pack(fill=tk.X, pady=(12, 8))

        header = ttk.Frame(self, style="Shell.Header.TFrame", padding=(18, 12))
        header.grid(row=0, column=1, sticky=tk.EW)
        header.columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self.title_var, style="Shell.Title.TLabel").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(header, textvariable=self.subtitle_var, style="Shell.Subtitle.TLabel").grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        self.header_button = ttk.Button(header, text="Refresh", style="Shell.Primary.TButton", command=lambda: self._nav(self._active_key()))
        self.header_button.grid(row=0, column=1, rowspan=2, sticky=tk.E, padx=(12, 0))
        self.header_button_action = lambda: self._nav(self._active_key())  # Default action

        body = ttk.Frame(self, style="Shell.Body.TFrame", padding=(18, 12))
        body.grid(row=1, column=1, sticky=tk.NSEW)
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
        
        self.active_key = key
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(bg="#0C90A0", fg="#FFFFFF")
            else:
                btn.configure(bg="#0F3C44", fg="#E8F1F2")

    def go_back(self) -> str | None:
        """Go back to the previous page. Returns the previous page key or None."""
        if len(self.nav_history) > 1:
            self.nav_history.pop()  # Remove current
            prev_key = self.nav_history[-1]  # Get previous
            return prev_key
        return None

    def set_content(self, frame: tk.Widget, *, title: str, subtitle: str | None = None) -> None:
        if self.current_content:
            self.current_content.destroy()
        self.current_content = frame
        frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.title_var.set(title)
        self.subtitle_var.set(subtitle or "")

    def set_header_button(self, text: str, command) -> None:
        """Update the header button text and action."""
        self.header_button.configure(text=text, command=command)
        self.header_button_action = command

    def update_user(self, user: dict) -> None:
        self.user = user
