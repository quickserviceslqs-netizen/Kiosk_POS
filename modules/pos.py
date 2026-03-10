"""POS cart/sales helpers."""
from __future__ import annotations

import sqlite3
import random
import string
from datetime import datetime
from typing import Iterable, List, Tuple, Optional
import logging

from database.init_db import get_connection
from modules import reports

logger = logging.getLogger(__name__)


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


def _ensure_sale_payments_table(conn: sqlite3.Connection) -> None:
    """Create sale_payments table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sale_payments (
            sale_payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id         INTEGER NOT NULL REFERENCES sales(sale_id) ON DELETE CASCADE,
            payment_method  TEXT NOT NULL,
            amount          REAL NOT NULL,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        )
        """
    )


def create_sale(
    line_items: Iterable[dict],
    *,
    payment: float,
    payment_method: str | None = None,
    split_payments: list[dict] | None = None,
    change: float = 0.0,
    vat_amount: float = 0.0,
    discount_amount: float = 0.0,
) -> dict:
    """Insert a sale.  *split_payments* is a list of ``{method, amount}`` dicts
    for multi-payment-method transactions.  When provided, *payment_method* on
    the sale row is set to ``"Split"`` and the breakdown is stored in
    ``sale_payments``."""
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
                        "variant_id": li.get("variant_id"),
                        "portion_id": li.get("portion_id"),
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
                        "variant_id": li.get("variant_id"),
                        "portion_id": li.get("portion_id"),
                    }
                )

        if not sanitized:
            raise ValueError("No valid line items provided")

        try:
            conn.execute("BEGIN")
            # create split payments table if needed
            _ensure_sale_payments_table(conn)
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
            
            # Resolve payment method label and total payment amount
            if split_payments:
                payment_method_label = "Split"
                payment_total = sum(float(sp["amount"]) for sp in split_payments)
                change = max(0.0, payment_total - total)
            else:
                payment_method_label = payment_method or "Cash"
                payment_total = payment
            
            # Generate unique receipt number
            receipt_number = _generate_receipt_number(conn)
            
            cursor = conn.execute(
                "INSERT INTO sales (receipt_number, date, time, total, payment, change, payment_received, payment_method, subtotal, vat_amount, discount_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (receipt_number, date_str, time_str, total, payment_total, change, payment_total, payment_method_label, subtotal, vat_amount, discount_amount),
            )
            sale_id = cursor.lastrowid

            # Record individual split payment rows when applicable
            if split_payments:
                for sp in split_payments:
                    conn.execute(
                        "INSERT INTO sale_payments (sale_id, payment_method, amount) VALUES (?, ?, ?)",
                        (sale_id, sp["method"], float(sp["amount"])),
                    )

            for entry in sanitized:
                item_id = entry["item_id"]
                qty = entry["quantity"]
                price = entry["price"]
                stock_units = entry["stock_units"]
                variant_id = entry.get("variant_id")
                portion_id = entry.get("portion_id")
                
                # Determine cost price using lot-based costing if available
                actual_cost_price = entry["cost_price"]
                lot_allocations = []
                
                try:
                    # Try to use lot-based costing.
                    # stock_lots uses integer quantities; fractional sales (special-volume
                    # items where stock_units < 1) are tracked via the items.quantity column
                    # directly and do not use lot allocation.
                    alloc_units = int(stock_units)
                    lot_allocations = _allocate_from_lots(conn, item_id, alloc_units, variant_id) if alloc_units >= 1 else []
                    if lot_allocations:
                        # Calculate weighted average cost from lot allocations
                        total_cost = sum(a["quantity"] * a["unit_cost"] for a in lot_allocations)
                        total_qty = sum(a["quantity"] for a in lot_allocations)
                        if total_qty > 0:
                            actual_cost_price = total_cost / total_qty
                except Exception as e:
                    # Fall back to item's cost_price if lot allocation fails
                    logger.debug(f"Lot allocation skipped for item {item_id}: {e}")
                
                # Insert sale item with variant and portion tracking
                cursor = conn.execute(
                    "INSERT INTO sales_items (sale_id, item_id, variant_id, portion_id, quantity, price, cost_price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sale_id, item_id, variant_id, portion_id, qty, price, actual_cost_price),
                )
                sale_item_id = cursor.lastrowid
                
                # Record lot allocations if we have them
                if lot_allocations:
                    _record_lot_deductions(conn, item_id, lot_allocations, sale_item_id, variant_id)
                else:
                    # Legacy: Deduct stock directly without lot tracking
                    if variant_id:
                        conn.execute(
                            "UPDATE item_variants SET quantity = quantity - ? WHERE variant_id = ?",
                            (stock_units, variant_id),
                        )
                    else:
                        conn.execute(
                            "UPDATE items SET quantity = quantity - ? WHERE item_id = ?",
                            (stock_units, item_id),
                        )
                        
            conn.commit()
            return {"sale_id": sale_id, "receipt_number": receipt_number}
        except Exception:
            conn.rollback()
            raise
        finally:
            # Invalidate report cache after sale creation
            reports.invalidate_cache()


def _allocate_from_lots(
    conn: sqlite3.Connection,
    item_id: int,
    quantity_needed: int,
    variant_id: Optional[int] = None
) -> List[dict]:
    """Allocate stock from lots using the configured costing method.
    
    Args:
        conn: Database connection
        item_id: Item ID
        quantity_needed: Quantity to allocate
        variant_id: Optional variant ID
        
    Returns:
        List of allocation dicts with lot_id, quantity, unit_cost
    """
    # Check if item has any stock lots
    query = "SELECT COUNT(*) FROM stock_lots WHERE item_id = ? AND quantity_remaining > 0"
    params = [item_id]
    if variant_id:
        query += " AND variant_id = ?"
        params.append(variant_id)
    
    lot_count = conn.execute(query, params).fetchone()[0]
    if lot_count == 0:
        return []  # No lots, use legacy method
    
    # Get costing method from settings
    method_row = conn.execute(
        "SELECT value FROM settings WHERE key = 'inventory_costing_method'"
    ).fetchone()
    method = method_row[0] if method_row else "FIFO"
    
    # Build allocation query based on method
    if method == "LIFO":
        order_by = "ORDER BY purchase_date DESC, lot_id DESC"
    else:  # FIFO is default
        order_by = "ORDER BY purchase_date ASC, lot_id ASC"
    
    query = f"""
        SELECT lot_id, quantity_remaining, cost_price
        FROM stock_lots
        WHERE item_id = ? AND quantity_remaining > 0
    """
    params = [item_id]
    if variant_id:
        query += " AND variant_id = ?"
        params.append(variant_id)
    query += f" {order_by}"
    
    lots = conn.execute(query, params).fetchall()
    
    allocations = []
    remaining = quantity_needed
    
    for lot in lots:
        if remaining <= 0:
            break
        
        take = min(remaining, lot[1])  # lot[1] = quantity_remaining
        allocations.append({
            "lot_id": lot[0],
            "quantity": take,
            "unit_cost": lot[2]  # lot[2] = cost_price
        })
        remaining -= take
    
    # For WAC method, adjust all costs to weighted average
    if method == "WAC" and allocations:
        # Calculate weighted average from all lots with stock
        wac_query = """
            SELECT SUM(quantity_remaining * cost_price) / SUM(quantity_remaining)
            FROM stock_lots
            WHERE item_id = ? AND quantity_remaining > 0
        """
        wac_params = [item_id]
        if variant_id:
            wac_query = wac_query.replace("WHERE item_id = ?", "WHERE item_id = ? AND variant_id = ?")
            wac_params.append(variant_id)
        
        wac_result = conn.execute(wac_query, wac_params).fetchone()
        wac = wac_result[0] if wac_result and wac_result[0] else 0
        
        # Apply WAC to all allocations
        for alloc in allocations:
            alloc["unit_cost"] = wac
    
    return allocations


def _record_lot_deductions(
    conn: sqlite3.Connection,
    item_id: int,
    allocations: List[dict],
    sale_item_id: int,
    variant_id: Optional[int] = None
) -> None:
    """Deduct stock from lots and record allocations.
    
    Args:
        conn: Database connection
        item_id: Item ID
        allocations: List of allocation dicts
        sale_item_id: Sale item ID for reference
        variant_id: Optional variant ID
    """
    total_qty = 0
    
    for alloc in allocations:
        # Deduct from lot
        conn.execute(
            "UPDATE stock_lots SET quantity_remaining = quantity_remaining - ? WHERE lot_id = ?",
            (alloc["quantity"], alloc["lot_id"])
        )
        
        # Record stock movement
        conn.execute(
            """
            INSERT INTO stock_movements
            (item_id, variant_id, lot_id, movement_type, quantity, unit_cost, total_cost,
             reference_id, reference_type)
            VALUES (?, ?, ?, 'sale', ?, ?, ?, ?, 'sale_item')
            """,
            (item_id, variant_id, alloc["lot_id"], -alloc["quantity"],
             alloc["unit_cost"], alloc["quantity"] * alloc["unit_cost"], sale_item_id)
        )
        
        # Record lot allocation for sale item
        conn.execute(
            """
            INSERT INTO sale_lot_allocations
            (sale_item_id, lot_id, quantity, unit_cost)
            VALUES (?, ?, ?, ?)
            """,
            (sale_item_id, alloc["lot_id"], alloc["quantity"], alloc["unit_cost"])
        )
        
        total_qty += alloc["quantity"]
    
    # Update item's total quantity
    conn.execute(
        "UPDATE items SET quantity = quantity - ? WHERE item_id = ?",
        (total_qty, item_id)
    )
    
    # Update variant quantity if applicable
    if variant_id:
        conn.execute(
            "UPDATE item_variants SET quantity = quantity - ? WHERE variant_id = ?",
            (total_qty, variant_id)
        )
