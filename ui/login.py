"""Login UI frame for the Kiosk POS application."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules.users import validate_credentials


class LoginFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_success, **kwargs):
        super().__init__(master, padding=24, **kwargs)
        self.on_success = on_success
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._init_styles()

        self._build_ui()

    def _init_styles(self) -> None:
        style = ttk.Style(self)
        style.configure("LoginRoot.TFrame", background="#EDE9E3")
        style.configure(
            "LoginCard.TFrame",
            background="#FDFBF7",
            bordercolor="#D9D2C7",
            relief="solid",
            borderwidth=1,
        )
        style.configure("LoginTitle.TLabel", background="#FDFBF7", foreground="#2F2A25", font=("Segoe UI", 18, "bold"))
        style.configure("LoginLabel.TLabel", background="#FDFBF7", foreground="#2F2A25", font=("Segoe UI", 10, "semibold"))
        style.configure(
            "LoginField.TEntry",
            fieldbackground="#FFFFFF",
            foreground="#2F2A25",
            bordercolor="#D9D2C7",
            lightcolor="#0A7C86",
            darkcolor="#0A7C86",
        )
        style.map(
            "LoginField.TEntry",
            bordercolor=[("focus", "#0A7C86")],
            lightcolor=[("focus", "#0A7C86")],
        )
        style.configure(
            "LoginPrimary.TButton",
            background="#0A7C86",
            foreground="#FFFFFF",
            font=("Segoe UI", 11, "medium"),
            padding=(12, 8),
            relief="raised",
            borderwidth=1,
            anchor="center",
        )
        style.map(
            "LoginPrimary.TButton",
            background=[
                ("pressed", "#0C90A0"),
                ("active", "#0C90A0"),
                ("!disabled", "#0A7C86"),
            ],
            foreground=[
                ("pressed", "#FFFFFF"),
                ("active", "#FFFFFF"),
                ("!disabled", "#FFFFFF"),
                ("disabled", "#E0E0E0"),
            ],
        )
        style.configure("LoginError.TLabel", background="#FDFBF7", foreground="#B53B3B", font=("Segoe UI", 9))


    def _build_ui(self) -> None:
        # Base surface
        self.configure(style="LoginRoot.TFrame")
        self.columnconfigure(0, weight=1)

        # Centered card
        card = ttk.Frame(self, padding=24, style="LoginCard.TFrame")
        card.grid(row=0, column=0, sticky=tk.N)
        card.columnconfigure(0, weight=0)
        card.columnconfigure(1, weight=1)

        # Logo (if available)
        try:
            from PIL import Image, ImageTk
            import os
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            logo_path = os.path.abspath(logo_path)
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((64, 64), Image.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = ttk.Label(card, image=self.logo_photo, background="#FDFBF7")
                logo_label.grid(row=0, column=0, columnspan=2, pady=(0, 8))
        except Exception:
            pass

        from main import APP_VERSION
        ttk.Label(card, text=f"Welcome to Kiosk POS v{APP_VERSION}", style="LoginTitle.TLabel").grid(row=1, column=0, columnspan=2, pady=(0, 8))
        ttk.Label(card, text="Sign in to continue", style="LoginLabel.TLabel").grid(row=2, column=0, columnspan=2, pady=(0, 16))

        ttk.Label(card, text="Username", style="LoginLabel.TLabel").grid(row=3, column=0, sticky=tk.W, pady=4)
        username_entry = ttk.Entry(card, textvariable=self.username_var, width=32, style="LoginField.TEntry")
        username_entry.grid(row=3, column=1, sticky=tk.EW, pady=4)
        username_entry.focus_set()

        ttk.Label(card, text="Password", style="LoginLabel.TLabel").grid(row=4, column=0, sticky=tk.W, pady=4)
        password_entry = ttk.Entry(card, textvariable=self.password_var, show="*", width=32, style="LoginField.TEntry")
        password_entry.grid(row=4, column=1, sticky=tk.EW, pady=4)
        password_entry.bind("<Return>", lambda _evt: self.submit())

        # Show password toggle
        self.show_password = tk.BooleanVar(value=False)
        def toggle_password():
            password_entry.config(show="" if self.show_password.get() else "*")
        show_pwd_chk = ttk.Checkbutton(card, text="Show Password", variable=self.show_password, command=toggle_password, style="LoginLabel.TLabel")
        show_pwd_chk.grid(row=5, column=1, sticky=tk.W, pady=(0, 8))

        # Use tk.Button to guarantee text visibility across themes
        login_btn = tk.Button(
            card,
            text="Login",
            command=self.submit,
            bg="#0A7C86",
            fg="#FFFFFF",
            activebackground="#0C90A0",
            activeforeground="#FFFFFF",
            relief=tk.RAISED,
            bd=1,
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=6,
        )
        login_btn.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=(14, 8))

        status_lbl = ttk.Label(card, textvariable=self.status_var, style="LoginError.TLabel")
        status_lbl.grid(row=7, column=0, columnspan=2, sticky=tk.W)

    def submit(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get()
        print(f"[DEBUG] Attempting login for user: {username}")
        if not username or not password:
            self.status_var.set("Enter username and password")
            print("[DEBUG] Username or password missing.")
            return

        try:
            user = validate_credentials(username, password)
            print(f"[DEBUG] validate_credentials returned: {user}")
        except Exception as e:
            self.status_var.set("Error accessing database.")
            print(f"[ERROR] Exception during validate_credentials: {e}")
            return

        if not user:
            self.status_var.set("Invalid credentials or inactive user")
            print("[DEBUG] Invalid credentials or inactive user.")
            return

        self.status_var.set("")
        print("[DEBUG] Login successful, calling on_success.")
        self.on_success(user)
