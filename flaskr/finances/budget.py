from flask import Blueprint, request, render_template, flash, redirect, url_for
from werkzeug.exceptions import abort
import re
from typing import List
from flaskr.finances.accounts import hash_id

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("budget", __name__)

internal_trac = [
    "MME SOILHAT MOHAMED",
    "VIREMENT EN VOTRE FAVEUR DE MONTEIRO ARTHUR",
    "MONTEIRO ARTHUR",
    "MOHAMED SOILHAT",
    "MOHAMED SOILHAT.+",
    "VIE COMMUNE",
    "VIE COMMUNE.+",
    "EPARGNE",
    "FACTURES",
    "VR.PERMANENT FACTURES",
    "VIREMENT EMIS WEB Compte joint",
    "VR.PERMANENT EPARGNE",
    "VIREMENT EMIS WEB MONTEIRO ARTHUR OU",
    "VIREMENT EMIS WEB MONTEIRO ARTHUR",
    "MLE MOHAMED SOILHAT",
]


@bp.route("/budget")
@login_required
def index():
    month = request.args.get("month", None, type=str)  # format "YYYY-MM"
    curr = get_db()[0]
    if month is None:
        curr.execute(
            "SELECT date_format(Date,'%Y-%m') FROM transaction ORDER BY Date DESC LIMIT 1"
        )
        month = curr.fetchone()[0]
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
        WHERE (end IS NULL OR end >= CURDATE()) AND fixed = 0 AND type = "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    income_currents = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE (end IS NULL OR end >= CURDATE()) AND fixed = 0 AND type <> "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    var_currents = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE (end IS NULL OR end >= CURDATE()) AND fixed = 1 AND type <> "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    fixed_currents = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE end <= CURDATE() AND fixed = 0 AND type = "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    income_olds = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE end <= CURDATE() AND fixed = 0 AND type <> "Income"
        ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc
    """
    )
    var_olds = curr.fetchall()
    curr.execute(
        """
        SELECT * FROM budget
        WHERE end <= CURDATE() AND fixed = 1 AND type <> "Income"
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
        SELECT sum(budget.amount)
        FROM budget
        WHERE budget.type = 'Income' 
            AND ( start IS NULL OR date_format(start,'%Y-%m') < '{month}')
            AND ( end IS NULL OR date_format(end,'%Y-%m') > '{month}')
    """
    )
    return curr.fetchone()[0]


def get_revenus(curr, month):
    revenus = f"""
        SELECT label, MAX(date) as date, to_currency(sum(amount)) as 'real_amount', MAX(budget) as budget
        FROM (
            SELECT trac.label, trac.date, trac.amount, to_currency(budget.amount) as budget, CASE WHEN budget.label IS NULL THEN trac.label else budget.label END as budget_label
            FROM transaction as trac
            INNER JOIN account as acc on trac.account=acc.id
            LEFT OUTER JOIN budget on Upper(trac.label) LIKE CONCAT('%',  Upper(budget.label), '%')
            WHERE acc.type = 'CHECKING' AND trac.amount > 0 AND date_format(Date,'%Y-%m') = '{month}'
		        AND (budget.type = 'Income' OR budget.type IS NULL)
                AND trac.label NOT REGEXP '^{"$|^".join(internal_trac)}$'
        UNION ALL
            SELECT DISTINCT budget.label, '' as date, to_currency(0) as 'real', to_currency(budget.amount) as budget, CASE WHEN budget.label IS NULL THEN trac.label else budget.label END as budget_label
            FROM budget
            LEFT JOIN transaction as trac on Upper(trac.label) LIKE CONCAT('%',  Upper(budget.label), '%')
            WHERE (trac.id IS NULL OR date_format(Date,'%Y-%m') <> '{month}')
		        AND (budget.type = 'Income' OR budget.type IS NULL) 
                AND ( start IS NULL OR date_format(start,'%Y-%m') <= '{month}')
                AND ( end IS NULL OR (date_format(end,'%Y-%m') >= '{month}'))
        )a
        GROUP BY budget_label
    """
    curr.execute(
        f"""
        {revenus}
    UNION ALL
        select 'Total' label,
            '' date,
            to_currency(sum(CAST(REPLACE(REPLACE(real_amount,'€',''),',','.') as DECIMAL(9,2)))) as 'real_amount',
            to_currency(sum(CAST(REPLACE(REPLACE(budget,'€',''),',','.') as DECIMAL(9,2)))) as budget
        FROM (
            {revenus}
	    )s
    """
    )
    return curr.fetchall()


def get_summary(curr, month):
    query = f"""
        SELECT type, to_prct(abs(sum(budget))*100/{get_budgeted_income(curr, month)}) as '%', to_currency(sum(budget))  as budget, to_currency(abs(sum(real_amount))) as 'real_amount'
        FROM (
            SELECT type, sum(amount) as 'real_amount', sum(budget)  as budget
            FROM (
                SELECT IFNULL(budget.type, fixed_bud.type) as type, trac.amount, 0 as budget
                FROM transaction as trac
                INNER JOIN account as acc on trac.account=acc.id
                LEFT OUTER JOIN budget on budget.id = trac.budget_id AND date_format(trac.Date,'%Y-%m') = '{month}'
                LEFT OUTER JOIN budget as fixed_bud on trac.label LIKE CONCAT('%',fixed_bud.label,'%') AND date_format(trac.Date,'%Y-%m') = '{month}'
                LEFT OUTER JOIN transaction as child ON child.parent = trac.id
                WHERE date_format(trac.Date,'%Y-%m') = '{month}'
                    AND (budget.type <> 'Income' OR budget.type IS NULL)
                    AND trac.amount < 0
                    AND trac.label NOT REGEXP '^{"$|^".join(internal_trac)}$'
                    AND trac.saving_id IS NULL
                    AND child.id IS NULL
		        GROUP BY trac.id
            UNION ALL
                SELECT budget.type, 0.0 as 'real_amount', budget.amount as budget
                FROM budget
                WHERE ( start IS NULL OR (date_format(start,'%Y-%m') <= '{month}'))
                    AND ( end IS NULL OR (date_format(end,'%Y-%m') >= '{month}'))
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
                to_prct(abs(sum(budget))*100/{get_budgeted_income(curr, month)}) as '%',
                to_currency(sum(CAST(REPLACE(REPLACE(budget,'€',''),',','.') as DECIMAL(9,2)))) as budget,
                to_currency(abs(sum(CAST(REPLACE(REPLACE(real_amount,'€',''),',','.') as DECIMAL(9,2))))) as 'real_amount'
            FROM (
                {query}
            )s
    """
    )
    return curr.fetchall()


def get_expenses(curr, month):
    query = f"""
        SELECT TRIM(LEADING '0' FROM trac.id) as id, trac.label, account.bank, trac.date, to_currency(abs(trac.amount)) as amount, 
            CASE 
                WHEN trac.saving_id is NOT NULL THEN concat('Saving - ',saving.name)
                WHEN trac.budget_id is NOT NULL THEN budget.label
                WHEN child.id IS NOT NULL THEN 'Split'
                ELSE ''
            END budget,
            '' as edit
	    FROM transaction as trac
        LEFT OUTER JOIN budget fix on trac.label LIKE CONCAT('%', fix.label ,'%')
        LEFT JOIN budget on trac.budget_id = budget.id
        LEFT JOIN saving on trac.saving_id = saving.id
        LEFT OUTER JOIN account on trac.account = account.id
        LEFT OUTER JOIN transaction child on child.parent = trac.id
        WHERE 
            trac.amount < 0
            AND date_format(trac.Date,'%Y-%m') = '{month}'
            AND trac.label NOT REGEXP '^{"$|^".join(internal_trac)}$'
            AND fix.label IS NULL
            AND trac.parent IS NULL
		GROUP BY trac.id
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select '' as id, 'Total' label, '' as bank, '' as 'date', 
                to_currency(abs(sum(
                    CAST(REPLACE(REPLACE(amount,'€',''),',','.') as DECIMAL(9,2))
                ))) as amount,
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
        SELECT budget.label, to_currency(budget.amount) as budget, to_currency(abs(sum(trac.amount))) as 'real_amount', 
            to_currency(budget.amount * (IF(date_format(curdate(),'%Y-%m') = date_format('{month}','%Y-%m'), DAYOFMONTH(curdate())/DAYOFMONTH(LAST_DAY(curdate())), 1)-(IFNULL(abs(sum(trac.amount)/ budget.amount),0))))
        remaining_prct, budget.type
        FROM budget
        LEFT JOIN transaction as trac on budget.id = trac.budget_id AND date_format(Date,'%Y-%m') = date_format('{month}','%Y-%m')
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
                to_currency(abs(sum(CAST(REPLACE(REPLACE(budget,'€',''),',','.') as DECIMAL(9,2))))) as budget,
                to_currency(abs(sum(CAST(REPLACE(REPLACE(real_amount,'€',''),',','.') as DECIMAL(9,2))))) as 'real_amount',
                '' as remaining_prct,
                '' as type
            FROM (
                {query}
            )s
    """
    )
    return curr.fetchall()


def get_fixed(curr, month):
    """Retrieve Fixed monthly budgeted transactions"""
    month = f"{month}-01"
    query = f"""
        SELECT budget.label, IFNULL(trac.Date,'') as date, to_currency(budget.amount) as budget, to_currency(abs(sum(trac.amount))) as 'real_amount', budget.type
        FROM budget
        LEFT JOIN transaction as trac on trac.label LIKE CONCAT('%', budget.label ,'%') AND date_format(Date,'%Y-%m') = date_format('{month}','%Y-%m')
        WHERE  ( start IS NULL OR start <= '{month}')
            AND ( end IS NULL OR end >= '{month}')
            AND budget.fixed = 1
            AND (budget.type <> 'Income' OR budget.type IS NULL)
            AND (trac.amount <= 0 OR trac.amount IS NULL)
        GROUP BY budget.label, budget.type
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select 'Total' label,
                '' as date,
                to_currency(abs(sum(CAST(REPLACE(REPLACE(budget,'€',''),',','.') as DECIMAL(9,2))))) as budget,
                to_currency(abs(sum(CAST(REPLACE(REPLACE(real_amount,'€',''),',','.') as DECIMAL(9,2))))) as 'real_amount',
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
        (
            SELECT budget.label
            FROM budget
            WHERE budget.type <> 'Income' AND budget.fixed = 0
                AND ( start IS NULL OR date_format(start,'%Y-%m') <= '{month}')
                AND ( end IS NULL OR date_format(end,'%Y-%m') >= '{month}')
        )
        UNION ALL
        (
            SELECT CONCAT("Saving - ",name)
            FROM saving
        )
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
    fixed = request.form["fixed"] == "on"
    error = None

    if not label:
        error = "Label is required."

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            "INSERT INTO budget (label, amount, type, start, end, fixed)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
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
            "UPDATE budget SET label = %s, amount = %s, type = %s, start = %s, end = %s, fixed = %s"
            " WHERE id = %s",
            (label, amount, budget_type, start, end, fixed, id),
        )
        conn.commit()
        return redirect(url_for("finances.budget.bud_list"))


def get_budget(id):
    curr = get_db()[0]
    curr.execute("SELECT * FROM budget WHERE id = %s", (id,))
    saving = curr.fetchone()

    if saving is None:
        abort(404, f"Budget id {id} doesn't exist.")

    return saving


@bp.route("/trac/<int:id>")
@login_required
def get_trac(id):
    curr, conn = get_db()
    query = f"""
        SELECT TRIM(LEADING '0' FROM trac.id) as id, trac.label, abs(trac.amount) as amount, 
            CASE 
                WHEN saving_id is NOT NULL THEN concat('Saving - ',saving.name)
                WHEN budget_id is NOT NULL THEN budget.label
                ELSE ''
            END budget
	    FROM transaction as trac
        LEFT OUTER JOIN budget fix on trac.label LIKE CONCAT('%', fix.label ,'%')
        LEFT JOIN budget on trac.budget_id = budget.id
        LEFT JOIN saving on trac.saving_id = saving.id
        WHERE trac.parent = {id}
    """
    curr.execute(
        f"""
            {query}
        UNION ALL
            select '' as id, 'Total' label, 
                to_currency(abs(sum(
                    CAST(REPLACE(REPLACE(amount,'€',''),',','.') as DECIMAL(9,2))
                ))) as amount,
                '' as 'budget'
            FROM (
                {query}
            )s
    """
    )
    transac = curr.fetchall()
    curr.execute(
        """
            SELECT trac.id, bank,to_currency(abs(trac.amount)), date, trac.label,
                CASE 
                    WHEN saving_id is NOT NULL THEN concat('Saving - ',saving.name)
                    WHEN budget_id is NOT NULL THEN budget.label
                    ELSE NULL
                END budget,
                comment
            FROM transaction trac
            LEFT JOIN account ON trac.account = account.id
            LEFT JOIN budget on trac.budget_id = budget.id
            LEFT JOIN saving on trac.saving_id = saving.id
            WHERE trac.id = %s
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
    curr.execute("DELETE FROM budget WHERE id = %s", (id,))
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
        compare = "concat('Saving - ',saving.name)"
    else:
        budget_table = "budget"
        budget_column = "budget_id"
        compare = "budget.label"

    curr.execute(f""" SELECT id FROM {budget_table} WHERE {compare} = %s""", (budget,))
    budget_id = curr.fetchone()
    curr.execute(
        f"""UPDATE transaction SET {budget_column} = %s WHERE id LIKE '%%s'""",
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
            """UPDATE transaction SET comment = %s WHERE id LIKE '%%s'""",
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
        curr.execute(f"DELETE FROM transaction WHERE parent = {id}")
        for trac in tracs:
            budget = trac["Budget"]
            budget_column = "budget_id"
            if budget:
                if budget.startswith("Saving"):
                    budget_table = "saving"
                    budget_column = "saving_id"
                    compare = "concat('Saving - ',saving.name)"
                else:
                    budget_table = "budget"
                    budget_column = "budget_id"
                    compare = "budget.label"
                curr.execute(
                    f""" SELECT id FROM {budget_table} WHERE {compare} = %s""",
                    (budget,),
                )
                budget_id = curr.fetchone()[0]
            curr.execute("SELECT date, account FROM transaction WHERE id=%s", (id,))
            date, account = curr.fetchone()
            curr.execute(
                f"""
                INSERT INTO transaction (id, label, amount, date, account, parent,{budget_column})
                VALUES (%s, %s, -%s, %s, %s, %s, %s)
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
    return index()


def format_remaining(row, cell_id):
    if row[cell_id] == "":
        return ""
    cell = row[cell_id].replace("€", "")
    cell = cell.replace(" ", "")
    cell = cell.replace(",", ".")
    if float(cell) > 0:
        return "color:green"
    return "color:var(--red)"
