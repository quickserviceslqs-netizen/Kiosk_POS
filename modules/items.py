"""Inventory data access helpers."""
from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional
from functools import lru_cache

from database.init_db import get_connection
from utils.validation import sanitize_string, validate_numeric, validate_integer, validate_barcode, validate_path, ValidationError, validate_item_name, validate_item_category, validate_item_barcode, validate_item_price, validate_item_cost, validate_item_quantity, validate_item_vat_rate, validate_item_low_stock_threshold, validate_item_unit_of_measure, validate_item_package_size
from utils.audit import audit_logger
from utils.performance import profile_function
from modules import reports, variants


# Cache for unit conversions to improve performance
@lru_cache(maxsize=128)
def _get_cached_unit_multiplier(unit_of_measure: str) -> float:
    """Cached version of unit multiplier lookup."""
    return _get_unit_multiplier(unit_of_measure)


@lru_cache(maxsize=128) 
def _get_cached_default_unit_size(unit_of_measure: str) -> int:
    """Cached version of default unit size lookup."""
    unit_lower = unit_of_measure.lower()
    if unit_lower in ("liters", "litre", "liter", "litres", "l", "kilograms", "kilogram", "kg", "kgs"):
        return 1000
    elif unit_lower in ("meters", "meter", "metre", "metres", "m"):
        return 100
    else:
        return 1


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


def _normalize_prices(cost_price: float, selling_price: float, unit_size: int, multiplier: float) -> dict:
    """Normalize and calculate all price fields from bulk prices.
    
    Returns a dict with all price fields calculated consistently.
    """
    total_units = unit_size * multiplier
    
    if total_units <= 0:
        return {
            "cost_price": cost_price,
            "selling_price": selling_price,
            "cost_price_per_unit": None,
            "selling_price_per_unit": None,
            "price_per_ml": None,
            "unit_multiplier": multiplier,
        }
    
    cost_price_per_unit = cost_price / total_units
    selling_price_per_unit = selling_price / total_units
    
    return {
        "cost_price": cost_price,
        "selling_price": selling_price,
        "cost_price_per_unit": cost_price_per_unit,
        "selling_price_per_unit": selling_price_per_unit,
        "price_per_ml": selling_price_per_unit,  # For backward compatibility
        "unit_multiplier": multiplier,
    }


@profile_function
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
    has_variants: int = 0,
    is_catalog_only: int | None = None,
) -> dict:
    """Create a new inventory item.

    This function creates a new item in the inventory system with comprehensive validation
    and automatic price calculations for different item types.

    Args:
        name: Item name (required, max 100 characters)
        category: Item category (optional, max 50 characters)
        cost_price: Purchase cost per unit (default: 0.0)
        selling_price: Selling price as displayed (default: 0.0)
        quantity: Current stock quantity (default: 0)
        image_path: Path to item image file (optional)
        barcode: Unique barcode for the item (optional, max 50 characters)
        vat_rate: VAT rate as percentage (default: 16.0, range: 0-100)
        low_stock_threshold: Alert threshold for low stock (default: 10, range: 0-10000)
        unit_of_measure: Unit type (pieces, liters, kilograms, etc.) (default: "pieces")
        is_special_volume: Whether item supports fractional quantities (0 or 1) (default: 0)
        unit_size_ml: Size of one package/unit in base units (optional)
        price_per_ml: Legacy price per ml field (optional, for backward compatibility)

    Returns:
        dict: Created item data including calculated fields like price_per_ml, unit_multiplier, etc.

    Raises:
        ValueError: If validation fails or business rules are violated (e.g., selling price < cost price)

    Examples:
        # Create a simple item
        item = create_item(name="Apple", selling_price=2.50, quantity=100)

        # Create a bulk item with fractional support
        item = create_item(
            name="Milk",
            category="Dairy",
            selling_price=5.00,
            cost_price=3.50,
            quantity=50,
            unit_of_measure="liters",
            unit_size_ml=1000,
            is_special_volume=1
        )
    """
    # Input validation and sanitization
    try:
        name = validate_item_name(name)
        category = validate_item_category(category)
    
        cost_price = validate_item_cost(cost_price)
        selling_price = validate_item_price(selling_price)
        quantity = validate_item_quantity(quantity)
        vat_rate = validate_item_vat_rate(vat_rate)
        low_stock_threshold = validate_item_low_stock_threshold(low_stock_threshold)

        barcode = validate_item_barcode(barcode)
        image_path = validate_path(image_path) if image_path else None
        unit_of_measure = validate_item_unit_of_measure(unit_of_measure)

        # Normalize has_variants input (allow bool or int)
        has_variants = 1 if bool(has_variants) else 0

        if unit_size_ml is not None:
            unit_size_ml = validate_item_package_size(unit_size_ml)
        else:
            unit_size_ml = _get_cached_default_unit_size(unit_of_measure)

    except ValidationError as e:
        raise ValueError(f"Validation error: {e}")

    # Business logic validation
    if selling_price < cost_price:
        raise ValueError("Selling price cannot be less than cost price")
    if cost_price > 0 and selling_price > cost_price * 10:  # Reasonable markup check only when cost_price > 0
        raise ValueError("Selling price cannot be more than 10x cost price")

    # Check unique barcode
    if barcode:
        with get_connection() as conn:
            existing = conn.execute("SELECT item_id FROM items WHERE barcode = ?", (barcode,)).fetchone()
            if existing:
                raise ValueError("Barcode already exists")
    
    if image_path and len(image_path.strip()) > 255:
        raise ValueError("Image path cannot exceed 255 characters")
    
    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            # Sanitize inputs
            name = name.strip()
            category = category.strip() if category else None
            barcode = barcode.strip() if barcode else None
            unit_of_measure = unit_of_measure.strip() if unit_of_measure else "pieces"
            image_path = image_path.strip() if image_path else None
            
            # Insert category if provided (atomic with item creation)
            if category:
                conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (category,))
            
            # Default to appropriate size for unit type if not specified
            if unit_size_ml is None:
                unit_size_ml = _get_cached_default_unit_size(unit_of_measure)
            unit_size = unit_size_ml
            
            multiplier = _get_cached_unit_multiplier(unit_of_measure)
            
            # Calculate normalized prices
            price_data = _normalize_prices(cost_price, selling_price, unit_size, multiplier)
            
            # Decide default for catalog-only: if not explicitly specified, default to has_variants
            if is_catalog_only is None:
                is_catalog_only = 1 if bool(has_variants) else 0
            else:
                is_catalog_only = 1 if bool(is_catalog_only) else 0

            conn.execute(
                """
                INSERT INTO items (name, category, cost_price, selling_price, quantity, image_path, barcode, vat_rate, low_stock_threshold, unit_of_measure, is_special_volume, unit_size_ml, price_per_ml, cost_price_per_unit, unit_multiplier, selling_price_per_unit, has_variants, is_catalog_only)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, category, price_data["cost_price"], price_data["selling_price"], quantity, image_path, barcode, vat_rate, low_stock_threshold, unit_of_measure, is_special_volume, unit_size, price_data["price_per_ml"], price_data["cost_price_per_unit"], price_data["unit_multiplier"], price_data["selling_price_per_unit"], int(bool(has_variants)), int(bool(is_catalog_only))),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM items WHERE rowid = last_insert_rowid();").fetchone()
    
    # Audit logging
    item_dict = _row_to_dict(row)
    audit_logger.log_data_change(
        "CREATE",
        "items",
        item_dict["item_id"],
        new_values=item_dict
    )
    
    # Invalidate report cache after item creation
    reports.invalidate_cache()
    
    return item_dict


@profile_function
def update_item(item_id: int, **fields) -> Optional[dict]:
    """Update an existing inventory item.

    This function updates specified fields of an existing item with validation
    and automatic recalculation of derived price fields.

    Args:
        item_id: The ID of the item to update
        **fields: Keyword arguments for fields to update. Valid fields include:
            - name: Item name (max 100 characters)
            - category: Item category (max 50 characters)
            - cost_price: Purchase cost per unit
            - selling_price: Selling price
            - quantity: Current stock quantity
            - image_path: Path to item image
            - barcode: Unique barcode (must not conflict with existing items)
            - vat_rate: VAT rate as percentage (0-100)
            - low_stock_threshold: Low stock alert threshold (0-10000)
            - unit_of_measure: Unit type
            - is_special_volume: Fractional quantity support flag
            - unit_size_ml: Package size in base units
            - price_per_ml: Price per ml (calculated automatically)
            - cost_price_per_unit: Cost per unit (calculated automatically)
            - unit_multiplier: Unit conversion multiplier (calculated automatically)
            - selling_price_per_unit: Selling price per unit (calculated automatically)

    Returns:
        dict: Updated item data, or None if item doesn't exist

    Raises:
        ValueError: If validation fails or business rules are violated

    Examples:
        # Update item name and price
        updated = update_item(123, name="New Name", selling_price=15.99)

        # Update stock quantity
        updated = update_item(123, quantity=50)
    """

    # Prepare updates dict and fetch current record for context
    updates = dict(fields)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        current = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
        if not current:
            raise ValueError(f"Item {item_id} not found")

    # Validation
    if "name" in updates:
        updates["name"] = validate_item_name(updates["name"])
    if "has_variants" in updates:
        # Normalize boolean-like inputs
        updates["has_variants"] = 1 if bool(updates["has_variants"]) else 0
    if "category" in updates:
        updates["category"] = validate_item_category(updates["category"])
    if "cost_price" in updates:
        updates["cost_price"] = validate_item_cost(updates["cost_price"])
    if "selling_price" in updates:
        updates["selling_price"] = validate_item_price(updates["selling_price"])
    if "quantity" in updates:
        updates["quantity"] = validate_item_quantity(updates["quantity"])
    if "vat_rate" in updates:
        updates["vat_rate"] = validate_item_vat_rate(updates["vat_rate"])
    if "low_stock_threshold" in updates:
        updates["low_stock_threshold"] = validate_item_low_stock_threshold(updates["low_stock_threshold"])
    if "unit_of_measure" in updates:
        updates["unit_of_measure"] = validate_item_unit_of_measure(updates["unit_of_measure"])
    if "unit_size_ml" in updates and updates["unit_size_ml"] is not None:
        updates["unit_size_ml"] = validate_item_package_size(updates["unit_size_ml"])
    if "barcode" in updates:
        updates["barcode"] = validate_item_barcode(updates["barcode"])
    if "image_path" in updates and updates["image_path"]:
        updates["image_path"] = validate_path(updates["image_path"])
    
    # Check barcode uniqueness if updating barcode
    if "barcode" in updates and updates["barcode"] and len(updates["barcode"].strip()) > 0:
        with get_connection() as conn:
            existing = conn.execute("SELECT item_id FROM items WHERE barcode = ? AND item_id != ?", (updates["barcode"].strip(), item_id)).fetchone()
            if existing:
                raise ValueError("Barcode already exists")
    
    # Check selling price >= cost price if both are being updated
    if ("selling_price" in updates or "cost_price" in updates):
        current_cost = current["cost_price"]
        current_sell = current["selling_price"]
        new_cost = updates.get("cost_price", current_cost)
        new_sell = updates.get("selling_price", current_sell)
        if new_sell < new_cost:
            raise ValueError("Selling price cannot be less than cost price")
        if new_sell > new_cost * 10:  # Reasonable markup check
            raise ValueError("Selling price cannot be more than 10x cost price")

    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            # Insert category if provided (atomic with item update)
            if "category" in updates and updates["category"]:
                conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (updates["category"],))
            
            # Get current item to merge values for recalculation
            conn.row_factory = sqlite3.Row
            current = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
            if not current:
                raise ValueError(f"Item {item_id} not found")
            
            # Store old values for audit logging
            old_values = _row_to_dict(current)
            
            # Determine values for per-unit price calculation
            unit_of_measure = updates.get("unit_of_measure", current["unit_of_measure"])
            unit_size = updates.get("unit_size_ml", current["unit_size_ml"]) or 1
            selling_price = updates.get("selling_price", current["selling_price"])
            cost_price = updates.get("cost_price", current["cost_price"])
            
            # Auto-calculate multiplier and per-unit prices
            multiplier = _get_cached_unit_multiplier(unit_of_measure)
            total_units = unit_size * multiplier
            
            if total_units > 0:
                # Use normalized price calculation
                price_data = _normalize_prices(cost_price, selling_price, unit_size, multiplier)
                updates.update(price_data)
            
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            params = list(updates.values()) + [item_id]
            
            conn.execute(f"UPDATE items SET {set_clause} WHERE item_id = ?", params)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        
        row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    # Audit logging
    if row:
        new_values = _row_to_dict(row)
        audit_logger.log_data_change(
            "UPDATE",
            "items",
            item_id,
            old_values=old_values,
            new_values=new_values
        )
    
    # Invalidate report cache after item update
    reports.invalidate_cache()
    
    return _row_to_dict(row) if row else None


def delete_item(item_id: int) -> None:
    """Delete an item from inventory.

    This permanently removes an item from the database. Use with caution.

    Args:
        item_id: The ID of the item to delete

    Examples:
        delete_item(123)  # Permanently removes item with ID 123
    """


def set_is_catalog_only(item_id: int, flag: bool) -> None:
    """Convenience wrapper to mark an item as catalog-only (not sellable directly)."""
    update_item(item_id, is_catalog_only=1 if flag else 0)


@profile_function
def get_item(item_id: int) -> Optional[dict]:
    """Retrieve a single item by ID.

    Args:
        item_id: The ID of the item to retrieve

    Returns:
        dict: Item data if found, None otherwise

    Examples:
        item = get_item(123)
        if item:
            print(f"Item: {item['name']}")
    """
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
    """Get low-stock alerts. Returns a list of alert dicts.

    - For items without variants: behaves like before (item-level alerts).
    - For items with variants: returns variant-level alerts for variants below their threshold.
      Parent-level alerts are NOT emitted for items that have variants (variant-only mode).
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM items ORDER BY quantity ASC")
        low_items: List[dict] = []
        for row in cursor.fetchall():
            item = _row_to_dict(row)
            item_threshold = item.get("low_stock_threshold") or threshold

            # If the item has variants, inspect them
            try:
                if variants.has_variants(item["item_id"]):
                    vars_list = variants.list_variants(item["item_id"])
                    variant_alerts = []
                    all_variants_low = True
                    aggregated_qty = 0
                    aggregated_volume = 0.0

                    for v in vars_list:
                        v_threshold = v.get("low_stock_threshold") or item_threshold
                        qty = int(v.get("quantity") or 0)
                        aggregated_qty += qty

                        if item.get("is_special_volume"):
                            unit_size = float(item.get("unit_size_ml") or 1)
                            actual = qty * unit_size
                            aggregated_volume += actual
                        else:
                            actual = qty

                        if actual <= v_threshold:
                            # Variant-level alert
                            alert = {
                                "type": "variant",
                                "item_id": item["item_id"],
                                "variant_id": v.get("variant_id"),
                                "name": f"{item.get('name')} — {v.get('variant_name')}",
                                "quantity": qty,
                                "actual_volume": actual,
                                "threshold": v_threshold,
                                "is_special_volume": bool(item.get("is_special_volume")),
                                "display_unit": ("L" if (item.get("unit_of_measure") or "").lower() in ("litre","liter","liters","litres","l") else ("kg" if (item.get("unit_of_measure") or "").lower() in ("kilogram","kilograms","kg","kgs") else ("m" if (item.get("unit_of_measure") or "").lower() in ("meter","meters","metre","metres","m") else "units")))
                            }
                            variant_alerts.append(alert)
                        else:
                            all_variants_low = False

                    low_items.extend(variant_alerts)

                    # Variant-only mode: for items that have variants we report variant-level alerts
                    # and do NOT emit parent-level alerts. This avoids duplicate/ambiguous alerts when
                    # variants are the actual stock carriers.
                    # (If desired in future, we can add a config flag to re-enable parent alerts.)
                else:
                    # No variants: existing behavior
                    if item.get("is_special_volume"):
                        unit_size = float(item.get("unit_size_ml") or 1)
                        actual_volume = item["quantity"] * unit_size
                        if actual_volume <= item_threshold:
                            item["actual_volume"] = actual_volume
                            item["display_unit"] = ("L" if (item.get("unit_of_measure") or "").lower() in ("litre","liter","liters","litres","l") else ("kg" if (item.get("unit_of_measure") or "").lower() in ("kilogram","kilograms","kg","kgs") else ("m" if (item.get("unit_of_measure") or "").lower() in ("meter","meters","metre","metres","m") else "units")))
                            low_items.append(item)
                    else:
                        if item["quantity"] <= item_threshold:
                            item["actual_volume"] = item["quantity"]
                            item["display_unit"] = "units"
                            low_items.append(item)
            except Exception:
                # On any unexpected error when checking variants, fall back to item-level check
                try:
                    if item.get("is_special_volume"):
                        unit_size = float(item.get("unit_size_ml") or 1)
                        actual_volume = item["quantity"] * unit_size
                        if actual_volume <= item_threshold:
                            item["actual_volume"] = actual_volume
                            item["display_unit"] = ("L" if (item.get("unit_of_measure") or "").lower() in ("litre","liter","liters","litres","l") else ("kg" if (item.get("unit_of_measure") or "").lower() in ("kilogram","kilograms","kg","kgs") else ("m" if (item.get("unit_of_measure") or "").lower() in ("meter","meters","metre","metres","m") else "units")))
                            low_items.append(item)
                    else:
                        if item["quantity"] <= item_threshold:
                            item["actual_volume"] = item["quantity"]
                            item["display_unit"] = "units"
                            low_items.append(item)
                except Exception:
                    # Give up and skip
                    continue

        return low_items


def get_categories() -> List[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM inventory_categories ORDER BY name").fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND TRIM(category) != '' ORDER BY category"
            ).fetchall()
            # rows may be tuples or dict-like depending on row_factory; handle both
            for row in rows:
                if isinstance(row, dict):
                    cat = row.get('category') or next(iter(row.values()), None)
                else:
                    try:
                        cat = row[0]
                    except Exception:
                        cat = None
                if cat:
                    conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", (cat,))
            conn.commit()
        # Ensure fallback
        conn.execute("INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)", ("Uncategorized",))
        conn.commit()

        # Normalize rows into simple list of strings
        result: list[str] = []
        for r in rows:
            if isinstance(r, dict):
                name = r.get('name') or r.get('category') or next(iter(r.values()), None)
            else:
                try:
                    name = r[0]
                except Exception:
                    name = str(r)
            if name:
                result.append(str(name))

    return result


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