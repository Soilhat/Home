"User definition"
from datetime import datetime


class User:
    "Tool user"

    def __init__(
        self, user_id: int, username: str, password: str, refreshed: datetime = None
    ) -> None:
        self.id = user_id
        self.username = username
        self.password = password
        self.refreshed = refreshed
