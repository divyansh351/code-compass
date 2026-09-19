"""Sample utilities fixture."""

import hashlib


def hash_token(token: str) -> str:
    """Hash a sensitive token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
