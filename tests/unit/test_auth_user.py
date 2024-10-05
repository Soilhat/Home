import pytest

from adapters.in_memory.user_repository import InMemoryUserRepository
from core.ports.user_repository import User, UserRepository
from core.use_cases.auth_user import AuthUser


@pytest.fixture(name="users_repository")
def users_repository_fixture() -> UserRepository:
    "In Memory repository"
    return InMemoryUserRepository()


@pytest.fixture(name="auth_user_use_case")
def auth_user_use_case_fixture(users_repository: UserRepository) -> User:
    "Auth use case to test"
    return AuthUser(users_repository)


class TestAuth:
    username = "test"
    password = "testing"

    def test_user_not_found(self, auth_user_use_case: AuthUser):
        assert auth_user_use_case.login(self.username) is None

    def test_user_registration(self, auth_user_use_case: AuthUser):
        auth_user_use_case.register(self.username, self.password)
        assert auth_user_use_case.login(self.username).password == self.password
