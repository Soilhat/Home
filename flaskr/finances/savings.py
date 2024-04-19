from datetime import datetime

import simplejson as json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("saving", __name__)


@bp.route("/saving")
@login_required
def index():
    json_return = request.args.get("json", False, type=bool)  # format "YYYY-MM"
    curr = get_db()[0]
    curr.execute(
        """
        SELECT saving.id, saving.name, IFNULL(sum('transaction'.amount),0) balance, saving.monthly_saving, saving.goal
        FROM saving
        LEFT JOIN 'transaction' on 'transaction'.saving_id = saving.id
        group by saving.id
        """
    )
    savings = curr.fetchall()
    if json_return:
        return json.dumps(savings)
    return render_template("finances/saving.html", savings=savings)


@bp.route("/saving", methods=("POST",))
@login_required
def create():
    name = request.form["name"]
    monthly_saving = request.form["monthly_saving"]
    goal = request.form["goal"] if request.form["goal"] != "" else None
    error = None

    if not name:
        error = "Name is required."

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            "INSERT INTO saving (name, monthly_saving, goal)" " VALUES (?, ?, ?)",
            (name, monthly_saving, goal),
        )
        conn.commit()
        return redirect(url_for("finances.saving.index"))


@bp.route("/saving/transaction", methods=("POST",))
@login_required
def create_transaction():
    amount = request.form["amount"]
    date = (
        request.form["date"]
        if request.form["date"] != ""
        else datetime.today().strftime("%Y-%m-%d")
    )
    label = request.form["label"]
    saving_id = int(request.form["saving"])
    error = None

    get_saving(saving_id)

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            "INSERT INTO 'transaction' (id, amount, date, label, saving_id)"
            " VALUES (FLOOR(1 + random() * (10000000000 - 0 + 1)), ?, ?, ?, ?)",
            (amount, date, label, saving_id),
        )
        conn.commit()
        return redirect(url_for("finances.saving.index"))


def get_saving(id):
    curr = get_db()[0]
    curr.execute("SELECT * FROM saving WHERE id = ?", (id,))
    saving = curr.fetchone()

    if saving is None:
        abort(404, f"Saving id {id} doesn't exist.")

    return saving


@bp.route("/saving/<int:saving_id>")
@login_required
def retrieve(saving_id):
    curr = get_db()[0]
    curr.execute(
        f"""
        SELECT 'transaction'.label, bank, strftime('%Y-%m-%d',date), amount
        FROM 'transaction'
        LEFT JOIN saving on 'transaction'.saving_id = saving.id
        LEFT JOIN account on 'transaction'.account = account.id
        WHERE saving.id = {saving_id}
        ORDER BY date desc
        """
    )
    saving_data = curr.fetchall()
    return render_template("finances/saving_id.html", saving_data=saving_data)


@bp.route("/saving/<int:id>", methods=("POST",))
@login_required
def update(id):
    name = request.form["name"]
    monthly_saving = request.form["monthly_saving"]
    goal = request.form["goal"] if request.form["goal"] != "" else None
    error = None

    if not name:
        error = "Name is required."

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            "UPDATE saving SET name = ?, monthly_saving = ?, goal = ?" " WHERE id = ?",
            (name, monthly_saving, goal, id),
        )
        conn.commit()
        return redirect(url_for("finances.saving.index"))


@bp.route("/saving/<int:id>", methods=("DELETE",))
@login_required
def delete(id):
    get_saving(id)
    curr, conn = get_db()
    curr.execute("DELETE FROM saving WHERE id = ?", (id,))
    conn.commit()
    return redirect(url_for("finances.saving.index"))
