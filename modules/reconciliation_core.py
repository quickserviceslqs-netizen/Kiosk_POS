"""
Reconciliation Core Module - Compatibility Layer

This module provides backwards compatibility with the existing UI
while delegating to the new modular reconciliation architecture.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from utils.date_utils import parse_date_flexible, format_date_storage
import logging
from modules.reconciliation.application.services import reconciliation_service

logger = logging.getLogger(__name__)

# Legacy data models for backwards compatibility
@dataclass
class ReconciliationItem:
    """Legacy model - represents a single payment method reconciliation item.

    Reconciliation formula:
        actual_sales = actual_amount (closing) - opening_balance + cash_out
        variance     = actual_sales - system_amount (POS sales)
    """
    payment_method: str
    system_amount: float
    actual_amount: float = 0.0          # Closing balance (counted)
    variance: float = 0.0
    is_reviewed: bool = False
    notes: str = ""
    opening_balance: float = 0.0        # Balance at start of period
    cash_out: float = 0.0               # Money removed (deposits, expenses)

    @property
    def actual_sales(self) -> float:
        """Derive actual daily sales from opening/closing/cash-out."""
        return self.actual_amount - self.opening_balance + self.cash_out

    @property
    def is_reconciled(self) -> bool:
        """Check if this item is reconciled."""
        return abs(self.variance) < 0.01 or self.is_reviewed

    def update_variance(self) -> None:
        """Recalculate variance: actual_sales vs system (POS) sales."""
        self.variance = self.actual_sales - self.system_amount


@dataclass
class ReconciliationSession:
    """Legacy model - represents a complete reconciliation session."""
    session_id: Optional[int]
    date: str
    period_type: str
    start_date: str
    end_date: str
    items: List[ReconciliationItem]
    status: str
    created_by: int
    created_at: str
    completed_at: Optional[str] = None
    notes: str = ""
    explanations: List[VarianceExplanation] = None
    explanations_loaded: bool = False

    def __post_init__(self):
        """Initialize explanations list."""
        if self.explanations is None:
            self.explanations = []

    @property
    def total_system_amount(self) -> float:
        """Total system amount."""
        return sum(item.system_amount for item in self.items)

    @property
    def total_actual_amount(self) -> float:
        """Total actual amount."""
        return sum(item.actual_amount for item in self.items)

    @property
    def total_variance(self) -> float:
        """Total variance."""
        return sum(item.variance for item in self.items)

    @property
    def is_complete(self) -> bool:
        """Check if all items are reconciled."""
        return all(item.is_reconciled for item in self.items)

    @property
    def unreviewed_count(self) -> int:
        """Count of unreviewed items with variance."""
        return sum(1 for item in self.items if not item.is_reviewed and abs(item.variance) >= 0.01)


@dataclass
class ReconciliationEntry:
    """Legacy database model."""
    payment_method: str
    system_amount: float
    actual_amount: float = 0.0
    variance: float = 0.0
    explanation: str = ""
    is_reviewed: bool = False
    opening_balance: float = 0.0
    cash_out: float = 0.0

    @property
    def actual_sales(self) -> float:
        return self.actual_amount - self.opening_balance + self.cash_out


@dataclass
class VarianceExplanation:
    """Legacy variance explanation model."""
    explanation_id: Optional[int]
    session_id: int
    payment_method: str
    explanation: str
    amount: float
    created_by: Optional[int]
    created_at: str

    @property
    def is_unexplained(self) -> bool:
        """Check if this is an unexplained variance entry."""
        return self.explanation.lower().strip() == "unexplained"


@dataclass
class DBReconciliationSession:
    """Legacy database model."""
    session_id: Optional[int]
    reconciliation_date: str
    period_type: str
    start_date: str
    end_date: str
    total_system_sales: float
    total_actual_cash: float
    total_variance: float
    status: str
    reconciled_by: Optional[int]
    reconciled_at: Optional[str]
    notes: str
    entries: List[ReconciliationEntry]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Import required modules for backwards compatibility
from modules import reports
from modules.external_accounts import account_manager


def get_sales_by_payment_method_for_period(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get sales breakdown by payment method for a specific period."""
    return reports.get_sales_by_payment_method(start_date, end_date)


def calculate_date_range(period_type: str, reference_date: str = None) -> Tuple[str, str]:
    """Calculate start and end dates for different period types."""
    if reference_date is None:
        reference_date = datetime.now().strftime("%Y-%m-%d")

    # Parse the reference date flexibly (handles any system date format)
    ref_date = parse_date_flexible(reference_date)

    if period_type == "daily":
        start_date = end_date = ref_date.strftime("%Y-%m-%d")
    elif period_type == "weekly":
        start_of_week = ref_date - timedelta(days=ref_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_date = start_of_week.strftime("%Y-%m-%d")
        end_date = end_of_week.strftime("%Y-%m-%d")
    elif period_type == "monthly":
        start_of_month = ref_date.replace(day=1)
        # Handle year rollover for December
        if start_of_month.month == 12:
            next_month = start_of_month.replace(year=start_of_month.year + 1, month=1, day=1)
        else:
            next_month = start_of_month.replace(month=start_of_month.month + 1, day=1)
        end_of_month = next_month - timedelta(days=1)
        start_date = start_of_month.strftime("%Y-%m-%d")
        end_date = end_of_month.strftime("%Y-%m-%d")
    elif period_type == "yearly":
        start_of_year = ref_date.replace(month=1, day=1)
        end_of_year = ref_date.replace(month=12, day=31)
        start_date = start_of_year.strftime("%Y-%m-%d")
        end_date = end_of_year.strftime("%Y-%m-%d")
    else:
        start_date = end_date = ref_date.strftime("%Y-%m-%d")

    return start_date, end_date


# Core functions - delegate to new architecture
def create_reconciliation_session(
    reconciliation_date: str,
    period_type: str,
    start_date: str,
    end_date: str,
    user_id: int
) -> int:
    """Create a new reconciliation session."""
    session = reconciliation_service.create_session(reconciliation_date, period_type, user_id, start_date, end_date)
    return session.session_id


def get_reconciliation_session(session_id: int) -> Optional[DBReconciliationSession]:
    """Get a reconciliation session by ID."""
    session = reconciliation_service.get_session(session_id)
    if not session:
        return None

    # Convert to legacy format
    entries = []
    for entry in session.entries:
        entries.append(ReconciliationEntry(
            payment_method=entry.payment_method,
            system_amount=entry.system_amount,
            actual_amount=entry.actual_amount,
            variance=entry.variance,
            explanation=entry.notes,
            is_reviewed=getattr(entry, 'is_reviewed', False),
            opening_balance=getattr(entry, 'opening_balance', 0.0),
            cash_out=getattr(entry, 'cash_out', 0.0),
        ))

    return DBReconciliationSession(
        session_id=session.session_id,
        reconciliation_date=session.date,
        period_type=session.period_type.value,
        start_date=session.start_date,
        end_date=session.end_date,
        total_system_sales=session.total_system_amount,
        total_actual_cash=session.total_actual_amount,
        total_variance=session.total_variance,
        status=session.status.value,
        reconciled_by=session.created_by,
        reconciled_at=session.completed_at.isoformat() if session.completed_at else None,
        notes=session.notes,
        entries=entries
    )


def update_reconciliation_entry(
    session_id: int,
    payment_method: str,
    actual_amount: float = None,
    explanation: str = ""
) -> None:
    """Update an entry in a reconciliation session.
    
    Args:
        session_id: The session ID
        payment_method: The payment method to update
        actual_amount: The new actual amount (None to keep existing)
        explanation: The explanation/notes for the entry
    """
    if actual_amount is not None:
        reconciliation_service.update_entry_amount(session_id, payment_method, actual_amount)
    
    # Update notes if provided
    if explanation:
        reconciliation_service.update_entry_notes(session_id, payment_method, explanation)


def complete_reconciliation_session(session_id: int, user_id: int, notes: str = "") -> None:
    """Mark a reconciliation session as completed."""
    reconciliation_service.complete_session(session_id, user_id, notes)


def get_reconciliation_sessions(
    start_date: str = None,
    end_date: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get reconciliation sessions with optional filters."""
    sessions = reconciliation_service.get_sessions(start_date, end_date, status, limit, offset)

    # Convert to legacy format
    result = []
    for session in sessions:
        result.append({
            'session_id': session.session_id,
            'reconciliation_date': session.date,
            'period_type': session.period_type.value,
            'start_date': session.start_date,
            'end_date': session.end_date,
            'status': session.status.value,
            'total_system_sales': session.total_system_amount,
            'total_actual_cash': session.total_actual_amount,
            'total_variance': session.total_variance,
            'reconciled_by': session.created_by,
            'reconciled_at': session.completed_at.isoformat() if session.completed_at else None,
            'notes': session.notes,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'updated_at': session.updated_at.isoformat() if session.updated_at else None
        })

    return result


def add_reconciliation_explanation(
    session_id: int,
    explanation_type: str,
    explanation: str,
    payment_method: str = None,
    amount: float = 0,
    user_id: int = None
) -> None:
    """Add an explanation/note to a reconciliation session."""
    if explanation_type == 'variance':
        reconciliation_service.add_variance_explanation(
            session_id, payment_method, explanation, amount, user_id
        )


def get_reconciliation_explanations(session_id: int) -> List[Dict[str, Any]]:
    """Get explanations for a reconciliation session."""
    explanations = reconciliation_service.explanation_repo.find_by_session_id(session_id)

    # Convert to legacy format
    result = []
    for exp in explanations:
        result.append({
            'explanation_id': exp.explanation_id,
            'session_id': session_id,  # Use the session_id parameter instead of exp.session_id
            'explanation_type': 'variance',
            'payment_method': exp.payment_method,
            'explanation': exp.explanation,
            'amount': exp.amount,
            'created_by': exp.created_by,
            'created_at': exp.created_at.isoformat() if exp.created_at else None
        })

    return result


def get_variance_explanations(session_or_id, payment_method: str = None) -> List[VarianceExplanation]:
    """Get variance explanations for a session."""
    if isinstance(session_or_id, ReconciliationSession):
        # In-memory session - check if saved or not
        if session_or_id.session_id is not None:
            # Session is saved, query DB for latest explanations
            explanations = reconciliation_service.explanation_repo.find_by_session_id(session_or_id.session_id)
            result = []
            for exp in explanations:
                if payment_method is None or exp.payment_method == payment_method:
                    result.append(VarianceExplanation(
                        explanation_id=exp.explanation_id,
                        session_id=session_or_id.session_id,
                        payment_method=exp.payment_method,
                        explanation=exp.explanation,
                        amount=exp.amount,
                        created_by=exp.created_by,
                        created_at=exp.created_at.isoformat() if exp.created_at else None
                    ))
            return result
        else:
            # Session not saved yet, use in-memory explanations
            if payment_method is None:
                return session_or_id.explanations
            return [e for e in session_or_id.explanations if e.payment_method == payment_method]
    else:
        # Session ID passed directly
        if session_or_id is None:
            return []
        explanations = reconciliation_service.explanation_repo.find_by_session_id(session_or_id)

        # Convert to legacy format
        result = []
        for exp in explanations:
            if payment_method is None or exp.payment_method == payment_method:
                result.append(VarianceExplanation(
                    explanation_id=exp.explanation_id,
                    session_id=session_or_id,
                    payment_method=exp.payment_method,
                    explanation=exp.explanation,
                    amount=exp.amount,
                    created_by=exp.created_by,
                    created_at=exp.created_at.isoformat() if exp.created_at else None
                ))

        return result


def add_variance_explanation(session_or_id, payment_method: str, explanation: str, amount: float, user_id: int = None) -> int:
    """Add a variance explanation."""
    if isinstance(session_or_id, ReconciliationSession):
        # Check if session is saved (has session_id)
        if session_or_id.session_id is not None:
            # Session is saved - add directly to database
            return reconciliation_service.add_variance_explanation(
                session_or_id.session_id, payment_method, explanation, amount, user_id
            )
        else:
            # Session not saved yet - add to in-memory list
            explanation_obj = VarianceExplanation(
                explanation_id=len(session_or_id.explanations) + 1,
                session_id=session_or_id.session_id,
                payment_method=payment_method,
                explanation=explanation,
                amount=amount,
                created_by=user_id,
                created_at=datetime.now().isoformat()
            )
            session_or_id.explanations.append(explanation_obj)
            return explanation_obj.explanation_id
    else:
        # Session ID
        return reconciliation_service.add_variance_explanation(
            session_or_id, payment_method, explanation, amount, user_id
        )


def get_explained_variance_total(session_or_id, payment_method: str) -> float:
    """Get the total explained variance amount for a payment method."""
    if isinstance(session_or_id, ReconciliationSession):
        # In-memory session
        if session_or_id.session_id is not None:
            # Session is saved, query DB
            return reconciliation_service.get_explained_variance_total(session_or_id.session_id, payment_method)
        else:
            # Session not saved yet, use in-memory explanations
            payment_explanations = [e for e in session_or_id.explanations if e.payment_method == payment_method]
            total_abs = sum(abs(e.amount) for e in payment_explanations)
            
            # Match the sign of the variance
            item = next((i for i in session_or_id.items if i.payment_method == payment_method), None)
            if item and item.variance < 0:
                return -total_abs
            return total_abs
    elif isinstance(session_or_id, DBReconciliationSession):
        # DB session object - use its session_id
        return reconciliation_service.get_explained_variance_total(session_or_id.session_id, payment_method)
    else:
        session_id = session_or_id
        if session_id is None:
            return 0.0
        return reconciliation_service.get_explained_variance_total(session_id, payment_method)


def add_variance_explanation_to_db(session_id: int, payment_method: str, explanation: str, amount: float, user_id: int = None) -> int:
    """Add a variance explanation directly to the database."""
    return reconciliation_service.add_variance_explanation(session_id, payment_method, explanation, amount, user_id)


def save_reconciliation_session(session: ReconciliationSession) -> int:
    """Save a reconciliation session to the database."""
    # Convert legacy session to new format and save
    from modules.reconciliation.domain.entities import ReconciliationSession as NewSession
    from modules.reconciliation.domain.entities import ReconciliationEntry as NewEntry
    from modules.reconciliation.domain.entities import ReconciliationStatus, PeriodType

    entries = []
    for item in session.items:
        entries.append(NewEntry(
            payment_method=item.payment_method,
            system_amount=item.system_amount,
            actual_amount=item.actual_amount,
            variance=item.variance,
            is_reviewed=item.is_reviewed,
            notes=item.notes,
            opening_balance=getattr(item, 'opening_balance', 0.0),
            cash_out=getattr(item, 'cash_out', 0.0),
        ))

    new_session = NewSession(
        session_id=session.session_id,
        date=session.date,
        period_type=PeriodType(session.period_type),
        start_date=session.start_date,
        end_date=session.end_date,
        status=ReconciliationStatus(session.status),
        created_by=session.created_by,
        entries=entries,
        notes=session.notes
    )

    return reconciliation_service.session_repo.save(new_session)


# Legacy functions for backwards compatibility
def set_entry_reviewed(session_id: int, payment_method: str, reviewed: bool = True) -> None:
    """Set the reviewed flag for a specific reconciliation entry."""
    reconciliation_service.mark_entry_reviewed(session_id, payment_method, reviewed)


def create_reconciliation_entry(session_id: int, payment_method: str, system_amount: float, actual_amount: float = 0.0) -> int:
    """Create an entry for a reconciliation session."""
    return 0


def get_system_amount_for_payment_method(session_id: int, payment_method: str) -> float:
    """Get the system amount for a payment method in a session."""
    session = reconciliation_service.get_session(session_id)
    if session:
        entry = next((e for e in session.entries if e.payment_method == payment_method), None)
        return entry.system_amount if entry else 0.0
    return 0.0


def _update_session_totals(session_id: int) -> None:
    """Update the total actual cash and variance for a session."""
    pass


def update_variance_explanation(session_or_id, explanation_id: int, explanation: str, amount: float) -> None:
    """Update a variance explanation."""
    if isinstance(session_or_id, ReconciliationSession):
        # Check if session is in-memory (not saved yet)
        if session_or_id.session_id is None:
            # Update in the in-memory explanations list
            for expl in session_or_id.explanations:
                if expl.explanation_id == explanation_id:
                    expl.explanation = explanation
                    expl.amount = amount
                    return
        else:
            # Session is saved, update in database
            reconciliation_service.explanation_repo.update(explanation_id, explanation, amount)
    else:
        # Session ID passed directly
        reconciliation_service.explanation_repo.update(explanation_id, explanation, amount)


def get_unexplained_variance(session_or_id, payment_method: str) -> float:
    """Get the unexplained variance for a payment method."""
    if isinstance(session_or_id, ReconciliationSession):
        # In-memory session - calculate directly from session data
        item = next((i for i in session_or_id.items if i.payment_method == payment_method), None)
        if not item:
            return 0.0
        
        # For in-memory sessions, get explained total from in-memory explanations
        if session_or_id.session_id is not None:
            # Session is saved, query DB for explained total
            explained_total = reconciliation_service.get_explained_variance_total(session_or_id.session_id, payment_method)
        else:
            # Session not saved yet, use in-memory explanations
            payment_explanations = [e for e in session_or_id.explanations if e.payment_method == payment_method]
            explained_total = sum(abs(e.amount) for e in payment_explanations)
            # Match the sign of the variance
            if item.variance < 0:
                explained_total = -explained_total
        
        return item.variance - explained_total
    elif isinstance(session_or_id, DBReconciliationSession):
        # DB session object - use its session_id
        return reconciliation_service.get_unexplained_variance(session_or_id.session_id, payment_method)
    else:
        # Session ID passed directly
        session_id = session_or_id
        if session_id is None:
            return 0.0
        return reconciliation_service.get_unexplained_variance(session_id, payment_method)


def delete_reconciliation_session(session_id: int) -> None:
    """Delete a reconciliation session."""
    reconciliation_service.delete_session(session_id)


# Legacy service class for backwards compatibility
class ReconciliationService:
    """Legacy service class - delegates to new architecture."""

    def __init__(self):
        pass

    def create_session(self, date: str, period_type: str, user_id: int) -> ReconciliationSession:
        """Create a new reconciliation session."""
        new_session = reconciliation_service.create_session(date, period_type, user_id)

        # Convert to legacy format
        items = []
        for entry in new_session.entries:
            items.append(ReconciliationItem(
                payment_method=entry.payment_method,
                system_amount=entry.system_amount,
                actual_amount=entry.actual_amount,
                variance=entry.variance,
                is_reviewed=entry.is_reviewed,
                notes=entry.notes
            ))

        return ReconciliationSession(
            session_id=new_session.session_id,
            date=new_session.date,
            period_type=new_session.period_type.value,
            start_date=new_session.start_date,
            end_date=new_session.end_date,
            items=items,
            status=new_session.status.value,
            created_by=new_session.created_by,
            created_at=new_session.created_at.isoformat() if new_session.created_at else datetime.now().isoformat(),
            completed_at=new_session.completed_at.isoformat() if new_session.completed_at else None,
            notes=new_session.notes,
            explanations_loaded=True
        )

    def load_session(self, session_id: int) -> Optional[ReconciliationSession]:
        """Load an existing reconciliation session."""
        new_session = reconciliation_service.get_session(session_id)
        if not new_session:
            return None

        # Convert to legacy format
        items = []
        for entry in new_session.entries:
            items.append(ReconciliationItem(
                payment_method=entry.payment_method,
                system_amount=entry.system_amount,
                actual_amount=entry.actual_amount,
                variance=entry.variance,
                is_reviewed=entry.is_reviewed,
                notes=entry.notes
            ))

        return ReconciliationSession(
            session_id=new_session.session_id,
            date=new_session.date,
            period_type=new_session.period_type.value,
            start_date=new_session.start_date,
            end_date=new_session.end_date,
            items=items,
            status=new_session.status.value,
            created_by=new_session.created_by,
            created_at=new_session.created_at.isoformat() if new_session.created_at else datetime.now().isoformat(),
            completed_at=new_session.completed_at.isoformat() if new_session.completed_at else None,
            notes=new_session.notes,
            explanations_loaded=True
        )

    def save_session(self, session: ReconciliationSession) -> int:
        """Save reconciliation session to database."""
        # Convert legacy session to new format and save
        from modules.reconciliation.domain.entities import ReconciliationSession as NewSession
        from modules.reconciliation.domain.entities import ReconciliationEntry as NewEntry
        from modules.reconciliation.domain.entities import ReconciliationStatus, PeriodType

        entries = []
        for item in session.items:
            entries.append(NewEntry(
                payment_method=item.payment_method,
                system_amount=item.system_amount,
                actual_amount=item.actual_amount,
                variance=item.variance,
                is_reviewed=item.is_reviewed,
                notes=item.notes
            ))

        new_session = NewSession(
            session_id=session.session_id,
            date=session.date,
            period_type=PeriodType(session.period_type),
            start_date=session.start_date,
            end_date=session.end_date,
            status=ReconciliationStatus(session.status),
            created_by=session.created_by,
            entries=entries,
            notes=session.notes
        )

        return reconciliation_service.session_repo.save(new_session)

    def update_item_actual_amount(self, session: ReconciliationSession,
                                payment_method: str, actual_amount: float) -> None:
        """Update the actual amount for a payment method."""
        reconciliation_service.update_entry_amount(session.session_id, payment_method, actual_amount)

        # Update in-memory session
        for item in session.items:
            if item.payment_method == payment_method:
                item.actual_amount = actual_amount
                item.update_variance()
                break

    def add_manual_entry(self, session: ReconciliationSession, payment_method: str, system_amount: float, actual_amount: float = 0.0) -> int:
        """Add a manual payment method entry."""
        return 0

    def mark_item_reviewed(self, session: ReconciliationSession,
                          payment_method: str, reviewed: bool = True) -> None:
        """Mark a payment method as reviewed."""
        reconciliation_service.mark_entry_reviewed(session.session_id, payment_method, reviewed)

        # Update in-memory session
        for item in session.items:
            if item.payment_method == payment_method:
                item.is_reviewed = reviewed
                break

    def complete_session(self, session: ReconciliationSession, notes: str = "", user_id: int | None = None) -> bool:
        """Complete the reconciliation session."""
        return reconciliation_service.complete_session(session.session_id, user_id or session.created_by, notes)

    def get_variance_explanations(self, session_or_id, payment_method: str = None) -> List[VarianceExplanation]:
        """Get variance explanations."""
        return get_variance_explanations(session_or_id, payment_method)

    def add_variance_explanation(self, session_or_id, payment_method: str, explanation: str, amount: float, user_id: int = None) -> int:
        """Add a variance explanation."""
        return add_variance_explanation(session_or_id, payment_method, explanation, amount, user_id)

    def get_explained_variance_total(self, session_or_id, payment_method: str) -> float:
        """Get explained variance total."""
        return get_explained_variance_total(session_or_id, payment_method)

    def get_unexplained_variance(self, session_or_id, payment_method: str) -> float:
        """Get unexplained variance."""
        return get_unexplained_variance(session_or_id, payment_method)


def delete_variance_explanation(session_or_id, explanation_id: int) -> None:
    """Delete a variance explanation."""
    if isinstance(session_or_id, ReconciliationSession):
        # Check if session is in-memory (not saved yet)
        if session_or_id.session_id is None:
            # Remove from in-memory explanations list
            session_or_id.explanations = [e for e in session_or_id.explanations if e.explanation_id != explanation_id]
        else:
            # Session is saved, delete from database
            reconciliation_service.explanation_repo.delete(explanation_id)
    else:
        # Session ID passed directly
        reconciliation_service.explanation_repo.delete(explanation_id)