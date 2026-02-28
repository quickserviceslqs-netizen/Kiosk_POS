"""Reconciliation report generators and formatters."""

from typing import Dict, List, Any, Optional
import logging

from .reports_base import ReportGenerator, ReportData, TextReportFormatter
from .reports_reconciliation_formatters import (
    ReconciliationSummaryTextFormatter, ReconciliationDetailsTextFormatter
)
from .reports_constants import REPORT_LIMITS
from modules.reconciliation_core import get_reconciliation_sessions, get_reconciliation_session

logger = logging.getLogger(__name__)


class ReconciliationSummaryGenerator(ReportGenerator):
    """Generator for reconciliation summary reports."""

    def __init__(self, start_date: str, end_date: str, status_filter: str = "all"):
        super().__init__(start_date, end_date)
        self.status_filter = status_filter

    def generate_data(self) -> ReportData:
        """Generate reconciliation summary data."""
        sessions = get_reconciliation_sessions(
            start_date=self.start_date,
            end_date=self.end_date,
            status=None if self.status_filter == "all" else self.status_filter
        )

        if sessions:
            # Group by status
            status_counts = {}
            total_variance = 0
            total_system = 0
            total_actual = 0

            for session in sessions:
                status_name = session['status']
                status_counts[status_name] = status_counts.get(status_name, 0) + 1
                total_variance += session.get('total_variance', 0) or 0
                total_system += session.get('total_system_sales', 0) or 0
                total_actual += session.get('total_actual_cash', 0) or 0

            metadata = {
                'status_counts': status_counts,
                'total_variance': total_variance,
                'total_system': total_system,
                'total_actual': total_actual,
                'session_count': len(sessions),
                'status_filter': self.status_filter
            }
        else:
            metadata = {'status_filter': self.status_filter}

        return ReportData('reconciliation_summary', self.start_date, self.end_date, sessions, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get reconciliation summary formatter."""
        return ReconciliationSummaryTextFormatter(report_data)


class ReconciliationDetailsGenerator(ReportGenerator):
    """Generator for reconciliation details reports."""

    def __init__(self, start_date: str, end_date: str, status_filter: str = "all"):
        super().__init__(start_date, end_date)
        self.status_filter = status_filter

    def generate_data(self) -> ReportData:
        """Generate reconciliation details data."""
        sessions = get_reconciliation_sessions(
            start_date=self.start_date,
            end_date=self.end_date,
            status=None if self.status_filter == "all" else self.status_filter
        )

        # Get detailed session data
        detailed_sessions = []
        for session in sessions[:REPORT_LIMITS['reconciliation_sessions']]:
            try:
                session_details = get_reconciliation_session(session['session_id'])
                if session_details:
                    detailed_sessions.append(session_details)
            except Exception as e:
                logger.warning(f"Could not get details for session {session['session_id']}: {e}")

        metadata = {
            'session_count': len(detailed_sessions),
            'total_sessions': len(sessions),
            'status_filter': self.status_filter
        }

        return ReportData('reconciliation_details', self.start_date, self.end_date, detailed_sessions, metadata)

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get reconciliation details formatter."""
        return ReconciliationDetailsTextFormatter(report_data)

    def fetch_page(self, page_size: int = 20, cursor: str | None = None, use_keyset: bool = False) -> tuple[list[dict], str | None, dict]:
        """Fetch a page of reconciliation detail sessions.

        Supports offset pagination (cursor is offset string). Keyset pagination is not natively supported by the underlying service; when use_keyset=True we'll fall back to offset style but expose same API.
        """
        try:
            # If keyset requested but not supported, fall back to offset pagination
            if use_keyset:
                # Interpret cursor as last_session_id token 'key:<id>' and perform an offset-based scan to find next page
                if cursor and cursor.startswith('key:'):
                    last_id = int(cursor[4:])
                    # Fetch sessions until we find sessions with id less than last_id
                    # For simplicity, perform an offset scan in chunks until we collect page_size rows
                    offset = 0
                    collected = []
                    while len(collected) < page_size:
                        chunk = get_reconciliation_sessions(start_date=self.start_date, end_date=self.end_date, status=None if self.status_filter == 'all' else self.status_filter, limit=page_size, offset=offset)
                        if not chunk:
                            break
                        for s in chunk:
                            if s['session_id'] < last_id:
                                collected.append(s)
                                if len(collected) >= page_size:
                                    break
                        offset += len(chunk)
                    
                    # Get detailed sessions for collected summaries
                    detailed_sessions = []
                    for session in collected:
                        try:
                            session_details = get_reconciliation_session(session['session_id'])
                            if session_details:
                                detailed_sessions.append(session_details)
                        except Exception as e:
                            logger.warning(f"Could not get details for session {session['session_id']}: {e}")
                    
                    next_cursor = None
                    if detailed_sessions:
                        last = detailed_sessions[-1]
                        next_cursor = f"key:{last.session_id}" if len(detailed_sessions) >= page_size else None
                    meta = {'page_size': page_size, 'keyset_supported': False}
                    return detailed_sessions, next_cursor, meta
                else:
                    # Initial page: fetch first page_size sessions
                    sessions = get_reconciliation_sessions(start_date=self.start_date, end_date=self.end_date, status=None if self.status_filter == 'all' else self.status_filter, limit=page_size, offset=0)
                    
                    # Get detailed sessions
                    detailed_sessions = []
                    for session in sessions:
                        try:
                            session_details = get_reconciliation_session(session['session_id'])
                            if session_details:
                                detailed_sessions.append(session_details)
                        except Exception as e:
                            logger.warning(f"Could not get details for session {session['session_id']}: {e}")
                    
                    next_cursor = f"key:{detailed_sessions[-1].session_id}" if detailed_sessions and len(detailed_sessions) >= page_size else None
                    return detailed_sessions, next_cursor, {'page_size': page_size, 'keyset_supported': False}

            # Offset pagination
            offset = int(cursor) if cursor and cursor.isdigit() else 0
            sessions = get_reconciliation_sessions(start_date=self.start_date, end_date=self.end_date, status=None if self.status_filter == 'all' else self.status_filter, limit=page_size, offset=offset)
            
            # Get detailed sessions
            detailed_sessions = []
            for session in sessions:
                try:
                    session_details = get_reconciliation_session(session['session_id'])
                    if session_details:
                        detailed_sessions.append(session_details)
                except Exception as e:
                    logger.warning(f"Could not get details for session {session['session_id']}: {e}")
            
            next_cursor = str(offset + len(detailed_sessions)) if len(detailed_sessions) == page_size else None
            return detailed_sessions, next_cursor, {'page_size': page_size}

        except Exception as e:
            # Fallback to full generation
            full = self.generate_data()
            offset = int(cursor) if cursor and cursor.isdigit() else 0
            rows = full.data[offset:offset + page_size]
            next_cursor = str(offset + len(rows)) if offset + len(rows) < len(full.data) else None
            metadata = {**full.metadata, 'total_items': len(full.data)}
            return rows, next_cursor, metadata