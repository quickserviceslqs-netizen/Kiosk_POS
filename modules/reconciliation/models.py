from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class ReconEntry:
    """Represents a single reconciliation entry."""
    payment_method: str
    system_amount: float
    actual_amount: float = 0.0
    variance: float = 0.0
    metadata: Optional[dict] = None


@dataclass
class ReconSummary:
    """Summary for a specific module."""
    module_key: str
    module_name: str
    total_system: float
    total_actual: float
    total_variance: float
    entries_count: int
    status: str = "pending"  # pending, reconciled, exception


@dataclass
class ReconException:
    """Represents an exception or discrepancy."""
    module_key: str
    description: str
    severity: str = "warning"  # warning, error
    details: Optional[dict] = None


@dataclass
class ReconSession:
    """Represents a reconciliation session."""
    session_id: int
    start_date: str
    end_date: str
    created_at: datetime
    entries: List[ReconEntry] = None
    summaries: List[ReconSummary] = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = []
        if self.summaries is None:
            self.summaries = []
