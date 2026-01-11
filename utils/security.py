from __future__ import annotations
"""Password hashing utilities using PBKDF2-HMAC (SHA-256)."""

def get_currency_code():
    """Return the configured ISO 4217 currency code (e.g., 'USD', 'KES')."""
    from database.init_db import get_connection
    with get_connection() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency'")
        row = cursor.fetchone()
        if row:
            return row['value'] if isinstance(row, dict) else row[0]
        return "USD"
 
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
