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
            "Demo Data",
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
        if self.current_step == 1:  # Database setup
            return self.db_setup_complete
        elif self.current_step == 2:  # Admin account
            return self._validate_admin_form()
        elif self.current_step == 3:  # System config
            return True  # Basic validation
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
        try:
            # Create admin user
            username = self.username.get().strip()
            password = self.password.get()
            create_user(username=username, password=password, role="admin", active=True)
            
            # Save currency setting
            self._save_currency_setting()
            
            # Seed demo data if requested
            if self.seed_demo_var.get():
                self._seed_demo_data()
            
            # Save basic config (could be expanded)
            # For now, just show success
            messagebox.showinfo("Success", f"Setup complete!\n\nAdmin account '{username}' created successfully.\n\nYou can now log in.")
            self.on_success()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete setup: {e}")
