from flask import Blueprint, redirect, render_template, url_for
from werkzeug.wrappers.response import Response


auth = Blueprint(
    "Authorization", __name__, template_folder="../templates", url_prefix="/auth"
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
    raise NotImplementedError

    return redirect(url_for("password_manager.landing"))


@auth.route("/logout", methods=["GET"])
def logout() -> Response:
    """
    Basic log out form.
    """
    raise NotImplementedError

    return render_template("logout.html")


@auth.route("/logout", methods=["POST"])
def _logout() -> Response:
    """
    Log out and redirect.
    """
    raise NotImplementedError

    return redirect(url_for("auth.login"))


@auth.route("/user", methods=["GET"])
def user() -> str:
    """
    Form to edit all user fields.
    """
    return render_template("user")


@auth.route("/user", methods=["POST"])
def _user() -> str:
    """
    Save edit form changes and redirect.
    """
    return render_template("user")
