"""Item portions module for preset fractional quantities.

Portions allow defining preset amounts for measurable items (sold by weight, volume, or length).
The portion_ml field stores the amount in the smallest unit (ml, g, or cm) regardless of item type.
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from database.init_db import get_connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_unit_info(item_id: int) -> dict:
    """Get unit information for an item to determine portion units.
    
    Returns dict with:
        - small_unit: The smallest unit (ml, g, cm)
        - base_unit: The base unit (L, kg, m)
        - multiplier: Conversion factor from base to small unit
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT unit_of_measure FROM items WHERE item_id = ?", (item_id,)).fetchone()
        if not row:
            return {"small_unit": "ml", "base_unit": "L", "multiplier": 1000}
        
        return get_unit_info_from_name(row["unit_of_measure"])


def get_unit_info_from_name(unit_name: str) -> dict:
    """Get unit information from a unit name string.
    
    Returns dict with:
        - small_unit: The smallest unit (ml, g, cm)
        - base_unit: The base unit (L, kg, m)
        - multiplier: Conversion factor from base to small unit
    """
    unit = (unit_name or "").lower()
    
    # Volume units - metric
    if unit in ("liters", "litre", "liter", "litres", "l"):
        return {"small_unit": "ml", "base_unit": "L", "multiplier": 1000}
    elif unit in ("ml", "milliliter", "milliliters", "millilitres"):
        return {"small_unit": "ml", "base_unit": "ml", "multiplier": 1}
    # Weight units - metric
    elif unit in ("kilograms", "kilogram", "kg", "kgs"):
        return {"small_unit": "g", "base_unit": "kg", "multiplier": 1000}
    elif unit in ("g", "gram", "grams"):
        return {"small_unit": "g", "base_unit": "g", "multiplier": 1}
    # Length units - metric
    elif unit in ("meters", "meter", "metre", "metres", "m"):
        return {"small_unit": "cm", "base_unit": "m", "multiplier": 100}
    elif unit in ("cm", "centimeter", "centimeters", "centimetres"):
        return {"small_unit": "cm", "base_unit": "cm", "multiplier": 1}
    # Pounds
    elif unit in ("lb", "lbs", "pound", "pounds"):
        return {"small_unit": "oz", "base_unit": "lb", "multiplier": 16}
    # Ounces
    elif unit in ("oz", "ounce", "ounces"):
        return {"small_unit": "oz", "base_unit": "oz", "multiplier": 1}
    # Gallons
    elif unit in ("gallon", "gallons", "gal"):
        return {"small_unit": "fl oz", "base_unit": "gal", "multiplier": 128}
    # Quart
    elif unit in ("quart", "quarts", "qt"):
        return {"small_unit": "fl oz", "base_unit": "qt", "multiplier": 32}
    # Pint
    elif unit in ("pint", "pints", "pt"):
        return {"small_unit": "fl oz", "base_unit": "pt", "multiplier": 16}
    # Yard
    elif unit in ("yard", "yards", "yd"):
        return {"small_unit": "in", "base_unit": "yd", "multiplier": 36}
    # Foot
    elif unit in ("foot", "feet", "ft"):
        return {"small_unit": "in", "base_unit": "ft", "multiplier": 12}
    # Inch
    elif unit in ("inch", "inches", "in"):
        return {"small_unit": "in", "base_unit": "in", "multiplier": 1}
    else:
        # Default for unknown units
        return {"small_unit": unit, "base_unit": unit, "multiplier": 1}


def create_portion(
    item_id: int,
    portion_name: str,
    portion_amount: float,
    selling_price: float,
    cost_price: float = 0,
    sort_order: int = 0,
    lot_id: Optional[int] = None,
) -> dict:
    """Create a new preset portion for an item.
    
    Args:
        item_id: The item this portion belongs to
        portion_name: Display name (e.g., "1/4 L", "500g", "50cm")
        portion_amount: Amount in smallest unit (ml, g, or cm)
        selling_price: Selling price for this portion
        cost_price: Cost price for this portion
        sort_order: Display order
        lot_id: Optional lot ID to base pricing on
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """INSERT INTO item_portions 
               (item_id, portion_name, portion_ml, selling_price, cost_price, sort_order, lot_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (item_id, portion_name, portion_amount, selling_price, cost_price, sort_order, lot_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM item_portions WHERE rowid = last_insert_rowid()"
        ).fetchone()
        result = _row_to_dict(row)
        # Add alias for clarity
        result["portion_amount"] = result["portion_ml"]
        return result


def update_portion(portion_id: int, **fields) -> Optional[dict]:
    """Update an existing portion.
    
    Accepts either portion_ml or portion_amount as the amount field.
    """
    if not fields:
        return get_portion(portion_id)
    
    # Map portion_amount to portion_ml for DB compatibility
    if "portion_amount" in fields:
        fields["portion_ml"] = fields.pop("portion_amount")
    
    allowed = {"portion_name", "portion_ml", "selling_price", "cost_price", "is_active", "sort_order", "lot_id"}
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
        if row:
            result = _row_to_dict(row)
            result["portion_amount"] = result["portion_ml"]
            return result
        return None


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
        if row:
            result = _row_to_dict(row)
            result["portion_amount"] = result["portion_ml"]  # Alias for clarity
            return result
        return None


def list_portions(item_id: int, active_only: bool = True) -> List[dict]:
    """List all portions for an item.
    
    Returns list of dicts with portion_amount as alias for portion_ml.
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM item_portions WHERE item_id = ?"
        params = [item_id]
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY sort_order, portion_ml"
        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            r = _row_to_dict(row)
            r["portion_amount"] = r["portion_ml"]  # Alias for clarity
            results.append(r)
        return results


def has_portions(item_id: int) -> bool:
    """Check if an item has any active preset portions."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM item_portions WHERE item_id = ? AND is_active = 1",
            (item_id,)
        ).fetchone()
        return row[0] > 0 if row else False


def create_default_portions(item_id: int, price_per_base: float = 0, cost_per_base: float = 0, unit_of_measure: str = None, lot_id: Optional[int] = None) -> List[dict]:
    """Create default preset portions for an item based on its unit of measure.
    
    Args:
        item_id: The item ID
        price_per_base: Price per base unit (L, kg, m). If 0, will try to get from item.
        cost_per_base: Cost per base unit. If 0, will try to get from item.
        unit_of_measure: Override the unit of measure (use this instead of fetching from DB).
        lot_id: Optional lot ID to associate with the created portions.
    
    Creates appropriate portions based on item's unit of measure:
        - Liters: 1/4L, 1/2L, 3/4L, 1L
        - Kilograms: 250g, 500g, 750g, 1kg
        - Meters: 25cm, 50cm, 75cm, 1m
    """
    # Get unit info - use provided unit or fetch from database
    if unit_of_measure:
        unit_info = get_unit_info_from_name(unit_of_measure)
    else:
        unit_info = get_unit_info(item_id)
    
    small_unit = unit_info["small_unit"]
    base_unit = unit_info["base_unit"]
    multiplier = unit_info["multiplier"]
    
    # Try to get price from item if not provided
    if price_per_base == 0:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT selling_price, cost_price, unit_of_measure FROM items WHERE item_id = ?", (item_id,)).fetchone()
            if row:
                price_per_base = float(row["selling_price"] or 0)
                cost_per_base = float(row["cost_price"] or 0)
    
    # Define portions based on unit type
    if small_unit == "ml":
        # Liquid portions
        if base_unit != small_unit:
            # Base unit is different (e.g., L), create fractional portions
            portions = [
                {"name": f"1/4 {base_unit} (250{small_unit})", "amount": 250, "factor": 0.25},
                {"name": f"1/2 {base_unit} (500{small_unit})", "amount": 500, "factor": 0.5},
                {"name": f"3/4 {base_unit} (750{small_unit})", "amount": 750, "factor": 0.75},
                {"name": f"1 {base_unit} (1000{small_unit})", "amount": 1000, "factor": 1.0},
            ]
        else:
            # Base unit is same as small unit (e.g., ml), create absolute portions
            portions = [
                {"name": f"250{small_unit}", "amount": 250, "factor": 0.25},
                {"name": f"500{small_unit}", "amount": 500, "factor": 0.5},
                {"name": f"750{small_unit}", "amount": 750, "factor": 0.75},
                {"name": f"1000{small_unit}", "amount": 1000, "factor": 1.0},
            ]
    elif small_unit == "g":
        # Weight portions
        if base_unit != small_unit:
            # Base unit is different (e.g., kg), create fractional portions
            portions = [
                {"name": f"250{small_unit}", "amount": 250, "factor": 0.25},
                {"name": f"500{small_unit}", "amount": 500, "factor": 0.5},
                {"name": f"750{small_unit}", "amount": 750, "factor": 0.75},
                {"name": f"1{base_unit} (1000{small_unit})", "amount": 1000, "factor": 1.0},
            ]
        else:
            # Base unit is same as small unit (e.g., g), create absolute portions
            portions = [
                {"name": f"250{small_unit}", "amount": 250, "factor": 0.25},
                {"name": f"500{small_unit}", "amount": 500, "factor": 0.5},
                {"name": f"750{small_unit}", "amount": 750, "factor": 0.75},
                {"name": f"1000{small_unit}", "amount": 1000, "factor": 1.0},
            ]
    elif small_unit == "cm":
        # Length portions
        if base_unit != small_unit:
            # Base unit is different (e.g., m), create fractional portions
            portions = [
                {"name": f"25{small_unit}", "amount": 25, "factor": 0.25},
                {"name": f"50{small_unit}", "amount": 50, "factor": 0.5},
                {"name": f"75{small_unit}", "amount": 75, "factor": 0.75},
                {"name": f"1{base_unit} (100{small_unit})", "amount": 100, "factor": 1.0},
            ]
        else:
            # Base unit is same as small unit (e.g., cm), create absolute portions
            portions = [
                {"name": f"25{small_unit}", "amount": 25, "factor": 0.25},
                {"name": f"50{small_unit}", "amount": 50, "factor": 0.5},
                {"name": f"75{small_unit}", "amount": 75, "factor": 0.75},
                {"name": f"100{small_unit}", "amount": 100, "factor": 1.0},
            ]
    elif small_unit == "oz":
        # Weight portions (imperial)
        if base_unit == "oz":
            # Base unit is ounces
            portions = [
                {"name": "4oz", "amount": 4, "factor": 0.25},
                {"name": "8oz", "amount": 8, "factor": 0.5},
                {"name": "12oz", "amount": 12, "factor": 0.75},
                {"name": "16oz", "amount": 16, "factor": 1.0},
            ]
        else:
            # Base unit is pounds
            portions = [
                {"name": "4oz", "amount": 4, "factor": 0.25},
                {"name": "8oz (1/2 lb)", "amount": 8, "factor": 0.5},
                {"name": "12oz (3/4 lb)", "amount": 12, "factor": 0.75},
                {"name": "1lb (16oz)", "amount": 16, "factor": 1.0},
            ]
    elif small_unit == "fl oz":
        # Volume portions (imperial fluid ounces)
        if base_unit == "fl oz":
            # Base unit is fluid ounces
            portions = [
                {"name": "8fl oz", "amount": 8, "factor": 0.25},
                {"name": "16fl oz", "amount": 16, "factor": 0.5},
                {"name": "24fl oz", "amount": 24, "factor": 0.75},
                {"name": "32fl oz", "amount": 32, "factor": 1.0},
            ]
        elif base_unit == "pt":
            # Base unit is pint (16 fl oz)
            portions = [
                {"name": "4fl oz", "amount": 4, "factor": 0.25},
                {"name": "8fl oz (1/2 pt)", "amount": 8, "factor": 0.5},
                {"name": "12fl oz (3/4 pt)", "amount": 12, "factor": 0.75},
                {"name": "1pt (16fl oz)", "amount": 16, "factor": 1.0},
            ]
        elif base_unit == "qt":
            # Base unit is quart (32 fl oz)
            portions = [
                {"name": "8fl oz", "amount": 8, "factor": 0.25},
                {"name": "16fl oz (1/2 qt)", "amount": 16, "factor": 0.5},
                {"name": "24fl oz (3/4 qt)", "amount": 24, "factor": 0.75},
                {"name": "1qt (32fl oz)", "amount": 32, "factor": 1.0},
            ]
        else:
            # Base unit is gallon (128 fl oz)
            portions = [
                {"name": "1 quart (32 fl oz)", "amount": 32, "factor": 0.25},
                {"name": "1/2 gal (64 fl oz)", "amount": 64, "factor": 0.5},
                {"name": "3 quarts (96 fl oz)", "amount": 96, "factor": 0.75},
                {"name": "1 gallon (128fl oz)", "amount": 128, "factor": 1.0},
            ]
    elif small_unit == "in":
        # Length portions (imperial)
        if base_unit == "in":
            # Base unit is inches
            portions = [
                {"name": "3in", "amount": 3, "factor": 0.25},
                {"name": "6in", "amount": 6, "factor": 0.5},
                {"name": "9in", "amount": 9, "factor": 0.75},
                {"name": "12in (1ft)", "amount": 12, "factor": 1.0},
            ]
        elif base_unit == "ft":
            # Base unit is feet (12 inches)
            portions = [
                {"name": "3in", "amount": 3, "factor": 0.25},
                {"name": "6in (1/2 ft)", "amount": 6, "factor": 0.5},
                {"name": "9in (3/4 ft)", "amount": 9, "factor": 0.75},
                {"name": "1ft (12in)", "amount": 12, "factor": 1.0},
            ]
        else:
            # Base unit is yard (36 inches)
            portions = [
                {"name": "9in (1/4 yd)", "amount": 9, "factor": 0.25},
                {"name": "18in (1/2 yd)", "amount": 18, "factor": 0.5},
                {"name": "27in (3/4 yd)", "amount": 27, "factor": 0.75},
                {"name": "1yd (36in)", "amount": 36, "factor": 1.0},
            ]
    else:
        # Generic portions
        portions = [
            {"name": f"0.25 {base_unit}", "amount": multiplier * 0.25, "factor": 0.25},
            {"name": f"0.5 {base_unit}", "amount": multiplier * 0.5, "factor": 0.5},
            {"name": f"0.75 {base_unit}", "amount": multiplier * 0.75, "factor": 0.75},
            {"name": f"1 {base_unit}", "amount": multiplier, "factor": 1.0},
        ]
    
    created = []
    for i, p in enumerate(portions):
        try:
            portion = create_portion(
                item_id=item_id,
                portion_name=p["name"],
                portion_amount=p["amount"],
                selling_price=round(price_per_base * p["factor"], 2),
                cost_price=round(cost_per_base * p["factor"], 2) if cost_per_base else 0,
                sort_order=i,
                lot_id=lot_id,
            )
            created.append(portion)
        except sqlite3.IntegrityError:
            # Portion already exists
            pass
    return created
