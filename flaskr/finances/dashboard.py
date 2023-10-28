from flask import Blueprint, render_template, json

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("dashboard", __name__)


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
    curr.execute("SELECT sum(balance) FROM saving")
    savings = curr.fetchone()[0]
    curr.execute(
        """
        SELECT sum(balance)
        FROM account LEFT Join loan on account.id=loan.id
        WHERE loan.id IS NOT NULL
    """
    )
    loans = curr.fetchone()[0]
    curr.execute(
        """select 
                date_format(date,'%M %Y') as Date,
                sum(CASE WHEN amount<0 THEN ABS(amount) END) as expenses,
                sum(CASE WHEN amount>0 THEN amount END) as earnings
            from transaction
            LEFT Join loan on transaction.account=loan.id
                    WHERE loan.id IS NULL
            group by year(date),month(date)
            order by year(date),month(date);
        """
    )
    expenses_data = curr.fetchall()
    dates=[]
    expenses = []
    earnings = []
    for date, expense, earning in expenses_data:
        dates.append(str(date))
        expenses.append(expense)
        earnings.append(earning)

    return render_template(
        "finances/dashboard.html",
        accounts=accounts,
        savings=savings,
        loans=loans,
        expenses=json.dumps(expenses),
        dates= json.dumps(dates),
        earnings= json.dumps(earnings)
    )
