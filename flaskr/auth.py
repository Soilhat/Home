"""The authentication blueprint has views to register new users and to log in and log out."""

import base64
import functools
from hashlib import sha256

import rsa
from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from core.use_cases.exceptions import UserAlreadyExists
from flaskr.extensions import user_repository

bp = Blueprint("auth", __name__, url_prefix="/auth")


class EncryptionKey:
    _publicKey = None
    _privateKey = None
    _hashedIP = ""

    def __init__(self, hashedIP):
        self._hashedIP = hashedIP

    def generateKeys(self):
        (pub, priv) = rsa.newkeys(1024)
        self._publicKey = pub
        self._privateKey = priv

    def isEqual(self, hashedIP):
        return hashedIP == self._hashedIP

    def isAuthorizedToGenerateNewKey(self):
        return True

    def decrypt(self, message):
        return (rsa.decrypt(base64.b64decode(message), self._privateKey)).decode(
            "utf-8"
        )


g_registeredEncryptionKeys = []


@bp.route("/register", methods=("GET", "POST"))
def register():
    """When the user visits the /auth/register URL,
    the register view will return HTML with a form for them to fill out.
    When they submit the form, it will validate their input
    and either show the form again with an error message
    or create the new user and go to the login page."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            try:
                user_repository.register(
                    username, generate_password_hash(password, method="pbkdf2")
                )
            except UserAlreadyExists:
                error = str(UserAlreadyExists)
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/encryption")
def generateEncryptionKeys():
    hashedCurrentIP = sha256(request.remote_addr.encode("utf-8")).hexdigest()

    global g_registeredEncryptionKeys
    encryptionKey = None
    for registeredKey in g_registeredEncryptionKeys:
        if registeredKey.isEqual(hashedCurrentIP):
            if registeredKey.isAuthorizedToGenerateNewKey() == False:
                return ""
            else:
                encryptionKey = registeredKey

    if encryptionKey == None:
        g_registeredEncryptionKeys.append(EncryptionKey(hashedCurrentIP))
        encryptionKey = g_registeredEncryptionKeys[-1]

    encryptionKey.generateKeys()

    return base64.b64encode(encryptionKey._publicKey._save_pkcs1_der())


@bp.route("/login", methods=("GET", "POST"))
def login():
    """When the user visits the /auth/login URL,
    the login view will return HTML with a form for them to fill out.
    When they submit the form, it will validate their input
    and either show the form again with an error message
    or the validation succeeds, the user's id is stored in a new session
    and redirect to index page."""
    if request.method == "POST":
        error = None

        username = request.form["username"]
        hashedCurrentIP = sha256(request.remote_addr.encode("utf-8")).hexdigest()
        encryptedPassword = request.form["password"]
        password = ""
        global g_registeredEncryptionKeys
        for registeredKey in g_registeredEncryptionKeys:
            if registeredKey.isEqual(hashedCurrentIP):
                password = registeredKey.decrypt(encryptedPassword)

        if password == "":
            error = "No encryption key found"
            flash(error, category="warning")

        user = user_repository.find_by_username(username)

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user.password, password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("index"))

        flash(error, category="warning")

    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    """Registers a function that runs before the view function, no matter what URL is requested.
    load_logged_in_user checks if a user id is stored in the session and gets that user’s data
    from the database, storing it on g.user, which lasts for the length of the request.
    If there is no user id, or if the id doesn't exist, g.user will be None.
    """
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = user_repository.find_by_id(user_id)


@bp.route("/logout")
def logout():
    """Removes the user id from the session and redirect to index."""
    session.clear()
    return redirect(url_for("auth.login"))


def login_required(view):
    """This decorator returns a new view function that wraps the original view it's applied to.
    The new function checks if a user is loaded and redirects to the login page otherwise.
    If a user is loaded the original view is called and continues normally."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
