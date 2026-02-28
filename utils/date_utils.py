from datetime import datetime, date
from database.init_db import get_setting

def get_date_format() -> str:
    """Get the current date format setting, defaulting to YYYY-MM-DD."""
    fmt = get_setting('date_format')
    return fmt if fmt else '%Y-%m-%d'

def parse_date_flexible(date_str: str) -> datetime:
    """Parse a date string in any of the supported formats.

    Args:
        date_str: Date string in any supported format

    Returns:
        datetime object

    Raises:
        ValueError: If the date string cannot be parsed in any supported format
    """
    # List of supported formats in order of preference
    # Always prioritize the system date format to avoid ambiguous parsing
    system_format = get_date_format()
    formats = [
        system_format,
        '%Y-%m-%d',  # ISO format (always supported)
        '%d/%m/%Y',  # DD/MM/YYYY
        '%m/%d/%Y',  # MM/DD/YYYY
        '%d-%m-%Y',  # DD-MM-YYYY
        '%m-%d-%Y',  # MM-DD-YYYY
        '%d.%m.%Y',  # DD.MM.YYYY
        '%m.%d.%Y',  # MM.DD.YYYY
    ]

    # Remove duplicates while preserving order
    seen = set()
    formats = [fmt for fmt in formats if not (fmt in seen or seen.add(fmt))]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date '{date_str}' in any supported format")

def format_date(dt: datetime | date | str, fmt: str | None = None) -> str:
    """Format a date/datetime using the current date format setting.

    Args:
        dt: The date/datetime to format (datetime, date, or ISO string)
        fmt: Optional specific format to use instead of the setting

    Returns:
        Formatted date string
    """
    if fmt is None:
        fmt = get_date_format()

    # Convert string to datetime if needed
    if isinstance(dt, str):
        try:
            # Try parsing ISO format first
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            # If parsing fails, return as-is
            return dt

    # Format the date
    if isinstance(dt, datetime):
        return dt.strftime(fmt)
    elif isinstance(dt, date):
        return dt.strftime(fmt)
    else:
        return str(dt)

def format_date_display(dt: datetime | date | str) -> str:
    """Format a date for display purposes using the current date format setting."""
    return format_date(dt)

def format_date_storage(dt: datetime | date) -> str:
    """Format a date for database storage (always ISO format)."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    elif isinstance(dt, date):
        return dt.isoformat()
    else:
        return str(dt)


def format_date_db(dt: datetime | date | str) -> str:
    """Return a date string suitable for database queries (YYYY-MM-DD).

    Accepts datetime, date, or a parseable date string. This is a
    compatibility wrapper used by older UI code.
    """
    # If a string was provided, try to parse it
    if isinstance(dt, str):
        try:
            parsed = parse_date_flexible(dt)
            return parsed.date().isoformat()
        except Exception:
            return dt

    # If a datetime, use the date part
    if isinstance(dt, datetime):
        return dt.date().isoformat()

    if isinstance(dt, date):
        return dt.isoformat()

    return str(dt)


def get_tkcalendar_date_pattern() -> str:
    """Return a tkcalendar-compatible date pattern based on system settings."""
    fmt = get_date_format()
    mapping = {
        '%Y-%m-%d': 'yyyy-mm-dd',
        '%d/%m/%Y': 'dd/mm/yyyy',
        '%m/%d/%Y': 'mm/dd/yyyy',
        '%d-%m-%Y': 'dd-mm-yyyy',
        '%m-%d-%Y': 'mm-dd-yyyy',
        '%d.%m.%Y': 'dd.mm.yyyy',
        '%m.%d.%Y': 'mm.dd.yyyy',
    }
    return mapping.get(fmt, 'yyyy-mm-dd')