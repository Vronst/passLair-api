from typing import cast

from cachelib import SimpleCache
from flask import redirect, session, url_for
from flask_session.base import ServerSideSession
from passlair import Identity
from werkzeug import Response

# Create a cache instance
cache = SimpleCache()


def check_login_redirect() -> Response | None:
    if not check_login_status():
        return redirect(url_for("auth.login"))


def check_login_status() -> bool:
    identity_id = cast(ServerSideSession, session).sid
    if identity_id and (identity := cache.get(identity_id)):
        return identity.login_status.success

    return False


def get_create_identity() -> Identity:
    if (identity_id := cast(ServerSideSession, session).sid) is None:
        raise RuntimeError("Session is required to create identity manager.")

    if not (identity := cache.get(identity_id)):
        identity = Identity()
        cache.set(identity_id, identity)

    return identity
