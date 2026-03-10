"""User management UI for admins."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import users
from modules import permissions
from utils import set_window_icon
from utils.security import get_username


class ChangePasswordDialog:
    def __init__(self, parent, username: str):
        self.result = False
        dialog = tk.Toplevel(parent)
        dialog.withdraw()
        dialog.title(f"Change password: {username}")
        set_window_icon(dialog)
        dialog.resizable(True, True)

        outer = ttk.Frame(dialog, padding=(14, 12, 14, 10))
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)

        old_pwd = tk.StringVar()
        new_pwd = tk.StringVar()
        confirm_pwd = tk.StringVar()

        ttk.Label(outer, text="Old Password").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        old_entry = ttk.Entry(outer, textvariable=old_pwd, show="*", width=24)
        old_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        ttk.Label(outer, text="New Password").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        ttk.Entry(outer, textvariable=new_pwd, show="*", width=24).grid(row=1, column=1, sticky=tk.EW, pady=5)

        ttk.Label(outer, text="Confirm Password").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        ttk.Entry(outer, textvariable=confirm_pwd, show="*", width=24).grid(row=2, column=1, sticky=tk.EW, pady=5)

        def on_submit():
            if not old_pwd.get():
                messagebox.showerror("Error", "Old password required", parent=dialog)
                return
            if not new_pwd.get() or new_pwd.get() != confirm_pwd.get():
                messagebox.showerror("Error", "New passwords do not match", parent=dialog)
                return
            if users.change_own_password(username, old_pwd.get(), new_pwd.get()):
                messagebox.showinfo("Success", "Password changed", parent=dialog)
                self.result = True
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Old password incorrect", parent=dialog)

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(10, 4))
        ttk.Button(btn_frame, text="💾  Change Password", command=on_submit, width=18).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=8).pack(side=tk.LEFT)
        dialog.bind("<Return>", lambda e: on_submit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        dialog.update_idletasks()
        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        w, h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        dialog.geometry(f"+{(sw - w) // 2}+{max(30, (sh - h) // 2 - 40)}")
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        old_entry.focus_set()
        dialog.wait_window()


class UserManagementFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, padding=16, **kwargs)
        self.current_user = getattr(master.winfo_toplevel(), "current_user", {})
        self.is_admin = permissions.has_permission(self.current_user, 'manage_users')
        
        # Check permission to view users
        current_username = get_username()
        if not permissions.has_permission(current_username, 'view_users'):
            messagebox.showerror("Permission Denied", "You do not have permission to view users")
            return
        
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
        ttk.Button(btns, text="Delete", command=self._delete_user).pack(side=tk.LEFT, padx=4)

        columns = ("username", "role", "active", "created_at")
        if self.is_admin:
            columns = ("username", "role", "password", "active", "created_at")
        tree = ttk.Treeview(self, columns=columns, show="headings")
        tree.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=8)

        headings = {
            "username": "Username",
            "role": "Role",
            "active": "Active",
            "created_at": "Created",
        }
        if self.is_admin:
            headings["password"] = "Password (double-click to reset)"
        for col, label in headings.items():
            tree.heading(col, text=label)
            tree.column(col, width=160, minwidth=100, anchor=tk.W, stretch=True)
        tree.column("username", width=220, minwidth=120)
        tree.column("created_at", width=200, minwidth=120)
        if self.is_admin:
            tree.column("password", width=180, minwidth=120)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=2, sticky=tk.NS)

        self.tree = tree

        # Add double-click handler for password reset
        if self.is_admin:
            tree.bind("<Double-1>", self._on_tree_double_click)

        # Ensure treeview can receive focus for events
        tree.focus_set()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.grid_propagate(True)  # Allow frame to expand

    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = users.list_users()
        for row in rows:
            values = (row["username"], row["role"], "Yes" if row["active"] else "No", row.get("created_at", ""))
            if self.is_admin:
                password = row.get("plain_password")
                if password is None:
                    password = "Reset to view"
                values = (row["username"], row["role"], password, "Yes" if row["active"] else "No", row.get("created_at", ""))
            self.tree.insert(
                "",
                tk.END,
                iid=row["username"],
                values=values,
                tags=("inactive",) if not row["active"] else (),
            )
        try:
            from utils.theme import get_theme_colors
            _tc = get_theme_colors()
            _inactive_fg = _tc.get('text_light', '#9ca3af')
        except Exception:
            _inactive_fg = '#9ca3af'
        self.tree.tag_configure("inactive", foreground=_inactive_fg)
        
        # Ensure double-click binding is active after refresh
        self._ensure_double_click_binding()
        
        # Ensure treeview maintains focus
        self.tree.focus_set()

    def _ensure_double_click_binding(self) -> None:
        """Ensure the double-click binding is active for admin users."""
        if self.is_admin:
            # Remove any existing binding first to avoid duplicates
            try:
                self.tree.unbind("<Double-1>")
            except:
                pass
            self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _on_tree_double_click(self, event) -> None:
        """Handle double-click on treeview to reset passwords for any user."""
        try:
            # Get the clicked row and column
            row_id = self.tree.identify_row(event.y)
            col_id = self.tree.identify_column(event.x)
            
            print(f"DEBUG: Double-click detected - row_id: {row_id}, col_id: {col_id}")  # Debug print
            
            if not row_id or not col_id:
                print("DEBUG: No row_id or col_id, returning")  # Debug print
                return
                
            # Only proceed if password column was clicked (column #2)
            if col_id != "#3":  # Treeview columns are 1-indexed: #1=username, #2=role, #3=password
                print(f"DEBUG: Wrong column clicked: {col_id}, expected #3")  # Debug print
                return
                
            uname = row_id
            
            # Check if this user exists
            user_data = users.get_user_by_username(uname)
            print(f"DEBUG: User data for {uname}: {user_data is not None}, plain_password: {user_data.get('plain_password') if user_data else None}")  # Debug print
            
            if user_data:
                # Select the user and open reset dialog
                self.tree.selection_set(uname)
                self._reset_selected_password()
                print(f"DEBUG: Opened reset dialog for user: {uname}")  # Debug print
        except Exception as e:
            print(f"DEBUG: Exception in double-click handler: {e}")  # Debug print
            # If anything goes wrong, try the fallback method
            uname = self._selected_username()
            if uname:
                user_data = users.get_user_by_username(uname)
                if user_data:
                    self._reset_selected_password()
                    print(f"DEBUG: Opened reset dialog via fallback for user: {uname}")  # Debug print

    def _selected_username(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    def _add_user_dialog(self) -> None:
        # Check permission to manage users
        current_username = get_username()
        if not permissions.has_permission(current_username, 'manage_users'):
            messagebox.showerror("Permission Denied", "You do not have permission to manage users")
            return
        
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title("Add User")
        set_window_icon(dialog)
        dialog.resizable(True, True)

        outer = ttk.Frame(dialog, padding=(14, 12, 14, 10))
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)

        username_var = tk.StringVar()
        password_var = tk.StringVar()
        role_var = tk.StringVar(value="cashier")
        active_var = tk.BooleanVar(value=True)

        ttk.Label(outer, text="Username *").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        uname_entry = ttk.Entry(outer, textvariable=username_var, width=24)
        uname_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        ttk.Label(outer, text="Password *").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        ttk.Entry(outer, textvariable=password_var, show="*", width=24).grid(row=1, column=1, sticky=tk.EW, pady=5)

        ttk.Label(outer, text="Role").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        ttk.Combobox(outer, textvariable=role_var, values=sorted(users.VALID_ROLES),
                     state="readonly", width=22).grid(row=2, column=1, sticky=tk.EW, pady=5)

        ttk.Checkbutton(outer, text="Active", variable=active_var).grid(
            row=3, column=1, sticky=tk.W, pady=5)

        def on_submit():
            uname = username_var.get().strip()
            pwd = password_var.get()
            if not uname or not pwd:
                messagebox.showerror("Required", "Username and password are required", parent=dialog)
                return
            try:
                users.create_user(uname, pwd, role=role_var.get(), active=active_var.get())
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=dialog)
                return
            self.refresh()
            dialog.destroy()

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(10, 4))
        ttk.Button(btn_frame, text="➕  Create User", command=on_submit, width=14).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=8).pack(side=tk.LEFT)
        dialog.bind("<Return>", lambda e: on_submit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        dialog.update_idletasks()
        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        w, h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        dialog.geometry(f"+{(sw - w) // 2}+{max(30, (sh - h) // 2 - 40)}")
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        uname_entry.focus_set()
        dialog.wait_window()

    def _reset_selected_password(self) -> None:
        # Check permission to manage users
        current_username = get_username()
        if not permissions.has_permission(current_username, 'manage_users'):
            messagebox.showerror("Permission Denied", "You do not have permission to manage users")
            return
        uname = self._selected_username()
        if not uname:
            messagebox.showinfo("Reset", "Select a user first")
            return
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title(f"Reset password: {uname}")
        set_window_icon(dialog)
        dialog.resizable(True, True)

        outer = ttk.Frame(dialog, padding=(14, 12, 14, 10))
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)

        new_pwd = tk.StringVar()
        ttk.Label(outer, text="New Password *").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        pwd_entry = ttk.Entry(outer, textvariable=new_pwd, show="*", width=24)
        pwd_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        def on_submit():
            if not new_pwd.get():
                messagebox.showerror("Required", "Password required", parent=dialog)
                return
            users.set_password(uname, new_pwd.get())
            dialog.destroy()
            messagebox.showinfo("Reset", "Password updated")
            self.refresh()
            self.tree.focus_set()
            self._ensure_double_click_binding()
            self.tree.focus(uname)

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(10, 4))
        ttk.Button(btn_frame, text="💾  Save Password", command=on_submit, width=16).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=8).pack(side=tk.LEFT)
        dialog.bind("<Return>", lambda e: on_submit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        dialog.update_idletasks()
        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        w, h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        dialog.geometry(f"+{(sw - w) // 2}+{max(30, (sh - h) // 2 - 40)}")
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        pwd_entry.focus_set()
        dialog.wait_window()

    def _toggle_active(self) -> None:
        # Check permission to manage users
        current_username = get_username()
        if not permissions.has_permission(current_username, 'manage_users'):
            messagebox.showerror("Permission Denied", "You do not have permission to manage users")
            return
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

    def _delete_user(self) -> None:
        # Check permission to manage users
        current_username = get_username()
        if not permissions.has_permission(current_username, 'manage_users'):
            messagebox.showerror("Permission Denied", "You do not have permission to manage users")
            return
        
        uname = self._selected_username()
        if not uname:
            messagebox.showinfo("Delete", "Select a user first")
            return

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete user '{uname}'?\n\nThis action cannot be undone."):
            return

        # Attempt deletion
        success, message = users.delete_user(uname)
        if success:
            messagebox.showinfo("Success", message)
            self.refresh()
        else:
            messagebox.showerror("Error", message)
