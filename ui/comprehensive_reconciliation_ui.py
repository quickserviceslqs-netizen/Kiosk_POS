"""
Comprehensive Reconciliation UI with Session Management

This UI provides a complete reconciliation workflow:
- Session creation with period selection (daily, weekly, monthly, custom)
- Calendar picker for custom date ranges
- Auto-population from system sales data
- Manual entry for actual amounts
- Variance calculations and explanations
- Session management (view, amend, delete)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkinter.font as tkFont
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Union
import logging
import sqlite3
import time
import csv
from pathlib import Path

try:
    from tkcalendar import Calendar
    TKCALENDAR_AVAILABLE = True
except ImportError:
    TKCALENDAR_AVAILABLE = False

from modules.reconciliation_core import (
    ReconciliationSession, ReconciliationItem, ReconciliationEntry,
    VarianceExplanation,  # Added for variance explanations
    create_reconciliation_session, get_reconciliation_session,
    update_reconciliation_entry, complete_reconciliation_session,
    get_sales_by_payment_method_for_period, calculate_date_range,
    get_variance_explanations, add_variance_explanation,  # Added for variance explanations
    update_variance_explanation, delete_variance_explanation,  # Added for variance explanations
    get_explained_variance_total, get_unexplained_variance,  # Added for variance explanations
    add_variance_explanation_to_db,  # Added for persisting in-memory explanations
    save_reconciliation_session,  # Added for saving sessions
    delete_reconciliation_session,  # Added for deleting sessions
    get_reconciliation_explanations  # Added for getting explanations from DB
)
from utils.i18n import get_currency_symbol
from utils.app_config import get_or_create_config
from utils import set_window_icon
from utils.date_utils import format_date, parse_date_flexible, get_tkcalendar_date_pattern
from utils.security import get_username
from modules import permissions

logger = logging.getLogger(__name__)


class ComprehensiveReconciliationUI(ttk.Frame):
    """Comprehensive reconciliation UI with session management."""

    def __init__(self, parent: tk.Misc, *, on_home: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Check permission to view reconciliation
        current_username = get_username()
        if not permissions.has_permission(current_username, 'view_reconciliation'):
            from tkinter import messagebox
            messagebox.showerror("Permission Denied", "You do not have permission to view reconciliation")
            return
        
        self.currency_symbol = get_currency_symbol()
        self.current_session: Optional[ReconciliationSession] = None
        self.on_home = on_home

        # Get database path from config
        app_dir = Path(__file__).parent.parent
        config = get_or_create_config(app_dir)
        self.db_path = config["db_path"]

        # Get user info
        root = parent.winfo_toplevel()
        self.current_user = getattr(root, "current_user", {})
        self.user_id = self.current_user.get('user_id', 1)

        self.configure(padding=10)
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the comprehensive reconciliation UI."""
        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text="Payment Reconciliation",
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

        # Main container with navigation
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Navigation buttons
        nav_frame = ttk.Frame(main_container)
        nav_frame.pack(fill=tk.X, pady=(0, 10))

        self.nav_buttons = {}
        nav_options = [
            ("create", "Create Session"),
            ("manage", "Manage Sessions"),
            ("reconcile", "Save Data"),
            ("save_draft", "💾 Save as Draft"),
            ("complete", "✅ Complete Reconciliation")
        ]

        for key, label in nav_options:
            if key in ["save_draft", "complete", "reconcile"]:
                # These buttons should only be enabled when there's an active session
                if key == "reconcile":
                    btn = ttk.Button(nav_frame, text=label, state="disabled",
                                   command=self._show_reconcile_status_dialog)
                else:
                    btn = ttk.Button(nav_frame, text=label, state="disabled",
                                   command=lambda k=key: self._handle_nav_action(k))
            else:
                btn = ttk.Button(nav_frame, text=label, command=lambda k=key: self._switch_view(k))
            btn.pack(side=tk.LEFT, padx=(0, 10))
            self.nav_buttons[key] = btn

        # Content area - use a container to hold cached view frames
        self.content_container = ttk.Frame(main_container)
        self.content_container.pack(fill=tk.BOTH, expand=True)

        # Cache for view frames to avoid recreating them
        self.view_frames = {}
        self.current_view_frame = None

        # Initialize with create session view
        self.current_view = "create"
        self._switch_view("create")

    def _switch_view(self, view: str) -> None:
        """Switch between different views."""
        # Update button styles
        for key, btn in self.nav_buttons.items():
            if key == view:
                btn.config(style="Accent.TButton")
            elif key in ["save_draft", "complete", "reconcile"]:
                # These buttons don't get accent style, just enable/disable
                pass
            else:
                btn.config(style="TButton")

        # Enable/disable session-specific buttons
        has_session = self.current_session is not None
        on_reconcile_view = view == "reconcile"

        # Check if session has meaningful system data
        has_system_data = has_session and self.current_session.items and any(item.system_amount != 0 for item in self.current_session.items)

        # Session action buttons (save_draft, complete, reconcile) only enabled on reconcile view with data
        session_buttons_enabled = has_system_data and on_reconcile_view
        self.nav_buttons["save_draft"].config(state="normal" if session_buttons_enabled else "disabled")
        self.nav_buttons["complete"].config(state="normal" if session_buttons_enabled else "disabled")
        # Save Data button: enabled only on reconcile view with data
        self.nav_buttons["reconcile"].config(state="normal" if session_buttons_enabled else "disabled")

        # Hide current content and show cached view
        if self.current_view_frame:
            self.current_view_frame.grid_remove()
        
        # Show selected view
        self.current_view = view
        if view not in self.view_frames:
            # Create and cache the view
            if view == "create":
                self.view_frames[view] = self._show_create_session()
            elif view == "manage":
                self.view_frames[view] = self._show_manage_sessions()
            elif view == "reconcile":
                # Save current work before showing reconciliation view
                if self.current_session and self.current_session.session_id is None:
                    # New unsaved session - save it first
                    try:
                        session_id = self._save_new_session_to_database()
                        self.current_session.session_id = session_id
                    except Exception as e:
                        messagebox.showerror("Save Error", f"Failed to save session: {str(e)}")
                        return
                elif self.current_session and self.current_session.session_id is not None:
                    # Existing session - save current changes
                    try:
                        self._save_session()
                    except Exception as e:
                        messagebox.showerror("Save Error", f"Failed to save changes: {str(e)}")
                        return
                self.view_frames[view] = self._show_reconciliation()
        else:
            # Refresh data for existing views if needed
            if view == "manage":
                self._load_sessions_list()
            elif view == "reconcile":
                self._load_session_data()
                self._update_totals()
        
        # Show the cached view
        self.view_frames[view].grid(row=0, column=0, sticky=tk.NSEW)
        self.current_view_frame = self.view_frames[view]

    def _handle_nav_action(self, action: str) -> None:
        """Handle navigation actions like save draft and complete."""
        if action == "save_draft":
            self._save_draft_session()
        elif action == "complete":
            self._complete_reconciliation()

    def _show_reconcile_status_dialog(self) -> None:
        """Save current reconciliation data and refresh the view."""
        if not self.current_session:
            messagebox.showerror("No Session", "No active reconciliation session.")
            return

        try:
            # Save current session (which refreshes cash_out from expenses)
            if self.current_session.session_id is None:
                # New unsaved session - save it first
                session_id = self._save_new_session_to_database()
                self.current_session.session_id = session_id
            else:
                # Existing session - save current changes
                self._save_session()

            # Refresh the current view to show updated calculations
            if self.current_view == "reconcile":
                self._load_session_data()
                self._update_totals()
            
            messagebox.showinfo("Success", "Reconciliation data saved and refreshed successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def _show_create_session(self) -> ttk.Frame:
        """Show session creation interface."""
        frame = ttk.Frame(self.content_container)
        # Don't pack here, let the caller handle it

        # Title
        ttk.Label(frame, text="Create New Reconciliation Session",
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))

        # Period selection
        period_frame = ttk.LabelFrame(frame, text="Select Period", padding=10)
        period_frame.pack(fill=tk.X, pady=(0, 20))

        # Period type selection
        type_frame = ttk.Frame(period_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(type_frame, text="Period Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.period_type_var = tk.StringVar(value="daily")
        period_combo = ttk.Combobox(type_frame, textvariable=self.period_type_var,
                                   values=["daily", "weekly", "monthly", "custom"],
                                   state="readonly", width=15)
        period_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        period_combo.bind("<<ComboboxSelected>>", self._on_period_type_change)

        # Date selection
        date_frame = ttk.Frame(period_frame)
        date_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(date_frame, text="Reference Date:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.reference_date_var = tk.StringVar(value=format_date(datetime.now()))
        date_entry = ttk.Entry(date_frame, textvariable=self.reference_date_var, width=12)
        date_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))

        ttk.Button(date_frame, text="📅", width=3,
                  command=self._show_calendar_picker).grid(row=0, column=2, sticky=tk.W)

        # Custom date range (hidden by default)
        self.custom_date_frame = ttk.Frame(period_frame)

        ttk.Label(self.custom_date_frame, text="Start Date:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.start_date_var = tk.StringVar()
        ttk.Entry(self.custom_date_frame, textvariable=self.start_date_var, width=12).grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(self.custom_date_frame, text="📅", width=3,
                  command=lambda: self._show_calendar_picker_for_field(self.start_date_var, trigger_update=False)).grid(row=0, column=2, sticky=tk.W, padx=(0, 20))

        ttk.Label(self.custom_date_frame, text="End Date:").grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        self.end_date_var = tk.StringVar()
        ttk.Entry(self.custom_date_frame, textvariable=self.end_date_var, width=12).grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        ttk.Button(self.custom_date_frame, text="📅", width=3,
                  command=lambda: self._show_calendar_picker_for_field(self.end_date_var, trigger_update=False)).grid(row=0, column=5, sticky=tk.W)

        # Create button
        ttk.Button(frame, text="Create Reconciliation Session",
                  command=self._create_session).pack(pady=20)

        # Status
        self.create_status_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.create_status_var,
                 foreground="blue").pack(pady=(10, 0))

        return frame

    def _show_manage_sessions(self) -> ttk.Frame:
        """Show session management interface."""
        frame = ttk.Frame(self.content_container)
        # Don't pack here

        # Title
        ttk.Label(frame, text="Manage Reconciliation Sessions",
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))

        # Initialize search/filter variables
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="All")
        self.period_filter_var = tk.StringVar(value="All")
        self.sort_var = tk.StringVar(value="Date")
        self.quick_date_var = tk.StringVar(value="30 Days")
        self.session_count_var = tk.StringVar(value="Loading sessions...")

        # Initialize date range to last 30 days
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        self.from_date_var = tk.StringVar(value=last_30_days.strftime("%Y-%m-%d"))
        self.to_date_var = tk.StringVar(value=today.strftime("%Y-%m-%d"))

        # Sessions list
        list_frame = ttk.LabelFrame(frame, text="All Sessions", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Search and filter controls
        controls_frame = ttk.Frame(list_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        # Search
        ttk.Label(controls_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(controls_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind('<KeyRelease>', self._on_search_change)

        # Status filter
        ttk.Label(controls_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        self.status_filter_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(controls_frame, textvariable=self.status_filter_var,
                                   values=["All", "Draft", "Completed", "Approved", "Reviewed", "Rejected"],
                                   state="readonly", width=10)
        status_combo.pack(side=tk.LEFT, padx=(0, 10))
        status_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        # Period filter
        ttk.Label(controls_frame, text="Period:").pack(side=tk.LEFT, padx=(0, 5))
        self.period_filter_var = tk.StringVar(value="All")
        period_combo = ttk.Combobox(controls_frame, textvariable=self.period_filter_var,
                                   values=["All", "Daily", "Weekly", "Monthly", "Yearly", "Custom"],
                                   state="readonly", width=10)
        period_combo.pack(side=tk.LEFT, padx=(0, 10))
        period_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        # Quick date range selector
        ttk.Label(controls_frame, text="Quick Range:").pack(side=tk.LEFT, padx=(0, 5))
        self.quick_date_var = tk.StringVar(value="30 Days")
        quick_date_combo = ttk.Combobox(controls_frame, textvariable=self.quick_date_var,
                                       values=["7 Days", "14 Days", "30 Days", "90 Days", "Custom"],
                                       state="readonly", width=10)
        quick_date_combo.pack(side=tk.LEFT, padx=(0, 10))
        quick_date_combo.bind("<<ComboboxSelected>>", self._on_quick_date_change)

        # Sort options
        ttk.Label(controls_frame, text="Sort by:").pack(side=tk.LEFT, padx=(0, 5))
        self.sort_var = tk.StringVar(value="Date")
        sort_combo = ttk.Combobox(controls_frame, textvariable=self.sort_var,
                                 values=["Date", "Session ID", "Status", "Total Variance"],
                                 state="readonly", width=12)
        sort_combo.pack(side=tk.LEFT, padx=(0, 10))
        sort_combo.bind("<<ComboboxSelected>>", self._on_sort_change)

        # Session count
        self.session_count_var = tk.StringVar(value="Loading sessions...")
        ttk.Label(controls_frame, textvariable=self.session_count_var,
                 font=("Segoe UI", 9, "italic")).pack(side=tk.RIGHT)

        # Treeview for sessions - taller for more data
        columns = ("session_id", "date", "period", "status", "total_system", "total_variance", "total_explained", "reviewed")
        self.sessions_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)

        self.sessions_tree.heading("session_id", text="Session ID")
        self.sessions_tree.heading("date", text="Date")
        self.sessions_tree.heading("period", text="Period")
        self.sessions_tree.heading("status", text="Status")
        self.sessions_tree.heading("total_system", text=f"System Total ({self.currency_symbol})")
        self.sessions_tree.heading("total_variance", text=f"Variance ({self.currency_symbol})")
        self.sessions_tree.heading("total_explained", text=f"Explained ({self.currency_symbol})")
        self.sessions_tree.heading("reviewed", text="Reviewed")

        self.sessions_tree.column("session_id", width=80, anchor='center')
        self.sessions_tree.column("date", width=100, anchor='center')
        self.sessions_tree.column("period", width=100, anchor='center')
        self.sessions_tree.column("status", width=100, anchor='center')
        self.sessions_tree.column("total_system", width=120, anchor='e')
        self.sessions_tree.column("total_variance", width=120, anchor='e')
        self.sessions_tree.column("total_explained", width=120, anchor='e')
        self.sessions_tree.column("reviewed", width=80, anchor='center')

        # Bind double-click event
        self.sessions_tree.bind("<Double-1>", self._on_session_double_click)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sessions_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.sessions_tree.xview)
        self.sessions_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.sessions_tree.pack(fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Action buttons
        actions_frame = ttk.Frame(frame)
        actions_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(actions_frame, text="📂 Load Session",
                  command=self._load_selected_session).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions_frame, text="✏️ Edit Session",
                  command=self._edit_selected_session).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions_frame, text="🗑️ Delete Session",
                  command=self._delete_selected_session).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions_frame, text="🔄 Refresh List",
                  command=self._load_sessions_list).pack(side=tk.LEFT, padx=(0, 10))

        # Add session summary footer
        self._add_sessions_footer(frame)

        # Load sessions
        self._load_sessions_list()

        return frame

    def _add_sessions_footer(self, parent_frame: ttk.Frame) -> None:
        """Add a footer showing session totals and breakdowns."""
        footer_frame = ttk.LabelFrame(parent_frame, text="Session Summary", padding=10)
        footer_frame.pack(fill=tk.X, pady=(20, 0))

        # Initialize summary variables
        self.total_sessions_var = tk.StringVar(value="0")
        self.reviewed_sessions_var = tk.StringVar(value="0")
        self.draft_sessions_var = tk.StringVar(value="0")
        self.completed_sessions_var = tk.StringVar(value="0")
        self.approved_sessions_var = tk.StringVar(value="0")
        self.rejected_sessions_var = tk.StringVar(value="0")
        self.total_system_sales_var = tk.StringVar(value=f"{self.currency_symbol}0.00")
        self.total_variance_var = tk.StringVar(value=f"{self.currency_symbol}0.00")
        self.total_explained_var = tk.StringVar(value=f"{self.currency_symbol}0.00")

        # Create a grid layout for the summary
        summary_frame = ttk.Frame(footer_frame)
        summary_frame.pack(fill=tk.X)

        # Row 1: Session counts
        row1_frame = ttk.Frame(summary_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row1_frame, text="Total Sessions:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row1_frame, textvariable=self.total_sessions_var, foreground="blue").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1_frame, text="Reviewed:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row1_frame, textvariable=self.reviewed_sessions_var, foreground="green").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1_frame, text="Draft:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row1_frame, textvariable=self.draft_sessions_var, foreground="orange").pack(side=tk.LEFT)

        # Row 2: Status breakdown
        row2_frame = ttk.Frame(summary_frame)
        row2_frame.pack(fill=tk.X, pady=(5, 5))

        ttk.Label(row2_frame, text="Completed:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row2_frame, textvariable=self.completed_sessions_var, foreground="blue").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row2_frame, text="Approved:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row2_frame, textvariable=self.approved_sessions_var, foreground="purple").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row2_frame, text="Rejected:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row2_frame, textvariable=self.rejected_sessions_var, foreground="red").pack(side=tk.LEFT)

        # Row 3: Financial totals
        row3_frame = ttk.Frame(summary_frame)
        row3_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(row3_frame, text="Total System Sales:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row3_frame, textvariable=self.total_system_sales_var, foreground="navy").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row3_frame, text="Total Variance:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row3_frame, textvariable=self.total_variance_var, foreground="red").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row3_frame, text="Total Explained:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
    def _on_search_change(self, event=None) -> None:
        """Handle search input changes."""
        self._load_sessions_list()

    def _on_filter_change(self, event=None) -> None:
        """Handle filter combobox changes."""
        self._load_sessions_list()

    def _on_sort_change(self, event=None) -> None:
        """Handle sort combobox changes."""
        self._load_sessions_list()

    def _on_date_change(self, event=None) -> None:
        """Handle date input changes."""
        self._load_sessions_list()

    def _on_session_double_click(self, event) -> None:
        """Handle double-click on a session to show detailed management dialog."""
        item = self.sessions_tree.identify_row(event.y)
        if not item:
            return

        session_id = self.sessions_tree.item(item)['values'][0]
        self._show_session_details_dialog(session_id)

    def _show_session_details_dialog(self, session_id: int) -> None:
        """Show a beautiful dialog with session details and management options."""
        # Load session data
        session = get_reconciliation_session(session_id)
        if not session:
            messagebox.showerror("Error", "Session not found.")
            return

        # Get reviewed status
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT reviewed FROM reconciliation_sessions WHERE session_id = ?", (session_id,))
        reviewed_row = cursor.fetchone()
        is_reviewed = reviewed_row[0] if reviewed_row else 0
        conn.close()

        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Session {session_id} - Details & Management")
        dialog.geometry("900x700")
        dialog.resizable(True, True)

        # Set the app icon
        set_window_icon(dialog)

        # Set as a normal window with full controls
        dialog.attributes('-toolwindow', False)
        dialog.attributes('-topmost', False)

        # Remove modal behavior to allow full window controls
        # dialog.transient(self)
        # dialog.grab_set()

        # Center the dialog
        dialog.geometry("+{}+{}".format(
            self.winfo_rootx() + self.winfo_width() // 2 - 450,
            self.winfo_rooty() + self.winfo_height() // 2 - 350
        ))

        # Action buttons at the top
        top_buttons_frame = ttk.Frame(dialog)
        top_buttons_frame.pack(fill=tk.X, padx=20, pady=(20, 10))

        # Left side buttons
        left_buttons = ttk.Frame(top_buttons_frame)
        left_buttons.pack(side=tk.LEFT)

        # Mark button (always present)
        is_completed = session.status.lower() == 'completed'
        mark_btn = ttk.Button(left_buttons, text="✅ Mark as Reviewed",
                              command=lambda: self._mark_session_reviewed_from_dialog(session_id, dialog))
        mark_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Approve/Reject (visible next to Mark; disabled until reviewed)
        approve_btn = ttk.Button(left_buttons, text="✅ Approve",
                                 command=lambda: self._approve_session_from_dialog(session_id, dialog))
        approve_btn.pack(side=tk.LEFT, padx=(0, 10))

        reject_btn = ttk.Button(left_buttons, text="❌ Reject",
                                command=lambda: self._reject_session_from_dialog(session_id, dialog))
        reject_btn.pack(side=tk.LEFT, padx=(0, 10))

        # If session isn't completed, disable mark and show explanation
        if not is_completed:
            mark_btn.config(state="disabled")
            ttk.Label(left_buttons, text="Only completed sessions can be reviewed", foreground="red").pack(side=tk.LEFT, padx=(10, 0))

        # Set initial states based on reviewed flag
        if is_reviewed:
            mark_btn.config(text="✅ Reviewed", state="disabled")
            approve_btn.config(state="normal")
            reject_btn.config(state="normal")
        else:
            approve_btn.config(state="disabled")
            reject_btn.config(state="disabled")

        # Store references for updating after marking reviewed
        dialog.mark_button = mark_btn
        dialog.approve_button = approve_btn
        dialog.reject_button = reject_btn
        dialog.left_buttons = left_buttons

        # Right side buttons
        right_buttons = ttk.Frame(top_buttons_frame)
        right_buttons.pack(side=tk.RIGHT)

        ttk.Button(right_buttons, text="🗑️ Delete Session",
                  command=lambda: self._delete_session_from_dialog(session_id, dialog)).pack(side=tk.RIGHT, padx=(10, 0))

        ttk.Button(right_buttons, text="✏️ Edit Session",
                  command=lambda: self._edit_session_from_dialog(session_id, dialog)).pack(side=tk.RIGHT, padx=(10, 0))

        # Main container with scrollbar
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Header section
        header_frame = ttk.LabelFrame(scrollable_frame, text="Session Overview", padding=15)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        # Session info grid
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(fill=tk.X)

        # Row 1
        ttk.Label(info_frame, text="Session ID:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_frame, text=str(session.session_id)).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(info_frame, text="Date:", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_frame, text=session.reconciliation_date).grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        ttk.Label(info_frame, text="Period:", font=("Segoe UI", 10, "bold")).grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_frame, text=session.period_type.title()).grid(row=0, column=5, sticky=tk.W)

        # Row 2
        ttk.Label(info_frame, text="Status:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        status_label = ttk.Label(info_frame, text=session.status.title())
        status_label.grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        # Keep a reference so calling code can update the label after actions
        dialog.status_label = status_label

        # Color code status
        if session.status.lower() == 'completed':
            status_label.config(foreground="green")
        elif session.status.lower() == 'draft':
            status_label.config(foreground="orange")
        elif session.status.lower() == 'rejected':
            status_label.config(foreground="red")

        ttk.Label(info_frame, text="Total System:", font=("Segoe UI", 10, "bold")).grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        ttk.Label(info_frame, text=f"{self.currency_symbol}{sum(entry.system_amount for entry in session.entries):.2f}").grid(row=1, column=3, sticky=tk.W, padx=(0, 20), pady=(10, 0))

        ttk.Label(info_frame, text="Total Variance:", font=("Segoe UI", 10, "bold")).grid(row=1, column=4, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        variance_total = sum(entry.variance for entry in session.entries)
        variance_label = ttk.Label(info_frame, text=f"{self.currency_symbol}{variance_total:.2f}")
        variance_label.grid(row=1, column=5, sticky=tk.W, pady=(10, 0))

        # Color code variance
        if abs(variance_total) < 0.01:
            variance_label.config(foreground="green")
        else:
            variance_label.config(foreground="red")

        # Row 2 - Reviewed
        ttk.Label(info_frame, text="Reviewed:", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        reviewed_label = ttk.Label(info_frame, text="Yes" if is_reviewed else "No")
        reviewed_label.grid(row=2, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        if is_reviewed:
            reviewed_label.config(foreground="green")
        else:
            reviewed_label.config(foreground="red")

        # Store references for updating after marking reviewed
        dialog.reviewed_label = reviewed_label
        dialog.left_buttons = left_buttons

        # Row 3 - Total Explained Variance
        ttk.Label(info_frame, text="Total Explained:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        # Calculate total explained variance
        explained_total = 0.0
        for entry in session.entries:
            explained_total += get_explained_variance_total(session.session_id, entry.payment_method)
        
        explained_label = ttk.Label(info_frame, text=f"{self.currency_symbol}{explained_total:.2f}")
        explained_label.grid(row=2, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        explained_label.config(foreground="blue")  # Blue for explained amounts

        # Entries breakdown section
        entries_frame = ttk.LabelFrame(scrollable_frame, text="Payment Method Breakdown", padding=15)
        entries_frame.pack(fill=tk.X, pady=(0, 20))

        # Create treeview for entries
        columns = ("method", "pos_sales", "opening", "cash_out", "closing", "actual_sales", "variance", "status")
        entries_tree = ttk.Treeview(entries_frame, columns=columns, show='headings', height=8)

        entries_tree.heading("method",       text="Payment Method")
        entries_tree.heading("pos_sales",    text=f"POS Sales ({self.currency_symbol})")
        entries_tree.heading("opening",      text=f"Opening ({self.currency_symbol})")
        entries_tree.heading("cash_out",     text=f"Cash Out ({self.currency_symbol})")
        entries_tree.heading("closing",      text=f"Closing ({self.currency_symbol})")
        entries_tree.heading("actual_sales", text=f"Actual Sales ({self.currency_symbol})")
        entries_tree.heading("variance",     text=f"Variance ({self.currency_symbol})")
        entries_tree.heading("status",       text="Status")

        entries_tree.column("method",       width=120)
        entries_tree.column("pos_sales",    width=90, anchor='e')
        entries_tree.column("opening",      width=90, anchor='e')
        entries_tree.column("cash_out",     width=90, anchor='e')
        entries_tree.column("closing",      width=90, anchor='e')
        entries_tree.column("actual_sales", width=100, anchor='e')
        entries_tree.column("variance",     width=90, anchor='e')
        entries_tree.column("status",       width=100, anchor='center')

        # Populate entries
        for entry in session.entries:
            opening = getattr(entry, 'opening_balance', 0.0)
            cash_out = getattr(entry, 'cash_out', 0.0)
            closing = entry.actual_amount
            actual_sales = closing - opening + cash_out
            status_text = "✓ Reconciled" if abs(entry.variance) < 0.01 else "⚠ Variance"

            entries_tree.insert("", tk.END, values=(
                entry.payment_method,
                f"{entry.system_amount:.2f}",
                f"{opening:.2f}",
                f"{cash_out:.2f}",
                f"{closing:.2f}",
                f"{actual_sales:.2f}",
                f"{entry.variance:.2f}",
                status_text
            ))

        # Add scrollbar
        v_scrollbar = ttk.Scrollbar(entries_frame, orient=tk.VERTICAL, command=entries_tree.yview)
        entries_tree.configure(yscrollcommand=v_scrollbar.set)

        entries_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Explanations section
        explanations_frame = ttk.LabelFrame(scrollable_frame, text="Detailed Explanations", padding=15)
        explanations_frame.pack(fill=tk.X, pady=(0, 20))

        # Get explanations for this session
        explanations = get_reconciliation_explanations(session_id)

        if explanations:
            # Create a frame to hold text widget and scrollbar
            text_frame = ttk.Frame(explanations_frame)
            text_frame.pack(fill=tk.BOTH, expand=True)

            exp_text = tk.Text(text_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)

            # Add scrollbar
            v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=exp_text.yview)
            exp_text.configure(yscrollcommand=v_scrollbar.set)

            exp_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            for exp in explanations:
                exp_text.config(state=tk.NORMAL)
                exp_text.insert(tk.END, f"• {exp['payment_method'] or 'General'}: {exp['explanation']}\n")
                if exp['amount']:
                    exp_text.insert(tk.END, f"  Amount: {self.currency_symbol}{exp['amount']:.2f}\n")
                exp_text.insert(tk.END, "\n")
                exp_text.config(state=tk.DISABLED)
        else:
            ttk.Label(explanations_frame, text="No detailed explanations recorded for this session.").pack()

        # Configure canvas scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _export_session_to_csv_from_dialog(self, session_id: int, dialog: tk.Toplevel) -> None:
        """Export session data to CSV from the dialog."""
        try:
            # Load the session
            session = get_reconciliation_session(session_id)
            if not session:
                messagebox.showerror("Error", "Session not found.")
                return

            # Ask for save location
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title=f"Export Session {session_id}"
            )

            if not filename:
                return

            # Write CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Payment Method", "Opening Balance", "POS Sales",
                                 "Cash Out", "Closing Balance", "Actual Sales",
                                 "Variance", "Explanation"])

                for entry in session.entries:
                    opening = getattr(entry, 'opening_balance', 0.0)
                    cash_out = getattr(entry, 'cash_out', 0.0)
                    actual_sales = entry.actual_amount - opening + cash_out
                    writer.writerow([
                        entry.payment_method,
                        f"{opening:.2f}",
                        f"{entry.system_amount:.2f}",
                        f"{cash_out:.2f}",
                        f"{entry.actual_amount:.2f}",
                        f"{actual_sales:.2f}",
                        f"{entry.variance:.2f}",
                        entry.explanation or ""
                    ])

            messagebox.showinfo("Success", f"Session exported to {filename}")
            dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export session: {str(e)}")

    def _mark_session_reviewed_from_dialog(self, session_id: int, dialog: tk.Toplevel) -> None:
        """Mark session as reviewed from the dialog."""
        try:
            # Verify session is completed before marking
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM reconciliation_sessions WHERE session_id = ?", (session_id,))
            status_row = cursor.fetchone()
            if not status_row or (status_row[0] or '').lower() != 'completed':
                conn.close()
                messagebox.showwarning("Not Allowed", "Only sessions with status 'Completed' can be marked as reviewed.")
                return

            # Update the session status to reviewed (only after validation)
            cursor.execute("""
                UPDATE reconciliation_sessions
                SET reviewed = 1, reviewed_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))

            conn.commit()
            conn.close()

            # Update the UI to enable Approve/Reject and mark the session as reviewed
            try:
                dialog.mark_button.config(text="✅ Reviewed", state="disabled")
                dialog.approve_button.config(state="normal")
                dialog.reject_button.config(state="normal")
                dialog.reviewed_label.config(text="Yes", foreground="green")
            except Exception as e:
                # Log a warning but do NOT close the dialog; keep it open for next steps
                logger.warning(f"Failed to update dialog UI after marking reviewed: {e}")

            # Refresh the sessions list and keep the dialog focused
            self._load_sessions_list()
            try:
                dialog.lift()
                dialog.focus_force()
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark session as reviewed: {str(e)}")

    def _run_db_write_single_query(self, query: str, params: tuple = (), retries: int = 5, delay: float = 0.2) -> None:
        """Run a single write query with retries on SQLITE 'database is locked'."""
        attempt = 0
        while True:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                conn.close()
                return
            except sqlite3.OperationalError as e:
                if 'locked' in str(e).lower() and attempt < retries:
                    attempt += 1
                    time.sleep(delay)
                    continue
                raise

    def _run_db_transaction(self, queries_params: list, retries: int = 5, delay: float = 0.2) -> None:
        """Run multiple queries in a single transaction with retries on database lock."""
        attempt = 0
        while True:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                cursor = conn.cursor()
                for q, p in queries_params:
                    cursor.execute(q, p)
                conn.commit()
                conn.close()
                return
            except sqlite3.OperationalError as e:
                if 'locked' in str(e).lower() and attempt < retries:
                    attempt += 1
                    time.sleep(delay)
                    continue
                raise

    def _approve_session_from_dialog(self, session_id: int, dialog: tk.Toplevel) -> None:
        """Approve session from the dialog."""
        try:
            self._run_db_write_single_query(
                "UPDATE reconciliation_sessions SET status = 'approved' WHERE session_id = ?",
                (session_id,)
            )
            messagebox.showinfo("Success", f"Session {session_id} approved.")
            # dialog.destroy()  # Removed to keep dialog open for other actions
            self._load_sessions_list()
        except sqlite3.IntegrityError as e:
            if 'CHECK constraint failed' in str(e) and 'status' in str(e):
                if messagebox.askyesno("Schema Mismatch",
                                       "Database schema does not allow 'approved' status.\nWould you like to apply pending database migrations now?\n\n(Recommended)"):
                    try:
                        from database.migrations import run_pending_migrations
                        applied = run_pending_migrations()
                        if applied:
                            messagebox.showinfo("Migrations Applied", f"Applied migrations: {', '.join(applied)}. Retrying approve...")
                            self._run_db_write_single_query(
                                "UPDATE reconciliation_sessions SET status = 'approved' WHERE session_id = ?",
                                (session_id,)
                            )
                            messagebox.showinfo("Success", f"Session {session_id} approved.")
                            # dialog.destroy()  # Removed to keep dialog open
                            self._load_sessions_list()
                            return
                        else:
                            messagebox.showwarning("No Migrations", "No pending migrations were found or applied. Please check your database setup.")
                    except Exception as me:
                        messagebox.showerror("Migration Error", f"Failed to apply migrations: {me}")
                        return
                else:
                    messagebox.showerror("Approve Failed", "Cannot set status to 'approved' because the database schema prohibits it. Run pending migrations (see migrations/20260208_add_rejected_status.json) or contact support.")
            else:
                messagebox.showerror("Integrity Error", f"Failed to approve session: {e}")
        except sqlite3.OperationalError as e:
            messagebox.showerror("Database Error", f"Database busy; please try again.\n\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to approve session: {str(e)}")

    def _reject_session_from_dialog(self, session_id: int, dialog: tk.Toplevel) -> None:
        """Reject session from the dialog."""
        try:
            self._run_db_write_single_query(
                "UPDATE reconciliation_sessions SET status = 'rejected' WHERE session_id = ?",
                (session_id,)
            )
            messagebox.showinfo("Success", f"Session {session_id} rejected.")
            # Update dialog UI: keep Reviewed as Yes but mark status as Rejected, and disable approve/reject
            try:
                if hasattr(dialog, 'reviewed_label'):
                    dialog.reviewed_label.config(text="Yes", foreground="green")
                if hasattr(dialog, 'status_label'):
                    dialog.status_label.config(text="Rejected", foreground="red")
                if hasattr(dialog, 'approve_button'):
                    dialog.approve_button.config(state="disabled")
                if hasattr(dialog, 'reject_button'):
                    dialog.reject_button.config(state="disabled")
                if hasattr(dialog, 'mark_button'):
                    dialog.mark_button.config(state="disabled")
                try:
                    dialog.lift()
                    dialog.focus_force()
                except Exception:
                    pass
            except Exception as ui_err:
                logger.warning(f"Failed to update dialog UI after reject: {ui_err}")

            self._load_sessions_list()
        except sqlite3.IntegrityError as e:
            # Likely CHECK constraint failed for status - help the user apply migrations
            if 'CHECK constraint failed' in str(e) and 'status' in str(e):
                if messagebox.askyesno("Schema Mismatch",
                                       "Database schema does not allow 'rejected' status.\nWould you like to apply pending database migrations now?\n\n(Recommended)"):
                    try:
                        from database.migrations import run_pending_migrations
                        applied = run_pending_migrations()
                        if applied:
                            messagebox.showinfo("Migrations Applied", f"Applied migrations: {', '.join(applied)}. Retrying reject...")
                            # Retry
                            self._run_db_write_single_query(
                                "UPDATE reconciliation_sessions SET status = 'rejected' WHERE session_id = ?",
                                (session_id,)
                            )
                            messagebox.showinfo("Success", f"Session {session_id} rejected.")
                            # Update dialog UI: keep Reviewed as Yes but mark status as Rejected, and disable approve/reject
                            try:
                                if hasattr(dialog, 'reviewed_label'):
                                    dialog.reviewed_label.config(text="Yes", foreground="green")
                                if hasattr(dialog, 'status_label'):
                                    dialog.status_label.config(text="Rejected", foreground="red")
                                if hasattr(dialog, 'approve_button'):
                                    dialog.approve_button.config(state="disabled")
                                if hasattr(dialog, 'reject_button'):
                                    dialog.reject_button.config(state="disabled")
                                if hasattr(dialog, 'mark_button'):
                                    dialog.mark_button.config(state="disabled")
                                try:
                                    dialog.lift()
                                    dialog.focus_force()
                                except Exception:
                                    pass
                            except Exception as ui_err:
                                logger.warning(f"Failed to update dialog UI after reject: {ui_err}")

                            self._load_sessions_list()
                            return
                        else:
                            messagebox.showwarning("No Migrations", "No pending migrations were found or applied. Please check your database setup.")
                    except Exception as me:
                        messagebox.showerror("Migration Error", f"Failed to apply migrations: {me}")
                        return
                else:
                    messagebox.showerror("Rejected Failed", "Cannot set status to 'rejected' because the database schema prohibits it. Run pending migrations (see migrations/20260208_add_rejected_status.json) or contact support.")
            else:
                messagebox.showerror("Integrity Error", f"Failed to reject session: {e}")
        except sqlite3.OperationalError as e:
            messagebox.showerror("Database Error", f"Database busy; please try again.\n\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reject session: {str(e)}")

    def _delete_session_from_dialog(self, session_id: int, dialog: tk.Toplevel) -> None:
        """Delete session from the dialog."""
        if not messagebox.askyesno("Confirm Delete",
                                 f"Are you sure you want to delete session {session_id}?\n\nThis action cannot be undone."):
            return

        try:
            # Delete the session
            try:
                queries = [
                    ("DELETE FROM reconciliation_sessions WHERE session_id = ?", (session_id,)),
                    ("DELETE FROM reconciliation_entries WHERE session_id = ?", (session_id,)),
                    ("DELETE FROM reconciliation_explanations WHERE session_id = ?", (session_id,)),
                ]
                self._run_db_transaction(queries)

                messagebox.showinfo("Success", f"Session {session_id} deleted successfully.")
                dialog.destroy()
                self._load_sessions_list()  # Refresh the list
            except sqlite3.OperationalError as e:
                messagebox.showerror("Database Error", f"Database busy; please try again.\n\n{e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete session: {str(e)}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete session: {str(e)}")

    def _edit_session_from_dialog(self, session_id: int, dialog: tk.Toplevel) -> None:
        """Edit session from the dialog - load it for editing."""
        # Check permission to edit reconciliation
        current_username = get_username()
        if not permissions.has_permission(current_username, 'edit_reconciliation'):
            messagebox.showerror("Permission Denied", "You do not have permission to edit reconciliation sessions")
            return
        
        dialog.destroy()
        # Load the session for editing
        self._load_selected_session_by_id(session_id)

    def _load_selected_session_by_id(self, session_id: int) -> None:
        """Load a session by ID for editing."""
        try:
            # Load the session
            session = get_reconciliation_session(session_id)
            if not session:
                messagebox.showerror("Error", "Session not found.")
                return

            # Convert to our UI session format
            self.current_session = ReconciliationSession(
                session_id=session.session_id,
                date=session.reconciliation_date,
                period_type=session.period_type,
                start_date=session.start_date,
                end_date=session.end_date,
                items=[],
                status=session.status,
                created_by=session.reconciled_by or 1,
                created_at=session.reconciled_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                completed_at=session.reconciled_at,
                notes=session.notes,
                explanations_loaded=True  # Will load explanations below
            )

            # Convert entries to items
            for entry in session.entries:
                # For existing sessions, use the saved opening balance, or recalculate if saved is 0
                saved_opening_balance = getattr(entry, 'opening_balance', 0.0)
                if saved_opening_balance == 0.0:
                    # If saved is 0, recalculate from previous closing
                    previous_closing = self._get_previous_closing_balances(session.start_date)
                    opening_balance = previous_closing.get(entry.payment_method, 0.0)
                else:
                    opening_balance = saved_opening_balance
                
                item = ReconciliationItem(
                    payment_method=entry.payment_method,
                    system_amount=entry.system_amount,
                    actual_amount=entry.actual_amount,
                    variance=entry.variance,
                    is_reviewed=getattr(entry, 'is_reviewed', False),
                    notes=entry.explanation if hasattr(entry, 'explanation') else '',
                    opening_balance=opening_balance,  # Use saved or recalculated
                    cash_out=getattr(entry, 'cash_out', 0.0),
                )
                # Update variance with the opening balance
                item.update_variance()
                self.current_session.items.append(item)

            # Load explanations into memory
            self.current_session.explanations = get_variance_explanations(self.current_session)

            # Switch to reconciliation view
            self._switch_view("reconcile")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session: {str(e)}")

    def _build_advanced_tab(self, parent_frame: ttk.Frame) -> None:
        """Build the advanced session management tab."""
        # Sessions list (same as basic tab but for advanced operations)
        list_frame = ttk.LabelFrame(parent_frame, text="Sessions for Advanced Operations", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Treeview for sessions (reuse the same treeview)
        columns = ("session_id", "date", "period", "status", "total_system", "total_variance")
        self.advanced_sessions_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)

        self.advanced_sessions_tree.heading("session_id", text="Session Name")
        self.advanced_sessions_tree.heading("date", text="Date")
        self.advanced_sessions_tree.heading("period", text="Period")
        self.advanced_sessions_tree.heading("status", text="Status")
        self.advanced_sessions_tree.heading("total_system", text=f"System Total ({self.currency_symbol})")
        self.advanced_sessions_tree.heading("total_variance", text=f"Variance ({self.currency_symbol})")

        self.advanced_sessions_tree.column("session_id", width=80, anchor='center')
        self.advanced_sessions_tree.column("date", width=100, anchor='center')
        self.advanced_sessions_tree.column("period", width=100, anchor='center')
        self.advanced_sessions_tree.column("status", width=100, anchor='center')
        self.advanced_sessions_tree.column("total_system", width=120, anchor='e')
        self.advanced_sessions_tree.column("total_variance", width=120, anchor='e')

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.advanced_sessions_tree.yview)
        self.advanced_sessions_tree.configure(yscrollcommand=v_scrollbar.set)

        self.advanced_sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Advanced action buttons
        actions_frame = ttk.Frame(parent_frame)
        actions_frame.pack(fill=tk.X, pady=(10, 0))

        # Store button references for enabling/disabling
        self.advanced_buttons = []

        btn_export = ttk.Button(actions_frame, text="📊 Export to CSV",
                               command=self._export_session_to_csv, state="disabled")
        btn_export.pack(side=tk.LEFT, padx=(0, 10))
        self.advanced_buttons.append(btn_export)

        btn_bulk_delete = ttk.Button(actions_frame, text="🗑️ Bulk Delete",
                                    command=self._bulk_delete_sessions, state="disabled")
        btn_bulk_delete.pack(side=tk.LEFT, padx=(0, 10))
        self.advanced_buttons.append(btn_bulk_delete)

        btn_mark_reviewed = ttk.Button(actions_frame, text="✅ Mark Reviewed",
                                      command=self._mark_session_reviewed, state="disabled")
        btn_mark_reviewed.pack(side=tk.LEFT, padx=(0, 10))
        self.advanced_buttons.append(btn_mark_reviewed)

        btn_filter = ttk.Button(actions_frame, text="🔍 Filter by Status",
                               command=self._filter_sessions_by_status, state="disabled")
        btn_filter.pack(side=tk.LEFT, padx=(0, 10))
        self.advanced_buttons.append(btn_filter)

        # Instructions
        instructions_frame = ttk.LabelFrame(parent_frame, text="Advanced Operations", padding=10)
        instructions_frame.pack(fill=tk.X, pady=(20, 0))

        instructions_text = (
            "• Export to CSV: Export selected session data to a spreadsheet-compatible file\n"
            "• Bulk Delete: Select multiple sessions (Ctrl+Click) and delete them at once\n"
            "• Mark Reviewed: Mark sessions as reviewed for audit trails\n"
            "• Filter by Status: Show only sessions with specific status (Open/Completed/Reviewed)"
        )

        ttk.Label(instructions_frame, text=instructions_text, justify=tk.LEFT).pack(anchor=tk.W)

    def _on_tab_changed(self, event) -> None:
        """Handle tab change events to enable/disable advanced features."""
        tab_control = event.widget
        current_tab = tab_control.select()
        tab_text = tab_control.tab(current_tab, "text")

        if tab_text == "Advanced":
            # Enable advanced buttons and load sessions in advanced tree
            for btn in self.advanced_buttons:
                btn.config(state="normal")
            self._load_advanced_sessions_list()
        else:
            # Disable advanced buttons
            for btn in self.advanced_buttons:
                btn.config(state="disabled")

    def _load_advanced_sessions_list(self) -> None:
        """Load sessions list for the advanced tab."""
        try:
            # Clear existing items
            for item in self.advanced_sessions_tree.get_children():
                self.advanced_sessions_tree.delete(item)

            # Get sessions from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed
                FROM reconciliation_sessions
                ORDER BY reconciliation_date DESC, session_id DESC
                LIMIT 50
            """)

            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed = row

                # Format status with reviewed indicator
                display_status = status.title()
                if reviewed:
                    display_status += " ✓"

                # Format amounts
                system_amt = f"{total_system_sales:.2f}" if total_system_sales else "0.00"
                variance_amt = f"{total_variance:.2f}" if total_variance else "0.00"

                self.advanced_sessions_tree.insert("", tk.END, values=(
                    session_id, reconciliation_date, period_type, display_status, system_amt, variance_amt
                ))

        except Exception as e:
            logger.error(f"Error loading advanced sessions list: {e}")
            messagebox.showerror("Error", f"Failed to load sessions: {str(e)}")

    def _show_reconciliation(self) -> ttk.Frame:
        """Show the reconciliation interface."""
        frame = ttk.Frame(self.content_container)
        # Don't pack here

        if not self.current_session:
            # No session loaded
            ttk.Label(frame, text="No reconciliation session loaded.",
                     font=("Segoe UI", 12)).pack(pady=20)
            ttk.Label(frame, text="Please create a new session or load an existing one.",
                     font=("Segoe UI", 10)).pack(pady=(0, 20))
            ttk.Button(frame, text="Go to Create Session",
                      command=lambda: self._switch_view("create")).pack()
            return frame

        # Session info
        info_frame = ttk.LabelFrame(frame, text="Session Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 20))

        # Format session name with status prefix
        if self.current_session.session_id is None:
            # Unsaved session
            session_name = f"Draft-Unsaved"
        else:
            status_prefix = "Draft" if self.current_session.status.lower() == "draft" else "Completed" if self.current_session.status.lower() == "completed" else self.current_session.status.title()
            session_name = f"{status_prefix}-{self.current_session.session_id}"
        
        ttk.Label(info_frame, text=f"Session: {session_name}").grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Label(info_frame, text=f"Period: {self.current_session.period_type.title()}").grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Label(info_frame, text=f"Date Range: {self.current_session.start_date} to {self.current_session.end_date}").grid(row=0, column=2, sticky=tk.W)

        # Reconciliation table
        table_frame = ttk.LabelFrame(frame, text="Payment Method Reconciliation", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # --- Formula banner ---
        formula_lbl = tk.Label(
            table_frame,
            text="Formula:  Actual Sales = Closing Balance − Opening Balance + Cash Out   |   Variance = Actual Sales − POS Sales",
            font=("Segoe UI", 9), bg="#EBF5FB", fg="#2471A3", anchor="w", padx=6, pady=3
        )
        formula_lbl.pack(fill=tk.X, pady=(0, 8))

        # Treeview columns (includes unexplained & actions)
        columns = ("payment_method", "pos_sales", "opening_bal", "cash_out",
                    "closing_bal", "actual_sales", "variance",
                    "unexplained", "actions", "status")
        # ---------- Scrollable container ----------
        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.recon_tree = ttk.Treeview(tree_container, columns=columns,
                                       show='headings', height=16)

        self.recon_tree.heading("payment_method", text="Payment Method")
        self.recon_tree.heading("pos_sales",       text=f"POS Sales ({self.currency_symbol})")
        self.recon_tree.heading("opening_bal",     text=f"Opening ({self.currency_symbol})")
        self.recon_tree.heading("cash_out",        text=f"Cash Out ({self.currency_symbol})")
        self.recon_tree.heading("closing_bal",     text=f"Closing ({self.currency_symbol})")
        self.recon_tree.heading("actual_sales",    text=f"Actual Sales ({self.currency_symbol})")
        self.recon_tree.heading("variance",        text=f"Variance ({self.currency_symbol})")
        self.recon_tree.heading("unexplained",     text=f"Unexplained ({self.currency_symbol})")
        self.recon_tree.heading("actions",         text="Actions")
        self.recon_tree.heading("status",          text="Status")

        self.recon_tree.column("payment_method", width=130, minwidth=80, anchor='w',      stretch=False)
        self.recon_tree.column("opening_bal",    width=100, minwidth=60, anchor='e',      stretch=False)
        self.recon_tree.column("pos_sales",      width=100, minwidth=60, anchor='e',      stretch=False)
        self.recon_tree.column("cash_out",       width=100, minwidth=60, anchor='e',      stretch=False)
        self.recon_tree.column("closing_bal",    width=100, minwidth=60, anchor='e',      stretch=False)
        self.recon_tree.column("actual_sales",   width=110, minwidth=60, anchor='e',      stretch=False)
        self.recon_tree.column("variance",       width=100, minwidth=60, anchor='e',      stretch=False)
        self.recon_tree.column("unexplained",    width=110, minwidth=60, anchor='e',      stretch=False)
        self.recon_tree.column("actions",        width=70,  minwidth=50, anchor='center', stretch=False)
        self.recon_tree.column("status",         width=130, minwidth=80, anchor='center', stretch=False)

        # Vertical scrollbar
        v_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL,
                                  command=self.recon_tree.yview)
        # Horizontal scrollbar
        h_scroll = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL,
                                  command=self.recon_tree.xview)
        self.recon_tree.configure(yscrollcommand=v_scroll.set,
                                  xscrollcommand=h_scroll.set)

        # Grid layout for tree + scrollbars
        self.recon_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Bind events
        self.recon_tree.bind('<Double-1>', self._on_item_double_click)
        self.recon_tree.bind('<Button-3>', self._on_right_click)  # Right-click for context menu

        # Load session data
        self._load_session_data()

        # Controls
        controls_frame = ttk.Frame(frame)
        controls_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(controls_frame,
                  text="💡 Double-click Opening Balance or Closing Balance to edit  |  Cash Out is read-only (from expenses)  |  Right-click for variance explanations",
                  font=("Segoe UI", 9), foreground="gray").pack(side=tk.LEFT)

        ttk.Button(controls_frame, text="🔄 Refresh Data",
                  command=self._refresh_session_data).pack(side=tk.RIGHT)

        # Totals
        totals_frame = ttk.Frame(frame)
        totals_frame.pack(fill=tk.X, pady=(10, 0))

        self.total_system_var = tk.StringVar(value=f"POS Sales Total: {self.currency_symbol}0.00")
        self.total_actual_var = tk.StringVar(value=f"Actual Sales Total: {self.currency_symbol}0.00")
        self.total_variance_var = tk.StringVar(value=f"Variance Total: {self.currency_symbol}0.00")

        ttk.Label(totals_frame, textvariable=self.total_system_var,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Label(totals_frame, textvariable=self.total_actual_var,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Label(totals_frame, textvariable=self.total_variance_var,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky=tk.W)

        self._update_totals()

    def _on_period_type_change(self, event=None) -> None:
        """Handle period type change."""
        period_type = self.period_type_var.get()
        if period_type == "custom":
            self.custom_date_frame.pack(fill=tk.X, pady=(10, 0))
        else:
            self.custom_date_frame.pack_forget()
            # Auto-calculate dates
            start_date, end_date = calculate_date_range(period_type, self.reference_date_var.get())
            self.start_date_var.set(start_date)
            self.end_date_var.set(end_date)

    def _show_calendar_picker(self) -> None:
        """Show calendar picker for reference date without triggering session list refresh."""
        self._show_calendar_picker_for_field(self.reference_date_var, trigger_update=False)

    def _show_calendar_picker_for_field(self, date_var: tk.StringVar, parent_dialog: Optional[tk.Toplevel] = None, trigger_update: bool = True) -> None:
        """Show calendar picker for a specific date field using tkcalendar.

        Args:
            date_var: StringVar to set when a date is chosen.
            parent_dialog: Optional Toplevel to set as transient parent (improves focus when called from another dialog).
            trigger_update: If True, call `self._load_sessions_list()` after selection (used for session list filters).
        """
        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title("Select Date")
        # Hide initially to prevent resize animation
        dialog.withdraw()
        dialog.resizable(False, False)
        # Use provided parent_dialog for transient if available to keep modality correct
        dialog.transient(parent_dialog if parent_dialog is not None else self.winfo_toplevel())
        dialog.grab_set()

        # Set the app icon
        set_window_icon(dialog)

        # Use system theme styles so the dialog appearance matches the rest of the app

        # Main container
        container = ttk.Frame(dialog, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Current date
        try:
            current_date = parse_date_flexible(date_var.get()).date() if date_var.get() else datetime.now().date()
        except ValueError:
            current_date = datetime.now().date()

        # Calendar widget
        if TKCALENDAR_AVAILABLE:
            # Place calendar inside themed container for consistent styling
            cal = Calendar(container, selectmode='day', year=current_date.year,
                          month=current_date.month, day=current_date.day,
                          date_pattern=get_tkcalendar_date_pattern(),
                          font=("Segoe UI", 10), showweeknumbers=False)
            # Style calendar to match theme
            try:
                # Use default styling to match system theme
                pass
            except Exception:
                # Some tkcalendar versions use different option names; ignore if unavailable
                pass

            cal.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

            def on_date_select():
                selected_date = cal.get_date()
                date_var.set(selected_date)
                dialog.destroy()
                # Only trigger session list refresh when requested
                if trigger_update and hasattr(self, '_load_sessions_list'):
                    self._load_sessions_list()

            # Buttons (use themed container)
            buttons_frame = ttk.Frame(container)
            buttons_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

            ttk.Button(buttons_frame, text="Select Date",
                      command=on_date_select, style="Accent.TButton").pack(side=tk.RIGHT, padx=(10, 0))
            ttk.Button(buttons_frame, text="Today",
                      command=lambda: cal.selection_set(datetime.now().date()), style="TButton").pack(side=tk.RIGHT)
            ttk.Button(buttons_frame, text="Cancel",
                      command=dialog.destroy, style="TButton").pack(side=tk.RIGHT, padx=(0, 10))

            # Bind double-click to select (removed single-click selection to require explicit button press)
            # cal.bind("<<CalendarSelected>>", lambda e: on_date_select())

        else:
            # Fallback to simple date entry if tkcalendar not available
            fallback_container = ttk.Frame(dialog, padding=10)
            fallback_container.pack(fill=tk.BOTH, expand=True)

            ttk.Label(fallback_container, text="tkcalendar not available.\nPlease enter date manually:",
                     font=("Segoe UI", 9)).pack(pady=10)

            date_entry = ttk.Entry(fallback_container, font=("Segoe UI", 12))
            date_entry.insert(0, date_var.get() or format_date(datetime.now()))
            date_entry.pack(pady=(0, 20), padx=10)

            def on_ok():
                date_var.set(date_entry.get())
                dialog.destroy()
                # Only trigger session list refresh when requested
                if trigger_update and hasattr(self, '_load_sessions_list'):
                    self._load_sessions_list()

            buttons_frame = ttk.Frame(fallback_container)
            buttons_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

            ttk.Button(buttons_frame, text="OK", command=on_ok, style="Accent.TButton").pack(side=tk.RIGHT, padx=(10, 0))
            ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy, style="TButton").pack(side=tk.RIGHT)

            date_entry.focus()
            date_entry.bind('<Return>', lambda e: on_ok())

        # Auto-size the dialog to fit its content and center it on the parent
        dialog.update_idletasks()
        req_w = dialog.winfo_reqwidth()
        req_h = dialog.winfo_reqheight()
        final_w = max(req_w + 20, 300)  # Minimum width of 300
        final_h = max(req_h + 20, 250)  # Minimum height of 250
        try:
            dialog.minsize(final_w, final_h)
        except Exception:
            pass
        # Allow resizing if needed for larger content
        try:
            dialog.resizable(True, True)
        except Exception:
            pass

        # Center on the parent window
        parent = parent_dialog if parent_dialog is not None else self.winfo_toplevel()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (final_w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (final_h // 2)
        dialog.geometry(f"{final_w}x{final_h}+{x}+{y}")
        # Show the dialog at its final size without animation
        dialog.deiconify()

    def _create_session(self) -> None:
        """Create a new reconciliation session in memory (not saved to database)."""
        # Check permission to create reconciliation
        current_username = get_username()
        if not permissions.has_permission(current_username, 'create_reconciliation'):
            messagebox.showerror("Permission Denied", "You do not have permission to create reconciliation sessions")
            return
        
        try:
            period_type = self.period_type_var.get()
            reference_date = self.reference_date_var.get()

            if period_type == "custom":
                start_date_display = self.start_date_var.get()
                end_date_display = self.end_date_var.get()
                if not start_date_display or not end_date_display:
                    messagebox.showerror("Error", "Please select start and end dates for custom period.")
                    return
                # Convert display format dates to ISO format for database queries
                start_date = parse_date_flexible(start_date_display).strftime("%Y-%m-%d")
                end_date = parse_date_flexible(end_date_display).strftime("%Y-%m-%d")
            else:
                start_date, end_date = calculate_date_range(period_type, reference_date)

            # Show loading indicator
            self.create_status_var.set("⏳ Loading sales data and creating session...")
            self.update_idletasks()  # Force UI update
            self.config(cursor="wait")
            
            # Create session in memory only (not saved to database)
            self.current_session = self._create_session_in_memory(
                reconciliation_date=reference_date,
                period_type=period_type,
                start_date=start_date,
                end_date=end_date
            )
            
            # Reset cursor
            self.config(cursor="")

            self.create_status_var.set("✓ Session created in memory! Use 'Save as Draft' or 'Complete Reconciliation' to persist.")
            self._switch_view("reconcile")

        except Exception as e:
            self.config(cursor="")  # Reset cursor on error
            messagebox.showerror("Error", f"Failed to create session: {str(e)}")
            self.create_status_var.set(f"✗ Error: {str(e)}")

    def _create_session_in_memory(self, reconciliation_date: str, period_type: str,
                                 start_date: str, end_date: str) -> ReconciliationSession:
        """Create a reconciliation session object in memory without saving to database.

        System amount = POS sales for the period.
        Opening balance = previous session's closing balance (actual_amount).
        """
        # Get POS sales for the period (this is the system amount)
        sales_data = get_sales_by_payment_method_for_period(start_date, end_date)
        # Build lookup: payment_method → total_sales
        sales_lookup: dict = {}
        for row in sales_data:
            sales_lookup[row['payment_method']] = float(row['total_sales'])

        # Also include external-account methods (so they always appear)
        from modules.external_accounts import account_manager
        account_balances = account_manager.get_balances_by_payment_method()
        all_methods = set(sales_lookup.keys()) | set(account_balances.keys())

        # Fetch previous session's closing balances for opening
        previous_closing = self._get_previous_closing_balances(start_date)

        # Create entries
        entries = []
        for pm in sorted(all_methods):
            system_amount = sales_lookup.get(pm, 0.0)
            opening = previous_closing.get(pm, 0.0)

            # Auto-populate cash_out from recorded expenses for this period
            from modules.expenses import get_expenses_total_for_period
            cash_out = get_expenses_total_for_period(start_date, end_date, payment_method=pm)

            item = ReconciliationItem(
                payment_method=pm,
                system_amount=system_amount,
                actual_amount=0.0,
                opening_balance=opening,
                cash_out=cash_out,
                notes=""
            )
            item.update_variance()
            entries.append(item)

        # Create session object
        session = ReconciliationSession(
            session_id=None,  # Will be set when saved
            date=reconciliation_date,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            items=entries,
            status="draft",
            created_by=self.user_id,
            created_at=datetime.now().isoformat(),
            completed_at=None,
            notes=""
        )

        return session

    def _get_previous_closing_balances(self, before_date: str) -> dict:
        """Return {payment_method: closing_balance} from the most recent
        session whose end_date is before *before_date*."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.session_id
                FROM reconciliation_sessions s
                WHERE s.end_date < ?
                ORDER BY s.end_date DESC, s.session_id DESC
                LIMIT 1
            """, (before_date,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {}
            prev_id = row[0]
            cursor.execute("""
                SELECT payment_method, actual_amount
                FROM reconciliation_entries
                WHERE session_id = ?
            """, (prev_id,))
            result = {r[0]: r[1] for r in cursor.fetchall()}
            conn.close()
            return result
        except Exception:
            return {}

    def _load_sessions_list(self) -> None:
        """Load the list of reconciliation sessions with search, filter, and sort options."""
        try:
            # Clear existing items
            for item in self.sessions_tree.get_children():
                self.sessions_tree.delete(item)

            # Build query with filters
            query = """
                SELECT session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed
                FROM reconciliation_sessions
                WHERE 1=1
            """
            params = []

            # Search filter
            search_term = self.search_var.get().strip()
            if search_term:
                query += " AND (session_id LIKE ? OR reconciliation_date LIKE ? OR period_type LIKE ? OR status LIKE ?)"
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

            # Status filter
            status_filter = self.status_filter_var.get()
            if status_filter != "All":
                if status_filter == "Reviewed":
                    query += " AND reviewed = 1"
                else:
                    query += " AND status = ?"
                    params.append(status_filter.lower())

            # Period filter
            period_filter = self.period_filter_var.get()
            if period_filter != "All":
                query += " AND period_type = ?"
                params.append(period_filter.lower())

            # Date range filter
            from_date = self.from_date_var.get().strip()
            to_date = self.to_date_var.get().strip()
            if from_date:
                query += " AND reconciliation_date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND reconciliation_date <= ?"
                params.append(to_date)

            # Sort options
            sort_option = self.sort_var.get()
            if sort_option == "Date":
                query += " ORDER BY reconciliation_date DESC, session_id DESC"
            elif sort_option == "Session ID":
                query += " ORDER BY session_id DESC"
            elif sort_option == "Status":
                query += " ORDER BY status ASC, reconciliation_date DESC"
            elif sort_option == "Total Variance":
                query += " ORDER BY ABS(total_variance) DESC, reconciliation_date DESC"

            # Execute query
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Update session count
            total_sessions = len(rows)
            self.session_count_var.set(f"Total: {total_sessions} sessions")

            # Process rows (limit display for performance, but show all in count)
            display_limit = 200  # Show up to 200 rows for performance
            displayed_rows = rows[:display_limit]

            for row in displayed_rows:
                session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed = row

                # Calculate total explained variance for this session
                explained_total = 0.0
                try:
                    cursor2 = conn.cursor()
                    cursor2.execute("SELECT DISTINCT payment_method FROM reconciliation_entries WHERE session_id = ?", (session_id,))
                    payment_methods = [row[0] for row in cursor2.fetchall()]

                    # Calculate explained variance for each payment method
                    for pm in payment_methods:
                        explained_total += get_explained_variance_total(session_id, pm)
                except Exception as e:
                    logger.warning(f"Error calculating explained variance for session {session_id}: {e}")
                    explained_total = 0.0

                # Format status with reviewed indicator
                display_status = status.title()
                if reviewed:
                    display_status += " ✓"

                # Format amounts
                system_amt = f"{total_system_sales:.2f}" if total_system_sales else "0.00"
                variance_amt = f"{total_variance:.2f}" if total_variance else "0.00"
                explained_amt = f"{explained_total:.2f}"

                reviewed_text = "Yes" if reviewed else "No"

                self.sessions_tree.insert("", tk.END, values=(
                    session_id, reconciliation_date, period_type.title(), display_status,
                    system_amt, variance_amt, explained_amt, reviewed_text
                ))

            conn.close()

            # Calculate summary counts from the filtered results
            reviewed_count = sum(1 for row in rows if row[6] == 1)
            draft_count = sum(1 for row in rows if row[3].lower() == 'draft')
            completed_count = sum(1 for row in rows if row[3].lower() == 'completed')
            approved_count = sum(1 for row in rows if row[3].lower() == 'approved')
            rejected_count = sum(1 for row in rows if row[3].lower() == 'rejected')
            total_system = sum(row[4] for row in rows if row[4])
            total_variance = sum(row[5] for row in rows if row[5])

            # Update summary variables
            self.total_sessions_var.set(str(total_sessions))
            self.reviewed_sessions_var.set(str(reviewed_count))
            self.draft_sessions_var.set(str(draft_count))
            self.completed_sessions_var.set(str(completed_count))
            self.approved_sessions_var.set(str(approved_count))
            self.rejected_sessions_var.set(str(rejected_count))
            self.total_system_sales_var.set(f"{self.currency_symbol}{total_system:.2f}")
            self.total_variance_var.set(f"{self.currency_symbol}{total_variance:.2f}")
            # Note: total_explained is calculated per row, so sum them up approximately
            total_explained = sum(float(self.sessions_tree.item(item)['values'][6]) for item in self.sessions_tree.get_children() if self.sessions_tree.item(item)['values'][6])
            self.total_explained_var.set(f"{self.currency_symbol}{total_explained:.2f}")

            # Show message if limited
            if total_sessions > display_limit:
                self.session_count_var.set(f"Showing {display_limit} of {total_sessions} sessions (use search to filter)")

        except Exception as e:
            logger.error(f"Error loading sessions list: {e}")
            messagebox.showerror("Error", f"Failed to load sessions: {str(e)}")

    def _update_session_summary(self, sessions_data: list) -> None:
        """Update the session summary footer with totals from the provided session data.

        This method is defensive: it tolerates None values and errors in individual
        rows so the footer always shows meaningful totals instead of being left
        empty when the DB contains unexpected or incomplete rows.
        """
        try:
            total_sessions = len(sessions_data)
            reviewed_count = 0
            draft_count = 0
            completed_count = 0
            approved_count = 0
            total_system_sales = 0.0
            total_variance = 0.0
            total_explained = 0.0

            # Reuse one DB connection for explained calculations (faster)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Process each session defensively
            for row in sessions_data:
                try:
                    # Unpack with safe defaults if some columns are missing
                    session_id = row[0]
                    reconciliation_date = row[1] if len(row) > 1 else ''
                    period_type = row[2] if len(row) > 2 else ''
                    status = (row[3] or '') if len(row) > 3 else ''
                    system_sales = float(row[4]) if len(row) > 4 and row[4] is not None else 0.0
                    variance = float(row[5]) if len(row) > 5 and row[5] is not None else 0.0
                    reviewed = bool(row[6]) if len(row) > 6 and row[6] else False

                    # Count by status
                    if reviewed:
                        reviewed_count += 1

                    status_lower = status.lower()
                    if status_lower == 'draft':
                        draft_count += 1
                    elif status_lower == 'completed':
                        completed_count += 1
                    elif status_lower == 'approved':
                        approved_count += 1

                    # Sum financial values
                    total_system_sales += system_sales
                    total_variance += variance

                    # Calculate explained variance for this session
                    explained_total = 0.0
                    try:
                        cursor.execute("SELECT DISTINCT payment_method FROM reconciliation_entries WHERE session_id = ?", (session_id,))
                        payment_methods = [r[0] for r in cursor.fetchall()]
                        for pm in payment_methods:
                            explained_total += get_explained_variance_total(session_id, pm)
                    except Exception as e:
                        logger.warning(f"Error calculating explained variance for session {session_id}: {e}")

                    total_explained += explained_total

                except Exception as row_err:
                    # Log and continue - a bad row should not blank the whole footer
                    logger.warning(f"Skipping malformed session row during summary calc: {row_err}")
                    continue

            conn.close()

            # Update summary variables
            self.total_sessions_var.set(str(total_sessions))
            self.reviewed_sessions_var.set(str(reviewed_count))
            self.draft_sessions_var.set(str(draft_count))
            self.completed_sessions_var.set(str(completed_count))
            self.approved_sessions_var.set(str(approved_count))
            self.total_system_sales_var.set(f"{self.currency_symbol}{total_system_sales:.2f}")
            self.total_variance_var.set(f"{self.currency_symbol}{total_variance:.2f}")
            self.total_explained_var.set(f"{self.currency_symbol}{total_explained:.2f}")

        except Exception as e:
            logger.error(f"Error updating session summary: {e}")
            # Set defaults on error
            self.total_sessions_var.set("0")
            self.reviewed_sessions_var.set("0")
            self.draft_sessions_var.set("0")
            self.completed_sessions_var.set("0")
            self.approved_sessions_var.set("0")
            self.total_system_sales_var.set(f"{self.currency_symbol}0.00")
            self.total_variance_var.set(f"{self.currency_symbol}0.00")
    def _on_search_change(self, event=None) -> None:
        """Handle search input changes."""
        self._load_sessions_list()

    def _on_date_change(self, event=None) -> None:
        """Handle date input changes."""
        self._load_sessions_list()

    def _on_quick_date_change(self, event=None) -> None:
        """Handle quick date range selection changes."""
        selected_range = self.quick_date_var.get()

        # If user selected Custom, open the custom date dialog
        if selected_range == "Custom":
            # Open dialog where user can pick custom From/To dates
            self._show_custom_date_dialog()
            return

        # Map selection to days
        days_map = {
            "7 Days": 7,
            "14 Days": 14,
            "30 Days": 30,
            "90 Days": 90
        }

        days = days_map.get(selected_range, 30)  # Default to 30 days

        today = datetime.now().date()
        start_date = today - timedelta(days=days)

        self.from_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.to_date_var.set(today.strftime("%Y-%m-%d"))
        self._load_sessions_list()

    def _show_custom_date_dialog(self) -> None:
        """Show a dialog for setting custom date ranges."""
        dialog = tk.Toplevel(self)
        dialog.title("Custom Date Range")
        dialog.geometry("400x200")
        # Hide initially to prevent resize animation
        dialog.withdraw()
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        set_window_icon(dialog)
        # Use system theme styles so the dialog appearance matches the rest of the app

        # Style configuration - keep minimal customizations and reuse the app's theme
        style = ttk.Style(dialog)
        style.configure("DialogTitle.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("DialogHint.TLabel", font=("Segoe UI", 9), foreground="#6B6B6B")
        style.configure("Dialog.TEntry", font=("Segoe UI", 10))
        # Use Accent.TButton for primary actions to align with main UI styling

        # Main container
        container = ttk.Frame(dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(container, text="Select Custom Date Range", style="DialogTitle.TLabel").pack(pady=(0, 5))
        ttk.Label(container, text="Enter dates in YYYY-MM-DD format", style="DialogHint.TLabel").pack(pady=(0, 15))

        # Date fields frame
        fields_frame = ttk.Frame(container)
        fields_frame.pack(fill=tk.X, pady=(0, 20))

        # From date
        from_frame = ttk.Frame(fields_frame)
        from_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(from_frame, text="From:", style="DialogHint.TLabel", width=8, anchor="w").pack(side=tk.LEFT)
        from_var = tk.StringVar(value=self.from_date_var.get() or "")
        from_entry = ttk.Entry(from_frame, textvariable=from_var, width=15, style="Dialog.TEntry")
        from_entry.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(from_frame, text="📅", width=3, command=lambda: self._show_calendar_picker_for_field(from_var, parent_dialog=dialog, trigger_update=False)).pack(side=tk.LEFT)

        # To date
        to_frame = ttk.Frame(fields_frame)
        to_frame.pack(fill=tk.X)
        ttk.Label(to_frame, text="To:", style="DialogHint.TLabel", width=8, anchor="w").pack(side=tk.LEFT)
        to_var = tk.StringVar(value=self.to_date_var.get() or "")
        to_entry = ttk.Entry(to_frame, textvariable=to_var, width=15, style="Dialog.TEntry")
        to_entry.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(to_frame, text="📅", width=3, command=lambda: self._show_calendar_picker_for_field(to_var, parent_dialog=dialog, trigger_update=False)).pack(side=tk.LEFT)

        # Focus and navigation
        from_entry.focus()
        from_entry.bind('<Return>', lambda e: to_entry.focus())
        to_entry.bind('<Return>', lambda e: apply_range())

        def apply_range():
            from_date = from_var.get().strip()
            to_date = to_var.get().strip()

            if not from_date or not to_date:
                messagebox.showerror("Error", "Please enter both From and To dates.")
                return

            try:
                from_dt = parse_date_flexible(from_date).date()
                to_dt = parse_date_flexible(to_date).date()
                if from_dt > to_dt:
                    messagebox.showerror("Error", "From date cannot be after To date.")
                    return
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
                return

            # Mark quick range as Custom and apply the selected custom dates
            self.quick_date_var.set("Custom")
            self.from_date_var.set(from_date)
            self.to_date_var.set(to_date)
            dialog.destroy()
            self._load_sessions_list()

        def clear_dates():
            from_var.set("")
            to_var.set("")

        def cancel():
            dialog.destroy()

        # Keyboard bindings
        dialog.bind('<Return>', lambda e: apply_range())
        dialog.bind('<Escape>', lambda e: cancel())

        # Buttons frame
        buttons_frame = ttk.Frame(container)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        # Place Clear to the left and Cancel/Apply to the right with a spacer in between
        ttk.Button(buttons_frame, text="Clear", command=clear_dates, style="TButton").pack(side=tk.LEFT)
        spacer = ttk.Frame(buttons_frame)
        spacer.pack(side=tk.LEFT, expand=True)
        ttk.Button(buttons_frame, text="Cancel", command=cancel, style="TButton").pack(side=tk.RIGHT)
        ttk.Button(buttons_frame, text="Apply", command=apply_range, style="Accent.TButton").pack(side=tk.RIGHT, padx=(10, 0))

        # Compute a sensible minimum size so all content (including buttons) is visible,
        # then center the dialog on the parent window and allow resizing if needed.
        dialog.update_idletasks()
        req_w = dialog.winfo_reqwidth()
        req_h = dialog.winfo_reqheight()
        final_w = max(req_w + 20, 360)
        final_h = max(req_h + 20, 140)
        try:
            dialog.minsize(final_w, final_h)
        except Exception:
            # Fall back silently if minsize isn't supported on the platform
            pass
        # Allow user to resize if they need more space
        try:
            dialog.resizable(True, True)
        except Exception:
            pass

        x = self.winfo_rootx() + (self.winfo_width() // 2) - (final_w // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (final_h // 2)
        dialog.geometry(f"{final_w}x{final_h}+{x}+{y}")
        # Show the dialog at its final size without animation
        dialog.deiconify()

    def _load_selected_session(self) -> None:
        """Load the selected session."""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a session to load.")
            return

        session_id = self.sessions_tree.item(selection[0])['values'][0]
        
        # Use the proper conversion method
        self._load_selected_session_by_id(session_id)

    def _delete_selected_session(self) -> None:
        """Delete the selected session."""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a session to delete.")
            return

        session_id = self.sessions_tree.item(selection[0])['values'][0]

        if not messagebox.askyesno("Confirm Delete",
                                  f"Are you sure you want to delete session {session_id}?\n\nThis action cannot be undone."):
            return

        try:
            delete_reconciliation_session(session_id)
            self._load_sessions_list()
            messagebox.showinfo("Success", f"Session {session_id} deleted successfully.")

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            messagebox.showerror("Error", f"Failed to delete session: {str(e)}")

    def _load_session(self, session_id: int) -> None:
        """Load a reconciliation session."""
        try:
            session = get_reconciliation_session(session_id)
            if session:
                # Convert to our UI session format
                self.current_session = ReconciliationSession(
                    session_id=session.session_id,
                    date=session.reconciliation_date,
                    period_type=session.period_type,
                    start_date=session.start_date,
                    end_date=session.end_date,
                    items=[],
                    status=session.status,
                    created_by=session.reconciled_by or 1,
                    created_at=session.reconciled_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    completed_at=session.reconciled_at,
                    notes=session.notes,
                    explanations_loaded=True  # Will load explanations below
                )

                # Convert entries to items
                for entry in session.entries:
                    item = ReconciliationItem(
                        payment_method=entry.payment_method,
                        system_amount=entry.system_amount,
                        actual_amount=entry.actual_amount,
                        variance=entry.variance,
                        is_reviewed=getattr(entry, 'is_reviewed', False),
                        notes=entry.explanation if hasattr(entry, 'explanation') else '',
                        opening_balance=getattr(entry, 'opening_balance', 0.0),
                        cash_out=getattr(entry, 'cash_out', 0.0),
                    )
                    self.current_session.items.append(item)

                # Load explanations into memory
                self.current_session.explanations = get_variance_explanations(self.current_session)

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            messagebox.showerror("Error", f"Failed to load session: {str(e)}")

        return frame

    def _load_session_data(self) -> None:
        """Load session data into the treeview (new opening/closing layout)."""
        if not self.current_session:
            return

        # Clear existing items
        for item in self.recon_tree.get_children():
            self.recon_tree.delete(item)

        # Add items
        for item in self.current_session.items:
            opening  = getattr(item, 'opening_balance', 0.0)
            # Always fetch cash_out from expenses for the current period
            from modules.expenses import get_expenses_total_for_period
            cash_out = get_expenses_total_for_period(
                self.current_session.start_date, 
                self.current_session.end_date, 
                payment_method=item.payment_method
            )
            closing  = item.actual_amount  # closing balance
            actual_sales = closing - opening + cash_out
            variance = actual_sales - item.system_amount

            # Update the item's cash_out and variance in the session object
            item.cash_out = cash_out
            item.variance = variance

            # Unexplained variance (total variance minus explained)
            unexplained = get_unexplained_variance(self.current_session, item.payment_method)
            explanations = get_variance_explanations(self.current_session, item.payment_method)

            # Actions & status
            if abs(variance) < 0.01:
                status = "✓ Reconciled"
                actions = "✓"
            elif explanations and abs(unexplained) < 0.01:
                status = "✓ Fully Explained"
                actions = "📝"
            else:
                status = f"⚠ {self.currency_symbol}{variance:+,.2f}"
                actions = "📝"

            self.recon_tree.insert("", tk.END, values=(
                item.payment_method,
                f"{self.currency_symbol}{item.system_amount:,.2f}",
                f"{self.currency_symbol}{opening:,.2f}",
                f"{self.currency_symbol}{cash_out:,.2f}",
                f"{self.currency_symbol}{closing:,.2f}",
                f"{self.currency_symbol}{actual_sales:,.2f}",
                f"{self.currency_symbol}{variance:,.2f}",
                f"{self.currency_symbol}{unexplained:,.2f}",
                actions,
                status
            ))

        # Auto-fit columns to content
        self._autofit_columns()

    def _autofit_columns(self) -> None:
        """Auto-fit every column width to the widest of header text or cell data."""
        tree = self.recon_tree
        measure_font = tkFont.Font(family="Segoe UI", size=10)
        heading_font = tkFont.Font(family="Segoe UI", size=10, weight="bold")
        padding = 36  # extra pixels for cell padding + sort arrow + borders

        for col in tree['columns']:
            # Start with header width
            header_text = tree.heading(col, 'text')
            max_w = heading_font.measure(header_text) + padding

            # Measure every row's value in this column
            for iid in tree.get_children():
                cell_text = str(tree.set(iid, col))
                cell_w = measure_font.measure(cell_text) + padding
                if cell_w > max_w:
                    max_w = cell_w

            tree.column(col, width=max_w, minwidth=max_w)

    def _on_item_double_click(self, event) -> None:
        """Handle double-click on reconciliation item for inline editing.

        Column indices (0-based):
          0 = Payment Method (read-only)
          1 = POS Sales          (read-only)
          2 = Opening Balance   ← editable
          3 = Cash Out           (read-only - auto from expenses)
          4 = Closing Balance    ← editable
          5 = Actual Sales       (calculated)
          6 = Variance           → click to open explanation dialog
          7 = Unexplained        (calculated)
          8 = Actions            → click to open explanation dialog
          9 = Status             (read-only)
        """
        region = self.recon_tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.recon_tree.identify_column(event.x)
        item_id = self.recon_tree.identify_row(event.y)
        if not item_id:
            return

        col_idx = int(column[1:]) - 1  # #1 → 0, etc.

        # Editable columns (cash_out is now read-only)
        if col_idx in (2, 4):
            self._edit_cell_inline(item_id, col_idx)
        # Explanation columns (variance, actions)
        elif col_idx in (6, 8):
            payment_method = self.recon_tree.set(item_id, "payment_method")
            self._show_variance_explanation_dialog(payment_method)

    def _edit_cell_inline(self, item_id: str, col_idx: int) -> None:
        """Edit a cell inline in the table.

        col_idx mapping:
          2 = opening_bal
          4 = closing_bal  (actual_amount)
        """
        col_name = self.recon_tree['columns'][col_idx]
        current_value = self.recon_tree.set(item_id, col_name)

        # Get cell position
        x, y, width, height = self.recon_tree.bbox(item_id, col_idx)

        # Create entry widget
        entry = ttk.Entry(self.recon_tree, justify='right', font=("Segoe UI", 9))
        clean_value = current_value.replace(self.currency_symbol, '').replace(',', '').strip()
        entry.insert(0, clean_value)
        entry.select_range(0, tk.END)
        entry.focus()
        entry.place(x=x, y=y, width=width, height=height)

        def save_edit():
            try:
                new_value = entry.get().strip()
                num_value = float(new_value) if new_value else 0.0

                # Update display
                display_value = f"{self.currency_symbol}{num_value:,.2f}"
                self.recon_tree.set(item_id, col_name, display_value)

                # Update the session data
                payment_method = self.recon_tree.set(item_id, "payment_method")
                if self.current_session:
                    for item in self.current_session.items:
                        if item.payment_method == payment_method:
                            if col_idx == 2:    # opening_bal
                                item.opening_balance = num_value
                            elif col_idx == 3:  # cash_out
                                item.cash_out = num_value
                            elif col_idx == 4:  # closing_bal
                                item.actual_amount = num_value
                            item.update_variance()
                            break

                    # Only update database if session is already saved
                    if self.current_session.session_id is not None:
                        update_reconciliation_entry(
                            self.current_session.session_id,
                            payment_method,
                            item.actual_amount,
                            ""
                        )
                        # Persist opening/cash_out via direct DB update
                        self._persist_entry_extras(
                            self.current_session.session_id, payment_method,
                            item.opening_balance, item.cash_out, item.variance
                        )

                # Refresh calculated columns for this row
                self._update_row_calculated(item_id)
                self._update_totals()

            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number.")
            finally:
                entry.destroy()

        def cancel_edit():
            entry.destroy()

        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: cancel_edit())
        entry.bind('<FocusOut>', lambda e: save_edit())

    def _persist_entry_extras(self, session_id: int, payment_method: str,
                              opening_balance: float, cash_out: float,
                              variance: float) -> None:
        """Persist opening_balance, cash_out, and recalculated variance to DB."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                UPDATE reconciliation_entries
                SET opening_balance = ?, cash_out = ?, variance = ?
                WHERE session_id = ? AND payment_method = ?
            """, (opening_balance, cash_out, variance, session_id, payment_method))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to persist entry extras: {e}")

    def _update_row_calculated(self, item_id: str) -> None:
        """Recalculate Actual Sales, Variance, Unexplained, Actions, Status for a row."""
        try:
            payment_method = self.recon_tree.set(item_id, "payment_method")

            def _parse(col: str) -> float:
                return float(self.recon_tree.set(item_id, col)
                             .replace(self.currency_symbol, '').replace(',', '').strip())

            opening  = _parse("opening_bal")
            pos_sales = _parse("pos_sales")
            cash_out = _parse("cash_out")
            closing  = _parse("closing_bal")

            actual_sales = closing - opening + cash_out
            variance = actual_sales - pos_sales

            self.recon_tree.set(item_id, "actual_sales", f"{self.currency_symbol}{actual_sales:,.2f}")
            self.recon_tree.set(item_id, "variance", f"{self.currency_symbol}{variance:,.2f}")

            # Unexplained & actions
            unexplained = get_unexplained_variance(self.current_session, payment_method)
            explanations = get_variance_explanations(self.current_session, payment_method)
            self.recon_tree.set(item_id, "unexplained", f"{self.currency_symbol}{unexplained:,.2f}")

            if abs(variance) < 0.01:
                self.recon_tree.set(item_id, "status", "✓ Reconciled")
                self.recon_tree.set(item_id, "actions", "✓")
            elif explanations and abs(unexplained) < 0.01:
                self.recon_tree.set(item_id, "status", "✓ Fully Explained")
                self.recon_tree.set(item_id, "actions", "📝")
            else:
                self.recon_tree.set(item_id, "status", f"⚠ {self.currency_symbol}{variance:+,.2f}")
                self.recon_tree.set(item_id, "actions", "📝")

        except (ValueError, TypeError):
            self.recon_tree.set(item_id, "actual_sales", f"{self.currency_symbol}0.00")
            self.recon_tree.set(item_id, "variance", f"{self.currency_symbol}0.00")
            self.recon_tree.set(item_id, "status", "⚠")

    def _add_explanation_for_selected(self) -> None:
        """Add explanation for selected item."""
        selection = self.recon_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a payment method to add explanation.")
            return

        item_id = selection[0]
        payment_method = self.recon_tree.set(item_id, "payment_method")

        # Find the item
        if not self.current_session:
            return

        for item in self.current_session.items:
            if item.payment_method == payment_method:
                self._edit_actual_amount(item_id)  # Reuse the edit dialog
                break

    def _update_totals(self) -> None:
        """Update the totals display."""
        if not self.current_session:
            return

        total_pos_sales = sum(item.system_amount for item in self.current_session.items)
        total_actual_sales = sum(item.actual_sales for item in self.current_session.items)
        total_variance = sum(item.variance for item in self.current_session.items)

        self.total_system_var.set(f"POS Sales Total: {self.currency_symbol}{total_pos_sales:,.2f}")
        self.total_actual_var.set(f"Actual Sales Total: {self.currency_symbol}{total_actual_sales:,.2f}")
        self.total_variance_var.set(f"Variance Total: {self.currency_symbol}{total_variance:,.2f}")

    def _save_session(self) -> None:
        """Save the manually entered reconciliation data to the payment table."""
        if not self.current_session or not self.current_session.session_id:
            messagebox.showwarning("No Session", "No active reconciliation session to save.")
            return

        # Check permission to edit reconciliation
        current_username = get_username()
        if not permissions.has_permission(current_username, 'edit_reconciliation'):
            messagebox.showerror("Permission Denied", "You do not have permission to edit reconciliation sessions")
            return

        try:
            # Update only the manually entered data in the reconciliation_entries table
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for item in self.current_session.items:
                    cursor.execute("""
                        UPDATE reconciliation_entries
                        SET actual_amount = ?, opening_balance = ?
                        WHERE session_id = ? AND payment_method = ?
                    """, (
                        item.actual_amount,
                        getattr(item, 'opening_balance', 0.0),
                        self.current_session.session_id,
                        item.payment_method
                    ))
                conn.commit()

            # Refresh the UI to show updated calculations
            self._load_session_data()
            self._update_totals()
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def _show_variance_explanation_dialog(self, payment_method: str) -> None:
        """Show the variance explanation dialog for a payment method."""
        if not self.current_session:
            return

        # Get current variance and explanations
        variance = None
        for item in self.current_session.items:
            if item.payment_method == payment_method:
                variance = item.variance
                break

        if variance is None:
            return

        explanations = get_variance_explanations(self.current_session, payment_method)

        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Variance Explanations - {payment_method}")
        dialog.geometry("700x500")
        dialog.resizable(True, True)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Set the app icon
        set_window_icon(dialog)

        # Title and variance info
        title_frame = ttk.Frame(dialog, padding=10)
        title_frame.pack(fill=tk.X)

        ttk.Label(title_frame, text=f"Payment Method: {payment_method}",
                 font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(title_frame, text=f"Total Variance: {self.currency_symbol}{variance:,.2f}",
                 font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(5, 0))

        # Explanations table
        table_frame = ttk.LabelFrame(dialog, text="Variance Explanations", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Treeview for explanations - store explanation_id in a hidden column
        columns = ("explanation", "amount", "status", "expl_id")
        expl_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=8)

        expl_tree.heading("explanation", text="Explanation")
        expl_tree.heading("amount", text=f"Amount ({self.currency_symbol})")
        expl_tree.heading("status", text="Status")
        expl_tree.heading("expl_id", text="")  # Hidden column for ID

        expl_tree.column("explanation", width=300, anchor='w')
        expl_tree.column("amount", width=120, anchor='e')
        expl_tree.column("status", width=100, anchor='center')
        expl_tree.column("expl_id", width=0, stretch=False)  # Hidden column

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=expl_tree.yview)
        expl_tree.configure(yscrollcommand=v_scrollbar.set)

        expl_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load existing explanations
        for expl in explanations:
            expl_tree.insert("", tk.END, values=(
                expl.explanation,
                f"{self.currency_symbol}{expl.amount:,.2f}",
                "✓ Explained",
                expl.explanation_id  # Hidden ID column
            ), tags=("explained",))

        # Add unexplained variance row
        unexplained = get_unexplained_variance(self.current_session, payment_method)
        if abs(unexplained) >= 0.01:
            expl_tree.insert("", tk.END, values=(
                "Unexplained",
                f"{self.currency_symbol}{unexplained:,.2f}",
                "⚠ Pending",
                ""  # No ID for unexplained row
            ), tags=("unexplained",))

        # Controls
        controls_frame = ttk.Frame(dialog, padding=10)
        controls_frame.pack(fill=tk.X)

        ttk.Button(controls_frame, text="Add Explanation",
                  command=lambda: self._add_variance_explanation(dialog, expl_tree, payment_method, update_status)).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(controls_frame, text="Edit Selected",
                  command=lambda: self._edit_selected_explanation(expl_tree, payment_method, update_status)).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(controls_frame, text="Delete Selected",
                  command=lambda: self._delete_selected_explanation(expl_tree, payment_method, update_status)).pack(side=tk.LEFT, padx=(0, 10))

        # Save button - always show to allow updating main table after explanation changes
        ttk.Button(controls_frame, text="💾 Save & Continue",
                  command=lambda: self._save_and_update_main_table(dialog, payment_method)).pack(side=tk.LEFT, padx=(0, 10))

        # Close button
        ttk.Button(controls_frame, text="Close",
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=(10, 0))

        # Status frame - separate row for better visibility
        status_frame = ttk.Frame(dialog, padding=(10, 5))
        status_frame.pack(fill=tk.X)

        # Status label with full width
        explained_total = get_explained_variance_total(self.current_session, payment_method)
        status_text = f"Explained: {self.currency_symbol}{explained_total:,.2f}  |  Unexplained: {self.currency_symbol}{unexplained:,.2f}"
        status_label = ttk.Label(status_frame, text=status_text, font=("Segoe UI", 10, "bold"))
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Function to update status
        def update_status():
            explained_total = get_explained_variance_total(self.current_session, payment_method)
            unexplained = get_unexplained_variance(self.current_session, payment_method)
            status_text = f"Explained: {self.currency_symbol}{explained_total:,.2f}  |  Unexplained: {self.currency_symbol}{unexplained:,.2f}"
            status_label.config(text=status_text)

        # Bind double-click to edit
        expl_tree.bind('<Double-1>', lambda e: self._edit_selected_explanation(expl_tree, payment_method, update_status))

    def _save_and_update_main_table(self, dialog: tk.Toplevel, payment_method: str = None) -> None:
        """Save explanations and update the main reconciliation table."""
        # Create a progress dialog with spinner
        progress_dialog = tk.Toplevel(dialog)
        progress_dialog.title("Saving...")
        progress_dialog.geometry("300x120")
        progress_dialog.resizable(False, False)
        progress_dialog.transient(dialog)
        progress_dialog.grab_set()
        
        # Center the progress dialog
        progress_dialog.update_idletasks()
        x = dialog.winfo_x() + (dialog.winfo_width() // 2) - 150
        y = dialog.winfo_y() + (dialog.winfo_height() // 2) - 60
        progress_dialog.geometry(f"+{x}+{y}")
        
        # Set the app icon
        set_window_icon(progress_dialog)
        
        # Remove window decorations for cleaner look
        progress_dialog.overrideredirect(False)
        
        # Progress frame
        progress_frame = ttk.Frame(progress_dialog, padding=20)
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # Spinner animation using text
        spinner_chars = ["◐", "◓", "◑", "◒"]
        spinner_index = [0]  # Use list to allow mutation in nested function
        
        spinner_label = ttk.Label(progress_frame, text=spinner_chars[0], font=("Segoe UI", 24))
        spinner_label.pack(pady=(0, 10))
        
        message_label = ttk.Label(progress_frame, text="Saving variance explanations...", font=("Segoe UI", 10))
        message_label.pack()
        
        # Animation function
        def animate_spinner():
            if progress_dialog.winfo_exists():
                spinner_index[0] = (spinner_index[0] + 1) % len(spinner_chars)
                spinner_label.config(text=spinner_chars[spinner_index[0]])
                progress_dialog.after(100, animate_spinner)
        
        # Start animation
        animate_spinner()
        progress_dialog.update()
        
        def do_save():
            try:
                if self.current_session.session_id is None:
                    # Save new session to database
                    session_id = self._save_new_session_to_database()
                    self.current_session.session_id = session_id
                    
                    # Reload session from database
                    db_session = get_reconciliation_session(session_id)
                    if db_session:
                        # Convert to our UI session format
                        self.current_session = ReconciliationSession(
                            session_id=db_session.session_id,
                            date=db_session.reconciliation_date,
                            period_type=db_session.period_type,
                            start_date=db_session.start_date,
                            end_date=db_session.end_date,
                            items=[],  # Will be populated below
                            status=db_session.status,
                            created_by=db_session.reconciled_by or 1,
                            created_at=db_session.created_at or datetime.now().isoformat(),
                            completed_at=db_session.reconciled_at,
                            notes=db_session.notes
                        )
                        
                        # Convert entries to items
                        for entry in db_session.entries:
                            item = ReconciliationItem(
                                payment_method=entry.payment_method,
                                system_amount=entry.system_amount,
                                actual_amount=entry.actual_amount,
                                variance=entry.variance,
                                notes=entry.explanation
                            )
                            self.current_session.items.append(item)
                        
                        # Load explanations into memory
                        self.current_session.explanations = get_variance_explanations(self.current_session)
                        self.current_session.explanations_loaded = True
                
                # Close progress dialog
                if progress_dialog.winfo_exists():
                    progress_dialog.destroy()
                
                # Show success message
                messagebox.showinfo("Success", "Variance explanations saved successfully!")
                
                # Close main dialog
                dialog.destroy()
                
                # Schedule UI refresh after dialog closes (non-blocking)
                self.after(10, self._refresh_main_display)
                
            except Exception as e:
                if progress_dialog.winfo_exists():
                    progress_dialog.destroy()
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
        
        # Schedule the save operation to allow the UI to update
        progress_dialog.after(200, do_save)

    def _refresh_main_display(self) -> None:
        """Refresh the main display after saving."""
        self._load_session_data()
        self._update_totals()

    def _add_variance_explanation(self, dialog: tk.Toplevel, expl_tree: ttk.Treeview, payment_method: str, update_status: callable) -> None:
        """Add a new variance explanation."""
        # Get the unexplained variance to pre-populate the amount field
        unexplained = get_unexplained_variance(self.current_session, payment_method)
        
        # Create input dialog
        input_dialog = tk.Toplevel(dialog)
        input_dialog.title("Add Variance Explanation")
        input_dialog.geometry("400x220")
        input_dialog.resizable(False, False)
        input_dialog.transient(dialog)
        input_dialog.grab_set()

        # Set the app icon
        set_window_icon(input_dialog)

        frame = ttk.Frame(input_dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Show remaining unexplained variance
        ttk.Label(frame, text=f"Remaining Unexplained: {self.currency_symbol}{abs(unexplained):,.2f}", 
                 font=("Segoe UI", 9, "italic")).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Explanation:").pack(anchor=tk.W)
        explanation_var = tk.StringVar()
        explanation_entry = ttk.Entry(frame, textvariable=explanation_var)
        explanation_entry.pack(fill=tk.X, pady=(5, 10))
        explanation_entry.focus()

        ttk.Label(frame, text=f"Amount ({self.currency_symbol}):").pack(anchor=tk.W)
        # Pre-fill with the absolute unexplained amount
        amount_var = tk.StringVar(value=f"{abs(unexplained):.2f}")
        amount_entry = ttk.Entry(frame, textvariable=amount_var)
        amount_entry.pack(fill=tk.X, pady=(5, 15))

        def save_explanation():
            try:
                explanation = explanation_var.get().strip()
                amount = float(amount_var.get())

                if not explanation:
                    messagebox.showerror("Error", "Please enter an explanation.")
                    return

                if amount <= 0:
                    messagebox.showerror("Error", "Amount must be greater than zero.")
                    return

                # Validate that amount doesn't exceed unexplained variance
                current_unexplained = abs(get_unexplained_variance(self.current_session, payment_method))
                if abs(amount) > current_unexplained + 0.01:  # Small tolerance for floating point
                    messagebox.showerror("Error", 
                        f"Amount ({self.currency_symbol}{abs(amount):,.2f}) exceeds the remaining unexplained variance ({self.currency_symbol}{current_unexplained:,.2f}).")
                    return

                # Match the sign of the variance for the explanation amount
                item = next((i for i in self.current_session.items if i.payment_method == payment_method), None)
                if item and item.variance < 0:
                    amount = -abs(amount)  # Negative variance needs negative explanation
                else:
                    amount = abs(amount)

                # Add explanation (works for both in-memory and saved sessions)
                add_variance_explanation(
                    self.current_session,
                    payment_method,
                    explanation,
                    amount,
                    self.user_id
                )

                # Refresh the explanations table
                self._refresh_explanations_table(expl_tree, payment_method)

                # Update status
                update_status()

                input_dialog.destroy()

            except ValueError:
                messagebox.showerror("Error", "Please enter a valid amount.")

        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill=tk.X)

        ttk.Button(buttons_frame, text="Cancel", command=input_dialog.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(buttons_frame, text="Save", command=save_explanation).pack(side=tk.RIGHT)

        explanation_entry.bind('<Return>', lambda e: amount_entry.focus())
        amount_entry.bind('<Return>', lambda e: save_explanation())

    def _edit_selected_explanation(self, expl_tree: ttk.Treeview, payment_method: str, update_status: callable) -> None:
        """Edit the selected explanation."""
        selection = expl_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an explanation to edit.")
            return

        item_id = selection[0]
        values = expl_tree.item(item_id, 'values')
        status = values[2]  # Status column
        expl_id = values[3] if len(values) > 3 else ""  # Hidden ID column

        if status == "⚠ Pending" or not expl_id:
            messagebox.showinfo("Info", "Unexplained variance cannot be edited directly. Add explanations to account for it.")
            return

        # Get explanation ID from the hidden column
        try:
            explanation_id = int(expl_id)
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Invalid explanation selection.")
            return

        # Get current values
        explanations = get_variance_explanations(self.current_session, payment_method)
        current_expl = next((e for e in explanations if e.explanation_id == explanation_id), None)

        if not current_expl:
            return

        # Create edit dialog
        edit_dialog = tk.Toplevel(self)
        edit_dialog.title("Edit Variance Explanation")
        edit_dialog.geometry("400x200")
        edit_dialog.resizable(False, False)
        edit_dialog.transient(self)
        edit_dialog.grab_set()

        # Set the app icon
        set_window_icon(edit_dialog)

        frame = ttk.Frame(edit_dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Explanation:").pack(anchor=tk.W)
        explanation_var = tk.StringVar(value=current_expl.explanation)
        explanation_entry = ttk.Entry(frame, textvariable=explanation_var)
        explanation_entry.pack(fill=tk.X, pady=(5, 10))
        explanation_entry.focus()

        ttk.Label(frame, text=f"Amount ({self.currency_symbol}):").pack(anchor=tk.W)
        # Show absolute amount for editing
        amount_var = tk.StringVar(value=f"{abs(current_expl.amount):.2f}")
        amount_entry = ttk.Entry(frame, textvariable=amount_var)
        amount_entry.pack(fill=tk.X, pady=(5, 15))

        def update_explanation():
            try:
                explanation = explanation_var.get().strip()
                amount = float(amount_var.get())

                if not explanation:
                    messagebox.showerror("Error", "Please enter an explanation.")
                    return

                if amount <= 0:
                    messagebox.showerror("Error", "Amount must be greater than zero.")
                    return

                # Calculate max allowed: current unexplained + current explanation amount
                current_unexplained = abs(get_unexplained_variance(self.current_session, payment_method))
                max_allowed = current_unexplained + abs(current_expl.amount)
                
                if abs(amount) > max_allowed + 0.01:  # Small tolerance for floating point
                    messagebox.showerror("Error", 
                        f"Amount ({self.currency_symbol}{abs(amount):,.2f}) exceeds the maximum allowed ({self.currency_symbol}{max_allowed:,.2f}).")
                    return

                # Match the sign of the variance for the explanation amount
                item = next((i for i in self.current_session.items if i.payment_method == payment_method), None)
                if item and item.variance < 0:
                    amount = -abs(amount)  # Negative variance needs negative explanation
                else:
                    amount = abs(amount)

                # Update explanation
                update_variance_explanation(self.current_session, explanation_id, explanation, amount)

                # Refresh the explanations table
                self._refresh_explanations_table(expl_tree, payment_method)

                # Update status
                update_status()

                edit_dialog.destroy()

            except ValueError:
                messagebox.showerror("Error", "Please enter a valid amount.")

        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill=tk.X)

        ttk.Button(buttons_frame, text="Cancel", command=edit_dialog.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(buttons_frame, text="Update", command=update_explanation).pack(side=tk.RIGHT)

    def _delete_selected_explanation(self, expl_tree: ttk.Treeview, payment_method: str, update_status: callable) -> None:
        """Delete the selected explanation."""
        selection = expl_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an explanation to delete.")
            return

        item_id = selection[0]
        values = expl_tree.item(item_id, 'values')
        status = values[2]  # Status column
        expl_id = values[3] if len(values) > 3 else ""  # Hidden ID column

        if status == "⚠ Pending" or not expl_id:
            messagebox.showinfo("Info", "Unexplained variance cannot be deleted.")
            return

        # Get explanation ID from the hidden column
        try:
            explanation_id = int(expl_id)
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Invalid explanation selection.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this explanation?"):
            try:
                delete_variance_explanation(self.current_session, explanation_id)
                self._refresh_explanations_table(expl_tree, payment_method)
                update_status()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete explanation: {str(e)}")

    def _refresh_explanations_table(self, expl_tree: ttk.Treeview, payment_method: str) -> None:
        """Refresh the explanations table (does not update main table - use Save & Continue for that)."""
        # Clear existing items
        for item in expl_tree.get_children():
            expl_tree.delete(item)

        # Reload explanations
        explanations = get_variance_explanations(self.current_session, payment_method)
        for expl in explanations:
            expl_tree.insert("", tk.END, values=(
                expl.explanation,
                f"{self.currency_symbol}{expl.amount:,.2f}",
                "✓ Explained",
                expl.explanation_id  # Hidden ID column
            ), tags=("explained",))

        # Add unexplained variance row
        unexplained = get_unexplained_variance(self.current_session, payment_method)
        if abs(unexplained) >= 0.01:
            expl_tree.insert("", tk.END, values=(
                "Unexplained",
                f"{self.currency_symbol}{unexplained:,.2f}",
                "⚠ Pending",
                ""  # No ID for unexplained row
            ), tags=("unexplained",))

    def _on_right_click(self, event) -> None:
        """Handle right-click on reconciliation item for context menu."""
        region = self.recon_tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        item_id = self.recon_tree.identify_row(event.y)
        if not item_id:
            return

        # Select the item
        self.recon_tree.selection_set(item_id)

        # Create context menu
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Add/Edit Explanation", command=lambda: self._add_explanation(item_id))

        # Show menu
        menu.post(event.x_root, event.y_root)

    def _add_explanation(self, item_id: str) -> None:
        """Add or edit explanation for a reconciliation item."""
        payment_method = self.recon_tree.set(item_id, "payment_method")

        # Get current notes
        current_notes = ""
        if self.current_session:
            for item in self.current_session.items:
                if item.payment_method == payment_method:
                    current_notes = item.notes
                    break

        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Add Explanation - {payment_method}")
        dialog.geometry("500x300")
        dialog.resizable(False, False)

        # Set the app icon
        set_window_icon(dialog)

        # Content
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"Payment Method: {payment_method}",
                 font=("Segoe UI", 10, "bold")).pack(pady=(0, 10))

        ttk.Label(frame, text="Explanation/Notes:").pack(anchor=tk.W)
        notes_text = scrolledtext.ScrolledText(frame, height=8, font=("Segoe UI", 9))
        notes_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        notes_text.insert(tk.END, current_notes)
        notes_text.focus()

        def save_explanation():
            notes = notes_text.get("1.0", tk.END).strip()

            # Update session data
            if self.current_session:
                for item in self.current_session.items:
                    if item.payment_method == payment_method:
                        item.notes = notes
                        break

            # Update database if session is saved
            if self.current_session and self.current_session.session_id is not None:
                update_reconciliation_entry(
                    self.current_session.session_id,
                    payment_method,
                    None,  # Don't update amount
                    notes
                )

            dialog.destroy()

        # Buttons
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(buttons_frame, text="Save", command=save_explanation).pack(side=tk.RIGHT)

        # Bind Ctrl+Enter to save
        notes_text.bind('<Control-Return>', lambda e: save_explanation())

    def _save_draft_session(self) -> None:
        """Save the manually entered reconciliation data as a draft."""
        if not self.current_session:
            messagebox.showerror("Error", "No active session to save.")
            return

        try:
            if self.current_session.session_id is None:
                # New session - save to database for the first time
                session_id = self._save_new_session_to_database()
                self.current_session.session_id = session_id
                messagebox.showinfo("Success", f"Session {session_id} saved as draft successfully!")
            else:
                # Existing session - update only manually entered data and session metadata
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Update the manually entered data in the reconciliation_entries table
                    for item in self.current_session.items:
                        cursor.execute("""
                            UPDATE reconciliation_entries
                            SET actual_amount = ?, opening_balance = ?
                            WHERE session_id = ? AND payment_method = ?
                        """, (
                            item.actual_amount,
                            getattr(item, 'opening_balance', 0.0),
                            self.current_session.session_id,
                            item.payment_method
                        ))
                    
                    # Update the session record to mark it as updated
                    cursor.execute("""
                        UPDATE reconciliation_sessions
                        SET updated_at = ?
                        WHERE session_id = ?
                    """, (datetime.now().isoformat(), self.current_session.session_id))
                    
                    conn.commit()

                messagebox.showinfo("Success", "Draft data updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save draft: {str(e)}")

    def _save_new_session_to_database(self) -> int:
        """Save a new in-memory session to the database.

        Uses save_reconciliation_session to persist the exact in-memory
        state (including custom dates, opening balances, cash_out, etc.)
        instead of re-deriving everything from scratch.
        """
        session_id = save_reconciliation_session(self.current_session)
        self.current_session.session_id = session_id

        # Persist any in-memory explanations
        if hasattr(self.current_session, 'explanations') and self.current_session.explanations:
            for explanation in self.current_session.explanations:
                add_variance_explanation_to_db(
                    session_id,
                    explanation.payment_method,
                    explanation.explanation,
                    explanation.amount,
                    self.user_id
                )

        return session_id

    def _complete_reconciliation(self) -> None:
        """Complete the reconciliation session."""
        if not self.current_session:
            messagebox.showerror("Error", "No active session to complete.")
            return

        # Check permission to approve reconciliation
        current_username = get_username()
        if not permissions.has_permission(current_username, 'approve_reconciliation'):
            messagebox.showerror("Permission Denied", "You do not have permission to approve reconciliation sessions")
            return

        # Check if all variances are explained
        unexplained_items = []
        for item in self.current_session.items:
            if abs(item.variance) >= 0.01:  # Has variance
                # Check unexplained variance (works for both saved and unsaved sessions)
                unexplained_variance = get_unexplained_variance(
                    self.current_session,
                    item.payment_method
                )
                if abs(unexplained_variance) >= 0.01:
                    unexplained_items.append(item.payment_method)

        if unexplained_items:
            result = messagebox.askyesno(
                "Unexplained Variances",
                f"The following payment methods have unexplained variances:\n"
                f"{', '.join(unexplained_items)}\n\n"
                f"Do you want to complete the reconciliation anyway?",
                icon='warning'
            )
            if not result:
                return

        try:
            if self.current_session.session_id is None:
                # New session - save to database first, then complete
                session_id = self._save_new_session_to_database()
                self.current_session.session_id = session_id

            # Update all entries in the database
            for item in self.current_session.items:
                update_reconciliation_entry(
                    self.current_session.session_id,
                    item.payment_method,
                    item.actual_amount,
                    item.notes
                )
                self._persist_entry_extras(
                    self.current_session.session_id,
                    item.payment_method,
                    getattr(item, 'opening_balance', 0.0),
                    getattr(item, 'cash_out', 0.0),
                    item.variance
                )

            # Complete the session
            complete_reconciliation_session(self.current_session.session_id, self.user_id)
            messagebox.showinfo("Success", "Reconciliation completed successfully!")

            # Clear current session and return to manage view
            self.current_session = None
            self._switch_view("manage")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete reconciliation: {str(e)}")

    def _refresh_session_data(self) -> None:
        """Refresh the current session data from database."""
        if not self.current_session:
            messagebox.showerror("Error", "No active session to refresh.")
            return

        try:
            # Reload session data
            self._load_session_data()
            messagebox.showinfo("Success", "Session data refreshed!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh data: {str(e)}")

    def _edit_selected_session(self) -> None:
        """Load the selected session for editing."""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session to edit.")
            return

        session_id = self.sessions_tree.item(selection[0])['values'][0]
        
        # Use the proper conversion method
        self._load_selected_session_by_id(session_id)

    def _export_session_to_csv(self) -> None:
        """Export the selected session data to CSV file."""
        treeview = self.sessions_tree
        selection = treeview.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session to export.")
            return

        session_id = treeview.item(selection[0])['values'][0]

        try:
            # Load the session
            session = get_reconciliation_session(session_id)
            if not session:
                messagebox.showerror("Error", "Session not found.")
                return

            # Ask for save location
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title=f"Export Session {session_id}",
                initialfile=f"reconciliation_session_{session_id}.csv"
            )

            if not filename:
                return

            # Export to CSV
            import csv
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Write header
                writer.writerow(['Session ID', 'Date', 'Period', 'Status', 'Item',
                                 'Opening Balance', 'POS Sales', 'Cash Out',
                                 'Closing Balance', 'Actual Sales', 'Variance', 'Explanation'])

                # Write session info
                for entry in session.entries:
                    opening = getattr(entry, 'opening_balance', 0.0)
                    cash_out = getattr(entry, 'cash_out', 0.0)
                    actual_sales = entry.actual_amount - opening + cash_out
                    writer.writerow([
                        session.session_id,
                        session.reconciliation_date,
                        session.period_type,
                        session.status,
                        entry.payment_method,
                        f"{opening:.2f}",
                        f"{entry.system_amount:.2f}",
                        f"{cash_out:.2f}",
                        f"{entry.actual_amount:.2f}",
                        f"{actual_sales:.2f}",
                        f"{entry.variance:.2f}",
                        entry.explanation or ""
                    ])

            messagebox.showinfo("Success", f"Session exported to {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export session: {str(e)}")

    def _bulk_delete_sessions(self) -> None:
        """Delete multiple selected sessions with confirmation."""
        treeview = self.sessions_tree
        selection = treeview.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select sessions to delete.")
            return

        session_count = len(selection)
        if session_count == 1:
            session_id = treeview.item(selection[0])['values'][0]
            if not messagebox.askyesno("Confirm Delete",
                                     f"Are you sure you want to delete session {session_id}?\n\nThis action cannot be undone."):
                return
        else:
            if not messagebox.askyesno("Confirm Bulk Delete",
                                     f"Are you sure you want to delete {session_count} sessions?\n\nThis action cannot be undone."):
                return

        deleted_count = 0
        errors = []

        for item in selection:
            session_id = treeview.item(item)['values'][0]
            try:
                delete_reconciliation_session(session_id)
                deleted_count += 1
            except Exception as e:
                errors.append(f"Session {session_id}: {str(e)}")

        # Refresh both lists
        self._load_sessions_list()
        if hasattr(self, 'advanced_sessions_tree'):
            self._load_advanced_sessions_list()

        # Show results
        if deleted_count > 0:
            messagebox.showinfo("Success", f"Successfully deleted {deleted_count} session(s).")
        if errors:
            error_msg = "Errors occurred during deletion:\n\n" + "\n".join(errors)
            messagebox.showerror("Delete Errors", error_msg)

    def _mark_session_reviewed(self) -> None:
        """Mark the selected session as reviewed."""
        treeview = self.sessions_tree
        selection = treeview.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session to mark as reviewed.")
            return

        session_id = treeview.item(selection[0])['values'][0]

        try:
            # Update the session status to reviewed
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE reconciliation_sessions
                SET reviewed = 1, reviewed_at = ?
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))

            conn.commit()
            conn.close()

            # Refresh both lists
            self._load_sessions_list()
            if hasattr(self, 'advanced_sessions_tree'):
                self._load_advanced_sessions_list()

            messagebox.showinfo("Success", f"Session {session_id} marked as reviewed.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to mark session as reviewed: {str(e)}")

    def _filter_sessions_by_status(self) -> None:
        """Show a dialog to filter sessions by status."""
        # Create filter dialog
        filter_window = tk.Toplevel(self)
        filter_window.title("Filter Sessions")
        filter_window.geometry("300x200")
        filter_window.resizable(False, False)
        filter_window.transient(self)
        filter_window.grab_set()

        # Set the app icon
        set_window_icon(filter_window)

        # Center the dialog
        filter_window.geometry("+{}+{}".format(
            self.winfo_rootx() + self.winfo_width() // 2 - 150,
            self.winfo_rooty() + self.winfo_height() // 2 - 100
        ))

        ttk.Label(filter_window, text="Select Status to Filter:").pack(pady=(20, 10))

        # Status options
        status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_window, textvariable=status_var,
                                   values=["All", "Open", "Completed", "Reviewed"])
        status_combo.pack(pady=(0, 20))

        def apply_filter():
            selected_status = status_var.get()
            self._apply_status_filter(selected_status)
            filter_window.destroy()

        def clear_filter():
            self._apply_status_filter("All")
            filter_window.destroy()

        button_frame = ttk.Frame(filter_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        ttk.Button(button_frame, text="Apply Filter", command=apply_filter).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Clear Filter", command=clear_filter).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Cancel", command=filter_window.destroy).pack(side=tk.RIGHT)

    def _apply_status_filter(self, status_filter: str) -> None:
        """Apply the status filter to the sessions list."""
        treeview = self.sessions_tree

        # Clear current items
        for item in treeview.get_children():
            treeview.delete(item)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if status_filter == "All":
                cursor.execute("""
                    SELECT session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed
                    FROM reconciliation_sessions
                    ORDER BY reconciliation_date DESC, session_id DESC
                    LIMIT 50
                """)
            else:
                status_condition = {
                    "Open": "status = 'draft'",
                    "Completed": "status = 'completed'",
                    "Reviewed": "reviewed = 1"
                }.get(status_filter, "")

                if status_condition:
                    cursor.execute(f"""
                        SELECT session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed
                        FROM reconciliation_sessions
                        WHERE {status_condition}
                        ORDER BY reconciliation_date DESC, session_id DESC
                        LIMIT 50
                    """)
                else:
                    # Fallback to all
                    cursor.execute("""
                        SELECT session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed
                        FROM reconciliation_sessions
                        ORDER BY reconciliation_date DESC, session_id DESC
                        LIMIT 50
                    """)

            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                session_id, reconciliation_date, period_type, status, total_system_sales, total_variance, reviewed = row

                # Format status with reviewed indicator
                display_status = status.title()
                if reviewed:
                    display_status += " ✓"

                # Format amounts
                system_amt = f"{total_system_sales:.2f}" if total_system_sales else "0.00"
                variance_amt = f"{total_variance:.2f}" if total_variance else "0.00"

                treeview.insert("", tk.END, values=(
                    session_id, reconciliation_date, period_type, display_status, system_amt, variance_amt
                ))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to filter sessions: {str(e)}")