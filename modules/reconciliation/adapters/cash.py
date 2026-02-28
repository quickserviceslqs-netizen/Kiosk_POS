"""Cash module adapter: provides cash-related reconciliation."""
from __future__ import annotations
from typing import List
from ..adapter_base import ReconAdapterBase
from ..models import ReconSummary, ReconException, ReconEntry
from modules.external_accounts import account_manager


class CashAdapter(ReconAdapterBase):
    """Adapter for cash payment reconciliation."""

    @property
    def module_key(self) -> str:
        return "cash"

    @property
    def module_name(self) -> str:
        return "Cash"

    def get_expected(self, session) -> float:
        """Return expected cash total from system."""
        balances = account_manager.get_balances_by_payment_method()
        total = 0.0
        for pm, amt in balances.items():
            if 'cash' in pm.lower() or pm.lower() == 'cash':
                total += float(amt)
        return total

    def get_entries(self, session) -> List[ReconEntry]:
        """Return a list of ReconEntry objects for cash payment methods in the session period."""
        balances = account_manager.get_balances_by_payment_method()
        entries: List[ReconEntry] = []
        for pm, amt in balances.items():
            if 'cash' in pm.lower() or pm.lower() == 'cash':
                entries.append(ReconEntry(payment_method=pm, system_amount=float(amt), actual_amount=0.0))
        return entries

    def get_actual(self, session) -> float:
        """Return actual cash total from session entries."""
        total = 0.0
        for entry in session.entries:
            if 'cash' in entry.payment_method.lower():
                total += entry.actual_amount
        return total

    def summarize(self, session) -> ReconSummary:
        """Return summary for cash module."""
        expected = self.get_expected(session)
        actual = self.get_actual(session)
        variance = actual - expected
        entries_count = len([e for e in session.entries if 'cash' in e.payment_method.lower()])
        status = "reconciled" if abs(variance) < 0.01 else "exception"
        return ReconSummary(
            module_key=self.module_key,
            module_name=self.module_name,
            total_system=expected,
            total_actual=actual,
            total_variance=variance,
            entries_count=entries_count,
            status=status
        )

    def validate(self, session) -> List[ReconException]:
        """Validate cash reconciliation."""
        exceptions = []
        summary = self.summarize(session)
        if abs(summary.total_variance) > 0.01:
            exceptions.append(ReconException(
                module_key=self.module_key,
                description=f"Cash variance: {summary.total_variance:.2f}",
                severity="error" if abs(summary.total_variance) > 10 else "warning"
            ))
        return exceptions


# Instance for auto-discovery
adapter = CashAdapter()