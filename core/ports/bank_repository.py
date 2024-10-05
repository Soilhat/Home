from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from core.entities.bank import Account, Bank, Loan, Transaction


class BankRepository(ABC):
    bank_config = {"ca-paris": {"module": "cragr", "website": "www.ca-paris.fr"}}

    @abstractmethod
    def get_balance(self, user_id: int, loans: bool = False) -> int:
        "Get full user balance from all banks"

    @abstractmethod
    def get_savings(self, user_id: int) -> int:
        "Get savings balance"

    @abstractmethod
    def get_all_savings(self, user_id: int):
        "Get all saving list"

    @abstractmethod
    def get_saving_trac(self, user_id, saving_id):
        "Get transactions for specific saving"

    @abstractmethod
    def get_incomes(self, user_id: int) -> int:
        "Get incomes for current month"

    @abstractmethod
    def get_incomes_avg(self, user_id: int) -> int:
        "Get incomes average for last 3 months"

    @abstractmethod
    def get_last_month(self, user_id: int) -> datetime:
        "Get last month data in format '%Y-%m'. Should return today's date as default"

    @abstractmethod
    def get_pending_budget(self, user_id: int, month: str) -> int:
        "Get left budget to spend on specific month ('%Y-%m')"

    @abstractmethod
    def get_curr_expenses(self, user_id: int) -> List[tuple]:
        "Get monthly saving for current month"

    @abstractmethod
    def get_monthly_savings(self, user_id: int) -> int:
        "Get monthly saving for current month"

    @abstractmethod
    def get_monthly_savings_avg(self, user_id: int) -> int:
        "Get monthly savings average for last 3 months"

    @abstractmethod
    def get_bud_expenses(self, user_id: int, fixed: bool = False) -> int:
        "Get budget variable or fixed expenses for current month"

    @abstractmethod
    def get_bud_expenses_avg(self, user_id: int, fixed: bool = False) -> int:
        "Get budget variable or fixed expenses average for last 3 months"

    @abstractmethod
    def get_all_accounts(self, user_id: int) -> tuple:
        "Get all accounts informations"

    @abstractmethod
    def get_transactions_count(self, user_id: int, month: str) -> int:
        "Get count of all transactions for specific month"

    @abstractmethod
    def get_transactions(
        self, user_id: int, month: str, length: int = 10, curr_page: int = 1
    ) -> tuple:
        "Get all transactions for specific month"

    @abstractmethod
    def get_budget_types(self, user_id: int) -> tuple:
        "Get all budget types"

    @abstractmethod
    def get_budgeted_transactions(
        self, user_id: int, month: str, fixed: bool = False
    ) -> tuple:
        "Get budgeted transactions for specific month"

    @abstractmethod
    def get_summary(self, user_id: int, month: str) -> tuple:
        "Get summary transactions for specific month"

    @abstractmethod
    def get_revenus(self, user_id: int, month: str) -> tuple:
        "Get revenus transactions for specific month"

    @abstractmethod
    def get_expenses(self, user_id: int, month: str) -> tuple:
        "Get expenses transactions for specific month"

    @abstractmethod
    def get_spendings(self, user_id: int, month: str) -> list:
        "Get spendings transactions for specific month"

    @abstractmethod
    def get_banks(self, user_id: int, case_module=True) -> list:
        "Get all banks info"

    @abstractmethod
    def upload_transactions(self, user_id, transactions: List[Transaction]):
        "upload transactions list"

    @abstractmethod
    def check_internal(self, user_id: int):
        "Check internal transactions for a user"

    @abstractmethod
    def get_account(self, user_id: int, account_number: str) -> Account:
        "get Account based on account number or id"

    @abstractmethod
    def update_trac(self, user_id: int, trac_id, budget_name):
        "update transaction linked budget"

    @abstractmethod
    def upload_accounts(self, user_id, accounts: List[Account]):
        "update given accounts"

    @abstractmethod
    def upload_loans(self, user_id, loans: List[Loan]):
        "update given loans"

    @abstractmethod
    def delete_bank(self, user_id: int, login):
        "delete existing bank"

    @abstractmethod
    def get_budget(self, user_id, current: bool, fixed: bool, income: bool):
        "Get budget informations applying filters"

    @abstractmethod
    def update_budget(self, user_id, label, amount, budget_type, start, end, fixed, id):
        "Update Budget values"
