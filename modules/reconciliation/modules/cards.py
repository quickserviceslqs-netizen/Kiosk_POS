"""Card payment module adapter: credit/debit cards."""
from __future__ import annotations
from typing import List
from ..models import ModuleEntry
from modules.external_accounts import account_manager

MODULE_KEY = "cards"
MODULE_NAME = "Cards"


def get_entries(start_date: str, end_date: str) -> List[ModuleEntry]:
    """Return card-related ModuleEntry objects by filtering known card-like payment methods."""
    balances = account_manager.get_balances_by_payment_method()
    entries = []
    for pm, amt in balances.items():
        low = pm.lower()
        if 'card' in low or 'credit' in low or 'debit' in low:
            entries.append(ModuleEntry(payment_method=pm, system_amount=float(amt)))
    return entries
