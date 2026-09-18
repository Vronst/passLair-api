from flask import Blueprint, render_template, url_for
from werkzeug.utils import redirect
from werkzeug.wrappers.response import Response

password_manager = Blueprint(
    "password_manager",
    __name__,
    template_folder="../templates",
    url_prefix="/passwords",
)


@password_manager.route("/")
def landing() -> str:
    """
    Save new password,
    edit password,
    delete password.
    """
    return render_template("landing.html")


@password_manager.route("/save", methods=["GET"])
def save_password() -> str:
    """
    Basic form to save service, login and password.
    """
    return render_template("passwords.html")


@password_manager.route("/save", methods=["POST"])
def _save_password() -> Response:
    """
    Save result of the save form.
    """
    return redirect(url_for("password_manager.landing"))


@password_manager.route("/edit", methods=["GET"])
def edit_password() -> str:
    """
    Form allowing to edit password details.
    """
    return render_template("passwords.html")


@password_manager.route("/edit", methods=["POST"])
def _edit_password() -> Response:
    """
    Save result of the edit form.
    """
    return redirect(url_for("password_manager.landing"))


@password_manager.route("/delete", methods=["GET"])
def delete_password() -> str:
    """
    Basic form to confirm deletion.
    """
    return render_template("passwords.html")


@password_manager.route("/delete", methods=["POST"])
def _delete_password() -> Response:
    """
    Deletes password and redirects.
    """
    return redirect(url_for("password_manager.landing"))
