from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Union


def convert_str_to_date(value: str, date_format=None) -> Union[str, datetime]:
    "try convert str to datetime using date formats"
    if date_format is None:
        date_format = ["%d-%m-%Y", "%Y-%m-%d %H:%M:%S"]
    if isinstance(date_format, str):
        date_format = [date_format]
    for frmt in date_format:
        try:
            value = datetime.strptime(value, frmt)
            break
        except ValueError:
            continue
    return value


class Bank:
    def __init__(
        self,
        login: str = None,
        module: str = None,
        name: str = None,
        password: str = None,
        website: str = None,
    ):
        self.login = login
        self.module = module
        self.name = name
        self.password = password
        self.website = website


class Account:
    id: str = None
    bank: Bank = None
    label: str = None
    type: str = None
    balance: float = None
    coming: float = None
    iban: str = None
    number: str = None

    def __init__(self, account: dict, date_format=None):
        for attr, value in account.items():
            if "date" in attr and isinstance(value, str):
                value = convert_str_to_date(value, date_format)
            setattr(self, attr, value)


class Budget:
    id: int
    label: str
    type: str
    amount: float
    start: datetime
    end: datetime
    fixed: bool


class Loan:
    id: str = None
    duration: int = None
    insurance_amount: float = None
    maturity_date: datetime = None
    nb_payments_left: int = None
    next_payment_amount: str = None
    next_payment_date: datetime = None
    rate: float = None
    total_amount: float = None

    def __init__(self, loan: dict, date_format=None):
        for attr, value in loan.items():
            if "date" in attr and isinstance(value, str):
                value = convert_str_to_date(value, date_format)
            setattr(self, attr, value)


class Saving:
    id: int
    name: str  # should be unique
    balance: int
    monthly_saving: int
    goal: int


class Transaction:
    id: str = None
    account: Account = None
    amount: float = None
    category: str = None
    date: datetime = None
    label: str = None
    type: str = None
    real_date: datetime = None
    value_date: datetime = None
    budget_id: int = None
    saving_id: int = None
    coming: bool = False
    comment: str = None
    parent: Transaction = None
    internal: Transaction = None

    def __init__(self, tra: dict, date_format=None):
        for attr, value in tra.items():
            if "date" in attr and isinstance(value, str):
                value = convert_str_to_date(value, date_format)
            setattr(self, attr, value)
        self.id = tra.get(
            "id",
            (
                hash_id(self.label) % 12345678
                + hash_id(
                    self.date
                    if isinstance(self.date, str)
                    else self.date.strftime("%Y-%m-%d %H:%M:%S")
                )
                % 213054
                + hash_id(str(self.amount)) % 65430
            ),
        )


def hash_id(string: str) -> int:
    """Hash String to INT"""
    return int(hashlib.sha1(string.encode("utf-8")).hexdigest(), 16)
