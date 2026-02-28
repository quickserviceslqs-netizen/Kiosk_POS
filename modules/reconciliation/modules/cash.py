"""Cash module adapter: provides cash-related entries."""
from __future__ import annotations
from typing import List
from ..models import ModuleEntry
from modules.external_accounts import account_manager

MODULE_KEY = "cash"
MODULE_NAME = "Cash"


def get_entries(start_date: str, end_date: str) -> List[ModuleEntry]:
    """Return list of ModuleEntry objects for cash payment methods in the period.
    For now, this uses account_manager balances and exposes any payment method with 'Cash' in the name.
    """
    balances = account_manager.get_balances_by_payment_method()
    entries = []
    for pm, amt in balances.items():
        if 'cash' in pm.lower() or pm.lower() == 'cash':
            entries.append(ModuleEntry(payment_method=pm, system_amount=float(amt)))
    return entries
