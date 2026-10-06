from typing import cast

from flask import Blueprint, flash, render_template, request, url_for
from flask.typing import ResponseReturnValue
from werkzeug.utils import redirect

from ..helpers.functions import (
    check_login_redirect,
    flash_and_redirect,
    get_create_password_manager,
)

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


@password_manager.route("/retrieve", methods=["GET", "POST"])
def retrieve_password() -> ResponseReturnValue:
    """
    Basic form asking for a service.
    Shows decrypted login and password for that service.
    """
    if request.method == "POST":
        service = request.form.get("service", "")
        if not service:
            flash("Service must not be empty", "warning")
            return render_template("passwords.html")

        manager = get_create_password_manager()
        result = manager.get_password_for_service(service)
        if not result.success:
            flash(result.message, "warning")
        else:
            flash(cast(str, result.data.get("login", "")), "retrieved_login")
            flash(cast(str, result.data.get("password", "")), "retrieved_password")

    return render_template("passwords.html")


@password_manager.route("/save", methods=["GET", "POST"])
def save_password() -> ResponseReturnValue:
    """
    Basic form to save service, login and password.
    Creates the entry, or overwrites it if the service already exists.
    """
    if request.method == "POST":
        form = request.form
        service = form.get("service", '')
        login = form.get("login", '')
        password = form.get("password", '')
        if not all([service, login, password]):
            flash("All fields must be filled", "warning")
            return render_template("passwords.html")

        manager = get_create_password_manager()
        result = manager.set_password_for_service(service, login, password)

        if not result.success:
            flash(result.message, "warning")
            return render_template("passwords.html")

        return flash_and_redirect("password_manager.landing", result.message, "info")

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
