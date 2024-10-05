from datetime import datetime

from adapters.sqllite.commun import ExecuteSqlite
from core.ports.user_repository import User, UserRepository


class SqlliteUserRepository(UserRepository):
    "SQLlite implementation of UserRepository"

    def __init__(self):
        self.executor = ExecuteSqlite("users.db", "create_user.sql")

    def find_by_id(self, user_id: int) -> User:
        user = self.executor.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,), one=True
        )
        if user is None:
            return None
        return User(user[0], user[1], user[2], user[3])

    def find_by_username(self, username: str) -> User:
        user = self.executor.execute(
            "SELECT * FROM user WHERE username = ?", (username,), one=True
        )
        return User(user[0], user[1], user[2], user[3])

    def register(self, username: str, password: str) -> User:
        self.executor.execute(
            "INSERT INTO user (username, password) VALUES (?, ?)",
            (username, password),
            commit=True,
        )
        return self.find_by_username(username)

    def update_refreshed_user(self, user_id: int, date: datetime = datetime.today()):
        self.executor.execute(
            f"UPDATE user SET refreshed=? WHERE id={user_id}", (date,), commit=True
        )
        return self.find_by_id(user_id)
