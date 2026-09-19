"""Sample User repository."""

from typing import Dict, Optional
from models import User


class BaseRepository:
    """Base repository with common operations."""
    def count(self) -> int:
        return 0


class UserRepository(BaseRepository):
    """User data access layer."""

    def __init__(self):
        self._storage: Dict[str, User] = {}

    def get(self, user_id: str) -> Optional[User]:
        """Fetch user by ID."""
        return self._storage.get(user_id)

    def save(self, user: User) -> None:
        """Save user record."""
        self._storage[user.id] = user
