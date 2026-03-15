"""Application services for reconciliation use cases."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
import logging
from ..domain.entities import (
    ReconciliationSession, ReconciliationEntry, VarianceExplanation,
    ReconciliationStatus, PeriodType
)
from ..domain.repositories.interfaces import (
    ReconciliationSessionRepository, VarianceExplanationRepository
)
from ..infrastructure.repositories import (
    SQLiteReconciliationSessionRepository, SQLiteVarianceExplanationRepository
)
from modules.external_accounts import account_manager
from modules import reports

logger = logging.getLogger(__name__)


class ReconciliationApplicationService:
    """Application service for reconciliation operations."""

    def __init__(self,
                 session_repo: Optional[ReconciliationSessionRepository] = None,
                 explanation_repo: Optional[VarianceExplanationRepository] = None):
        self.session_repo = session_repo or SQLiteReconciliationSessionRepository()
        self.explanation_repo = explanation_repo or SQLiteVarianceExplanationRepository()

    def create_session(self, date: str, period_type: str, user_id: int, start_date: str = None, end_date: str = None) -> ReconciliationSession:
        """Create a new reconciliation session.

        System amount is now derived from POS sales for the period.
        Opening balance is auto-populated from the previous session's closing
        balance (actual_amount) for each payment method.
        """
        # Calculate date range
        if start_date and end_date:
            # Use provided dates (for custom periods)
            session_start_date = start_date
            session_end_date = end_date
        else:
            # Calculate dates based on period type
            session_start_date, session_end_date = self._calculate_date_range(period_type, date)

        # Get POS sales as the authoritative system amount
        sales_data = reports.get_sales_by_payment_method(session_start_date, session_end_date)

        # Build a lookup: payment_method → POS total
        sales_lookup: dict[str, float] = {}
        for row in sales_data:
            pm = row['payment_method']
            sales_lookup[pm] = float(row['total_sales'])

        # Get ALL payment methods that have ever been used (not just those with sales in this period)
        from database.init_db import get_connection
        all_historical_methods = set()
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT COALESCE(payment_method, 'Cash') as payment_method FROM sale_payments ORDER BY payment_method")
                all_historical_methods = {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.warning(f"Could not fetch all payment methods: {e}")

        # Also include any external-account payment methods
        account_balances = account_manager.get_balances_by_payment_method()
        all_methods = all_historical_methods | set(account_balances.keys()) | set(sales_lookup.keys())

        # Fetch the last completed/draft session's closing balances to use
        # as today's opening balance.
        previous_closing = self._get_previous_closing_balances(session_start_date)

        # Auto-populate cash_out from recorded expenses for the period
        from modules.expenses import get_expenses_total_by_payment_method
        expense_totals = get_expenses_total_by_payment_method(session_start_date, session_end_date)

        # Create entries
        entries = []
        for pm in sorted(all_methods):
            system_amount = sales_lookup.get(pm, 0.0)
            opening = previous_closing.get(pm, 0.0)
            cash_out = expense_totals.get(pm, 0.0)
            entries.append(ReconciliationEntry(
                payment_method=pm,
                system_amount=system_amount,
                actual_amount=0.0,
                opening_balance=opening,
                cash_out=cash_out,
            ))

        # Update variances
        for entry in entries:
            entry.update_variance()

        # Create session
        session = ReconciliationSession(
            date=date,
            period_type=PeriodType(period_type),
            start_date=session_start_date,
            end_date=session_end_date,
            created_by=user_id,
            entries=entries
        )

        # Save to database
        session_id = self.session_repo.save(session)
        session.session_id = session_id

        return session

    # ------------------------------------------------------------------
    # Helper: fetch previous session's closing (actual_amount) per method
    # ------------------------------------------------------------------
    def _get_previous_closing_balances(self, before_date: str) -> dict[str, float]:
        """Return {payment_method: closing_balance} from the most recent
        session whose end_date is before *before_date*."""
        from database.init_db import get_connection
        try:
            with get_connection() as conn:
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
                    return {}
                prev_id = row[0]
                cursor.execute("""
                    SELECT payment_method, actual_amount
                    FROM reconciliation_entries
                    WHERE session_id = ?
                """, (prev_id,))
                return {r[0]: r[1] for r in cursor.fetchall()}
        except Exception:
            return {}

    def get_session(self, session_id: int) -> Optional[ReconciliationSession]:
        """Get a session by ID."""
        return self.session_repo.find_by_id(session_id)

    def update_entry_amount(self, session_id: int, payment_method: str, actual_amount: float) -> None:
        """Update the actual amount for a payment method."""
        session = self.session_repo.find_by_id(session_id)
        if session:
            session.update_entry_amount(payment_method, actual_amount)
            self.session_repo.save(session)

    def update_entry_notes(self, session_id: int, payment_method: str, notes: str) -> None:
        """Update the notes for a payment method entry."""
        session = self.session_repo.find_by_id(session_id)
        if session:
            entry = session.get_entry(payment_method)
            if entry:
                entry.notes = notes
                self.session_repo.save(session)

    def mark_entry_reviewed(self, session_id: int, payment_method: str, reviewed: bool = True) -> None:
        """Mark an entry as reviewed."""
        session = self.session_repo.find_by_id(session_id)
        if session:
            session.mark_entry_reviewed(payment_method, reviewed)
            self.session_repo.save(session)

    def add_variance_explanation(self, session_id: int, payment_method: str,
                               explanation: str, amount: float, user_id: int) -> int:
        """Add a variance explanation."""
        explanation_obj = VarianceExplanation(
            payment_method=payment_method,
            explanation=explanation,
            amount=amount,
            created_by=user_id,
            created_at=datetime.now()
        )

        explanation_id = self.explanation_repo.save(session_id, explanation_obj)

        # Update session in memory if loaded
        session = self.session_repo.find_by_id(session_id)
        if session:
            explanation_obj.explanation_id = explanation_id
            session.add_explanation(explanation_obj)
            self.session_repo.save(session)

        return explanation_id

    def complete_session(self, session_id: int, user_id: int, notes: str = "") -> bool:
        """Complete a reconciliation session."""
        session = self.session_repo.find_by_id(session_id)
        if not session or not session.is_complete:
            return False

        session.status = ReconciliationStatus.COMPLETED
        session.completed_at = datetime.now()
        session.notes = notes

        self.session_repo.save(session)
        return True

    def get_sessions(self, start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    status: Optional[str] = None,
                    limit: int = 50,
                    offset: int = 0) -> List[ReconciliationSession]:
        """Get sessions with filters."""
        return self.session_repo.find_all(start_date, end_date, status, limit, offset)

    def delete_session(self, session_id: int) -> None:
        """Delete a session."""
        self.session_repo.delete(session_id)

    def get_explained_variance_total(self, session_id: int, payment_method: str) -> float:
        """Get total explained variance for a payment method."""
        explanations = self.explanation_repo.find_by_session_id(session_id)
        payment_explanations = [exp for exp in explanations if exp.payment_method == payment_method]

        total_abs_amount = sum(abs(exp.amount) for exp in payment_explanations)

        # Determine variance sign
        session = self.session_repo.find_by_id(session_id)
        if session:
            entry = next((e for e in session.entries if e.payment_method == payment_method), None)
            if entry and entry.variance < 0:
                return -total_abs_amount  # Explanations reduce negative variance

        return total_abs_amount  # Explanations reduce positive variance

    def get_unexplained_variance(self, session_id: int, payment_method: str) -> float:
        """Get unexplained variance for a payment method."""
        session = self.session_repo.find_by_id(session_id)
        if not session:
            return 0.0

        entry = next((e for e in session.entries if e.payment_method == payment_method), None)
        if not entry:
            return 0.0

        explained_total = self.get_explained_variance_total(session_id, payment_method)
        return entry.variance - explained_total

    def _calculate_date_range(self, period_type: str, reference_date: str) -> tuple[str, str]:
        """Calculate start and end dates for different period types."""
        from datetime import datetime, timedelta
        from utils.date_utils import parse_date_flexible

        if reference_date == 'today':
            ref_date = datetime.now().date()
        else:
            # Use flexible date parsing to handle multiple formats
            try:
                ref_date = parse_date_flexible(reference_date).date()
            except ValueError:
                # Fallback: try ISO format
                ref_date = datetime.strptime(reference_date, '%Y-%m-%d').date()

        if period_type == 'daily':
            start_date = ref_date
            end_date = ref_date
        elif period_type == 'weekly':
            start_date = ref_date - timedelta(days=ref_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif period_type == 'monthly':
            start_date = ref_date.replace(day=1)
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
        elif period_type == 'yearly':
            start_date = ref_date.replace(month=1, day=1)
            end_date = ref_date.replace(month=12, day=31)
        elif period_type == 'custom':
            # For custom period, just use the reference date as both start and end
            # The caller should handle custom date ranges separately
            start_date = ref_date
            end_date = ref_date
        else:
            raise ValueError(f"Unknown period type: {period_type}")

        return start_date.isoformat(), end_date.isoformat()


# Global service instance
reconciliation_service = ReconciliationApplicationService()