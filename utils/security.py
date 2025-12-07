"""Password hashing utilities using PBKDF2-HMAC (SHA-256)."""
from __future__ import annotations

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
