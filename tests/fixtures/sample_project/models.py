"""Sample User data model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Represents a system user."""
    id: str
    username: str
    email: str
    is_active: bool = True
