"""Item portions module for preset fractional quantities."""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from database.init_db import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def create_portion(
    item_id: int,
    portion_name: str,
    portion_ml: float,
    selling_price: float,
    cost_price: float = 0,
    sort_order: int = 0,
) -> dict:
    """Create a new preset portion for an item."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """INSERT INTO item_portions 
               (item_id, portion_name, portion_ml, selling_price, cost_price, sort_order)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (item_id, portion_name, portion_ml, selling_price, cost_price, sort_order),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM item_portions WHERE rowid = last_insert_rowid()"
        ).fetchone()
        return _row_to_dict(row)


def update_portion(portion_id: int, **fields) -> Optional[dict]:
    """Update an existing portion."""
    if not fields:
        return get_portion(portion_id)
    
    allowed = {"portion_name", "portion_ml", "selling_price", "cost_price", "is_active", "sort_order"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    
    if not fields:
        return get_portion(portion_id)
    
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [portion_id]
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(f"UPDATE item_portions SET {set_clause} WHERE portion_id = ?", values)
        conn.commit()
        row = conn.execute("SELECT * FROM item_portions WHERE portion_id = ?", (portion_id,)).fetchone()
        return _row_to_dict(row) if row else None


def delete_portion(portion_id: int) -> bool:
    """Delete a portion."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM item_portions WHERE portion_id = ?", (portion_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_portion(portion_id: int) -> Optional[dict]:
    """Get a single portion by ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM item_portions WHERE portion_id = ?", (portion_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_portions(item_id: int, active_only: bool = True) -> List[dict]:
    """List all portions for an item."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM item_portions WHERE item_id = ?"
        params = [item_id]
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY sort_order, portion_ml"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]


def has_portions(item_id: int) -> bool:
    """Check if an item has any active preset portions."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM item_portions WHERE item_id = ? AND is_active = 1",
            (item_id,)
        ).fetchone()
        return row[0] > 0 if row else False


def create_default_portions(item_id: int, price_per_liter: float, cost_per_liter: float = 0) -> List[dict]:
    """Create default preset portions (1/4L, 1/2L, 3/4L, 1L) for an item."""
    portions = [
        {"name": "1/4 L (250ml)", "ml": 250, "factor": 0.25},
        {"name": "1/2 L (500ml)", "ml": 500, "factor": 0.5},
        {"name": "3/4 L (750ml)", "ml": 750, "factor": 0.75},
        {"name": "1 L (1000ml)", "ml": 1000, "factor": 1.0},
    ]
    
    created = []
    for i, p in enumerate(portions):
        try:
            portion = create_portion(
                item_id=item_id,
                portion_name=p["name"],
                portion_ml=p["ml"],
                selling_price=round(price_per_liter * p["factor"], 2),
                cost_price=round(cost_per_liter * p["factor"], 2) if cost_per_liter else 0,
                sort_order=i,
            )
            created.append(portion)
        except sqlite3.IntegrityError:
            # Portion already exists
            pass
    return created
