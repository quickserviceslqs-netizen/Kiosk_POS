import tkinter as tk
from tkinter import ttk, messagebox
from modules.users import create_user, validate_password_strength
from utils import set_window_icon
from utils.theme import get_status_color
import threading
import time
import logging
from pathlib import Path

# Setup logging for the setup process
setup_logger = logging.getLogger('setup')
setup_logger.setLevel(logging.INFO)
setup_log_file = Path(__file__).parent.parent / "logs" / "setup.log"
setup_log_file.parent.mkdir(parents=True, exist_ok=True)
setup_handler = logging.FileHandler(setup_log_file, encoding="utf-8")
setup_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
setup_logger.addHandler(setup_handler)

# ── Design tokens ────────────────────────────────────────────────────────────
_C_TOP    = (30,  64, 175)   # #1e40af  deep blue   (top of gradient)
_C_BOT    = (76,  29, 149)   # #4c1d95  deep purple (bottom of gradient)
_C_ACCENT = '#60a5fa'         # sky-blue accent text
_C_WHITE  = '#ffffff'
_C_CARD   = '#f8fafc'
_C_BORDER = '#e2e8f0'
_C_TEXT   = '#1e293b'
_C_MUTED  = '#64748b'
_C_PRIMARY= '#2563eb'
_C_PRHOV  = '#1d4ed8'
_C_DANGER = '#dc2626'
_C_SUCCESS= '#16a34a'
_SIDE_W   = 380               # left panel pixel width


def _lerp_color(a: tuple, b: tuple, t: float) -> str:
    """Linearly interpolate between two RGB tuples and return #rrggbb."""
    r = int(a[0] + (b[0] - a[0]) * t)
    g = int(a[1] + (b[1] - a[1]) * t)
    b_ = int(a[2] + (b[2] - a[2]) * t)
    return f'#{r:02x}{g:02x}{b_:02x}'


class AdminSetupFrame(ttk.Frame):
    """First-time setup wizard for initializing the Kiosk POS system."""
    
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.current_step = 0
        self.setup_errors = []  # Track errors for recovery
        self.completed_steps = set()  # Track successfully completed steps
        self.steps = [
            "Welcome",
            "Database",
            "Admin",
            "Config",
            "Preferences",
            "Complete"
        ]
        self.theme_var = tk.StringVar(value='default')
        self.receipt_footer_var = tk.StringVar(value='Thank you for shopping with us!')
        self.date_format_var = tk.StringVar(value='%Y-%m-%d')
        # Persistent vars for System Config step — must survive step navigation
        self.business_name = tk.StringVar(value='My Store')
        self.currency = tk.StringVar(value='USD')
        setup_logger.info("Setup wizard initialized")
        self._build_ui()
        self._show_step(0)

    def _build_ui(self):
        """Build the split-pane setup wizard UI."""
        self.columnconfigure(0, weight=0)   # left panel — fixed width
        self.columnconfigure(1, weight=1)   # right panel — expands
        self.rowconfigure(0, weight=1)

        # ── Left hero canvas ─────────────────────────────────────────────────
        self._lcanvas = tk.Canvas(self, width=_SIDE_W, highlightthickness=0, bd=0)
        self._lcanvas.grid(row=0, column=0, sticky=tk.NSEW)
        self._lcanvas.bind('<Configure>', self._redraw_left)

        # ── Right content panel ───────────────────────────────────────────────
        right = tk.Frame(self, bg=_C_CARD)
        right.grid(row=0, column=1, sticky=tk.NSEW)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # Top accent bar
        tk.Frame(right, bg=_C_PRIMARY, height=4).grid(row=0, column=0, sticky=tk.EW)

        # Scrollable content host
        scroll_host = tk.Frame(right, bg=_C_CARD)
        scroll_host.grid(row=1, column=0, sticky=tk.NSEW)
        scroll_host.columnconfigure(0, weight=1)
        scroll_host.rowconfigure(0, weight=1)

        self._scrollcanvas = tk.Canvas(scroll_host, bg=_C_CARD, highlightthickness=0)
        self._scrollcanvas.grid(row=0, column=0, sticky=tk.NSEW)
        _vsb = ttk.Scrollbar(scroll_host, orient=tk.VERTICAL,
                              command=self._scrollcanvas.yview)
        _vsb.grid(row=0, column=1, sticky=tk.NS)
        self._scrollcanvas.configure(yscrollcommand=_vsb.set)

        self.content_frame = tk.Frame(self._scrollcanvas, bg=_C_CARD)
        self._cfw = self._scrollcanvas.create_window(
            (0, 0), window=self.content_frame, anchor='nw')
        self.content_frame.bind('<Configure>', self._on_content_configure)
        self._scrollcanvas.bind('<Configure>', self._on_canvas_configure)

        # Bottom nav bar
        nav_bar = tk.Frame(right, bg=_C_WHITE,
                           highlightbackground=_C_BORDER, highlightthickness=1)
        nav_bar.grid(row=2, column=0, sticky=tk.EW)
        nav_bar.columnconfigure(1, weight=1)

        self.back_btn = tk.Button(
            nav_bar, text='Back',
            bg=_C_CARD, fg=_C_MUTED,
            activebackground=_C_BORDER, activeforeground=_C_TEXT,
            font=('Segoe UI', 10), relief=tk.FLAT,
            padx=20, pady=10, cursor='hand2',
            highlightbackground=_C_BORDER, highlightthickness=1,
            state=tk.DISABLED, command=self._go_back)
        self.back_btn.grid(row=0, column=0, padx=16, pady=12)

        # Exit demo shortcut — only rendered when running with --demo
        import sys as _sys_chk
        if '--demo' in _sys_chk.argv:
            import subprocess as _sp_chk, json as _json_chk
            from pathlib import Path as _pchk
            _app_dir_chk = _pchk(__file__).parent.parent
            _conf_chk    = _app_dir_chk / 'config.json'

            def _live_ready_chk() -> bool:
                import sqlite3 as _sq
                try:
                    if not _conf_chk.exists():
                        return False
                    _db = _pchk(_json_chk.loads(_conf_chk.read_text()).get('db_path', ''))
                    if not _db.exists():
                        return False
                    with _sq.connect(_db) as _c:
                        return _c.execute(
                            'SELECT COUNT(*) FROM users WHERE active=1'
                        ).fetchone()[0] > 0
                except Exception:
                    return False

            _lbl = '← Live Store' if _live_ready_chk() else '← Set Up Live Store'

            def _exit_demo():
                _sp_chk.Popen([_sys_chk.executable,
                               str(_app_dir_chk / 'main.py')])
                self.winfo_toplevel().after(400,
                    lambda: self.winfo_toplevel().destroy())

            tk.Button(
                nav_bar, text=_lbl,
                bg='#fef3c7', fg='#92400e',
                activebackground='#fde68a', activeforeground='#78350f',
                font=('Segoe UI', 9), relief=tk.FLAT,
                padx=12, pady=10, cursor='hand2',
                command=_exit_demo,
            ).grid(row=0, column=5, padx=(0, 8), pady=12)

        else:
            # Live-store wizard: offer a "Try Demo" shortcut
            import subprocess as _sp_live
            from pathlib import Path as _pchk_live
            _app_dir_live = _pchk_live(__file__).parent.parent

            def _open_demo():
                _sp_live.Popen([_sys_chk.executable,
                                str(_app_dir_live / 'main.py'), '--demo'])
                # Don't close this window — user can still continue setup

            tk.Button(
                nav_bar, text='🧪 Try Demo',
                bg='#fef3c7', fg='#92400e',
                activebackground='#fde68a', activeforeground='#78350f',
                font=('Segoe UI', 9), relief=tk.FLAT,
                padx=12, pady=10, cursor='hand2',
                highlightbackground='#d97706', highlightthickness=1,
                command=_open_demo,
            ).grid(row=0, column=5, padx=(0, 8), pady=12)

        tk.Button(
            nav_bar, text='Help',
            bg=_C_CARD, fg=_C_MUTED,
            activebackground=_C_BORDER, activeforeground=_C_TEXT,
            font=('Segoe UI', 10), relief=tk.FLAT,
            padx=16, pady=10, cursor='hand2',
            command=self._show_help
        ).grid(row=0, column=1)

        self.finish_btn = tk.Button(
            nav_bar, text='Finish Setup',
            bg=_C_SUCCESS, fg=_C_WHITE,
            activebackground='#15803d', activeforeground=_C_WHITE,
            font=('Segoe UI', 10, 'bold'), relief=tk.FLAT,
            padx=20, pady=10, cursor='hand2',
            state=tk.DISABLED, command=self._finish_setup)
        self.finish_btn.grid(row=0, column=3, padx=(0, 6), pady=12)

        self.next_btn = tk.Button(
            nav_bar, text='Next  >',
            bg=_C_PRIMARY, fg=_C_WHITE,
            activebackground=_C_PRHOV, activeforeground=_C_WHITE,
            font=('Segoe UI', 10, 'bold'), relief=tk.FLAT,
            padx=20, pady=10, cursor='hand2',
            command=self._go_next)
        self.next_btn.grid(row=0, column=4, padx=(0, 16), pady=12)

        # Pre-load logo for canvas drawing
        self._logo_img = None
        try:
            from PIL import Image, ImageTk
            logo_path = Path(__file__).parent.parent / 'assets' / 'logo.png'
            img = Image.open(logo_path).convert('RGBA').resize((200, 200), Image.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(img)
        except Exception:
            pass

    # ── Canvas helpers ────────────────────────────────────────────────────────

    def _on_content_configure(self, _e=None):
        self._scrollcanvas.configure(scrollregion=self._scrollcanvas.bbox('all'))

    def _on_canvas_configure(self, e):
        self._scrollcanvas.itemconfigure(self._cfw, width=e.width)

    def _redraw_left(self, _e=None):
        """Draw gradient + logo + step progress dots on the left canvas."""
        c = self._lcanvas
        c.delete('all')
        w = c.winfo_width() or _SIDE_W
        h = c.winfo_height() or 800

        # Gradient fill (top → bottom via horizontal strips)
        for i in range(h):
            c.create_line(0, i, w, i, fill=_lerp_color(_C_TOP, _C_BOT, i / max(h - 1, 1)))

        # Logo centred at 35 % height
        logo_y = int(h * 0.35)
        if self._logo_img:
            c.create_image(w // 2, logo_y, image=self._logo_img, anchor='center', tags='logo')
        else:
            c.create_text(w // 2, logo_y, text='POS',
                          fill=_C_WHITE, font=('Segoe UI', 56, 'bold'), anchor='center')

        # App name & tagline
        c.create_text(w // 2, logo_y + 118,
                      text='Kiosk POS', fill=_C_WHITE,
                      font=('Segoe UI', 22, 'bold'), anchor='center')
        c.create_text(w // 2, logo_y + 148,
                      text='Point of Sale System', fill=_C_ACCENT,
                      font=('Segoe UI', 11), anchor='center')

        # ── Step dots at 72 % height ──────────────────────────────────────────
        dots_y = int(h * 0.72)
        dot_r  = 9
        dot_gap = 44
        total  = len(self.steps)
        start_x = w // 2 - (total - 1) * dot_gap // 2

        # Connector lines first (so dots sit on top)
        for i in range(total - 1):
            x1 = start_x + i * dot_gap + dot_r
            x2 = start_x + (i + 1) * dot_gap - dot_r
            col = _C_ACCENT if i < self.current_step else '#3b5998'
            c.create_line(x1, dots_y, x2, dots_y, fill=col, width=2)

        for i, name in enumerate(self.steps):
            cx = start_x + i * dot_gap
            if i < self.current_step:                              # completed
                c.create_oval(cx-dot_r, dots_y-dot_r, cx+dot_r, dots_y+dot_r,
                              fill=_C_ACCENT, outline='')
                c.create_text(cx, dots_y, text='✓', fill='#1e3a8a',
                              font=('Segoe UI', 9, 'bold'), anchor='center')
            elif i == self.current_step:                           # active
                c.create_oval(cx-dot_r-3, dots_y-dot_r-3,
                              cx+dot_r+3, dots_y+dot_r+3,
                              fill='', outline=_C_WHITE, width=2)
                c.create_oval(cx-dot_r, dots_y-dot_r, cx+dot_r, dots_y+dot_r,
                              fill=_C_WHITE, outline='')
                c.create_text(cx, dots_y, text=str(i+1),
                              fill=_lerp_color(_C_TOP, _C_BOT, i / max(total-1, 1)),
                              font=('Segoe UI', 9, 'bold'), anchor='center')
            else:                                                  # upcoming
                c.create_oval(cx-dot_r, dots_y-dot_r, cx+dot_r, dots_y+dot_r,
                              fill='', outline='#93c5fd', width=2)
                c.create_text(cx, dots_y, text=str(i+1), fill='#93c5fd',
                              font=('Segoe UI', 9), anchor='center')

            # Label below dot
            is_active = (i == self.current_step)
            c.create_text(cx, dots_y + dot_r + 14, text=name,
                          fill=_C_WHITE if is_active else '#bfdbfe',
                          font=('Segoe UI', 8, 'bold' if is_active else 'normal'),
                          anchor='center')

        # Keep logo on top
        c.lift('logo')

        # Version footer
        c.create_text(w // 2, h - 20, text='v1.0 Setup Wizard',
                      fill='#475569', font=('Segoe UI', 8), anchor='center')

    # ── Step routing ──────────────────────────────────────────────────────────

    def _show_step(self, step_index):
        for child in self.content_frame.winfo_children():
            child.destroy()

        self.current_step = step_index
        last_content = len(self.steps) - 2   # index of last content step

        self.back_btn.config(state=tk.NORMAL if step_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if step_index < last_content else tk.DISABLED)
        self.finish_btn.config(state=tk.NORMAL if step_index == last_content else tk.DISABLED)

        self._redraw_left()
        self._scrollcanvas.yview_moveto(0)

        if step_index == 0:
            self._show_welcome()
        elif step_index == 1:
            self._show_database_setup()
        elif step_index == 2:
            self._show_admin_account()
        elif step_index == 3:
            self._show_system_config()
        elif step_index == 4:
            self._show_preferences()
        elif step_index == 5:
            self._show_complete()

    # ── Shared style helpers ──────────────────────────────────────────────────

    def _step_header(self, icon: str, title: str, subtitle: str) -> None:
        hdr = tk.Frame(self.content_frame, bg=_C_PRIMARY)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=icon, font=('Segoe UI', 28),
                 bg=_C_PRIMARY, fg=_C_WHITE).pack(pady=(24, 0))
        tk.Label(hdr, text=title, font=('Segoe UI', 20, 'bold'),
                 bg=_C_PRIMARY, fg=_C_WHITE).pack()
        tk.Label(hdr, text=subtitle, font=('Segoe UI', 10),
                 bg=_C_PRIMARY, fg='#bfdbfe').pack(pady=(2, 20))
        tk.Frame(hdr, bg=_C_ACCENT, height=3).pack(fill=tk.X)

    def _card(self, parent=None, **kw) -> tk.Frame:
        p = parent or self.content_frame
        return tk.Frame(p, bg=_C_WHITE,
                        highlightbackground=_C_BORDER,
                        highlightthickness=1, **kw)

    # ── Step 0: Welcome ───────────────────────────────────────────────────────

    def _show_welcome(self):
        self._step_header('', 'Welcome to Kiosk POS', 'Let\'s get your store set up in minutes')

        body = tk.Frame(self.content_frame, bg=_C_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)

        tk.Label(body, text='This wizard walks you through four quick steps to get your store ready:',
                 font=('Segoe UI', 11), bg=_C_CARD, fg=_C_TEXT, anchor='w').pack(fill=tk.X, pady=(0, 16))

        steps_info = [
            (
                _C_PRIMARY, '1', 'Database Setup',
                'Creates and initialises your secure local store database.',
                'All your sales, inventory and customer data will be stored here.',
            ),
            (
                '#7c3aed', '2', 'Administrator Account',
                'Creates the first admin login for your store.',
                'Use this account to manage users, settings and permissions.',
            ),
            (
                '#0891b2', '3', 'System Configuration',
                'Sets your business name, operating currency and date format.',
                'These values appear on receipts, reports and throughout the app.',
            ),
            (
                '#059669', '4', 'Preferences',
                'Choose your app colour theme and add a receipt footer message.',
                'You can change these at any time from Settings after setup.',
            ),
        ]
        for color, num, title, desc, detail in steps_info:
            row = self._card(body)
            row.pack(fill=tk.X, pady=6)
            row.columnconfigure(1, weight=1)
            tk.Label(row, text=num, font=('Segoe UI', 14, 'bold'),
                     bg=color, fg=_C_WHITE, width=3, height=2).grid(
                row=0, column=0, rowspan=3, sticky=tk.NS)
            tk.Label(row, text=title, font=('Segoe UI', 11, 'bold'),
                     bg=_C_WHITE, fg=_C_TEXT, anchor='w').grid(
                row=0, column=1, sticky=tk.W, padx=16, pady=(10, 0))
            tk.Label(row, text=desc, font=('Segoe UI', 9),
                     bg=_C_WHITE, fg=_C_TEXT, anchor='w').grid(
                row=1, column=1, sticky=tk.W, padx=16, pady=(1, 0))
            tk.Label(row, text=detail, font=('Segoe UI', 9, 'italic'),
                     bg=_C_WHITE, fg=_C_MUTED, anchor='w').grid(
                row=2, column=1, sticky=tk.W, padx=16, pady=(1, 10))

        tk.Label(body,
                 text='⏱  Setup takes less than two minutes.  Click  Next  when you\'re ready.',
                 font=('Segoe UI', 10, 'italic'), bg=_C_CARD, fg=_C_MUTED).pack(pady=(20, 0))

    # ── Step 1: Database Setup ────────────────────────────────────────────────

    def _show_database_setup(self):
        self._step_header('', 'Database Setup', 'Creating and initialising your store database')

        body = tk.Frame(self.content_frame, bg=_C_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)
        body.columnconfigure(0, weight=1)

        card = self._card(body)
        card.pack(fill=tk.X, pady=(0, 16))
        card.columnconfigure(0, weight=1)

        tk.Label(card, text='Initialising database…',
                 font=('Segoe UI', 12, 'bold'),
                 bg=_C_WHITE, fg=_C_TEXT).pack(anchor='w', padx=20, pady=(16, 8))

        self.db_progress_var = tk.DoubleVar()
        ttk.Progressbar(card, variable=self.db_progress_var,
                        maximum=100, mode='determinate').pack(
                            fill=tk.X, padx=20, pady=(0, 8))

        self.db_status_label = tk.Label(card, text='Preparing…',
                                        font=('Segoe UI', 10),
                                        bg=_C_WHITE, fg=_C_MUTED)
        self.db_status_label.pack(anchor='w', padx=20, pady=(0, 4))

        self.db_error_label = tk.Label(card, text='',
                                       font=('Segoe UI', 9),
                                       bg=_C_WHITE, fg=_C_DANGER,
                                       wraplength=400, justify=tk.LEFT)
        self.db_error_label.pack(anchor='w', padx=20)

        self.retry_btn = tk.Button(card, text='Retry',
                                   bg=_C_DANGER, fg=_C_WHITE,
                                   relief=tk.FLAT, padx=14, pady=6,
                                   font=('Segoe UI', 10),
                                   command=self._retry_database_setup)
        self.retry_btn.pack(anchor='w', padx=20, pady=(4, 16))
        self.retry_btn.pack_forget()

        self.db_setup_complete = False
        self.db_setup_error = None
        self._start_database_setup()

    def _start_database_setup(self):
        """Start database setup with progress tracking."""
        setup_logger.info("Starting database setup")
        self.db_progress_var.set(0)
        self.db_status_label.config(text="Preparing database...", fg=_C_MUTED)
        self.db_error_label.config(text="")
        self.retry_btn.pack_forget()
        
        # Run setup in background thread
        threading.Thread(target=self._setup_database_thread, daemon=True).start()

    def _setup_database_thread(self):
        """Database setup running in background thread."""
        try:
            # Step 1: Initialize database connection
            self.db_progress_var.set(10)
            self.db_status_label.config(text="Connecting to database...")
            time.sleep(0.5)
            
            # Step 2: Create schema
            self.db_progress_var.set(30)
            self.db_status_label.config(text="Creating database tables...")
            setup_logger.info("Creating database schema")
            time.sleep(0.5)
            
            # Step 3: Setup default data
            self.db_progress_var.set(60)
            self.db_status_label.config(text="Setting up default data...")
            setup_logger.info("Setting up default data")
            time.sleep(0.5)
            
            # Step 4: Validate setup
            self.db_progress_var.set(90)
            self.db_status_label.config(text="Validating setup...")
            from database.init_db import validate_database_setup
            validate_database_setup()
            setup_logger.info("Database validation passed")
            time.sleep(0.5)
            
            # Complete
            self.db_progress_var.set(100)
            self.db_status_label.config(text="Database setup complete!", foreground=get_status_color('success'))
            self.db_setup_complete = True
            self.completed_steps.add(1)  # Mark database setup as completed
            setup_logger.info("Database setup completed successfully")
            
        except Exception as e:
            setup_logger.error(f"Database setup failed: {e}")
            self.db_setup_error = str(e)
            self.db_progress_var.set(0)
            self.db_status_label.config(text="Database setup failed!", foreground=get_status_color('danger'))
            self.db_error_label.config(text=f"Error: {e}")
            self.retry_btn.pack(pady=5)
            self.db_setup_complete = False

    def _retry_database_setup(self):
        """Retry database setup after failure."""
        setup_logger.info("Retrying database setup")
        self._start_database_setup()

    # ── Step 2: Admin Account ─────────────────────────────────────────────────

    def _show_admin_account(self):
        self._step_header('', 'Administrator Account', 'Create your secure admin login')

        body = tk.Frame(self.content_frame, bg=_C_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)
        body.columnconfigure(0, weight=1)

        card = self._card(body)
        card.pack(fill=tk.X)
        card.columnconfigure(0, weight=1)

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.confirm  = tk.StringVar()

        def field(label, row, var, show=None):
            tk.Label(card, text=label, font=('Segoe UI', 10, 'bold'),
                     bg=_C_WHITE, fg=_C_TEXT, anchor='w').grid(
                row=row*2, column=0, sticky=tk.W, padx=20, pady=(16, 2))
            e = ttk.Entry(card, textvariable=var, width=36,
                          show=show or '', font=('Segoe UI', 11))
            e.grid(row=row*2+1, column=0, sticky=tk.EW, padx=20, pady=(0, 4))
            return e

        uname_entry = field('Username',         0, self.username)
        field('Password',                       1, self.password, show='•')
        field('Confirm Password',               2, self.confirm,  show='•')
        uname_entry.focus()

        hint = tk.Frame(card, bg='#eff6ff',
                        highlightbackground='#bfdbfe', highlightthickness=1)
        hint.grid(row=6, column=0, sticky=tk.EW, padx=20, pady=(8, 20))
        tk.Label(hint,
                 text='  Password requirements: 8+ characters, uppercase, lowercase and numbers.',
                 font=('Segoe UI', 9), bg='#eff6ff', fg='#1d4ed8',
                 anchor='w').pack(fill=tk.X, padx=6, pady=8)

    # ── Step 3: System Configuration ─────────────────────────────────────────

    def _show_system_config(self):
        self._step_header('', 'System Configuration', 'Set your business name, currency and date format')

        body = tk.Frame(self.content_frame, bg=_C_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)
        body.columnconfigure(0, weight=1)

        card = self._card(body)
        card.pack(fill=tk.X)
        card.columnconfigure(0, weight=1)

        tk.Label(card, text='Business Name', font=('Segoe UI', 10, 'bold'),
                 bg=_C_WHITE, fg=_C_TEXT, anchor='w').grid(
            row=0, column=0, sticky=tk.W, padx=20, pady=(20, 2))
        ttk.Entry(card, textvariable=self.business_name,
                  width=38, font=('Segoe UI', 11)).grid(
            row=1, column=0, sticky=tk.EW, padx=20, pady=(0, 4))

        tk.Label(card, text='Currency', font=('Segoe UI', 10, 'bold'),
                 bg=_C_WHITE, fg=_C_TEXT, anchor='w').grid(
            row=2, column=0, sticky=tk.W, padx=20, pady=(16, 2))
        _CURRENCIES = ['USD', 'EUR', 'GBP', 'KES', 'ZAR', 'CAD', 'AUD', 'JPY', 'CNY']
        cur = ttk.Combobox(
            card, textvariable=self.currency, width=36,
            values=_CURRENCIES,
            state='readonly', font=('Segoe UI', 11))
        cur.grid(row=3, column=0, sticky=tk.EW, padx=20, pady=(0, 4))
        # Preserve existing selection; default to USD only on first render
        if self.currency.get() not in _CURRENCIES:
            self.currency.set('USD')

        # ── Date Format ───────────────────────────────────────────────────
        tk.Frame(card, bg=_C_BORDER, height=1).grid(
            row=4, column=0, sticky=tk.EW, padx=20, pady=(16, 0))
        tk.Label(card, text='Date Format', font=('Segoe UI', 10, 'bold'),
                 bg=_C_WHITE, fg=_C_TEXT, anchor='w').grid(
            row=5, column=0, sticky=tk.W, padx=20, pady=(12, 2))
        tk.Label(card, text='How dates are displayed across the application.',
                 font=('Segoe UI', 9), bg=_C_WHITE, fg=_C_MUTED, anchor='w').grid(
            row=6, column=0, sticky=tk.W, padx=20, pady=(0, 6))

        _DATE_FORMATS = [
            ('%d/%m/%Y', 'DD/MM/YYYY'),
            ('%m/%d/%Y', 'MM/DD/YYYY'),
            ('%Y-%m-%d', 'YYYY-MM-DD'),
            ('%d-%m-%Y', 'DD-MM-YYYY'),
            ('%d.%m.%Y', 'DD.MM.YYYY'),
        ]
        from datetime import datetime as _dt
        radio_row = tk.Frame(card, bg=_C_WHITE)
        radio_row.grid(row=7, column=0, sticky=tk.W, padx=16, pady=(0, 4))

        preview_lbl = tk.Label(card, text='', font=('Segoe UI', 9, 'italic'),
                               bg=_C_WHITE, fg=_C_MUTED)
        preview_lbl.grid(row=8, column=0, sticky=tk.W, padx=20, pady=(0, 20))

        def _update_date_preview(*_):
            fmt = self.date_format_var.get()
            try:
                preview_lbl.config(text=f'Preview: {_dt.now().strftime(fmt)}')
            except Exception:
                preview_lbl.config(text='Preview: —')

        for fmt, label in _DATE_FORMATS:
            tk.Radiobutton(
                radio_row, text=label, variable=self.date_format_var,
                value=fmt, font=('Segoe UI', 10), bg=_C_WHITE, fg=_C_TEXT,
                activebackground=_C_WHITE, selectcolor=_C_WHITE,
                command=_update_date_preview,
            ).pack(side=tk.LEFT, padx=(4, 12))

        _update_date_preview()

    # ── Step 4: Preferences ──────────────────────────────────────────────────

    def _show_preferences(self):
        self._step_header('', 'Preferences', 'Personalise your experience')

        body = tk.Frame(self.content_frame, bg=_C_CARD)
        body.pack(fill=tk.X, expand=False, padx=32, pady=24)
        body.columnconfigure(0, weight=1)

        # ── Theme selection ───────────────────────────────────────────────
        theme_card = self._card(body)
        theme_card.pack(fill=tk.X, pady=(0, 16))
        theme_card.columnconfigure(0, weight=1)

        tk.Label(theme_card, text='App Theme', font=('Segoe UI', 11, 'bold'),
                 bg=_C_WHITE, fg=_C_TEXT, anchor='w').pack(
            anchor='w', padx=20, pady=(16, 2))
        tk.Label(theme_card, text='Choose the colour scheme for the application.',
                 font=('Segoe UI', 9), bg=_C_WHITE, fg=_C_MUTED, anchor='w').pack(
            anchor='w', padx=20, pady=(0, 12))

        swatch_grid = tk.Frame(theme_card, bg=_C_WHITE)
        swatch_grid.pack(fill=tk.X, padx=20, pady=(0, 16))

        _THEME_LIST = [
            ('default',       'Default',       '#2563eb', '#f5f5f5', '#1f2937'),
            ('dark',          'Dark',          '#4f46e5', '#1a1a2e', '#f1f5f9'),
            ('light',         'Light',         '#3b82f6', '#f8fafc', '#18181b'),
            ('blue',          'Ocean Blue',    '#0284c7', '#f0f9ff', '#0c4a6e'),
            ('green',         'Forest Green',  '#059669', '#f0fdf4', '#14532d'),
            ('purple',        'Royal Purple',  '#7c3aed', '#faf5ff', '#581c87'),
            ('high_contrast', 'High Contrast', '#000000', '#ffffff', '#000000'),
        ]

        self._theme_frames = {}

        def _select(key):
            self.theme_var.set(key)
            for k, f in self._theme_frames.items():
                sel = (k == key)
                f.config(highlightbackground=_C_PRIMARY if sel else _C_BORDER,
                         highlightthickness=3 if sel else 1)

        for idx, (key, name, primary, bg, fg_col) in enumerate(_THEME_LIST):
            col = idx % 4
            row = idx // 4
            sw = tk.Frame(swatch_grid, bg=bg,
                          highlightbackground=_C_BORDER, highlightthickness=1,
                          cursor='hand2', width=118, height=70)
            sw.grid(row=row, column=col, padx=4, pady=4, sticky='nw')
            sw.grid_propagate(False)
            self._theme_frames[key] = sw
            tk.Frame(sw, bg=primary, height=20).pack(fill=tk.X)
            tk.Label(sw, text=name, font=('Segoe UI', 8, 'bold'),
                     bg=bg, fg=fg_col).pack(pady=(4, 0))
            dot_row = tk.Frame(sw, bg=bg)
            dot_row.pack(pady=2)
            for dot_col in [primary, bg, fg_col]:
                tk.Label(dot_row, text='●', font=('Segoe UI', 7),
                         bg=bg, fg=dot_col).pack(side=tk.LEFT)

        # bind click after all children created
        for key, sw in self._theme_frames.items():
            k = key
            sw.bind('<Button-1>', lambda e, k=k: _select(k))
            for child in sw.winfo_children():
                child.bind('<Button-1>', lambda e, k=k: _select(k))
                for grandchild in child.winfo_children():
                    grandchild.bind('<Button-1>', lambda e, k=k: _select(k))

        _select(self.theme_var.get())
        # ── Receipt Footer ────────────────────────────────────────────────
        receipt_card = self._card(body)
        receipt_card.pack(fill=tk.X)
        receipt_card.columnconfigure(0, weight=1)

        tk.Label(receipt_card, text='Receipt Footer Message',
                 font=('Segoe UI', 11, 'bold'), bg=_C_WHITE, fg=_C_TEXT, anchor='w').grid(
            row=0, column=0, sticky=tk.W, padx=20, pady=(16, 2))
        tk.Label(receipt_card, text='Shown at the bottom of every receipt  (optional)',
                 font=('Segoe UI', 9), bg=_C_WHITE, fg=_C_MUTED, anchor='w').grid(
            row=1, column=0, sticky=tk.W, padx=20, pady=(0, 4))
        ttk.Entry(receipt_card, textvariable=self.receipt_footer_var,
                  width=38, font=('Segoe UI', 11)).grid(
            row=2, column=0, sticky=tk.EW, padx=20, pady=(0, 20))

        # ensure the canvas scroll region is updated
        self.content_frame.update_idletasks()
        self._scrollcanvas.configure(scrollregion=self._scrollcanvas.bbox('all'))

    def _save_preferences_settings(self):
        """Save theme and receipt footer to the database."""
        try:
            # Use set_theme() so the in-memory theme cache is updated immediately.
            # This ensures the login page renders with the chosen theme right away.
            from utils.theme import set_theme
            set_theme(self.theme_var.get())

            from database.init_db import get_connection
            footer = self.receipt_footer_var.get().strip()
            date_fmt = self.date_format_var.get().strip() or '%Y-%m-%d'
            with get_connection() as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                    ('receipt_footer', footer))
                conn.execute(
                    'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                    ('date_format', date_fmt))
                conn.commit()
            setup_logger.info("Preferences saved")
        except Exception as e:
            setup_logger.warning(f"Failed to save preferences (non-critical): {e}")

    # ── Step 5: Complete ──────────────────────────────────────────────────────

    def _show_complete(self):
        self._step_header('', 'Setup Complete!', 'Your store is ready — log in to get started')

        body = tk.Frame(self.content_frame, bg=_C_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)

        card = self._card(body)
        card.pack(fill=tk.X)
        tk.Label(card, text='Everything is configured and ready.',
                 font=('Segoe UI', 12), bg=_C_WHITE, fg=_C_TEXT).pack(pady=(24, 8))
        tk.Label(card,
                 text='Click Login above to sign in with the\nadministrator account you just created.',
                 font=('Segoe UI', 10), bg=_C_WHITE, fg=_C_MUTED,
                 justify=tk.CENTER).pack(pady=(0, 24))

    def _go_back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _go_next(self):
        if self.current_step < len(self.steps) - 1:
            # Validate current step before proceeding
            if self._validate_current_step():
                self._show_step(self.current_step + 1)

    def _validate_current_step(self):
        """Validate current step before allowing progression."""
        if self.current_step == 1:  # Database setup
            if not self.db_setup_complete:
                messagebox.showwarning("Setup Incomplete", 
                    "Database setup is not complete yet. Please wait for it to finish or check for errors.")
                return False
            return True
        elif self.current_step == 2:  # Admin account
            return self._validate_admin_form()
        elif self.current_step == 3:  # System config
            business_name = self.business_name.get().strip()
            if not business_name:
                messagebox.showerror("Validation Error", "Business name is required.")
                return False
            if len(business_name) < 2:
                messagebox.showerror("Validation Error", "Business name must be at least 2 characters.")
                return False
            return True
        elif self.current_step == 4:  # Preferences — all optional
            return True
        return True

    def _validate_admin_form(self):
        username = self.username.get().strip()
        password = self.password.get()
        confirm = self.confirm.get()
        
        if not username:
            messagebox.showerror("Error", "Username is required.")
            return False
        if len(username) < 3:
            messagebox.showerror("Error", "Username must be at least 3 characters.")
            return False
        if not password:
            messagebox.showerror("Error", "Password is required.")
            return False
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            messagebox.showerror("Error", error_msg)
            return False
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return False
        return True

    def _save_currency_setting(self):
        """Save business name and currency (code + symbol) to the database."""
        try:
            from database.init_db import get_connection
            from utils.i18n import get_default_currency_symbol_for_code
            code   = self.currency.get().strip().upper()
            symbol = get_default_currency_symbol_for_code(code)
            biz    = self.business_name.get().strip() or 'My Store'
            with get_connection() as conn:
                for key, value in [
                    ('business_name',  biz),
                    ('currency_code',  code),
                    ('currency_symbol', symbol),
                    ('currency',       code),   # legacy fallback
                ]:
                    conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        (key, value))
                conn.commit()
        except Exception as e:
            print(f"Warning: Failed to save currency/business setting: {e}")

    def _finish_setup(self):
        """Complete the setup with comprehensive error handling and recovery."""
        try:
            setup_logger.info("Starting final setup completion")
            
            # Step 1: Create admin user
            setup_logger.info("Creating admin user")
            username = self.username.get().strip()
            password = self.password.get()
            create_user(username=username, password=password, role="admin", active=True)
            self.completed_steps.add(2)  # Mark admin account as completed
            setup_logger.info(f"Admin user '{username}' created successfully")
            
            # Step 2: Save currency and system config
            setup_logger.info("Saving currency settings")
            self._save_currency_setting()
            self.completed_steps.add(3)  # Mark system config as completed

            # Step 2b: Save preferences (theme, receipt footer)
            setup_logger.info("Saving preferences")
            self._save_preferences_settings()
            self.completed_steps.add(4)  # Mark preferences as completed
            
            # Step 3: Final health check
            setup_logger.info("Running final health check")
            from main import validate_setup_health
            healthy, health_message = validate_setup_health()
            
            if not healthy:
                setup_logger.warning(f"Health check issues detected: {health_message}")
                # Show warning but don't fail setup
                messagebox.showwarning("Setup Warnings", 
                    f"Setup completed with some warnings:\n\n{health_message}\n\n"
                    "The system should still function, but you may want to review the configuration.")
            
            # Step 4: Seed sample data — demo mode only, never in live store
            import sys as _sys_seed
            if '--demo' in _sys_seed.argv:
                setup_logger.info("Demo mode: seeding sample data")
                self._seed_sample_data()
            else:
                setup_logger.info("Live mode: skipping sample data seed")

            # Step 5: Optimize database for production use
            setup_logger.info("Optimizing database for production use")
            self._optimize_database()
            
            # Success
            setup_logger.info("Setup completed successfully")
            messagebox.showinfo("Success", f"Setup complete!\n\nAdmin account '{username}' created successfully.\n\nYou can now log in.")
            self.on_success()
            
        except Exception as e:
            setup_logger.error(f"Setup completion failed: {e}")
            self.setup_errors.append(str(e))
            
            # Offer recovery options
            self._show_recovery_options(str(e))

    def _seed_sample_data(self):
        """Seed the main database with ~60 sample items across 10 categories for testing."""
        try:
            from database.init_db import get_connection
            with get_connection() as conn:
                # Skip if items already exist
                if conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] > 0:
                    setup_logger.info("Items already present — skipping sample data seed")
                    return

                # ── Categories ────────────────────────────────────────────────
                inv_cats = [
                    "Food & Beverages", "Snacks & Confectionery", "Dairy & Eggs",
                    "Bakery", "Fresh Produce", "Personal Care",
                    "Cleaning & Household", "Stationery & Office",
                    "Health & Pharmacy", "Electronics & Accessories",
                ]
                exp_cats = [
                    "Rent", "Utilities", "Salaries", "Restocking",
                    "Repairs & Maintenance", "Marketing & Advertising",
                    "Transport & Delivery", "Packaging", "Insurance", "Miscellaneous",
                ]
                for cat in inv_cats:
                    conn.execute(
                        "INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (cat,))
                for cat in exp_cats:
                    conn.execute(
                        "INSERT OR IGNORE INTO expense_categories (name) VALUES (?)", (cat,))

                # ── Items (name, category, cost, sell, qty, low_thresh) ────────
                items = [
                    # Food & Beverages
                    ("Coca-Cola 500ml",          "Food & Beverages",       55,   80, 200, 20),
                    ("Fanta Orange 500ml",        "Food & Beverages",       55,   80, 180, 20),
                    ("Water 500ml",               "Food & Beverages",       25,   40, 300, 30),
                    ("Juice 1L (Assorted)",       "Food & Beverages",       90,  130, 120, 15),
                    ("Energy Drink 250ml",        "Food & Beverages",       80,  120,  80, 10),
                    ("Black Tea Bags x25",        "Food & Beverages",       70,  110,  60, 10),
                    # Snacks & Confectionery
                    ("Crisps 100g",               "Snacks & Confectionery", 40,   60, 150, 20),
                    ("Chocolate Bar 50g",         "Snacks & Confectionery", 50,   80, 120, 15),
                    ("Biscuits 200g",             "Snacks & Confectionery", 60,   90, 100, 15),
                    ("Popcorn 80g",               "Snacks & Confectionery", 35,   55,  90, 10),
                    ("Gummy Bears 150g",          "Snacks & Confectionery", 55,   85,  70, 10),
                    ("Peanuts 200g",              "Snacks & Confectionery", 65,  100,  80, 10),
                    # Dairy & Eggs
                    ("Fresh Milk 500ml",          "Dairy & Eggs",           50,   70, 100, 20),
                    ("Yoghurt 400g",              "Dairy & Eggs",           70,  105,  80, 10),
                    ("Butter 250g",               "Dairy & Eggs",           95,  140,  60, 10),
                    ("Eggs (tray of 30)",         "Dairy & Eggs",          320,  420,  40,  5),
                    ("Cheese Slices 200g",        "Dairy & Eggs",          180,  260,  50,  8),
                    # Bakery
                    ("White Bread 400g",          "Bakery",                 50,   75, 100, 15),
                    ("Whole Wheat Bread 400g",    "Bakery",                 60,   90,  80, 10),
                    ("Croissant",                 "Bakery",                 35,   55,  60, 10),
                    ("Doughnuts x4",              "Bakery",                 60,   95,  50,  8),
                    # Fresh Produce
                    ("Tomatoes 1kg",              "Fresh Produce",          60,   90,  80, 10),
                    ("Onions 1kg",                "Fresh Produce",          55,   80,  80, 10),
                    ("Bananas (bunch)",           "Fresh Produce",          80,  120,  60, 10),
                    ("Potatoes 2kg",              "Fresh Produce",         100,  150,  70, 10),
                    ("Carrots 500g",              "Fresh Produce",          45,   70,  60,  8),
                    # Personal Care
                    ("Soap Bar 100g",             "Personal Care",          40,   65, 120, 15),
                    ("Shampoo 200ml",             "Personal Care",         140,  210,  80, 10),
                    ("Toothpaste 100ml",          "Personal Care",          90,  140,  90, 12),
                    ("Deodorant Stick",           "Personal Care",         180,  270,  60,  8),
                    ("Sanitary Pads x10",         "Personal Care",         100,  160,  70, 10),
                    ("Lotion 300ml",              "Personal Care",         160,  240,  55,  8),
                    # Cleaning & Household
                    ("Dishwashing Liquid 500ml",  "Cleaning & Household",  90,  140,  80, 10),
                    ("Laundry Detergent 1kg",     "Cleaning & Household", 200,  300,  60,  8),
                    ("Toilet Paper x4",           "Cleaning & Household",  80,  130, 100, 15),
                    ("Bleach 500ml",              "Cleaning & Household",  60,   95,  70, 10),
                    ("Floor Cleaner 750ml",       "Cleaning & Household", 110,  170,  50,  8),
                    # Stationery & Office
                    ("Exercise Book A4",          "Stationery & Office",   30,   50, 100, 20),
                    ("Ballpoint Pen (blue)",      "Stationery & Office",   10,   18, 200, 30),
                    ("Pencil HB",                 "Stationery & Office",    8,   15, 150, 25),
                    ("Ruler 30cm",                "Stationery & Office",   25,   40,  80, 10),
                    ("Stapler",                   "Stationery & Office",   180,  280,  30,  5),
                    ("A4 Paper Ream 500 sheets",  "Stationery & Office",   350,  520,  40,  5),
                    # Health & Pharmacy
                    ("Paracetamol x24",           "Health & Pharmacy",      45,   75, 100, 15),
                    ("Vitamin C 500mg x30",       "Health & Pharmacy",     120,  190,  60, 10),
                    ("Hand Sanitiser 100ml",      "Health & Pharmacy",      90,  140,  80, 12),
                    ("Bandages Assorted x10",     "Health & Pharmacy",      60,  100,  50,  8),
                    ("Antiseptic Cream 30g",      "Health & Pharmacy",      80,  130,  50,  8),
                    # Electronics & Accessories
                    ("AA Batteries x4",           "Electronics & Accessories",  80, 130,  80, 10),
                    ("USB-A Charging Cable 1m",   "Electronics & Accessories", 200, 320,  50,  8),
                    ("Phone Screen Protector",    "Electronics & Accessories", 120, 200,  40,  5),
                    ("Earphones (basic)",         "Electronics & Accessories", 250, 420,  30,  5),
                    ("Extension Lead 3-way",      "Electronics & Accessories", 450, 700,  20,  3),
                    ("LED Bulb 9W",               "Electronics & Accessories", 110, 180,  60,  8),
                ]

                for name, category, cost, sell, qty, low in items:
                    conn.execute("""
                        INSERT OR IGNORE INTO items
                            (name, category, cost_price, selling_price,
                             quantity, low_stock_threshold, barcode)
                        VALUES (?, ?, ?, ?, ?, ?, NULL)
                    """, (name, category, cost, sell, qty, low))

                conn.commit()
                setup_logger.info(f"Sample data seeded: {len(items)} items across {len(inv_cats)} categories")
        except Exception as e:
            setup_logger.warning(f"Sample data seeding failed (non-critical): {e}")

    def _show_recovery_options(self, error_message):
        """Show recovery options when setup fails."""
        setup_logger.info("Showing recovery options to user")
        
        recovery_window = tk.Toplevel(self.parent)
        recovery_window.title("Setup Recovery")
        recovery_window.geometry("500x400")
        recovery_window.resizable(True, True)
        recovery_window.transient(self.parent)
        recovery_window.grab_set()
        
        ttk.Label(recovery_window, text="Setup encountered an error", 
                 font=("Segoe UI", 14, "bold")).pack(pady=(20, 10))
        
        # Error details
        error_frame = ttk.LabelFrame(recovery_window, text="Error Details")
        error_frame.pack(fill=tk.X, padx=20, pady=10)
        
        error_text = tk.Text(error_frame, height=6, wrap=tk.WORD, font=("Segoe UI", 9))
        error_text.insert(tk.END, error_message)
        error_text.config(state=tk.DISABLED)
        error_text.pack(fill=tk.X, padx=10, pady=10)
        
        # Recovery options
        ttk.Label(recovery_window, text="Choose how to proceed:", 
                 font=("Segoe UI", 11)).pack(pady=(10, 5))
        
        btn_frame = ttk.Frame(recovery_window)
        btn_frame.pack(pady=20)
        
        def retry_setup():
            setup_logger.info("User chose to retry setup")
            recovery_window.destroy()
            # Reset to first step and try again
            self.current_step = 0
            self.setup_errors = []
            self.completed_steps = set()
            self._show_step(0)
        
        def skip_to_login():
            setup_logger.info("User chose to skip to login despite errors")
            recovery_window.destroy()
            # Try to proceed despite errors
            try:
                self.on_success()
            except Exception as e:
                messagebox.showerror("Error", f"Cannot proceed to login: {e}")
        
        def exit_setup():
            setup_logger.info("User chose to exit setup")
            recovery_window.destroy()
            self.parent.quit()
        
        ttk.Button(btn_frame, text="Retry Setup", command=retry_setup).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Continue Anyway", command=skip_to_login).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Exit Setup", command=exit_setup).pack(side=tk.LEFT, padx=10)
        
        # Show completed steps
        if self.completed_steps:
            completed_frame = ttk.LabelFrame(recovery_window, text="Successfully Completed Steps")
            completed_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
            
            completed_text = []
            step_names = ["Welcome", "Database Setup", "Admin Account", "System Config"]
            for step_idx in sorted(self.completed_steps):
                if step_idx < len(step_names):
                    completed_text.append(f"✓ {step_names[step_idx]}")
            
            ttk.Label(completed_frame, text="\n".join(completed_text), 
                     font=("Segoe UI", 9), justify=tk.LEFT).pack(padx=10, pady=5)

    def _show_help(self):
        """Show setup help and documentation."""
        help_window = tk.Toplevel(self.parent)
        help_window.title("Setup Help")
        help_window.geometry("600x500")
        help_window.resizable(True, True)
        help_window.transient(self.parent)
        
        # Create scrollable text area
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Segoe UI", 10), padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Help content
        help_content = """
Kiosk POS Setup Help
====================

Welcome to the Kiosk POS setup wizard! This guide will help you understand each step of the setup process.

STEP 1: Welcome
---------------
This is just an introduction. Click "Next" to begin setup.

STEP 2: Database Setup
----------------------
The system creates and initializes the database with all necessary tables and default data. This step:
• Creates database tables for items, sales, users, etc.
• Sets up default units of measure, categories, and default data
• Validates the database structure

If this step fails, check that the database directory is writable.

STEP 3: Administrator Account
-----------------------------
Create your main administrator account. Requirements:
• Username: 3+ characters
• Password: 8+ characters with uppercase, lowercase, and numbers
• This account has full access to all system features

STEP 4: System Configuration
---------------------------
Configure basic system settings:
• Business Name: Your store/company name
• Currency: Primary currency for transactions (USD, EUR, GBP, etc.)

TROUBLESHOOTING
===============

Database Issues:
• Ensure the application has write permissions to its directory
• Check that no other instances of the application are running
• Try running the application as administrator (Windows)

Email Configuration:
• SMTP settings are validated during setup
• Test your email settings in the Email Settings menu after setup
• Common issues: incorrect server/port, authentication failures

Performance:
• Initial setup may take a minute to complete
• Database optimization runs automatically after setup
• For best performance, ensure adequate disk space

GETTING STARTED
==============

After setup completes:
1. Log in with your administrator account
2. Configure email notifications (optional)
3. Add your products in the Inventory section
4. Add your products and configure pricing in the Inventory section
5. Start processing sales!

For more detailed documentation, visit the user manual or contact support.
        """
        
        text_widget.insert(tk.END, help_content.strip())
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)

    def _optimize_database(self):
        """Optimize database for production use after setup."""
        try:
            from database.init_db import get_connection
            with get_connection() as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode = WAL;")
                # Set synchronous mode for balance of performance and safety
                conn.execute("PRAGMA synchronous = NORMAL;")
                # Run VACUUM to optimize database file
                conn.execute("VACUUM;")
                # Create indexes for better performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_items_sale_id ON sales_items(sale_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);")
                conn.commit()
            setup_logger.info("Database optimization completed")
        except Exception as e:
            setup_logger.warning(f"Database optimization failed (non-critical): {e}")
            # Don't fail setup for optimization issues
