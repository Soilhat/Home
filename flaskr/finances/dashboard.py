from flask import Blueprint, render_template, json

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("dashboard", __name__)

internal_trac = [
    "MME SOILHAT MOHAMED",
    "VIREMENT EN VOTRE FAVEUR DE MONTEIRO ARTHUR",
    "MONTEIRO ARTHUR",
    "MOHAMED SOILHAT",
    "VIE COMMUNE",
    "EPARGNE",
    "FACTURES",
]


@bp.route("/")
@login_required
def index():
    curr = get_db()[0]
    curr.execute(
        """
        SELECT sum(balance)
        FROM account LEFT Join loan on account.id=loan.id
        WHERE loan.id IS NULL
    """
    )
    accounts = curr.fetchone()[0]
    curr.execute(
        """SELECT sum(amount)
        FROM transaction
        LEFT JOIN saving on transaction.saving_id = saving.id
        WHERE saving.id IS NOT NULL"""
    )
    savings = curr.fetchone()[0]
    curr.execute(
        "SELECT date_format(Date,'%Y-%m') FROM transaction ORDER BY Date DESC LIMIT 1"
    )
    month = curr.fetchone()[0]
    curr.execute(
        f"""
        SELECT sum(budget) + sum(amount)
        FROM (
            SELECT IFNULL(budget.type, fixed_bud.type) as type, trac.amount, 0 as budget
            FROM transaction as trac
            INNER JOIN account as acc on trac.account=acc.id
            LEFT OUTER JOIN budget on budget.label = trac.budget AND date_format(Date,'%Y-%m') = '{month}'
            LEFT OUTER JOIN budget as fixed_bud on trac.label LIKE CONCAT('%',fixed_bud.label,'%') AND date_format(Date,'%Y-%m') = '{month}'
            WHERE date_format(Date,'%Y-%m') = '{month}'
                AND (budget.type <> 'Income' OR budget.type IS NULL)
                AND trac.amount < 0
                AND trac.label NOT REGEXP '{"|".join(internal_trac)}'
                AND (trac.budget NOT LIKE '%Saving%' OR trac.budget IS NULL)
        UNION ALL
            SELECT budget.type, 0 as 'real_amount', budget.amount as budget
            FROM budget
            WHERE ( start IS NULL OR (date_format(start,'%Y-%m') <= '{month}'))
                AND ( end IS NULL OR (date_format(end,'%Y-%m') >= '{month}'))
                AND (type <> 'Income' OR type IS NULL)
        )labels
    """
    )
    pending_budget = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(balance)
        FROM account LEFT Join loan on account.id=loan.id
        WHERE loan.id IS NOT NULL
    """
    )
    loans = curr.fetchone()[0]
    curr.execute(
        f"""select 
                date_format(date,'%M %Y') as Date,
                sum(CASE WHEN amount<0 THEN ABS(amount) END) as expenses,
                sum(CASE WHEN amount>0 THEN amount END) as earnings
            from transaction
            LEFT Join loan on transaction.account=loan.id
            WHERE loan.id IS NULL
                AND label NOT REGEXP '{"|".join(internal_trac)}'
                AND account IS NOT NULL
            group by year(date),month(date)
            order by year(date),month(date);
        """
    )
    expenses_data = curr.fetchall()
    dates = []
    expenses = []
    earnings = []
    for date, expense, earning in expenses_data:
        dates.append(str(date))
        expenses.append(expense)
        earnings.append(earning)

    return render_template(
        "finances/dashboard.html",
        accounts=accounts,
        pending_budget=pending_budget,
        savings=savings,
        loans=loans,
        expenses=json.dumps(expenses),
        dates=json.dumps(dates),
        earnings=json.dumps(earnings),
    )
