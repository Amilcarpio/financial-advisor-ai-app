"""OAuth helper utilities."""
from typing import Any, Dict


def build_authorization_url(base_url: str, **params: Any) -> str:
    """Construct an authorization URL."""

    if not params:
        return base_url
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"{base_url}?{query}"
