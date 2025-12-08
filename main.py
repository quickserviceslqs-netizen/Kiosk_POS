from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from database.init_db import initialize_database
from modules.users import ensure_admin_user
from modules import backup
from ui.pos import PosFrame
from ui.user_mgmt import UserManagementFrame
from ui.inventory import InventoryFrame
from ui.login import LoginFrame
from ui.vat_settings import VatSettingsFrame
from ui.reports import ReportsFrame
from ui.expenses import ExpensesFrame
from ui.backup import BackupFrame
from ui.dashboard import DashboardFrame
from ui.email_settings import EmailSettingsFrame

APP_TITLE = "Kiosk POS v1.000"
APP_VERSION = "1.000"


def bootstrap_database() -> Path:
    """Create the database file and schema if missing, returning the resolved path."""
    db_path = initialize_database()
    if not db_path.exists():
        raise RuntimeError("Database creation failed; file not found after initialization.")
    ensure_admin_user()  # seed a default admin if none exists
    
    # Check and run auto backup if needed
    try:
        backup.check_and_run_auto_backup()
    except Exception:
        pass  # Silent fail to not interrupt startup
    
    return db_path


def show_home(root: tk.Tk, user: dict) -> None:
    """Show dashboard as home screen."""
    root.current_user = user
    for child in root.winfo_children():
        child.destroy()

    # Top navigation buttons
    nav = ttk.Frame(root)
    nav.pack(fill=tk.X, padx=12, pady=(8, 8))
    
    ttk.Label(nav, text=f"Logged in as: {user['username']} ({user['role']})", foreground="gray").pack(side=tk.LEFT)
    
    btn_frame = ttk.Frame(nav)
    btn_frame.pack(side=tk.RIGHT)
    
    ttk.Button(btn_frame, text="POS", width=12, command=lambda: show_pos(root)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Inventory", width=12, command=lambda: show_inventory(root)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Reports", width=12, command=lambda: show_reports(root)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Expenses", width=12, command=lambda: show_expenses(root)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Backup", width=12, command=lambda: show_backup(root)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="⚙ Settings", width=12, command=lambda: _show_settings_menu(root, user)).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Logout", width=10, command=lambda: show_login(root)).pack(side=tk.LEFT, padx=2)
    
    # Show dashboard below navigation
    frame = DashboardFrame(root, on_home=None)
    frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


def _show_settings_menu(root: tk.Tk, user: dict) -> None:
    """Show settings submenu (admin-only)."""
    if user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return
    
    for child in root.winfo_children():
        child.destroy()
    
    ttk.Label(root, text="⚙ Settings", font=("Segoe UI", 16, "bold")).pack(pady=(16, 4))
    ttk.Label(root, text=f"Logged in as: {user['username']} ({user['role']})", foreground="gray").pack(pady=(0, 16))
    
    btns = ttk.Frame(root)
    btns.pack(pady=12)
    
    ttk.Button(btns, text="👤 User Management", width=24, command=lambda: show_user_mgmt(root)).grid(row=0, column=0, padx=8, pady=6)
    ttk.Button(btns, text="📊 VAT Settings", width=24, command=lambda: show_vat_settings(root)).grid(row=0, column=1, padx=8, pady=6)
    ttk.Button(btns, text="📧 Email Notifications", width=24, command=lambda: show_email_settings(root)).grid(row=1, column=0, padx=8, pady=6)
    ttk.Button(btns, text="🔑 Change Password", width=24, command=lambda: show_change_password(root, user)).grid(row=1, column=1, padx=8, pady=6)
    from ui.settings import CurrencySettingsFrame
    ttk.Button(btns, text="💱 Currency Settings", width=24, command=lambda: show_currency_settings(root)).grid(row=2, column=0, padx=8, pady=6)

    # Add Home button to main settings page (not sub-settings)
    ttk.Button(root, text="← Home", command=lambda: show_home(root, user)).pack(pady=(8, 0))


def show_currency_settings(root: tk.Tk) -> None:
    for child in root.winfo_children():
        child.destroy()
    nav = ttk.Frame(root)
    nav.pack(fill=tk.X, pady=(4, 2))
    ttk.Button(nav, text="← Settings", command=lambda: _show_settings_menu(root, getattr(root, "current_user", {}))).pack(side=tk.LEFT, padx=6)
    from ui.settings import CurrencySettingsFrame
    frame = CurrencySettingsFrame(root)
    frame.pack(fill=tk.BOTH, expand=True)


def show_inventory(root: tk.Tk) -> None:
    for child in root.winfo_children():
        child.destroy()
    nav = ttk.Frame(root)
    nav.pack(fill=tk.X, pady=(4, 2))
    ttk.Button(nav, text="← Home", command=lambda: show_home(root, getattr(root, "current_user", {}))).pack(side=tk.LEFT, padx=6)

    frame = InventoryFrame(root)
    frame.pack(fill=tk.BOTH, expand=True)


def show_pos(root: tk.Tk) -> None:
    for child in root.winfo_children():
        child.destroy()
    nav = ttk.Frame(root)
    nav.pack(fill=tk.X, pady=(4, 2))
    ttk.Button(nav, text="← Home", command=lambda: show_home(root, getattr(root, "current_user", {}))).pack(side=tk.LEFT, padx=6)

    frame = PosFrame(root)
    frame.pack(fill=tk.BOTH, expand=True)


def show_user_mgmt(root: tk.Tk) -> None:
    user = getattr(root, "current_user", None)
    if not user or user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return
    for child in root.winfo_children():
        child.destroy()
    nav = ttk.Frame(root)
    nav.pack(fill=tk.X, pady=(4, 2))
    ttk.Button(nav, text="← Home", command=lambda: show_home(root, user)).pack(side=tk.LEFT, padx=6)

    frame = UserManagementFrame(root)
    frame.pack(fill=tk.BOTH, expand=True)


def show_vat_settings(root: tk.Tk) -> None:
    user = getattr(root, "current_user", None)
    if not user or user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return
    for child in root.winfo_children():
        child.destroy()
    
    frame = VatSettingsFrame(root, on_home=lambda: show_home(root, user))
    frame.pack(fill=tk.BOTH, expand=True)


def show_reports(root: tk.Tk) -> None:
    for child in root.winfo_children():
        child.destroy()
    
    user = getattr(root, "current_user", {})
    frame = ReportsFrame(root, on_home=lambda: show_home(root, user))
    frame.pack(fill=tk.BOTH, expand=True)


def show_expenses(root: tk.Tk) -> None:
    user = getattr(root, "current_user", None)
    if not user or user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return
    for child in root.winfo_children():
        child.destroy()
    
    frame = ExpensesFrame(root, on_home=lambda: show_home(root, user))
    frame.pack(fill=tk.BOTH, expand=True)


def show_backup(root: tk.Tk) -> None:
    user = getattr(root, "current_user", None)
    if not user or user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return
    for child in root.winfo_children():
        child.destroy()
    
    frame = BackupFrame(root, on_home=lambda: show_home(root, user))
    frame.pack(fill=tk.BOTH, expand=True)


def show_email_settings(root: tk.Tk) -> None:
    user = getattr(root, "current_user", None)
    if not user or user.get("role") != "admin":
        messagebox.showerror("Access denied", "Admin role required")
        return
    for child in root.winfo_children():
        child.destroy()
    
    frame = EmailSettingsFrame(root, on_home=lambda: show_home(root, user))
    frame.pack(fill=tk.BOTH, expand=True)


def show_change_password(root: tk.Tk, user: dict) -> None:
    from ui.user_mgmt import ChangePasswordDialog
    ChangePasswordDialog(root, user['username'])
    # stay on home after closing dialog


def show_login(root: tk.Tk) -> None:
    for child in root.winfo_children():
        child.destroy()
    login_frame = LoginFrame(root, on_success=lambda user: show_home(root, user))
    login_frame.pack(fill=tk.BOTH, expand=True)


def main() -> None:

    from pathlib import Path
    db_file = Path("database/pos.db")


    root = tk.Tk()
    root.geometry("900x640")
    root.minsize(720, 520)
    ttk.Style(root).theme_use("clam")
    root.title(APP_TITLE)

    # Set window icon
    import os, sys
    if hasattr(sys, "_MEIPASS"):
        icon_path = os.path.join(sys._MEIPASS, "assets", "app_icon.ico")
    else:
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    def after_admin_setup():
        show_login(root)

    if not db_file.exists():
        bootstrap_database()  # First-time setup: create DB and admin
        from ui.admin_setup import AdminSetupFrame
        for child in root.winfo_children():
            child.destroy()
        setup_frame = AdminSetupFrame(root, on_success=after_admin_setup)
        setup_frame.pack(fill=tk.BOTH, expand=True)
    else:
        show_login(root)
    root.mainloop()


if __name__ == "__main__":
    main()
