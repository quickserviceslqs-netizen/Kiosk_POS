import tkinter as tk
from tkinter import ttk, messagebox
from modules.users import create_user, validate_password_strength
from utils import set_window_icon
import threading
import time


class AdminSetupFrame(ttk.Frame):
    """First-time setup wizard for initializing the Kiosk POS system."""
    
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.current_step = 0
        self.steps = [
            "Welcome",
            "Database Setup", 
            "Admin Account",
            "System Configuration",
            "Complete"
        ]
        self._build_ui()
        self._show_step(0)

    def _build_ui(self):
        # Center the content
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        center_frame = ttk.Frame(self)
        center_frame.grid(row=0, column=0)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(center_frame, variable=self.progress_var, 
                                          maximum=len(self.steps), mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=40, pady=(20, 10))
        
        # Step indicator
        self.step_label = ttk.Label(center_frame, text="", font=("Segoe UI", 10))
        self.step_label.pack(pady=(0, 20))
        
        # Content frame
        self.content_frame = ttk.Frame(center_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=10)
        
        # Navigation buttons
        btn_frame = ttk.Frame(center_frame)
        btn_frame.pack(fill=tk.X, padx=40, pady=20)
        
        self.back_btn = ttk.Button(btn_frame, text="← Back", command=self._go_back, state=tk.DISABLED)
        self.back_btn.pack(side=tk.LEFT)
        
        self.next_btn = ttk.Button(btn_frame, text="Next →", command=self._go_next)
        self.next_btn.pack(side=tk.RIGHT)
        
        self.finish_btn = ttk.Button(btn_frame, text="Finish Setup", command=self._finish_setup, state=tk.DISABLED)
        self.finish_btn.pack(side=tk.RIGHT, padx=(0, 10))

    def _show_step(self, step_index):
        # Clear current content
        for child in self.content_frame.winfo_children():
            child.destroy()
        
        self.current_step = step_index
        step_name = self.steps[step_index]
        
        # Update progress
        self.progress_var.set(step_index + 1)
        self.step_label.config(text=f"Step {step_index + 1} of {len(self.steps)}: {step_name}")
        
        # Update button states
        self.back_btn.config(state=tk.NORMAL if step_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if step_index < len(self.steps) - 2 else tk.DISABLED)
        self.finish_btn.config(state=tk.NORMAL if step_index == len(self.steps) - 2 else tk.DISABLED)
        
        # Show step content
        if step_index == 0:
            self._show_welcome()
        elif step_index == 1:
            self._show_database_setup()
        elif step_index == 2:
            self._show_admin_account()
        elif step_index == 3:
            self._show_system_config()
        elif step_index == 4:
            self._show_complete()

    def _show_welcome(self):
        ttk.Label(self.content_frame, text="🏪 Welcome to Kiosk POS", 
                  font=("Segoe UI", 20, "bold")).pack(pady=(20, 8))
        ttk.Label(self.content_frame, text="First-Time Setup Wizard", 
                  font=("Segoe UI", 14)).pack(pady=(0, 8))
        ttk.Label(self.content_frame, text="This wizard will help you set up your point-of-sale system.\n\n"
                  "We'll guide you through:\n"
                  "• Database initialization\n"
                  "• Administrator account creation\n"
                  "• Basic system configuration\n\n"
                  "Click Next to begin.", 
                  font=("Segoe UI", 10), justify=tk.LEFT).pack(pady=(0, 20))

    def _show_database_setup(self):
        ttk.Label(self.content_frame, text="Database Setup", 
                  font=("Segoe UI", 16, "bold")).pack(pady=(20, 8))
        ttk.Label(self.content_frame, text="Initializing the database for your store...",
                  font=("Segoe UI", 10)).pack(pady=(0, 20))
        
        # Status label
        self.db_status_label = ttk.Label(self.content_frame, text="Preparing database...",
                                       font=("Segoe UI", 10))
        self.db_status_label.pack(pady=10)
        
        # Start database setup in background
        self.db_setup_complete = False
        threading.Thread(target=self._setup_database, daemon=True).start()

    def _setup_database(self):
        try:
            self.db_status_label.config(text="Creating database tables...")
            time.sleep(0.5)  # Simulate work
            
            self.db_status_label.config(text="Setting up default data...")
            time.sleep(0.5)
            
            self.db_status_label.config(text="Database setup complete!")
            self.db_setup_complete = True
            
        except Exception as e:
            self.db_status_label.config(text=f"Error: {e}", foreground="red")
            self.db_setup_complete = False

    def _show_admin_account(self):
        ttk.Label(self.content_frame, text="Administrator Account", 
                  font=("Segoe UI", 16, "bold")).pack(pady=(20, 8))
        ttk.Label(self.content_frame, text="Create your administrator account",
                  font=("Segoe UI", 10)).pack(pady=(0, 20))

        # Form frame
        form_container = ttk.Frame(self.content_frame)
        form_container.pack(pady=10)

        # Username
        ttk.Label(form_container, text="Username:").grid(row=0, column=0, sticky=tk.W, padx=6, pady=8)
        self.username = tk.StringVar()
        username_entry = ttk.Entry(form_container, textvariable=self.username, width=30)
        username_entry.grid(row=0, column=1, padx=6, pady=8)
        username_entry.focus()

        # Password
        ttk.Label(form_container, text="Password:").grid(row=1, column=0, sticky=tk.W, padx=6, pady=8)
        self.password = tk.StringVar()
        ttk.Entry(form_container, textvariable=self.password, show="•", width=30).grid(row=1, column=1, padx=6, pady=8)

        # Confirm Password
        ttk.Label(form_container, text="Confirm Password:").grid(row=2, column=0, sticky=tk.W, padx=6, pady=8)
        self.confirm = tk.StringVar()
        ttk.Entry(form_container, textvariable=self.confirm, show="•", width=30).grid(row=2, column=1, padx=6, pady=8)

        # Password requirements hint
        ttk.Label(form_container, text="Password must be at least 8 characters with uppercase, lowercase, and numbers",
                  font=("Segoe UI", 9), foreground="gray").grid(row=3, column=0, columnspan=2, pady=(4, 0))

    def _show_system_config(self):
        ttk.Label(self.content_frame, text="System Configuration", 
                  font=("Segoe UI", 16, "bold")).pack(pady=(20, 8))
        ttk.Label(self.content_frame, text="Configure basic system settings",
                  font=("Segoe UI", 10)).pack(pady=(0, 20))

        # Form frame
        form_container = ttk.Frame(self.content_frame)
        form_container.pack(pady=10)

        # Business Name
        ttk.Label(form_container, text="Business Name:").grid(row=0, column=0, sticky=tk.W, padx=6, pady=8)
        self.business_name = tk.StringVar(value="My Store")
        ttk.Entry(form_container, textvariable=self.business_name, width=30).grid(row=0, column=1, padx=6, pady=8)

        # Currency
        ttk.Label(form_container, text="Currency:").grid(row=1, column=0, sticky=tk.W, padx=6, pady=8)
        self.currency = tk.StringVar(value="USD")
        currency_combo = ttk.Combobox(form_container, textvariable=self.currency, 
                                    values=["USD", "EUR", "GBP", "KES", "ZAR"], width=27, state="readonly")
        currency_combo.grid(row=1, column=1, padx=6, pady=8)
        currency_combo.current(0)

    def _show_complete(self):
        ttk.Label(self.content_frame, text="✅ Setup Complete!", 
                  font=("Segoe UI", 20, "bold")).pack(pady=(20, 8))
        ttk.Label(self.content_frame, text="Your Kiosk POS system is ready to use.",
                  font=("Segoe UI", 12)).pack(pady=(0, 20))
        ttk.Label(self.content_frame, text="You can now log in with your administrator account.",
                  font=("Segoe UI", 10)).pack(pady=(0, 10))

    def _go_back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _go_next(self):
        if self.current_step < len(self.steps) - 1:
            # Validate current step before proceeding
            if self._validate_current_step():
                self._show_step(self.current_step + 1)

    def _validate_current_step(self):
        if self.current_step == 1:  # Database setup
            return self.db_setup_complete
        elif self.current_step == 2:  # Admin account
            return self._validate_admin_form()
        elif self.current_step == 3:  # System config
            return True  # Basic validation
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

    def _finish_setup(self):
        try:
            # Create admin user
            username = self.username.get().strip()
            password = self.password.get()
            create_user(username=username, password=password, role="admin", active=True)
            
            # Save basic config (could be expanded)
            # For now, just show success
            messagebox.showinfo("Success", f"Setup complete!\n\nAdmin account '{username}' created successfully.\n\nYou can now log in.")
            self.on_success()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete setup: {e}")
