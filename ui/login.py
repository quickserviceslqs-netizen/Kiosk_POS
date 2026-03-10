"""Login UI frame for the Kiosk POS application."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules.users import validate_credentials


def _get_login_colors():
    """Get colors from the theme system for login screen."""
    try:
        from utils.theme import get_theme_colors
        tc = get_theme_colors()
        return {
            'bg': tc.get('surface', '#f8fafc'),
            'card_bg': tc.get('surface', '#FDFBF7'),
            'text': tc.get('text', '#2F2A25'),
            'border': tc.get('border', '#D9D2C7'),
            'primary': tc.get('primary', '#0A7C86'),
            'primary_dark': tc.get('primary_dark', '#0C90A0'),
            'btn_bg': tc.get('sidebar_active', '#475569'),
            'btn_fg': tc.get('text_white', '#FFFFFF'),
            'btn_hover': tc.get('sidebar_hover', '#334155'),
            'danger': tc.get('danger', '#B53B3B'),
            'field_bg': tc.get('field_bg', '#FFFFFF'),
            'field_text': tc.get('field_text', '#1f2937'),
            'text_white': tc.get('text_white', '#FFFFFF'),
            'text_secondary': tc.get('text_secondary', '#6b7280'),
        }
    except Exception:
        return {
            'bg': '#f8fafc', 'card_bg': '#FDFBF7', 'text': '#2F2A25',
            'border': '#D9D2C7', 'primary': '#0A7C86', 'primary_dark': '#0C90A0',
            'btn_bg': '#475569', 'btn_fg': '#FFFFFF', 'btn_hover': '#334155',
            'danger': '#B53B3B', 'field_bg': '#FFFFFF', 'field_text': '#1f2937',
            'text_white': '#FFFFFF', 'text_secondary': '#6b7280',
        }


class LoginFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_success, **kwargs):
        super().__init__(master, padding=24, **kwargs)
        self.on_success = on_success
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.lc = _get_login_colors()

        self._init_styles()

        self._build_ui()

    def _init_styles(self) -> None:
        c = self.lc
        style = ttk.Style(self)
        style.configure("LoginRoot.TFrame", background=c['bg'])
        style.configure(
            "LoginCard.TFrame",
            background=c['card_bg'],
            bordercolor=c['border'],
            relief="solid",
            borderwidth=1,
        )
        style.configure("LoginTitle.TLabel", background=c['card_bg'], foreground=c['text'], font=("Segoe UI", 18, "bold"))
        style.configure("LoginLabel.TLabel", background=c['card_bg'], foreground=c['text'], font=("Segoe UI", 10, "semibold"))
        style.configure(
            "LoginField.TEntry",
            fieldbackground=c['field_bg'],
            foreground=c['field_text'],
            insertcolor=c['field_text'],
            bordercolor=c['border'],
            lightcolor=c['field_bg'],
            darkcolor=c['border'],
        )
        style.map(
            "LoginField.TEntry",
            bordercolor=[("focus", c['primary'])],
            lightcolor=[("focus", c['primary'])],
            darkcolor=[("focus", c['primary'])],
        )
        style.configure(
            "LoginPrimary.TButton",
            background=c['primary'],
            foreground=c['text_white'],
            font=("Segoe UI", 11, "medium"),
            padding=(12, 8),
            relief="raised",
            borderwidth=1,
            anchor="center",
        )
        style.map(
            "LoginPrimary.TButton",
            background=[
                ("pressed", c['primary_dark']),
                ("active", c['primary_dark']),
                ("!disabled", c['primary']),
            ],
            foreground=[
                ("pressed", c['text_white']),
                ("active", c['text_white']),
                ("!disabled", c['text_white']),
                ("disabled", c.get('disabled_bg', '#e5e7eb')),
            ],
        )
        style.configure("LoginError.TLabel", background=c['card_bg'], foreground=c['danger'], font=("Segoe UI", 9))


    def _build_ui(self) -> None:
        c = self.lc
        # Base surface
        self.configure(style="LoginRoot.TFrame")
        self.columnconfigure(0, weight=1)
        self.grid_propagate(False)

        # Centered card
        card = ttk.Frame(self, padding=24, style="LoginCard.TFrame")
        card.grid(row=0, column=0, sticky=tk.N)
        card.columnconfigure(0, weight=0)
        card.columnconfigure(1, weight=1)

        # Logo (if available)
        try:
            from PIL import Image, ImageTk
            import os
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            logo_path = os.path.abspath(logo_path)
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((64, 64), Image.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = ttk.Label(card, image=self.logo_photo, background=c['card_bg'])
                logo_label.grid(row=0, column=0, columnspan=2, pady=(0, 8))
        except Exception:
            pass

        from main import APP_VERSION
        ttk.Label(card, text=f"Welcome to Kiosk POS v{APP_VERSION}", style="LoginTitle.TLabel").grid(row=1, column=0, columnspan=2, pady=(0, 8))
        ttk.Label(card, text="Sign in to continue", style="LoginLabel.TLabel").grid(row=2, column=0, columnspan=2, pady=(0, 16))

        ttk.Label(card, text="Username", style="LoginLabel.TLabel").grid(row=3, column=0, sticky=tk.W, pady=4)
        username_entry = ttk.Entry(card, textvariable=self.username_var, width=32, style="LoginField.TEntry")
        username_entry.grid(row=3, column=1, sticky=tk.EW, pady=4)
        username_entry.focus_set()

        ttk.Label(card, text="Password", style="LoginLabel.TLabel").grid(row=4, column=0, sticky=tk.W, pady=4)
        password_entry = ttk.Entry(card, textvariable=self.password_var, show="*", width=32, style="LoginField.TEntry")
        password_entry.grid(row=4, column=1, sticky=tk.EW, pady=4)
        password_entry.bind("<Return>", lambda _evt: self.submit())

        # Show password toggle
        self.show_password = tk.BooleanVar(value=False)
        def toggle_password():
            password_entry.config(show="" if self.show_password.get() else "*")
        show_pwd_chk = ttk.Checkbutton(card, text="Show Password", variable=self.show_password, command=toggle_password, style="LoginLabel.TLabel")
        show_pwd_chk.grid(row=5, column=1, sticky=tk.W, pady=(0, 8))

        # Use tk.Button to guarantee text visibility across themes
        login_btn = tk.Button(
            card,
            text="Login",
            command=self.submit,
            bg=c['btn_bg'],
            fg=c['btn_fg'],
            activebackground=c['btn_hover'],
            activeforeground=c['btn_fg'],
            relief=tk.RAISED,
            bd=1,
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=6,
        )
        login_btn.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=(14, 8))

        status_lbl = ttk.Label(card, textvariable=self.status_var, style="LoginError.TLabel")
        status_lbl.grid(row=7, column=0, columnspan=2, sticky=tk.W)

        # ── Mode switch ──────────────────────────────────────────────────
        import sys as _sys, subprocess as _sp
        from pathlib import Path as _Path
        _is_demo = '--demo' in _sys.argv
        _app_script = str(_Path(__file__).parent.parent / 'main.py')

        ttk.Separator(card, orient='horizontal').grid(
            row=8, column=0, columnspan=2, sticky=tk.EW, pady=(18, 10)
        )

        if _is_demo:
            _switch_label = '← Switch to Live Store'
            _switch_args  = [_sys.executable, _app_script]          # no --demo
        else:
            _switch_label = '🧪 Try Demo Mode'
            _switch_args  = [_sys.executable, _app_script, '--demo']

        def _switch_mode():
            _sp.Popen(_switch_args)
            self.winfo_toplevel().after(400, lambda: self.winfo_toplevel().destroy())

        switch_btn = tk.Button(
            card,
            text=_switch_label,
            command=_switch_mode,
            bg=c['card_bg'],
            fg='#f59e0b' if not _is_demo else c['primary'],
            activebackground=c['card_bg'],
            activeforeground=c['primary_dark'],
            relief=tk.FLAT,
            bd=0,
            font=('Segoe UI', 9, 'bold'),
            cursor='hand2',
        )
        switch_btn.grid(row=9, column=0, columnspan=2, pady=(0, 4))

    def submit(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get()
        if not username or not password:
            self.status_var.set("Enter username and password")
            return

        try:
            user = validate_credentials(username, password)
        except Exception as e:
            self.status_var.set("Error accessing database.")
            return

        if not user:
            self.status_var.set("Invalid credentials or inactive user")
            return

        self.status_var.set("")
        self.on_success(user)
