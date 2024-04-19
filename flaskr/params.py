from flask import Blueprint, redirect, render_template, request, url_for

from flaskr.auth import login_required
from flaskr.finances.accounts import refresh
from flaskr.finances.bank import create_banks, delete_bank, get_banks

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
    delete_bank(login)
    return redirect(url_for("params.finances"), code=303)
