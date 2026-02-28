"""
Stock Reconciliation UI

Daily stock reconciliation by comparing physical counts against POS records.
Supports:
- Creating a session for a specific date
- Auto-populating opening stock, received, POS sales
- User enters actual physical count
- System calculates variance per item
- Save as draft / complete
- View past sessions
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import csv
from datetime import datetime, timedelta
from typing import Optional, Callable
from pathlib import Path

try:
    from tkcalendar import Calendar
    TKCALENDAR_AVAILABLE = True
except ImportError:
    TKCALENDAR_AVAILABLE = False

from modules.stock_reconciliation import (
    StockReconSession, StockReconEntry,
    create_stock_recon_session, save_stock_recon_session,
    get_stock_recon_session, get_stock_recon_sessions,
    complete_stock_recon_session, delete_stock_recon_session,
    update_entry_actual, get_stock_recon_summary,
    calculate_stock_date_range,
)
from utils.i18n import get_currency_symbol
from utils.app_config import get_or_create_config
from utils import set_window_icon
from utils.date_utils import format_date, parse_date_flexible
from utils.security import get_username
from modules import permissions

logger = logging.getLogger(__name__)


class StockReconciliationUI(ttk.Frame):
    """Stock reconciliation UI – compare physical counts vs POS records."""

    def __init__(self, parent: tk.Misc, *, on_home: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)

        # Permission check
        current_username = get_username()
        if not permissions.has_permission(current_username, 'view_reconciliation'):
            messagebox.showerror("Permission Denied",
                                 "You do not have permission to view reconciliation")
            return

        self.currency_symbol = get_currency_symbol()
        self.current_session: Optional[StockReconSession] = None
        self.on_home = on_home
        self._search_var = tk.StringVar()

        root = parent.winfo_toplevel()
        self.current_user = getattr(root, "current_user", {})
        self.user_id = self.current_user.get("user_id", 1)

        self.configure(padding=10)
        self._current_view = "create"  # track active internal view
        self._build_ui()



    # ------------------------------------------------------------------
    #  UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Title + Refresh button
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="Stock Reconciliation",
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        ttk.Button(title_frame, text="🔄 Refresh",
                   command=self.refresh).pack(side=tk.RIGHT)

        # Navigation bar
        nav_frame = ttk.Frame(self)
        nav_frame.pack(fill=tk.X, pady=(0, 10))

        self.nav_buttons = {}
        nav_options = [
            ("create", "New Session"),
            ("manage", "Past Sessions"),
            ("reconcile", "Reconcile"),
            ("save_draft", "💾 Save Draft"),
            ("complete", "✅ Complete"),
        ]
        for key, label in nav_options:
            if key in ("save_draft", "complete", "reconcile"):
                btn = ttk.Button(nav_frame, text=label, state="disabled",
                                 command=lambda k=key: self._handle_action(k))
            else:
                btn = ttk.Button(nav_frame, text=label,
                                 command=lambda k=key: self._switch_view(k))
            btn.pack(side=tk.LEFT, padx=(0, 10))
            self.nav_buttons[key] = btn

        # Content area
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self._switch_view("create")

    # ------------------------------------------------------------------
    #  Navigation helpers
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Reload the current view in-place (preserves session)."""
        logger.info("Refreshing stock recon view: %s", self._current_view)
        self._switch_view(self._current_view)

    def _switch_view(self, view: str) -> None:
        self._current_view = view
        for key, btn in self.nav_buttons.items():
            if key == view:
                btn.config(style="Accent.TButton")
            elif key not in ("save_draft", "complete", "reconcile"):
                btn.config(style="TButton")

        has_session = self.current_session is not None
        on_recon = view == "reconcile"
        self.nav_buttons["save_draft"].config(
            state="normal" if has_session and on_recon else "disabled")
        self.nav_buttons["complete"].config(
            state="normal" if has_session and on_recon else "disabled")
        self.nav_buttons["reconcile"].config(
            state="normal" if has_session else "disabled")

        for w in self.content_frame.winfo_children():
            w.destroy()

        if view == "create":
            self._show_create()
        elif view == "manage":
            self._show_manage()
        elif view == "reconcile":
            self._show_reconcile()

    def _handle_action(self, action: str) -> None:
        if action == "reconcile":
            self._switch_view("reconcile")
        elif action == "save_draft":
            self._save_draft()
        elif action == "complete":
            self._complete_session()

    # ------------------------------------------------------------------
    #  CREATE view
    # ------------------------------------------------------------------
    def _show_create(self) -> None:
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Create Stock Reconciliation Session",
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))

        # ── Period type selection ──
        period_frame = ttk.LabelFrame(frame, text="Select Period", padding=10)
        period_frame.pack(fill=tk.X, pady=(0, 15))

        type_row = ttk.Frame(period_frame)
        type_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(type_row, text="Period Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.period_type_var = tk.StringVar(value="daily")
        period_combo = ttk.Combobox(type_row, textvariable=self.period_type_var,
                                    values=["daily", "weekly", "monthly", "custom"],
                                    state="readonly", width=14)
        period_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        period_combo.bind("<<ComboboxSelected>>", self._on_period_type_change)

        # ── Reference date ──
        date_row = ttk.Frame(period_frame)
        date_row.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(date_row, text="Reference Date:").pack(side=tk.LEFT, padx=(0, 10))

        self.recon_date_var = tk.StringVar(value=format_date(datetime.now()))
        date_entry = ttk.Entry(date_row, textvariable=self.recon_date_var, width=14)
        date_entry.pack(side=tk.LEFT, padx=(0, 5))
        # Update computed range whenever user edits the reference date
        self.recon_date_var.trace_add("write", lambda *_: self._update_computed_range())

        ttk.Button(date_row, text="📅", width=3,
                   command=self._pick_date).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(date_row, text="Today",
                   command=lambda: self.recon_date_var.set(
                       format_date(datetime.now()))).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(date_row, text="Yesterday",
                   command=lambda: self.recon_date_var.set(
                       format_date(datetime.now() - timedelta(days=1))
                   )).pack(side=tk.LEFT)

        # ── Computed / custom date range ──
        range_row = ttk.Frame(period_frame)
        range_row.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(range_row, text="Start Date:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.start_date_var = tk.StringVar()
        self.start_date_entry = ttk.Entry(range_row, textvariable=self.start_date_var, width=14, state="readonly")
        self.start_date_entry.grid(row=0, column=1, padx=(0, 5))
        self.start_cal_btn = ttk.Button(range_row, text="📅", width=3, state="disabled",
                                        command=lambda: self._pick_date_for(self.start_date_var))
        self.start_cal_btn.grid(row=0, column=2, padx=(0, 20))

        ttk.Label(range_row, text="End Date:").grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        self.end_date_var = tk.StringVar()
        self.end_date_entry = ttk.Entry(range_row, textvariable=self.end_date_var, width=14, state="readonly")
        self.end_date_entry.grid(row=0, column=4, padx=(0, 5))
        self.end_cal_btn = ttk.Button(range_row, text="📅", width=3, state="disabled",
                                      command=lambda: self._pick_date_for(self.end_date_var))
        self.end_cal_btn.grid(row=0, column=5)

        # Populate initial range
        self._update_computed_range()

        # Create button + status (above info box so it's always visible)
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Button(action_frame, text="▶ Create Session",
                   command=self._create_session).pack(side=tk.LEFT, padx=(0, 15))
        self.create_status_var = tk.StringVar()
        ttk.Label(action_frame, textvariable=self.create_status_var,
                  foreground="blue").pack(side=tk.LEFT)

        # Info box with scrollbar
        info_frame = ttk.LabelFrame(frame, text="How It Works", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        info_text = (
            "Stock reconciliation compares your physical stock count against POS records.\n\n"
            "Formula:\n"
            "  Expected Closing = Opening Stock + Received − POS Sales − Other Outflows\n"
            "  Variance = Actual Count − Expected Closing\n\n"
            "Period types:\n"
            "  • Daily – single day\n"
            "  • Weekly – Monday to Sunday of the week containing the reference date\n"
            "  • Monthly – 1st to last day of the month containing the reference date\n"
            "  • Custom – you choose start and end dates\n\n"
            "Opening stock is automatically taken from:\n"
            "  • Previous completed reconciliation's actual closing, or\n"
            "  • Back-calculated from current system stock if no prior reconciliation exists."
        )

        text_container = ttk.Frame(info_frame)
        text_container.pack(fill=tk.X, expand=False)

        info_widget = tk.Text(text_container, wrap=tk.WORD, font=("Segoe UI", 9),
                              height=6, relief=tk.FLAT, bg=info_frame.winfo_toplevel().cget("bg"),
                              cursor="arrow", padx=4, pady=4)
        info_scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL,
                                       command=info_widget.yview)
        info_widget.configure(yscrollcommand=info_scrollbar.set)

        info_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        info_widget.insert(tk.END, info_text)
        info_widget.configure(state=tk.DISABLED)

    def _on_period_type_change(self, event=None) -> None:
        """Handle period type combobox change."""
        pt = self.period_type_var.get()
        is_custom = pt == "custom"

        # Enable/disable manual editing of start/end dates
        state = "normal" if is_custom else "readonly"
        btn_state = "normal" if is_custom else "disabled"

        self.start_date_entry.config(state=state)
        self.end_date_entry.config(state=state)
        self.start_cal_btn.config(state=btn_state)
        self.end_cal_btn.config(state=btn_state)

        if not is_custom:
            self._update_computed_range()

    def _update_computed_range(self) -> None:
        """Recompute the start/end dates from the reference date and period type."""
        pt = self.period_type_var.get()
        if pt == "custom":
            return  # user controls these manually

        ref = self.recon_date_var.get()
        try:
            sd, ed = calculate_stock_date_range(pt, ref)
            self.start_date_var.set(sd)
            self.end_date_var.set(ed)
        except Exception:
            pass  # date might be partially typed

    def _pick_date_for(self, date_var: tk.StringVar) -> None:
        """Open a calendar picker that writes into the given StringVar."""
        dialog = tk.Toplevel(self)
        dialog.title("Select Date")
        dialog.geometry("300x300")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        set_window_icon(dialog)

        try:
            cur = parse_date_flexible(date_var.get())
        except Exception:
            cur = datetime.now()

        if TKCALENDAR_AVAILABLE:
            cal = Calendar(dialog, selectmode="day",
                           year=cur.year, month=cur.month, day=cur.day,
                           date_pattern="yyyy-mm-dd",
                           font=("Segoe UI", 10))
            cal.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

            def select():
                date_var.set(cal.get_date())
                dialog.destroy()

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
            ttk.Button(btn_frame, text="Select", command=select).pack(side=tk.RIGHT)
            ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=(0, 5))
            cal.bind("<<CalendarSelected>>", lambda e: select())
        else:
            ttk.Label(dialog, text="Enter date (YYYY-MM-DD):").pack(pady=10)
            e = ttk.Entry(dialog)
            e.insert(0, date_var.get())
            e.pack(pady=5)
            ttk.Button(dialog, text="OK",
                       command=lambda: (date_var.set(e.get()), dialog.destroy())).pack(pady=10)

    def _pick_date(self) -> None:
        self._pick_date_for(self.recon_date_var)

    def _create_session(self) -> None:
        current_username = get_username()
        if not permissions.has_permission(current_username, 'create_reconciliation'):
            messagebox.showerror("Permission Denied",
                                 "You do not have permission to create reconciliation sessions")
            return

        date_str = self.recon_date_var.get()
        try:
            parse_date_flexible(date_str)
        except Exception:
            messagebox.showerror("Invalid Date", "Please enter a valid reference date.")
            return

        period_type = self.period_type_var.get()
        start_date = self.start_date_var.get()
        end_date = self.end_date_var.get()

        # Validate custom dates
        if period_type == "custom":
            if not start_date or not end_date:
                messagebox.showerror("Missing Dates",
                                     "Please set both start and end dates for a custom period.")
                return
            try:
                parse_date_flexible(start_date)
                parse_date_flexible(end_date)
            except Exception:
                messagebox.showerror("Invalid Date", "Start or end date is invalid.")
                return

        try:
            self.create_status_var.set("⏳ Loading stock data…")
            self.update_idletasks()
            self.config(cursor="wait")

            # Normalise dates to YYYY-MM-DD
            dt = parse_date_flexible(date_str)
            iso_date = dt.strftime("%Y-%m-%d")

            if period_type == "custom":
                sd = parse_date_flexible(start_date).strftime("%Y-%m-%d")
                ed = parse_date_flexible(end_date).strftime("%Y-%m-%d")
            else:
                sd, ed = calculate_stock_date_range(period_type, iso_date)

            logger.info("Creating stock recon session: period=%s, range=%s to %s",
                        period_type, sd, ed)

            self.current_session = create_stock_recon_session(
                iso_date, self.user_id,
                period_type=period_type,
                start_date=sd,
                end_date=ed,
            )
            self.config(cursor="")

            if not self.current_session.entries:
                self.create_status_var.set("⚠ No items found in inventory.")
                logger.warning("Stock recon session created with 0 entries")
                return

            logger.info("Stock recon session created with %d items, switching to reconcile view",
                        len(self.current_session.entries))

            # Switch to reconcile view (do NOT set create_status_var after
            # this, because _switch_view destroys the label it's bound to)
            self._switch_view("reconcile")

        except Exception as e:
            self.config(cursor="")
            logger.exception("Failed to create stock recon session")
            messagebox.showerror("Error", f"Failed to create session:\n{e}")
            self.create_status_var.set(f"✗ Error: {e}")

    # ------------------------------------------------------------------
    #  MANAGE (past sessions) view
    # ------------------------------------------------------------------
    def _show_manage(self) -> None:
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Past Stock Reconciliation Sessions",
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))

        cols = ("session_id", "date", "period", "range", "status", "items", "variance", "completed")
        self.sessions_tree = ttk.Treeview(frame, columns=cols, show="headings", height=12)
        self.sessions_tree.heading("session_id", text="ID")
        self.sessions_tree.heading("date", text="Ref Date")
        self.sessions_tree.heading("period", text="Period")
        self.sessions_tree.heading("range", text="Date Range")
        self.sessions_tree.heading("status", text="Status")
        self.sessions_tree.heading("items", text="Items")
        self.sessions_tree.heading("variance", text="Total Variance")
        self.sessions_tree.heading("completed", text="Completed At")

        self.sessions_tree.column("session_id", width=40, anchor="center")
        self.sessions_tree.column("date", width=95, anchor="center")
        self.sessions_tree.column("period", width=70, anchor="center")
        self.sessions_tree.column("range", width=170, anchor="center")
        self.sessions_tree.column("status", width=75, anchor="center")
        self.sessions_tree.column("items", width=50, anchor="center")
        self.sessions_tree.column("variance", width=100, anchor="e")
        self.sessions_tree.column("completed", width=140, anchor="center")

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.sessions_tree.yview)
        self.sessions_tree.configure(yscrollcommand=vsb.set)
        self.sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="📂 Load Session",
                   command=self._load_selected_session).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="🗑️ Delete",
                   command=self._delete_selected_session).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="🔄 Refresh",
                   command=self._load_sessions_list).pack(side=tk.LEFT)

        self._load_sessions_list()

    def _load_sessions_list(self) -> None:
        for i in self.sessions_tree.get_children():
            self.sessions_tree.delete(i)

        try:
            sessions = get_stock_recon_sessions(limit=50)
            for s in sessions:
                # Load full session to get entry count and variance
                full = get_stock_recon_session(s.session_id)
                item_count = len(full.entries) if full else 0
                total_var = sum(e.variance for e in full.entries) if full else 0.0

                self.sessions_tree.insert("", tk.END, values=(
                    s.session_id,
                    s.reconciliation_date,
                    s.period_type.title(),
                    f"{s.start_date} → {s.end_date}" if s.start_date else s.reconciliation_date,
                    s.status.title(),
                    item_count,
                    f"{total_var:+.1f}",
                    s.completed_at or "—",
                ))
        except Exception as e:
            logger.exception("Failed to load stock recon sessions")
            messagebox.showerror("Error", str(e))

    def _load_selected_session(self) -> None:
        sel = self.sessions_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a session to load.")
            return
        sid = self.sessions_tree.item(sel[0])["values"][0]
        session = get_stock_recon_session(sid)
        if session:
            self.current_session = session
            self._switch_view("reconcile")
        else:
            messagebox.showerror("Error", "Session not found.")

    def _delete_selected_session(self) -> None:
        sel = self.sessions_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a session to delete.")
            return
        sid = self.sessions_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm", f"Delete session #{sid}?"):
            delete_stock_recon_session(sid)
            self._load_sessions_list()

    # ------------------------------------------------------------------
    #  RECONCILE view – main data entry table
    # ------------------------------------------------------------------
    def _show_reconcile(self) -> None:
        logger.info("Showing reconcile view, session=%s, entries=%d",
                    self.current_session.session_id if self.current_session else None,
                    len(self.current_session.entries) if self.current_session else 0)

        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if not self.current_session:
            ttk.Label(frame, text="No session loaded.",
                      font=("Segoe UI", 12)).pack(pady=20)
            ttk.Button(frame, text="Create New Session",
                       command=lambda: self._switch_view("create")).pack()
            return

        # Session info header
        info_frame = ttk.LabelFrame(frame, text="Session Information", padding=8)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        status_text = "Unsaved Draft" if self.current_session.session_id is None \
            else f"{self.current_session.status.title()} (ID #{self.current_session.session_id})"

        period_label = self.current_session.period_type.title()
        range_label = (f"{self.current_session.start_date} → {self.current_session.end_date}"
                       if self.current_session.start_date
                       else self.current_session.reconciliation_date)

        ttk.Label(info_frame, text=f"Period: {period_label}"
                  ).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Label(info_frame, text=f"Range: {range_label}"
                  ).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Label(info_frame, text=f"Status: {status_text}"
                  ).grid(row=0, column=2, sticky=tk.W, padx=(0, 20))
        ttk.Label(info_frame, text=f"Items: {len(self.current_session.entries)}"
                  ).grid(row=0, column=3, sticky=tk.W)

        # Search / filter bar
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self._search_var.set("")
        search_entry = ttk.Entry(filter_frame, textvariable=self._search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        self._show_variance_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="Show variance only",
                        variable=self._show_variance_only,
                        command=self._apply_filter).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(filter_frame, text="📥 Export CSV",
                   command=self._export_csv).pack(side=tk.RIGHT)

        # Instruction banner
        if self.current_session.status == "draft":
            counted = sum(1 for e in self.current_session.entries if e.actual_closing > 0)
            total = len(self.current_session.entries)
            instr_frame = ttk.Frame(frame, style="Card.TLabelframe")
            instr_frame.pack(fill=tk.X, pady=(0, 5))
            instr_text = (f"📋  {total} items loaded.  "
                         f"Double-click the 'Actual Count' column to enter your physical stock counts.  "
                         f"({counted}/{total} counted)")
            ttk.Label(instr_frame, text=instr_text,
                      font=("Segoe UI", 10), foreground="#1565C0",
                      padding=(8, 6)).pack(fill=tk.X)

        # Main table
        cols = ("item", "opening", "received", "pos_sales", "other_out",
                "expected", "actual", "variance")

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.recon_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=20)

        headings = {
            "item": ("Item", 180, "w"),
            "opening": ("Opening", 80, "e"),
            "received": ("Received", 80, "e"),
            "pos_sales": ("POS Sales", 80, "e"),
            "other_out": ("Other Out", 80, "e"),
            "expected": ("Expected", 80, "e"),
            "actual": ("Actual Count", 100, "e"),
            "variance": ("Variance", 90, "e"),
        }
        for col, (text, width, anchor) in headings.items():
            self.recon_tree.heading(col, text=text)
            self.recon_tree.column(col, width=width, anchor=anchor)

        # Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.recon_tree.yview)
        self.recon_tree.configure(yscrollcommand=vsb.set)

        self.recon_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click for inline edit on Actual Count column
        self.recon_tree.bind("<Double-1>", self._on_double_click)

        # Load data
        self._load_recon_data()

        # Tip
        ttk.Label(frame, text="💡 Double-click the 'Actual Count' column to enter physical counts",
                  font=("Segoe UI", 9), foreground="gray").pack(anchor=tk.W, pady=(5, 0))

        # Summary bar
        self.summary_frame = ttk.LabelFrame(frame, text="Summary", padding=8)
        self.summary_frame.pack(fill=tk.X, pady=(10, 0))
        self._update_summary()

    def _load_recon_data(self, filter_text: str = "", variance_only: bool = False) -> None:
        for i in self.recon_tree.get_children():
            self.recon_tree.delete(i)

        if not self.current_session:
            return

        for entry in self.current_session.entries:
            # Apply filter
            if filter_text and filter_text.lower() not in entry.item_name.lower():
                continue
            if variance_only and abs(entry.variance) < 0.01:
                continue

            # Colour-code variance
            tag = ""
            if entry.actual_closing > 0:  # has been counted
                if abs(entry.variance) < 0.01:
                    tag = "ok"
                elif entry.variance < 0:
                    tag = "short"
                else:
                    tag = "over"

            self.recon_tree.insert("", tk.END, iid=str(entry.item_id), values=(
                entry.item_name,
                f"{entry.opening_stock:.1f}",
                f"{entry.stock_received:.1f}",
                f"{entry.system_sales:.1f}",
                f"{entry.other_out:.1f}",
                f"{entry.expected_closing:.1f}",
                f"{entry.actual_closing:.1f}" if entry.actual_closing > 0 else ">> enter",
                f"{entry.variance:+.1f}" if entry.actual_closing > 0 else "—",
            ), tags=(tag,))

        # Configure tag colours
        self.recon_tree.tag_configure("ok", foreground="green")
        self.recon_tree.tag_configure("short", foreground="red")
        self.recon_tree.tag_configure("over", foreground="orange")

    def _apply_filter(self) -> None:
        self._load_recon_data(
            filter_text=self._search_var.get(),
            variance_only=self._show_variance_only.get(),
        )

    def _on_double_click(self, event) -> None:
        region = self.recon_tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        col = self.recon_tree.identify_column(event.x)
        item_iid = self.recon_tree.identify_row(event.y)
        if not item_iid:
            return

        col_idx = int(col[1:]) - 1  # 0-based

        # Only allow editing the "actual" column (index 6)
        if col_idx != 6:
            return

        # Check if session is completed
        if self.current_session and self.current_session.status == "completed":
            messagebox.showinfo("Read Only",
                                "This session is completed. Create a new session to re-count.")
            return

        self._edit_actual_inline(item_iid, col_idx)

    def _edit_actual_inline(self, item_iid: str, col_idx: int) -> None:
        """Open an inline editor for the actual count cell."""
        x, y, w, h = self.recon_tree.bbox(item_iid, col_idx)

        entry = ttk.Entry(self.recon_tree, justify="right", font=("Segoe UI", 9))

        # Get current value
        current = self.recon_tree.set(item_iid, self.recon_tree["columns"][col_idx])
        clean = current.replace("—", "").replace(",", "").strip()
        if clean:
            entry.insert(0, clean)
        entry.select_range(0, tk.END)
        entry.focus()
        entry.place(x=x, y=y, width=w, height=h)

        def save():
            try:
                val_str = entry.get().strip()
                val = float(val_str) if val_str else 0.0

                item_id = int(item_iid)
                update_entry_actual(self.current_session, item_id, val)

                # Refresh that row
                for e in self.current_session.entries:
                    if e.item_id == item_id:
                        tag = ""
                        if abs(e.variance) < 0.01:
                            tag = "ok"
                        elif e.variance < 0:
                            tag = "short"
                        else:
                            tag = "over"

                        self.recon_tree.item(item_iid, values=(
                            e.item_name,
                            f"{e.opening_stock:.1f}",
                            f"{e.stock_received:.1f}",
                            f"{e.system_sales:.1f}",
                            f"{e.other_out:.1f}",
                            f"{e.expected_closing:.1f}",
                            f"{e.actual_closing:.1f}",
                            f"{e.variance:+.1f}",
                        ), tags=(tag,))
                        break

                self._update_summary()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number.")
            finally:
                entry.destroy()

        entry.bind("<Return>", lambda e: save())
        entry.bind("<Escape>", lambda e: entry.destroy())
        entry.bind("<FocusOut>", lambda e: save())

    def _update_summary(self) -> None:
        """Update the summary bar."""
        for w in self.summary_frame.winfo_children():
            w.destroy()

        if not self.current_session:
            return

        summary = get_stock_recon_summary(self.current_session)

        labels = [
            ("Total Items", str(summary["total_items"])),
            ("Counted", str(summary["counted_items"])),
            ("Uncounted", str(summary["uncounted_items"])),
            ("With Variance", str(summary["items_with_variance"])),
            ("Total Variance (Qty)", f"{summary['total_variance_qty']:+.1f}"),
            ("POS Sales (Qty)", f"{summary['total_system_sales']:.1f}"),
            ("Actual Sales (Qty)", f"{summary['total_actual_sales']:.1f}"),
            ("Sales Variance", f"{summary['sales_variance']:+.1f}"),
        ]

        for i, (label, value) in enumerate(labels):
            ttk.Label(self.summary_frame, text=f"{label}:",
                      font=("Segoe UI", 9, "bold")).grid(row=0, column=i * 2, sticky=tk.W, padx=(10, 2))
            val_label = ttk.Label(self.summary_frame, text=value,
                                  font=("Segoe UI", 9))
            val_label.grid(row=0, column=i * 2 + 1, sticky=tk.W, padx=(0, 10))

            # Colour variance labels
            if "variance" in label.lower():
                try:
                    v = float(value.replace("+", ""))
                    if abs(v) < 0.01:
                        val_label.config(foreground="green")
                    else:
                        val_label.config(foreground="red")
                except ValueError:
                    pass

    # ------------------------------------------------------------------
    #  Actions
    # ------------------------------------------------------------------
    def _save_draft(self) -> None:
        if not self.current_session:
            return
        try:
            self.current_session.status = "draft"
            sid = save_stock_recon_session(self.current_session)
            self.current_session.session_id = sid
            messagebox.showinfo("Saved", f"Session saved as draft (ID #{sid}).")
            self._switch_view("reconcile")
        except Exception as e:
            logger.exception("Failed to save draft")
            messagebox.showerror("Error", str(e))

    def _complete_session(self) -> None:
        if not self.current_session:
            return

        # Check all items counted
        uncounted = sum(1 for e in self.current_session.entries if e.actual_closing <= 0)
        if uncounted > 0:
            proceed = messagebox.askyesno(
                "Uncounted Items",
                f"{uncounted} items have not been counted (actual = 0).\n\n"
                "Items with 0 actual count will show as full variance.\n"
                "Continue anyway?"
            )
            if not proceed:
                return

        # Save first
        self.current_session.status = "draft"
        sid = save_stock_recon_session(self.current_session)
        self.current_session.session_id = sid

        # Complete
        if complete_stock_recon_session(sid):
            self.current_session.status = "completed"
            self.current_session.completed_at = datetime.now().isoformat()
            messagebox.showinfo("Completed",
                                f"Session #{sid} marked as completed.\n"
                                "Tomorrow's reconciliation will use today's actual counts as opening stock.")
            self._switch_view("reconcile")
        else:
            messagebox.showerror("Error", "Failed to complete session.")

    def _export_csv(self) -> None:
        if not self.current_session:
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"stock_recon_{self.current_session.reconciliation_date}.csv",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Item", "Opening Stock", "Received", "POS Sales",
                    "Other Out", "Expected Closing", "Actual Count", "Variance",
                ])
                for e in self.current_session.entries:
                    writer.writerow([
                        e.item_name, e.opening_stock, e.stock_received,
                        e.system_sales, e.other_out, e.expected_closing,
                        e.actual_closing, e.variance,
                    ])

            messagebox.showinfo("Exported", f"Data exported to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
