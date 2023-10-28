"""The authentication blueprint has views to register new users and to log in and log out."""
import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from mysql.connector.errors import IntegrityError

from flaskr.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    """When the user visits the /auth/register URL,
    the register view will return HTML with a form for them to fill out.
    When they submit the form, it will validate their input
    and either show the form again with an error message
    or create the new user and go to the login page."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        curr, conn = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                curr.execute(
                    "INSERT INTO user (username, password) VALUES (%s, %s)",
                    (username, generate_password_hash(password)),
                )
                conn.commit()
            except IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    """When the user visits the /auth/login URL,
    the login view will return HTML with a form for them to fill out.
    When they submit the form, it will validate their input
    and either show the form again with an error message
    or the validation succeeds, the user's id is stored in a new session
    and redirect to index page."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        curr = get_db()[0]
        error = None
        curr.execute(
            'SELECT * FROM user WHERE username = %s', (username,)
        )
        user = curr.fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user[2], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user[0]
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    """Registers a function that runs before the view function, no matter what URL is requested.
    load_logged_in_user checks if a user id is stored in the session and gets that user’s data
    from the database, storing it on g.user, which lasts for the length of the request.
    If there is no user id, or if the id doesn't exist, g.user will be None.
    """
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        curr = get_db()[0]
        curr.execute(
            'SELECT * FROM user WHERE id = %s', (user_id,)
        )
        g.user = curr.fetchone()

@bp.route('/logout')
def logout():
    """Removes the user id from the session and redirect to index."""
    session.clear()
    return redirect(url_for('auth.login'))

def login_required(view):
    """This decorator returns a new view function that wraps the original view it's applied to.
    The new function checks if a user is loaded and redirects to the login page otherwise.
    If a user is loaded the original view is called and continues normally."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
