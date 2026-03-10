"""Enhanced System Information UI for Kiosk POS."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sqlite3
import sys
import os
import platform
import threading
from datetime import datetime

from database.init_db import get_default_db_path
from utils.date_utils import format_date


def _fmt_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _fmt_ts(ts: float) -> str:
    dt = datetime.fromtimestamp(ts)
    return f"{format_date(dt)} {dt.strftime('%H:%M:%S')}"

class SystemInfoFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    # ── data collection ─────────────────────────────────────────────────
    def _collect_data(self) -> dict:
        """Gather all system data before any widgets are created."""
        data = {}

        # Application
        try:
            from main import APP_VERSION
        except Exception:
            APP_VERSION = "N/A"
        data['app_version'] = APP_VERSION
        data['build_mode'] = "Frozen (exe)" if getattr(sys, 'frozen', False) else "Development (source)"
        data['executable'] = sys.executable
        data['cwd'] = str(Path.cwd())
        try:
            app_dir = Path(__file__).parent.parent
            data['app_dir'] = str(app_dir)
            data['log_dir'] = str(app_dir / "logs")
            data['config_file'] = str(app_dir / "config.json")
        except Exception:
            data['app_dir'] = data['log_dir'] = data['config_file'] = "N/A"
        _now = datetime.now()
        data['started_at'] = f"{format_date(_now)} {_now.strftime('%H:%M:%S')}"

        # Python
        data['py_version'] = sys.version.split()[0]
        data['py_full'] = sys.version[:65]
        data['py_platform'] = sys.platform
        data['arch'] = platform.machine()
        data['processor'] = (platform.processor()[:50] or "N/A")
        data['default_enc'] = sys.getdefaultencoding().upper()
        data['fs_enc'] = sys.getfilesystemencoding().upper()
        data['max_int'] = str(sys.maxsize)

        # OS
        data['os_name'] = platform.system()
        data['os_release'] = platform.release()
        data['os_version'] = platform.version()[:65]
        data['os_platform'] = platform.platform()[:65]
        data['node'] = platform.node()
        data['login_user'] = (os.environ.get("USERNAME") or os.environ.get("USER")
                              or os.environ.get("LOGNAME", "N/A"))
        data['home_dir'] = str(Path.home())
        data['temp_dir'] = str(Path(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp"))))

        # Hardware (psutil — can be slow)
        try:
            import psutil
            mem  = psutil.virtual_memory()
            swap = psutil.swap_memory()
            disk = psutil.disk_usage(str(Path.cwd()))
            freq = psutil.cpu_freq()
            data['hw'] = {
                'cpu_phys':   str(psutil.cpu_count(logical=False) or "N/A"),
                'cpu_logi':   str(psutil.cpu_count(logical=True)  or "N/A"),
                'cpu_mhz':    f"{freq.current:.0f} MHz" if freq else None,
                'ram_total':  _fmt_bytes(mem.total),
                'ram_used':   _fmt_bytes(mem.used),
                'ram_avail':  _fmt_bytes(mem.available),
                'ram_pct':    mem.percent,
                'swap_total': _fmt_bytes(swap.total),
                'disk_total': _fmt_bytes(disk.total),
                'disk_free':  _fmt_bytes(disk.free),
                'disk_pct':   disk.percent,
            }
        except ImportError:
            data['hw'] = {'cpu_phys': str(os.cpu_count() or "N/A"), 'no_psutil': True}

        # Database
        db_path = get_default_db_path()
        data['db_path'] = str(db_path)
        data['db_exists'] = db_path.exists()
        if data['db_exists']:
            stats = db_path.stat()
            data['db_size']    = _fmt_bytes(stats.st_size)
            data['db_mtime']   = _fmt_ts(stats.st_mtime)
            data['db_ctime']   = _fmt_ts(stats.st_ctime)
            try:
                conn = sqlite3.connect(str(db_path))
                cur  = conn.cursor()
                table_counts = [
                    ("Users",         "users"),
                    ("Items",         "items"),
                    ("Categories",    "categories"),
                    ("Sales",         "sales"),
                    ("Sales Items",   "sales_items"),
                    ("Customers",     "customers"),
                    ("Expenses",      "expenses"),
                    ("Expense Cats",  "expense_categories"),
                    ("Stock Batches", "stock_batches"),
                ]
                counts = []
                for label, tbl in table_counts:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                        counts.append((label, f"{cur.fetchone()[0]:,} records"))
                    except Exception:
                        pass
                data['db_counts'] = counts
                try:
                    cur.execute("PRAGMA journal_mode")
                    data['db_journal'] = cur.fetchone()[0].upper()
                except Exception:
                    data['db_journal'] = "N/A"
                cur.execute("SELECT sqlite_version()")
                data['sqlite_ver'] = cur.fetchone()[0]
                conn.close()
                data['db_error'] = None
            except Exception as ex:
                data['db_counts'] = []
                data['db_journal'] = data['sqlite_ver'] = "N/A"
                data['db_error'] = str(ex)[:80]

        # Packages
        packages = [
            ("tkinter",       "tkinter"),
            ("PIL / Pillow",  "PIL"),
            ("reportlab",     "reportlab"),
            ("matplotlib",    "matplotlib"),
            ("pycountry",     "pycountry"),
            ("tkcalendar",    "tkcalendar"),
            ("psutil",        "psutil"),
            ("requests",      "requests"),
            ("openpyxl",      "openpyxl"),
            ("pandas",        "pandas"),
        ]
        pkg_rows = []
        for name, mod in packages:
            try:
                m   = __import__(mod)
                ver = getattr(m, "__version__", getattr(m, "version", "installed"))
                pkg_rows.append((name, f"✅ {ver}", True))
            except ImportError:
                pkg_rows.append((name, "❌ Not installed", False))
        data['packages'] = pkg_rows

        _cap = datetime.now()
        data['captured_at'] = f"{format_date(_cap)} {_cap.strftime('%H:%M:%S')}"
        return data

    # ── UI build ─────────────────────────────────────────────────────────
    def _build_ui(self):
        from utils.theme import get_theme_colors
        colors = get_theme_colors()

        for w in self.winfo_children():
            w.destroy()

        # ── Show loading indicator immediately ──────────────────────────
        loading_frame = tk.Frame(self, bg=colors['background'])
        loading_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            loading_frame,
            text="🔧 System Information",
            font=("Segoe UI", 18, "bold"),
            bg=colors['background'], fg=colors['text'],
        ).pack(pady=(60, 12))

        spinner_var = tk.StringVar(value="Loading…")
        spinner_lbl = tk.Label(
            loading_frame,
            textvariable=spinner_var,
            font=("Segoe UI", 11),
            bg=colors['background'], fg=colors['text_secondary'],
        )
        spinner_lbl.pack()

        bar = ttk.Progressbar(loading_frame, mode='indeterminate', length=260)
        bar.pack(pady=(12, 0))
        bar.start(12)

        _dots = ["", ".", "..", "…"]
        _dot_idx = [0]

        def _animate():
            if not self.winfo_exists():
                return
            _dot_idx[0] = (_dot_idx[0] + 1) % len(_dots)
            spinner_var.set(f"Gathering system data{_dots[_dot_idx[0]]}")
            self._anim_id = self.after(400, _animate)

        self._anim_id = self.after(400, _animate)

        # ── Collect data off the UI thread ──────────────────────────────
        def _worker():
            try:
                d = self._collect_data()
            except Exception as exc:
                d = {'_error': str(exc)}
            if self.winfo_exists():
                self.after(0, lambda: _render(d))

        def _render(d):
            if hasattr(self, '_anim_id'):
                self.after_cancel(self._anim_id)
            for w in self.winfo_children():
                w.destroy()

            if d.get('_error'):
                tk.Label(self, text=f"Error loading system info:\n{d['_error']}",
                         font=("Segoe UI", 10), fg='red').pack(pady=40)
                return

            self._render_data(d, colors)

        threading.Thread(target=_worker, daemon=True).start()

    def _render_data(self, d: dict, colors: dict):
        canvas = tk.Canvas(self, bg=colors['background'], highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        inner = tk.Frame(canvas, bg=colors['background'])
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # Page header
        hdr = tk.Frame(inner, bg=colors['surface'])
        hdr.pack(fill=tk.X, pady=(0, 18))
        tk.Label(hdr, text="🔧 System Information",
                 font=("Segoe UI", 18, "bold"),
                 bg=colors['surface'], fg=colors['text']).pack(anchor=tk.W, padx=20, pady=(14, 2))
        tk.Label(hdr, text="Application, database, environment and hardware details",
                 font=("Segoe UI", 10),
                 bg=colors['surface'], fg=colors['text_secondary']).pack(anchor=tk.W, padx=20, pady=(0, 14))
        tk.Frame(hdr, bg=colors['border'], height=1).pack(fill=tk.X)

        # Refresh button
        btn_row = tk.Frame(inner, bg=colors['background'])
        btn_row.pack(fill=tk.X, padx=20, pady=(0, 12))
        refresh_btn = tk.Button(btn_row, text="🔄 Refresh",
                  font=("Segoe UI", 10), relief=tk.FLAT, bd=0, cursor="hand2",
                  bg=colors['border'], fg=colors['text'],
                  activebackground=colors['neutral_bg'],
                  activeforeground=colors['primary'],
                  command=self._build_ui)
        refresh_btn.pack(side=tk.LEFT, ipadx=8, ipady=3)
        refresh_btn.bind("<Enter>", lambda e: refresh_btn.configure(bg=colors['neutral_bg'], fg=colors['primary']))
        refresh_btn.bind("<Leave>", lambda e: refresh_btn.configure(bg=colors['border'], fg=colors['text']))

        col_frame = tk.Frame(inner, bg=colors['background'])
        col_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 20))
        col_frame.columnconfigure(0, weight=1)
        col_frame.columnconfigure(1, weight=1)

        def _card(title, icon, row, col):
            c = tk.Frame(col_frame, bg=colors['surface'],
                         highlightbackground=colors['border'], highlightthickness=1)
            c.grid(row=row, column=col, sticky=tk.NSEW, padx=8, pady=8)
            col_frame.rowconfigure(row, weight=1)
            ch = tk.Frame(c, bg=colors['primary'])
            ch.pack(fill=tk.X)
            tk.Label(ch, text=f"{icon}  {title}",
                     font=("Segoe UI", 11, "bold"),
                     bg=colors['primary'], fg=colors['text_white']).pack(anchor=tk.W, padx=12, pady=7)
            body = tk.Frame(c, bg=colors['surface'])
            body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 12))
            body.columnconfigure(1, weight=1)
            return body

        def _row(body, label, value, r, value_color=None):
            tk.Label(body, text=label, font=("Segoe UI", 9, "bold"),
                     bg=colors['surface'], fg=colors['text_secondary'],
                     anchor="w").grid(row=r, column=0, sticky=tk.W, pady=2, padx=(0, 14))
            tk.Label(body, text=str(value), font=("Segoe UI", 9),
                     bg=colors['surface'], fg=value_color or colors['text'],
                     anchor="w", wraplength=300).grid(row=r, column=1, sticky=tk.W, pady=2)

        # ── 1: Application ─────────────────────────────────────────
        b1 = _card("Application", "🏪", 0, 0)
        exe = d['executable']
        cwd = d['cwd']
        _row(b1, "App Name",      "Kiosk POS",                                         0)
        _row(b1, "Version",       d['app_version'],                                     1, colors.get('success', '#22c55e'))
        _row(b1, "Build Mode",    d['build_mode'],                                      2)
        _row(b1, "Executable",    (exe[:65] + "…") if len(exe) > 65 else exe,           3)
        _row(b1, "Working Dir",   (cwd[:65] + "…") if len(cwd) > 65 else cwd,           4)
        _row(b1, "App Directory", d['app_dir'],                                         5)
        _row(b1, "Log Directory", d['log_dir'],                                         6)
        _row(b1, "Config File",   d['config_file'],                                     7)
        _row(b1, "Started At",    d['started_at'],                                      8)

        # ── 2: Python & Runtime ────────────────────────────────────
        b2 = _card("Python & Runtime", "🐍", 0, 1)
        _row(b2, "Python Version",  d['py_version'],   0, colors.get('info', '#06b6d4'))
        _row(b2, "Full Version",    d['py_full'],       1)
        _row(b2, "Platform",        d['py_platform'],   2)
        _row(b2, "Architecture",    d['arch'],          3)
        _row(b2, "Processor",       d['processor'],     4)
        _row(b2, "Default Encoding",d['default_enc'],   5)
        _row(b2, "File System Enc", d['fs_enc'],        6)
        _row(b2, "Max Int",         d['max_int'],       7)

        # ── 3: Operating System ────────────────────────────────────
        b3 = _card("Operating System", "💻", 1, 0)
        _row(b3, "OS",          d['os_name'],         0)
        _row(b3, "Release",     d['os_release'],      1)
        _row(b3, "Version",     d['os_version'],      2)
        _row(b3, "Full Name",   d['os_platform'],     3)
        _row(b3, "Node / Host", d['node'],            4)
        _row(b3, "Login User",  d['login_user'],      5)
        _row(b3, "Home Dir",    d['home_dir'],        6)
        _row(b3, "Temp Dir",    d['temp_dir'],        7)

        # ── 4: Hardware Resources ──────────────────────────────────
        b4 = _card("Hardware Resources", "⚡", 1, 1)
        hw = d['hw']
        if hw.get('no_psutil'):
            _row(b4, "CPU Cores", hw['cpu_phys'],                                      0)
            _row(b4, "Note", "Install psutil for full hardware details",               1, colors.get('warning', '#eab308'))
        else:
            r = 0
            _row(b4, "CPU Cores (physical)", hw['cpu_phys'],                           r); r += 1
            _row(b4, "CPU Cores (logical)",  hw['cpu_logi'],                           r); r += 1
            if hw.get('cpu_mhz'):
                _row(b4, "CPU Frequency", hw['cpu_mhz'],                              r); r += 1
            _row(b4, "Total RAM",     hw['ram_total'],                                 r); r += 1
            _row(b4, "Used RAM",      hw['ram_used'],                                  r); r += 1
            _row(b4, "Available RAM", hw['ram_avail'],                                 r); r += 1
            mem_col = colors.get('danger') if hw['ram_pct'] > 85 else (colors.get('warning') if hw['ram_pct'] > 70 else None)
            _row(b4, "RAM Usage",     f"{hw['ram_pct']:.1f}%",                         r, mem_col); r += 1
            _row(b4, "Swap Total",    hw['swap_total'],                                r); r += 1
            _row(b4, "Disk Total",    hw['disk_total'],                                r); r += 1
            _row(b4, "Disk Free",     hw['disk_free'],                                 r); r += 1
            disk_col = colors.get('danger') if hw['disk_pct'] > 90 else (colors.get('warning') if hw['disk_pct'] > 75 else None)
            _row(b4, "Disk Usage",    f"{hw['disk_pct']:.1f}%",                        r, disk_col)

        # ── 5: Database ────────────────────────────────────────────
        b5 = _card("Database", "🗄", 2, 0)
        db_str = d['db_path']
        _row(b5, "Path",   (db_str[:65] + "…") if len(db_str) > 65 else db_str,        0)
        _row(b5, "Status", "✅ Connected" if d['db_exists'] else "❌ Not found",        1,
             colors.get('success') if d['db_exists'] else colors.get('danger'))
        if d['db_exists']:
            _row(b5, "File Size",     d['db_size'],    2)
            _row(b5, "Last Modified", d['db_mtime'],   3)
            _row(b5, "Created",       d['db_ctime'],   4)
            r = 5
            for label, val in d.get('db_counts', []):
                _row(b5, f"  {label}", val, r); r += 1
            _row(b5, "Journal Mode",  d.get('db_journal', 'N/A'), r); r += 1
            _row(b5, "SQLite Version",d.get('sqlite_ver', 'N/A'), r)
            if d.get('db_error'):
                _row(b5, "DB Error", d['db_error'], r + 1, colors.get('danger'))

        # ── 6: Key Packages ────────────────────────────────────────
        b6 = _card("Installed Packages", "📦", 2, 1)
        for r, (name, val, ok) in enumerate(d['packages']):
            _row(b6, name, val, r, colors.get('success', '#22c55e') if ok else colors.get('danger', '#f43f5e'))

        # Footer
        tk.Label(inner,
                 text=f"ℹ  Captured at {d['captured_at']}  •  {platform.node()}",
                 font=("Segoe UI", 8), bg=colors['background'],
                 fg=colors['text_secondary']).pack(anchor=tk.W, padx=20, pady=(0, 16))

