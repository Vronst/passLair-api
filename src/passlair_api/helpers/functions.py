from typing import cast

from flask import redirect, session, url_for
from flask_session.base import ServerSideSession
from passlair.core import Identity
from werkzeug import Response

user_manager: dict[str, Identity] = {}


def check_login_redirect() -> Response | None:
    if not check_login_status():
        return redirect(url_for("auth.login"))


def check_login_status() -> bool:
    identity_id = cast(ServerSideSession, session).sid
    if identity_id and (identity := user_manager.get(identity_id)):
        return identity.login_status.success

    return False


def get_create_identity() -> Identity:
    if (identity_id := cast(ServerSideSession, session).sid) is None:
        raise RuntimeError("Session is required to create identity manager.")

    if not (identity := user_manager.get(identity_id)):
        session["init"] = True
        identity = Identity()
        user_manager[identity_id] = identity

    return identity


def remove_identity() -> None:
    if not (identity_id := cast(ServerSideSession, session).sid):
        raise RuntimeError("Nothing to remove")

    del user_manager[identity_id]
    session.clear()
