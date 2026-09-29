from typing import cast

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ..helpers.functions import check_login_status, get_create_identity, remove_identity
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
        username, password = data.get("username", ""), data.get("password", "")
        result = identity.login(username, password)
        if result.success:
            return redirect(url_for("password_manager.landing"))

        flash("Wrong password or username", "error")

    return render_template("login.html")


@auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout() -> ResponseReturnValue:
    """
    Basic log out form.
    Log out and redirect.
    """
    if request.method == "POST":
        remove_identity()
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

    backup_phrase = request.form.get('backup_phrase', None)
    if not backup_phrase:
        flash("Backup phrase cannot be read.", "error")
        return redirect("auth.reset_password")

    password, password_confirm = request.form.get("password"), request.form.get("password_confirm")
    if password != password_confirm:
        flash("Passwords must match", "warning")
        return redirect("auth.reset_password")

    identity = get_create_identity()
    identity.reset_user_password(username, backup_phrase, password)

    return render_template("new_password_for_reset.html")


@auth.route("/register", methods=["GET", "POST"])
def register() -> str | ResponseReturnValue:
    def flash_warning(message: str) -> ResponseReturnValue:
        flash(message, "warning")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        identity = get_create_identity()
        data = request.form
        username, email, password, password_confirm = (
            data.get("username", ""),
            data.get("email", ""),
            data.get("password", ""),
            data.get("password_confirm"),
        )
        if not all((username, email, password, password_confirm)):
            return flash_warning("All field must be filled.")

        elif password != password_confirm:
            return flash_warning("Password and confirm password must be identical!")

        result = identity.register_user(username, email, password)
        if not result.success:
            return flash_warning(f"{result.message}")

        flash(cast(str, result.data.get("backup_phrase")), "backup_phrase")
        return redirect(url_for("password_manager.landing"))

    return render_template("register.html")
