import hashlib
from math import ceil

from flask import Blueprint, current_app, render_template, request
from woob.capabilities.bank.base import Account, Loan, Transaction
from woob.capabilities.base import NotLoadedType
from woob.core import Woob
from woob.core.bcall import CallErrors
from woob.exceptions import BrowserUnavailable

from flaskr.auth import login_required
from flaskr.db import executemany, get_db

bp = Blueprint("accounts", __name__)


@bp.route("/accounts")
@login_required
def index():
    length = request.args.get("length", 10, type=int)
    curr_page = request.args.get("page", 1, type=int)
    month = request.args.get("month", None, type=str)  # format "YYYY-MM"
    curr = get_db()[0]
    curr.execute("SELECT * FROM account")
    accounts = curr.fetchall()
    types = {}
    for account in accounts:
        if account[3] not in types:
            types[account[3]] = []
        types[account[3]].append(account)
    if month is None:
        curr.execute(
            "SELECT date_format(Date,'%Y-%m') FROM transaction ORDER BY Date DESC LIMIT 1"
        )
        month = curr.fetchone()[0]
    curr.execute(
        f"""SELECT COUNT(*)
        FROM transaction
        WHERE YEAR(Date) = {int(month[0:4])} AND MONTH(Date) ={int(month[6:7])}"""
    )
    total = curr.fetchone()[0]
    curr.execute(
        f"""
        SELECT Date, Category, Amount, Label, Type
        FROM transaction 
        WHERE YEAR(Date) = {int(month[0:4])} AND MONTH(Date) ={int(month[6:7])}
        ORDER BY date DESC
        LIMIT {length}
        OFFSET {(curr_page-1)*length}
    """
    )
    transactions = curr.fetchall()
    return render_template(
        "finances/accounts.html",
        types=types,
        transactions=transactions,
        total=total,
        length=length,
        ceil=ceil,
        curr_page=curr_page,
        month=month,
    )


@bp.route("/accounts/<acc_id>")
@login_required
def transaction(acc_id):
    """Query all transactions for a specific account"""
    curr = get_db()[0]
    curr.execute("SELECT * FROM transaction WHERE account=%s", acc_id)
    transactions = curr.fetchall()
    return render_template("finances/transactions.html", transactions=transactions)


def hash_id(string: str) -> int:
    """Hash String to INT"""
    return int(hashlib.sha1(string.encode("utf-8")).hexdigest(), 16)


@bp.route("/accounts/refresh")
@login_required
def refresh():
    """Refresh all accounts history"""
    banks = [
        {
            "module_name": "bnp",
            "name": "bnp",
            "params": {
                "login": current_app.config["BNP_LOGIN"],
                "password": current_app.config["BNP_PASSWORD"],
            },
        },
        {
            "module_name": "hellobank",
            "name": "hb",
            "params": {
                "login": current_app.config["HB_LOGIN"],
                "password": current_app.config["HB_PASSWORD"],
            },
        },
        {
            "module_name": "bp",
            "name": "bp",
            "params": {
                "login": current_app.config["BP_LOGIN"],
                "password": current_app.config["BP_PASSWORD"],
            },
        },
        {
            "module_name": "cragr",
            "name": "ca",
            "params": {
                "login": current_app.config["CA_LOGIN"],
                "password": current_app.config["CA_PASSWORD"],
                "website": "www.ca-paris.fr",
            },
        },
    ]

    for bank in banks:
        woob = Woob()
        print(f"Processing {bank['module_name']}")
        woob.load_backend(bank["module_name"], bank["name"], params=bank["params"])
        accounts: list[Account] = list(woob.iter_accounts())

        loans = [x for x in accounts if isinstance(x, Loan)]

        if accounts:
            print("Loading accounts")
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
            executemany(
                """
                INSERT INTO account 
                    (id, bank, label, type, balance, coming, iban, number)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s) 
                ON DUPLICATE KEY UPDATE 
                    type     = VALUES(type),
                    balance  = VALUES(balance), 
                    coming   = VALUES(coming) ;
            """,
                records,
            )

        if loans:
            print("Loading loans")

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
            executemany(
                """
                INSERT INTO loan 
                    (id, duration, insurance_amount,
                    maturity_date, nb_payments_left, next_payment_amount,
                    next_payment_date, rate, total_amount)
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
            """,
                records,
            )

        for account in accounts:
            print(f"Processing transactions : {account.label}")
            try:
                transactions: list[Transaction] = list(woob.iter_history(account))
                coming_transactions: list[Transaction] = list(
                    woob.iter_coming(account)
                )
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

                executemany(
                    """
                        UPDATE transaction
                        SET id = %s,category = %s, date = %s, type = %s, value_date = %s, real_date = %s, coming = 0
                        WHERE transaction.label = %s AND transaction.account = %s AND transaction.amount = %s AND coming = 1
                    """,
                    [
                        (
                            tra.id,
                            tra.category,
                            (
                                tra.date.strftime("%Y-%m-%d %H:%M:%S")
                                if not isinstance(tra.date, NotLoadedType)
                                else None
                            ),
                            tr_type[tra.type],
                            (
                                tra.vdate.strftime("%Y-%m-%d %H:%M:%S")
                                if not isinstance(tra.vdate, NotLoadedType)
                                else None
                            ),
                            (
                                tra.rdate.strftime("%Y-%m-%d %H:%M:%S")
                                if not isinstance(tra.rdate, NotLoadedType)
                                else None
                            ),
                            tra.label,
                            account.id,
                            tra.amount,
                        )
                        for tra in transactions
                    ],
                )

                records = [
                    (
                        (
                            hash_id(transaction.label) % 12345678
                            + hash_id(transaction.date.strftime("%Y-%m-%d %H:%M:%S"))
                            % 213054
                            + hash_id(str(transaction.amount)) % 65430
                            if transaction.id == ""
                            else transaction.id
                        ),
                        account.id,
                        transaction.amount,
                        transaction.category,
                        (
                            transaction.date.strftime("%Y-%m-%d %H:%M:%S")
                            if not isinstance(transaction.date, NotLoadedType)
                            else None
                        ),
                        transaction.label,
                        tr_type[transaction.type],
                        (
                            transaction.rdate.strftime("%Y-%m-%d %H:%M:%S")
                            if not isinstance(transaction.rdate, NotLoadedType)
                            else None
                        ),
                        (
                            transaction.vdate.strftime("%Y-%m-%d %H:%M:%S")
                            if not isinstance(transaction.vdate, NotLoadedType)
                            else None
                        ),
                    )
                    for transaction in transactions
                ]
                executemany(
                    """
                        INSERT INTO transaction 
                            (id, account, amount,
                            category, date, label,
                            type, real_date, value_date)
                        VALUES 
                            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            id   =  VALUES(id)
                    """,
                    records,
                )

            if coming_transactions:
                records = [
                    (
                        (
                            hash_id(transaction.label) % 12345678
                            + hash_id(transaction.date.strftime("%Y-%m-%d %H:%M:%S"))
                            % 213054
                            + hash_id(str(transaction.amount)) % 65430
                            if transaction.id == ""
                            else transaction.id
                        ),
                        account.id,
                        transaction.amount,
                        (
                            transaction.date.strftime("%Y-%m-%d %H:%M:%S")
                            if not isinstance(transaction.date, NotLoadedType)
                            else None
                        ),
                        transaction.label,
                    )
                    for transaction in coming_transactions
                ]
                executemany(
                    """
                        INSERT INTO transaction 
                            (id, account, amount, date, label, coming)
                        VALUES 
                            (%s, %s, %s, %s, %s, 1)
                        ON DUPLICATE KEY UPDATE
                            id   =  VALUES(id)
                            coming = 1
                    """,
                    records,
                )
    return "refreshed"
