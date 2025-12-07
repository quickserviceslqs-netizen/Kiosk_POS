"""Inventory data access helpers."""
from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional

from database.init_db import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def create_item(
    *,
    name: str,
    category: str | None = None,
    cost_price: float = 0.0,
    selling_price: float = 0.0,
    quantity: int = 0,
    image_path: str | None = None,
    barcode: str | None = None,
    vat_rate: float = 16.0,
    low_stock_threshold: int = 10,
) -> dict:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO items (name, category, cost_price, selling_price, quantity, image_path, barcode, vat_rate, low_stock_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, cost_price, selling_price, quantity, image_path, barcode, vat_rate, low_stock_threshold),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM items WHERE rowid = last_insert_rowid();").fetchone()
    return _row_to_dict(row)


def update_item(item_id: int, **fields) -> Optional[dict]:
    if not fields:
        return get_item(item_id)

    allowed = {"name", "category", "cost_price", "selling_price", "quantity", "image_path", "barcode", "vat_rate", "low_stock_threshold"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_item(item_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    params = list(updates.values()) + [item_id]

    with get_connection() as conn:
        conn.execute(f"UPDATE items SET {set_clause} WHERE item_id = ?", params)
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_item(item_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
        conn.commit()


def get_item(item_id: int) -> Optional[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_items(search: str | None = None) -> List[dict]:
    like = f"%{search.lower()}%" if search else None
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if like:
            cursor = conn.execute(
                """
                SELECT * FROM items
                WHERE lower(name) LIKE ? OR lower(category) LIKE ? OR lower(barcode) LIKE ?
                ORDER BY name COLLATE NOCASE
                """,
                (like, like, like),
            )
        else:
            cursor = conn.execute("SELECT * FROM items ORDER BY name COLLATE NOCASE")
        return [_row_to_dict(row) for row in cursor.fetchall()]


def low_stock(threshold: int = 5) -> List[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM items WHERE quantity <= ? ORDER BY quantity ASC", (threshold,))
        return [_row_to_dict(row) for row in cursor.fetchall()]
