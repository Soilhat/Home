from core.ports.user_repository import User, UserRepository


class AuthUser:
    "Authentication process"

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def register(self, username: str, password: str) -> User:
        "Add new user to repository"
        return self.user_repository.register(username, password)

    def login(self, username: str) -> User:
        "Retrieve user by username"
        return self.user_repository.find_by_username(username)
