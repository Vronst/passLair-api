from flask import Blueprint, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue

from ..helpers.functions import check_login_status, get_create_identity
from ..helpers.wrapers import login_required

auth = Blueprint("auth", __name__, template_folder="../templates", url_prefix="/auth")


@auth.route("/")
@login_required
def landing() -> str:
    """
    Change you information,
    Delete account.
    """
    return render_template(
        "landing.html", links=[{"url": "data.landing", "label": "data label"}]
    )


@auth.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    """
    Basic form.
    Log in and redirect.
    """
    if check_login_status():
        return redirect(url_for("password_manager.landing"))

    identity = get_create_identity()
    if request.method == "POST":
        data = request.form
        username, password = data.get("username", ''), data.get("password", '')
        result = identity.login(username, password)
        if result.success:
            return redirect(url_for("password_manager.landing"))
        # TODO: flash message about login failure

    return render_template("login.html")


@auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout() -> ResponseReturnValue:
    """
    Basic log out form.
    Log out and redirect.
    """
    if request.method == "POST":
        session.clear()
        return redirect(url_for("auth.login"))

    return render_template("logout.html")


@auth.route("/user", methods=["GET", "POST"])
@login_required
def user() -> ResponseReturnValue:
    """
    Form to edit all user fields.
    Save edit form changes and redirect.
    """
    if request.method == "POST":
        return render_template("user.html")

    return render_template("user.html")


@auth.route("/reset_password", methods=["GET"])
def reset_password() -> str:
    """
    Form for backup phrases that allows for password change.
    """
    return render_template("reset_password.html")


@auth.route("/reset_password/new_password", methods=["GET", "POST"])
def new_password() -> ResponseReturnValue:
    """
    Allows to set new password.
    After successfull authorization with backup phrases, sents user to landing page.
    Set new message with new backup phrase.
    """
    if request.method != "POST":
        return redirect(url_for("auth.reset_password"))

    return render_template("new_password_for_reset.html")
