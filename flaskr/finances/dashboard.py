from datetime import datetime

from flask import Blueprint, json, render_template

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    curr = get_db()[0]
    curr.execute(
        """
        SELECT sum(balance) as balance
        FROM account LEFT Join loan on account.id=loan.id
        WHERE loan.id IS NULL
    """
    )
    accounts = curr.fetchone()[0]
    curr.execute(
        """SELECT sum(amount) saving
        FROM "transaction"
        LEFT JOIN saving on "transaction".saving_id = saving.id
        WHERE saving.id IS NOT NULL"""
    )
    savings = curr.fetchone()[0]
    curr.execute(
        """SELECT strftime('%Y-%m',Date) month FROM "transaction" ORDER BY Date DESC LIMIT 1"""
    )
    month = curr.fetchone()
    if month:
        month = month[0]
    else:
        month = datetime.today().strftime("%Y-%m")
    curr.execute(
        f"""
        SELECT sum(budget) + sum(amount) as pending
        FROM (
            SELECT IFNULL(budget.type, fixed_bud.type) as type, trac.amount, 0 as budget
            FROM "transaction" as trac
            INNER JOIN account as acc on trac.account=acc.id
            LEFT OUTER JOIN budget on budget.id = trac.budget_id
                AND strftime('%Y-%m',Date) = '{month}'
            LEFT OUTER JOIN budget as fixed_bud on trac.label LIKE '%'||fixed_bud.label||'%'
                AND strftime('%Y-%m',Date) = '{month}'
            WHERE strftime('%Y-%m',Date) = '{month}'
                AND (budget.type <> 'Income' OR budget.type IS NULL)
                AND trac.amount < 0
                AND trac.internal IS NULL
                AND trac.saving_id IS NULL
                AND trac.parent IS NULL
        UNION ALL
            SELECT budget.type, 0 as 'real_amount', budget.amount as budget
            FROM budget
            WHERE ( start IS NULL OR (strftime('%Y-%m',start) <= '{month}'))
                AND ( end IS NULL OR (strftime('%Y-%m',end) >= '{month}'))
                AND (type <> 'Income' OR type IS NULL)
        )labels
    """
    )
    pending_budget = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(balance) loans
        FROM account LEFT Join loan on account.id=loan.id
        WHERE loan.id IS NOT NULL
    """
    )
    loans = curr.fetchone()[0]
    curr.execute(
        """select
                substr('--JanFebMarAprMayJunJulAugSepOctNovDec',strftime ('%m', date) * 3, 3)||' '||strftime ('%Y', date) as Date,
                sum(CASE WHEN amount<0 THEN ABS(amount) END) as expenses,
                sum(CASE WHEN amount>0 THEN amount END) as earnings
            from "transaction" trac
            INNER JOIN account as acc on trac.account=acc.id
            WHERE acc.type = 'CHECKING'
                AND trac.internal IS NULL
                AND account IS NOT NULL
                AND date BETWEEN 
                    DATE(DATE(DATE(DATE((SELECT MAX(date) from "transaction"), '-1 year'), '-2 month'), 'start of month', '+1 month', '-1 day') ,'-1 day')
                    AND DATE(DATE((SELECT MAX(date) from "transaction"), '-1 month'), 'start of month', '+1 month', '-1 day') 
                AND trac.parent IS NULL
            group by strftime('%Y', date),strftime('%m', date)
            order by strftime('%Y', date),strftime('%m', date);
        """
    )
    expenses_data = curr.fetchall()
    curr.execute(
        """
        SELECT sum(amount) as revenus
        FROM budget
        WHERE Type = 'Income'
            AND (end IS NULL OR end > DATE('now'))
        """
    )
    revenus = curr.fetchone()[0]
    curr.execute(
        """
        SELECT CAST(sum(amount)/3 AS DECIMAL(10,2)) as revenus_avg
        FROM "transaction"
        WHERE amount > 0
			AND type = 'TYPE_TRANSFER'
            AND internal IS NULL
            AND parent IS NULL
            AND date BETWEEN DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-4 month')
                AND DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-1 MONTH')
        """
    )
    revenus_avg = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(monthly_saving) as savings
        FROM saving
        """
    )
    monthly_savings = curr.fetchone()[0]
    curr.execute(
        """
        SELECT CAST(sum(amount)/3 AS DECIMAL(10,2)) as savings_avg
        FROM "transaction"
        WHERE saving_id IS NOT NULL
            AND amount > 0
            AND date BETWEEN DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-4 month')
                AND DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-1 MONTH')
        """
    )
    monthly_savings_avg = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(amount) as var_exps
        FROM budget
        WHERE fixed = 0
            AND Type <> 'Income'
            AND (end IS NULL OR end > DATE('now'))
        """
    )
    bud_var_expenses = curr.fetchone()[0]
    curr.execute(
        """
        SELECT ABS(CAST(sum("transaction".amount)/3 AS DECIMAL(10,2))) as var_exps_avg
        FROM "transaction"
        LEFT JOIN budget on budget_id = budget.id
        WHERE budget_id IS NOT NULL
            AND budget.Type <> 'Income'
            AND fixed = 0
            AND date BETWEEN DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-4 month')
                AND DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-1 MONTH')
        """
    )
    bud_var_expenses_avg = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(amount) as fix_exps
        FROM budget
        WHERE fixed = 1
            AND Type <> 'Income'
            AND (end IS NULL OR end > DATE('now'))
        """
    )
    bud_fix_expenses = curr.fetchone()[0]
    curr.execute(
        """
        SELECT ABS(CAST(sum("transaction".amount)/3 AS DECIMAL(10,2))) as fix_exps_avg
        FROM "transaction"
        LEFT JOIN budget on "transaction".label LIKE '%'||budget.label||'%'
        WHERE budget.fixed = 1
            AND date BETWEEN DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-4 month')
                AND DATE(DATE(DATE((SELECT MAX(date) from "transaction"), 'start of month', '+1 month', '-1 day'), '+1 day'), '-1 MONTH')
        """
    )
    bud_fix_expenses_avg = curr.fetchone()[0]
    dates = []
    expenses = []
    earnings = []
    for date, expense, earning in expenses_data:
        dates.append(date)
        expenses.append(expense)
        earnings.append(earning)

    return render_template(
        "finances/dashboard.html",
        accounts=accounts or 0,
        pending_budget=pending_budget or 0,
        savings=savings or 0,
        loans=loans or 0,
        revenus=revenus or 0,
        revenus_avg=revenus_avg or 0,
        monthly_savings=monthly_savings or 0,
        monthly_savings_avg=monthly_savings_avg or 0,
        bud_var_expenses=bud_var_expenses or 0,
        bud_var_expenses_avg=bud_var_expenses_avg or 0,
        bud_fix_expenses=bud_fix_expenses or 0,
        bud_fix_expenses_avg=bud_fix_expenses_avg or 0,
        expenses=json.dumps(expenses),
        dates=json.dumps(dates),
        earnings=json.dumps(earnings),
    )
