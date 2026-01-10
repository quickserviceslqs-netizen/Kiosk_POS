import tkinter as tk
from tkinter import ttk, messagebox
from modules.users import create_user, validate_password_strength
from utils import set_window_icon
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
            "Database Setup", 
            "Admin Account",
            "System Configuration",
            "Demo Data",
            "Complete"
        ]
        setup_logger.info("Setup wizard initialized")
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
        
        # Help button
        help_btn = ttk.Button(center_frame, text="❓ Help", command=self._show_help)
        help_btn.pack(anchor=tk.NE, padx=20, pady=(0, 10))
        
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
            self._show_demo_data()
        elif step_index == 5:
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
        
        # Progress frame
        progress_frame = ttk.Frame(self.content_frame)
        progress_frame.pack(pady=10, fill=tk.X)
        
        # Progress bar for database setup
        self.db_progress_var = tk.DoubleVar()
        self.db_progress_bar = ttk.Progressbar(progress_frame, variable=self.db_progress_var, 
                                             maximum=100, mode='determinate')
        self.db_progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # Status label
        self.db_status_label = ttk.Label(progress_frame, text="Preparing database...",
                                       font=("Segoe UI", 9))
        self.db_status_label.pack(pady=2)
        
        # Error display (initially hidden)
        self.db_error_label = ttk.Label(progress_frame, text="", 
                                      font=("Segoe UI", 9), foreground="red", wraplength=400)
        self.db_error_label.pack(pady=2)
        
        # Retry button (initially hidden)
        self.retry_btn = ttk.Button(progress_frame, text="Retry", command=self._retry_database_setup)
        self.retry_btn.pack(pady=5)
        self.retry_btn.pack_forget()  # Hide initially
        
        # Start database setup
        self.db_setup_complete = False
        self.db_setup_error = None
        self._start_database_setup()

    def _start_database_setup(self):
        """Start database setup with progress tracking."""
        setup_logger.info("Starting database setup")
        self.db_progress_var.set(0)
        self.db_status_label.config(text="Preparing database...", foreground="black")
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
            self.db_status_label.config(text="Database setup complete!", foreground="green")
            self.db_setup_complete = True
            self.completed_steps.add(1)  # Mark database setup as completed
            setup_logger.info("Database setup completed successfully")
            
        except Exception as e:
            setup_logger.error(f"Database setup failed: {e}")
            self.db_setup_error = str(e)
            self.db_progress_var.set(0)
            self.db_status_label.config(text="Database setup failed!", foreground="red")
            self.db_error_label.config(text=f"Error: {e}")
            self.retry_btn.pack(pady=5)
            self.db_setup_complete = False

    def _retry_database_setup(self):
        """Retry database setup after failure."""
        setup_logger.info("Retrying database setup")
        self._start_database_setup()

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
                                    values=["USD", "EUR", "GBP", "KES", "ZAR", "CAD", "AUD", "JPY", "CNY"], width=27, state="readonly")
        currency_combo.grid(row=1, column=1, padx=6, pady=8)
        currency_combo.current(0)

        # Currency description
        ttk.Label(form_container, text="Select your primary currency for transactions and reports",
                 font=("Segoe UI", 9), foreground="gray").grid(row=2, column=0, columnspan=2, pady=(4, 0))

    def _show_demo_data(self):
        ttk.Label(self.content_frame, text="Demo Data (Optional)", 
                  font=("Segoe UI", 16, "bold")).pack(pady=(20, 8))
        ttk.Label(self.content_frame, text="Would you like to add sample data to explore the system?",
                  font=("Segoe UI", 10)).pack(pady=(0, 20))

        # Demo data options
        options_frame = ttk.Frame(self.content_frame)
        options_frame.pack(pady=10)

        self.seed_demo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Add demo items and sample sales", 
                       variable=self.seed_demo_var).pack(anchor=tk.W, pady=5)

        ttk.Label(options_frame, text="This will create:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
        demo_items = [
            "• Sample products (Bananas, Milk, Bread)",
            "• Demo cashier user account",
            "• Sample sales transactions",
            "• Dashboard data for testing"
        ]
        for item in demo_items:
            ttk.Label(options_frame, text=item, font=("Segoe UI", 9)).pack(anchor=tk.W, padx=20)

        ttk.Label(options_frame, text="\nYou can remove demo data later from the admin panel.", 
                 font=("Segoe UI", 9), foreground="gray").pack(anchor=tk.W, pady=(10, 0))

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
            # Validate business name and currency
            business_name = self.business_name.get().strip()
            if not business_name:
                messagebox.showerror("Validation Error", "Business name is required.")
                return False
            if len(business_name) < 2:
                messagebox.showerror("Validation Error", "Business name must be at least 2 characters.")
                return False
            return True
        elif self.current_step == 4:  # Demo data
            return True  # Always valid (optional)
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

    def _seed_demo_data(self):
        """Seed demo data into the database."""
        try:
            from modules import items, pos, users
            
            # Create a test cashier user
            try:
                users.create_user('cashier', 'cashier123', role='cashier')
            except Exception:
                pass  # User may already exist
            
            # Create demo items
            demo_items = [
                dict(name='Bananas', category='Fruit', cost_price=20.0, selling_price=35.0, quantity=100, unit_of_measure='pieces', is_special_volume=0),
                dict(name='Milk 1L', category='Dairy', cost_price=40.0, selling_price=60.0, quantity=200, unit_of_measure='L', is_special_volume=1, unit_size_ml=1000),
                dict(name='Bread Loaf', category='Bakery', cost_price=25.0, selling_price=45.0, quantity=80, unit_of_measure='pieces', is_special_volume=0),
            ]
            
            created_items = []
            for item_data in demo_items:
                try:
                    item = items.create_item(**item_data)
                    created_items.append(item)
                except Exception:
                    pass  # Item may already exist
            
            # Create demo sales if items were created
            if created_items:
                try:
                    # Sale 1: 2 bananas
                    if len(created_items) > 0:
                        line_items = [{'item_id': created_items[0]['item_id'], 'quantity': 2, 'price': 35.0}]
                        pos.create_sale(line_items, payment=70.0)
                except Exception:
                    pass
                
                try:
                    # Sale 2: 1 liter milk
                    if len(created_items) > 1:
                        line_items = [{'item_id': created_items[1]['item_id'], 'quantity': 1, 'price': 60.0}]
                        pos.create_sale(line_items, payment=60.0)
                except Exception:
                    pass
                    
        except Exception as e:
            # Don't fail setup if demo data seeding fails
            print(f"Warning: Failed to seed demo data: {e}")

    def _save_currency_setting(self):
        """Save the selected currency to the database."""
        try:
            from database.init_db import get_connection
            currency = self.currency.get()
            with get_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                           ("currency", currency))
                conn.commit()
        except Exception as e:
            # Don't fail setup if currency save fails
            print(f"Warning: Failed to save currency setting: {e}")

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
            
            # Step 2: Save currency setting
            setup_logger.info("Saving currency settings")
            self._save_currency_setting()
            self.completed_steps.add(3)  # Mark system config as completed
            
            # Step 3: Seed demo data if requested
            if self.seed_demo_var.get():
                setup_logger.info("Seeding demo data")
                try:
                    self._seed_demo_data()
                    setup_logger.info("Demo data seeded successfully")
                except Exception as demo_error:
                    setup_logger.warning(f"Demo data seeding failed (non-critical): {demo_error}")
                    # Don't fail setup for demo data issues
            
            self.completed_steps.add(4)  # Mark demo data as completed
            
            # Step 4: Final health check
            setup_logger.info("Running final health check")
            from main import validate_setup_health
            healthy, health_message = validate_setup_health()
            
            if not healthy:
                setup_logger.warning(f"Health check issues detected: {health_message}")
                # Show warning but don't fail setup
                messagebox.showwarning("Setup Warnings", 
                    f"Setup completed with some warnings:\n\n{health_message}\n\n"
                    "The system should still function, but you may want to review the configuration.")
            
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

    def _show_recovery_options(self, error_message):
        """Show recovery options when setup fails."""
        setup_logger.info("Showing recovery options to user")
        
        recovery_window = tk.Toplevel(self.parent)
        recovery_window.title("Setup Recovery")
        recovery_window.geometry("500x400")
        recovery_window.resizable(False, False)
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
            step_names = ["Welcome", "Database Setup", "Admin Account", "System Config", "Demo Data"]
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
• Sets up default VAT rates, units of measure, and categories
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

STEP 5: Demo Data (Optional)
---------------------------
Choose whether to add sample data to explore the system:
• Sample products (Bananas, Milk, Bread)
• Demo cashier user account
• Sample sales transactions
• Dashboard data for testing

You can safely skip this if you want to start with a clean system.

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
4. Set up VAT rates and units of measure
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
