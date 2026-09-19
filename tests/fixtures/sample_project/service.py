"""Sample User service demonstrating classes, imports, inheritance, and calls."""

import hashlib
from repository import UserRepository
from models import User
import requests


class UserService:
    """User business logic service."""

    def __init__(self):
        self.repo = UserRepository()

    def get_user(self, user_id: str) -> User:
        """Retrieve user with validation."""
        user = self.repo.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

    def create_user(self, username: str, email: str) -> User:
        """Create and store a new user."""
        u_id = hashlib.sha256(email.encode("utf-8")).hexdigest()[:8]
        new_user = User(id=u_id, username=username, email=email)
        self.repo.save(new_user)
        return new_user
