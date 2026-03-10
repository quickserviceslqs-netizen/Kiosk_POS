"""Configuration management UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import json
from typing import Dict, Any, Optional
import logging

from utils.app_config import (
    load_config, save_config, update_config, reset_config_to_defaults,
    AppConfig, get_environment_info, ENVIRONMENT, IS_PRODUCTION
)
from utils.validation import ValidationError

logger = logging.getLogger(__name__)


class ConfigManagementDialog:
    """Dialog for managing application configuration."""

    def __init__(self, parent: tk.Misc):
        self.parent = parent
        self.config: Optional[AppConfig] = None
        self.app_dir: Optional[Path] = None
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the configuration management dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Configuration Management")
        self.dialog.geometry("900x700")
        self.dialog.minsize(800, 600)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Get app directory and load config
        import sys
        if getattr(sys, 'frozen', False):
            self.app_dir = Path(sys.executable).parent
        else:
            self.app_dir = Path(__file__).parent.parent

        try:
            self.config = load_config(self.app_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}", parent=self.dialog)
            self.dialog.destroy()
            return

        self._build_ui()
        self._load_current_config()

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="Application Configuration",
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)

        # Environment info
        env_info = get_environment_info()
        env_text = f"Environment: {env_info['environment'].title()}"
        ttk.Label(title_frame, text=env_text, foreground=get_status_color('info')).pack(side=tk.RIGHT)

        # Notebook for different config sections
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create tabs
        self._create_general_tab()
        self._create_security_tab()
        self._create_ui_tab()
        self._create_business_tab()
        self._create_performance_tab()
        self._create_backup_tab()
        self._create_advanced_tab()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Save Changes", command=self._save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Reset to Defaults", command=self._reset_to_defaults).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Export Config", command=self._export_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Import Config", command=self._import_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT)

    def _create_general_tab(self) -> None:
        """Create the general settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="General")

        # Database settings
        db_group = ttk.LabelFrame(frame, text="Database", padding=5)
        db_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(db_group, text="Connection Pool Size:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.db_pool_size = ttk.Spinbox(db_group, from_=1, to=20, width=10)
        self.db_pool_size.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(db_group, text="Connection Timeout (sec):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.db_timeout = ttk.Spinbox(db_group, from_=5, to=300, width=10)
        self.db_timeout.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.db_wal_mode = tk.BooleanVar()
        ttk.Checkbutton(db_group, text="Enable WAL Mode", variable=self.db_wal_mode).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Logging settings
        log_group = ttk.LabelFrame(frame, text="Logging", padding=5)
        log_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(log_group, text="Log Level:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.log_level = ttk.Combobox(log_group, values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], state="readonly", width=12)
        self.log_level.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(log_group, text="Max Log Size (MB):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.log_max_size = ttk.Spinbox(log_group, from_=1, to=100, width=10)
        self.log_max_size.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(log_group, text="Backup Count:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.log_backup_count = ttk.Spinbox(log_group, from_=1, to=20, width=10)
        self.log_backup_count.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.audit_logging = tk.BooleanVar()
        ttk.Checkbutton(log_group, text="Enable Audit Logging", variable=self.audit_logging).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)

    def _create_security_tab(self) -> None:
        """Create the security settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Security")

        # Session settings
        session_group = ttk.LabelFrame(frame, text="Session Management", padding=5)
        session_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(session_group, text="Session Timeout (minutes):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.session_timeout = ttk.Spinbox(session_group, from_=5, to=480, width=10)
        self.session_timeout.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Login settings
        login_group = ttk.LabelFrame(frame, text="Login Security", padding=5)
        login_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(login_group, text="Max Login Attempts:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.max_login_attempts = ttk.Spinbox(login_group, from_=1, to=10, width=10)
        self.max_login_attempts.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(login_group, text="Minimum Password Length:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.password_min_length = ttk.Spinbox(login_group, from_=6, to=128, width=10)
        self.password_min_length.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.account_lockout = tk.BooleanVar()
        ttk.Checkbutton(login_group, text="Enable Account Lockout", variable=self.account_lockout).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(login_group, text="Lockout Duration (minutes):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.lockout_duration = ttk.Spinbox(login_group, from_=1, to=1440, width=10)
        self.lockout_duration.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)

    def _create_ui_tab(self) -> None:
        """Create the UI settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="User Interface")

        # Appearance
        appearance_group = ttk.LabelFrame(frame, text="Appearance", padding=5)
        appearance_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(appearance_group, text="Theme:").grid(row=0, column=0, sticky=tk.W, pady=2)
        from utils.theme import get_available_themes
        theme_options = list(get_available_themes().keys())
        self.theme = ttk.Combobox(appearance_group, values=theme_options, state="readonly", width=12)
        self.theme.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(appearance_group, text="Language:").grid(row=1, column=0, sticky=tk.W, pady=2)
        from utils.i18n import get_available_languages
        languages = get_available_languages()
        self.language = ttk.Combobox(appearance_group, values=list(languages.keys()), state="readonly", width=12)
        self.language.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Create a label to show the selected language name
        self.language_label = ttk.Label(appearance_group, text="", font=("Segoe UI", 8))
        self.language_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Bind language selection to update the label
        def on_language_select(event):
            selected = self.language.get()
            if selected in languages:
                self.language_label.config(text=languages[selected])
        
        self.language.bind("<<ComboboxSelected>>", on_language_select)

        # Display settings
        display_group = ttk.LabelFrame(frame, text="Display Settings", padding=5)
        display_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(display_group, text="Items Per Page:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.items_per_page = ttk.Spinbox(display_group, from_=10, to=1000, width=10)
        self.items_per_page.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.virtual_scrolling = tk.BooleanVar()
        ttk.Checkbutton(display_group, text="Enable Virtual Scrolling", variable=self.virtual_scrolling).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Currency and formatting
        format_group = ttk.LabelFrame(frame, text="Formatting", padding=5)
        format_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(format_group, text="Currency Symbol:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.currency_symbol = ttk.Entry(format_group, width=5)
        self.currency_symbol.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(format_group, text="Date Format:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.date_format = ttk.Entry(format_group, width=15)
        self.date_format.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        ttk.Label(format_group, text="(e.g., %Y-%m-%d)", font=("Segoe UI", 8)).grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=2)

    def _create_business_tab(self) -> None:
        """Create the business settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Business")

        # Business info
        info_group = ttk.LabelFrame(frame, text="Business Information", padding=5)
        info_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_group, text="Business Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.business_name = ttk.Entry(info_group, width=30)
        self.business_name.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=2)

        ttk.Label(info_group, text="Address:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.business_address = ttk.Entry(info_group, width=30)
        self.business_address.grid(row=1, column=1, sticky=tk.EW, padx=(10, 0), pady=2)

        ttk.Label(info_group, text="Phone:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.business_phone = ttk.Entry(info_group, width=30)
        self.business_phone.grid(row=2, column=1, sticky=tk.EW, padx=(10, 0), pady=2)

        ttk.Label(info_group, text="Email:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.business_email = ttk.Entry(info_group, width=30)
        self.business_email.grid(row=3, column=1, sticky=tk.EW, padx=(10, 0), pady=2)

        # Tax settings
        tax_group = ttk.LabelFrame(frame, text="Tax Settings", padding=5)
        tax_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(tax_group, text="Default Tax Rate (%):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.tax_rate_default = ttk.Spinbox(tax_group, from_=0.0, to=100.0, increment=0.1, width=10)
        self.tax_rate_default.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Loyalty program
        loyalty_group = ttk.LabelFrame(frame, text="Features", padding=5)
        loyalty_group.pack(fill=tk.X, pady=(0, 10))

        self.loyalty_program = tk.BooleanVar()
        ttk.Checkbutton(loyalty_group, text="Enable Loyalty Program", variable=self.loyalty_program).grid(row=0, column=0, sticky=tk.W, pady=2)

    def _create_performance_tab(self) -> None:
        """Create the performance settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Performance")

        # Cache settings
        cache_group = ttk.LabelFrame(frame, text="Caching", padding=5)
        cache_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(cache_group, text="Image Cache Size (MB):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.image_cache_size = ttk.Spinbox(cache_group, from_=10, to=500, width=10)
        self.image_cache_size.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Concurrency settings
        concurrency_group = ttk.LabelFrame(frame, text="Concurrency", padding=5)
        concurrency_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(concurrency_group, text="Max Concurrent Operations:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.max_concurrent_ops = ttk.Spinbox(concurrency_group, from_=1, to=10, width=10)
        self.max_concurrent_ops.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(concurrency_group, text="Database Query Timeout (sec):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.db_query_timeout = ttk.Spinbox(concurrency_group, from_=5, to=300, width=10)
        self.db_query_timeout.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

    def _create_backup_tab(self) -> None:
        """Create the backup settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Backup")

        # Auto-backup settings
        auto_group = ttk.LabelFrame(frame, text="Automatic Backups", padding=5)
        auto_group.pack(fill=tk.X, pady=(0, 10))

        self.auto_backup_enabled = tk.BooleanVar()
        ttk.Checkbutton(auto_group, text="Enable Automatic Backups", variable=self.auto_backup_enabled).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(auto_group, text="Backup Interval (hours):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.backup_interval = ttk.Spinbox(auto_group, from_=1, to=168, width=10)
        self.backup_interval.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(auto_group, text="Maximum Backups to Keep:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.max_backups_keep = ttk.Spinbox(auto_group, from_=1, to=100, width=10)
        self.max_backups_keep.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.backup_compression = tk.BooleanVar()
        ttk.Checkbutton(auto_group, text="Enable Backup Compression", variable=self.backup_compression).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)

    def _create_advanced_tab(self) -> None:
        """Create the advanced settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="Advanced")

        # Development settings
        dev_group = ttk.LabelFrame(frame, text="Development", padding=5)
        dev_group.pack(fill=tk.X, pady=(0, 10))

        self.debug_mode = tk.BooleanVar()
        ttk.Checkbutton(dev_group, text="Debug Mode", variable=self.debug_mode).grid(row=0, column=0, sticky=tk.W, pady=2)

        self.demo_data = tk.BooleanVar()
        ttk.Checkbutton(dev_group, text="Enable Demo Data", variable=self.demo_data).grid(row=1, column=0, sticky=tk.W, pady=2)

        self.insecure_connections = tk.BooleanVar()
        ttk.Checkbutton(dev_group, text="Allow Insecure Connections", variable=self.insecure_connections).grid(row=2, column=0, sticky=tk.W, pady=2)

        # Raw config viewer/editor
        raw_group = ttk.LabelFrame(frame, text="Raw Configuration", padding=5)
        raw_group.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        ttk.Label(raw_group, text="Raw JSON Configuration:").pack(anchor=tk.W, pady=(0, 5))
        self.raw_config_text = scrolledtext.ScrolledText(raw_group, height=15, font=("Consolas", 9))
        self.raw_config_text.pack(fill=tk.BOTH, expand=True)

        ttk.Button(raw_group, text="Load Raw Config", command=self._load_raw_config).pack(side=tk.LEFT, pady=(5, 0))
        ttk.Button(raw_group, text="Save Raw Config", command=self._save_raw_config).pack(side=tk.LEFT, padx=(5, 0), pady=(5, 0))

    def _load_current_config(self) -> None:
        """Load current configuration values into the UI."""
        if not self.config:
            return

        # General tab
        self.db_pool_size.set(self.config.db_connection_pool_size)
        self.db_timeout.set(self.config.db_connection_timeout)
        self.db_wal_mode.set(self.config.db_enable_wal_mode)
        self.log_level.set(self.config.log_level)
        self.log_max_size.set(self.config.log_max_size_mb)
        self.log_backup_count.set(self.config.log_backup_count)
        self.audit_logging.set(self.config.enable_audit_logging)

        # Security tab
        self.session_timeout.set(self.config.session_timeout_minutes)
        self.max_login_attempts.set(self.config.max_login_attempts)
        self.password_min_length.set(self.config.password_min_length)
        self.account_lockout.set(self.config.enable_account_lockout)
        self.lockout_duration.set(self.config.lockout_duration_minutes)

        # UI tab
        self.theme.set(self.config.theme)
        self.language.set(self.config.language)
        # Update language label
        from utils.i18n import get_available_languages
        languages = get_available_languages()
        if self.config.language in languages:
            self.language_label.config(text=languages[self.config.language])
        self.items_per_page.set(self.config.items_per_page)
        self.virtual_scrolling.set(self.config.enable_virtual_scrolling)
        self.currency_symbol.delete(0, tk.END)
        self.currency_symbol.insert(0, self.config.currency_symbol)
        self.date_format.delete(0, tk.END)
        self.date_format.insert(0, self.config.date_format)

        # Business tab
        self.business_name.delete(0, tk.END)
        self.business_name.insert(0, self.config.business_name)
        self.business_address.delete(0, tk.END)
        self.business_address.insert(0, self.config.business_address)
        self.business_phone.delete(0, tk.END)
        self.business_phone.insert(0, self.config.business_phone)
        self.business_email.delete(0, tk.END)
        self.business_email.insert(0, self.config.business_email)
        self.tax_rate_default.set(self.config.tax_rate_default)
        self.loyalty_program.set(self.config.enable_loyalty_program)

        # Performance tab
        self.image_cache_size.set(self.config.image_cache_size_mb)
        self.max_concurrent_ops.set(self.config.max_concurrent_operations)
        self.db_query_timeout.set(self.config.database_query_timeout)
        # Backup tab
        self.auto_backup_enabled.set(self.config.auto_backup_enabled)
        self.backup_interval.set(self.config.backup_interval_hours)
        self.max_backups_keep.set(self.config.max_backups_to_keep)
        self.backup_compression.set(self.config.backup_compression)

        # Advanced tab
        self.debug_mode.set(self.config.debug_mode)
        self.demo_data.set(self.config.enable_demo_data)
        self.insecure_connections.set(self.config.allow_insecure_connections)

        # Load raw config
        self._load_raw_config()

    def _load_raw_config(self) -> None:
        """Load raw JSON configuration into the text area."""
        if self.config:
            import json
            config_dict = {
                k: v for k, v in self.config.__dict__.items()
                if not k.startswith('_')
            }
            self.raw_config_text.delete(1.0, tk.END)
            self.raw_config_text.insert(1.0, json.dumps(config_dict, indent=2))

    def _save_raw_config(self) -> None:
        """Save raw JSON configuration from the text area."""
        try:
            raw_text = self.raw_config_text.get(1.0, tk.END).strip()
            config_dict = json.loads(raw_text)

            # Create new config from dict
            new_config = AppConfig()
            for key, value in config_dict.items():
                if hasattr(new_config, key):
                    setattr(new_config, key, value)

            # Validate and save
            new_config.validate()
            save_config(new_config, self.app_dir)
            self.config = new_config

            messagebox.showinfo("Success", "Raw configuration saved successfully!", parent=self.dialog)

        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON: {e}", parent=self.dialog)
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self.dialog)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}", parent=self.dialog)

    def _save_config(self) -> None:
        """Save configuration from UI fields."""
        try:
            updates = {}

            # General tab
            updates["db_connection_pool_size"] = int(self.db_pool_size.get())
            updates["db_connection_timeout"] = int(self.db_timeout.get())
            updates["db_enable_wal_mode"] = self.db_wal_mode.get()
            updates["log_level"] = self.log_level.get()
            updates["log_max_size_mb"] = int(self.log_max_size.get())
            updates["log_backup_count"] = int(self.log_backup_count.get())
            updates["enable_audit_logging"] = self.audit_logging.get()

            # Security tab
            updates["session_timeout_minutes"] = int(self.session_timeout.get())
            updates["max_login_attempts"] = int(self.max_login_attempts.get())
            updates["password_min_length"] = int(self.password_min_length.get())
            updates["enable_account_lockout"] = self.account_lockout.get()
            updates["lockout_duration_minutes"] = int(self.lockout_duration.get())

            # UI tab
            updates["theme"] = self.theme.get()
            updates["language"] = self.language.get()
            updates["items_per_page"] = int(self.items_per_page.get())
            updates["enable_virtual_scrolling"] = self.virtual_scrolling.get()
            updates["currency_symbol"] = self.currency_symbol.get().strip()
            updates["date_format"] = self.date_format.get().strip()

            # Business tab
            updates["business_name"] = self.business_name.get().strip()
            updates["business_address"] = self.business_address.get().strip()
            updates["business_phone"] = self.business_phone.get().strip()
            updates["business_email"] = self.business_email.get().strip()
            updates["tax_rate_default"] = float(self.tax_rate_default.get())
            updates["enable_loyalty_program"] = self.loyalty_program.get()

            # Performance tab
            updates["image_cache_size_mb"] = int(self.image_cache_size.get())
            updates["max_concurrent_operations"] = int(self.max_concurrent_ops.get())
            updates["database_query_timeout"] = int(self.db_query_timeout.get())

            # Backup tab
            updates["auto_backup_enabled"] = self.auto_backup_enabled.get()
            updates["backup_interval_hours"] = int(self.backup_interval.get())
            updates["max_backups_to_keep"] = int(self.max_backups_keep.get())
            updates["backup_compression"] = self.backup_compression.get()

            # Advanced tab
            updates["debug_mode"] = self.debug_mode.get()
            updates["enable_demo_data"] = self.demo_data.get()
            updates["allow_insecure_connections"] = self.insecure_connections.get()

            # Update and save configuration
            self.config = update_config(updates, self.app_dir)
            messagebox.showinfo("Success", "Configuration saved successfully!\n\nSome changes may require application restart.", parent=self.dialog)

        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self.dialog)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}", parent=self.dialog)

    def _reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all configuration to defaults?\n\nThis cannot be undone.", parent=self.dialog):
            try:
                from utils.app_config import reset_config_to_defaults
                self.config = reset_config_to_defaults(self.app_dir)
                self._load_current_config()
                messagebox.showinfo("Success", "Configuration reset to defaults!", parent=self.dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset configuration: {e}", parent=self.dialog)

    def _export_config(self) -> None:
        """Export configuration to file."""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Configuration",
                parent=self.dialog
            )
            if filename:
                import json
                config_dict = {
                    k: v for k, v in self.config.__dict__.items()
                    if not k.startswith('_')
                }
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2)
                messagebox.showinfo("Success", f"Configuration exported to {filename}", parent=self.dialog)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export configuration: {e}", parent=self.dialog)

    def _import_config(self) -> None:
        """Import configuration from file."""
        try:
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Configuration",
                parent=self.dialog
            )
            if filename:
                import json
                with open(filename, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)

                # Validate imported config
                new_config = AppConfig()
                for key, value in config_dict.items():
                    if hasattr(new_config, key):
                        setattr(new_config, key, value)

                new_config.validate()
                save_config(new_config, self.app_dir)
                self.config = new_config
                self._load_current_config()

                messagebox.showinfo("Success", f"Configuration imported from {filename}\n\nSome changes may require application restart.", parent=self.dialog)
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self.dialog)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import configuration: {e}", parent=self.dialog)