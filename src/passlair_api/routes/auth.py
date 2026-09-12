from flask import Blueprint, redirect, render_template, url_for
from werkzeug.wrappers.response import Response


auth = Blueprint(
    "auth", __name__, template_folder="../templates", url_prefix="/auth"
)


@auth.route("/")
def landing() -> str:
    """
    Change you information,
    Delete account.
    """
    return render_template(
        "landing.html", links=[{"url": "Data.landing", "label": "data label"}]
    )


@auth.route("/login", methods=["GET"])
def login() -> str:
    """
    Basic form.
    """
    return render_template("login.html")


@auth.route("/login", methods=["POST"])
def _login() -> Response:
    """
    Log in and redirect.
    """

    return redirect(url_for("password_manager.landing"))


@auth.route("/logout", methods=["GET"])
def logout() -> str:
    """
    Basic log out form.
    """
    return render_template("logout.html")


@auth.route("/logout", methods=["POST"])
def _logout() -> Response:
    """
    Log out and redirect.
    """

    return redirect(url_for("auth.login"))


@auth.route("/user", methods=["GET"])
def user() -> str:
    """
    Form to edit all user fields.
    """
    return render_template("user.html")


@auth.route("/user", methods=["POST"])
def _user() -> str:
    """
    Save edit form changes and redirect.
    """
    return render_template("user.html")


@auth.route("/reset_password", methods=["GET"])
def reset_password() -> str:
    """
    Form for backup phrases that allows for password change.
    """
    return render_template("reset_password.html")


@auth.route("/reset_password/new_password", methods=["GET"])
def new_password() -> str:
    """
    Allows to set new password.
    """
    return render_template("new_password_for_reset.html")

@auth.route("/reset_password/new_password", methods=["POST"])
def _new_password() -> Response:
    """
    After successfull authorization with backup phrases, sents user to landing page.
    Set new message with new backup phrase.
    """
    # if fail
    return redirect(url_for("auth.reset_password"))
    # if success
    return redirect(url_for("password_manager.landing"))
