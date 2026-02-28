"""Unit of Measure management module."""
from __future__ import annotations

from database.init_db import get_connection


def list_units(active_only: bool = True, category: str | None = None) -> list[dict]:
    """Return all units of measure, optionally filtered by category.
    
    Args:
        active_only: If True, return only active units.
        category: If provided, filter by category ('discrete' or 'measurable').
    """
    with get_connection() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        
        conditions = []
        params = []
        
        if active_only:
            conditions.append("is_active = 1")
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        query = "SELECT * FROM units_of_measure"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY name"
        
        rows = conn.execute(query, params).fetchall()
        return rows


def get_unit(uom_id: int) -> dict | None:
    """Get a single unit by ID."""
    with get_connection() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        return conn.execute(
            "SELECT * FROM units_of_measure WHERE uom_id = ?", (uom_id,)
        ).fetchone()


def get_unit_by_name(name: str) -> dict | None:
    """Get a single unit by name."""
    with get_connection() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        return conn.execute(
            "SELECT * FROM units_of_measure WHERE name = ?", (name,)
        ).fetchone()


def create_unit(
    name: str,
    abbreviation: str = "",
    conversion_factor: float = 1,
    base_unit: str | None = None,
    category: str = "discrete",
) -> int:
    """Create a new unit of measure.
    
    Args:
        name: Unit name (e.g., 'kilogram', 'piece')
        abbreviation: Short form (e.g., 'kg', 'pc')
        conversion_factor: Factor to convert to base unit
        base_unit: Base unit name for conversion
        category: 'discrete' for counting units, 'measurable' for weight/volume/length
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO units_of_measure (name, abbreviation, conversion_factor, base_unit, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), abbreviation.strip(), conversion_factor, base_unit, category),
        )
        conn.commit()
        return cursor.lastrowid


def update_unit(uom_id: int, **kwargs) -> None:
    """Update an existing unit of measure."""
    allowed = {"name", "abbreviation", "conversion_factor", "base_unit", "is_active", "category"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [uom_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE units_of_measure SET {set_clause} WHERE uom_id = ?", values)
        conn.commit()


def delete_unit(uom_id: int) -> None:
    """Delete a unit of measure."""
    with get_connection() as conn:
        conn.execute("DELETE FROM units_of_measure WHERE uom_id = ?", (uom_id,))
        conn.commit()


def toggle_active(uom_id: int) -> None:
    """Toggle the active status of a unit."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE units_of_measure SET is_active = 1 - is_active WHERE uom_id = ?",
            (uom_id,),
        )
        conn.commit()


def get_unit_names(active_only: bool = True) -> list[str]:
    """Return list of unit names for combobox."""
    units = list_units(active_only=active_only)
    return [u["name"] for u in units]


def get_discrete_units(active_only: bool = True) -> list[str]:
    """Return list of discrete unit names (for items sold as whole units)."""
    units = list_units(active_only=active_only, category="discrete")
    return [u["name"] for u in units]


def get_measurable_units(active_only: bool = True) -> list[str]:
    """Return list of measurable unit names (for weight/volume/length)."""
    units = list_units(active_only=active_only, category="measurable")
    return [u["name"] for u in units]


def get_conversion_factor(unit_name: str) -> float:
    """Get the conversion factor for a unit (e.g., kg -> 1000 for grams)."""
    unit = get_unit_by_name(unit_name)
    if unit:
        return unit.get("conversion_factor", 1) or 1
    # Fallback conversions
    conversions = {"L": 1000, "litre": 1000, "kg": 1000, "kilogram": 1000, "m": 100, "metre": 100}
    return conversions.get(unit_name, 1)
