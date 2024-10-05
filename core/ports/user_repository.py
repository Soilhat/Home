"User Repository interface definition"
from abc import ABC, abstractmethod
from datetime import datetime

from core.entities.user import User


class UserRepository(ABC):
    "Repository that holds all users"

    @abstractmethod
    def find_by_id(self, user_id: int) -> User:
        "Find user based on id"

    @abstractmethod
    def find_by_username(self, username: str) -> User:
        "Find user based on username"

    @abstractmethod
    def register(self, username: str, password: str) -> User:
        "Register a new user to the repository"

    @abstractmethod
    def update_refreshed_user(
        self, user_id: int, date: datetime = datetime.today()
    ) -> User:
        "Update specific user refreshed date"
