"""
Quantity display utilities for consistent stock level formatting across the application.

This module provides standardized functions for displaying item quantities,
handling special volume conversions, unit formatting, and variant aggregation.
"""

from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def format_item_quantity_display(
    quantity: float,
    is_special_volume: bool,
    unit_of_measure: str,
    unit_size_ml: float,
    has_variants: bool = False,
    variant_quantities: Optional[list] = None
) -> str:
    """
    Format item quantity for display in UI components.

    This function provides consistent quantity display across POS, inventory,
    and other UI components.

    Args:
        quantity: Raw quantity from database
        is_special_volume: Whether this is a special volume item
        unit_of_measure: Unit of measure (liters, kg, etc.)
        unit_size_ml: Size of unit in base units (ml, g, cm)
        has_variants: Whether item has variants
        variant_quantities: List of variant quantities (if has_variants=True)

    Returns:
        Formatted quantity string for display
    """
    try:
        # Handle items with variants
        if has_variants and variant_quantities:
            total_qty = sum(variant_quantities)
            return f"{int(total_qty)} (variants)"

        # Handle special volume items
        if is_special_volume:
            return _format_special_volume_quantity(quantity, unit_of_measure, unit_size_ml)

        # Regular items
        return str(int(quantity))

    except Exception as e:
        logger.warning(f"Error formatting quantity {quantity}: {e}")
        return str(int(quantity))


def _format_special_volume_quantity(
    quantity: float,
    unit_of_measure: str,
    unit_size_ml: float
) -> str:
    """
    Format quantity for special volume items with unit conversions.

    Args:
        quantity: Raw quantity (number of containers/packages)
        unit_of_measure: Unit type (liters, kg, meters, etc.)
        unit_size_ml: Size per container in base units

    Returns:
        Formatted quantity string
    """
    if not unit_size_ml or unit_size_ml <= 0:
        return str(int(quantity))

    # Calculate total in base units
    total_base = quantity * unit_size_ml

    unit_lower = (unit_of_measure or "").lower()

    # Handle different unit types
    if unit_lower in ("litre", "liter", "liters", "litres", "l"):
        return _format_volume_quantity(total_base, "L", "ml")
    elif unit_lower in ("kilogram", "kilograms", "kg", "kgs"):
        return _format_weight_quantity(total_base, "kg", "g")
    elif unit_lower in ("meter", "meters", "metre", "metres", "m"):
        return _format_length_quantity(total_base, "m", "cm")
    else:
        # Unknown unit type, show container count
        return str(int(quantity))


def _format_volume_quantity(total_ml: float, large_unit: str, small_unit: str) -> str:
    """Format volume quantity with appropriate unit."""
    if total_ml >= 1000:
        return f"{total_ml / 1000:.1f} {large_unit}"
    else:
        return f"{int(total_ml)} {small_unit}"


def _format_weight_quantity(total_g: float, large_unit: str, small_unit: str) -> str:
    """Format weight quantity with appropriate unit."""
    if total_g >= 1000:
        return f"{total_g / 1000:.1f} {large_unit}"
    else:
        return f"{int(total_g)} {small_unit}"


def _format_length_quantity(total_cm: float, large_unit: str, small_unit: str) -> str:
    """Format length quantity with appropriate unit."""
    if total_cm >= 100:
        return f"{total_cm / 100:.1f} {large_unit}"
    else:
        return f"{int(total_cm)} {small_unit}"


def get_unit_display_info(unit_of_measure: str) -> Tuple[float, str, str]:
    """
    Get unit conversion information for display.

    Args:
        unit_of_measure: The unit of measure string

    Returns:
        Tuple of (conversion_factor, abbreviation, base_unit)
    """
    try:
        from modules import uom
        unit_info = uom.get_unit_by_name(unit_of_measure) or {}
        conv_factor = float(unit_info.get("conversion_factor", 1) or 1)
        abbr = unit_info.get("abbreviation") or ""
        base_unit = (unit_info.get("base_unit") or "").lower()
        return conv_factor, abbr, base_unit
    except Exception:
        # Fallback if UOM module not available
        return 1.0, "", ""