import json
import os
from typing import cast

from flask import flash, redirect, session, url_for
from flask_session.base import ServerSideSession
from passlair.core import Identity
from passlair.core.crypto import decrypt, encrypt
from pymemcache.client.base import Client
from werkzeug import Response

# Connects via internal Podman DNS using service name and default port 11211
cache = Client((os.getenv("MEMCACHED_HOST", "memcache"), 11211))


def check_login_redirect() -> Response | None:
    if not check_login_status():
        return redirect(url_for("auth.login"))

    return None


def flash_and_redirect(
    endpoint: str, message: str, category: str = "error"
) -> Response:
    flash(message, category)
    return redirect(url_for(endpoint))


def check_login_status() -> bool:
    identity = get_create_identity()
    return identity.login_status.success


def _get_session_sid() -> str:
    if (identity_id := cast(ServerSideSession, session).sid) is None:
        raise RuntimeError("Session is required to create identity manager.")

    return identity_id


def save_identity(identity: Identity) -> None:
    identity_id = _get_session_sid()
    session["init"] = True
    user_id = identity.manager.user_id
    encrypted_dek_bytes, nonce = encrypt(identity.manager.get_session_key(), DEK)
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
    identity = Identity()
    session["init"] = True
    if (user_data_string := cache.get(f"user_dek:{_get_session_sid()}")) and (
        user_data := json.loads(user_data_string)
    ):
        identity.restore_session(
            user_data.get("user_id", ""),
            decrypt(
                bytes.fromhex(user_data.get("dek", "")),
                bytes.fromhex(user_data.get("nonce", "")),
                DEK,
            ),
        )

    return identity


def remove_identity() -> None:
    if not (identity_id := cast(ServerSideSession, session).sid):
        raise RuntimeError("Nothing to remove")

    _ = cache.delete(f"user_dek:{identity_id}")
    session.clear()


def load_dek() -> bytes:
    dek_path = os.getenv("DEK_FILE_PATH", "/run/secrets/app_dek")
    try:
        with open(dek_path, "rb") as f:
            content = f.read().strip()
            return bytes.fromhex(content.decode("utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"Critical Error: DEK secret file not found at {dek_path}!")


DEK = load_dek()
