
import sys
import os
import hashlib

from woob.core import Woob
from woob.capabilities.bank.base import Account, Loan, Transaction
from woob.capabilities.base import NotLoadedType
from woob.exceptions import BrowserUnavailable
from woob.core.bcall import CallErrors
from db import executemany

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from instance.config import BNP_login, BNP_password,HB_login, HB_password, CA_login, CA_password, BP_login, BP_password

banks = [
    {"module_name" : 'bnp', "name":'bnp', "params":{'login': BNP_login, 'password': BNP_password}},
    {"module_name" : 'hellobank', "name":'hb', "params":{'login': HB_login, 'password': HB_password}},
    {"module_name" : 'bp', "name":'bp', "params":{'login': BP_login, 'password': BP_password}},
    {"module_name" : 'cragr', "name":'ca', "params":{'login': CA_login, 'password': CA_password, 'website':"www.ca-paris.fr"}},
]

def hash_id(string:str)->int:
    """ Hash String to INT"""
    return int(hashlib.sha1(string.encode("utf-8")).hexdigest(),16)

for bank in banks:
    w = Woob()
    print(f"Processing {bank['module_name']}")
    w.load_backend(bank["module_name"], bank["name"], params=bank["params"])
    accounts: list[Account] = list(w.iter_accounts())

    loans = [x for x in accounts if isinstance(x, Loan)]

    if accounts:
        print("Loading accounts")
        QUERY = """
            INSERT INTO account 
                (id, bank, label, type, balance, coming, iban, number)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s) 
            ON DUPLICATE KEY UPDATE 
                type     = VALUES(type),
                balance  = VALUES(balance), 
                coming   = VALUES(coming) ;
        """
        account_type = [
            "UNKNOWN",
            "CHECKING",
            "SAVINGS",
            "DEPOSIT",
            "LOAN",
            "MARKET",
            "JOINT",
            "CARD",
            "LIFE INSURANCE",
            "PEE",
            "PERCO",
            "ARTICLE 83",
            "RSP",
            "PEA",
            "CAPITALISATION",
            "PERP",
            "MADELIN",
            "MORTGAGE",
            "CONSUMER CREDIT",
            "REVOLVING CREDIT",
            "PER",
            "REAL ESTATE",
            "CROWDLENDING",
        ]

        records = [
            (
                account.id,
                account.backend,
                account.label,
                account_type[account.type],
                account.balance,
                account.coming,
                account.iban,
                account.number,
            )
            for account in accounts
        ]
        executemany(QUERY, records)

    if loans:
        print("Loading loans")
        QUERY = """
            INSERT INTO loan 
                (id, duration, insurance_amount, maturity_date, nb_payments_left, next_payment_amount, next_payment_date, rate, total_amount)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
            ON DUPLICATE KEY UPDATE 
                duration  = VALUES(duration), 
                insurance_amount  = VALUES(insurance_amount),
                maturity_date  = VALUES(maturity_date),
                nb_payments_left  = VALUES(nb_payments_left),
                next_payment_amount  = VALUES(next_payment_amount),
                next_payment_date  = VALUES(next_payment_date),
                rate  = VALUES(rate),
                total_amount  = VALUES(total_amount);
        """

        records = [
            (
                loan.id,
                loan.duration,
                loan.insurance_amount,
                loan.maturity_date.strftime("%Y-%m-%d %H:%M:%S"),
                loan.nb_payments_left,
                loan.next_payment_amount,
                loan.next_payment_date.strftime("%Y-%m-%d %H:%M:%S"),
                loan.rate,
                loan.total_amount,
            )
            for loan in loans
        ]
        executemany(QUERY, records)

    for account in accounts:
        print(f"Processing transactions : {account.label}")
        try:
            transactions: list[Transaction] = list(w.iter_history(account))
        except (BrowserUnavailable, CallErrors) as exc:
            print(f"{exc.errors}")
            print(f"{account.backend} Browser Unavailable")
            continue

        if transactions:
            tr_type = [
                "TYPE_UNKNOWN",
                "TYPE_TRANSFER",
                "TYPE_ORDER",
                "TYPE_CHECK",
                "TYPE_DEPOSIT",
                "TYPE_PAYBACK",
                "TYPE_WITHDRAWAL",
                "TYPE_CARD",
                "TYPE_LOAN_PAYMENT",
                "TYPE_BANK",
                "TYPE_CASH_DEPOSIT",
                "TYPE_CARD_SUMMARY",
                "TYPE_DEFERRED_CARD",
                "TYPE_INSTANT",
            ]

            QUERY = """
                INSERT INTO transaction 
                    (id, account, amount, category, date, label, type, real_date, value_date)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    id   =  VALUES(id)
            """

            records = [
                (
                    hash_id(transaction.label) % 12345678 + hash_id(transaction.date.strftime("%Y-%m-%d %H:%M:%S")) % 213054 + hash_id(str(transaction.amount)) % 65430 if transaction.id == '' else transaction.id,
                    account.id,
                    transaction.amount,
                    transaction.category,
                    transaction.date.strftime("%Y-%m-%d %H:%M:%S") if not isinstance(transaction.date, NotLoadedType) else None,
                    transaction.label,
                    tr_type[transaction.type],
                    transaction.rdate.strftime("%Y-%m-%d %H:%M:%S") if not isinstance(transaction.rdate, NotLoadedType) else None,
                    transaction.vdate.strftime("%Y-%m-%d %H:%M:%S") if not isinstance(transaction.vdate, NotLoadedType) else None,
                )
                for transaction in transactions
            ]
            executemany(QUERY, records)
