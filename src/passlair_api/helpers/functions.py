from flask import redirect, session, url_for
from werkzeug import Response


def check_login() -> Response | None:
    if session.get("current_user") is None:
        return redirect(url_for("auth.login"))
