from __future__ import annotations
from pathlib import Path
import sys
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
# UI and other imports that access the database are imported lazily inside main()
# to ensure database initialization runs before any module-level database access.
from ui.order_history import OrderHistoryFrame

APP_TITLE = "Kiosk POS v1.003"
APP_VERSION = "1.003"


# Use per-install config to determine DB path
def _default_db_path() -> Path:
    import sys
    # Always use the EXE directory for config/DB when bundled, never _MEIPASS
    if getattr(sys, 'frozen', False):
        app_dir = Path(sys.executable).parent
    else:
        app_dir = Path(__file__).parent
    config = get_or_create_config(app_dir)
    return Path(config["db_path"])


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
    try:
        backup.check_and_run_auto_backup()
    except Exception:
        pass
    return db_path


def _build_shell(root: tk.Tk, user: dict) -> AppShell:
    """Create the persistent shell layout with nav and content area."""
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


def _render(root: tk.Tk, *, title: str, builder, subtitle: str | None = None):
    """Render a frame inside the shell's content area."""
    shell = _ensure_shell(root)
    if not shell:
        return None
    frame = builder(shell.content_area)
    shell.set_content(frame, title=title, subtitle=subtitle)
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
    elif key == "cart":
        show_cart(root)
    elif key == "inventory":
        show_inventory(root)
    elif key == "reports":
        show_reports(root)
    elif key == "order_history":
        show_order_history(root)
    elif key == "expenses":
        show_expenses(root)
    elif key == "backup":
        show_backup(root)
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
        else:
            # No previous page in Settings, go to dashboard
            show_home(root, getattr(root, "current_user", {}))


def _set_refresh_button(shell, root: tk.Tk, page_key: str) -> None:
    """Set the header button to Refresh for main pages."""
    if shell:
        shell.set_header_button("🔄 Refresh", lambda: _handle_nav(root, page_key))


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


def show_home(root: tk.Tk, user: dict) -> None:
    """Show dashboard as home screen inside the shell."""
    root.current_user = user
    shell = _ensure_shell(root)
    if not shell:
        return
    frame = DashboardFrame(shell.content_area, on_home=None)
    shell.set_content(frame, title="Dashboard", subtitle="Today at a glance")
    shell.activate_nav("dashboard")
    _set_refresh_button(shell, root, "dashboard")


def _show_settings_menu(root: tk.Tk, user: dict) -> None:
    """Show settings submenu (admin-only) within the shell."""
    if user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return

    def builder(container: tk.Misc):
        frame = ttk.Frame(container, padding=24)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="System Settings", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 20))

        buttons = [
            ("👤 User Management", lambda: show_user_mgmt(root)),
            ("📊 VAT Settings", lambda: show_vat_settings(root)),
            ("� Units of Measure", lambda: show_uom_settings(root)),
            ("�📧 Email Notifications", lambda: show_email_settings(root)),
            ("� System Info", lambda: show_system_info(root)),
            ("�🔑 Change Password", lambda: show_change_password(root, user)),
            ("💱 Currency Settings", lambda: show_currency_settings(root)),
        ]
        for idx, (label, cmd) in enumerate(buttons):
            r, c = divmod(idx, 2)
            ttk.Button(frame, text=label, width=28, command=cmd).grid(row=2 + r, column=c, sticky=tk.EW, padx=6, pady=6)
        return frame
    
    frame = _render(root, title="Settings", subtitle="Manage your system", builder=builder)
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("settings")
        shell.set_header_button("🏠 Home", lambda: show_home(root, user))


def show_system_info(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    from ui.system_info import SystemInfoFrame

    frame = _render(root, title="System Info", subtitle="Database and environment", builder=lambda parent: SystemInfoFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "system_info")
        _set_back_button(shell, root)


def show_currency_settings(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    from ui.settings import CurrencySettingsFrame

    frame = _render(root, title="Currency", subtitle="Display currency and rounding", builder=lambda parent: CurrencySettingsFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "currency_settings")
        _set_back_button(shell, root)
        try:
            frame.refresh()
        except Exception:
            pass


def show_inventory(root: tk.Tk) -> None:
    frame = _render(root, title="Inventory", subtitle="Items, stock, and pricing", builder=lambda parent: InventoryFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("inventory")
        _set_refresh_button(shell, root, "inventory")
        try:
            frame.refresh()
        except Exception:
            pass


def show_pos(root: tk.Tk) -> None:
    cart_state = getattr(root, "cart_state", {"items": [], "suspended": []})
    frame = _render(root, title="Point of Sale", subtitle="Sell, scan, and collect payments", builder=lambda parent: PosFrame(parent, cart_state=cart_state))
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("pos")
        _set_refresh_button(shell, root, "pos")
        try:
            frame.refresh_all()
            frame.ensure_populated(force=True)
        except Exception:
            pass


def show_cart(root: tk.Tk) -> None:
    """Show the dedicated cart review page."""
    cart_state = getattr(root, "cart_state", {"items": [], "suspended": []})
    frame = _render(root, title="Cart", subtitle="Review and checkout", builder=lambda parent: CartFrame(parent, cart_state=cart_state, on_back=lambda: show_pos(root)))
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("cart")


def show_user_mgmt(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    frame = _render(root, title="Users", subtitle="Manage accounts and roles", builder=lambda parent: UserManagementFrame(parent))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "user_mgmt")
        _set_back_button(shell, root)
        try:
            if hasattr(frame, "refresh"):
                frame.refresh()
        except Exception:
            pass


def show_vat_settings(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    frame = _render(root, title="VAT Settings", subtitle="Configure tax rates", builder=lambda parent: VatSettingsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "vat_settings")
        _set_back_button(shell, root)
        try:
            frame.refresh()
        except Exception:
            pass


def show_uom_settings(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    frame = _render(root, title="Units of Measure", subtitle="Configure measurement units", builder=lambda parent: UomSettingsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "uom_settings")
        _set_back_button(shell, root)
        try:
            frame.refresh()
        except Exception:
            pass


def show_reports(root: tk.Tk) -> None:
    frame = _render(root, title="Reports", subtitle="Performance and history", builder=lambda parent: ReportsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("reports")
        _set_refresh_button(shell, root, "reports")
        try:
            if hasattr(frame, "refresh"):
                frame.refresh()
        except Exception:
            pass


def show_order_history(root: tk.Tk) -> None:
    frame = _render(root, title="Order History", subtitle="View orders and receipts", builder=lambda parent: OrderHistoryFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("order_history")
        _set_refresh_button(shell, root, "order_history")
        try:
            if hasattr(frame, "refresh"):
                frame.refresh()
        except Exception:
            pass


def show_expenses(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    frame = _render(root, title="Expenses", subtitle="Track spending", builder=lambda parent: ExpensesFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("expenses")
        _set_refresh_button(shell, root, "expenses")
        try:
            frame.refresh()
        except Exception:
            pass


def show_backup(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    frame = _render(root, title="Backup", subtitle="Protect your data", builder=lambda parent: BackupFrame(parent, on_home=None))
    shell = _ensure_shell(root)
    if shell and frame:
        shell.activate_nav("backup")
        shell.set_header_button("🏠 Home", lambda: show_home(root, getattr(root, "current_user", {})))
        try:
            frame._refresh_list()
        except Exception:
            pass


def show_email_settings(root: tk.Tk) -> None:
    if not _require_admin(root):
        return
    frame = _render(root, title="Email Notifications", subtitle="Alerts and receipts", builder=lambda parent: EmailSettingsFrame(parent, on_home=lambda: show_home(root, getattr(root, "current_user", {}))))
    shell = _ensure_shell(root)
    if shell and frame:
        _activate_settings_subpage(shell, "email_settings")
        _set_back_button(shell, root)
        try:
            frame.refresh()
        except Exception:
            pass


def show_change_password(root: tk.Tk, user: dict) -> None:
    from ui.user_mgmt import ChangePasswordDialog
    ChangePasswordDialog(root, user['username'])
    # stay on home after closing dialog


def show_login(root: tk.Tk) -> None:
    from ui.login import LoginFrame
    for child in root.winfo_children():
        child.destroy()
    root.shell = None
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)
    login_frame = LoginFrame(root, on_success=lambda user: _launch_shell(root, user))
    login_frame.grid(row=0, column=0, sticky=tk.NSEW)


def _launch_shell(root: tk.Tk, user: dict) -> None:
    root.current_user = user
    _build_shell(root, user)
    show_home(root, user)


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

    # Command line support: recalculate per-unit prices (run after install or on demand)
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


    root = tk.Tk()
    root.geometry("1600x1000")
    root.minsize(1400, 800)
    root.resizable(True, True)
    try:
        root.state("zoomed")
    except Exception:
        pass
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)
    root.grid_propagate(False)
    style = ttk.Style(root)
    style.theme_use("clam")
    # Increase row height and font for Treeview to improve readability and make tables visually larger
    try:
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[("selected", "#E3F2FD")])  # Light blue for selected rows
        # Alternate row colors
        style.configure("Treeview", fieldbackground="#FFFFFF")
        # For buttons
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.map("TButton", background=[("active", "#BBDEFB")])
        # For labels
        style.configure("TLabel", font=("Segoe UI", 10))
        # For frames/cards
        style.configure("Card.TLabelframe", borderwidth=2, relief="raised", padding=10)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 12, "bold"))
    except Exception:
        pass
    root.title(APP_TITLE)

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

        # On Windows, force both small and large icons at the Win32 level
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                LR_LOADFROMFILE = 0x00000010
                IMAGE_ICON = 1
                WM_SETICON = 0x0080
                # Load small and large icons from the ICO file
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

    # Check if this is first-time setup (no database or no users)
    from modules.users import list_users
    is_first_time = not db_file.exists()
    
    # Always bootstrap database without creating default admin
    # Admin creation is handled through the UI setup process
    bootstrap_database(create_default_admin=False)

    # Lazily import UI modules now that the DB is ready
    from ui.pos import PosFrame as _PosFrame
    from ui.user_mgmt import UserManagementFrame as _UserManagementFrame
    from ui.inventory import InventoryFrame as _InventoryFrame
    from ui.login import LoginFrame as _LoginFrame
    from ui.vat_settings import VatSettingsFrame as _VatSettingsFrame
    from ui.uom_settings import UomSettingsFrame as _UomSettingsFrame
    from ui.reports import ReportsFrame as _ReportsFrame
    from ui.expenses import ExpensesFrame as _ExpensesFrame
    from ui.backup import BackupFrame as _BackupFrame
    from ui.dashboard import DashboardFrame as _DashboardFrame
    from ui.email_settings import EmailSettingsFrame as _EmailSettingsFrame
    from ui.shell import AppShell as _AppShell
    from ui.cart import CartFrame as _CartFrame
    from ui.order_history import OrderHistoryFrame as _OrderHistoryFrame
    from ui.admin_setup import AdminSetupFrame as _AdminSetupFrame

    # Export into module globals so other functions can reference them
    globals().update({
        'PosFrame': _PosFrame,
        'UserManagementFrame': _UserManagementFrame,
        'InventoryFrame': _InventoryFrame,
        'LoginFrame': _LoginFrame,
        'VatSettingsFrame': _VatSettingsFrame,
        'UomSettingsFrame': _UomSettingsFrame,
        'ReportsFrame': _ReportsFrame,
        'ExpensesFrame': _ExpensesFrame,
        'BackupFrame': _BackupFrame,
        'DashboardFrame': _DashboardFrame,
        'EmailSettingsFrame': _EmailSettingsFrame,
        'AppShell': _AppShell,
        'CartFrame': _CartFrame,
        'OrderHistoryFrame': _OrderHistoryFrame,
        'AdminSetupFrame': _AdminSetupFrame,
    })
    # Check if any users exist
    users = list_users()

    if not users:
        # No users - show first-time admin setup
        try:
            for child in root.winfo_children():
                child.destroy()
            root.rowconfigure(0, weight=1)
            root.rowconfigure(1, weight=0)
            setup_frame = AdminSetupFrame(root, on_success=after_admin_setup)
            setup_frame.grid(row=0, column=0, sticky=tk.NSEW)
        except Exception as e:
            logger.exception("Failed to initialize AdminSetupFrame: %s", e)
            messagebox.showerror("Initialization error", f"Failed to start admin setup: {e}")
    else:
        try:
            show_login(root)
        except Exception as e:
            logger.exception("Failed to show login frame: %s", e)
            messagebox.showerror("Initialization error", f"Failed to open login: {e}")
    root.mainloop()


if __name__ == "__main__":
    main()
