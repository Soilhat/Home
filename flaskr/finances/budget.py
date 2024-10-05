import re
from typing import List

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db
from flaskr.extensions import bank_repository
from flaskr.finances.accounts import hash_id

bp = Blueprint("budget", __name__)


@bp.route("/budget")
@login_required
def index():
    month = request.args.get("month", None, type=str)  # format "YYYY-MM"
    user_id = session.get("user_id")
    if month is None:
        month = bank_repository.get_last_month(user_id)
    budget_type = bank_repository.get_budget_types(user_id)

    return render_template(
        "finances/budget.html",
        budget_type=budget_type,
        revenus=bank_repository.get_revenus(user_id, month),
        summary=bank_repository.get_summary(user_id, month),
        variables=bank_repository.get_budgeted_transactions(user_id, month),
        fixed=bank_repository.get_budgeted_transactions(user_id, month, True),
        expenses=bank_repository.get_expenses(user_id, month),
        spendings=bank_repository.get_spendings(user_id, month),
        month=month,
        get_index=get_index,
        update_transac=update_transac_budget,
        format_remaining=format_remaining,
    )


@bp.route("/budgets")
@login_required
def bud_list():
    user_id = session["user_id"]
    income_currents = bank_repository.get_budget(
        user_id, current=True, fixed=False, income=True
    )
    var_currents = bank_repository.get_budget(
        user_id, current=True, fixed=False, income=False
    )
    fixed_currents = bank_repository.get_budget(
        user_id, current=True, fixed=True, income=False
    )
    income_olds = bank_repository.get_budget(
        user_id, current=False, fixed=False, income=True
    )
    var_olds = bank_repository.get_budget(
        user_id, current=False, fixed=False, income=False
    )
    fixed_olds = bank_repository.get_budget(
        user_id, current=False, fixed=True, income=False
    )
    budget_type = bank_repository.get_budget_types(user_id)

    return render_template(
        "finances/budgets.html",
        var_currents=var_currents,
        fixed_currents=fixed_currents,
        var_olds=var_olds,
        fixed_olds=fixed_olds,
        budget_type=budget_type,
        income_currents=income_currents,
        income_olds=income_olds,
    )


def get_index(row, columns, index):
    return row[
        columns.index(
            next(filter(lambda x: x["name"] == columns[index]["index"], columns))
        )
    ]


@bp.route("/budget/create", methods=("POST",))
@login_required
def create():
    label = request.form["label"]
    amount = request.form["amount"]
    budget_type = request.form["type"]
    start = request.form["start"] if request.form["start"] != "" else None
    end = request.form["end"] if request.form["end"] != "" else None
    fixed = ("fixed" in request.form) and (request.form["fixed"] == "on")
    error = None

    if not label:
        error = "Label is required."

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            "INSERT INTO budget (label, amount, type, start, end, fixed)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (label, amount, budget_type, start, end, fixed),
        )
        conn.commit()
        return redirect(url_for("finances.budget.bud_list"))


@bp.route("/budget/<int:id>", methods=("POST",))
@login_required
def update(id):
    label = request.form["label"] if request.form["label"] != "" else None
    amount = float(request.form["amount"])
    budget_type = request.form["type"]
    start = request.form["start"] if request.form["start"] != "" else None
    end = request.form["end"] if request.form["end"] != "" else None
    fixed = request.form["fixed"] == "on"
    error = None

    if not label:
        error = "Label is required."

    if error is not None:
        flash(error)
    else:
        bank_repository.update_budget(
            session["user_id"], label, amount, budget_type, start, end, fixed, id
        )
        return redirect(url_for("finances.budget.bud_list"))


def get_budget(id):
    curr = get_db()[0]
    curr.execute("SELECT * FROM budget WHERE id = ?", (id,))
    saving = curr.fetchone()

    if saving is None:
        abort(404, f"Budget id {id} doesn't exist.")

    return saving


@bp.route("/trac/<string:id>")
@login_required
def get_trac(id):
    curr, conn = get_db()
    query = f"""
        SELECT LTRIM(trac.id,'0') as id, trac.label, abs(trac.amount) as amount, 
            CASE 
                WHEN saving_id is NOT NULL THEN 'Saving - '||saving.name
                WHEN budget_id is NOT NULL THEN budget.label
                ELSE ''
            END budget
	    FROM 'transaction' as trac
        LEFT OUTER JOIN budget fix on trac.label LIKE '%'||fix.label||'%'
        LEFT JOIN budget on trac.budget_id = budget.id
        LEFT JOIN saving on trac.saving_id = saving.id
        WHERE LTRIM(trac.parent,'0') = LTRIM('{id}','0')
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select '' as id, 'Total' label, 
                abs(sum(amount)) as amount,
                '' as 'budget'
            FROM (
                {query}
            )s
    """
    )
    transac = curr.fetchall()
    curr.execute(
        """
            SELECT LTRIM(trac.id,'0'), bank,abs(trac.amount), strftime('%Y-%m-%d',date) as date, trac.label,
                CASE 
                    WHEN saving_id is NOT NULL THEN 'Saving - '|| saving.name
                    WHEN budget_id is NOT NULL THEN budget.label
                    ELSE NULL
                END budget,
                comment
            FROM 'transaction' trac
            LEFT JOIN account ON trac.account = account.id
            LEFT JOIN budget on trac.budget_id = budget.id
            LEFT JOIN saving on trac.saving_id = saving.id
            WHERE LTRIM(trac.id,'0') = ?
        """,
        (id,),
    )
    item = curr.fetchone()
    return render_template(
        "finances/transaction_id.html",
        item=item,
        transac=transac,
        spendings=bank_repository.get_spendings(
            session["user_id"], str(item[3]).split("-")[1]
        ),
        get_index=get_index,
    )


@bp.route("/budget/<int:id>", methods=("DELETE",))
@login_required
def delete(id):
    get_budget(id)
    curr, conn = get_db()
    curr.execute("DELETE FROM budget WHERE id = ?", (id,))
    conn.commit()
    return redirect(url_for("finances.budget.index"))


@bp.route("/transac/<int:id>/budget", methods=("POST",))
@login_required
def update_transac_budget(id):
    budget: str = request.get_json()
    bank_repository.update_trac(session["user_id"], id, budget)
    return index()


@bp.route("/transac/<string:id>/comment", methods=("POST",))
@login_required
def update_transac_comment(id):
    transactions: dict = request.values.dicts[1].to_dict()
    comment = transactions.pop("comment")
    curr, conn = get_db()
    if comment:
        curr.execute(
            """UPDATE 'transaction' SET comment = ? WHERE id LIKE '%'||?""",
            (comment, id),
        )
    if transactions:
        tracs: List[dict] = []
        for key, value in transactions.items():
            trac_ind = re.findall(r"\d+", key)[0]
            column = key.replace(trac_ind, "")
            element = {column: value}
            if len(tracs) < int(trac_ind):
                tracs.append(element)
            else:
                tracs[int(trac_ind) - 1].update(element)
        curr.execute(f"DELETE FROM 'transaction' WHERE parent = {id}")
        for trac in tracs:
            budget = trac["Budget"]
            budget_column = "budget_id"
            if budget:
                if budget.startswith("Saving"):
                    budget_table = "saving"
                    budget_column = "saving_id"
                    compare = "'Saving - '||saving.name"
                else:
                    budget_table = "budget"
                    budget_column = "budget_id"
                    compare = "budget.label"
                curr.execute(
                    f""" SELECT id FROM {budget_table} WHERE {compare} = ?""",
                    (budget,),
                )
                budget_id = curr.fetchone()[0]
            curr.execute(
                "SELECT date, account FROM 'transaction' WHERE LTRIM(id,'0') =?", (id,)
            )
            date, account = curr.fetchone()
            curr.execute(
                f"""
                INSERT INTO 'transaction' (id, label, amount, date, account, parent,{budget_column})
                VALUES (?, ?, -?, ?, ?, ?, ?)
            """,
                (
                    hash_id(trac["Label"]) % 12345678
                    + hash_id(str(id)) % 213054
                    + hash_id(str(trac["Amount"])) % 65430,
                    trac["Label"],
                    trac["Amount"],
                    date,
                    account,
                    str(id),
                    budget_id if budget else None,
                ),
            )
    conn.commit()
    return redirect(url_for("finances.budget.index"))


def format_remaining(row, cell_id):
    if row[cell_id] == "":
        return ""
    if float(row[cell_id]) > 0:
        return "color:green"
    return "color:var(--red)"
