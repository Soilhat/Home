from typing import List

from core.ports.bank_repository import Bank, BankRepository


class BankCase:
    "Financial use case"

    def __init__(self, bank_repository: BankRepository) -> None:
        self.bank_repository = bank_repository

    def load_banks(self, user_id: int) -> List[Bank]:
        "Load banks for specific user"
        return self.bank_repository.load_banks(user_id)
