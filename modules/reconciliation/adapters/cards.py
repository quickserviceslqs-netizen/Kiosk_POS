"""Card payment module adapter: credit/debit cards."""
from __future__ import annotations
from typing import List
from ..adapter_base import ReconAdapterBase
from ..models import ReconSummary, ReconException, ReconEntry
from modules.external_accounts import account_manager


class CardsAdapter(ReconAdapterBase):
    """Adapter for card payment reconciliation."""

    @property
    def module_key(self) -> str:
        return "cards"

    @property
    def module_name(self) -> str:
        return "Cards"

    def get_expected(self, session) -> float:
        """Return expected card total from system."""
        balances = account_manager.get_balances_by_payment_method()
        total = 0.0
        for pm, amt in balances.items():
            low = pm.lower()
            if 'card' in low or 'credit' in low or 'debit' in low:
                total += float(amt)
        return total

    def get_entries(self, session) -> List[ReconEntry]:
        """Return a list of ReconEntry objects for card payment methods in the session period."""
        balances = account_manager.get_balances_by_payment_method()
        entries: List[ReconEntry] = []
        for pm, amt in balances.items():
            low = pm.lower()
            if 'card' in low or 'credit' in low or 'debit' in low:
                entries.append(ReconEntry(payment_method=pm, system_amount=float(amt), actual_amount=0.0))
        return entries

    def get_actual(self, session) -> float:
        """Return actual card total from session entries."""
        total = 0.0
        for entry in session.entries:
            low = entry.payment_method.lower()
            if 'card' in low or 'credit' in low or 'debit' in low:
                total += entry.actual_amount
        return total

    def summarize(self, session) -> ReconSummary:
        """Return summary for cards module."""
        expected = self.get_expected(session)
        actual = self.get_actual(session)
        variance = actual - expected
        entries_count = len([e for e in session.entries if any(x in e.payment_method.lower() for x in ['card', 'credit', 'debit'])])
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
        """Validate card reconciliation."""
        exceptions = []
        summary = self.summarize(session)
        if abs(summary.total_variance) > 0.01:
            exceptions.append(ReconException(
                module_key=self.module_key,
                description=f"Cards variance: {summary.total_variance:.2f}",
                severity="error" if abs(summary.total_variance) > 10 else "warning"
            ))
        return exceptions


# Instance for auto-discovery
adapter = CardsAdapter()