from __future__ import annotations
from pathlib import Path
import sys
import os
import subprocess
import logging
import tkinter as tk
from tkinter import ttk, messagebox

# Configure application logging before importing modules that may log during import
if getattr(sys, 'frozen', False):
    _app_dir = Path(sys.executable).parent
else:
    _app_dir = Path(__file__).parent
_log_dir = _app_dir / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
_log_file = _log_dir / "kioskpos.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from database.init_db import initialize_database
from utils.app_config import get_or_create_config
from modules.users import ensure_admin_user
from modules import backup
# All UI imports are done lazily inside their respective functions so the
# login screen appears immediately without waiting for heavy modules to load.

APP_TITLE = "Kiosk POS v1.004"
APP_VERSION = "1.004"


# Use per-install config to determine DB path
def _default_db_path() -> Path:
    import sys
    # Demo mode: use a separate isolated database
    if '--demo' in sys.argv:
        app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        return app_dir / 'database' / 'demo.db'
    # Always use the EXE directory for config/DB when bundled, never _MEIPASS
    if getattr(sys, 'frozen', False):
        app_dir = Path(sys.executable).parent
    else:
        app_dir = Path(__file__).parent
    config = get_or_create_config(app_dir)
    return Path(config["db_path"])


def validate_setup_health() -> tuple[bool, str]:
    """
    Perform comprehensive health checks on the system setup.
    
    Returns:
        Tuple of (healthy: bool, message: str)
    """
    issues = []
    
    try:
        # Check database connectivity
        from database.init_db import get_connection
        with get_connection() as conn:
            # Check if required tables exist
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            required_tables = {'users', 'items', 'sales', 'sales_items', 'settings'}
            
            missing_tables = required_tables - existing_tables
            if missing_tables:
                issues.append(f"Missing database tables: {', '.join(missing_tables)}")
            
            # Check if admin user exists
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1")
            admin_count = cursor.fetchone()[0]
            if admin_count == 0:
                issues.append("No active admin user found")
            
            # Check settings table has basic config
            cursor = conn.execute("SELECT COUNT(*) FROM settings")
            settings_count = cursor.fetchone()[0]
            if settings_count == 0:
                issues.append("No system settings configured")
                
    except Exception as e:
        issues.append(f"Database connectivity issue: {e}")
    
    # Check configuration files
    config_files = ['email_config.json']
    for config_file in config_files:
        if not Path(__file__).parent.joinpath(config_file).exists():
            issues.append(f"Configuration file missing: {config_file}")
    
    # Check assets directory
    assets_dir = Path(__file__).parent / "assets"
    if not assets_dir.exists():
        issues.append("Assets directory missing")
    
    if issues:
        return False, "Setup health check failed:\n" + "\n".join(f"• {issue}" for issue in issues)
    
    return True, "System setup is healthy and ready to use!"


def bootstrap_database(*, create_default_admin: bool = True) -> Path:
    """Create the database file and schema if missing, returning the resolved path."""
    db_path = _default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path = initialize_database(db_path)
    if not db_path.exists():
        raise RuntimeError("Database creation failed; file not found after initialization.")
    
    # Validate database setup
    from database.init_db import validate_database_setup
    validate_database_setup(db_path)
    
    if create_default_admin:
        ensure_admin_user()

    # Apply any pending database migrations automatically during bootstrap
    try:
        from database.migrations import run_pending_migrations
        applied = run_pending_migrations()
        if applied:
            try:
                import tkinter as _tk
                _tk.messagebox.showinfo("Database Updated", f"Applied migrations: {', '.join(applied)}")
            except Exception:
                logger.info(f"Applied migrations: {', '.join(applied)}")
    except Exception as e:
        logger.warning(f"Failed to run pending migrations at startup: {e}")

    return db_path


def _run_auto_backup_silent() -> None:
    """Run auto-backup check in the background after the UI is fully ready."""
    try:
        backup.check_and_run_auto_backup()
    except Exception:
        pass


def _build_shell(root: tk.Tk, user: dict):
    """Create the persistent shell layout with nav and content area."""
    from ui.shell import AppShell
    for child in root.winfo_children():
        child.destroy()
    if not hasattr(root, "cart_state"):
        root.cart_state = {"items": [], "suspended": []}
    root.shell = AppShell(
        root,
        user=user,
        on_nav=lambda key: _handle_nav(root, key),
        on_logout=lambda: _logout(root),
    )
    root.shell.grid(row=0, column=0, sticky=tk.NSEW)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    return root.shell


def _ensure_shell(root: tk.Tk) -> AppShell | None:
    shell = getattr(root, "shell", None)
    user = getattr(root, "current_user", None)
    if shell:
        return shell
    if not user:
        return None
    return _build_shell(root, user)


def _render(root: tk.Tk, *, title: str, builder, subtitle: str | None = None, cache_key: str | None = None):
    """Render a frame inside the shell's content area."""
    shell = _ensure_shell(root)
    if not shell:
        return None
    
    # Use cached frame if available, otherwise build new one
    if cache_key and cache_key in shell.cached_frames:
        frame = shell.cached_frames[cache_key]
        # Refresh live data (currency, theme, etc.) on every navigation to a cached frame
        if hasattr(frame, 'refresh') and callable(frame.refresh):
            try:
                frame.refresh()
            except Exception:
                pass
    else:
        frame = builder(shell.content_area)
    
    shell.set_content(frame, title=title, subtitle=subtitle, cache_key=cache_key)
    return frame


def _logout(root: tk.Tk) -> None:
    root.current_user = None
    shell = getattr(root, "shell", None)
    if shell:
        shell.destroy()
    root.shell = None
    show_login(root)


def _handle_nav(root: tk.Tk, key: str) -> None:
    """Central navigation handler invoked by the shell nav buttons."""
    if key == "dashboard":
        show_home(root, getattr(root, "current_user", {}))
    elif key == "pos":
        show_pos(root)
    elif key == "inventory":
        show_inventory(root)
    elif key == "stock_receiving":
        show_stock_receiving(root)
    elif key == "purchase_orders":
        show_purchase_orders(root)
    elif key == "reports":
        show_reports(root)
    elif key == "order_history":
        show_order_history(root)
    elif key == "expenses":
        show_expenses(root)
    elif key == "reconciliation":
        show_reconciliation(root)
    elif key == "stock_recon":
        show_stock_reconciliation(root)
    elif key == "backup":
        show_backup(root)
    elif key == "reset_demo":
        import sys as _sys_rd
        from pathlib import Path as _Path_rd
        _demo_db = _Path_rd(__file__).parent / 'database' / 'demo.db'
        if not _demo_db.exists():
            messagebox.showinfo('Reset Demo', 'No demo database found — nothing to reset.')
            return
        if messagebox.askyesno(
            'Reset Demo Environment',
            'This will delete the demo database and all demo data.\n\n'
            'The next launch will start fresh with the setup wizard.\n\nContinue?'
        ):
            try:
                _demo_db.unlink()
                for _ext in ('.db-wal', '.db-shm'):
                    _s = _demo_db.with_suffix(_ext)
                    if _s.exists():
                        _s.unlink(missing_ok=True)
                messagebox.showinfo('Reset Complete',
                    'Demo environment reset.\nThe next launch will start fresh.')
            except Exception as _exc:
                messagebox.showerror('Error', f'Could not reset demo environment:\n{_exc}')
    elif key == "settings":
        _show_settings_menu(root, getattr(root, "current_user", {}))


def _go_back(root: tk.Tk) -> None:
    """Go back to the previous page within Settings."""
    shell = _ensure_shell(root)
    if shell:
        prev_key = shell.go_back()
        if prev_key:
            # Map Settings subpage keys to handler functions
            if prev_key == "settings":
                _show_settings_menu(root, getattr(root, "current_user", {}))
            elif prev_key == "user_mgmt":
                show_user_mgmt(root)
            elif prev_key == "vat_settings":
                show_vat_settings(root)
            elif prev_key == "email_settings":
                show_email_settings(root)
            elif prev_key == "currency_settings":
                show_currency_settings(root)
            elif prev_key == "upgrade_manager":
                show_upgrade_manager(root)
        else:
            # No previous page in Settings, go to dashboard
            show_home(root, getattr(root, "current_user", {}))


def _set_refresh_button(shell, root: tk.Tk, page_key: str) -> None:
    """Set the header button to Home for main pages."""
    if shell:
        shell.set_header_button("🏠 Home", lambda: show_home(root, getattr(root, "current_user", {})))


def _set_back_button(shell, root: tk.Tk) -> None:
    """Set the header button to Back for Settings pages."""
    if shell:
        shell.set_header_button("← Back", lambda: _go_back(root))


def _activate_settings_subpage(shell, key: str) -> None:
    """Activate a settings subpage with proper navigation tracking."""
    if shell:
        shell.activate_nav("settings")  # Keep the button highlighted as "settings"
        shell.nav_history.append(key)  # Track the subpage separately


def _require_admin(root: tk.Tk) -> dict | None:
    user = getattr(root, "current_user", None)
    if not user or user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return None
    return user


def _require_permission(root: tk.Tk, permission: str) -> dict | None:
    """Check if current user has the required permission."""
    user = getattr(root, "current_user", None)
    if not user:
        messagebox.showerror("Access denied", "Authentication required")
        return None

    from modules import permissions
    if not permissions.has_permission(user, permission):
        messagebox.showerror("Access denied", f"Permission '{permission}' required")
        return None

    return user


def show_home(root: tk.Tk, user: dict) -> None:
    """Show dashboard as home screen inside the shell."""
    from ui.dashboard import DashboardFrame
    root.current_user = user
    frame = _render(root, title="Dashboard", subtitle="Today at a glance",
                    builder=lambda parent: DashboardFrame(parent, on_home=None),
                    cache_key="dashboard")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("dashboard")
        _set_refresh_button(shell, root, "dashboard")


def restart_application(root: tk.Tk) -> None:
    """Restart the application."""
    if messagebox.askyesno("Restart Application", "Are you sure you want to restart the application?"):
        try:
            # Get the Python executable and script path
            python = sys.executable
            script = sys.argv[0]
            
            # Close the current window
            root.destroy()
            
            # Start a new instance
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                # Running as script
                subprocess.Popen([python, script])
                sys.exit(0)
        except Exception as e:
            logger.exception("Failed to restart application: %s", e)
            messagebox.showerror("Error", f"Failed to restart: {e}")


def _show_settings_menu(root: tk.Tk, user: dict) -> None:
    """Show settings submenu within the shell."""
    if not _require_permission(root, 'view_settings'):
        return

    def builder(container: tk.Misc):
        from utils.theme import get_theme_colors
        colors = get_theme_colors()

        wrapper = tk.Frame(container, bg=colors['background'])
        wrapper.columnconfigure(0, weight=1)
        wrapper.rowconfigure(0, weight=1)

        canvas = tk.Canvas(wrapper, bg=colors['background'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        frame = tk.Frame(canvas, bg=colors['background'])
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(frame_id, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # ── Header ─────────────────────────────────────────────────
        hdr = tk.Frame(frame, bg=colors['surface'])
        hdr.pack(fill=tk.X, pady=(0, 18))
        tk.Label(hdr, text="⚙ System Settings",
                 font=("Segoe UI", 18, "bold"),
                 bg=colors['surface'], fg=colors['text']).pack(anchor=tk.W, padx=20, pady=(14, 2))
        tk.Label(hdr, text="Manage your application configuration",
                 font=("Segoe UI", 10),
                 bg=colors['surface'], fg=colors['text_secondary']).pack(anchor=tk.W, padx=20, pady=(0, 14))
        tk.Frame(hdr, bg=colors['border'], height=1).pack(fill=tk.X)

        categories = [
            ("🔐 Access & Security", [
                ("👤 User Management",        lambda: show_user_mgmt(root)),
                ("🔒 Permission Management",  lambda: show_permission_mgmt(root)),
                ("🔑 Change Password",        lambda: show_change_password(root, user)),
            ]),
            ("🎨 Appearance", [
                ("🎨 Theme Settings",         lambda: show_theme_settings(root)),
                ("📅 Date Format",            lambda: show_date_format_settings(root)),
            ]),
            ("💰 Finance & Tax", [
                ("📊 VAT Settings",           lambda: show_vat_settings(root)),
                ("💱 Currency Settings",      lambda: show_currency_settings(root)),
                ("💰 Financial Reconciliation", lambda: show_reconciliation(root)),
            ]),
            ("🛒 Operations", [
                ("🛍️ POS Settings",           lambda: show_pos_settings(root)),
                ("🧾 Receipt Settings",       lambda: show_receipt_settings(root)),
                ("📦 Inventory Settings",     lambda: show_inventory_settings(root)),
                ("⚖️ Units of Measure",       lambda: show_uom_settings(root)),
            ]),
            ("📊 Reports & Notifications", [
                ("📊 Report Settings",        lambda: show_report_settings(root)),
                ("📧 Email Notifications",    lambda: show_email_settings(root)),
            ]),
            ("🔧 System", [
                ("🔧 System Info",            lambda: show_system_info(root)),
                ("📋 Audit Logs",             lambda: show_audit_logs(root)),
                ("⬆️ Upgrade Manager",        lambda: show_upgrade_manager(root)),
                ("🔄 Restart App",            lambda: restart_application(root)),
            ]),
        ]

        outer = tk.Frame(frame, bg=colors['background'])
        outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        row = 0
        for col_idx, (cat_title, items) in enumerate(categories):
            col = col_idx % 2
            if col == 0 and col_idx > 0:
                row += 1

            # Category card
            card = tk.Frame(outer, bg=colors['surface'],
                            relief='flat', bd=0,
                            highlightbackground=colors['border'],
                            highlightthickness=1)
            card.grid(row=row, column=col, sticky=tk.NSEW, padx=8, pady=8)
            outer.rowconfigure(row, weight=1)

            # Category header bar
            cat_hdr = tk.Frame(card, bg=colors['primary'])
            cat_hdr.pack(fill=tk.X)
            tk.Label(cat_hdr, text=cat_title,
                     font=("Segoe UI", 11, "bold"),
                     bg=colors['primary'],
                     fg=colors['text_white']).pack(anchor=tk.W, padx=14, pady=8)

            # Buttons inside card
            btn_area = tk.Frame(card, bg=colors['surface'])
            btn_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            for label, cmd in items:
                btn = tk.Button(
                    btn_area,
                    text=label,
                    anchor="w",
                    padx=10,
                    pady=6,
                    relief=tk.FLAT,
                    bd=0,
                    bg=colors['surface'],
                    fg=colors['text'],
                    activebackground=colors['neutral_bg'],
                    activeforeground=colors['primary'],
                    highlightthickness=1,
                    highlightbackground=colors['border'],
                    font=("Segoe UI", 10),
                    cursor="hand2",
                    command=cmd,
                )
                btn.pack(fill=tk.X, pady=2)

                def _on_enter(e, b=btn):
                    b.configure(bg=colors['neutral_bg'], fg=colors['primary'])
                def _on_leave(e, b=btn):
                    b.configure(bg=colors['surface'], fg=colors['text'])
                btn.bind("<Enter>", _on_enter)
                btn.bind("<Leave>", _on_leave)

        return wrapper

    frame = _render(root, title="Settings", subtitle="Manage your system", builder=builder, cache_key="settings")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("settings")
        shell.set_header_button("🏠 Home", lambda: show_home(root, user))


def show_system_info(root: tk.Tk) -> None:
    if not _require_permission(root, 'view_system_info'):
        return
    from ui.system_info import SystemInfoFrame

    frame = _render(root, title="System Info", subtitle="Database and environment", builder=lambda parent: SystemInfoFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "system_info")
        _set_back_button(shell, root)


def show_audit_logs(root: tk.Tk) -> None:
    if not _require_permission(root, 'view_audit_logs'):
        return
    from ui.audit_logs import AuditLogsFrame

    frame = _render(root, title="Audit Logs", subtitle="System activity and user actions", builder=lambda parent: AuditLogsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "audit_logs")
        _set_back_button(shell, root)


def show_upgrade_manager(root: tk.Tk) -> None:
    if not _require_permission(root, "manage_upgrades"):
        return
    from ui.upgrade_manager import UpgradeManagerFrame

    frame = _render(root, title="Upgrade Manager", subtitle="Upload and apply system upgrades", builder=lambda parent: UpgradeManagerFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "upgrade_manager")
        _set_back_button(shell, root)


def show_demo_environment(root: tk.Tk) -> None:
    """In-app Demo / Test Environment management page."""
    if not _require_permission(root, 'manage_settings'):
        return

    def builder(container: tk.Misc):
        import sys as _sys
        from pathlib import Path as _Path
        from utils.theme import get_theme_colors
        colors = get_theme_colors()
        is_demo = '--demo' in _sys.argv
        demo_db = _Path(__file__).parent / 'database' / 'demo.db'
        demo_exists = demo_db.exists()

        f = tk.Frame(container, bg=colors['background'])
        f.columnconfigure(0, weight=1)

        # ── Status banner ─────────────────────────────────────────
        banner_color = '#f59e0b' if is_demo else colors['surface']
        banner_fg = '#1c1917' if is_demo else colors['text']
        banner = tk.Frame(f, bg=banner_color,
                          highlightbackground='#d97706' if is_demo else colors['border'],
                          highlightthickness=1)
        banner.pack(fill=tk.X, pady=(0, 18))
        status_text = (
            '🧪  DEMO MODE — you are in an isolated test environment'
            if is_demo else
            '⚪  Demo mode is not active — you are using your live database'
        )
        tk.Label(banner, text=status_text,
                 bg=banner_color, fg=banner_fg,
                 font=('Segoe UI', 11, 'bold'), pady=10, padx=16,
                 anchor='w').pack(fill=tk.X)

        # ── What is the demo environment ─────────────────────────
        info_card = tk.Frame(f, bg=colors['surface'],
                             highlightbackground=colors['border'],
                             highlightthickness=1)
        info_card.pack(fill=tk.X, pady=(0, 14))
        tk.Label(info_card, text='ℹ  What is the Demo Environment?',
                 bg=colors['surface'], fg=colors['text'],
                 font=('Segoe UI', 11, 'bold'), anchor='w',
                 padx=14).pack(fill=tk.X, pady=(10, 4))
        tk.Label(info_card,
                 text=(
                     'The demo environment opens Kiosk POS in a completely isolated database\n'
                     'that is separate from your live data. It starts exactly like a fresh\n'
                     'installation — you go through the full setup: create an admin account,\n'
                     'configure your business, add items, and explore every feature freely.\n\n'
                     'Your live data is never touched. Reset it any time to start over.'
                 ),
                 bg=colors['surface'], fg=colors['text_secondary'],
                 font=('Segoe UI', 10), justify=tk.LEFT,
                 padx=14).pack(fill=tk.X, pady=(0, 12))

        # ── How to use ───────────────────────────────────────────
        how_card = tk.Frame(f, bg=colors['surface'],
                            highlightbackground=colors['border'],
                            highlightthickness=1)
        how_card.pack(fill=tk.X, pady=(0, 14))
        tk.Label(how_card, text='🚀  How to use',
                 bg=colors['surface'], fg=colors['text'],
                 font=('Segoe UI', 11, 'bold'), anchor='w',
                 padx=14).pack(fill=tk.X, pady=(10, 4))
        steps = [
            '1.  Click "Launch Demo Environment" below.',
            '2.  A new window opens with a fresh setup wizard.',
            '3.  Create your admin password and configure the demo store.',
            '4.  Explore all features — sales, inventory, reports, settings.',
            '5.  When done, close the demo window. Your live app is untouched.',
            '6.  Click "Reset Demo" to wipe it clean and start fresh again.',
        ]
        for step in steps:
            tk.Label(how_card, text=step,
                     bg=colors['surface'], fg=colors['text_secondary'],
                     font=('Segoe UI', 10), anchor='w',
                     padx=20).pack(fill=tk.X, pady=1)
        tk.Frame(how_card, bg=colors['surface'], height=10).pack()

        # ── Actions ──────────────────────────────────────────────
        act_card = tk.Frame(f, bg=colors['surface'],
                            highlightbackground=colors['border'],
                            highlightthickness=1)
        act_card.pack(fill=tk.X, pady=(0, 14))
        tk.Label(act_card, text='⚡  Actions',
                 bg=colors['surface'], fg=colors['text'],
                 font=('Segoe UI', 11, 'bold'), anchor='w',
                 padx=14).pack(fill=tk.X, pady=(10, 6))

        btn_row = tk.Frame(act_card, bg=colors['surface'])
        btn_row.pack(fill=tk.X, padx=14, pady=(0, 12))

        def _launch_demo():
            import subprocess as _sp
            _sp.Popen([_sys.executable, str(_Path(__file__)), '--demo'])

        def _reset_demo():
            if not messagebox.askyesno(
                'Reset Demo Environment',
                'This will delete the demo database and all demo data.\n\n'
                'The next launch will start fresh with the setup wizard.\n\n'
                'Continue?'
            ):
                return
            try:
                if demo_db.exists():
                    demo_db.unlink()
                for ext in ('.db-wal', '.db-shm'):
                    side = demo_db.with_suffix(ext)
                    if side.exists():
                        side.unlink(missing_ok=True)
                messagebox.showinfo('Reset Complete',
                    'Demo environment has been reset.\n'
                    'The next launch will start with the setup wizard.')
            except Exception as exc:
                messagebox.showerror('Error', f'Could not reset demo environment:\n{exc}')

        tk.Button(
            btn_row,
            text='Launch Demo Environment',
            bg=colors['surface'], fg=colors['primary'],
            activebackground=colors['neutral_bg'], activeforeground=colors['primary_dark'],
            font=('Segoe UI', 10, 'bold'),
            relief=tk.FLAT, padx=16, pady=8, cursor='hand2',
            highlightbackground=colors['border'], highlightthickness=1,
            command=_launch_demo,
        ).pack(side=tk.LEFT, padx=(0, 12))

        reset_state = tk.NORMAL if demo_exists else tk.DISABLED
        reset_fg = colors['danger'] if demo_exists else colors['text_light']
        reset_btn = tk.Button(
            btn_row,
            text='Reset Demo',
            bg=colors['surface'], fg=reset_fg,
            activebackground=colors['neutral_bg'], activeforeground=colors['danger'],
            font=('Segoe UI', 10),
            relief=tk.FLAT, padx=14, pady=8, cursor='hand2',
            highlightbackground=colors['border'], highlightthickness=1,
            state=reset_state,
            command=_reset_demo,
        )
        reset_btn.pack(side=tk.LEFT)

        db_status = (
            f'Demo database: {demo_db}'
            + (f'  —  {demo_db.stat().st_size // 1024} KB' if demo_exists else '  —  not yet created')
        )
        tk.Label(act_card, text=db_status,
                 bg=colors['surface'], fg=colors['text_secondary'],
                 font=('Segoe UI', 8), padx=14).pack(anchor='w', pady=(0, 8))

        return f

    frame = _render(root, title='Demo Environment',
                    subtitle='Isolated test environment — starts fresh like a new installation',
                    builder=builder)
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav('settings')
        shell.set_header_button('Home', lambda: show_home(root, getattr(root, 'current_user', {})))


def show_currency_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_currency_settings'):
        return
    from ui.settings import CurrencySettingsFrame

    frame = _render(root, title="Currency", subtitle="Display currency and rounding", builder=lambda parent: CurrencySettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "currency_settings")
        _set_back_button(shell, root)


def show_theme_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_settings'):
        return
    from ui.theme_settings import ThemeSettingsFrame

    frame = _render(root, title="Theme", subtitle="Customize application appearance", builder=lambda parent: ThemeSettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "theme_settings")
        _set_back_button(shell, root)


def show_date_format_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_date_format'):
        return
    from ui.date_format_settings import DateFormatSettingsFrame

    frame = _render(root, title="Date Format", subtitle="Choose how dates are displayed", builder=lambda parent: DateFormatSettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "date_format_settings")
        _set_back_button(shell, root)


def show_receipt_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_receipt_settings'):
        return
    from ui.receipt_settings import ReceiptSettingsFrame

    frame = _render(root, title="Receipt Settings", subtitle="Configure receipt printing options", builder=lambda parent: ReceiptSettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "receipt_settings")
        _set_back_button(shell, root)


def show_pos_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_pos_settings'):
        return
    from ui.pos_settings import POSSettingsFrame

    frame = _render(root, title="POS Settings", subtitle="Configure POS behavior and display", builder=lambda parent: POSSettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "pos_settings")
        _set_back_button(shell, root)


def show_report_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_report_settings'):
        return
    from ui.report_settings import ReportSettingsFrame

    frame = _render(root, title="Report Settings", subtitle="Configure report display and export preferences", builder=lambda parent: ReportSettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "report_settings")
        _set_back_button(shell, root)


def show_inventory_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_inventory_settings'):
        return
    from ui.inventory_settings import InventorySettingsFrame

    frame = _render(root, title="Inventory Settings", subtitle="Configure inventory alerts and behavior", builder=lambda parent: InventorySettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "inventory_settings")
        _set_back_button(shell, root)


def show_inventory(root: tk.Tk) -> None:
    if not _require_permission(root, "view_inventory"):
        return
    from ui.inventory import InventoryFrame
    frame = _render(root, title="Inventory", subtitle="Items, stock, and pricing", builder=lambda parent: InventoryFrame(parent), cache_key="inventory")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("inventory")
        _set_refresh_button(shell, root, "inventory")


def show_pos(root: tk.Tk) -> None:
    """Show the POS / cart screen."""
    if not _require_permission(root, "process_sales"):
        return
    from ui.pos import PosFrame
    frame = _render(
        root,
        title="Point of Sale",
        subtitle="Sales and checkout",
        builder=lambda parent: PosFrame(parent),
        cache_key="pos",
    )
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("pos")
        _set_refresh_button(shell, root, "pos")


def show_stock_receiving(root: tk.Tk) -> None:
    """Show the Stock Receiving UI for managing inventory purchases with lot tracking."""
    if not _require_permission(root, "receive_stock"):
        return
    from ui.stock_receiving import StockReceivingFrame
    
    user_id = getattr(root, "current_user", {}).get("user_id")
    frame = _render(
        root, 
        title="Stock Receiving", 
        subtitle="Receive inventory with cost tracking", 
        builder=lambda parent: StockReceivingFrame(parent, user_id=user_id),
        cache_key="stock_receiving"
    )
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("stock_receiving")
        # Store frame reference for refresh button and create custom refresh handler
        root.stock_receiving_frame = frame
        shell.set_header_button("🏠 Home", lambda: show_home(root, getattr(root, "current_user", {})))


def show_purchase_orders(root: tk.Tk) -> None:
    """Show the Purchase Orders (LPO/PO) UI."""
    if not _require_permission(root, "view_purchase_orders"):
        return
    from ui.purchase_orders_ui import PurchaseOrdersFrame
    frame = _render(
        root,
        title="Purchase Orders",
        subtitle="Create and manage LPOs / POs",
        builder=lambda parent: PurchaseOrdersFrame(parent),
        cache_key="purchase_orders",
    )
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("purchase_orders")
        _set_refresh_button(shell, root, "pos")
        # refresh helpers from HEAD branch
        try:
            frame.refresh_all()
            frame.ensure_populated(force=True)
        except Exception:
            pass


def show_user_mgmt(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_users'):
        return
    from ui.user_mgmt import UserManagementFrame
    frame = _render(root, title="Users", subtitle="Manage accounts and roles", builder=lambda parent: UserManagementFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "user_mgmt")
        _set_back_button(shell, root)


def show_permission_mgmt(root: tk.Tk) -> None:
    if not _require_permission(root, "manage_permissions"):
        return
    from ui.permission_mgmt import PermissionManagementFrame

    frame = _render(root, title="Permission Management", subtitle="Manage user permissions explicitly", builder=lambda parent: PermissionManagementFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "permission_mgmt")
        _set_back_button(shell, root)


def show_vat_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_vat_settings'):
        return
    from ui.vat_settings import VatSettingsFrame
    frame = _render(root, title="VAT Settings", subtitle="Configure tax rates", builder=lambda parent: VatSettingsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "vat_settings")
        _set_back_button(shell, root)


def show_uom_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_uom_settings'):
        return
    from ui.uom_settings import UomSettingsFrame
    frame = _render(root, title="Units of Measure", subtitle="Configure measurement units", builder=lambda parent: UomSettingsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "uom_settings")
        _set_back_button(shell, root)


def show_reports(root: tk.Tk) -> None:
    if not _require_permission(root, "view_reports"):
        return
    from ui.reports import ReportsFrame
    frame = _render(root, title="Reports", subtitle="Performance and history", builder=lambda parent: ReportsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))), cache_key="reports")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("reports")
        _set_refresh_button(shell, root, "reports")


def show_order_history(root: tk.Tk) -> None:
    if not _require_permission(root, "view_order_history"):
        return
    from ui.order_history import OrderHistoryFrame
    frame = _render(root, title="Order History", subtitle="View orders and receipts", builder=lambda parent: OrderHistoryFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))), cache_key="order_history")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("order_history")
        _set_refresh_button(shell, root, "order_history")


def show_expenses(root: tk.Tk) -> None:
    if not _require_permission(root, "view_expenses"):
        return
    from ui.expenses import ExpensesFrame
    frame = _render(root, title="Expenses", subtitle="Track spending", builder=lambda parent: ExpensesFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))), cache_key="expenses")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("expenses")
        _set_refresh_button(shell, root, "expenses")


def show_backup(root: tk.Tk) -> None:
    if not _require_permission(root, 'backup_database'):
        return
    from ui.backup import BackupFrame
    frame = _render(root, title="Backup", subtitle="Protect your data", builder=lambda parent: BackupFrame(parent, on_home=None), cache_key="backup")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("backup")
        shell.set_header_button("🏠 Home", lambda: show_home(root, getattr(root, "current_user", {})))


def show_email_settings(root: tk.Tk) -> None:
    if not _require_permission(root, 'manage_email_settings'):
        return
    from ui.email_settings import EmailSettingsFrame
    frame = _render(root, title="Email Notifications", subtitle="Alerts and receipts", builder=lambda parent: EmailSettingsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "email_settings")
        _set_back_button(shell, root)


def show_reconciliation(root: tk.Tk) -> None:
    """Show financial reconciliation interface inside the app shell (default).

    Use the header button 'Open in Window' to pop the view into a separate window if needed.
    """
    if not _require_permission(root, 'view_reconciliation'):
        return
    # Lazy import to avoid module-level UI imports before DB init
    from ui.comprehensive_reconciliation_ui import ComprehensiveReconciliationUI

    # Render inside the main app shell
    def builder(parent: tk.Misc):
        frame = ComprehensiveReconciliationUI(parent, on_home=lambda: show_home(root, getattr(root, 'current_user', {})))
        return frame

    frame = _render(root, title="Payment Reconciliation", builder=builder, subtitle="Reconcile payments", cache_key="reconciliation")
    shell = _ensure_shell(root)

    if shell and frame:
        shell.activate_nav("reconciliation")
        shell.set_header_button("🏠 Home", lambda: show_home(root, getattr(root, "current_user", {})))


def show_reconciliation_window(root: tk.Tk) -> None:
    """Open the reconciliation UI in a dedicated, well-sized Toplevel window."""
    if not _require_permission(root, 'view_reconciliation'):
        return
    from ui.comprehensive_reconciliation_ui import ComprehensiveReconciliationUI

    recon_window = tk.Toplevel(root)
    recon_window.title("Payment Reconciliation - Kiosk POS")

    # Use a sensible default size that fits most screens and lets the UI display fully
    recon_window.geometry("1200x800")
    recon_window.minsize(900, 700)
    recon_window.resizable(True, True)

    recon_ui = ComprehensiveReconciliationUI(recon_window, on_home=lambda: recon_window.destroy())
    recon_ui.pack(fill=tk.BOTH, expand=True)

    # Ensure decorations and focus
    recon_window.attributes('-topmost', False)
    recon_window.overrideredirect(False)
    recon_window.lift()
    recon_window.focus_set()

    # Center on screen
    screen_width = recon_window.winfo_screenwidth()
    screen_height = recon_window.winfo_screenheight()
    final_width = min(1200, screen_width - 150)
    final_height = min(800, screen_height - 150)
    x = max(0, (screen_width // 2) - (final_width // 2))
    y = max(0, (screen_height // 2) - (final_height // 2))
    recon_window.geometry(f"{final_width}x{final_height}+{x}+{y}")

    def on_close():
        recon_window.destroy()

    recon_window.protocol("WM_DELETE_WINDOW", on_close)
    recon_window.focus_set()


def show_stock_reconciliation(root: tk.Tk) -> None:
    """Show stock reconciliation interface inside the app shell."""
    if not _require_permission(root, 'view_reconciliation'):
        return
    from ui.stock_reconciliation_ui import StockReconciliationUI

    def builder(parent: tk.Misc):
        frame = StockReconciliationUI(parent, on_home=lambda: show_home(root, getattr(root, 'current_user', {})))
        return frame

    frame = _render(root, title="Stock Reconciliation", builder=builder, subtitle="Reconcile physical stock counts", cache_key="stock_recon")
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("stock_recon")


def show_change_password(root: tk.Tk, user: dict) -> None:
    from ui.user_mgmt import ChangePasswordDialog
    ChangePasswordDialog(root, user['username'])
    # stay on home after closing dialog


def show_login(root: tk.Tk) -> None:
    from ui.login import LoginFrame
    from utils.theme import get_theme_colors, apply_theme_to_root
    for child in root.winfo_children():
        child.destroy()
    root.shell = None
    # Apply theme to root so background matches the set theme
    apply_theme_to_root(root)
    theme_colors = get_theme_colors()
    root.configure(bg=theme_colors['surface'])
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)
    login_frame = LoginFrame(root, on_success=lambda user: _launch_shell(root, user))
    login_frame.grid(row=0, column=0, sticky=tk.NSEW)
    root.deiconify()  # Show window now that login is ready


def _launch_shell(root: tk.Tk, user: dict) -> None:
    root.current_user = user
    _build_shell(root, user)
    show_home(root, user)
    # Schedule a background update check 3 s after login so the shell is fully rendered
    root.after(3000, lambda: _run_startup_update_check(root))


def _run_startup_update_check(root: tk.Tk) -> None:
    """Background update check that runs once after login."""
    try:
        from modules.update_check import run_startup_check
        def _on_result(info):
            if info:
                def _notify():
                    shell = getattr(root, "shell", None)
                    if shell and hasattr(shell, "show_update_notification"):
                        shell.show_update_notification(
                            info,
                            on_click=lambda: show_upgrade_manager(root),
                        )
                root.after(0, _notify)
        run_startup_check(APP_VERSION, _on_result)
    except Exception as e:
        logger.debug(f"Startup update check failed: {e}")


def main() -> None:

    import sys
    logger.debug("Command line args: %s", sys.argv)  # Debug: print arguments
    logger.info("Application starting; frozen=%s", getattr(sys, 'frozen', False))
    
    # Verify dependencies before proceeding
    try:
        from utils.app_config import verify_dependencies
        verify_dependencies()
    except RuntimeError as e:
        # For command line operations, print to stderr and exit
        if "--initialize-db" in sys.argv or "--recalc-prices" in sys.argv:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        # For GUI mode, show error dialog
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Dependency Error", str(e))
            root.destroy()
        except Exception:
            print(str(e), file=sys.stderr)
        sys.exit(1)
    

    db_file = _default_db_path()

    # Command line support: initialize DB during install without showing UI
    if "--initialize-db" in sys.argv:
        try:
            # For GUI apps, show message boxes instead of print
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            messagebox.showinfo("Database Setup", "Starting database initialization...")
            
            db_path = _default_db_path()
            
            # For fresh installs, ensure no existing database files interfere
            db_dir = db_path.parent
            removed_files = []
            for existing_db in db_dir.glob("pos_*.db"):
                removed_files.append(str(existing_db))
                existing_db.unlink(missing_ok=True)
            
            bootstrap_database(create_default_admin=False)
            
            success_msg = f"Database initialization completed successfully!\n\nDatabase: {db_path}"
            if removed_files:
                success_msg += f"\n\nCleaned up old databases:\n" + "\n".join(removed_files)
            
            messagebox.showinfo("Database Setup Complete", success_msg)
            root.destroy()
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Database Setup Failed", f"Database initialization failed: {e}")
            root.destroy()
            raise
        return

    # Command line support: run setup health check
    if "--health-check" in sys.argv:
        try:
            root = tk.Tk()
            root.withdraw()
            
            healthy, message = validate_setup_health()
            
            if healthy:
                messagebox.showinfo("Health Check Passed", message)
            else:
                messagebox.showerror("Health Check Failed", message)
            
            root.destroy()
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Health Check Error", f"Failed to run health check: {e}")
            root.destroy()
            raise
        return

    # Command line support: recalculate per-unit prices
    if "--recalc-prices" in sys.argv:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Price Recalc", "Recalculating per-unit prices. This may take a moment...")
            from database import init_db
            db_path = _default_db_path()
            updated = init_db.recalculate_per_unit_values(db_path)
            messagebox.showinfo("Price Recalc Complete", f"Recalculated per-unit prices for {updated} item(s)")
            root.destroy()
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Price Recalc Failed", f"Price recalculation failed: {e}")
            root.destroy()
            raise
        return

    # ── All non-UI setup runs BEFORE creating the Tk window ──────────────────
    # This way the window is created once and immediately has content — no blank
    # flash and no title-bar decorations ever get lost.
    from modules.users import list_users
    is_demo = '--demo' in sys.argv
    is_first_time = not db_file.exists()
    bootstrap_database(create_default_admin=False)
    users = list_users()

    # ── Create root window ────────────────────────────────────────────────────
    root = tk.Tk()
    root.withdraw()  # Hide immediately — before any event loop tick paints a blank frame
    root.geometry("1600x1000")
    root.minsize(1400, 800)
    root.resizable(True, True)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)
    root.grid_propagate(False)
    style = ttk.Style(root)
    style.theme_use("clam")
    
    # Apply system-wide theme from settings
    from utils.theme import get_theme_colors, apply_theme_to_root
    theme_colors = get_theme_colors()
    apply_theme_to_root(root)
    root.configure(bg=theme_colors['background'])
    
    # Increase row height and font for Treeview to improve readability and make tables visually larger
    try:
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10),
                       background=theme_colors['surface'], fieldbackground=theme_colors['surface'],
                       foreground=theme_colors['text'])
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"),
                       background=theme_colors['table_header'], foreground=theme_colors['text'])
        style.map("Treeview",
                  background=[("selected", theme_colors['primary_light'])],
                  foreground=[("selected", theme_colors['text'])])
        style.configure("TLabel", font=("Segoe UI", 10), foreground=theme_colors['text'])
        style.configure("TFrame", background=theme_colors['background'])
        style.configure("Card.TLabelframe", borderwidth=2, relief="raised", padding=10)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 12, "bold"))
    except Exception:
        pass
    root.title(APP_TITLE + "  [DEMO MODE]" if is_demo else APP_TITLE)

    # Set window icon
    import os, sys
    if hasattr(sys, "_MEIPASS"):
        import tempfile
        import shutil
        temp_dir = tempfile.gettempdir()
        temp_icon = os.path.join(temp_dir, "app_icon.ico")
        shutil.copy(os.path.join(sys._MEIPASS, "assets", "app_icon.ico"), temp_icon)
        icon_path = temp_icon
    else:
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass
        try:
            icon_img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, icon_img)
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import ctypes
                LR_LOADFROMFILE = 0x00000010
                IMAGE_ICON = 1
                WM_SETICON = 0x0080
                hicon_small = ctypes.windll.user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                hicon_big = ctypes.windll.user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                if hicon_small:
                    ctypes.windll.user32.SendMessageW(root.winfo_id(), WM_SETICON, 0, hicon_small)
                if hicon_big:
                    ctypes.windll.user32.SendMessageW(root.winfo_id(), WM_SETICON, 1, hicon_big)
            except Exception:
                pass

    def after_admin_setup():
        show_login(root)

    def _show_setup_wizard():
        """Present the AdminSetupFrame (called from landing or directly in demo mode)."""
        for child in root.winfo_children():
            child.destroy()
        try:
            from ui.admin_setup import AdminSetupFrame
            root.rowconfigure(0, weight=1)
            root.rowconfigure(1, weight=0)
            setup_frame = AdminSetupFrame(root, on_success=after_admin_setup)
            setup_frame.grid(row=0, column=0, sticky=tk.NSEW)
        except Exception as e:
            logger.exception("Failed to initialize AdminSetupFrame: %s", e)
            messagebox.showerror("Initialization error", f"Failed to start admin setup: {e}")

    # ── Show first frame immediately — window goes straight from hidden to content ──
    if not users:
        if is_demo:
            # Demo mode: go straight to setup wizard (no landing — user already chose demo)
            _show_setup_wizard()
        else:
            # First run: show landing screen so user can choose Setup or Try Demo
            try:
                from ui.landing import LandingFrame
                root.rowconfigure(0, weight=1)
                root.rowconfigure(1, weight=0)
                landing = LandingFrame(
                    root,
                    on_setup=_show_setup_wizard,
                    on_login=lambda: show_login(root),
                )
                landing.grid(row=0, column=0, sticky=tk.NSEW)
            except Exception as e:
                logger.exception("Failed to initialize LandingFrame: %s", e)
                # Fallback: go straight to setup wizard
                _show_setup_wizard()
    else:
        try:
            show_login(root)
            if not is_demo:
                root.after(3000, lambda: _run_auto_backup_silent())
        except Exception as e:
            logger.exception("Failed to show login frame: %s", e)
            messagebox.showerror("Initialization error", f"Failed to open login: {e}")

    # Maximise AFTER content is in place so the title bar is always intact
    root.deiconify()  # Ensure window is visible (show_login also calls this, but be explicit)
    try:
        root.state("zoomed")
    except Exception:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()
