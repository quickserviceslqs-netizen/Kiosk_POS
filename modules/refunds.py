"""Refund and return management."""
from __future__ import annotations

import sqlite3
import random
import string
from datetime import datetime
from database.init_db import get_connection
from modules import items
from modules import reports


class RefundError(Exception):
    pass


def _generate_refund_code(conn: sqlite3.Connection) -> str:
    """Generate a unique refund code in format REF-YYYYMMDD-XXXX."""
    date_part = datetime.now().strftime("%Y%m%d")
    
    while True:
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        refund_code = f"REF-{date_part}-{random_code}"
        
        # Check uniqueness
        existing = conn.execute("SELECT 1 FROM refunds WHERE refund_code = ?", (refund_code,)).fetchone()
        if not existing:
            return refund_code


def create_refund(
    original_sale_id: int,
    refund_items: list[dict],  # [{item_id, quantity_to_refund}, ...]
    reason: str = "",
    refund_amount: float = 0.0,
) -> dict:
    """Process a refund and restore items to inventory.
    
    Args:
        original_sale_id: ID of the original sale being refunded
        refund_items: List of items to refund with quantities
        reason: Reason for refund
        refund_amount: Amount to refund (if 0, calculated from items)
    
    Returns:
        Refund record
    """
    if not original_sale_id or original_sale_id <= 0:
        raise RefundError("Invalid sale ID for refund")
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Verify original sale exists
        original_sale = conn.execute(
            "SELECT * FROM sales WHERE sale_id = ?",
            (original_sale_id,)
        ).fetchone()
        
        if not original_sale:
            raise RefundError(f"Sale #{original_sale_id} not found")
        
        # NOTE: Allow multiple refunds per sale (partial refunds supported).
        # We'll validate quantities against previously refunded quantities for each sale_item.
        def _get_already_refunded_qty(sale_item_id: int) -> float:
            row = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) AS refunded_qty FROM refunds_items WHERE sale_item_id = ?",
                (sale_item_id,)
            ).fetchone()
            return float(row["refunded_qty"] or 0) if row else 0.0

        def _get_already_refunded_by_sale_and_item(sale_id: int, item_id: int) -> float:
            row = conn.execute(
                "SELECT COALESCE(SUM(quantity),0) AS refunded_qty FROM refunds_items WHERE sale_id = ? AND item_id = ?",
                (sale_id, item_id)
            ).fetchone()
            return float(row["refunded_qty"] or 0) if row else 0.0
        
        try:
            # Ensure refunds_items table exists (for older DBs that may lack it)
            t = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='refunds_items'").fetchone()
            if not t:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS refunds_items (
                        refund_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        refund_id INTEGER NOT NULL,
                        sale_item_id INTEGER,
                        sale_id INTEGER NOT NULL,
                        item_id INTEGER NOT NULL,
                        quantity REAL NOT NULL,
                        line_total REAL NOT NULL
                    );
                    """
                )

            # Load sale monetary context for prorating VAT/discount if available
            sale_subtotal = original_sale["subtotal"] if "subtotal" in original_sale.keys() else None
            sale_vat = original_sale["vat_amount"] if "vat_amount" in original_sale.keys() else 0.0
            sale_discount = original_sale["discount_amount"] if "discount_amount" in original_sale.keys() else 0.0

            # Collect item rows and validate quantities (support sale_item_id where provided)
            selected_rows = []
            for refund_item in refund_items:
                sale_item = None
                if refund_item.get("sale_item_id"):
                    sale_item = conn.execute(
                        "SELECT * FROM sales_items WHERE sale_item_id = ? AND sale_id = ?",
                        (refund_item["sale_item_id"], original_sale_id)
                    ).fetchone()
                else:
                    # fallback: find a sale_item row matching item_id (choose first with remaining refundable quantity)
                    rows = conn.execute(
                        "SELECT * FROM sales_items WHERE sale_id = ? AND item_id = ? ORDER BY sale_item_id",
                        (original_sale_id, refund_item["item_id"])
                    ).fetchall()
                    for r in rows:
                        sale_item_id = r["sale_item_id"] if "sale_item_id" in r.keys() else None
                        already_refunded = _get_already_refunded_qty(sale_item_id) if sale_item_id else 0.0
                        remaining = r["quantity"] - already_refunded
                        if remaining > 0:
                            sale_item = r
                            break

                if not sale_item:
                    raise RefundError(f"Item #{refund_item.get('item_id')} not found or nothing refundable in original sale")

                qty_to_refund = float(refund_item.get("quantity", sale_item["quantity"]))
                # Check against previously refunded quantity for this sale_item
                sale_item_id = sale_item["sale_item_id"] if "sale_item_id" in sale_item.keys() else None
                already = _get_already_refunded_qty(sale_item_id) if sale_item_id else 0.0
                if qty_to_refund > (sale_item["quantity"] - already):
                    raise RefundError(
                        f"Cannot refund {qty_to_refund} units of item #{refund_item.get('item_id')} "
                        f"(only {sale_item['quantity'] - already} remaining refundable)"
                    )

                line_total = sale_item["price"] * qty_to_refund
                selected_rows.append({
                    "sale_item_id": sale_item["sale_item_id"] if "sale_item_id" in sale_item.keys() else None,
                    "item_id": sale_item["item_id"],
                    "qty": qty_to_refund,
                    "line_total": line_total,
                    "full_quantity": sale_item["quantity"]
                })

            # Compute refund amount based on what was actually paid (always recompute)
            subtotal_selected = sum(r["line_total"] for r in selected_rows)
            refund_amount_calc = subtotal_selected

            if sale_subtotal and sale_subtotal > 0:
                proportion = subtotal_selected / sale_subtotal
                vat_share = sale_vat * proportion
                discount_share = sale_discount * proportion
                refund_amount_calc = subtotal_selected + vat_share - discount_share

            # Cap to original sale total to avoid rounding overages
            if "total" in original_sale.keys() and original_sale["total"] is not None:
                refund_amount_calc = min(refund_amount_calc, float(original_sale["total"]))

            refund_amount = max(refund_amount_calc, 0.0)

            # Always restore items to inventory
            for row in selected_rows:
                item_id = row["item_id"]
                qty_to_restore = row["qty"]
                
                # Check if this is a fractional/special volume item
                item_data = conn.execute(
                    "SELECT is_special_volume, unit_size_ml, unit_multiplier, unit_of_measure FROM items WHERE item_id = ?",
                    (item_id,)
                ).fetchone()
                
                if item_data and item_data["is_special_volume"]:
                    # Convert from small units (ml/g/cm) back to base units (L/kg/m)
                    unit_size = float(item_data["unit_size_ml"] or 1)
                    multiplier = float(item_data["unit_multiplier"] or 1)
                    # qty_to_restore is in small units (e.g., ml), convert to stock units
                    stock_units = qty_to_restore / (unit_size * multiplier) if (unit_size * multiplier) else qty_to_restore
                    items.add_stock(item_id, stock_units)
                else:
                    # Regular item - quantity is in whole units
                    items.add_stock(item_id, qty_to_restore)

            # Create refund record
            now = datetime.now()
            refund_code = _generate_refund_code(conn)
            refund_record = conn.execute(
                """INSERT INTO refunds 
                   (refund_code, original_sale_id, refund_amount, reason, created_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (refund_code, original_sale_id, refund_amount, reason, now.strftime("%Y-%m-%d %H:%M:%S"))
            )
            refund_id = refund_record.lastrowid

            # Insert refund line items into refunds_items table
            for row in selected_rows:
                conn.execute(
                    "INSERT INTO refunds_items (refund_id, sale_item_id, sale_id, item_id, quantity, line_total) VALUES (?, ?, ?, ?, ?, ?)",
                    (refund_id, row.get('sale_item_id'), original_sale_id, row.get('item_id'), row.get('qty'), row.get('line_total')),
                )

            conn.commit()
            
            # Get the created refund
            refund = conn.execute(
                "SELECT * FROM refunds WHERE refund_id = ?",
                (refund_id,)
            ).fetchone()
            
            return dict(refund)
        
        except Exception as e:
            conn.rollback()
            raise RefundError(str(e))
        finally:
            # Invalidate report cache after refund creation
            reports.invalidate_cache()


def get_refund(refund_id: int) -> dict | None:
    """Get refund details."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        refund = conn.execute("SELECT * FROM refunds WHERE refund_id = ?", (refund_id,)).fetchone()
        return dict(refund) if refund else None


def get_refunded_quantities_for_sale(original_sale_id: int) -> dict:
    """Return a mapping of sale_item_id to total refunded quantity for a sale."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT sale_item_id, COALESCE(SUM(quantity),0) AS refunded_qty FROM refunds_items WHERE sale_id = ? GROUP BY sale_item_id",
            (original_sale_id,)
        ).fetchall()
        return {row['sale_item_id']: float(row['refunded_qty']) for row in rows}


def is_sale_fully_refunded(original_sale_id: int) -> bool:
    """Return True if all sale line quantities have been refunded (considering refunds_items)."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        sale_items = conn.execute("SELECT * FROM sales_items WHERE sale_id = ?", (original_sale_id,)).fetchall()
        if not sale_items:
            return False
        refunded = get_refunded_quantities_for_sale(original_sale_id)
        for si in sale_items:
            sid = si['sale_item_id']
            already = refunded.get(sid, 0.0)
            if float(si['quantity']) > already:
                return False
        return True


def get_last_refund_for_sale(original_sale_id: int) -> dict | None:
    """Return the most recent refund record for a sale (if any)."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        r = conn.execute(
            "SELECT * FROM refunds WHERE original_sale_id = ? ORDER BY created_at DESC LIMIT 1",
            (original_sale_id,)
        ).fetchone()
        return dict(r) if r else None


def list_refunds(start_date: str = None, end_date: str = None) -> list[dict]:
    """List all refunds with optional date filtering."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = "SELECT * FROM refunds WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND DATE(created_at) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND DATE(created_at) <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC"
        
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_refund_for_sale(original_sale_id: int) -> dict | None:
    """Check if a sale has been refunded."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        refund = conn.execute(
            "SELECT * FROM refunds WHERE original_sale_id = ?",
            (original_sale_id,)
        ).fetchone()
        return dict(refund) if refund else None
