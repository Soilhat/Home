class UserAlreadyExists(Exception):
    def __init__(self, username):
        self.username = username

    def __str__(self) -> str:
        return f"User {self.username} is already registered."
