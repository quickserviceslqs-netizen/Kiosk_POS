"""User management UI for admins."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import users


class ChangePasswordDialog:
    def __init__(self, parent, username: str):
        self.result = False
        dialog = tk.Toplevel(parent)
        dialog.title(f"Change password: {username}")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        old_pwd = tk.StringVar()
        new_pwd = tk.StringVar()
        confirm_pwd = tk.StringVar()

        ttk.Label(dialog, text="Old Password").grid(row=0, column=0, sticky=tk.W, pady=4, padx=6)
        ttk.Entry(dialog, textvariable=old_pwd, show="*").grid(row=0, column=1, sticky=tk.EW, pady=4, padx=6)

        ttk.Label(dialog, text="New Password").grid(row=1, column=0, sticky=tk.W, pady=4, padx=6)
        ttk.Entry(dialog, textvariable=new_pwd, show="*").grid(row=1, column=1, sticky=tk.EW, pady=4, padx=6)

        ttk.Label(dialog, text="Confirm Password").grid(row=2, column=0, sticky=tk.W, pady=4, padx=6)
        ttk.Entry(dialog, textvariable=confirm_pwd, show="*").grid(row=2, column=1, sticky=tk.EW, pady=4, padx=6)

        def on_submit():
            if not old_pwd.get():
                messagebox.showerror("Error", "Old password required")
                return
            if not new_pwd.get() or new_pwd.get() != confirm_pwd.get():
                messagebox.showerror("Error", "New passwords do not match")
                return
            if users.change_own_password(username, old_pwd.get(), new_pwd.get()):
                messagebox.showinfo("Success", "Password changed")
                self.result = True
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Old password incorrect")

        ttk.Button(dialog, text="Change", command=on_submit).grid(row=3, column=0, columnspan=2, pady=10)
        dialog.columnconfigure(1, weight=1)
        dialog.wait_window()


class UserManagementFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.tree = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Users", font=("Segoe UI", 14, "bold"))
        header.grid(row=0, column=0, sticky=tk.W, pady=(0, 12))

        btns = ttk.Frame(self)
        btns.grid(row=0, column=1, sticky=tk.E)
        ttk.Button(btns, text="Add", command=self._add_user_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Reset Password", command=self._reset_selected_password).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Toggle Active", command=self._toggle_active).pack(side=tk.LEFT, padx=4)

        columns = ("username", "role", "active", "created_at")
        tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        tree.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=8)

        headings = {
            "username": "Username",
            "role": "Role",
            "active": "Active",
            "created_at": "Created",
        }
        for col, label in headings.items():
            tree.heading(col, text=label)
            tree.column(col, width=120, anchor=tk.W)
        tree.column("username", width=160)
        tree.column("created_at", width=160)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=2, sticky=tk.NS)

        self.tree = tree

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = users.list_users()
        for row in rows:
            self.tree.insert(
                "",
                tk.END,
                iid=row["username"],
                values=(row["username"], row["role"], "Yes" if row["active"] else "No", row.get("created_at", "")),
                tags=("inactive",) if not row["active"] else (),
            )
        self.tree.tag_configure("inactive", foreground="gray")

    def _selected_username(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    def _add_user_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Add User")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        username = tk.StringVar()
        password = tk.StringVar()
        role = tk.StringVar(value="cashier")
        active = tk.BooleanVar(value=True)

        fields = [
            ("Username", username),
            ("Password", password),
        ]
        for idx, (label, var) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=idx, column=0, sticky=tk.W, pady=4, padx=6)
            show = "*" if label == "Password" else None
            ttk.Entry(dialog, textvariable=var, show=show).grid(row=idx, column=1, sticky=tk.EW, pady=4, padx=6)

        ttk.Label(dialog, text="Role").grid(row=2, column=0, sticky=tk.W, pady=4, padx=6)
        role_box = ttk.Combobox(dialog, textvariable=role, values=sorted(users.VALID_ROLES), state="readonly")
        role_box.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=6)

        ttk.Checkbutton(dialog, text="Active", variable=active).grid(row=3, column=1, sticky=tk.W, pady=4, padx=6)

        def on_submit():
            uname = username.get().strip()
            pwd = password.get()
            if not uname or not pwd:
                messagebox.showerror("Invalid", "Username and password are required")
                return
            try:
                users.create_user(uname, pwd, role=role.get(), active=active.get())
            except Exception as exc:  # sqlite unique or validation
                messagebox.showerror("Error", str(exc))
                return
            self.refresh()
            dialog.destroy()

        ttk.Button(dialog, text="Create", command=on_submit).grid(row=4, column=0, columnspan=2, pady=10)
        dialog.columnconfigure(1, weight=1)
        dialog.wait_window()

    def _reset_selected_password(self) -> None:
        uname = self._selected_username()
        if not uname:
            messagebox.showinfo("Reset", "Select a user first")
            return
        dialog = tk.Toplevel(self)
        dialog.title(f"Reset password: {uname}")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        new_pwd = tk.StringVar()
        ttk.Label(dialog, text="New Password").grid(row=0, column=0, sticky=tk.W, pady=4, padx=6)
        ttk.Entry(dialog, textvariable=new_pwd, show="*").grid(row=0, column=1, sticky=tk.EW, pady=4, padx=6)

        def on_submit():
            if not new_pwd.get():
                messagebox.showerror("Invalid", "Password required")
                return
            users.set_password(uname, new_pwd.get())
            dialog.destroy()
            messagebox.showinfo("Reset", "Password updated")

        ttk.Button(dialog, text="Save", command=on_submit).grid(row=1, column=0, columnspan=2, pady=8)
        dialog.columnconfigure(1, weight=1)
        dialog.wait_window()

    def _toggle_active(self) -> None:
        uname = self._selected_username()
        if not uname:
            messagebox.showinfo("Toggle", "Select a user first")
            return
        current = users.get_user_by_username(uname)
        if not current:
            messagebox.showerror("Error", "User not found")
            return
        target_state = not bool(current.get("active"))
        users.set_active(uname, target_state)
        self.refresh()

        state_text = "activated" if target_state else "deactivated"
        messagebox.showinfo("Status", f"User {uname} {state_text}")
