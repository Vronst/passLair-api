"""Vault export and import routes."""

import io

from flask import Blueprint, render_template, request, send_file
from flask.typing import ResponseReturnValue
from passlair import Exporter, Importer
from passlair.core.readers.helpers import compare_passwords
from passlair.share.formats import FORMATS
from werkzeug.exceptions import RequestEntityTooLarge

from ..helpers.functions import (
    check_login_redirect,
    flash_and_redirect,
    get_create_identity,
    no_store,
)
from ..helpers.uploads import MAX_UPLOAD_BYTES

data = Blueprint("data", __name__, template_folder="../templates", url_prefix="/data")
data.before_request(check_login_redirect)
data.after_request(no_store)


@data.errorhandler(RequestEntityTooLarge)
def upload_too_large(_: RequestEntityTooLarge) -> ResponseReturnValue:
    """Over MAX_UPLOAD_BYTES (helpers/uploads.py): back to the form, not a bare 413."""
    limit_mib = MAX_UPLOAD_BYTES // (1024 * 1024)
    return flash_and_redirect(
        "data.import_passwords",
        f"The export is too large (limit {limit_mib} MiB).",
        "warning",
    )


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
        fmt = request.form.get("format", "")
        if fmt not in FORMATS:
            return flash_and_redirect(
                "data.export_passwords", "Choose a valid export format.", "warning"
            )

        manager = get_create_identity().manager
        if not compare_passwords(
            (manager.user_id or ""), request.form.get("password", "")
        ):
            return flash_and_redirect(
                "data.export_passwords", "Wrong password", "warning"
            )

        passwords = Exporter(manager).serialize(fmt)
        file_like = io.BytesIO(passwords.encode("utf-8"))
        return send_file(
            file_like, download_name=f"password_export.{fmt}", as_attachment=True
        )

    return render_template("export.html")


@data.route("/import", methods=["GET", "POST"])
def import_passwords() -> ResponseReturnValue:
    """
    User uploads or pastes a password export and picks its format.
    Imports and redirects; read in memory, never written to disk by us.
    """
    if request.method == "POST":
        fmt = request.form.get("format", "")
        # An empty file part (no file chosen) is falsy, so the textarea wins.
        upload = request.files.get("import_file")
        raw: bytes | str = (
            upload.read() if upload else request.form.get("import_text", "")
        )
        if not raw:
            return flash_and_redirect(
                "data.import_passwords", "No data to import.", "warning"
            )

        try:
            content = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            result = Importer(get_create_identity().manager).import_text(content, fmt)
        # UnicodeDecodeError subclasses ValueError, so it must come first.
        except UnicodeDecodeError:
            return flash_and_redirect(
                "data.import_passwords", "The file must be UTF-8 text.", "warning"
            )
        # Unknown format, or core's ImportFormatError -- both user-safe messages.
        except ValueError as err:
            return flash_and_redirect("data.import_passwords", str(err), "warning")

        return flash_and_redirect(
            "data.landing",
            f"Imported {result.imported} entries, skipped {result.skipped}.",
            "info",
        )

    return render_template("import.html")
