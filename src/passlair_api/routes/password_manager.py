from flask import Blueprint, render_template, request, url_for
from flask.typing import ResponseReturnValue
from werkzeug.utils import redirect

from ..helpers.functions import check_login_redirect

password_manager = Blueprint(
    "password_manager",
    __name__,
    template_folder="../templates",
    url_prefix="/passwords",
)
password_manager.before_request(check_login_redirect)


@password_manager.route("/")
def landing() -> str:
    """
    Save new password,
    edit password,
    delete password.
    """
    return render_template("landing.html")


@password_manager.route("/save", methods=["GET", "POST"])
def save_password() -> ResponseReturnValue:
    """
    Basic form to save service, login and password.
    Save result of the save form.
    """
    if request.method == "POST":
        return redirect(url_for("password_manager.landing"))

    return render_template("passwords.html")


@password_manager.route("/edit", methods=["GET", "POST"])
def edit_password() -> ResponseReturnValue:
    """
    Form allowing to edit password details.
    Save result of the edit form.
    """
    if request.method == "POST":
        return redirect(url_for("password_manager.landing"))

    return render_template("passwords.html")


@password_manager.route("/delete", methods=["GET", "POST"])
def delete_password() -> ResponseReturnValue:
    """
    Basic form to confirm deletion.
    Deletes password and redirects.
    """
    if request.method == "POST":
        return redirect(url_for("password_manager.landing"))

    return render_template("passwords.html")
