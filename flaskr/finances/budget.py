from flask import (
    Blueprint, request, render_template, flash, redirect, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('budget', __name__)

internal_trac = [
    'MME SOILHAT MOHAMED',
    'VIREMENT EN VOTRE FAVEUR DE MONTEIRO ARTHUR',
    'MONTEIRO ARTHUR',
    'MOHAMED SOILHAT',
    'VIE COMMUNE',
    '00003310727 ECHEANCE',
    'EPARGNE',
    'FACTURES'
]

@bp.route('/budget')
@login_required
def index():
    month = request.args.get('month', None, type=str) # format "YYYY-MM"
    curr = get_db()[0]
    if month is None:
        curr.execute("SELECT date_format(Date,'%Y-%m') FROM transaction ORDER BY Date DESC LIMIT 1")
        month = curr.fetchone()[0]
    curr.execute("SELECT DISTINCT type FROM budget")
    budget_type = curr.fetchall()

    return render_template(
        'finances/budget.html',
        budget_type = budget_type,
        revenus = get_revenus(curr, month),
        summary = get_summary(curr, month),
        variables = get_variables(curr, month),
        expenses = get_expenses(curr, month),
        loans= get_loans(curr, month),
        spendings= get_spendings(curr),
        month = month,
        get_index=get_index,
        update_transac=update_transac
    )


def get_index(row, columns, index):
    return row[columns.index(next(filter(lambda x: x['name'] == columns[index]["index"], columns)))]

def get_budgeted_income(curr, month):
    curr.execute(f"""
        SELECT sum(budget.amount)
        FROM budget
        WHERE budget.type = 'Income' 
            AND ( start IS NULL OR start < '{month}')
            AND ( end IS NULL OR end > '{month}')
    """)
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
                AND trac.label NOT REGEXP '{"|".join(internal_trac)}'
        UNION ALL
            SELECT DISTINCT budget.label, '' as date, to_currency(0) as 'real', to_currency(budget.amount) as budget, CASE WHEN budget.label IS NULL THEN trac.label else budget.label END as budget_label
            FROM budget
            LEFT JOIN transaction as trac on Upper(trac.label) LIKE CONCAT('%',  Upper(budget.label), '%')
            WHERE (trac.id IS NULL OR date_format(Date,'%Y-%m') <> '{month}')
		        AND (budget.type = 'Income' OR budget.type IS NULL) 
                AND ( start IS NULL OR (YEAR(start) <= {int(month[0:4])} AND MONTH(start) <={int(month[6:7])}))
                AND ( end IS NULL OR (YEAR(end) >= {int(month[0:4])} AND MONTH(end) <={int(month[6:7])}))
        )a
        GROUP BY budget_label
    """
    curr.execute(f"""
        {revenus}
    UNION ALL
        select 'Total' label, '' date, to_currency(sum(real_amount)) as 'real_amount', to_currency(sum(budget)) as budget
        FROM (
            {revenus}
	    )s
    """)
    return curr.fetchall()

def get_summary(curr, month):
    query = f"""
        SELECT type, to_prct(abs(sum(budget))*100/{get_budgeted_income(curr, month)}) as '%', to_currency(sum(budget))  as budget, to_currency(abs(sum(real_amount))) as 'real_amount'
        FROM (
            SELECT type, to_currency(sum(amount)) as 'real_amount', sum(budget)  as budget
            FROM (
                SELECT budget.type, trac.amount, 0 as budget
                FROM transaction as trac
                INNER JOIN account as acc on trac.account=acc.id
                LEFT OUTER JOIN budget on budget.label = trac.budget AND date_format(Date,'%Y-%m') = '{month}'
                WHERE date_format(Date,'%Y-%m') = '{month}'
                    AND (budget.type <> 'Income' OR budget.type IS NULL)
                    AND trac.amount < 0
                    AND trac.Type <> 'TYPE_LOAN_PAYMENT'
                    AND trac.label NOT REGEXP '{"|".join(internal_trac)}'
            UNION ALL
                SELECT budget.type, 0 as 'real_amount', budget.amount as budget
                FROM budget
                WHERE ( start IS NULL OR (YEAR(start) <= {int(month[0:4])} AND MONTH(start) <={int(month[6:7])}))
                    AND ( end IS NULL OR (YEAR(end) >= {int(month[0:4])} AND MONTH(end) <={int(month[6:7])}))
                    AND (type <> 'Income' OR type IS NULL)
            )labels
            GROUP BY type
        )type_table
        GROUP BY type
    """
    curr.execute(f"""
            {query}
        UNION ALL
            select 'Total' type, to_prct(abs(sum(budget))*100/{get_budgeted_income(curr, month)}) as '%', to_currency(sum(budget)) as budget, to_currency(abs(sum(real_amount))) as 'real_amount'
            FROM (
                {query}
            )s
    """)
    return curr.fetchall()

def get_expenses(curr, month):
    query = f"""
        SELECT TRIM(LEADING '0' FROM trac.id) as id, trac.label, trac.date, to_currency(abs(trac.amount)) as amount, IFNULL(budget,'') as budget
	    FROM transaction as trac
        WHERE trac.amount < 0 AND date_format(Date,'%Y-%m') = '{month}' AND Type <> 'TYPE_LOAN_PAYMENT' AND trac.label NOT REGEXP '{"|".join(internal_trac)}'
    """
    curr.execute(f"""
            {query}
        UNION ALL
            select '' as id, 'Total' label, '' as 'date', to_currency(abs(sum(amount))) as amount, '' as 'budget'
            FROM (
                {query}
            )s
        ORDER BY date DESC
    """)
    return curr.fetchall()

def get_variables(curr, month):
    month = f"{month}-01"
    query = f"""
        SELECT budget.label, to_currency(budget.amount) as budget, to_currency(abs(sum(trac.amount))) as 'real_amount', budget.type
        FROM budget
        LEFT JOIN transaction as trac on budget.label = trac.budget AND date_format(Date,'%Y-%m') = date_format('{month}','%Y-%m')
        WHERE  ( start IS NULL OR start < '{month}')
            AND ( end IS NULL OR end > '{month}')
            AND (budget.type <> 'Income' OR budget.type IS NULL)
        GROUP BY budget.label, budget.type
    """
    curr.execute(f"""
            {query}
        UNION ALL
            select 'Total' label, to_currency(abs(sum(budget))) as budget, to_currency(abs(sum(real_amount))) as 'real_amount', '' as type
            FROM (
                {query}
            )s
    """)
    return curr.fetchall()

def get_loans(curr, month):
    query = f"""
        SELECT trac.label, trac.date, to_currency(abs(trac.amount)) as amount, IFNULL(budget,'') as budget
	    FROM transaction as trac
        WHERE trac.amount < 0 AND date_format(Date,'%Y-%m') = '{month}' AND Type = 'TYPE_LOAN_PAYMENT'
    """
    curr.execute(f"""
            {query}
        UNION ALL
            select 'Total' label, '' as 'date', to_currency(abs(sum(amount))) as amount, '' as 'budget'
            FROM (
                {query}
            )s
    """)
    return curr.fetchall()

def get_spendings(curr):
    curr.execute("""
        (
            SELECT budget.label
            FROM budget
            WHERE budget.type <> 'Income'
        )
        UNION ALL
        (
            SELECT CONCAT("Saving - ",name)
            FROM saving
        )
    """)
    result = [ "" ]
    return [spending[0] for spending in curr.fetchall()] + result

@bp.route('/budget/create', methods=('POST',))
@login_required
def create():
    label = request.form['label']
    amount = request.form['amount']
    budget_type = request.form['type']
    start = request.form['start'] if request.form['start'] != '' else None
    end = request.form['end'] if request.form['end'] != '' else None
    error = None

    if not label:
        error = 'Label is required.'

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            'INSERT INTO budget (label, amount, type, start, end)'
            ' VALUES (%s, %s, %s, %s, %s)',
            (label, amount, budget_type, start, end)
        )
        conn.commit()
        return redirect(url_for('finances.budget.index'))


@bp.route('/budget/<int:id>', methods=('POST',))
@login_required
def update(id):
    label = request.form['label']
    amount = request.form['amount']
    budget_type = request.form['type']
    start = request.form['start']
    end = request.form['end'] if request.form['end'] != '' else None
    error = None

    if not label:
        error = 'Label is required.'

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            'UPDATE budget SET label = %s, amount = %s, type = %s, start = %s, end = %s'
            ' WHERE id = %s',
            (label, amount, budget_type, start, end, id)
        )
        conn.commit()
        return redirect(url_for('finances.budget.index'))

def get_budget(id):
    curr = get_db()[0]
    curr.execute(
        'SELECT * FROM budget WHERE id = %s',
        (id,)
    )
    saving = curr.fetchone()

    if saving is None:
        abort(404, f"Budget id {id} doesn't exist.")

    return saving

@bp.route('/budget/<int:id>', methods=('DELETE',))
@login_required
def delete(id):
    get_budget(id)
    curr, conn = get_db()
    curr.execute('DELETE FROM budget WHERE id = %s', (id,))
    conn.commit()
    return redirect(url_for('finances.budget.index'))


@bp.route('/transac/<int:id>', methods=('POST',))
@login_required
def update_transac(id):
    budget = request.get_json()
    curr, conn = get_db()
    curr.execute(
        "UPDATE transaction SET budget = %s WHERE id LIKE '%%s'",
        (budget, id)
    )
    conn.commit()
    return index()
