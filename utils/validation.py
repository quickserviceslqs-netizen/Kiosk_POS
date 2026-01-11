"""Input validation and sanitization utilities."""
from __future__ import annotations

import re
from typing import Any, Optional


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def sanitize_string(value: Any, max_length: int = 255, allow_empty: bool = True) -> Optional[str]:
    """
    Sanitize a string value.

    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length
        allow_empty: Whether empty strings are allowed

    Returns:
        Sanitized string or None if input was None

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        return None

    # Convert to string and strip whitespace
    result = str(value).strip()

    if not allow_empty and not result:
        raise ValidationError("Value cannot be empty")

    if len(result) > max_length:
        raise ValidationError(f"Value exceeds maximum length of {max_length} characters")

    # Remove potentially dangerous characters
    result = re.sub(r'[<>\"\'&]', '', result)

    return result


def validate_numeric(value: Any, min_value: Optional[float] = None,
                    max_value: Optional[float] = None, allow_zero: bool = True) -> float:
    """
    Validate and convert to numeric value.

    Args:
        value: Input value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allow_zero: Whether zero is allowed

    Returns:
        Validated numeric value

    Raises:
        ValidationError: If validation fails
    """
    try:
        result = float(value or 0)
    except (ValueError, TypeError):
        raise ValidationError("Invalid numeric value")

    if not allow_zero and result == 0:
        raise ValidationError("Value cannot be zero")

    if min_value is not None and result < min_value:
        raise ValidationError(f"Value must be at least {min_value}")

    if max_value is not None and result > max_value:
        raise ValidationError(f"Value cannot exceed {max_value}")

    return result


def validate_integer(value: Any, min_value: Optional[int] = None,
                    max_value: Optional[int] = None, allow_zero: bool = True) -> int:
    """
    Validate and convert to integer value.

    Args:
        value: Input value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allow_zero: Whether zero is allowed

    Returns:
        Validated integer value

    Raises:
        ValidationError: If validation fails
    """
    try:
        result = int(float(value or 0))
    except (ValueError, TypeError):
        raise ValidationError("Invalid integer value")

    if not allow_zero and result == 0:
        raise ValidationError("Value cannot be zero")

    if min_value is not None and result < min_value:
        raise ValidationError(f"Value must be at least {min_value}")

    if max_value is not None and result > max_value:
        raise ValidationError(f"Value cannot exceed {max_value}")

    return result


def validate_email(email: str) -> str:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Validated email address

    Raises:
        ValidationError: If email format is invalid
    """
    email = sanitize_string(email, max_length=254, allow_empty=False)
    if not email:
        raise ValidationError("Email address is required")

    # Basic email regex validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Invalid email address format")

    return email


def validate_phone(phone: str) -> Optional[str]:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Validated phone number or None

    Raises:
        ValidationError: If phone format is invalid
    """
    if not phone:
        return None

    phone = sanitize_string(phone, max_length=20, allow_empty=False)
    if not phone:
        return None

    # Remove all non-digit characters except + for international codes
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Basic validation: should start with + or digit, and have reasonable length
    if not (cleaned.startswith('+') or cleaned[0].isdigit()):
        raise ValidationError("Invalid phone number format")

    if len(cleaned) < 7 or len(cleaned) > 15:
        raise ValidationError("Phone number length is invalid")

    return cleaned


def validate_barcode(barcode: str) -> Optional[str]:
    """
    Validate barcode format.

    Args:
        barcode: Barcode to validate

    Returns:
        Validated barcode or None

    Raises:
        ValidationError: If barcode format is invalid
    """
    if not barcode:
        return None

    barcode = sanitize_string(barcode, max_length=50, allow_empty=False)
    if not barcode:
        return None

    # Basic validation: should contain only alphanumeric characters and some special chars
    if not re.match(r'^[a-zA-Z0-9\-_\.]+$', barcode):
        raise ValidationError("Barcode contains invalid characters")

    return barcode


def validate_path(path: str, must_exist: bool = False) -> Optional[str]:
    """
    Validate file path.

    Args:
        path: File path to validate
        must_exist: Whether the file must exist

    Returns:
        Validated path or None

    Raises:
        ValidationError: If path is invalid
    """
    if not path:
        return None

    path = sanitize_string(path, max_length=500, allow_empty=False)
    if not path:
        return None

    # Basic path validation - prevent directory traversal
    if '..' in path or path.startswith('/'):
        raise ValidationError("Invalid path format")

    if must_exist:
        from pathlib import Path
        if not Path(path).exists():
            raise ValidationError("File does not exist")

    return path


# Item-specific validation functions

def validate_item_name(name: str) -> str:
    """
    Validate item name.

    Args:
        name: Item name to validate

    Returns:
        Validated item name

    Raises:
        ValidationError: If validation fails
    """
    return sanitize_string(name, max_length=100, allow_empty=False)


def validate_item_category(category: str) -> Optional[str]:
    """
    Validate item category.

    Args:
        category: Item category to validate

    Returns:
        Validated category or None

    Raises:
        ValidationError: If validation fails
    """
    if not category:
        return None
    return sanitize_string(category, max_length=50, allow_empty=True)


def validate_item_barcode(barcode: str) -> Optional[str]:
    """
    Validate item barcode.

    Args:
        barcode: Barcode to validate

    Returns:
        Validated barcode or None

    Raises:
        ValidationError: If validation fails
    """
    return validate_barcode(barcode)


def validate_item_price(price: Any) -> float:
    """
    Validate item price.

    Args:
        price: Price to validate

    Returns:
        Validated price

    Raises:
        ValidationError: If validation fails
    """
    return validate_numeric(price, min_value=0, max_value=999999.99)


def validate_item_cost(cost: Any) -> float:
    """
    Validate item cost.

    Args:
        cost: Cost to validate

    Returns:
        Validated cost

    Raises:
        ValidationError: If validation fails
    """
    return validate_numeric(cost, min_value=0, max_value=999999.99)


def validate_item_quantity(quantity: Any) -> float:
    """
    Validate item quantity.

    Args:
        quantity: Quantity to validate

    Returns:
        Validated quantity

    Raises:
        ValidationError: If validation fails
    """
    return validate_numeric(quantity, min_value=0, max_value=999999.99)


def validate_item_vat_rate(vat_rate: Any) -> float:
    """
    Validate VAT rate.

    Args:
        vat_rate: VAT rate to validate

    Returns:
        Validated VAT rate

    Raises:
        ValidationError: If validation fails
    """
    return validate_numeric(vat_rate, min_value=0, max_value=100)


def validate_item_low_stock_threshold(threshold: Any) -> int:
    """
    Validate low stock threshold.

    Args:
        threshold: Threshold to validate

    Returns:
        Validated threshold

    Raises:
        ValidationError: If validation fails
    """
    return validate_integer(threshold, min_value=0, max_value=10000)


def validate_item_unit_of_measure(unit: str) -> str:
    """
    Validate unit of measure.

    Args:
        unit: Unit to validate

    Returns:
        Validated unit

    Raises:
        ValidationError: If validation fails
    """
    valid_units = ["pieces", "liters", "kilograms", "meters", "grams", "milliliters"]
    unit = sanitize_string(unit, max_length=20, allow_empty=False)
    if unit not in valid_units:
        raise ValidationError(f"Invalid unit of measure. Must be one of: {', '.join(valid_units)}")
    return unit


def validate_item_package_size(size: Any) -> int:
    """
    Validate package size.

    Args:
        size: Package size to validate

    Returns:
        Validated package size

    Raises:
        ValidationError: If validation fails
    """
    return validate_integer(size, min_value=1, max_value=1000000)