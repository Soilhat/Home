import pandas
from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from flaskr.auth import login_required
from flaskr.extensions import bank_repository, user_repository
from flaskr.finances.accounts import refresh
from flaskr.finances.bank import (
    create_banks,
    get_banks,
    process_bnp_excel,
    process_ca_excel,
    process_bp_csv,
)

bp = Blueprint("params", __name__)


def get_index(row, columns, index):
    return index


@bp.route("/finances", methods=("GET", "POST"))
@login_required
def finances():
    if request.method == "POST":
        create_banks()
        refresh()
    return render_template(
        "finances/params.html",
        banks=get_banks(),
        avail_banks=["bnp", "ca-paris", "hellobank", "bp", "lcl"],
        get_index=get_index,
    )


@bp.route("/bank/<string:login>", methods=("DELETE",))
@login_required
def delete_banks(login):
    bank_repository.delete_bank(session["user_id"], login)
    return redirect(url_for("params.finances"), code=303)


@bp.route("/db")
@login_required
def download_db():
    return send_from_directory(
        "../adapters/sqllite/databases", f"{session['user_id']}.db"
    )


@bp.post("/upload_transactions")
@login_required
def upload_transactions():

    # Read the File using Flask request
    file = request.files["file"]

    # Parse the data as a Pandas DataFrame type
    if file.content_type == "text/csv":
        df = pandas.read_csv(file, header=None)
    df = pandas.read_excel(file)

    banks_processes = {
        "bnp": process_bnp_excel,
        "hellobank": process_bnp_excel,
        "ca-paris": process_ca_excel,
        "bp": process_bp_csv,
    }
    # check bank
    bank = request.form["bank"].split("(")[1].split(":")[0]
    transactions, account_number, upload_date, balance = banks_processes.get(bank)(df)
    user_id = session["user_id"]
    account = bank_repository.get_account(user_id, account_number)
    for tra in transactions:
        setattr(tra, "account", account)
    bank_repository.upload_transactions(user_id, transactions)
    bank_repository.check_internal(user_id)
    setattr(account, "balance", balance)
    bank_repository.upload_accounts(user_id, [account])
    user_repository.update_refreshed_user(user_id, upload_date)

    return redirect(url_for("params.finances"))
