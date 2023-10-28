from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('saving', __name__)

@bp.route('/saving')
@login_required
def index():
    curr = get_db()[0]
    curr.execute(
        'SELECT * FROM saving'
    )
    savings = curr.fetchall()
    return render_template('finances/saving.html', savings=savings)

@bp.route('/saving', methods=('POST',))
@login_required
def create():
    name = request.form['name']
    balance = request.form['balance']
    monthly_saving = request.form['monthly_saving']
    goal = request.form['goal'] if request.form['goal'] != '' else None
    error = None

    if not name:
        error = 'Name is required.'

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            'INSERT INTO saving (name, balance, monthly_saving, goal)'
            ' VALUES (%s, %s, %s, %s)',
            (name, balance, monthly_saving, goal)
        )
        conn.commit()
        return redirect(url_for('finances.saving.index'))

def get_saving(id):
    curr = get_db()[0]
    curr.execute(
        'SELECT * FROM saving WHERE id = %s',
        (id,)
    )
    saving = curr.fetchone()

    if saving is None:
        abort(404, f"Saving id {id} doesn't exist.")

    return saving

@bp.route('/saving/<int:id>', methods=('POST',))
@login_required
def update(id):
    name = request.form['name']
    balance = request.form['balance']
    monthly_saving = request.form['monthly_saving']
    goal = request.form['goal'] if request.form['goal'] != '' else None
    error = None

    if not name:
        error = 'Name is required.'

    if error is not None:
        flash(error)
    else:
        curr, conn = get_db()
        curr.execute(
            'UPDATE saving SET name = %s, balance = %s, monthly_saving = %s, goal = %s'
            ' WHERE id = %s',
            (name, balance, monthly_saving, goal, id)
        )
        conn.commit()
        return redirect(url_for('finances.saving.index'))

@bp.route('/saving/<int:id>', methods=('DELETE',))
@login_required
def delete(id):
    get_saving(id)
    curr, conn = get_db()
    curr.execute('DELETE FROM saving WHERE id = %s', (id,))
    conn.commit()
    return redirect(url_for('finances.saving.index'))
