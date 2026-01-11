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
from typing import Tuple

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
