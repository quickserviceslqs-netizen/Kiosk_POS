import tkinter as tk
from tkinter import ttk, messagebox
from modules.users import ensure_admin_user

class AdminSetupFrame(ttk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Admin Setup", font=("Segoe UI", 16, "bold")).pack(pady=(24, 8))
        ttk.Label(self, text="Set up your admin account for first-time use.").pack(pady=(0, 16))

        form = ttk.Frame(self)
        form.pack(pady=8)

        ttk.Label(form, text="Username:").grid(row=0, column=0, sticky=tk.W, padx=6, pady=4)
        self.username = tk.StringVar()
        ttk.Entry(form, textvariable=self.username).grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(form, text="Password:").grid(row=1, column=0, sticky=tk.W, padx=6, pady=4)
        self.password = tk.StringVar()
        ttk.Entry(form, textvariable=self.password, show="*").grid(row=1, column=1, padx=6, pady=4)

        ttk.Label(form, text="Confirm Password:").grid(row=2, column=0, sticky=tk.W, padx=6, pady=4)
        self.confirm = tk.StringVar()
        ttk.Entry(form, textvariable=self.confirm, show="*").grid(row=2, column=1, padx=6, pady=4)

        ttk.Button(self, text="Create Admin Account", command=self._submit).pack(pady=16)

    def _submit(self):
        username = self.username.get().strip()
        password = self.password.get()
        confirm = self.confirm.get()
        if not username or not password:
            messagebox.showerror("Error", "Username and password required.")
            return
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        if ensure_admin_user(username, password):
            messagebox.showinfo("Success", "Admin account created.")
            self.on_success()
        else:
            messagebox.showerror("Error", "Failed to create admin account.")
