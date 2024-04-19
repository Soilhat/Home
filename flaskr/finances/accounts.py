import hashlib
import traceback
from datetime import datetime
from math import ceil

from flask import Blueprint, render_template, request, session
from woob.capabilities.bank.base import Account, Loan, Transaction
from woob.capabilities.base import NotAvailableType, NotLoadedType
from woob.core import Woob
from woob.core.bcall import CallErrors
from woob.exceptions import BrowserUnavailable

from flaskr.auth import login_required
from flaskr.db import executemany, get_db, get_user_db
from flaskr.finances.bank import get_banks

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
            "SELECT strftime('%Y-%m',Date) as date FROM 'transaction' ORDER BY Date DESC LIMIT 1"
        )
        month: dict = curr.fetchone()
        if month is None:
            month = datetime.today().strftime("%Y-%m")
        else:
            month = month[0]
    curr.execute(
        f"""SELECT COUNT(*)
        FROM 'transaction'
        WHERE strftime('%Y-%m',Date) = '{month}'"""
    )
    total = curr.fetchone()[0]
    query = f"""
        SELECT strftime('%Y-%m-%d',Date), bank, Category, Amount, trac.Label, trac.Type, CASE WHEN internal IS NOT NULL THEN 'TRUE' ELSE 'FALSE' END
        FROM 'transaction' trac
        JOIN account ON account.id = trac.account
        WHERE strftime('%Y-%m',Date) = '{month}'
        ORDER BY date DESC
        LIMIT {length}
        OFFSET {(curr_page-1)*length}
    """
    curr.execute(query)
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
                (
                    account.id,
                    account.backend,
                    account.label,
                    account_type[account.type],
                    conv_float(account.balance),
                    conv_float(account.coming),
                    account.iban,
                    account.number,
                )
                for account in accounts
            ]
            executemany(
                """
                REPLACE INTO account 
                    (id, bank, label, type, balance, coming, iban, number)
                VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                records,
            )

        if loans:
            print("Loading loans")

            records = [
                (
                    loan.id,
                    conv_float(loan.duration),
                    conv_float(loan.insurance_amount),
                    conv_date(loan.maturity_date),
                    conv_float(loan.nb_payments_left),
                    conv_float(loan.next_payment_amount),
                    conv_date(loan.next_payment_date),
                    conv_float(loan.rate),
                    conv_float(loan.total_amount),
                )
                for loan in loans
            ]
            executemany(
                """
                REPLACE INTO loan 
                    (id, duration, insurance_amount,
                    maturity_date, nb_payments_left, next_payment_amount,
                    next_payment_date, rate, total_amount)
                VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                records,
            )

        for account in accounts:
            print(f"Processing transactions : {account.label}")
            try:
                transactions: list[Transaction] = list(woob.iter_history(account))
                coming_transactions: list[Transaction] = list(woob.iter_coming(account))
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
                        UPDATE 'transaction'
                        SET id = ?, category = ?, date = ?, type = ?, 
                            value_date = ?, real_date = ?, coming = 0, label = ?
                        WHERE id <> ? AND account = ? AND amount = ? AND coming = 1 
                            AND ? BETWEEN DATE(date, '-7 days') AND DATE(date, '7 days')
                    """,
                    [
                        (
                            (
                                hash_id(tra.label) % 12345678
                                + hash_id(tra.date.strftime("%Y-%m-%d %H:%M:%S"))
                                % 213054
                                + hash_id(str(tra.amount)) % 65430
                                if tra.id == ""
                                else tra.id
                            ),
                            tra.category,
                            conv_date(tra.date),
                            tr_type[tra.type],
                            conv_date(tra.vdate),
                            conv_date(tra.rdate),
                            tra.label,
                            (
                                hash_id(tra.label) % 12345678
                                + hash_id(tra.date.strftime("%Y-%m-%d %H:%M:%S"))
                                % 213054
                                + hash_id(str(tra.amount)) % 65430
                                if tra.id == ""
                                else tra.id
                            ),
                            account.id,
                            conv_float(tra.amount),
                            conv_date(tra.date),
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
                        conv_float(transaction.amount),
                        transaction.category,
                        conv_date(transaction.date),
                        transaction.label,
                        tr_type[transaction.type],
                        conv_date(transaction.rdate),
                        conv_date(transaction.vdate),
                    )
                    for transaction in transactions
                ]
                executemany(
                    """
                        INSERT OR IGNORE INTO 'transaction' 
                            (id, account, amount,
                            category, date, label,
                            type, real_date, value_date)
                        VALUES 
                            (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        conv_float(transaction.amount),
                        (conv_date(transaction.date)),
                        transaction.label.replace("FACTURE CARTE ", ""),
                    )
                    for transaction in coming_transactions
                    if transaction.label
                ]
                if records:
                    print(f"Adding {len(records)} coming transactions")
                    executemany(
                        """
                            INSERT or IGNORE INTO 'transaction' 
                                (id, account, amount, date, label, coming)
                            VALUES 
                                (?, ?, ?, ?, ?, 1)
                        """,
                        records,
                    )

    check_internal()
    conn = get_user_db()
    curr = conn.cursor()
    curr.execute(f"""UPDATE user SET refreshed=NOW() WHERE id={session["user_id"]}""")
    conn.commit()
    return "refreshed"


@bp.route("/accounts/refresh_date")
@login_required
def refresh_date():
    conn = get_user_db()
    curr = conn.cursor()
    curr.execute(f"""SELECT refreshed FROM user WHERE id={session["user_id"]}""")
    date = curr.fetchone()[0]
    if date is None:
        return "unknown"
    return date.strftime("%Y-%m-%d")


def conv_float(value):
    return (
        float(value)
        if (not isinstance(value, NotLoadedType))
        and (not isinstance(value, NotAvailableType))
        else None
    )


def conv_date(value):
    return (
        value.strftime("%Y-%m-%d %H:%M:%S")
        if not isinstance(value, NotLoadedType)
        else None
    )


def check_internal():
    curr = get_db()[0]
    curr.execute(
        """
        SELECT 
            coming.id, exp.id
        FROM 'transaction' coming
        JOIN 'transaction' exp ON coming.amount + exp.amount = 0 AND NOT EXISTS (
            SELECT null from 'transaction' tmp
            WHERE coming.amount + tmp.amount = 0 
                AND tmp.date <= coming.date
                AND tmp.date > exp.date
        )
        AND (exp.date BETWEEN DATE(coming.date, '-7 days') AND DATE(coming.date, '7 days'))
        WHERE coming.amount > 0  AND coming.internal IS NULL AND exp.internal IS NULL
    """
    )
    internals = curr.fetchall()
    update_list = []
    for internal in internals:
        update_list.append((internal[0], internal[1]))
        update_list.append((internal[1], internal[0]))
    if update_list:
        print("Update Internal transactions...")
        executemany(
            """
            UPDATE 'transaction' set internal = ? WHERE id = ?
        """,
            update_list,
        )
