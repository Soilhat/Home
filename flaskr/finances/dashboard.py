from flask import Blueprint, render_template, json

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("dashboard", __name__)

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
    "MLE MOHAMED SOILHAT"
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
            LEFT OUTER JOIN budget on budget.id = trac.budget_id
                AND date_format(Date,'%Y-%m') = '{month}'
            LEFT OUTER JOIN budget as fixed_bud on trac.label LIKE CONCAT('%',fixed_bud.label,'%')
                AND date_format(Date,'%Y-%m') = '{month}'
            WHERE date_format(Date,'%Y-%m') = '{month}'
                AND (budget.type <> 'Income' OR budget.type IS NULL)
                AND trac.amount < 0
                AND trac.label NOT REGEXP '^{"$|^".join(internal_trac)}$'
                AND trac.saving_id IS NULL
                AND trac.parent IS NULL
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
            from transaction trac
            INNER JOIN account as acc on trac.account=acc.id
            WHERE acc.type = 'CHECKING'
                AND trac.label NOT REGEXP '^{"$|^".join(internal_trac)}$'
                AND account IS NOT NULL
                AND date BETWEEN 
                    DATE_ADD(LAST_DAY(DATE_ADD(DATE_ADD((SELECT MAX(date) from transaction), INTERVAL -1 YEAR), INTERVAL -2 MONTH)),INTERVAL 1 DAY)
                    AND LAST_DAY(DATE_ADD((SELECT MAX(date) from transaction), INTERVAL -1 MONTH))
                AND trac.parent IS NULL
            group by year(date),month(date)
            order by year(date),month(date);
        """
    )
    expenses_data = curr.fetchall()
    curr.execute(
        """
        SELECT sum(amount)
        FROM budget
        WHERE Type = 'Income'
            AND (end IS NULL OR end > curdate())
        """
    )
    revenus = curr.fetchone()[0]
    curr.execute(
        f"""
        SELECT CAST(sum(amount)/3 AS DECIMAL(10,2))
        FROM transaction
        WHERE amount > 0
			AND type = 'TYPE_TRANSFER'
            AND label NOT REGEXP '^{"$|^".join(internal_trac)}$'
            AND parent IS NULL
            AND date BETWEEN DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -4 MONTH) AND DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -1 MONTH)
        """
    )
    revenus_avg = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(monthly_saving)
        FROM saving
        """
    )
    monthly_savings = curr.fetchone()[0]
    curr.execute(
        """
        SELECT CAST(sum(amount)/3 AS DECIMAL(10,2))
        FROM transaction
        WHERE saving_id IS NOT NULL
            AND amount > 0
            AND date BETWEEN DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -4 MONTH) AND DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -1 MONTH)
        """
    )
    monthly_savings_avg = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(amount)
        FROM budget
        WHERE fixed = 0
            AND Type <> 'Income'
            AND (end IS NULL OR end > curdate())
        """
    )
    bud_var_expenses = curr.fetchone()[0]
    curr.execute(
        """
        SELECT ABS(CAST(sum(transaction.amount)/3 AS DECIMAL(10,2)))
        FROM transaction
        LEFT JOIN budget on budget_id = budget.id
        WHERE budget_id IS NOT NULL
            AND budget.Type <> 'Income'
            AND fixed = 0
            AND date BETWEEN DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -4 MONTH) AND DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -1 MONTH)
        """
    )
    bud_var_expenses_avg = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(amount)
        FROM budget
        WHERE fixed = 1
            AND Type <> 'Income'
            AND (end IS NULL OR end > curdate())
        """
    )
    bud_fix_expenses = curr.fetchone()[0]
    curr.execute(
        """
        SELECT ABS(CAST(sum(transaction.amount)/3 AS DECIMAL(10,2)))
        FROM transaction
        LEFT JOIN budget on transaction.label LIKE CONCAT('%',budget.label,'%')
        WHERE budget.fixed = 1
            AND date BETWEEN DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -4 MONTH) AND DATE_ADD(DATE_ADD(LAST_DAY((SELECT MAX(date) from transaction)), INTERVAL 1 DAY), INTERVAL -1 MONTH)
        """
    )
    bud_fix_expenses_avg = curr.fetchone()[0]
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
        revenus=revenus,
        revenus_avg=revenus_avg,
        monthly_savings=monthly_savings,
        monthly_savings_avg=monthly_savings_avg,
        bud_var_expenses=bud_var_expenses,
        bud_var_expenses_avg = bud_var_expenses_avg,
        bud_fix_expenses=bud_fix_expenses,
        bud_fix_expenses_avg=bud_fix_expenses_avg,
        expenses=json.dumps(expenses),
        dates=json.dumps(dates),
        earnings=json.dumps(earnings),
    )
