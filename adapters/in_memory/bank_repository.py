from typing import List

from core.ports.bank_repository import Bank, BankRepository


class InMemoryBankRepository(BankRepository):
    "In Memory implementation of BankRepository"
    banks = {}

    def load_banks(self, user_id: int) -> List[Bank]:
        self.banks.get(user_id, [])
