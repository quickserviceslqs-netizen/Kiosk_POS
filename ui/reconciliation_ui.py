"""
Clean UI Implementation for Reconciliation Module

This UI provides a streamlined reconciliation experience where:
- System amounts are automatically displayed from external accounts
- Users focus on entering actual amounts
- Clear visual feedback for variances and status
- Simple review and completion workflow
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import tkinter.font as tkFont
from datetime import datetime
from utils.date_utils import format_date
from utils.theme import get_status_color
from typing import Optional, Dict, Any, List
import logging

from modules.reconciliation_core import (
    ReconciliationSession, ReconciliationItem, reconciliation_service
)
from modules.reconciliation import orchestrator, ReconSession
from utils.i18n import get_currency_symbol
from utils import set_window_icon

logger = logging.getLogger(__name__)


class ReconciliationUI(ttk.Frame):
    """Clean reconciliation UI with automatic system amounts."""

    def __init__(self, parent: tk.Misc, *, on_home: callable | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.currency_symbol = get_currency_symbol()
        self.current_session: Optional[ReconciliationSession] = None
        self.on_home = on_home

        # Get user info
        root = parent.winfo_toplevel()
        self.current_user = getattr(root, "current_user", {})
        self.user_id = self.current_user.get('user_id', 1)

        self.add_payment_var = tk.StringVar(value="Cash")
        self.add_actual_var = tk.StringVar()

        # Add padding to the main frame
        self.configure(padding=10)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the clean reconciliation UI."""
        # Get root for menu
        self.root = self.winfo_toplevel()

        # Add menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Create Functions menu
        functions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Functions", menu=functions_menu)
        functions_menu.add_command(label="Session Management", command=self._open_session_management_window)
        functions_menu.add_command(label="Reports", command=self._open_reports_window)
        functions_menu.add_command(label="Settings", command=self._open_settings_window)
        functions_menu.add_command(label="Add Counted Amounts", command=self._open_add_amounts_window)

        # Header with title
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        title_label = ttk.Label(header, text="Payment Reconciliation",
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(side=tk.LEFT)

        # Status indicator
        self.status_var = tk.StringVar(value="No active session")
        status_label = ttk.Label(header, textvariable=self.status_var,
                               foreground=get_status_color('gray'))
        status_label.pack(side=tk.RIGHT)

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Session controls
        session_frame = ttk.LabelFrame(toolbar, text="Session", padding=5)
        session_frame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(session_frame, text="New Session",
                  command=self._create_new_session).pack(side=tk.LEFT, padx=(0, 5))

        # Period selection
        period_frame = ttk.LabelFrame(toolbar, text="Period", padding=5)
        period_frame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(period_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.period_var = tk.StringVar(value="daily")
        period_combo = ttk.Combobox(period_frame, textvariable=self.period_var,
                                   values=["daily", "weekly", "monthly"], width=8)
        period_combo.grid(row=0, column=1, sticky=tk.W, padx=2)

        ttk.Label(period_frame, text="Date:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.date_var = tk.StringVar(value=format_date(datetime.now()))
        date_entry = ttk.Entry(period_frame, textvariable=self.date_var, width=10)
        date_entry.grid(row=1, column=1, sticky=tk.W, padx=2)

        # Main content area
        self._build_reconciliation_content(self)

    def _update_nav_buttons(self) -> None:
        """Update navigation button appearances to show active view."""
        labels = {
            'session': "Session Management",
            'recon': "Reconciliation", 
            'reports': "Reports",
            'settings': "Settings"
        }
        for key, btn in self.nav_buttons.items():
            if key == self.current_nav:
                btn.config(text=f"▶ {labels[key]}")
            else:
                btn.config(text=labels[key])

    def _show_reconciliation(self) -> None:
        """Show the main reconciliation view."""
        if self.current_view:
            self.current_view.destroy()
        self.current_view = ttk.Frame(self.content_frame)
        self.current_view.pack(fill=tk.BOTH, expand=True)

        self.current_nav = 'recon'
        self._update_nav_buttons()

        # Summary panel
        self._build_summary_panel(self.current_view)

        # Reconciliation items panel
        self._build_items_panel(self.current_view)

        # Welcome message
        self._show_welcome_message()

    def _show_welcome_message(self) -> None:
        """Show welcome message when no session is active."""
        if not self.current_session and hasattr(self, 'items_container'):
            self._welcome_frame = ttk.Frame(self.items_container)
            self._welcome_frame.pack(fill=tk.BOTH, expand=True, pady=20)
            ttk.Label(self._welcome_frame, text="Welcome to Payment Reconciliation",
                     font=("Segoe UI", 16, "bold")).pack(pady=10)
            ttk.Label(self._welcome_frame, text="Create a new session to begin reconciling payments.",
                     font=("Segoe UI", 10)).pack(pady=5)
            ttk.Button(self._welcome_frame, text="Create New Session",
                      command=self._create_new_session).pack(pady=10)

    def _build_reconciliation_content(self, parent: ttk.Frame) -> None:
        """Build the reconciliation content in the given parent."""
        # Summary panel
        self._build_summary_panel(parent)

        # Reconciliation items panel
        self._build_items_panel(parent)

        # Notes panel
        self._build_notes_panel(parent)

        # Welcome message
        self._show_welcome_message()

    def _open_session_management_window(self) -> None:
        """Open session management in a new window."""
        win = tk.Toplevel(self.root)
        win.title("Session Management")
        
        # Set the app icon
        set_window_icon(win)
        
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True)
        self._build_session_management_content(frame)

    def _open_reports_window(self) -> None:
        """Open reports in a new window."""
        win = tk.Toplevel(self.root)
        win.title("Reports & Export")
        
        # Set the app icon
        set_window_icon(win)
        
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True)
        self._build_reports_content(frame)

    def _open_settings_window(self) -> None:
        """Open settings in a new window."""
        win = tk.Toplevel(self.root)
        win.title("Settings")
        
        # Set the app icon
        set_window_icon(win)
        
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True)
        self._build_settings_content(frame)

    def _open_add_amounts_window(self) -> None:
        """Open add counted amounts in a new window."""
        win = tk.Toplevel(self.root)
        win.title("Add Counted Amounts")
        
        # Set the app icon
        set_window_icon(win)
        
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        ttk.Label(frame, text="Add Counted Amounts", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Entry controls
        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=(0, 5))
        entry_frame.columnconfigure(1, weight=1)
        entry_frame.columnconfigure(3, weight=0)

        ttk.Label(entry_frame, text="Payment Method:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        add_combo = ttk.Combobox(entry_frame, textvariable=self.add_payment_var, width=24)
        add_combo['values'] = ['Cash', 'Credit Card', 'Debit Card', 'Digital Wallet', 'Check', 'Gift Card', 'Other']
        add_combo.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(entry_frame, text="Counted Amount:").grid(row=0, column=2, sticky=tk.W, padx=(8, 6))
        ttk.Entry(entry_frame, textvariable=self.add_actual_var, width=12, justify=tk.RIGHT).grid(row=0, column=3, sticky=tk.W)

        ttk.Button(entry_frame, text="Add to Counted List", command=self._on_add_manual_entry).grid(row=0, column=4, sticky=tk.W, padx=(8,0))

        # Instructions
        instr = ttk.Label(frame, text="Use this section to add payment methods and their actual counted amounts.\nThese will appear in the 'Manual / Counted Amounts' table for mapping to system balances.",
                 font=("Segoe UI", 8), foreground=get_status_color("text_light"), justify=tk.LEFT)
        instr.pack(anchor=tk.W, fill=tk.X, pady=(10,0))
        instr.configure(wraplength=500)

    def _build_session_management_content(self, parent: ttk.Frame) -> None:
        """Build session management content."""
        # Title
        ttk.Label(parent, text="Session Management", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Create new session button
        ttk.Button(parent, text="Create New Session", command=self._create_new_session).pack(pady=5)

        # List of sessions (placeholder)
        sessions_frame = ttk.LabelFrame(parent, text="Recent Sessions", padding=10)
        sessions_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # For now, just show current session info
        if self.current_session:
            ttk.Label(sessions_frame, text=f"Current Session: {self.current_session.session_id}").pack()
            ttk.Label(sessions_frame, text=f"Status: {self.current_session.status}").pack()
        else:
            ttk.Label(sessions_frame, text="No active session").pack()

    def _build_reports_content(self, parent: ttk.Frame) -> None:
        """Build reports content."""
        # Title
        ttk.Label(parent, text="Reports & Export", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Export buttons
        ttk.Button(parent, text="Export to CSV", command=self._export_csv).pack(pady=5)
        ttk.Button(parent, text="Import from CSV", command=self._import_csv).pack(pady=5)

        # Placeholder for reports
        reports_frame = ttk.LabelFrame(parent, text="Available Reports", padding=10)
        reports_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        ttk.Label(reports_frame, text="Reconciliation Summary Report").pack(anchor=tk.W)
        ttk.Label(reports_frame, text="Variance Analysis Report").pack(anchor=tk.W)

    def _build_settings_content(self, parent: ttk.Frame) -> None:
        """Build settings content."""
        # Title
        ttk.Label(parent, text="Settings", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Period settings (moved from toolbar)
        period_frame = ttk.LabelFrame(parent, text="Default Period Settings", padding=10)
        period_frame.pack(fill=tk.X, pady=10)

        ttk.Label(period_frame, text="Type:").grid(row=0, column=0, sticky=tk.W, padx=2)
        period_combo = ttk.Combobox(period_frame, textvariable=self.period_var,
                                   values=["daily", "weekly", "monthly"], width=8)
        period_combo.grid(row=0, column=1, sticky=tk.W, padx=2)

        ttk.Label(period_frame, text="Date:").grid(row=1, column=0, sticky=tk.W, padx=2)
        date_entry = ttk.Entry(period_frame, textvariable=self.date_var, width=10)
        date_entry.grid(row=1, column=1, sticky=tk.W, padx=2)

        # Other settings placeholder
        other_frame = ttk.LabelFrame(parent, text="Other Settings", padding=10)
        other_frame.pack(fill=tk.X, pady=10)
        ttk.Label(other_frame, text="Additional settings can be added here.").pack()

    def _build_summary_panel(self, parent: ttk.Frame) -> None:
        """Build the summary information panel."""
        summary_frame = ttk.LabelFrame(parent, text="Summary", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))

        # Summary variables
        self.summary_vars = {
            'period': tk.StringVar(value="--"),
            'system_total': tk.StringVar(value=f"{self.currency_symbol}0.00"),
            'actual_total': tk.StringVar(value=f"{self.currency_symbol}0.00"),
            'variance_total': tk.StringVar(value=f"{self.currency_symbol}0.00"),
            'status': tk.StringVar(value="No session")
        }

        # Layout summary info
        # Make columns responsive so values don't overflow
        for c in range(4):
            summary_frame.columnconfigure(c, weight=1)

        ttk.Label(summary_frame, text="Period:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(summary_frame, textvariable=self.summary_vars['period']).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(summary_frame, text="System Total:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Label(summary_frame, textvariable=self.summary_vars['system_total']).grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        ttk.Label(summary_frame, text="Actual Total:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(summary_frame, textvariable=self.summary_vars['actual_total']).grid(row=1, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(summary_frame, text="Total Variance:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10))
        variance_label = ttk.Label(summary_frame, textvariable=self.summary_vars['variance_total'])
        variance_label.grid(row=1, column=3, sticky=tk.W)

        # Status
        ttk.Label(summary_frame, text="Status:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        status_label = ttk.Label(summary_frame, textvariable=self.summary_vars['status'])
        status_label.grid(row=2, column=1, sticky=tk.W)

    def _build_items_panel(self, parent: ttk.Frame) -> None:
        """Build the reconciliation items panel."""
        items_frame = ttk.LabelFrame(parent, text="Payment Methods", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Make header responsive
        header_frame = ttk.Frame(items_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        header_frame.columnconfigure(1, weight=1)
        header_frame.columnconfigure(3, weight=1)

        ttk.Label(header_frame, text="Payment Method", font=("Segoe UI", 9, "bold"), anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(header_frame, text="Expected Amount", font=("Segoe UI", 9, "bold"), anchor=tk.E).grid(row=0, column=1, sticky=tk.E, padx=(0, 10))
        ttk.Label(header_frame, text="Counted Amount", font=("Segoe UI", 9, "bold"), anchor=tk.E).grid(row=0, column=2, sticky=tk.E, padx=(0, 10))
        ttk.Label(header_frame, text="Variance", font=("Segoe UI", 9, "bold"), anchor=tk.E).grid(row=0, column=3, sticky=tk.E, padx=(0, 10))

        # Separator
        ttk.Separator(items_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 5))

        # Scrollable container for items (prevents controls from being hidden on small windows)
        canvas = tk.Canvas(items_frame, highlightthickness=0, height=220)
        vscroll = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mouse wheel scrolling on the items frame
        items_frame.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        items_frame.focus_set()  # Ensure it can receive events

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0,0), window=inner, anchor='nw')
        # Expose the inner container for other methods (welcome message, refresh, etc.)
        self.items_container = inner

        def _on_inner_config(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        inner.bind('<Configure>', _on_inner_config)

        # Ensure the inner frame width matches the canvas width when resized
        def _on_canvas_config(event):
            canvas.itemconfig(inner_id, width=event.width)

        canvas.bind('<Configure>', _on_canvas_config)

        # Single reconciliation table
        tree_container = ttk.Frame(inner)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.recon_tree = ttk.Treeview(tree_container, columns=("pm","expected","actual","variance"), show='headings', selectmode='browse')
        self.recon_tree.heading('pm', text='Payment Method')
        self.recon_tree.heading('expected', text='Expected Amount')
        self.recon_tree.heading('actual', text='Counted Amount')
        self.recon_tree.heading('variance', text='Variance')
        self.recon_tree.column('pm', width=150, anchor='w', stretch=True)
        self.recon_tree.column('expected', width=120, anchor='e', stretch=True)
        self.recon_tree.column('actual', width=120, anchor='e', stretch=True)
        self.recon_tree.column('variance', width=120, anchor='e', stretch=True)
        self.recon_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        tree_vscroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.recon_tree.yview)
        self.recon_tree.configure(yscrollcommand=tree_vscroll.set)
        tree_vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        tree_hscroll = ttk.Scrollbar(inner, orient=tk.HORIZONTAL, command=self.recon_tree.xview)
        self.recon_tree.configure(xscrollcommand=tree_hscroll.set)
        tree_hscroll.pack(fill=tk.X)

        # Bind double-click to edit actual amounts
        self.recon_tree.bind('<Double-1>', self._on_recon_double_click)

        # Recalculate column widths on resize
        inner.bind('<Configure>', lambda e: self._autosize_tree_columns(self.recon_tree))

        # Simple controls
        simple_frame = ttk.Frame(inner)
        simple_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Button(simple_frame, text="Load Expected Amounts", command=self._load_expected).pack(side=tk.LEFT, padx=(0,8))
        ttk.Button(simple_frame, text="Complete Reconciliation", command=self._complete_session).pack(side=tk.RIGHT)

        # Mapping state (simplified, no complex mappings)
        self._recon_data = {}  # pm -> {'expected': float, 'actual': float}

        # Store item widgets (deprecated)
        self.item_widgets = {}

        # Prepare a font measurement
        self._tv_font = tkFont.Font(family="Segoe UI", size=10)
        self._resize_after_id = None

        # Store item widgets (deprecated for dual view compatibility)
        self.item_widgets = {}

        # Prepare a font measurement for column sizing (match Treeview style)
        self._tv_font = tkFont.Font(family="Segoe UI", size=10)
        self._resize_after_id = None

        # Details window handle
        self._details_window = None
        self._original_parents = {}  # store original pack placements when moving frames

    def _build_notes_panel(self, parent: ttk.Frame) -> None:
        """Build the notes panel."""
        notes_frame = ttk.LabelFrame(parent, text="Notes", padding=10)
        notes_frame.pack(fill=tk.X)

        self.notes_frame = notes_frame
        self.notes_text = scrolledtext.ScrolledText(notes_frame, height=4, wrap=tk.WORD)
        self.notes_text.pack(fill=tk.BOTH, expand=True)

    def _autosize_tree_columns(self, tree: ttk.Treeview) -> None:
        """Auto-size Treeview columns to fit their content and header.

        Measures header and each row's text for each column and sets an appropriate width.
        """
        try:
            cols = tree['columns']
            padding = 18  # pixels of extra space for readability
            for ci, col in enumerate(cols):
                # Measure header
                heading = tree.heading(col).get('text', '')
                max_w = self._tv_font.measure(str(heading)) + padding

                # Measure each value in column
                for iid in tree.get_children(''):
                    vals = tree.item(iid, 'values') or []
                    if ci < len(vals):
                        text = str(vals[ci])
                        w = self._tv_font.measure(text) + padding
                        if w > max_w:
                            max_w = w

                # Set a minimum width to avoid too-narrow columns
                min_width = 80 if ci == 0 else 100
                final_w = max(min_width, max_w)

                # Apply width; allow first column to stretch for flexible layouts
                stretch = True if ci == 0 else False
                tree.column(col, width=final_w, minwidth=min_width, stretch=stretch)
        except Exception as e:
            logger.debug(f"Autosize failed: {e}")

    def _on_items_resize(self) -> None:
        """Debounced resize handler to recalc column widths when container size changes."""
        if self._resize_after_id:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.after(120, lambda: (self._autosize_tree_columns(self.system_tree), self._autosize_tree_columns(self.manual_tree)))

    def _on_manual_double_click(self, event):
        """Handle double-click on manual tree to edit amounts."""
        # Get the clicked item and column
        item = self.manual_tree.identify_row(event.y)
        column = self.manual_tree.identify_column(event.x)

        if not item or column != '#2':  # Only allow editing the amount column
            return

        # Get current values
        values = self.manual_tree.item(item, 'values')
        if not values:
            return

        pm, current_amount = values

        # Create an entry widget for editing
        x, y, width, height = self.manual_tree.bbox(item, column)
        entry = ttk.Entry(self.manual_tree, justify='right')

        # Remove currency symbol for editing
        clean_amount = current_amount.replace(self.currency_symbol, '').replace(',', '').strip()
        entry.insert(0, clean_amount)
        entry.select_range(0, tk.END)
        entry.focus()

        entry.place(x=x, y=y, width=width, height=height)

        def save_edit():
            try:
                new_amount = float(entry.get().strip() or '0')
                # Update the tree
                self.manual_tree.item(item, values=(pm, f"{self.currency_symbol}{new_amount:.2f}"))

                # Update the session if this corresponds to a mapped item
                if pm in self._mappings:
                    sys_pm = self._mappings[pm]
                    reconciliation_service.update_item_actual_amount(
                        self.current_session, sys_pm, new_amount
                    )
                else:
                    # Find the item in session and update
                    for session_item in self.current_session.items:
                        if session_item.payment_method == pm:
                            reconciliation_service.update_item_actual_amount(
                                self.current_session, pm, new_amount
                            )
                            break

                self._refresh_display()
                self._update_summary()

            except ValueError:
                pass  # Invalid input, don't update
            finally:
                entry.destroy()

        def cancel_edit():
            entry.destroy()

        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: cancel_edit())
        entry.bind('<FocusOut>', lambda e: save_edit())

    def _on_recon_double_click(self, event):
        """Handle double-click on recon tree to edit actual amounts."""
        # Get the clicked item and column
        item = self.recon_tree.identify_row(event.y)
        column = self.recon_tree.identify_column(event.x)

        if not item or column != '#3':  # Only allow editing the actual column
            return

        # Get current values
        values = self.recon_tree.item(item, 'values')
        if not values or len(values) < 3:
            return

        pm, expected, current_actual, variance = values

        # Create an entry widget for editing
        x, y, width, height = self.recon_tree.bbox(item, column)
        entry = ttk.Entry(self.recon_tree, justify='right')

        # Remove currency symbol for editing
        clean_amount = current_actual.replace(self.currency_symbol, '').replace(',', '').strip()
        entry.insert(0, clean_amount)
        entry.select_range(0, tk.END)
        entry.focus()

        entry.place(x=x, y=y, width=width, height=height)

        def save_edit():
            try:
                new_amount = float(entry.get().strip() or '0')
                # Update data
                if pm in self._recon_data:
                    self._recon_data[pm]['actual'] = new_amount
                    expected = self._recon_data[pm]['expected']
                    variance = new_amount - expected
                    self.recon_tree.item(item, values=(pm, f"{self.currency_symbol}{expected:.2f}", f"{self.currency_symbol}{new_amount:.2f}", f"{self.currency_symbol}{variance:.2f}"))

                    # Update session
                    reconciliation_service.update_item_actual_amount(self.current_session, pm, new_amount)
                    self._update_summary()

            except ValueError:
                pass  # Invalid input, don't update
            finally:
                entry.destroy()

        def cancel_edit():
            entry.destroy()

        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: cancel_edit())
        entry.bind('<FocusOut>', lambda e: save_edit())

    def _load_expected(self) -> None:
        """Load expected amounts from system/external accounts."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please create a session first.")
            return

        try:
            # Create ReconSession for orchestrator
            recon_session = ReconSession(
                session_id=self.current_session.session_id,
                start_date=self.current_session.start_date,
                end_date=self.current_session.end_date,
                created_at=self.current_session.created_at
            )

            # Get entries from all adapters
            for module_key in orchestrator.get_available_modules():
                entries = orchestrator.get_module_entries(recon_session, module_key)
                for entry in entries:
                    pm = entry.payment_method
                    expected = entry.system_amount
                    # Add to DB session if not exists
                    existing = next((i for i in self.current_session.items if i.payment_method == pm), None)
                    if not existing:
                        reconciliation_service.add_item(self.current_session, pm, expected, 0.0)
                    self._recon_data[pm] = {'expected': expected, 'actual': 0.0}

            self._refresh_display()

        except Exception as e:
            logger.error(f"Error loading expected amounts: {e}")
            messagebox.showerror("Error", f"Failed to load expected amounts: {e}")

    def _on_add_manual_entry(self) -> None:
        """Add a manual payment method to the current session (uses external account as system amount)."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please create or load a session first.")
            return

        pm = self.add_payment_var.get().strip()
        if not pm:
            messagebox.showwarning("Missing Data", "Please choose a payment method to add.")
            return

        try:
            actual_text = self.add_actual_var.get().strip()
            actual_amount = float(actual_text) if actual_text else 0.0

            # System amount auto-filled from account manager
            from modules.external_accounts import account_manager
            balances = account_manager.get_balances_by_payment_method()
            system_amount = balances.get(pm, 0.0)

            # If session is persisted, add to DB; otherwise add in-memory
            reconciliation_service.add_manual_entry(self.current_session, pm, system_amount, actual_amount)

            # Also insert into manual tree for mapping convenience
            iid = f"manual_{pm}"
            self.manual_tree.insert('', 'end', iid=iid, values=(pm, f"{self.currency_symbol}{actual_amount:.2f}"))

            # Clear inputs and refresh
            self.add_payment_var.set("")
            self.add_actual_var.set("")
            self._refresh_display()
            messagebox.showinfo("Added", f"Added {pm} to session.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid amount for Actual.")
        except Exception as e:
            logger.error(f"Error adding manual entry: {e}")
            messagebox.showerror("Error", f"Failed to add payment method: {e}")

    def _show_welcome_message(self) -> None:
        """Show welcome message when no session is active."""
        welcome_frame = ttk.Frame(self.items_container)
        welcome_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        # Track reference for restore when details window moves frames
        self._welcome_frame = welcome_frame

        welcome_text = """Welcome to Payment Reconciliation

This simple tool helps you reconcile payments for your kiosk.

To get started:
1. Click "New Session" to create a reconciliation
2. Click "Load Expected Amounts" to load system balances
3. Double-click on "Counted Amount" to enter your actual counts
4. Review the variances
5. Click "Complete Reconciliation" when done

That's it!"""

        welcome_label = ttk.Label(welcome_frame, text=welcome_text,
                                justify=tk.LEFT, foreground=get_status_color("text_light"))
        welcome_label.pack(fill=tk.BOTH)
        welcome_label.configure(wraplength=700)

        self.welcome_frame = welcome_frame

    def _create_new_session(self) -> None:
        """Create a new reconciliation session."""
        try:
            date = self.date_var.get()
            period_type = self.period_var.get()

            self.current_session = reconciliation_service.create_session(
                date, period_type, self.user_id
            )

            self._refresh_display()
            messagebox.showinfo("Session Created",
                              f"Created reconciliation session for {period_type} period.")

            # Ensure details window (if open) gets the new notes reference
            if self._details_window and tk.Toplevel.winfo_exists(self._details_window):
                # Nothing special needed here as notes_frame is moved when opened
                pass

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            messagebox.showerror("Error", f"Failed to create session: {e}")

    def _refresh_display(self) -> None:
        """Refresh the UI to show current session data."""
        if not self.current_session:
            self._show_welcome_message()
            return

        # Hide welcome message
        if hasattr(self, 'welcome_frame'):
            self.welcome_frame.pack_forget()

        # Update summary
        self._update_summary()

        # Populate single recon tree
        for i in self.recon_tree.get_children():
            self.recon_tree.delete(i)

        if not self._recon_data:
            # Load expected if not loaded
            try:
                self._load_expected()
            except:
                pass  # If fails, leave empty
        else:
            for pm, data in self._recon_data.items():
                expected = data['expected']
                actual = data['actual']
                variance = actual - expected
                self.recon_tree.insert('', tk.END, values=(pm, f"{self.currency_symbol}{expected:.2f}", f"{self.currency_symbol}{actual:.2f}", f"{self.currency_symbol}{variance:.2f}"))

        # Auto-size columns
        try:
            self._autosize_tree_columns(self.recon_tree)
        except Exception:
            pass

    def _create_item_row(self, item: ReconciliationItem) -> None:
        """Legacy item row creation (kept for backward compatibility). Use dual tables for new layout."""
        # Kept for compatibility with older flows, but prefer dual-table views.
        row_frame = ttk.Frame(self.items_container)
        row_frame.pack(fill=tk.X, pady=(0, 2))

        # Payment method
        ttk.Label(row_frame, text=item.payment_method, width=15, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        # System amount (read-only)
        system_var = tk.StringVar(value=f"{self.currency_symbol}{item.system_amount:.2f}")
        ttk.Label(row_frame, textvariable=system_var, width=12, anchor=tk.E).grid(row=0, column=1, sticky=tk.E, padx=(0, 10))

        # Actual amount entry
        actual_var = tk.StringVar(value=f"{item.actual_amount:.2f}" if item.actual_amount > 0 else "")
        actual_entry = ttk.Entry(row_frame, textvariable=actual_var, width=12, justify=tk.RIGHT)
        actual_entry.grid(row=0, column=2, sticky=tk.E, padx=(0, 10))
        actual_entry.bind('<KeyRelease>', lambda e, pm=item.payment_method, var=actual_var: self._on_actual_amount_change(pm, var))

        # Variance
        variance_var = tk.StringVar(value=f"{self.currency_symbol}{item.variance:.2f}")
        variance_label = ttk.Label(row_frame, textvariable=variance_var, width=10, anchor=tk.E)
        variance_label.grid(row=0, column=3, sticky=tk.E, padx=(0, 10))

        # Status
        status_var = tk.StringVar(value="✓" if item.is_reconciled else "⚠")
        status_label = ttk.Label(row_frame, textvariable=status_var, width=3, anchor=tk.CENTER)
        status_label.grid(row=0, column=4, sticky=tk.E, padx=(0, 10))

        # Color coding and reviewed checkbox as before
        if item.is_reconciled:
            variance_label.configure(foreground=get_status_color("success"))
            status_label.configure(foreground=get_status_color("success"))
        else:
            variance_label.configure(foreground=get_status_color("danger"))
            status_label.configure(foreground=get_status_color("danger"))

        reviewed_var = tk.BooleanVar(value=item.is_reviewed)
        reviewed_cb = ttk.Checkbutton(row_frame, variable=reviewed_var,
                                    command=lambda pm=item.payment_method, var=reviewed_var: self._on_reviewed_change(pm, var))
        reviewed_cb.grid(row=0, column=5, sticky=tk.E)

        # Store references
        self.item_widgets[item.payment_method] = {
            'frame': row_frame,
            'system_var': system_var,
            'actual_var': actual_var,
            'variance_var': variance_var,
            'status_var': status_var,
            'reviewed_var': reviewed_var,
            'variance_label': variance_label,
            'status_label': status_label
        }

    def _on_actual_amount_change(self, payment_method: str, actual_var: tk.StringVar) -> None:
        """Handle actual amount input changes."""
        try:
            actual_text = actual_var.get().strip()
            actual_amount = float(actual_text) if actual_text else 0.0

            reconciliation_service.update_item_actual_amount(
                self.current_session, payment_method, actual_amount
            )

            self._update_item_display(payment_method)
            self._update_summary()

        except ValueError:
            # Invalid input, don't update
            pass

    def _on_reviewed_change(self, payment_method: str, reviewed_var: tk.BooleanVar) -> None:
        """Handle reviewed checkbox changes."""
        reviewed = reviewed_var.get()
        reconciliation_service.mark_item_reviewed(
            self.current_session, payment_method, reviewed
        )

        # Also reflect mapping/UI state
        self._refresh_display()
        self._update_summary()

    def _auto_match(self) -> None:
        """Auto-match manual entries to system entries by name equality."""
        self._mappings.clear()
        for mid in self.manual_tree.get_children():
            mvals = self.manual_tree.item(mid, 'values')
            if not mvals:
                continue
            m_pm = mvals[0]
            if m_pm in self.system_tree.get_children():
                # if iid equal pm exists in system_tree
                self._mappings[m_pm] = m_pm
        messagebox.showinfo('Auto-match', f'Auto-mapped {len(self._mappings)} entries by name.')

    def _map_selected(self) -> None:
        """Map the selected manual row to the selected system row."""
        sel_sys = self.system_tree.selection()
        sel_man = self.manual_tree.selection()
        if not sel_sys or not sel_man:
            messagebox.showwarning('Mapping', 'Select one system row and one manual row to map.')
            return
        sys_pm = self.system_tree.item(sel_sys[0], 'values')[0]
        man_pm = self.manual_tree.item(sel_man[0], 'values')[0]
        self._mappings[man_pm] = sys_pm
        messagebox.showinfo('Mapped', f'{man_pm} -> {sys_pm}')

    def _clear_mappings(self) -> None:
        """Clear all mappings."""
        self._mappings.clear()
        messagebox.showinfo('Mappings', 'Cleared mappings.')

    def _reconcile_mapped(self) -> None:
        """Apply manual actual amounts to mapped system payment methods and persist."""
        if not self._mappings:
            messagebox.showwarning('Reconcile', 'No mappings to reconcile.')
            return

        applied = 0
        for man_pm, sys_pm in list(self._mappings.items()):
            # get manual amount
            man_iid = f"manual_{man_pm}"
            if man_iid not in self.manual_tree.get_children() and man_pm not in [self.manual_tree.item(i,'values')[0] for i in self.manual_tree.get_children()]:
                continue
            # search for manual tree entry (support both iid and by value)
            man_val = None
            if man_iid in self.manual_tree.get_children():
                man_val = self.manual_tree.item(man_iid, 'values')
            else:
                # fallback: find by pm
                for iid in self.manual_tree.get_children():
                    if self.manual_tree.item(iid, 'values')[0] == man_pm:
                        man_val = self.manual_tree.item(iid, 'values')
                        break
            if not man_val:
                continue
            actual_str = man_val[1].replace(self.currency_symbol, '').replace(',', '').strip()
            try:
                actual_amount = float(actual_str)
            except Exception:
                continue

            # If system payment exists, update it
            if sys_pm in self.system_tree.get_children():
                # Persist via service
                reconciliation_service.update_item_actual_amount(self.current_session, sys_pm, actual_amount)
                applied += 1
            else:
                # Create a new manual entry in session mapped to system name
                reconciliation_service.add_manual_entry(self.current_session, sys_pm, 0.0, actual_amount)
                applied += 1

        # Refresh and report
        self._refresh_display()
        self._update_summary()
        messagebox.showinfo('Reconciled', f'Applied {applied} mappings.')

    def _update_item_display(self, payment_method: str) -> None:
        """Update the display for a specific item."""
        if payment_method not in self.item_widgets:
            return

        item = next((i for i in self.current_session.items if i.payment_method == payment_method), None)
        if not item:
            return

        widgets = self.item_widgets[payment_method]

        # Update variance
        widgets['variance_var'].set(f"{self.currency_symbol}{item.variance:.2f}")

        # Update status
        widgets['status_var'].set("✓" if item.is_reconciled else "⚠")

        # Update colors
        if item.is_reconciled:
            widgets['variance_label'].configure(foreground=get_status_color("success"))
            widgets['status_label'].configure(foreground=get_status_color("success"))
        else:
            widgets['variance_label'].configure(foreground=get_status_color("danger"))
            widgets['status_label'].configure(foreground=get_status_color("danger"))

    def _update_summary(self) -> None:
        """Update the summary panel."""
        if not self.current_session:
            return

        session = self.current_session

        self.summary_vars['period'].set(f"{session.start_date} to {session.end_date}")
        self.summary_vars['system_total'].set(f"{self.currency_symbol}{session.total_system_amount:.2f}")
        self.summary_vars['actual_total'].set(f"{self.currency_symbol}{session.total_actual_amount:.2f}")
        self.summary_vars['variance_total'].set(f"{self.currency_symbol}{session.total_variance:.2f}")

        if session.status == 'completed':
            self.summary_vars['status'].set("Completed ✓")
        elif session.is_complete:
            self.summary_vars['status'].set("Ready to complete")
        else:
            unreviewed = session.unreviewed_count
            self.summary_vars['status'].set(f"{unreviewed} items need review")


    def _on_tree_double(self, event):
        """Generic double-click handler for editing Actual values on a treeview."""
        t = event.widget
        try:
            item = t.identify_row(event.y)
            column = t.identify_column(event.x)
        except Exception:
            return

        # We use column '#2' for manual tree in modern panel (pm, actual)
        # Fallback: if column is '#3' use legacy layout (pm, system, actual)
        if not item or column not in ('#2', '#3'):
            return

        vals = t.item(item, 'values')
        if not vals:
            return

        pm = vals[0]
        # Determine which index holds the amount
        amt_index = 1 if column == '#2' else 2
        try:
            cur_amount_text = vals[amt_index].replace(self.currency_symbol, '').replace(',','').strip()
        except Exception:
            cur_amount_text = '0'

        entry_widget_parent = t
        entry = ttk.Entry(entry_widget_parent, justify='right')
        try:
            x, y, width, height = t.bbox(item, column)
        except Exception:
            return
        entry.insert(0, cur_amount_text)
        entry.select_range(0, tk.END)
        entry.focus()
        entry.place(x=x, y=y, width=width, height=height)

        def save():
            try:
                new_amount = float(entry.get().strip() or '0')
                # Persist via existing reconciliation service
                reconciliation_service.update_item_actual_amount(self.current_session, pm, new_amount)
                # Refresh UI
                self._refresh_display()
                self._update_summary()
            except Exception:
                pass
            finally:
                entry.destroy()

        entry.bind('<Return>', lambda e: save())
        entry.bind('<Escape>', lambda e: entry.destroy())
        entry.bind('<FocusOut>', lambda e: save())



    # Keep backward compatible method name for old binding
    def _on_tree_double_compat(self, event):
        self._on_tree_double(event)

    def _validate_session(self) -> None:
        """Validate the current session."""
        if not self.current_session:
            return

        session = self.current_session

        if session.is_complete:
            messagebox.showinfo("Validation Passed",
                              "All reconciliation items are properly reconciled.")
        else:
            unreviewed = session.unreviewed_count
            messagebox.showwarning("Validation Issues",
                                 f"{unreviewed} items have variances that need to be reviewed.")

    def _complete_session(self) -> None:
        """Complete the reconciliation session."""
        if not self.current_session:
            return

        # Get notes
        notes = self.notes_text.get(1.0, tk.END).strip()

        # Confirm completion
        if not messagebox.askyesno("Complete Reconciliation",
                                 "Are you sure you want to complete this reconciliation session?"):
            return

        # Attempt completion
        if reconciliation_service.complete_session(self.current_session, notes, user_id=self.user_id):
            self._refresh_display()
            messagebox.showinfo("Completed",
                              "Reconciliation session has been completed successfully.")
        else:
            messagebox.showerror("Cannot Complete",
                               "Session cannot be completed. All items must be reconciled first.")

    def _import_csv(self) -> None:
        """Import manual counted amounts from CSV file."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please create or load a session first.")
            return

    def _open_details_window(self) -> None:
        """Open a dedicated window for mappings, add entry and notes to free up table space."""
        # If already open, bring to front
        if self._details_window and tk.Toplevel.winfo_exists(self._details_window):
            try:
                self._details_window.lift()
                self._details_window.focus_set()
            except Exception:
                pass
            return

        # Store original parents and pack_forget to move frames into the window
        self._original_parents['ctrl_frame'] = self.ctrl_frame.pack_info() if self.ctrl_frame.winfo_ismapped() else None
        self._original_parents['notes_frame'] = self.notes_frame.pack_info() if self.notes_frame.winfo_ismapped() else None
        self._original_parents['welcome_frame'] = getattr(self, '_welcome_frame', None).pack_info() if hasattr(self, '_welcome_frame') and getattr(self, '_welcome_frame') and getattr(self, '_welcome_frame').winfo_ismapped() else None

        # Create window
        self._details_window = tk.Toplevel(self)
        self._details_window.title('Reconciliation Details')
        self._details_window.geometry('700x520')
        self._details_window.minsize(500, 380)

        # Set the app icon
        set_window_icon(self._details_window)

        # Container
        container = ttk.Frame(self._details_window, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)

        # Move control frames into container
        try:
            self.ctrl_frame.pack_forget()
            self.ctrl_frame.master = container
            self.ctrl_frame.pack(fill=tk.X, pady=(0,6))
        except Exception:
            pass

        try:
            self.notes_frame.pack_forget()
            self.notes_frame.master = container
            self.notes_frame.pack(fill=tk.BOTH, expand=True, pady=(8,0))
        except Exception:
            pass

        # Close button
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=(8,0))
        ttk.Button(btn_frame, text='Close', command=self._close_details_window).pack(side=tk.RIGHT)

        # Ensure focus
        self._details_window.transient(self.winfo_toplevel())
        self._details_window.lift()
        self._details_window.focus_set()

    def _close_details_window(self) -> None:
        """Restore frames back to the main layout and close details window."""
        if not (self._details_window and tk.Toplevel.winfo_exists(self._details_window)):
            return

        # Remove frames from details window
        try:
            self.ctrl_frame.pack_forget()
            self.notes_frame.pack_forget()
        except Exception:
            pass

        # Repack to original places
        try:
            self.ctrl_frame.master = self.items_container
            self.ctrl_frame.pack(fill=tk.X, pady=(6, 0))
        except Exception:
            pass

        try:
            self.notes_frame.master = self
            self.notes_frame.pack(fill=tk.X)
        except Exception:
            pass

        try:
            if hasattr(self, '_welcome_frame') and self._welcome_frame:
                # Reattach welcome if it was present
                self._welcome_frame.master = self.items_container
                self._welcome_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        except Exception:
            pass

        try:
            self._details_window.destroy()
            self._details_window = None
        except Exception:
            pass
        from tkinter import filedialog
        import csv

        file_path = filedialog.askopenfilename(
            title="Import CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            imported_count = 0
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                # Check for required columns
                required_cols = ['payment_method', 'actual_amount']
                if not all(col in reader.fieldnames for col in required_cols):
                    messagebox.showerror("Invalid CSV",
                                       f"CSV must contain columns: {', '.join(required_cols)}")
                    return

                for row in reader:
                    pm = row.get('payment_method', '').strip()
                    actual_str = row.get('actual_amount', '').strip()

                    if not pm or not actual_str:
                        continue

                    try:
                        actual_amount = float(actual_str)

                        # Get system amount from external accounts
                        from modules.external_accounts import account_manager
                        balances = account_manager.get_balances_by_payment_method()
                        system_amount = balances.get(pm, 0.0)

                        # Add to session
                        reconciliation_service.add_manual_entry(
                            self.current_session, pm, system_amount, actual_amount
                        )
                        imported_count += 1

                    except ValueError:
                        logger.warning(f"Invalid amount '{actual_str}' for {pm}, skipping")
                        continue

            self._refresh_display()
            messagebox.showinfo("Import Complete",
                              f"Successfully imported {imported_count} payment methods from CSV.")

        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            messagebox.showerror("Import Error", f"Failed to import CSV: {e}")

    def _export_csv(self) -> None:
        """Export reconciliation data to CSV file."""
        if not self.current_session:
            messagebox.showwarning("No Session", "Please create or load a session first.")
            return

        from tkinter import filedialog
        import csv

        file_path = filedialog.asksaveasfilename(
            title="Export CSV File",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['payment_method', 'system_amount', 'actual_amount',
                            'variance', 'is_reconciled', 'is_reviewed']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()

                for item in self.current_session.items:
                    writer.writerow({
                        'payment_method': item.payment_method,
                        'system_amount': f"{item.system_amount:.2f}",
                        'actual_amount': f"{item.actual_amount:.2f}" if item.actual_amount else "0.00",
                        'variance': f"{item.variance:.2f}",
                        'is_reconciled': item.is_reconciled,
                        'is_reviewed': item.is_reviewed
                    })

            # Also export summary info as comments
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n# Summary\n")
                f.write(f"# Period: {self.current_session.start_date} to {self.current_session.end_date}\n")
                f.write(f"# System Total: {self.currency_symbol}{self.current_session.total_system_amount:.2f}\n")
                f.write(f"# Actual Total: {self.currency_symbol}{self.current_session.total_actual_amount:.2f}\n")
                f.write(f"# Total Variance: {self.currency_symbol}{self.current_session.total_variance:.2f}\n")
                f.write(f"# Status: {self.current_session.status}\n")

            messagebox.showinfo("Export Complete",
                              f"Reconciliation data exported to {file_path}")

        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")