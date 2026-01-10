import tkinter as tk
from tkinter import ttk, messagebox
from modules.users import create_user
from utils import set_window_icon


class AdminSetupFrame(ttk.Frame):
    """First-time setup frame for creating the initial admin account."""
    
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self._build_ui()

    def _build_ui(self):
        # Center the content
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        center_frame = ttk.Frame(self)
        center_frame.grid(row=0, column=0)
        
        # Welcome header
        ttk.Label(center_frame, text="🏪 Welcome to Kiosk POS", 
                  font=("Segoe UI", 20, "bold")).pack(pady=(40, 8))
        ttk.Label(center_frame, text="First-Time Setup", 
                  font=("Segoe UI", 14)).pack(pady=(0, 8))
        ttk.Label(center_frame, text="Create your administrator account to get started.",
                  font=("Segoe UI", 10)).pack(pady=(0, 24))

        # Form frame with border
        form_container = ttk.LabelFrame(center_frame, text="Admin Account", padding=20)
        form_container.pack(pady=8, padx=40)

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
        ttk.Label(form_container, text="Password must be at least 6 characters",
                  font=("Segoe UI", 9), foreground="gray").grid(row=3, column=0, columnspan=2, pady=(4, 0))

        # Submit button
        btn_frame = ttk.Frame(center_frame)
        btn_frame.pack(pady=24)
        ttk.Button(btn_frame, text="Create Admin Account", command=self._submit, 
                   style="Accent.TButton").pack(ipadx=20, ipady=8)

    def _submit(self):
        username = self.username.get().strip()
        password = self.password.get()
        confirm = self.confirm.get()
        
        # Validation
        if not username:
            messagebox.showerror("Error", "Username is required.")
            return
        if len(username) < 3:
            messagebox.showerror("Error", "Username must be at least 3 characters.")
            return
        if not password:
            messagebox.showerror("Error", "Password is required.")
            return
        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        
        try:
            create_user(username=username, password=password, role="admin", active=True)
            messagebox.showinfo("Success", f"Admin account '{username}' created successfully!\n\nYou can now log in.")
            self.on_success()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create admin account: {e}")
