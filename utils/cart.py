"""Pure cart calculation helpers.

Provides functions to compute subtotal, discount, VAT, and total from precomputed line totals.
"""
from __future__ import annotations

from typing import Iterable, Dict


def compute_totals_from_line_totals(entries: Iterable[Dict], discount_pct: float = 0.0, vat_enabled: bool = True, default_vat_percent: float = 16.0) -> Dict[str, float]:
    """Compute subtotal, discount amount, VAT amount and grand total.

    entries: iterable of dict-like objects where each entry should have a
      ``_line_total`` numeric key (falling back to ``price * quantity`` if
      missing) and may optionally contain a ``vat_rate`` percentage.
    discount_pct: fraction (e.g., 0.10 for 10%) to apply across the cart.
    vat_enabled: whether VAT should be calculated.
    default_vat_percent: default VAT percentage to use when an entry doesn't
      provide ``vat_rate``.

    Returns dict with keys: subtotal, discount_amt, vat_amt, total
    """
    subtotal = 0.0
    for entry in entries:
        try:
            line = float(entry.get("_line_total", entry.get("price", 0) * entry.get("quantity", 0)))
        except Exception:
            line = 0.0
        subtotal += line

    discount_amt = subtotal * (discount_pct or 0.0)
    vat_amt = 0.0

    if vat_enabled:
        for entry in entries:
            try:
                line = float(entry.get("_line_total", entry.get("price", 0) * entry.get("quantity", 0)))
            except Exception:
                line = 0.0
            item_discount = line * (discount_pct or 0.0)
            item_vat_base = line - item_discount
            try:
                item_vat = float(entry.get("vat_rate", default_vat_percent)) / 100.0
            except Exception:
                item_vat = float(default_vat_percent) / 100.0
            vat_amt += item_vat_base * item_vat

    total = (subtotal - discount_amt) + vat_amt

    return {
        "subtotal": subtotal,
        "discount_amt": discount_amt,
        "vat_amt": vat_amt,
        "total": total,
    }