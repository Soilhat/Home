from datetime import datetime

from core.entities.user import User
from core.ports.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    "In Memory implementation of UserRepository"
    users: list[User] = []

    def find_by_id(self, user_id: str) -> User:
        for user in self.users:
            if user_id == user.id:
                return user
        return None

    def find_by_username(self, username: str) -> User:
        for user in self.users:
            if username == user.username:
                return user
        return None

    def register(self, username: str, password: str) -> User:
        user = User(len(self.users), username, password)
        self.users.append(user)
        return user

    def update_refreshed_user(self, user_id: int) -> User:
        "Update specific user refreshed date to now"
        user = self.find_by_id(user_id)
        user.refreshed = datetime.now()
        return user
