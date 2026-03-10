"""
Landing / entry-point chooser shown when Kiosk POS has never been configured.

Presents two paths:
  • Set Up My Store  → runs the normal AdminSetupFrame wizard
  • Try Demo         → relaunches the process with --demo so the isolated
                       demo database is used from the very first screen

Design mirrors the AdminSetupFrame split-pane layout (gradient left panel,
white right panel) so the visual language is consistent.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import tkinter as tk
from tkinter import ttk

# ── Design tokens (kept in sync with admin_setup.py) ─────────────────────────
_C_TOP      = (30, 64, 175)     # deep blue
_C_BOT      = (76, 29, 149)     # deep purple
_C_ACCENT   = '#60a5fa'
_C_WHITE    = '#ffffff'
_C_CARD     = '#f8fafc'
_C_BORDER   = '#e2e8f0'
_C_TEXT     = '#1e293b'
_C_MUTED    = '#64748b'
_C_PRIMARY  = '#2563eb'
_C_PRHOV    = '#1d4ed8'
_C_SUCCESS  = '#16a34a'
_C_AMBER    = '#d97706'
_SIDE_W     = 380


def _lerp_color(a: tuple, b: tuple, t: float) -> str:
    r = int(a[0] + (b[0] - a[0]) * t)
    g = int(a[1] + (b[1] - a[1]) * t)
    bl = int(a[2] + (b[2] - a[2]) * t)
    return f'#{r:02x}{g:02x}{bl:02x}'


class LandingFrame(tk.Frame):
    """
    Full-window landing frame shown on first launch (no users in DB).

    Parameters
    ----------
    parent : tk.Widget
    on_setup : callable
        Called when the user clicks "Set Up My Store".
    on_login : callable or None
        Called when the user clicks "Log in" (shown only when a pre-existing
        live store is detected).  Defaults to ``on_setup`` if not provided.
    """

    def __init__(self, parent: tk.Widget, *, on_setup, on_login=None):
        super().__init__(parent, bg=_C_CARD)
        self.on_setup = on_setup
        self.on_login = on_login if on_login is not None else on_setup
        self._logo_img = None
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Left gradient panel ───────────────────────────────────────────────
        self._canvas = tk.Canvas(self, width=_SIDE_W, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky=tk.NSEW)
        self._canvas.bind('<Configure>', self._redraw_left)
        self._preload_logo()

        # ── Right content panel ───────────────────────────────────────────────
        right = tk.Frame(self, bg=_C_CARD)
        right.grid(row=0, column=1, sticky=tk.NSEW)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        inner = tk.Frame(right, bg=_C_CARD)
        inner.grid(row=0, column=0, sticky='')   # centred

        # Tagline
        tk.Label(inner, text='Welcome to Kiosk POS',
                 font=('Segoe UI', 24, 'bold'), bg=_C_CARD, fg=_C_TEXT).pack(pady=(0, 6))
        tk.Label(inner, text='How would you like to get started?',
                 font=('Segoe UI', 12), bg=_C_CARD, fg=_C_MUTED).pack(pady=(0, 32))

        # "Already have a store" link — shown when a live store with users exists
        import json as _json, sqlite3 as _sqlite3
        from pathlib import Path as _Path
        _config = _Path(__file__).parent.parent / 'config.json'
        _live_ready = False
        try:
            if _config.exists():
                _db = _Path(_json.loads(_config.read_text()).get('db_path', ''))
                if _db.exists():
                    with _sqlite3.connect(_db) as _c:
                        _live_ready = _c.execute(
                            'SELECT COUNT(*) FROM users WHERE active=1'
                        ).fetchone()[0] > 0
        except Exception:
            pass
        if _live_ready:
            existing_row = tk.Frame(inner, bg=_C_CARD)
            existing_row.pack(pady=(0, 8))
            tk.Label(existing_row, text='Already set up this store?',
                     font=('Segoe UI', 10), bg=_C_CARD, fg=_C_MUTED).pack(side=tk.LEFT)
            login_lnk = tk.Label(existing_row, text='  Log in →',
                     font=('Segoe UI', 10, 'bold'), bg=_C_CARD, fg=_C_PRIMARY,
                     cursor='hand2')
            login_lnk.pack(side=tk.LEFT)
            login_lnk.bind('<Button-1>', lambda _e: self._do_login())

        # ── Card: Set Up My Store ─────────────────────────────────────────────
        setup_card = tk.Frame(inner, bg=_C_WHITE,
                              highlightthickness=2,
                              highlightbackground=_C_BORDER)
        setup_card.pack(fill=tk.X, ipadx=8, ipady=8, pady=(0, 18))

        tk.Label(setup_card, text='🏪  Set Up My Store',
                 font=('Segoe UI', 14, 'bold'), bg=_C_WHITE, fg=_C_TEXT,
                 anchor='w').pack(anchor='w', padx=24, pady=(20, 4))
        tk.Label(setup_card,
                 text=(
                     'Create your admin account, configure your business name,\n'
                     'currency, and preferences. Takes about 2 minutes.'
                 ),
                 font=('Segoe UI', 10), bg=_C_WHITE, fg=_C_MUTED,
                 anchor='w', justify=tk.LEFT).pack(anchor='w', padx=24, pady=(0, 16))

        setup_btn = tk.Button(
            setup_card,
            text='Set Up My Store  →',
            bg=_C_PRIMARY, fg=_C_WHITE,
            activebackground=_C_PRHOV, activeforeground=_C_WHITE,
            font=('Segoe UI', 11, 'bold'),
            relief=tk.FLAT, padx=24, pady=10, cursor='hand2',
            command=self._do_setup,
        )
        setup_btn.pack(anchor='w', padx=24, pady=(0, 20))

        # ── Card: Try Demo ────────────────────────────────────────────────────
        demo_card = tk.Frame(inner, bg=_C_WHITE,
                             highlightthickness=2,
                             highlightbackground=_C_BORDER)
        demo_card.pack(fill=tk.X, ipadx=8, ipady=8)

        # Amber accent bar at top
        tk.Frame(demo_card, bg=_C_AMBER, height=4).pack(fill=tk.X)

        tk.Label(demo_card, text='🧪  Try Demo',
                 font=('Segoe UI', 14, 'bold'), bg=_C_WHITE, fg=_C_TEXT,
                 anchor='w').pack(anchor='w', padx=24, pady=(16, 4))
        tk.Label(demo_card,
                 text=(
                     'Explore every feature in an isolated test environment.\n'
                     'No data is saved to your live store. Reset any time.'
                 ),
                 font=('Segoe UI', 10), bg=_C_WHITE, fg=_C_MUTED,
                 anchor='w', justify=tk.LEFT).pack(anchor='w', padx=24, pady=(0, 16))

        demo_btn = tk.Button(
            demo_card,
            text='Launch Demo  →',
            bg='#fef3c7', fg='#92400e',
            activebackground='#fde68a', activeforeground='#78350f',
            font=('Segoe UI', 11, 'bold'),
            relief=tk.FLAT, padx=24, pady=10, cursor='hand2',
            highlightbackground=_C_AMBER, highlightthickness=1,
            command=self._do_demo,
        )
        demo_btn.pack(anchor='w', padx=24, pady=(0, 20))

    # ── Action handlers ───────────────────────────────────────────────────────

    def _do_setup(self):
        """Transition to the setup wizard."""
        self.destroy()
        self.on_setup()

    def _do_login(self):
        """Transition to the login screen."""
        self.destroy()
        self.on_login()

    def _do_demo(self):
        """Relaunch this process with --demo and close this window."""
        script = Path(sys.argv[0]).resolve()
        subprocess.Popen([sys.executable, str(script), '--demo'])
        # Give the new process a moment, then quit this window
        self.after(400, lambda: self.winfo_toplevel().destroy())

    # ── Left-panel drawing ────────────────────────────────────────────────────

    def _preload_logo(self):
        try:
            from PIL import Image, ImageTk
            logo_path = Path(__file__).parent.parent / 'assets' / 'logo.png'
            img = Image.open(logo_path).convert('RGBA').resize((200, 200), Image.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(img)
        except Exception:
            pass

    def _redraw_left(self, _e=None):
        c = self._canvas
        c.delete('all')
        w = c.winfo_width() or _SIDE_W
        h = c.winfo_height() or 800

        for i in range(h):
            c.create_line(0, i, w, i,
                          fill=_lerp_color(_C_TOP, _C_BOT, i / max(h - 1, 1)))

        logo_y = int(h * 0.38)
        if self._logo_img:
            c.create_image(w // 2, logo_y, image=self._logo_img, anchor='center', tags='logo')
        else:
            c.create_text(w // 2, logo_y, text='POS',
                          fill=_C_WHITE, font=('Segoe UI', 56, 'bold'), anchor='center')

        c.create_text(w // 2, logo_y + 118,
                      text='Kiosk POS', fill=_C_WHITE,
                      font=('Segoe UI', 22, 'bold'), anchor='center')
        c.create_text(w // 2, logo_y + 148,
                      text='Point of Sale System', fill=_C_ACCENT,
                      font=('Segoe UI', 11), anchor='center')

        # Bullet feature list
        features = [
            '✓  Sales & Inventory',
            '✓  Reports & Analytics',
            '✓  Receipts & Payments',
            '✓  Multi-user Access',
        ]
        fstart = int(h * 0.64)
        for fi, feat in enumerate(features):
            c.create_text(w // 2, fstart + fi * 26,
                          text=feat, fill='#bfdbfe',
                          font=('Segoe UI', 10), anchor='center')

        c.create_text(w // 2, h - 20,
                      text='v1.0 · Ready to use',
                      fill='#475569', font=('Segoe UI', 8), anchor='center')
        c.lift('logo')
