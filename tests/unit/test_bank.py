import pytest

from adapters.in_memory.bank_repository import InMemoryBankRepository
from core.ports.bank_repository import Bank, BankRepository
from core.use_cases.bank import BankCase


@pytest.fixture(name="bank_repository")
def bank_repository_fixture() -> BankRepository:
    "In Memory repository"
    return InMemoryBankRepository()


@pytest.fixture(name="bank_use_case")
def bank_use_case_fixture(bank_repository: BankRepository) -> Bank:
    "Bank use case to test"
    return BankCase(bank_repository)


class TestBank:
    user_id = 1

    def test_empty_banks(self, bank_use_case: BankCase):
        assert bank_use_case.load_banks(self.user_id) == []
