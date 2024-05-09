import re
from datetime import datetime
from typing import List

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db
from flaskr.finances.accounts import hash_id

bp = Blueprint("budget", __name__)


@bp.route("/budget")
@login_required
def index():
    month = request.args.get("month", None, type=str)  # format "YYYY-MM"
    curr = get_db()[0]
    if month is None:
        curr.execute(
            "SELECT strftime('%Y-%m',Date) as date FROM 'transaction' ORDER BY Date DESC LIMIT 1"
        )
        month: tuple = curr.fetchone()
        if month is None:
            month = datetime.today().strftime("%Y-%m")
        else:
            month = month[0]
    curr.execute("SELECT DISTINCT type FROM budget")
    budget_type = curr.fetchall()

    return render_template(
        "finances/budget.html",
        budget_type=budget_type,
        revenus=get_revenus(curr, month),
        summary=get_summary(curr, month),
        variables=get_variables(curr, month),
        fixed=get_fixed(curr, month),
        expenses=get_expenses(curr, month),
        spendings=get_spendings(curr, month),
        month=month,
        get_index=get_index,
        update_transac=update_transac_budget,
        format_remaining=format_remaining,
    )


@bp.route("/budgets")
@login_required
def bud_list():
    curr = get_db()[0]
    curr.execute(
        """
        SELECT * FROM budget
        WHERE (end IS NULL OR end >= DATE('now')) AND fixed = 0 AND type = "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    income_currents = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE (end IS NULL OR end >= DATE('now')) AND fixed = 0 AND type <> "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    var_currents = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE (end IS NULL OR end >= DATE('now')) AND fixed = 1 AND type <> "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    fixed_currents = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE end <= DATE('now') AND fixed = 0 AND type = "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    income_olds = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE end <= DATE('now') AND fixed = 0 AND type <> "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    var_olds = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE end <= DATE('now') AND fixed = 1 AND type <> "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    fixed_olds = curr.fetchall()
    curr.execute("SELECT DISTINCT type FROM budget")
    budget_type = curr.fetchall()

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


def get_budgeted_income(curr, month):
    curr.execute(
        f"""
        SELECT sum(budget.amount) as bedget
        FROM budget
        WHERE budget.type = 'Income' 
            AND ( start IS NULL OR strftime('%Y-%m',start) < '{month}')
            AND ( end IS NULL OR strftime('%Y-%m',end) > '{month}')
    """
    )
    return curr.fetchone()[0] or 0


def get_revenus(curr, month):
    revenus = f"""
        SELECT label, IFNULL(strftime('%Y-%m-%d',MAX(date)),'') as date, sum(amount) as 'real_amount', IFNULL(MAX(budget),0) as budget
        FROM (
            SELECT trac.label, trac.date, trac.amount, budget.amount as budget, CASE WHEN budget.label IS NULL THEN trac.label else budget.label END as budget_label
            FROM 'transaction' as trac
            INNER JOIN account as acc on trac.account=acc.id
            LEFT OUTER JOIN budget on Upper(trac.label) LIKE '%'||Upper(budget.label)||'%'
            WHERE acc.type = 'CHECKING' AND trac.amount > 0 AND strftime('%Y-%m',Date) = '{month}'
		        AND (budget.type = 'Income' OR budget.type IS NULL)
                AND trac.internal IS NULL
        UNION ALL
            SELECT DISTINCT budget.label, '' as date, 0 as 'real', budget.amount as budget, CASE WHEN budget.label IS NULL THEN trac.label else budget.label END as budget_label
            FROM budget
            LEFT JOIN 'transaction' as trac on Upper(trac.label) LIKE '%'||Upper(budget.label)||'%'
            WHERE (trac.id IS NULL OR strftime('%Y-%m',Date) <> '{month}')
		        AND (budget.type = 'Income' OR budget.type IS NULL) 
                AND ( start IS NULL OR strftime('%Y-%m',start) <= '{month}')
                AND ( end IS NULL OR (strftime('%Y-%m',end) >= '{month}'))
        )a
        GROUP BY budget_label
    """
    curr.execute(
        f"""
        {revenus}
    UNION ALL
        select 'Total' label,
            '' date,
            IFNULL(sum(real_amount),0) as 'real_amount',
            IFNULL(sum(budget),0) as budget
        FROM (
            {revenus}
	    )s
    """
    )
    return curr.fetchall()


def get_summary(curr, month):
    query = f"""
        SELECT type, IFNULL(abs(sum(budget))*100/{get_budgeted_income(curr, month)},0) as '%', sum(budget) as budget, abs(sum(real_amount)) as 'real_amount'
        FROM (
            SELECT type, sum(amount) as 'real_amount', sum(budget)  as budget
            FROM (
                SELECT IFNULL(budget.type, fixed_bud.type) as type, trac.amount, 0 as budget
                FROM 'transaction' as trac
                INNER JOIN account as acc on trac.account=acc.id
                LEFT OUTER JOIN budget on budget.id = trac.budget_id AND strftime('%Y-%m',trac.Date) = '{month}'
                LEFT OUTER JOIN budget as fixed_bud on trac.label LIKE '%'||fixed_bud.label||'%' AND strftime('%Y-%m',trac.Date) = '{month}'
                LEFT OUTER JOIN 'transaction' as child ON LTRIM(child.parent,'0') = LTRIM(trac.id,'0')
                WHERE strftime('%Y-%m',trac.Date) = '{month}'
                    AND (budget.type <> 'Income' OR budget.type IS NULL)
                    AND trac.amount < 0
                    AND trac.internal IS NULL
                    AND trac.saving_id IS NULL
                    AND child.id IS NULL
		        GROUP BY trac.id
            UNION ALL
                SELECT budget.type, 0.0 as 'real_amount', budget.amount as budget
                FROM budget
                WHERE ( start IS NULL OR (strftime('%Y-%m',start) <= '{month}'))
                    AND ( end IS NULL OR (strftime('%Y-%m',end) >= '{month}'))
                    AND (type <> 'Income' OR type IS NULL)
            )labels
            GROUP BY type
        )type_table
        GROUP BY type
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select 'Total' type,
                IFNULL(abs(sum(budget))*100/{get_budgeted_income(curr, month)},0) as '%',
                sum(budget) as budget,
                sum(real_amount) as 'real_amount'
            FROM (
                {query}
            )s
    """
    )
    return curr.fetchall()


def get_expenses(curr, month):
    query = f"""
        SELECT LTRIM(trac.id,'0') as id, trac.label, account.bank, strftime('%Y-%m-%d',trac.date) as date, abs(trac.amount) as amount, 
            CASE 
                WHEN trac.saving_id is NOT NULL THEN 'Saving - '||saving.name
                WHEN trac.budget_id is NOT NULL THEN budget.label
                WHEN child.id IS NOT NULL THEN 'Split'
                ELSE ''
            END budget,
            '' as edit
	    FROM 'transaction' as trac
        LEFT OUTER JOIN budget fix on trac.label LIKE '%'||fix.label||'%'
        LEFT JOIN budget on trac.budget_id = budget.id
        LEFT JOIN saving on trac.saving_id = saving.id
        LEFT OUTER JOIN account on trac.account = account.id
        LEFT OUTER JOIN 'transaction' child on LTRIM(child.parent,'0') = LTRIM(trac.id,'0')
        WHERE 
            trac.amount < 0
            AND strftime('%Y-%m',trac.Date) = '{month}'
            AND trac.internal IS NULL
            AND fix.label IS NULL
            AND trac.parent IS NULL
		GROUP BY trac.id
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select '' as id, 'Total' label, '' as bank, '' as 'date', 
                IFNULL(sum(amount),0) as amount,
                '' as 'budget', '' as edit
            FROM (
                {query}
            )s
        ORDER BY date DESC, amount desc
    """
    )
    return curr.fetchall()


def get_variables(curr, month):
    month = f"{month}-01"
    query = f"""
        SELECT budget.label, budget.amount as budget, IFNULL(abs(sum(trac.amount)),0) as 'real_amount', 
            budget.amount * (
				CASE WHEN strftime('%Y-%m',Date('now')) = strftime('%Y-%m','{month}')
					THEN CAST(strftime('%d',DATE('now'))AS FLOAT)/CAST(strftime('%d',DATE(DATE('now'), 'start of month', '+1 month', '-1 day'))AS FLOAT)
					ELSE 1 END
				)-(IFNULL(abs(sum(trac.amount)),0))
        remaining_prct, budget.type
        FROM budget
        LEFT JOIN 'transaction' as trac on budget.id = trac.budget_id AND strftime('%Y-%m',Date) = strftime('%Y-%m','{month}')
        WHERE  ( start IS NULL OR start < '{month}')
            AND ( end IS NULL OR end > '{month}')
            AND budget.fixed = 0
            AND (budget.type <> 'Income' OR budget.type IS NULL)
        GROUP BY budget.label, budget.type
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select 'Total' label,
                IFNULL(sum(budget),0) as budget,
                IFNULL(sum(real_amount),0) as 'real_amount',
                '' as remaining_prct,
                '' as type
            FROM (
                {query}
            )s
    """
    )
    return curr.fetchall()


def get_fixed(curr, month):
    """Retrieve Fixed monthly budgeted 'transaction's"""
    month = f"{month}-01"
    query = f"""
        SELECT budget.label, IFNULL(GROUP_CONCAT(bank, ','),''), IFNULL(strftime('%Y-%m-%d',trac.Date),'') as date, budget.amount as budget, IFNULL(abs(sum(trac.amount)),0) as 'real_amount', budget.type
        FROM budget
        LEFT JOIN 'transaction' as trac on trac.label LIKE '%'||budget.label||'%'
            AND strftime('%Y-%m',Date) = strftime('%Y-%m','{month}')
            AND trac.amount <= 0
        LEFT OUTER JOIN account on account.id = trac.account
        WHERE  ( start IS NULL OR start <= '{month}')
            AND ( end IS NULL OR end >= '{month}')
            AND budget.fixed = 1
            AND (budget.type <> 'Income' OR budget.type IS NULL)
        GROUP BY budget.label, budget.type
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select 'Total' label,
                '' as bank,
                '' as date,
                IFNULL(sum(budget),0) as budget,
                IFNULL(sum(real_amount),0) as 'real_amount',
                '' as type
            FROM (
                {query}
            )s
    """
    )
    return curr.fetchall()


def get_spendings(curr, month):
    curr.execute(
        f"""
            SELECT budget.label
            FROM budget
            WHERE budget.type <> 'Income' AND budget.fixed = 0
                AND ( start IS NULL OR strftime('%Y-%m',start) <= '{month}')
                AND ( end IS NULL OR strftime('%Y-%m',end) >= '{month}')
        UNION ALL
            SELECT "Saving - "||name
            FROM saving
    """
    )
    result = ["", "Split"]
    return [spending[0] for spending in curr.fetchall()] + result


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
        curr, conn = get_db()
        curr.execute(
            "UPDATE budget SET label = ?, amount = ?, type = ?, start = ?, end = ?, fixed = ?"
            " WHERE id = ?",
            (label, amount, budget_type, start, end, fixed, id),
        )
        conn.commit()
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
        spendings=get_spendings(curr, str(item[3]).split("-")[1]),
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
    curr, conn = get_db()
    if budget.startswith("Saving"):
        budget_table = "saving"
        budget_column = "saving_id"
        compare = "'Saving - '||saving.name"
    else:
        budget_table = "budget"
        budget_column = "budget_id"
        compare = "budget.label"

    curr.execute(f""" SELECT id FROM {budget_table} WHERE {compare} = ?""", (budget,))
    budget_id = curr.fetchone()
    curr.execute(
        f"""UPDATE 'transaction' SET {budget_column} = ? WHERE id LIKE '%'||?""",
        (budget_id[0], id),
    )
    conn.commit()
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
