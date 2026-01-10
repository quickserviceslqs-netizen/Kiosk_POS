"""POS cart/sales helpers."""
from __future__ import annotations

import sqlite3
import random
import string
from datetime import datetime
from typing import Iterable, List

from database.init_db import get_connection


class InsufficientStock(Exception):
    pass


def _now_date_time() -> Tuple[str, str]:
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")


def _generate_receipt_number(conn: sqlite3.Connection) -> str:
    """Generate a unique receipt number: REC-YYYYMMDD-XXXX"""
    date_part = datetime.now().strftime("%Y%m%d")
    
    while True:
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        receipt_number = f"REC-{date_part}-{random_code}"
        
        # Check if unique
        if not conn.execute("SELECT 1 FROM sales WHERE receipt_number = ?", (receipt_number,)).fetchone():
            return receipt_number


def create_sale(
    line_items: Iterable[dict],
    *,
    payment: float,
    payment_method: str | None = None,
    change: float = 0.0,
    vat_amount: float = 0.0,
    discount_amount: float = 0.0,
) -> dict:
    """Insert a sale with line_items = [{item_id, quantity, price}], returns identifiers."""
    date_str, time_str = _now_date_time()

    # sanitize and compute total
    sanitized: List[dict] = []  # {item_id, quantity, price, cost_price, stock_units}
    subtotal = 0.0
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # First pass: validate and get cost prices
        for li in line_items:
            item_id = int(li["item_id"])
            price = float(li.get("price", 0.0))
            qty_raw = float(li.get("quantity", 1))

            # Get item row for stock/cost and special-volume flags
            item_row = conn.execute(
                "SELECT quantity, cost_price, is_special_volume, unit_size_ml, cost_price_per_unit, unit_multiplier FROM items WHERE item_id = ?",
                (item_id,),
            ).fetchone()
            if item_row is None:
                raise ValueError(f"Item {item_id} not found")
            unit_size = float(item_row["unit_size_ml"] or 1000)
            stored_multiplier = float(item_row["unit_multiplier"] or 1)
            stored_cost_per_unit = item_row["cost_price_per_unit"]
            is_special = bool(li.get("is_special_volume") or item_row["is_special_volume"])

            if is_special:
                qty_small = float(li.get("qty_ml") or qty_raw)
                price_per_unit = float(li.get("price_per_ml") or price)
                multiplier = float(li.get("unit_multiplier", stored_multiplier))
                if price_per_unit <= 0 and unit_size:
                    price_per_unit = price / (unit_size * multiplier)
                if qty_small <= 0:
                    continue
                available_units = float(item_row["quantity"])
                available_small = available_units * unit_size * multiplier
                if qty_small > available_small:
                    display_unit = li.get("display_unit", "unit")
                    raise InsufficientStock(
                        f"Item {item_id} insufficient stock: need {qty_small:.2f} {display_unit}, have {available_small:.2f} {display_unit}"
                    )

                stock_units = qty_small / (unit_size * multiplier) if (unit_size * multiplier) else qty_small
                # Use stored cost_price_per_unit if available, otherwise calculate
                if stored_cost_per_unit is not None:
                    cost_price = stored_cost_per_unit
                else:
                    cost_price = float(li.get("cost_price_override") or item_row["cost_price"]) / (unit_size * multiplier or 1)
                subtotal += price_per_unit * qty_small
                sanitized.append(
                    {
                        "item_id": item_id,
                        "quantity": qty_small,
                        "price": price_per_unit,
                        "cost_price": cost_price,
                        "stock_units": stock_units,
                    }
                )
            else:
                qty = int(qty_raw) if qty_raw.is_integer() else float(qty_raw)
                if qty <= 0:
                    continue
                cost_price = float(item_row["cost_price"])
                subtotal += price * qty
                sanitized.append(
                    {
                        "item_id": item_id,
                        "quantity": qty,
                        "price": price,
                        "cost_price": cost_price,
                        "stock_units": qty,
                    }
                )

        if not sanitized:
            raise ValueError("No valid line items provided")

        try:
            conn.execute("BEGIN")
            # check stock
            for entry in sanitized:
                item_id = entry["item_id"]
                stock_units = entry["stock_units"]
                row = conn.execute("SELECT quantity FROM items WHERE item_id = ?", (item_id,)).fetchone()
                if row is None:
                    raise ValueError(f"Item {item_id} not found")
                if row["quantity"] < stock_units:
                    raise InsufficientStock(f"Item {item_id} insufficient stock")

            # Calculate totals: total = subtotal + vat - discount
            total = subtotal + vat_amount - discount_amount
            
            # Generate unique receipt number
            receipt_number = _generate_receipt_number(conn)
            
            cursor = conn.execute(
                "INSERT INTO sales (receipt_number, date, time, total, payment, change, payment_received, payment_method, subtotal, vat_amount, discount_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (receipt_number, date_str, time_str, total, payment, change, payment, payment_method or "Cash", subtotal, vat_amount, discount_amount),
            )
            sale_id = cursor.lastrowid

            for entry in sanitized:
                item_id = entry["item_id"]
                qty = entry["quantity"]
                price = entry["price"]
                cost_price = entry["cost_price"]
                stock_units = entry["stock_units"]
                conn.execute(
                    "INSERT INTO sales_items (sale_id, item_id, quantity, price, cost_price) VALUES (?, ?, ?, ?, ?)",
                    (sale_id, item_id, qty, price, cost_price),
                )
                conn.execute(
                    "UPDATE items SET quantity = quantity - ? WHERE item_id = ?",
                    (stock_units, item_id),
                )
            conn.commit()
            return {"sale_id": sale_id, "receipt_number": receipt_number}
        except Exception:
            conn.rollback()
            raise
