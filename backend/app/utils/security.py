"""Security related helpers."""
from hashlib import sha256


def hash_secret(raw: str) -> str:
    """Naive hashing helper for placeholder implementations."""

    return sha256(raw.encode("utf-8")).hexdigest()
