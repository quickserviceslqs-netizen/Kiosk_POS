from __future__ import annotations
"""Password hashing utilities using PBKDF2-HMAC (SHA-256)."""

def get_currency_code():
    """Return the configured ISO 4217 currency code (e.g., 'USD', 'KES')."""
    from database.init_db import get_connection
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency_code'")
        row = cursor.fetchone()
        if row:
            return row['value'] if isinstance(row, dict) else row[0]
        return "USD"


def get_cart_vat_enabled():
    """Return True if VAT calculation is enabled for cart."""
    from database.init_db import get_connection
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'vat_enabled'")
        row = cursor.fetchone()
        if row:
            value = row['value'] if isinstance(row, dict) else row[0]
            return value.lower() == 'true'
        return True  # Default to enabled


def get_cart_discount_enabled():
    """Return True if discount functionality is enabled for cart."""
    from database.init_db import get_connection
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'discount_enabled'")
        row = cursor.fetchone()
        if row:
            value = row['value'] if isinstance(row, dict) else row[0]
            return value.lower() == 'true'
        return True  # Default to enabled


def get_cart_suspend_enabled():
    """Return True if cart suspend/resume functionality is enabled."""
    from database.init_db import get_connection
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'suspend_enabled'")
        row = cursor.fetchone()
        if row:
            value = row['value'] if isinstance(row, dict) else row[0]
            return value.lower() == 'true'
        return True  # Default to enabled


def set_cart_vat_enabled(enabled: bool):
    """Set whether VAT calculation is enabled for cart."""
    from database.init_db import get_connection
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('vat_enabled', ?)", (str(enabled).lower(),))
        conn.commit()


def set_cart_discount_enabled(enabled: bool):
    """Set whether discount functionality is enabled for cart."""
    from database.init_db import get_connection
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('discount_enabled', ?)", (str(enabled).lower(),))
        conn.commit()


def set_cart_suspend_enabled(enabled: bool):
    """Set whether cart suspend/resume functionality is enabled."""
    from database.init_db import get_connection
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('suspend_enabled', ?)", (str(enabled).lower(),))
        conn.commit()


# Payment methods helpers
import json

_DEFAULT_PAYMENT_METHODS = ["Cash", "M-Pesa", "Card"]


def get_payment_methods() -> list[str]:
    """Return the configured list of payment methods for the system."""
    from database.init_db import get_connection
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'payment_methods'")
        row = cursor.fetchone()
        if row:
            raw = row['value'] if isinstance(row, dict) else row[0]
            try:
                methods = json.loads(raw)
                if isinstance(methods, list):
                    return [str(m) for m in methods]
            except Exception:
                pass
    # Return default if not set or error
    return list(_DEFAULT_PAYMENT_METHODS)


def set_payment_methods(methods: list[str]) -> None:
    """Persist the list of payment methods (JSON encoded) in settings and notify listeners."""
    from database.init_db import get_connection
    try:
        raw = json.dumps(list(methods))
    except Exception:
        raw = json.dumps([str(m) for m in methods])
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('payment_methods', ?)", (raw,))
        conn.commit()
    # Notify any in-process subscribers that the payment methods have changed
    _notify_payment_methods_changed()


# Simple in-process pub/sub for payment methods changes
_payment_methods_listeners: list[callable] = []

def subscribe_payment_methods(cb: callable) -> None:
    """Register a callback to be notified when payment methods change.

    The callback must be callable without arguments.
    """
    if cb not in _payment_methods_listeners:
        _payment_methods_listeners.append(cb)


def unsubscribe_payment_methods(cb: callable) -> None:
    """Unregister a previously registered callback."""
    try:
        _payment_methods_listeners.remove(cb)
    except ValueError:
        pass


def _notify_payment_methods_changed() -> None:
    """Call all registered callbacks safely."""
    for cb in list(_payment_methods_listeners):
        try:
            cb()
        except Exception:
            # Swallow exceptions from user callbacks to avoid affecting app flow
            pass
import hashlib
import hmac
import os
import re
import time
from typing import Tuple, Dict, Any
from collections import defaultdict

PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16


def hash_password(password: str, salt: bytes | None = None) -> Tuple[str, str]:
    """Return (salt_hex, hash_hex) for the given password."""
    if salt is None:
        salt = os.urandom(SALT_BYTES)
    pwd_bytes = password.encode("utf-8")
    digest = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    """Verify password against stored salt/hash; constant-time compare."""
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    pwd_bytes = password.encode("utf-8")
    candidate = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(candidate, expected)


def sanitize_html_input(text: str) -> str:
    """Sanitize HTML input to prevent XSS attacks.

    Removes potentially dangerous HTML tags and attributes.
    This is a basic implementation - for production use consider a proper HTML sanitizer.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text safe for HTML display
    """
    if not text:
        return ""

    # Remove script tags and their content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove other dangerous tags
    dangerous_tags = ['iframe', 'object', 'embed', 'form', 'input', 'button', 'link', 'meta']
    for tag in dangerous_tags:
        text = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(rf'<{tag}[^>]*/>', '', text, flags=re.IGNORECASE)

    # Remove event handlers
    text = re.sub(r'\bon\w+\s*=', '', text, flags=re.IGNORECASE)

    # Remove javascript: URLs
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)

    return text


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.

    Args:
        length: Length of the token in bytes (will be hex-encoded so actual length is 2x)

    Returns:
        Hex-encoded secure random token
    """
    return os.urandom(length).hex()


def validate_file_upload(filename: str, allowed_extensions: list[str] = None) -> bool:
    """Validate uploaded file for security.

    Args:
        filename: Original filename
        allowed_extensions: List of allowed file extensions (e.g., ['.jpg', '.png'])

    Returns:
        True if file is safe to upload, False otherwise
    """
    if not filename:
        return False

    # Check for dangerous characters
    if any(char in filename for char in ['/', '\\', '..', '<', '>', ':', '*', '?', '"', '|']):
        return False

    # Check file extension
    if allowed_extensions:
        _, ext = os.path.splitext(filename.lower())
        if ext not in [e.lower() for e in allowed_extensions]:
            return False

    return True


class RateLimiter:
    """Simple rate limiter to prevent brute force attacks."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if action is allowed for the given key.

        Args:
            key: Identifier for the rate limit (e.g., IP address, username)

        Returns:
            True if action is allowed, False if rate limit exceeded
        """
        now = time.time()
        attempts = self.attempts[key]

        # Remove old attempts outside the window
        attempts[:] = [t for t in attempts if now - t < self.window_seconds]

        if len(attempts) >= self.max_attempts:
            return False

        attempts.append(now)
        return True

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self.attempts[key].clear()


# Global rate limiter instance for login attempts
login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)  # 5 attempts per 5 minutes


def check_login_rate_limit(identifier: str) -> bool:
    """Check if login attempt is allowed for the given identifier.

    Args:
        identifier: User identifier (IP, username, etc.)

    Returns:
        True if login is allowed, False if rate limited
    """
    return login_rate_limiter.is_allowed(identifier)
