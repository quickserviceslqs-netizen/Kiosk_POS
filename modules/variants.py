"""Variant management for items (e.g., sizes, colors, etc.)."""
from database.init_db import get_connection


def create_variant(item_id: int, variant_name: str, selling_price: float, cost_price: float = 0, 
                   quantity: int = 0, barcode: str = None, sku: str = None, vat_rate: float = 16.0, 
                   low_stock_threshold: int = 10, image_path: str = None) -> int:
    """Create a new variant for an item."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO item_variants (item_id, variant_name, selling_price, cost_price, quantity, 
                                       barcode, sku, vat_rate, low_stock_threshold, image_path, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (item_id, variant_name, selling_price, cost_price, quantity, barcode, sku, vat_rate, low_stock_threshold, image_path)
        )
        conn.commit()
        return cursor.lastrowid


def list_variants(item_id: int) -> list[dict]:
    """Get all variants for an item."""
    with get_connection() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        rows = conn.execute(
            """
            SELECT variant_id, item_id, variant_name, selling_price, cost_price, quantity, barcode, sku, 
                   vat_rate, low_stock_threshold, image_path, is_active, created_at
            FROM item_variants
            WHERE item_id = ?
            ORDER BY variant_name
            """,
            (item_id,)
        ).fetchall()
        return rows


def get_variant(variant_id: int) -> dict | None:
    """Get a single variant by ID."""
    with get_connection() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        row = conn.execute(
            """
            SELECT variant_id, item_id, variant_name, selling_price, cost_price, quantity, barcode, sku, 
                   vat_rate, low_stock_threshold, image_path, is_active, created_at
            FROM item_variants
            WHERE variant_id = ?
            """,
            (variant_id,)
        ).fetchone()
        return row


def update_variant(variant_id: int, variant_name: str = None, selling_price: float = None, 
                   cost_price: float = None, quantity: int = None, barcode: str = None, sku: str = None, 
                   vat_rate: float = None, low_stock_threshold: int = None, image_path: str = None, 
                   is_active: bool = None) -> None:
    """Update a variant."""
    with get_connection() as conn:
        updates = []
        params = []
        if variant_name is not None:
            updates.append("variant_name = ?")
            params.append(variant_name)
        if selling_price is not None:
            updates.append("selling_price = ?")
            params.append(selling_price)
        if cost_price is not None:
            updates.append("cost_price = ?")
            params.append(cost_price)
        if quantity is not None:
            updates.append("quantity = ?")
            params.append(quantity)
        if barcode is not None:
            updates.append("barcode = ?")
            params.append(barcode)
        if sku is not None:
            updates.append("sku = ?")
            params.append(sku)
        if vat_rate is not None:
            updates.append("vat_rate = ?")
            params.append(vat_rate)
        if low_stock_threshold is not None:
            updates.append("low_stock_threshold = ?")
            params.append(low_stock_threshold)
        if image_path is not None:
            updates.append("image_path = ?")
            params.append(image_path)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if not updates:
            return
        
        params.append(variant_id)
        conn.execute(f"UPDATE item_variants SET {', '.join(updates)} WHERE variant_id = ?", params)
        conn.commit()


def delete_variant(variant_id: int) -> None:
    """Delete a variant."""
    with get_connection() as conn:
        conn.execute("DELETE FROM item_variants WHERE variant_id = ?", (variant_id,))
        conn.commit()


def has_variants(item_id: int) -> bool:
    """Check if an item has any variants."""
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM item_variants WHERE item_id = ?", (item_id,)).fetchone()[0]
        return count > 0
