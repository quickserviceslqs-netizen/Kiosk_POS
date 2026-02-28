"""Domain entities for reconciliation system."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ReconciliationStatus(Enum):
    """Status of a reconciliation session."""
    DRAFT = "draft"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"


class PeriodType(Enum):
    """Type of reconciliation period."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class PaymentMethod:
    """Represents a payment method in the system."""
    name: str
    is_active: bool = True
    description: Optional[str] = None


@dataclass
class ReconciliationEntry:
    """Domain entity for a reconciliation entry.

    Reconciliation formula:
        actual_sales = actual_amount (closing balance) - opening_balance + cash_out
        variance     = actual_sales - system_amount (POS sales)
    """
    payment_method: str
    system_amount: float
    actual_amount: float = 0.0          # Closing balance (what was counted)
    variance: float = 0.0
    is_reviewed: bool = False
    notes: str = ""
    entry_id: Optional[int] = None
    opening_balance: float = 0.0        # Balance at start of period
    cash_out: float = 0.0               # Money removed (deposits, expenses)

    @property
    def actual_sales(self) -> float:
        """Derive actual daily sales from opening/closing/cash-out."""
        return self.actual_amount - self.opening_balance + self.cash_out

    def update_variance(self) -> None:
        """Recalculate variance: actual_sales vs system (POS) sales."""
        self.variance = self.actual_sales - self.system_amount

    @property
    def is_reconciled(self) -> bool:
        """Check if this entry is reconciled."""
        return abs(self.variance) < 0.01 or self.is_reviewed


@dataclass
class VarianceExplanation:
    """Domain entity for variance explanations."""
    explanation: str
    amount: float
    payment_method: str
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    explanation_id: Optional[int] = None


@dataclass
class ReconciliationSession:
    """Domain entity for a reconciliation session."""
    date: str
    period_type: PeriodType
    start_date: str
    end_date: str
    created_by: int
    session_id: Optional[int] = None
    status: ReconciliationStatus = ReconciliationStatus.DRAFT
    completed_at: Optional[datetime] = None
    notes: str = ""
    entries: List[ReconciliationEntry] = field(default_factory=list)
    explanations: List[VarianceExplanation] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def total_system_amount(self) -> float:
        """Total system amount across all entries."""
        return sum(entry.system_amount for entry in self.entries)

    @property
    def total_actual_amount(self) -> float:
        """Total actual amount across all entries."""
        return sum(entry.actual_amount for entry in self.entries)

    @property
    def total_variance(self) -> float:
        """Total variance across all entries."""
        return sum(entry.variance for entry in self.entries)

    @property
    def is_complete(self) -> bool:
        """Check if all entries are reconciled."""
        return all(entry.is_reconciled for entry in self.entries)

    @property
    def unreviewed_count(self) -> int:
        """Count of unreviewed entries with variance."""
        return sum(1 for entry in self.entries
                  if not entry.is_reviewed and abs(entry.variance) >= 0.01)

    def add_entry(self, entry: ReconciliationEntry) -> None:
        """Add an entry to the session."""
        self.entries.append(entry)

    def add_explanation(self, explanation: VarianceExplanation) -> None:
        """Add an explanation to the session."""
        self.explanations.append(explanation)

    def update_entry_amount(self, payment_method: str, actual_amount: float) -> None:
        """Update the actual amount for a payment method."""
        for entry in self.entries:
            if entry.payment_method == payment_method:
                entry.actual_amount = actual_amount
                entry.update_variance()
                break

    def mark_entry_reviewed(self, payment_method: str, reviewed: bool = True) -> None:
        """Mark an entry as reviewed."""
        for entry in self.entries:
            if entry.payment_method == payment_method:
                entry.is_reviewed = reviewed
                break

    def get_entry(self, payment_method: str) -> Optional[ReconciliationEntry]:
        """Get an entry by payment method."""
        return next((entry for entry in self.entries if entry.payment_method == payment_method), None)

    def get_explained_variance_total(self, payment_method: str) -> float:
        """Get total explained variance for a payment method."""
        payment_explanations = [exp for exp in self.explanations if exp.payment_method == payment_method]
        total_abs_amount = sum(abs(exp.amount) for exp in payment_explanations)
        
        # Apply sign based on variance direction
        entry = self.get_entry(payment_method)
        if entry and entry.variance < 0:
            return -total_abs_amount
        return total_abs_amount

    def get_unexplained_variance(self, payment_method: str) -> float:
        """Get unexplained variance for a payment method."""
        entry = self.get_entry(payment_method)
        if not entry:
            return 0.0
        explained_total = self.get_explained_variance_total(payment_method)
        return entry.variance - explained_total