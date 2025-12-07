"""POS cart/sales helpers."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Iterable, List, Tuple

from database.init_db import get_connection


class InsufficientStock(Exception):
    pass


def _now_date_time() -> Tuple[str, str]:
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")


def create_sale(
    line_items: Iterable[dict],
    *,
    payment: float,
    payment_method: str | None = None,
    change: float = 0.0,
) -> int:
    """Insert a sale with line_items = [{item_id, quantity, price}], returns sale_id."""
    date_str, time_str = _now_date_time()

    # sanitize and compute total
    sanitized: List[Tuple[int, int, float, float]] = []  # (item_id, qty, price, cost_price)
    total = 0.0
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # First pass: validate and get cost prices
        for li in line_items:
            item_id = int(li["item_id"])
            qty = int(li.get("quantity", 1))
            price = float(li.get("price", 0.0))
            if qty <= 0:
                continue
            
            # Get cost_price from items table
            item_row = conn.execute("SELECT cost_price FROM items WHERE item_id = ?", (item_id,)).fetchone()
            if item_row is None:
                raise ValueError(f"Item {item_id} not found")
            cost_price = float(item_row["cost_price"])
            
            total += price * qty
            sanitized.append((item_id, qty, price, cost_price))

        if not sanitized:
            raise ValueError("No valid line items provided")

        try:
            conn.execute("BEGIN")
            # check stock
            for item_id, qty, _, _ in sanitized:
                row = conn.execute("SELECT quantity FROM items WHERE item_id = ?", (item_id,)).fetchone()
                if row is None:
                    raise ValueError(f"Item {item_id} not found")
                if row["quantity"] < qty:
                    raise InsufficientStock(f"Item {item_id} insufficient stock")

            cursor = conn.execute(
                "INSERT INTO sales (date, time, total, payment, change) VALUES (?, ?, ?, ?, ?)",
                (date_str, time_str, total, payment, change),
            )
            sale_id = cursor.lastrowid

            for item_id, qty, price, cost_price in sanitized:
                conn.execute(
                    "INSERT INTO sales_items (sale_id, item_id, quantity, price, cost_price) VALUES (?, ?, ?, ?, ?)",
                    (sale_id, item_id, qty, price, cost_price),
                )
                conn.execute(
                    "UPDATE items SET quantity = quantity - ? WHERE item_id = ?",
                    (qty, item_id),
                )
            conn.commit()
            return sale_id
        except Exception:
            conn.rollback()
            raise
