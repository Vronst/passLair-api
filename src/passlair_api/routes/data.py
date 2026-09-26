from flask import Blueprint, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ..helpers.functions import check_login_redirect

data = Blueprint("data", __name__, template_folder="../templates", url_prefix="/data")
data.before_request(check_login_redirect)


@data.route("/")
def landing() -> str:
    """
    Export,
    import.
    """
    return render_template("landing.html")


@data.route("/export", methods=["GET", "POST"])
def export_passwords() -> ResponseReturnValue:
    """
    Export confirmation with user password.
    Exports passwords (file download) and redirects.
    """
    if request.method == "POST":
        return redirect(url_for("data.landing"))

    return render_template("export.html")


@data.route("/import", methods=["GET", "POST"])
def import_passwords() -> ResponseReturnValue:
    """
    User sends or paste the password exoprt file/string.
    Imports and redirects
    """
    if request.method == "POST":
        return redirect(url_for("data.landing"))

    return render_template("import.html")
