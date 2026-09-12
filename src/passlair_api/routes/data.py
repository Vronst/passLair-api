from flask import Blueprint, redirect, render_template, url_for
from werkzeug.wrappers.response import Response

data = Blueprint("Data", __name__, template_folder="../templates", url_prefix="/data")


@data.route("/")
def landing() -> str:
    """
    Export,
    import.
    """
    return render_template("landing.html")


@data.route("/export", methods=["GET"])
def export_passwords() -> str:
    """
    Export confirmation with user password.
    """
    return render_template("export.html")


@data.route("/export", methods=["POST"])
def _export_passwords() -> Response:
    """
    Exports passwords (file download) and redirects.
    """
    return redirect(url_for("data.landing"))


@data.route("/import", methods=["GET"])
def import_passwords() -> str:
    """
    User sends or paste the password exoprt file/string.
    """
    return render_template("import.html")


@data.route("/import", methods=["POST"])
def _import_passwords() -> Response:
    """
    Imports and redirects
    """
    return redirect(url_for("data.landing"))
