"""Audit log viewer UI for administrators."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import os
import json
from typing import List, Dict, Any

from database.init_db import get_connection
from utils.audit import audit_logger
from utils import set_window_icon


class AuditLogsFrame(ttk.Frame):
    """Display audit logs with filtering and search capabilities."""

    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.file_audit_entries: List[Dict[str, Any]] = []
        self.db_audit_entries: List[Dict[str, Any]] = []
        self.filtered_entries: List[Dict[str, Any]] = []
        self.all_entries: List[Dict[str, Any]] = []
        self.current_page = 0
        self.page_size = 100
        self.total_entries = 0
        self._build_ui()
        self._load_audit_data()

    def _build_ui(self):
        """Build the UI layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Tree frame gets expansion space

        # Title
        ttk.Label(self, text="Audit Logs", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 20))

        # Filters frame
        filters_frame = ttk.LabelFrame(self, text="Filters", padding=10)
        filters_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 10))
        filters_frame.columnconfigure(1, weight=1)
        filters_frame.columnconfigure(3, weight=1)

        # Date range filters
        ttk.Label(filters_frame, text="From Date:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.from_date_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        self.from_date_entry = ttk.Entry(filters_frame, textvariable=self.from_date_var, width=12)
        self.from_date_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(filters_frame, text="To Date:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.to_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.to_date_entry = ttk.Entry(filters_frame, textvariable=self.to_date_var, width=12)
        self.to_date_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        # User filter
        ttk.Label(filters_frame, text="User:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(filters_frame, textvariable=self.user_var, width=15)
        self.user_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))

        # Action filter
        ttk.Label(filters_frame, text="Action:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        self.action_var = tk.StringVar()
        self.action_combo = ttk.Combobox(filters_frame, textvariable=self.action_var, width=15)
        self.action_combo.grid(row=1, column=3, sticky=tk.W, padx=(0, 20), pady=(10, 0))

        # Source filter
        ttk.Label(filters_frame, text="Source:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        self.source_var = tk.StringVar(value="All")
        self.source_combo = ttk.Combobox(filters_frame, textvariable=self.source_var,
                                        values=["All", "Database", "File"], width=15)
        self.source_combo.grid(row=2, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))

        # Apply filters button
        ttk.Button(filters_frame, text="Apply Filters", command=self._apply_filters).grid(
            row=2, column=2, columnspan=2, sticky=tk.W, pady=(10, 0))

        # Treeview for audit entries
        tree_frame = ttk.LabelFrame(self, text="Audit Entries", padding=10)
        tree_frame.grid(row=2, column=0, sticky=tk.NSEW, pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)  # Treeview gets all available space in this frame

        # Create treeview with scrollbars
        columns = ("timestamp", "user", "action", "table", "record_id", "source", "details")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=25)  # Increased height further

        # Define column headings
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("user", text="User")
        self.tree.heading("action", text="Action")
        self.tree.heading("table", text="Table")
        self.tree.heading("record_id", text="Record ID")
        self.tree.heading("source", text="Source")
        self.tree.heading("details", text="Details")

        # Define column widths
        self.tree.column("timestamp", width=150, minwidth=120)
        self.tree.column("user", width=100, minwidth=80)
        self.tree.column("action", width=120, minwidth=100)
        self.tree.column("table", width=100, minwidth=80)
        self.tree.column("record_id", width=80, minwidth=60)
        self.tree.column("source", width=80, minwidth=60)
        self.tree.column("details", width=300, minwidth=200)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Grid the treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        h_scrollbar.grid(row=1, column=0, sticky=tk.EW)

        # Configure tree_frame grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Bind double-click to show details
        self.tree.bind("<Double-1>", self._show_entry_details)

        # Action buttons
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(row=3, column=0, sticky=tk.EW, pady=(0, 10))

        ttk.Button(buttons_frame, text="Refresh", command=self._load_audit_data).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Export to CSV", command=self._export_to_csv).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Clear Old Entries", command=self._clear_old_entries).pack(side=tk.LEFT)

        # Pagination controls (moved outside tree_frame for better space allocation)
        pagination_frame = ttk.Frame(self)
        pagination_frame.grid(row=4, column=0, sticky=tk.EW, pady=(0, 10))

        ttk.Button(pagination_frame, text="◀◀ First", command=self._go_to_first_page).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pagination_frame, text="◀ Previous", command=self._go_to_previous_page).pack(side=tk.LEFT, padx=(0, 10))

        self.page_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_label.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(pagination_frame, text="Next ▶", command=self._go_to_next_page).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pagination_frame, text="Last ▶▶", command=self._go_to_last_page).pack(side=tk.LEFT)

        # Page size selector
        ttk.Label(pagination_frame, text="Show:").pack(side=tk.RIGHT, padx=(10, 0))
        self.page_size_var = tk.StringVar(value="100")
        page_size_combo = ttk.Combobox(pagination_frame, textvariable=self.page_size_var,
                                      values=["50", "100", "200", "500"], width=5)
        page_size_combo.pack(side=tk.RIGHT, padx=(0, 10))
        page_size_combo.bind("<<ComboboxSelected>>", self._change_page_size)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self, textvariable=self.status_var, foreground="blue")
        self.status_label.grid(row=5, column=0, sticky=tk.W)

        # Configure grid weights for proper expansion
        self.grid_rowconfigure(2, weight=1)  # Tree frame gets expansion
        self.grid_columnconfigure(0, weight=1)

    def _load_audit_data(self):
        """Load audit data from both file and database sources."""
        try:
            self.status_var.set("Loading audit data...")

            # Load file audit entries (all of them since they're usually not too many)
            self.file_audit_entries = self._load_file_audit_entries()

            # Get total count of database entries for pagination
            self.total_entries = self._get_db_audit_count()

            # Load first page of database entries
            self.current_page = 0
            self.db_audit_entries = audit_logger.get_audit_trail(
                limit=self.page_size,
                offset=self.current_page * self.page_size
            )

            # Combine entries for current page
            self._combine_and_sort_entries()

            # Update filter options
            self._update_filter_options()

            # Apply current filters
            self._apply_filters()

            self._update_page_label()
            self.status_var.set(f"Loaded page {self.current_page + 1} ({len(self.db_audit_entries)} DB + {len(self.file_audit_entries)} file entries)")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load audit data: {e}")
            self.status_var.set("Error loading data")

    def _load_file_audit_entries(self) -> List[Dict[str, Any]]:
        """Load audit entries from the file-based log."""
        entries = []
        audit_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'order_history_audit.log')

        if not os.path.exists(audit_file):
            return entries

        try:
            with open(audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # Parse log line: "timestamp - level - message"
                    parts = line.split(' - ', 2)
                    if len(parts) >= 3:
                        timestamp_str = parts[0]
                        message = parts[2]

                        # Parse the message: "ACTION=action, SALE_ID=id, USER=user, DETAILS=details"
                        entry = {"source": "File", "table": None, "record_id": None, "old_values": None, "new_values": None}

                        # Parse timestamp
                        try:
                            entry["timestamp"] = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f').isoformat()
                        except ValueError:
                            entry["timestamp"] = timestamp_str

                        # Parse message fields
                        msg_parts = message.split(', ')
                        for part in msg_parts:
                            if '=' in part:
                                key, value = part.split('=', 1)
                                if key == 'ACTION':
                                    entry["action"] = value
                                elif key == 'SALE_ID':
                                    entry["record_id"] = int(value) if value.isdigit() else None
                                elif key == 'USER':
                                    entry["username"] = value
                                elif key == 'DETAILS':
                                    entry["details"] = value

                        entries.append(entry)

        except Exception as e:
            print(f"Error reading audit file: {e}")

        return entries

    def _get_db_audit_count(self) -> int:
        """Get total count of database audit entries."""
        try:
            audit_logger._ensure_table()
            with get_connection() as conn:
                result = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
                return result[0] if result else 0
        except Exception:
            return 0

    def _combine_and_sort_entries(self):
        """Combine database and file entries, sort by timestamp."""
        all_entries = self.db_audit_entries + self.file_audit_entries

        # Sort by timestamp (newest first)
        all_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        self.all_entries = all_entries

    def _update_filter_options(self):
        """Update the filter combobox options based on available data."""
        # Get unique users
        users = set()
        for entry in self.all_entries:
            username = entry.get("username")
            if username:
                users.add(username)
        self.user_combo['values'] = [""] + sorted(list(users))

        # Get unique actions
        actions = set()
        for entry in self.all_entries:
            action = entry.get("action")
            if action:
                actions.add(action)
        self.action_combo['values'] = [""] + sorted(list(actions))

    def _apply_filters(self):
        """Apply current filters to the audit data."""
        try:
            from_date = datetime.strptime(self.from_date_var.get(), '%Y-%m-%d') if self.from_date_var.get() else None
            to_date = datetime.strptime(self.to_date_var.get() + ' 23:59:59', '%Y-%m-%d %H:%M:%S') if self.to_date_var.get() else None

            user_filter = self.user_var.get().strip()
            action_filter = self.action_var.get().strip()
            source_filter = self.source_var.get()

            self.filtered_entries = []

            for entry in self.all_entries:
                # Date filter
                entry_date = None
                timestamp = entry.get("timestamp", "")
                if timestamp:
                    try:
                        if 'T' in timestamp:
                            entry_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            entry_date = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                if from_date and entry_date and entry_date < from_date:
                    continue
                if to_date and entry_date and entry_date > to_date:
                    continue

                # User filter
                if user_filter and entry.get("username", "") != user_filter:
                    continue

                # Action filter
                if action_filter and entry.get("action", "") != action_filter:
                    continue

                # Source filter
                if source_filter != "All" and entry.get("source", "").lower() != source_filter.lower():
                    continue

                self.filtered_entries.append(entry)

            self._update_treeview()

        except Exception as e:
            messagebox.showerror("Filter Error", f"Invalid filter criteria: {e}")

    def _update_treeview(self):
        """Update the treeview with filtered entries."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add filtered entries
        for entry in self.filtered_entries:
            timestamp = entry.get("timestamp", "")
            # Format timestamp for display
            try:
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                display_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                display_timestamp = timestamp

            values = (
                display_timestamp,
                entry.get("username", ""),
                entry.get("action", ""),
                entry.get("table_name", entry.get("table", "")),
                entry.get("record_id", ""),
                entry.get("source", ""),
                entry.get("details", "")
            )

            self.tree.insert("", tk.END, values=values, tags=(entry.get("source", "").lower(),))

        # Configure row colors based on source
        self.tree.tag_configure("database", background="#f0f8ff")
        self.tree.tag_configure("file", background="#fff8f0")

        # Update page label
        self._update_page_label()

    def _go_to_first_page(self):
        """Go to first page."""
        if self.current_page > 0:
            self.current_page = 0
            self._load_current_page()

    def _go_to_previous_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._load_current_page()

    def _go_to_next_page(self):
        """Go to next page."""
        total_pages = (self.total_entries + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._load_current_page()

    def _go_to_last_page(self):
        """Go to last page."""
        total_pages = (self.total_entries + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page = total_pages - 1
            self._load_current_page()

    def _change_page_size(self, event=None):
        """Change page size and reload data."""
        try:
            new_size = int(self.page_size_var.get())
            if new_size != self.page_size:
                self.page_size = new_size
                self.current_page = 0
                self._load_audit_data()
        except ValueError:
            pass

    def _load_current_page(self):
        """Load the current page of data."""
        try:
            self.status_var.set(f"Loading page {self.current_page + 1}...")

            # Load current page of database entries
            self.db_audit_entries = audit_logger.get_audit_trail(
                limit=self.page_size,
                offset=self.current_page * self.page_size
            )

            # Combine with file entries
            self._combine_and_sort_entries()

            # Apply current filters
            self._apply_filters()

            self._update_page_label()
            self.status_var.set(f"Loaded page {self.current_page + 1} ({len(self.db_audit_entries)} DB + {len(self.file_audit_entries)} file entries)")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load page: {e}")
            self.status_var.set("Error loading page")

    def _update_page_label(self):
        """Update the page navigation label."""
        total_pages = (self.total_entries + self.page_size - 1) // self.page_size
        current_page_display = self.current_page + 1
        self.page_label.config(text=f"Page {current_page_display} of {max(1, total_pages)}")

    def _show_entry_details(self, event):
        """Show detailed information for the selected audit entry."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.tree.item(item, "values")

        # Find the corresponding entry
        index = self.tree.index(item)
        if index < len(self.filtered_entries):
            entry = self.filtered_entries[index]

            # Create details dialog
            dialog = tk.Toplevel(self)
            dialog.title("Audit Entry Details")
            dialog.geometry("600x400")
            set_window_icon(dialog)

            # Create scrollable text area
            text_frame = ttk.Frame(dialog, padding=10)
            text_frame.pack(fill=tk.BOTH, expand=True)

            text = tk.Text(text_frame, wrap=tk.WORD, padx=10, pady=10)
            scrollbar = ttk.Scrollbar(text_frame, command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)

            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Format details
            details = f"""Audit Entry Details
{'='*50}

Timestamp: {values[0]}
User: {values[1] or 'N/A'}
Action: {values[2] or 'N/A'}
Table: {values[3] or 'N/A'}
Record ID: {values[4] or 'N/A'}
Source: {values[5] or 'N/A'}

Details: {values[6] or 'N/A'}

Full Entry Data:
{'-'*30}
"""

            # Add all entry fields
            for key, value in entry.items():
                if key not in ["timestamp", "username", "action", "table_name", "table", "record_id", "source", "details"]:
                    if isinstance(value, dict):
                        details += f"{key}: {json.dumps(value, indent=2)}\n"
                    else:
                        details += f"{key}: {value}\n"

            text.insert(tk.END, details)
            text.config(state=tk.DISABLED)

            # OK button
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _export_to_csv(self):
        """Export filtered audit entries to CSV."""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                title="Export Audit Logs",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

            if not filename:
                return

            import csv
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'username', 'action', 'table', 'record_id', 'source', 'details']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for entry in self.filtered_entries:
                    writer.writerow({
                        'timestamp': entry.get('timestamp', ''),
                        'username': entry.get('username', ''),
                        'action': entry.get('action', ''),
                        'table': entry.get('table_name', entry.get('table', '')),
                        'record_id': entry.get('record_id', ''),
                        'source': entry.get('source', ''),
                        'details': entry.get('details', '')
                    })

            messagebox.showinfo("Export Complete", f"Audit logs exported to {filename}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _clear_old_entries(self):
        """Clear old audit entries from database (admin confirmation required)."""
        result = messagebox.askyesno(
            "Confirm Clear",
            "This will permanently delete audit entries older than 365 days from the database.\n\nFile-based logs will not be affected.\n\nContinue?"
        )

        if result:
            try:
                deleted_count = audit_logger.cleanup_old_entries()
                messagebox.showinfo("Cleanup Complete", f"Deleted {deleted_count} old audit entries from database.")
                self._load_audit_data()  # Refresh the display
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear old entries: {e}")