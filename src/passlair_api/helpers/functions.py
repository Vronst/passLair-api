"""Helper functions"""

import json
import logging
import os
from typing import cast

from flask import current_app, flash, redirect, request, session, url_for
from flask_session.base import ServerSideSession, ServerSideSessionInterface
from passlair.core import Identity
from passlair.core.crypto import decrypt, encrypt
from pymemcache.client.base import PooledClient
from werkzeug import Response

logger = logging.getLogger(__name__)

CACHE_TIMEOUT_SECONDS = 2
LOGIN_ATTEMPT_LIMIT = 10
LOGIN_ATTEMPT_WINDOW_SECONDS = 900


def _load_wrap_key() -> bytes:
    """The key protecting user DEKs in memcached; all workers must share it."""
    try:
        return bytes.fromhex(os.environ["SESSION_WRAP_KEY"])
    except KeyError:
        raise RuntimeError(
            "SESSION_WRAP_KEY is not set. Start gunicorn with gunicorn_config.py, "
            "which generates one key for all workers."
        ) from None


def _build_cache(server: tuple[str, int]) -> PooledClient:
    """A pool, because gunicorn threads must not share one memcached socket."""
    return PooledClient(
        server,
        connect_timeout=CACHE_TIMEOUT_SECONDS,
        timeout=CACHE_TIMEOUT_SECONDS,
        default_noreply=False,
    )


SESSION_WRAP_KEY = _load_wrap_key()
# Connects via internal Podman DNS using service name and default port 11211
cache = _build_cache((os.getenv("MEMCACHED_HOST", "memcache"), 11211))


def no_store(response: Response) -> Response:
    """Keeps pages that can show passwords or backup phrases out of caches."""
    response.headers["Cache-Control"] = "no-store"
    return response


def _login_attempts_key() -> str:
    # nginx overwrites X-Real-IP, and only nginx can reach the app.
    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    return f"login_failures:{client_ip}"


def login_attempts_exceeded() -> bool:
    """True once this client used up its failed logins for the window."""
    failures = cache.get(_login_attempts_key())
    return int(failures or 0) >= LOGIN_ATTEMPT_LIMIT


def record_failed_login() -> None:
    """Counts a failure. Success doesn't reset it, or an attacker with their
    own account could log in between guesses to keep guessing forever."""
    key = _login_attempts_key()
    cache.add(key, 0, expire=LOGIN_ATTEMPT_WINDOW_SECONDS)
    cache.incr(key, 1)


def check_login_redirect() -> Response | None:
    """Used for requireing to be loged in."""
    if not check_login_status():
        return redirect(url_for("auth.login"))

    return None


def flash_and_redirect(
    endpoint: str, message: str, category: str = "error"
) -> Response:
    """Allows for quick flash and redirect."""
    flash(message, category)
    return redirect(url_for(endpoint))


def check_login_status() -> bool:
    """Helper to check if user is logged in."""
    identity = get_create_identity()
    return identity.login_status.success


def _get_session_sid() -> str:
    if (identity_id := cast(ServerSideSession, session).sid) is None:
        raise RuntimeError("Session is required to create identity manager.")

    return identity_id


def save_identity(identity: Identity) -> None:
    """Saves current user identity data - allows for keeping up session."""
    session["init"] = True
    # A new id at login stops a session id planted beforehand from becoming
    # logged in. regenerate() ignores empty sessions, hence "init" above.
    interface = current_app.session_interface
    if not isinstance(interface, ServerSideSessionInterface):
        raise TypeError("Flask-Session is required to regenerate the session id.")
    interface.regenerate(cast(ServerSideSession, session))
    identity_id = _get_session_sid()
    user_id = identity.manager.user_id
    encrypted_dek_bytes, nonce = encrypt(
        identity.manager.get_session_key(), SESSION_WRAP_KEY
    )
    cache.set(
        f"user_dek:{identity_id}",
        json.dumps(
            {
                "user_id": user_id,
                "dek": encrypted_dek_bytes.hex(),
                "nonce": nonce.hex(),
            }
        ),
        expire=1800,
    )


def get_create_identity() -> Identity:
    """Creates session with Identity or restores it."""
    identity = Identity()
    key = f"user_dek:{_get_session_sid()}"
    if not (user_data_string := cache.get(key)):
        return identity

    try:
        user_data = json.loads(user_data_string)
        user_id = user_data["user_id"]
        dek = decrypt(
            bytes.fromhex(user_data["dek"]),
            bytes.fromhex(user_data["nonce"]),
            SESSION_WRAP_KEY,
        )
    # An entry written under an earlier key, e.g. before a restart, can never
    # be read again, so the user has to log in again.
    except (ValueError, KeyError, TypeError) as err:
        logger.warning("Discarding unreadable session entry: %s", type(err).__name__)
        cache.delete(key)
        return identity

    identity.restore_session(user_id, dek)
    return identity


def remove_identity() -> None:
    """Removes identity data."""
    if not (identity_id := cast(ServerSideSession, session).sid):
        raise RuntimeError("Nothing to remove")

    _ = cache.delete(f"user_dek:{identity_id}")
    session.clear()
