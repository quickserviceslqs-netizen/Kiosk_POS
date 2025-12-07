"""VAT rates data access helpers."""
from __future__ import annotations

import sqlite3
from typing import Optional

from database.init_db import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_vat_rates(active_only: bool = True) -> list[dict]:
    """Return all VAT rates, optionally filtered by active status."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM vat_rates"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY rate ASC"
        rows = conn.execute(query).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_vat_rate(vat_id: int) -> Optional[dict]:
    """Return a single VAT rate by ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM vat_rates WHERE vat_id = ?", (vat_id,)).fetchone()
    return _row_to_dict(row) if row else None


def create_vat_rate(*, rate: float, description: str = "", active: bool = True) -> dict:
    """Create a new VAT rate."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO vat_rates (rate, description, active) VALUES (?, ?, ?)",
            (rate, description, int(active))
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM vat_rates WHERE rowid = last_insert_rowid()").fetchone()
    return _row_to_dict(row)


def update_vat_rate(vat_id: int, **fields) -> Optional[dict]:
    """Update a VAT rate."""
    if not fields:
        return get_vat_rate(vat_id)
    
    allowed = {"rate", "description", "active"}
    updates = {k: v if k != "active" else int(v) for k, v in fields.items() if k in allowed}
    if not updates:
        return get_vat_rate(vat_id)
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    params = list(updates.values()) + [vat_id]
    
    with get_connection() as conn:
        conn.execute(f"UPDATE vat_rates SET {set_clause} WHERE vat_id = ?", params)
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM vat_rates WHERE vat_id = ?", (vat_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_vat_rate(vat_id: int) -> None:
    """Delete a VAT rate (soft delete by setting active=0)."""
    with get_connection() as conn:
        conn.execute("UPDATE vat_rates SET active = 0 WHERE vat_id = ?", (vat_id,))
        conn.commit()


def get_active_rates_list() -> list[float]:
    """Return a list of active VAT rate values for UI dropdowns."""
    rates = list_vat_rates(active_only=True)
    return [r["rate"] for r in rates]
