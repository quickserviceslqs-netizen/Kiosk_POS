"""Base classes for report generation and formatting."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
from utils.i18n import get_currency_symbol
from utils.date_utils import format_date

from .reports_constants import WINDOW_PADDING, STYLES, HEADER_PADDING, CARD_PADDING

import tkinter as tk
from tkinter import ttk, messagebox

# pagination and export helpers (imported at runtime below to prevent cycles)
from .reports_pagination import ReportPaginator
from .reports_export import ExportManager

logger = logging.getLogger(__name__)


class ReportData:
    """Container for report data and metadata."""

    def __init__(self, report_type: str, start_date: str, end_date: str,
                 data: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None):
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        self.data = data or []
        self.metadata = metadata or {}
        self.generated_at = datetime.now()
        self.currency_symbol = get_currency_symbol()

    @property
    def is_empty(self) -> bool:
        """Check if report has no data."""
        return len(self.data) == 0

    @property
    def record_count(self) -> int:
        """Get number of records in the report."""
        return len(self.data)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get basic summary statistics."""
        if self.is_empty:
            return {}

        return {
            'record_count': self.record_count,
            'generated_at': self.generated_at.isoformat(),
            'date_range': f"{self.start_date} to {self.end_date}"
        }


class ReportFormatter(ABC):
    """Abstract base class for report formatters."""

    def __init__(self, report_data: ReportData):
        self.report_data = report_data
        self.currency_symbol = report_data.currency_symbol

    @abstractmethod
    def format_header(self) -> str:
        """Format the report header."""
        pass

    @abstractmethod
    def format_body(self) -> str:
        """Format the main report content."""
        pass

    @abstractmethod
    def format_footer(self) -> str:
        """Format the report footer."""
        pass

    def format_report(self) -> str:
        """Format the complete report."""
        try:
            header = self.format_header()
            body = self.format_body()
            footer = self.format_footer()
            return f"{header}\n{body}\n{footer}"
        except Exception as e:
            logger.error(f"Error formatting report: {e}")
            return f"Error formatting report: {e}"

    def _format_currency(self, amount: float) -> str:
        """Format currency amount."""
        return f"{self.currency_symbol}{amount:.2f}"

    def _format_percentage(self, value: float, total: float) -> str:
        """Format percentage."""
        if total == 0:
            return "0.0%"
        return f"{(value / total * 100):.1f}%"


class TextReportFormatter(ReportFormatter):
    """Base text formatter for reports."""

    def format_header(self) -> str:
        """Format text report header."""
        title = self._get_report_title()
        separator = "=" * len(title)
        date_info = self._get_date_info()
        return f"{title}\n{separator}\n{date_info}\n"

    def format_footer(self) -> str:
        """Format text report footer."""
        generated_date = format_date(self.report_data.generated_at.date())
        generated_time = self.report_data.generated_at.strftime("%H:%M:%S")
        return f"\nReport generated at: {generated_date} {generated_time}"

    def _get_report_title(self) -> str:
        """Get the report title."""
        return f"{self.report_data.report_type.upper()} REPORT"

    def _get_date_info(self) -> str:
        """Get date range information."""
        from utils.date_utils import format_date
        
        start_display = format_date(self.report_data.start_date)
        end_display = format_date(self.report_data.end_date)
        
        if self.report_data.start_date == self.report_data.end_date:
            return f"Date: {start_display}"
        else:
            return f"Period: {start_display} to {end_display}"


class CSVReportFormatter(ReportFormatter):
    """CSV formatter for reports."""

    def format_header(self) -> str:
        """CSV doesn't need a text header."""
        return ""

    def format_body(self) -> str:
        """Format CSV body - to be implemented by subclasses."""
        return ""

    def format_footer(self) -> str:
        """CSV doesn't need a text footer."""
        return ""

    def get_csv_rows(self) -> List[List[Any]]:
        """Get CSV rows - to be implemented by subclasses."""
        return []


class ReportGenerator(ABC):
    """Abstract base class for report generators."""

    def __init__(self, start_date: str, end_date: str):
        self.start_date = start_date
        self.end_date = end_date

    @abstractmethod
    def generate_data(self) -> ReportData:
        """Generate the report data."""
        pass

    @abstractmethod
    def get_formatter(self, report_data: ReportData) -> ReportFormatter:
        """Get the appropriate formatter for this report."""
        pass

    def generate_report(self) -> ReportData:
        """Generate complete report with data and formatting."""
        try:
            return self.generate_data()
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            # Return empty report data with error info
            return ReportData(
                report_type=self.__class__.__name__,
                start_date=self.start_date,
                end_date=self.end_date,
                data=[],
                metadata={'error': str(e)}
            )

    # Pagination API (optional for each generator)
    def fetch_page(self, page_size: int = 100, cursor: str | None = None) -> tuple[list[Dict], str | None, dict]:
        """Fetch a single page of rows.

        Default implementation materializes the full dataset and slices it in-memory.
        Subclasses that can query pages efficiently should override this method.

        Returns a tuple of (rows, next_cursor, metadata)
        where `rows` is a list of dictionaries, `next_cursor` is an opaque string token
        (or None when no more pages), and `metadata` may contain paging info such as
        total_items.
        """
        # Fallback: generate entire dataset and slice
        report = self.generate_data()
        data = report.data or []
        offset = int(cursor) if cursor else 0
        rows = data[offset:offset + page_size]
        next_cursor = str(offset + len(rows)) if offset + len(rows) < len(data) else None
        metadata = {**report.metadata, 'total_items': len(data)}
        return rows, next_cursor, metadata


class ReportError(Exception):
    """Custom exception for report generation errors."""


class BaseReportFrame(ttk.Frame):
    """Shared UI frame logic for report pages.

    Subclasses should call :meth:`build_filters` and supply a
    `report_type` when invoking :meth:`generate_report`.
    """

    def __init__(self, parent: tk.Misc, service=None, **kwargs):
        super().__init__(parent, **kwargs)
        if service is None:
            from .reports_controller import ReportController
            service = ReportController()
        self.service = service
        self.start_date = tk.StringVar()
        self.end_date = tk.StringVar()
        self.status_filter = tk.StringVar(value="all")
        self._local_date_vars: dict = {}
        self._local_status_vars: dict = {}
        self.current_request_id = None
        self.paginator = ReportPaginator()
        self.export_manager = ExportManager()
        self.current_report_data = None
        self._paging_state = None

        # build basic UI containers
        self.configure(padding=WINDOW_PADDING)
        self._build_header()
        self.content_frame = ttk.Frame(self, style=STYLES['frame'])
        self.content_frame.grid(row=1, column=0, sticky=tk.NSEW)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def _build_header(self):
        """Override in subclass to create nav or title area."""
        pass

    def build_filters(self, parent, include_status=False):
        """Construct filter widgets (date range and optional status)."""
        frame = ttk.Frame(parent, style=STYLES['frame'])
        ttk.Label(frame, text="Start:", style=STYLES['body_label']).grid(row=0, column=0, padx=4)
        ttk.Entry(frame, textvariable=self.start_date, width=10).grid(row=0, column=1, padx=4)
        ttk.Label(frame, text="End:", style=STYLES['body_label']).grid(row=0, column=2, padx=4)
        ttk.Entry(frame, textvariable=self.end_date, width=10).grid(row=0, column=3, padx=4)
        if include_status:
            ttk.Label(frame, text="Status:", style=STYLES['body_label']).grid(row=0, column=4, padx=(20,4))
            ttk.Combobox(frame, textvariable=self.status_filter,
                         values=["all","draft","completed","approved"], state="readonly", width=12).grid(row=0, column=5)
        return frame

    def show_loading(self):
        """Display a simple loading overlay in the content area."""
        for w in self.content_frame.winfo_children():
            w.destroy()
        lbl = ttk.Label(self.content_frame, text="⏳ Loading report...", style=STYLES['subheader_label'])
        lbl.pack(pady=20)
        self.progress = ttk.Progressbar(self.content_frame, mode='indeterminate')
        self.progress.pack(pady=10)
        self.progress.start()

    def hide_loading(self):
        try:
            self.progress.stop()
            self.progress.destroy()
        except Exception:
            pass

    def generate_report(self, report_type: str, start=None, end=None, status=None):
        """Wrapper to call controller asynchronously and handle callback."""
        if start:
            self.start_date.set(start)
        if end:
            self.end_date.set(end)
        if status:
            self.status_filter.set(status)
        self.show_loading()

        iso_start = self.start_date.get()
        iso_end = self.end_date.get()
        status_val = self.status_filter.get()

        def on_complete(rd: ReportData):
            self.after(0, lambda: self.display_report(rd))

        try:
            self.current_request_id = self.service.generate_report_async(
                report_type, iso_start, iso_end, on_complete, status_val
            )
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            self.hide_loading()
            messagebox.showerror("Error", str(e))

    def display_report(self, report_data: ReportData):
        """Basic display logic; subclasses may override or extend.

        This implementation renders a paginated table if data rows are
        present.  It uses :class:`ReportPaginator` to manage paging.  The
        table is created inside ``self.content_frame``.
        """
        self.hide_loading()
        if report_data.metadata.get('error'):
            messagebox.showerror("Report Error", report_data.metadata['error'])
            return
        self.current_report_data = report_data
        # clear existing content
        for w in self.content_frame.winfo_children():
            w.destroy()
        data = report_data.data or []
        self.paginator.set_data(data)
        # use helper to build table within content_frame
        self._render_page()

    def render_table(self, parent, data: List[Dict[str, Any]]):
        """Render a paginated table inside *parent* widget.

        Returns a tuple (tree, nav_frame) where ``nav_frame`` contains
        the prev/next buttons if paging is required.
        """
        # clear parent children
        for w in parent.winfo_children():
            w.destroy()
        self.paginator.set_data(data)
        page = self.paginator.get_page(data)
        if not page:
            ttk.Label(parent, text="No data", style=STYLES['body_label']).pack(pady=20)
            return None, None

        cols = list(page[0].keys())
        tree = ttk.Treeview(parent, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c.replace('_', ' ').title())
            tree.column(c, anchor=tk.W)
        for row in page:
            tree.insert('', tk.END, values=[row.get(c) for c in cols])
        tree.pack(fill=tk.BOTH, expand=True)

        nav = ttk.Frame(parent, style=STYLES['frame'])
        nav.pack(fill=tk.X, pady=(6,0))
        prev_btn = ttk.Button(nav, text='◀ Prev', command=self.prev_page)
        prev_btn.pack(side=tk.LEFT)
        next_btn = ttk.Button(nav, text='Next ▶', command=self.next_page)
        next_btn.pack(side=tk.LEFT, padx=(6,0))
        self._page_buttons = (prev_btn, next_btn)
        self._update_page_buttons()
        return tree, nav

    def _render_page(self):
        """Render the current page of data inside content_frame."""
        # called by display_report and page navigation
        for w in self.content_frame.winfo_children():
            w.destroy()

        data = self.current_report_data.data or []
        page = self.paginator.get_page(data)
        if not page:
            ttk.Label(self.content_frame, text="No data", style=STYLES['body_label']).pack(pady=20)
            return

        # build treeview
        cols = list(page[0].keys())
        tree = ttk.Treeview(self.content_frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c.replace('_', ' ').title())
            tree.column(c, anchor=tk.W)
        for row in page:
            tree.insert('', tk.END, values=[row.get(c) for c in cols])
        tree.pack(fill=tk.BOTH, expand=True)

        # paging controls
        nav = ttk.Frame(self.content_frame, style=STYLES['frame'])
        nav.pack(fill=tk.X, pady=(6,0))
        prev_btn = ttk.Button(nav, text='◀ Prev', command=self.prev_page)
        prev_btn.pack(side=tk.LEFT)
        next_btn = ttk.Button(nav, text='Next ▶', command=self.next_page)
        next_btn.pack(side=tk.LEFT, padx=(6,0))
        self._page_buttons = (prev_btn, next_btn)
        self._update_page_buttons()

    def _update_page_buttons(self):
        """Enable/disable page buttons based on paginator state."""
        if not hasattr(self, '_page_buttons'):
            return
        prev_btn, next_btn = self._page_buttons
        info = self.paginator.get_page_info()
        prev_btn.config(state=tk.NORMAL if info['has_prev'] else tk.DISABLED)
        next_btn.config(state=tk.NORMAL if info['has_next'] else tk.DISABLED)

    # paging helpers reused by subclasses
    def prev_page(self):
        if self.paginator.prev_page():
            self._render_page()

    def next_page(self):
        if self.paginator.next_page():
            self._render_page()

    def export_current(self, format_type: str):
        if self.current_report_data:
            self.export_manager.export(self.current_report_data, format_type)



class ReportValidationError(ReportError):
    """Exception for report validation errors."""
    pass