from flask import Blueprint, json, render_template, session

from flaskr.auth import login_required
from flaskr.extensions import bank_repository

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    user_id = session.get("user_id")
    accounts = bank_repository.get_balance(user_id)
    savings = bank_repository.get_savings(user_id)
    month = bank_repository.get_last_month(user_id)
    pending_budget = bank_repository.get_pending_budget(user_id, month)
    loans = bank_repository.get_balance(user_id, loans=True)
    revenus = bank_repository.get_incomes(user_id)
    revenus_avg = bank_repository.get_incomes_avg(user_id)
    expenses_data = bank_repository.get_curr_expenses(user_id)
    monthly_savings = bank_repository.get_monthly_savings(user_id)
    monthly_savings_avg = bank_repository.get_monthly_savings_avg(user_id)
    bud_var_expenses = bank_repository.get_bud_expenses(user_id)
    bud_var_expenses_avg = bank_repository.get_bud_expenses_avg(user_id)
    bud_fix_expenses = bank_repository.get_bud_expenses(user_id, fixed=True)
    bud_fix_expenses_avg = bank_repository.get_bud_expenses_avg(user_id, fixed=True)
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
