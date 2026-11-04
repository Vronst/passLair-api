"""Login, logout, registration and password management routes."""

from typing import cast

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue
from passlair.core import Identity

from ..helpers.functions import (
    check_login_status,
    flash_and_redirect,
    get_create_identity,
    login_attempts_exceeded,
    no_store,
    record_failed_login,
    remove_identity,
    save_identity,
)
from ..helpers.wrapers import login_required

auth = Blueprint("auth", __name__, template_folder="../templates", url_prefix="/auth")
auth.after_request(no_store)


@auth.route("/")
@login_required
def landing() -> str:
    """
    Change you information,
    Delete account.
    """
    return render_template(
        "landing.html", links=[{"url": "data.landing", "label": "Export/Import"}]
    )


@auth.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    """
    Basic form.
    Log in and redirect.
    """
    if check_login_status():
        return redirect(url_for("password_manager.landing"))

    if request.method == "POST":
        # Checked first, so blocked attempts skip the expensive password hashing.
        if login_attempts_exceeded():
            flash("Too many failed attempts. Try again later.", "error")
            return render_template("login.html"), 429

        identity = Identity()
        data = request.form
        username, password = data.get("username", ""), data.get("password", "")
        result = identity.login(username, password)
        if result.success:
            save_identity(identity)
            session["username"] = username
            return redirect(url_for("password_manager.landing"))

        record_failed_login()
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
    Form to change password. Username is fixed after registration.
    Save edit form changes and redirect.
    """
    if request.method == "GET":
        username = session.get("username")
        return render_template("user.html", username=username)

    identity = get_create_identity()
    form = request.form
    current_password, changed_password, confirm_password = (
        form.get("current_password"),
        form.get("password"),
        form.get("password_confirm"),
    )
    if not all([current_password, changed_password, confirm_password]):
        return flash_and_redirect(
            "auth.user", "Required fields are missing.", "warning"
        )

    if changed_password != confirm_password:
        return flash_and_redirect("auth.user", "New passwords do not match", "warning")

    assert current_password and changed_password
    result = identity.change_user_password(changed_password, current_password)

    if not result.success:
        return flash_and_redirect("auth.user", result.message, "warning")

    flash(cast(str, result.data.get("backup_phrase")), "backup_phrase")
    return flash_and_redirect(
        "password_manager.landing", "Password changed successfully.", "info"
    )


@auth.route("/reset_password", methods=["GET"])
def reset_password() -> ResponseReturnValue:
    """
    Form for username, backup phrase and new password.
    Submits to new_password, which performs the reset.
    """
    return render_template("reset_password.html")


@auth.route("/reset_password/new_password", methods=["GET", "POST"])
def new_password() -> ResponseReturnValue:
    """
    Handles the reset form.
    Validates the fields, resets the password using the backup phrase,
    and flashes the newly rotated backup phrase.
    Any failure, and a plain GET, redirects back to the reset form.
    """

    def back_to_reset_form(message: str, type_: str = "error") -> ResponseReturnValue:
        flash(message, type_)
        return redirect(url_for("auth.reset_password"))

    if request.method != "POST":
        return back_to_reset_form("No backup phrase provided", "warning")

    backup_phrase = request.form.get("backup_phrase", None)
    if not backup_phrase:
        return back_to_reset_form("Backup phrase cannot be read.")

    password, password_confirm = (
        request.form.get("password"),
        request.form.get("password_confirm"),
    )
    if not password or password != password_confirm:
        return back_to_reset_form(
            "Passwords must match, and must not be empty", "warning"
        )

    username = request.form.get("username")
    if not username:
        return back_to_reset_form("Username must be non empty", "warning")

    identity = Identity()
    result = identity.reset_user_password(username, backup_phrase, password)

    if result.success:
        _ = back_to_reset_form(
            "Password successfully changed.",
            "info",
        )
        assert result.data
        return back_to_reset_form(
            cast(str, result.data.get("backup_phrase")), "backup_phrase"
        )

    return back_to_reset_form("Username or backup phrase incorrect.", "error")


@auth.route("/register", methods=["GET", "POST"])
def register() -> str | ResponseReturnValue:
    """
    Basic form for username and password.
    Creates the account, logs in and shows the backup phrase.
    """

    def flash_warning(message: str) -> ResponseReturnValue:
        flash(message, "warning")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        identity = Identity()
        data = request.form
        username, password, password_confirm = (
            data.get("username", ""),
            data.get("password", ""),
            data.get("password_confirm"),
        )
        if not all((username, password, password_confirm)):
            return flash_warning("All field must be filled.")

        if password != password_confirm:
            return flash_warning("Password and confirm password must be identical!")

        result = identity.register_user(username, password)
        if not result.success:
            return flash_warning(f"{result.message}")

        flash(cast(str, result.data.get("backup_phrase")), "backup_phrase")
        save_identity(identity)
        session["username"] = username
        return redirect(url_for("password_manager.landing"))

    return render_template("register.html")
