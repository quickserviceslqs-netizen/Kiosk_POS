"""Email notification settings UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import notifications


class EmailSettingsFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.config = notifications.get_email_config()
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.grid_propagate(True)  # Allow frame to expand

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="📧 Email Notifications", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="🏠 Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)

        # Scrollable content area
        canvas = tk.Canvas(self, highlightthickness=0, bg="white")
        canvas.grid(row=1, column=0, sticky=tk.NSEW)
        
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.grid(row=1, column=1, sticky=tk.NS)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=content, anchor=tk.NW)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_canvas_configure(event):
            # Don't stretch - let content size naturally
            pass
        
        content.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        content.columnconfigure(0, weight=0)
        content.columnconfigure(1, weight=0)
        content.rowconfigure(4, weight=0)
        
        # Enable/Disable
        enable_frame = ttk.Frame(content)
        enable_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=8, padx=8)
        ttk.Checkbutton(
            enable_frame,
            text="Enable email notifications",
            variable=(enabled_var := tk.BooleanVar(value=self.config["enabled"])),
            command=lambda: setattr(self.config, "enabled", enabled_var.get())
        ).pack(side=tk.LEFT)
        self.enabled_var = enabled_var

        # SMTP Settings
        smtp_frame = ttk.LabelFrame(content, text="SMTP Server Settings", padding=12)
        smtp_frame.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=8, padx=8)
        smtp_frame.columnconfigure(1, weight=1)
        
        ttk.Label(smtp_frame, text="SMTP Server:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.smtp_server_var = tk.StringVar(value=self.config["smtp_server"])
        ttk.Entry(smtp_frame, textvariable=self.smtp_server_var, width=35).grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        
        ttk.Label(smtp_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.smtp_port_var = tk.StringVar(value=str(self.config["smtp_port"]))
        ttk.Entry(smtp_frame, textvariable=self.smtp_port_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=4, padx=(8, 0))
        
        ttk.Label(smtp_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.smtp_username_var = tk.StringVar(value=self.config["smtp_username"])
        ttk.Entry(smtp_frame, textvariable=self.smtp_username_var, width=35).grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        
        ttk.Label(smtp_frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.smtp_password_var = tk.StringVar(value=self.config["smtp_password"])
        ttk.Entry(smtp_frame, textvariable=self.smtp_password_var, width=35, show="*").grid(row=3, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        
        # Email Addresses
        email_frame = ttk.LabelFrame(content, text="Email Addresses", padding=12)
        email_frame.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW, pady=8, padx=8)
        email_frame.columnconfigure(1, weight=1)
        
        ttk.Label(email_frame, text="From Email:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.from_email_var = tk.StringVar(value=self.config["from_email"])
        ttk.Entry(email_frame, textvariable=self.from_email_var, width=35).grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        
        ttk.Label(email_frame, text="To Emails:\n(comma-separated)", font=("Segoe UI", 9), foreground="#333").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.to_emails_var = tk.StringVar(value=", ".join(self.config["to_emails"]))
        ttk.Entry(email_frame, textvariable=self.to_emails_var, width=35).grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(8, 0))
        
        email_frame.columnconfigure(1, weight=1)
        
        # Notification Preferences
        prefs_frame = ttk.LabelFrame(content, text="Notification Preferences", padding=12)
        prefs_frame.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, pady=8, padx=8)
        prefs_frame.columnconfigure(0, weight=1)
        
        self.daily_report_var = tk.BooleanVar(value=self.config["daily_report_enabled"])
        ttk.Checkbutton(
            prefs_frame,
            text="Send daily sales report",
            variable=self.daily_report_var
        ).grid(row=0, column=0, sticky=tk.W, pady=4)
        
        self.low_stock_var = tk.BooleanVar(value=self.config["low_stock_alerts_enabled"])
        ttk.Checkbutton(
            prefs_frame,
            text="Send low stock alerts for items with notifications",
            variable=self.low_stock_var
        ).grid(row=1, column=0, sticky=tk.W, pady=4)
        
        ttk.Label(prefs_frame, text="Each item has its own low stock threshold set during creation.", foreground="gray", font=("Segoe UI", 8)).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        ttk.Label(prefs_frame, text="Emails only send when items have alerts to report.", foreground="orange", font=("Segoe UI", 8)).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        
        # Store threshold var for backward compatibility (not displayed)
        self.threshold_var = tk.IntVar(value=self.config["low_stock_threshold"])
        
        # Buttons - with wrapping for better visibility
        btn_frame = ttk.Frame(content)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=16, sticky=tk.EW, padx=8)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        
        self.save_btn = ttk.Button(btn_frame, text="💾 Save", command=self._save_settings)
        self.save_btn.grid(row=0, column=0, padx=4, pady=4, sticky=tk.EW)
        
        self.test_btn = ttk.Button(btn_frame, text="📧 Test", command=self._test_email)
        self.test_btn.grid(row=0, column=1, padx=4, pady=4, sticky=tk.EW)
        
        self.report_btn = ttk.Button(btn_frame, text="📊 Report", command=self._send_daily_report)
        self.report_btn.grid(row=1, column=0, padx=4, pady=4, sticky=tk.EW)
        
        self.alert_btn = ttk.Button(btn_frame, text="⚠ Alert", command=self._send_stock_alert)
        self.alert_btn.grid(row=1, column=1, padx=4, pady=4, sticky=tk.EW)
        
        # Bind validation to field changes
        for var in [self.smtp_server_var, self.smtp_port_var, self.smtp_username_var, 
                    self.smtp_password_var, self.from_email_var, self.to_emails_var]:
            var.trace_add("write", lambda *args: self._validate_fields())
        
        # Initial validation
        self._validate_fields()

    def refresh(self) -> None:
        """Reload email settings from database."""
        self.config = notifications.get_email_config()
        # Update all form fields with fresh data
        self.enabled_var.set(self.config["enabled"])
        self.smtp_server_var.set(self.config["smtp_server"])
        self.smtp_port_var.set(str(self.config["smtp_port"]))
        self.smtp_username_var.set(self.config["smtp_username"])
        self.smtp_password_var.set(self.config["smtp_password"])
        self.from_email_var.set(self.config["from_email"])
        self.to_emails_var.set(", ".join(self.config["to_emails"]))
        self.daily_report_var.set(self.config["daily_report_enabled"])
        self.low_stock_var.set(self.config["low_stock_alerts_enabled"])
        self.threshold_var.set(self.config["low_stock_threshold"])
        self._validate_fields()

    def _validate_fields(self) -> None:
        """Validate form fields and enable/disable buttons accordingly."""
        smtp_server = self.smtp_server_var.get().strip()
        smtp_port = self.smtp_port_var.get().strip()
        smtp_username = self.smtp_username_var.get().strip()
        smtp_password = self.smtp_password_var.get().strip()
        from_email = self.from_email_var.get().strip()
        to_emails = self.to_emails_var.get().strip()
        
        # Validate port
        port_valid = smtp_port.isdigit() and 1 <= int(smtp_port) <= 65535
        
        # Validate email formats
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        from_email_valid = bool(re.match(email_pattern, from_email)) if from_email else False
        
        to_emails_list = [email.strip() for email in to_emails.split(",") if email.strip()]
        to_emails_valid = all(re.match(email_pattern, email) for email in to_emails_list) and len(to_emails_list) > 0
        
        # Check if all required fields are filled and valid
        all_filled = all([smtp_server, smtp_port, smtp_username, smtp_password, from_email, to_emails]) and port_valid and from_email_valid and to_emails_valid
        
        # Enable/Disable action buttons based on field validation
        state = tk.NORMAL if all_filled else tk.DISABLED
        self.save_btn.config(state=state)
        self.test_btn.config(state=state)
        self.report_btn.config(state=state)
        self.alert_btn.config(state=state)

    def _save_settings(self) -> None:
        """Save email settings."""
        self.config["enabled"] = self.enabled_var.get()
        self.config["smtp_server"] = self.smtp_server_var.get()
        port_str = self.smtp_port_var.get().strip()
        self.config["smtp_port"] = int(port_str) if port_str.isdigit() else 0
        self.config["smtp_username"] = self.smtp_username_var.get()
        self.config["smtp_password"] = self.smtp_password_var.get()
        self.config["from_email"] = self.from_email_var.get()
        self.config["to_emails"] = [email.strip() for email in self.to_emails_var.get().split(",") if email.strip()]
        self.config["daily_report_enabled"] = self.daily_report_var.get()
        self.config["low_stock_alerts_enabled"] = self.low_stock_var.get()
        self.config["low_stock_threshold"] = self.threshold_var.get()
        
        notifications.save_email_config(self.config)
        messagebox.showinfo("Success", "Email settings saved successfully!")

    def _save_settings_silent(self) -> None:
        """Save email settings without showing confirmation."""
        self.config["enabled"] = self.enabled_var.get()
        self.config["smtp_server"] = self.smtp_server_var.get()
        port_str = self.smtp_port_var.get().strip()
        self.config["smtp_port"] = int(port_str) if port_str.isdigit() else 0
        self.config["smtp_username"] = self.smtp_username_var.get()
        self.config["smtp_password"] = self.smtp_password_var.get()
        self.config["from_email"] = self.from_email_var.get()
        self.config["to_emails"] = [email.strip() for email in self.to_emails_var.get().split(",") if email.strip()]
        self.config["daily_report_enabled"] = self.daily_report_var.get()
        self.config["low_stock_alerts_enabled"] = self.low_stock_var.get()
        self.config["low_stock_threshold"] = self.threshold_var.get()
        
        notifications.save_email_config(self.config)

    def _test_email(self) -> None:
        """Send a test email."""
        # Save settings silently first
        self._save_settings_silent()
        
        # Send test
        success, message = notifications.test_email_configuration(self.config)
        
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)

    def _send_daily_report(self) -> None:
        """Send daily report now."""
        self._save_settings_silent()
        
        if notifications.send_daily_report():
            messagebox.showinfo("Success", "Daily report sent successfully!")
        else:
            messagebox.showerror("Error", "Failed to send daily report. Make sure email is enabled.")

    def _send_stock_alert(self) -> None:
        """Send stock alert now."""
        self._save_settings_silent()
        
        result = notifications.send_low_stock_alert()
        
        if result:
            messagebox.showinfo("Success", "Stock alert sent successfully to all recipients!")
        else:
            messagebox.showinfo("Info", "No low stock items to alert about at this time.\n\nEmail notifications are only sent when items have low stock alerts.")
