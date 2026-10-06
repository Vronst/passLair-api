from typing import cast

from flask import flash, redirect, session, url_for
from flask_session.base import ServerSideSession
from passlair.core import Identity, PasswordManager
from werkzeug import Response

user_manager: dict[str, Identity] = {}
password_manager: dict[str, PasswordManager] = {}


def check_login_redirect() -> Response | None:
    if not check_login_status():
        return redirect(url_for("auth.login"))


def flash_and_redirect(
    endpoint: str, message: str, category: str = "error"
) -> Response:
    flash(message, category)
    return redirect(url_for(endpoint))


def check_login_status() -> bool:
    identity_id = cast(ServerSideSession, session).sid
    if identity_id and (identity := user_manager.get(identity_id)):
        return identity.login_status.success

    return False


def _get_session_sid() -> str:
    if (identity_id := cast(ServerSideSession, session).sid) is None:
        raise RuntimeError("Session is required to create identity manager.")

    return identity_id


def save_identity(identity: Identity) -> None:
    identity_id = _get_session_sid()
    session["init"] = True
    user_manager[identity_id] = identity


def get_create_identity() -> Identity:
    identity_id = _get_session_sid()

    if not (identity := user_manager.get(identity_id)):
        session["init"] = True
        identity = Identity()
        user_manager[identity_id] = identity

    return identity


def remove_identity() -> None:
    if not (identity_id := cast(ServerSideSession, session).sid):
        raise RuntimeError("Nothing to remove")

    del user_manager[identity_id]
    password_manager.pop(identity_id, None)
    session.clear()


def get_create_password_manager() -> PasswordManager:
    manager_id = _get_session_sid()
    if not (manager := password_manager.get(manager_id)):
        manager = PasswordManager(get_create_identity().manager)
        password_manager[manager_id] = manager

    return manager
