"""
Settings management module.

Provides a centralized interface for accessing application settings
stored in the database settings table.
"""

from database.init_db import get_setting, set_setting


def get_business_name() -> str:
    """Get the business name setting."""
    return get_setting('business_name') or 'Kiosk POS'


def set_business_name(name: str) -> None:
    """Set the business name setting."""
    set_setting('business_name', name)


def get_address() -> str:
    """Get the business address setting."""
    return get_setting('business_address') or ''


def set_address(address: str) -> None:
    """Set the business address setting."""
    set_setting('business_address', address)


def get_phone() -> str:
    """Get the business phone setting."""
    return get_setting('business_phone') or ''


def set_phone(phone: str) -> None:
    """Set the business phone setting."""
    set_setting('business_phone', phone)


def get_email() -> str:
    """Get the business email setting."""
    return get_setting('business_email') or ''


def set_email(email: str) -> None:
    """Set the business email setting."""
    set_setting('business_email', email)


def get_tax_id() -> str:
    """Get the business tax ID setting."""
    return get_setting('business_tax_id') or ''


def set_tax_id(tax_id: str) -> None:
    """Set the business tax ID setting."""
    set_setting('business_tax_id', tax_id)


def get_receipt_footer() -> str:
    """Get the receipt footer text setting."""
    return get_setting('receipt_footer') or 'Thank you for your purchase!'


def set_receipt_footer(footer: str) -> None:
    """Set the receipt footer text setting."""
    set_setting('receipt_footer', footer)