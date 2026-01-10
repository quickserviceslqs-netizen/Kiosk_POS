"""Inventory data access helpers."""
from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional

from database.init_db import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


from modules import units_of_measure as uom


def _get_unit_multiplier(unit_of_measure: str) -> float:
    """Get the multiplier for converting a large unit to its small unit count.

    Prefer database-configured conversion factors (via `units_of_measure`); fall back
    to sensible defaults for common names if the DB does not contain the unit.
    """
    if not unit_of_measure:
        return 1
    # Try database first (this allows admin-editable units)
    try:
        factor = uom.get_conversion_factor(unit_of_measure)
        return float(factor)
    except Exception:
        # Fallback mapping for common unit names
        unit = unit_of_measure.lower()
        unit_multipliers = {
            "liters": 1000, "litre": 1000, "liter": 1000, "litres": 1000, "l": 1000,
            "kilograms": 1000, "kilogram": 1000, "kg": 1000, "kgs": 1000,
            "meters": 100, "meter": 100, "metre": 100, "metres": 100, "m": 100,
            "pieces": 1, "piece": 1, "pcs": 1,
            "packs": 1, "pack": 1,
            "boxes": 1, "box": 1,
        }
        return unit_multipliers.get(unit, 1)


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
    unit_of_measure: str = "pieces",
    is_special_volume: int = 0,
    unit_size_ml: int | None = None,
    price_per_ml: float | None = None,
) -> dict:
    # Validation
    if not name or not name.strip():
        raise ValueError("Item name is required")
    if cost_price < 0 or selling_price < 0:
        raise ValueError("Prices cannot be negative")
    if selling_price < cost_price:
        raise ValueError("Selling price cannot be less than cost price")
    if quantity < 0:
        raise ValueError("Quantity cannot be negative")
    if barcode and len(barcode.strip()) > 0:
        # Check unique barcode
        with get_connection() as conn:
            existing = conn.execute("SELECT item_id FROM items WHERE barcode = ?", (barcode.strip(),)).fetchone()
            if existing:
                raise ValueError("Barcode already exists")
    if vat_rate < 0 or vat_rate > 100:
        raise ValueError("VAT rate must be between 0 and 100")
    
    with get_connection() as conn:
        if category:
            conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (category,))
        
        # Default to 1 for non-volume items unless explicitly provided
        unit_size = unit_size_ml or 1
        multiplier = _get_unit_multiplier(unit_of_measure)
        
        # Calculate per-unit prices (for fractional sales)
        total_units = unit_size * multiplier
        selling_price_per_unit = selling_price / total_units if total_units > 0 else None
        cost_price_per_unit = cost_price / total_units if total_units > 0 else None
        
        # Keep price_per_ml for backward compatibility
        ppm = price_per_ml if price_per_ml is not None else selling_price_per_unit
        
        conn.execute(
            """
            INSERT INTO items (name, category, cost_price, selling_price, quantity, image_path, barcode, vat_rate, low_stock_threshold, unit_of_measure, is_special_volume, unit_size_ml, price_per_ml, cost_price_per_unit, unit_multiplier, selling_price_per_unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, cost_price, selling_price, quantity, image_path, barcode, vat_rate, low_stock_threshold, unit_of_measure, is_special_volume, unit_size, ppm, cost_price_per_unit, multiplier, selling_price_per_unit),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM items WHERE rowid = last_insert_rowid();").fetchone()
    return _row_to_dict(row)


def update_item(item_id: int, **fields) -> Optional[dict]:
    if not fields:
        return get_item(item_id)

    allowed = {"name", "category", "cost_price", "selling_price", "quantity", "image_path", "barcode", "vat_rate", "low_stock_threshold", "unit_of_measure", "is_special_volume", "unit_size_ml", "price_per_ml", "cost_price_per_unit", "unit_multiplier", "selling_price_per_unit"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_item(item_id)

    # Validation
    if "name" in updates and (not updates["name"] or not updates["name"].strip()):
        raise ValueError("Item name is required")
    if "cost_price" in updates and updates["cost_price"] < 0:
        raise ValueError("Cost price cannot be negative")
    if "selling_price" in updates and updates["selling_price"] < 0:
        raise ValueError("Selling price cannot be negative")
    if "quantity" in updates and updates["quantity"] < 0:
        raise ValueError("Quantity cannot be negative")
    if "vat_rate" in updates and (updates["vat_rate"] < 0 or updates["vat_rate"] > 100):
        raise ValueError("VAT rate must be between 0 and 100")
    # Check barcode uniqueness if updating barcode
    if "barcode" in updates and updates["barcode"] and len(updates["barcode"].strip()) > 0:
        with get_connection() as conn:
            existing = conn.execute("SELECT item_id FROM items WHERE barcode = ? AND item_id != ?", (updates["barcode"].strip(), item_id)).fetchone()
            if existing:
                raise ValueError("Barcode already exists")
    # Check selling price >= cost price if both are being updated
    if "selling_price" in updates and "cost_price" in updates and updates["selling_price"] < updates["cost_price"]:
        raise ValueError("Selling price cannot be less than cost price")

    with get_connection() as conn:
        if "category" in updates and updates["category"]:
            conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (updates["category"],))
        
        # Get current item to merge values for recalculation
        conn.row_factory = sqlite3.Row
        current = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
        if not current:
            return None
        
        # Determine values for per-unit price calculation
        unit_of_measure = updates.get("unit_of_measure", current["unit_of_measure"])
        unit_size = updates.get("unit_size_ml", current["unit_size_ml"]) or 1
        selling_price = updates.get("selling_price", current["selling_price"])
        cost_price = updates.get("cost_price", current["cost_price"])
        
        # Auto-calculate multiplier and per-unit prices
        multiplier = _get_unit_multiplier(unit_of_measure)
        total_units = unit_size * multiplier
        
        if total_units > 0:
            updates["unit_multiplier"] = multiplier
            updates["selling_price_per_unit"] = selling_price / total_units
            updates["cost_price_per_unit"] = cost_price / total_units
            # Keep price_per_ml for backward compatibility
            updates["price_per_ml"] = updates["selling_price_per_unit"]
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        params = list(updates.values()) + [item_id]
        
        conn.execute(f"UPDATE items SET {set_clause} WHERE item_id = ?", params)
        conn.commit()
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
    """Get items with low stock. For fractional items, considers actual volume."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        # Get all items and filter based on their type
        cursor = conn.execute("SELECT * FROM items ORDER BY quantity ASC")
        low_items = []
        for row in cursor.fetchall():
            item = _row_to_dict(row)
            item_threshold = item.get("low_stock_threshold") or threshold
            if item.get("is_special_volume"):
                # For fractional items, check actual volume (qty * unit_size)
                unit_size = float(item.get("unit_size_ml") or 1)
                actual_volume = item["quantity"] * unit_size
                if actual_volume <= item_threshold:
                    low_items.append(item)
            else:
                # For regular items, just check quantity
                if item["quantity"] <= item_threshold:
                    low_items.append(item)
        return low_items


def get_categories() -> List[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM inventory_categories ORDER BY name").fetchall()
        if not rows:
            rows = conn.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND TRIM(category) != '' ORDER BY category").fetchall()
            for (cat,) in rows:
                conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (cat,))
            conn.commit()
        # Ensure fallback
        conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", ("Uncategorized",))
        conn.commit()
    return [r[0] for r in rows]


def add_category(name: str) -> dict:
    clean = (name or "").strip()
    if not clean:
        raise ValueError("Category name is required")
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (clean,))
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM inventory_categories WHERE name = ?", (clean,)).fetchone()
    return _row_to_dict(row) if row else {"name": clean}


def rename_category(old_name: str, new_name: str) -> dict:
    old_clean = (old_name or "").strip()
    new_clean = (new_name or "").strip()
    if not old_clean or not new_clean:
        raise ValueError("Both old and new category names are required")
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (new_clean,))
        conn.execute("UPDATE inventory_categories SET name = ? WHERE name = ?", (new_clean, old_clean))
        conn.execute("UPDATE items SET category = ? WHERE category = ?", (new_clean, old_clean))
        conn.commit()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM inventory_categories WHERE name = ?", (new_clean,)).fetchone()
    return _row_to_dict(row) if row else {"name": new_clean}


def delete_category(name: str, *, reassign_to: str = "Uncategorized") -> None:
    target = (name or "").strip()
    fallback = (reassign_to or "Uncategorized").strip()
    if not target:
        raise ValueError("Category name is required")
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (fallback,))
        conn.execute("UPDATE items SET category = ? WHERE category = ?", (fallback, target))
        conn.execute("DELETE FROM inventory_categories WHERE name = ?", (target,))
        conn.commit()

def add_stock(item_id: int, quantity: int) -> Optional[dict]:
    """Add quantity to an item's stock (used for refunds/returns)."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Check if item exists
        item = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
        if not item:
            return None
        
        # Update quantity
        conn.execute("UPDATE items SET quantity = quantity + ? WHERE item_id = ?", (quantity, item_id))
        conn.commit()
        
        # Return updated item
        return get_item(item_id)