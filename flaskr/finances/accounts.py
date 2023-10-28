from math import ceil
from flask import (
    Blueprint,request, render_template
)

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('accounts', __name__)


@bp.route('/accounts')
@login_required
def index():
    length = request.args.get('length', 10, type=int)
    curr_page = request.args.get('page', 1, type=int)
    month = request.args.get('month', None, type=str) # format "YYYY-MM"
    curr = get_db()[0]
    curr.execute(
        'SELECT * FROM account'
    )
    accounts = curr.fetchall()
    types = {}
    for account in accounts :
        if account[3] not in types:
            types[account[3]] = []
        types[account[3]].append(account)
    if month is None:
        curr.execute("SELECT date_format(Date,'%Y-%m') FROM transaction ORDER BY Date DESC LIMIT 1")
        month = curr.fetchone()[0]
    curr.execute(f'SELECT COUNT(*) FROM transaction WHERE YEAR(Date) = {int(month[0:4])} AND MONTH(Date) ={int(month[6:7])}')
    total = curr.fetchone()[0]
    curr.execute(f'''
        SELECT Date, Category, Amount, Label, Type
        FROM transaction 
        WHERE YEAR(Date) = {int(month[0:4])} AND MONTH(Date) ={int(month[6:7])}
        ORDER BY date DESC
        LIMIT {length}
        OFFSET {(curr_page-1)*length}
    ''')
    transactions = curr.fetchall()
    return render_template(
        'finances/accounts.html',
        types=types,
        transactions=transactions,
        total = total,
        length= length,
        ceil = ceil,
        curr_page = curr_page,
        month = month,
    )

@bp.route('/accounts/<id>')
@login_required
def transaction(id):
    curr = get_db()[0]
    curr.execute(
        'SELECT * FROM transaction WHERE account=%s',id
    )
    transactions = curr.fetchall()
    return render_template('finances/transactions.html', transactions=transactions)
