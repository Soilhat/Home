import hashlib
import traceback
from math import ceil

from flask import Blueprint, render_template, request, session
from woob.capabilities.bank.base import Account, Loan, Transaction
from woob.capabilities.base import NotAvailableType, NotLoadedType
from woob.core import Woob
from woob.core.bcall import CallErrors
from woob.exceptions import BrowserUnavailable

from core.entities.bank import Account as CoreAccount
from core.entities.bank import Bank as CoreBank
from core.entities.bank import Loan as CoreLoan
from core.entities.bank import Transaction as Trac
from flaskr.auth import login_required
from flaskr.db import get_db
from flaskr.extensions import bank_repository, user_repository
from flaskr.finances.bank import get_banks

bp = Blueprint("accounts", __name__)


@bp.route("/accounts")
@login_required
def index():
    length = request.args.get("length", 10, type=int)
    curr_page = request.args.get("page", 1, type=int)
    month = request.args.get("month", None, type=str)  # format "YYYY-MM"
    user_id = session.get("user_id")
    accounts = bank_repository.get_all_accounts(user_id)
    types = {}
    for account in accounts:
        if account[3] not in types:
            types[account[3]] = []
        types[account[3]].append(account)
    if month is None:
        month = bank_repository.get_last_month(user_id)
    total = bank_repository.get_transactions_count(user_id, month)
    transactions = bank_repository.get_transactions(user_id, month, length, curr_page)
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
    curr.execute("SELECT * FROM 'transaction' WHERE account=?", acc_id)
    transactions = curr.fetchall()
    return render_template("finances/transactions.html", transactions=transactions)


def hash_id(string: str) -> int:
    """Hash String to INT"""
    return int(hashlib.sha1(string.encode("utf-8")).hexdigest(), 16)


@bp.route("/accounts/refresh")
@login_required
def refresh():
    """Refresh all accounts history"""
    user_id = session["user_id"]
    banks = [
        {
            "module_name": bank[1],
            "name": bank[2],
            "params": {
                "login": bank[0],
                "password": bank[3],
                "website": bank[4],
            },
        }
        for bank in get_banks(case_module=False)
    ]
    for bank in banks:
        woob = Woob()
        print(f"Processing {bank['module_name']}")
        corebank = CoreBank(name = bank["name"])
        try:
            woob.load_backend(
                bank["module_name"],
                bank["name"],
                params={
                    key: value
                    for key, value in bank["params"].items()
                    if value is not None
                },
            )
            accounts: list[Account] = list(woob.iter_accounts())
        except Exception:
            traceback.print_exc()
            continue

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
                CoreAccount(
                    {
                        "id": conv_woob(value=account.id),
                        "bank": corebank,
                        "label": conv_woob(value=account.label),
                        "type": conv_woob(value=account_type[account.type]),
                        "balance": conv_woob(type="float", value=account.balance),
                        "coming": conv_woob(type="float", value=account.coming),
                        "iban": conv_woob(account.iban),
                        "number": conv_woob(value=account.number),
                    }
                )
                for account in accounts
            ]
            bank_repository.upload_accounts(user_id, records)

        if loans:
            print("Loading loans")

            records = [
                CoreLoan(
                    {
                        "id": loan.id,
                        "duration": conv_woob(type="float", value=loan.duration),
                        "insurance_amount": conv_woob(
                            type="float", value=loan.insurance_amount
                        ),
                        "maturity_date": conv_woob(
                            type="date", value=loan.maturity_date
                        ),
                        "nb_payments_left": conv_woob(
                            type="float", value=loan.nb_payments_left
                        ),
                        "next_payment_amount": conv_woob(
                            type="float", value=loan.next_payment_amount
                        ),
                        "next_payment_date": conv_woob(
                            type="date", value=loan.next_payment_date
                        ),
                        "rate": conv_woob(type="float", value=loan.rate),
                        "total_amount": conv_woob(
                            type="float", value=loan.total_amount
                        ),
                    }
                )
                for loan in loans
            ]
            bank_repository.upload_loans(user_id, records)

        for account in accounts:
            print(f"Processing transactions : {account.label}")
            try:
                transactions: list[Transaction] = list(woob.iter_history(account))
                coming_transactions: list[Transaction] = list(woob.iter_coming(account))
            except (BrowserUnavailable, CallErrors) as exc:
                print(f"{exc.errors}")
                print(f"{account.backend} Browser Unavailable")
                continue
            core_account = CoreAccount(
                {
                    "id": conv_woob(value=account.id),
                    "bank": corebank,
                    "label": conv_woob(value=account.label),
                    "type": conv_woob(value=account_type[account.type]),
                    "balance": conv_woob(type="float", value=account.balance),
                    "coming": conv_woob(type="float", value=account.coming),
                    "iban": conv_woob(account.iban),
                    "number": conv_woob(value=account.number),
                }
            )
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
                bank_repository.upload_transactions(
                    user_id,
                    [
                        Trac(
                            {
                                "id": (
                                    hash_id(transaction.label) % 12345678
                                    + hash_id(
                                        transaction.date.strftime("%Y-%m-%d %H:%M:%S")
                                    )
                                    % 213054
                                    + hash_id(str(transaction.amount)) % 65430
                                    if transaction.id == ""
                                    else transaction.id
                                ),
                                "account": core_account,
                                "amount": conv_woob(
                                    type="float", value=transaction.amount
                                ),
                                "category": conv_woob(value=transaction.category),
                                "date": conv_woob(type="date", value=transaction.date),
                                "label": conv_woob(value=transaction.label),
                                "type": tr_type[transaction.type],
                                "real_date": conv_woob(
                                    type="date", value=transaction.rdate
                                ),
                                "value_date": conv_woob(
                                    type="date", value=transaction.vdate
                                ),
                            }
                        )
                        for transaction in transactions
                    ],
                )

            if coming_transactions:
                bank_repository.upload_transactions(
                    user_id,
                    [
                        Trac(
                            {
                                "id": (
                                    hash_id(transaction.label) % 12345678
                                    + hash_id(
                                        transaction.date.strftime("%Y-%m-%d %H:%M:%S")
                                    )
                                    % 213054
                                    + hash_id(str(transaction.amount)) % 65430
                                    if transaction.id == ""
                                    else transaction.id
                                ),
                                "account": core_account,
                                "amount": conv_woob(
                                    type="float", value=transaction.amount
                                ),
                                "date": conv_woob(type="date", value=transaction.date),
                                "label": transaction.label,
                                "coming": True,
                            }
                        )
                        for transaction in coming_transactions
                        if transaction.label
                    ],
                )
    bank_repository.check_internal(user_id)
    user_repository.update_refreshed_user(user_id)
    return "refreshed"


@bp.route("/accounts/refresh_date")
@login_required
def refresh_date():
    date = user_repository.find_by_id(session["user_id"]).refreshed
    if date is None:
        return "unknown"
    return date


def conv_woob(value=None, type: str = None):
    value = (
        value
        if (not isinstance(value, NotLoadedType))
        and (not isinstance(value, NotAvailableType))
        else None
    )
    if value and type == "float":
        value = float(value)
    if value and type == "date":
        value = value.strftime("%Y-%m-%d %H:%M:%S")
    return value
