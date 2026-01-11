"""Permission management UI for granular access control."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional
import threading

from modules import users, permissions
from utils.audit import audit_logger


class PermissionManagementFrame(ttk.Frame):
    """UI for managing user permissions."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.current_user = getattr(parent.winfo_toplevel(), "current_user", {})
        self.permission_vars: Dict[str, tk.BooleanVar] = {}
        self.user_tree = None
        self.permission_frame = None
        self.selected_user = None

        self._build_ui()
        self._load_users()

    def _build_ui(self) -> None:
        """Build the permission management interface."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        title_label = ttk.Label(main_frame, text="Permission Management",
                               font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 5))

        # Subtitle with guidance
        subtitle_label = ttk.Label(main_frame,
                                 text="Manage user permissions explicitly. No permissions are granted automatically - admins must approve all access.",
                                 font=("Segoe UI", 9), foreground="#666")
        subtitle_label.pack(pady=(0, 20))

        # Create paned window for split layout
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left panel - Users
        left_frame = ttk.LabelFrame(paned, text="Users", padding=10)
        paned.add(left_frame, weight=1)

        # User list
        user_frame = ttk.Frame(left_frame)
        user_frame.pack(fill=tk.BOTH, expand=True)

        # User treeview
        columns = ("Username", "Role", "Status")
        self.user_tree = ttk.Treeview(user_frame, columns=columns, show="headings", height=15)

        for col in columns:
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(user_frame, orient=tk.VERTICAL, command=self.user_tree.yview)
        self.user_tree.configure(yscrollcommand=scrollbar.set)

        self.user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.user_tree.bind("<<TreeviewSelect>>", self._on_user_select)

        # User action buttons
        user_btn_frame = ttk.Frame(left_frame)
        user_btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(user_btn_frame, text="Revoke All Permissions",
                  command=self._reset_user_permissions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(user_btn_frame, text="Refresh", command=self._load_users).pack(side=tk.RIGHT)

        # Right panel - Permissions
        right_frame = ttk.LabelFrame(paned, text="Permissions", padding=10)
        paned.add(right_frame, weight=2)

        # Permission controls
        perm_frame = ttk.Frame(right_frame)
        perm_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable frame for permissions
        self.permission_frame = ttk.Frame(perm_frame)
        self.permission_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas and scrollbar for permissions
        canvas = tk.Canvas(self.permission_frame, height=400)
        scrollbar = ttk.Scrollbar(self.permission_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Permission checkboxes will be added here
        self.permission_container = scrollable_frame

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Permission action buttons
        perm_btn_frame = ttk.Frame(right_frame)
        perm_btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(perm_btn_frame, text="💾 Save Changes",
                  command=self._save_permission_changes).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(perm_btn_frame, text="Grant Selected",
                  command=self._grant_selected_permissions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(perm_btn_frame, text="Revoke Selected",
                  command=self._revoke_selected_permissions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(perm_btn_frame, text="Apply Role Suggestions",
                  command=self._apply_role_suggestions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(perm_btn_frame, text="Select All",
                  command=self._select_all_permissions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(perm_btn_frame, text="Select None",
                  command=self._select_none_permissions).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(perm_btn_frame, text="Grant All",
                  command=self._grant_all_permissions).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(perm_btn_frame, text="Revoke All",
                  command=self._revoke_all_permissions).pack(side=tk.LEFT)

        # Status bar
        self.status_var = tk.StringVar(value="Select a user to manage permissions")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _load_users(self) -> None:
        """Load and display all users."""
        # Clear existing items
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)

        try:
            all_users = users.list_users()
            for user in all_users:
                status = "Active" if user.get('active', 1) else "Inactive"
                self.user_tree.insert("", tk.END, values=(
                    user['username'],
                    user['role'].title(),
                    status
                ), tags=(user['user_id'],))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {e}")

    def _on_user_select(self, event) -> None:
        """Handle user selection."""
        selection = self.user_tree.selection()
        if not selection:
            return

        item = selection[0]
        user_id = int(self.user_tree.item(item, "tags")[0])

        # Find user details
        all_users = users.list_users()
        self.selected_user = next((u for u in all_users if u['user_id'] == user_id), None)

        if self.selected_user:
            self._load_user_permissions()
            self.status_var.set(f"Managing permissions for: {self.selected_user['username']}")

    def _load_user_permissions(self) -> None:
        """Load and display permissions for selected user."""
        if not self.selected_user:
            return

        # Clear existing permission checkboxes
        for widget in self.permission_container.winfo_children():
            widget.destroy()

        self.permission_vars.clear()

        try:
            # Get all available permissions
            all_perms = permissions.get_all_permissions()

            # Get user's effective permissions
            effective_perms = permissions.get_effective_permissions(self.selected_user)
            user_specific_perms = permissions.get_user_permissions(self.selected_user['user_id'])
            role_perms = permissions.get_role_permissions(self.selected_user['role'])

            # Group permissions by category for better organization
            perm_groups = {
                "Dashboard": [],
                "Point of Sale": [],
                "Inventory": [],
                "Reports": [],
                "Order History": [],
                "Expenses": [],
                "User Management": [],
                "Settings": [],
                "System": []
            }

            for perm_key, description in all_perms.items():
                if perm_key.startswith("view_dashboard"):
                    perm_groups["Dashboard"].append((perm_key, description))
                elif perm_key.startswith(("access_pos", "process_sales", "apply_discounts", "void_sales")):
                    perm_groups["Point of Sale"].append((perm_key, description))
                elif perm_key.startswith(("view_inventory", "add_inventory", "edit_inventory", "delete_inventory", "adjust_stock", "view_low_stock")):
                    perm_groups["Inventory"].append((perm_key, description))
                elif perm_key.startswith(("view_reports", "export_reports", "view_profit_reports")):
                    perm_groups["Reports"].append((perm_key, description))
                elif perm_key.startswith(("view_order_history", "refund_orders")):
                    perm_groups["Order History"].append((perm_key, description))
                elif perm_key.startswith(("view_expenses", "add_expenses", "edit_expenses", "delete_expenses")):
                    perm_groups["Expenses"].append((perm_key, description))
                elif perm_key.startswith(("view_users", "manage_users", "manage_roles")):
                    perm_groups["User Management"].append((perm_key, description))
                elif perm_key.startswith(("view_settings", "manage_settings", "manage_permissions")):
                    perm_groups["Settings"].append((perm_key, description))
                else:
                    perm_groups["System"].append((perm_key, description))

            # Create permission checkboxes by group
            row = 0
            for group_name, group_perms in perm_groups.items():
                if not group_perms:
                    continue

                # Group label
                group_label = ttk.Label(self.permission_container, text=f"{group_name}:",
                                       font=("Segoe UI", 10, "bold"))
                group_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 5) if row > 0 else (0, 5))
                row += 1

                # Permission checkboxes
                for perm_key, description in group_perms:
                    # Determine permission status
                    if perm_key in user_specific_perms:
                        status = "Granted (User)"
                        bg_color = "#e8f5e8"  # Light green
                        checkbox_state = True
                    elif perm_key in role_perms:
                        status = "Suggested (Role)"
                        bg_color = "#fff3cd"  # Light yellow
                        checkbox_state = False  # Don't auto-check role suggestions
                    else:
                        status = "Not Granted"
                        bg_color = "#f8d7da"  # Light red
                        checkbox_state = False

                    # Create checkbox variable
                    var = tk.BooleanVar(value=checkbox_state)
                    self.permission_vars[perm_key] = var

                    # Create checkbox with description
                    cb = ttk.Checkbutton(self.permission_container, text=f"{perm_key}", variable=var)
                    cb.grid(row=row, column=0, sticky="w", padx=(20, 5))

                    # Status label
                    status_label = ttk.Label(self.permission_container, text=f"{description} [{status}]",
                                           background=bg_color)
                    status_label.grid(row=row, column=1, sticky="w", padx=(0, 5))

                    row += 1

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load permissions: {e}")

    def _get_selected_permissions(self) -> List[str]:
        """Get list of selected permission keys from checkboxes."""
        selected_perms = []
        for perm_key, var in self.permission_vars.items():
            if var.get():
                selected_perms.append(perm_key)
        return selected_perms

    def _save_permission_changes(self) -> None:
        """Save all permission changes based on current checkbox states."""
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        # Get current checkbox states
        checked_permissions = set(self._get_selected_permissions())

        # Get currently granted permissions
        current_permissions = set(permissions.get_user_permissions(self.selected_user['user_id']))

        # Determine what needs to be granted and revoked
        to_grant = checked_permissions - current_permissions
        to_revoke = current_permissions - checked_permissions

        if not to_grant and not to_revoke:
            messagebox.showinfo("No Changes", "No permission changes detected")
            return

        # Show summary and confirm
        changes_summary = []
        if to_grant:
            changes_summary.append(f"Grant: {len(to_grant)} permission(s)")
        if to_revoke:
            changes_summary.append(f"Revoke: {len(to_revoke)} permission(s)")

        confirm = messagebox.askyesno(
            "Save Permission Changes",
            f"Save permission changes for {self.selected_user['username']}?\n\n"
            f"{' | '.join(changes_summary)}\n\n"
            "This will update the user's permissions to match the current checkbox selections."
        )

        if not confirm:
            return

        try:
            current_user_id = self.current_user.get('user_id')
            changes_made = 0

            # Grant new permissions
            for perm in to_grant:
                permissions.grant_permission(self.selected_user['user_id'], perm, current_user_id)
                changes_made += 1

            # Revoke removed permissions
            for perm in to_revoke:
                permissions.revoke_permission(self.selected_user['user_id'], perm, current_user_id)
                changes_made += 1

            messagebox.showinfo("Success", f"Saved {changes_made} permission change(s)")
            self._load_user_permissions()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save permission changes: {e}")

    def _grant_all_permissions(self) -> None:
        """Grant all permissions to the selected user."""
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        all_perms = list(permissions.get_all_permissions().keys())
        confirm = messagebox.askyesno(
            "Grant All Permissions",
            f"Grant ALL {len(all_perms)} permissions to {self.selected_user['username']}?\n\n"
            "This will give the user access to all system features."
        )

        if confirm:
            try:
                current_user_id = self.current_user.get('user_id')
                for perm in all_perms:
                    permissions.grant_permission(self.selected_user['user_id'], perm, current_user_id)

                messagebox.showinfo("Success", f"Granted all {len(all_perms)} permissions")
                self._load_user_permissions()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to grant all permissions: {e}")

    def _grant_selected_permissions(self) -> None:
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        selected_perms = self._get_selected_permissions()
        if not selected_perms:
            messagebox.showerror("Error", "No permissions selected")
            return

        try:
            current_user_id = self.current_user.get('user_id')
            for perm in selected_perms:
                permissions.grant_permission(self.selected_user['user_id'], perm, current_user_id)

            messagebox.showinfo("Success", f"Granted {len(selected_perms)} permission(s)")
            self._load_user_permissions()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to grant permissions: {e}")

    def _revoke_selected_permissions(self) -> None:
        """Revoke selected permissions from current user."""
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        selected_perms = self._get_selected_permissions()
        if not selected_perms:
            messagebox.showerror("Error", "No permissions selected")
            return

        try:
            current_user_id = self.current_user.get('user_id')
            for perm in selected_perms:
                permissions.revoke_permission(self.selected_user['user_id'], perm, current_user_id)

            messagebox.showinfo("Success", f"Revoked {len(selected_perms)} permission(s)")
            self._load_user_permissions()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to revoke permissions: {e}")

    def _grant_all_permissions(self) -> None:
        """Grant all permissions to current user."""
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        try:
            current_user_id = self.current_user.get('user_id')
            all_perms = list(permissions.get_all_permissions().keys())

            for perm in all_perms:
                permissions.grant_permission(self.selected_user['user_id'], perm, current_user_id)

            messagebox.showinfo("Success", f"Granted all {len(all_perms)} permissions")
            self._load_user_permissions()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to grant all permissions: {e}")

    def _revoke_all_permissions(self) -> None:
        """Revoke all permissions from current user."""
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        try:
            current_user_id = self.current_user.get('user_id')
            all_perms = list(permissions.get_all_permissions().keys())

            for perm in all_perms:
                permissions.revoke_permission(self.selected_user['user_id'], perm, current_user_id)

            messagebox.showinfo("Success", f"Revoked all {len(all_perms)} permissions")
            self._load_user_permissions()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to revoke all permissions: {e}")

    def _select_all_permissions(self) -> None:
        """Select all permission checkboxes."""
        for var in self.permission_vars.values():
            var.set(True)

    def _select_none_permissions(self) -> None:
        """Deselect all permission checkboxes."""
        for var in self.permission_vars.values():
            var.set(False)

    def _apply_role_suggestions(self) -> None:
        """Apply role-based permission suggestions for the selected user."""
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        role = self.selected_user['role']
        role_perms = permissions.get_role_permissions(role)

        if not role_perms:
            messagebox.showinfo("Info", f"No permissions suggested for {role} role")
            return

        confirm = messagebox.askyesno(
            "Apply Role Suggestions",
            f"Grant {len(role_perms)} suggested permissions for {role} role to {self.selected_user['username']}?\n\n"
            f"This will grant permissions typically associated with the {role} role."
        )

        if confirm:
            try:
                current_user_id = self.current_user.get('user_id')
                for perm in role_perms:
                    permissions.grant_permission(self.selected_user['user_id'], perm, current_user_id)

                messagebox.showinfo("Success", f"Applied {len(role_perms)} role suggestions")
                self._load_user_permissions()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to apply role suggestions: {e}")

    def _reset_user_permissions(self) -> None:
        """Revoke all permissions from the selected user."""
        if not self.selected_user:
            messagebox.showerror("Error", "No user selected")
            return

        confirm = messagebox.askyesno(
            "Confirm Revoke All",
            f"Revoke ALL permissions from {self.selected_user['username']}?\n\n"
            "This will remove all granted permissions. Use 'Apply Role Suggestions' to grant permissions again."
        )

        if confirm:
            try:
                current_user_id = self.current_user.get('user_id')
                permissions.reset_user_permissions(self.selected_user['user_id'], self.selected_user['role'], current_user_id)

                messagebox.showinfo("Success", f"Revoked all permissions from {self.selected_user['username']}")
                self._load_user_permissions()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to revoke permissions: {e}")

    def refresh(self) -> None:
        """Refresh the permission management interface."""
        self._load_users()
        if self.selected_user:
            self._load_user_permissions()