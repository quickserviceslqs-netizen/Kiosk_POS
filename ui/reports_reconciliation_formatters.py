"""Text formatters for reconciliation reports."""

from typing import Dict, List, Any
from utils.date_utils import format_date
from .reports_base import TextReportFormatter


class ReconciliationSummaryTextFormatter(TextReportFormatter):
    """Formatter for reconciliation summary reports."""

    def _get_report_title(self) -> str:
        return "RECONCILIATION SUMMARY REPORT"

    def format_body(self) -> str:
        """Format reconciliation summary content."""
        if self.report_data.is_empty:
            return "No reconciliation sessions found for this period.\n"

        metadata = self.report_data.metadata

        output = f"Total Reconciliation Sessions: {metadata.get('session_count', 0)}\n\n"

        # Status summary
        status_counts = metadata.get('status_counts', {})
        if status_counts:
            output += "STATUS SUMMARY:\n"
            output += "-" * 20 + "\n"
            for status_name, count in status_counts.items():
                output += f"{status_name.title()}: {count} sessions\n"
            output += "\n"

        # Financial summary
        total_system = metadata.get('total_system', 0)
        total_actual = metadata.get('total_actual', 0)
        total_variance = metadata.get('total_variance', 0)

        output += "FINANCIAL SUMMARY:\n"
        output += "-" * 20 + "\n"
        output += f"Total System Amount: {self._format_currency(total_system)}\n"
        output += f"Total Actual Amount: {self._format_currency(total_actual)}\n"
        output += f"Total Variance: {self._format_currency(total_variance)}\n\n"

        # Recent sessions
        sessions = self.report_data.data[-10:]  # Show last 10 sessions
        if sessions:
            output += "RECENT SESSIONS:\n"
            output += "-" * 20 + "\n"
            header = f"{'Date':<12} {'Status':<10} {'System':<12} {'Actual':<12} {'Variance':<12}"
            output += header + "\n"
            output += "-" * len(header) + "\n"

            for session in sessions:
                # Support both legacy dict sessions and object sessions
                if isinstance(session, dict):
                    date_raw = session.get('created_at') or session.get('reconciliation_date')
                    if isinstance(date_raw, str) and 'T' in date_raw:
                        date = format_date(date_raw.split('T')[0])
                    else:
                        date = format_date(date_raw) if date_raw else 'N/A'

                    status_name = (session.get('status') or '').title()
                    system_amt = session.get('total_system_sales') or session.get('total_system') or 0
                    actual_amt = session.get('total_actual_cash') or session.get('total_actual') or 0
                    variance = session.get('total_variance') or 0
                else:
                    date = format_date(session.created_at.date()) if getattr(session, 'created_at', None) else 'N/A'
                    status_name = session.status.title() if getattr(session, 'status', None) else ''
                    system_amt = getattr(session, 'total_system_amount', 0) or 0
                    actual_amt = getattr(session, 'total_actual_amount', 0) or 0
                    variance = getattr(session, 'total_variance', 0) or 0

                line = f"{date:<12} {status_name:<10} {self._format_currency(system_amt):<12} {self._format_currency(actual_amt):<12} {self._format_currency(variance):<12}"
                output += line + "\n"

        return output


class ReconciliationDetailsTextFormatter(TextReportFormatter):
    """Formatter for reconciliation details reports."""

    def _get_report_title(self) -> str:
        return "RECONCILIATION DETAILS REPORT"

    def format_body(self) -> str:
        """Format reconciliation details content (robust for dict/object sessions)."""
        if self.report_data.is_empty:
            return "No reconciliation sessions found for this period.\n"

        def _fmt_date(s):
            # Accept datetime, ISO str, or None
            if s is None:
                return 'N/A'
            if hasattr(s, 'date'):
                return format_date(s.date())
            if isinstance(s, str):
                if 'T' in s:
                    return format_date(s.split('T')[0])
                return format_date(s)
            return 'N/A'

        def _get_field(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        metadata = self.report_data.metadata
        sessions = self.report_data.data

        output = f"Showing {metadata.get('session_count', 0)} of {metadata.get('total_sessions', 0)} sessions\n\n"

        for i, session in enumerate(sessions, 1):
            created = _get_field(session, 'created_at', _get_field(session, 'reconciliation_date', None))
            output += f"SESSION {i}: {_fmt_date(created)}\n"

            status = _get_field(session, 'status', '') or ''
            output += f"Status: {status.title()}\n"

            start = _get_field(session, 'start_date', '')
            end = _get_field(session, 'end_date', '')
            output += f"Period: {format_date(start) if start else 'N/A'} to {format_date(end) if end else 'N/A'}\n"
            output += "-" * 50 + "\n"

            # Session entries
            entries = _get_field(session, 'entries', []) or []
            if entries:
                header = f"{'Method':<15} {'System':<12} {'Actual':<12} {'Variance':<12}"
                output += header + "\n"
                output += "-" * len(header) + "\n"

                for entry in entries:
                    method = _get_field(entry, 'payment_method', '') or ''
                    if method and len(method) > 14:
                        method = method[:14]
                    system = _get_field(entry, 'system_amount', 0) or 0
                    actual = _get_field(entry, 'actual_amount', 0) or 0
                    variance = _get_field(entry, 'variance', 0) or 0
                    line = f"{method:<15} {self._format_currency(system):<12} {self._format_currency(actual):<12} {self._format_currency(variance):<12}"
                    output += line + "\n"

            # Session totals
            system_total = _get_field(session, 'total_system_amount', _get_field(session, 'total_system_sales', 0)) or 0
            actual_total = _get_field(session, 'total_actual_amount', _get_field(session, 'total_actual_cash', 0)) or 0
            variance_total = _get_field(session, 'total_variance', 0) or 0

            output += f"Session Totals: System: {self._format_currency(system_total)}, "
            output += f"Actual: {self._format_currency(actual_total)}, "
            output += f"Variance: {self._format_currency(variance_total)}\n\n"

        return output