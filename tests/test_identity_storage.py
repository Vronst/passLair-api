"""Which requests may leave a user identity in memcached.

Only a logged-in user may be stored. Anything else - a page view, a failed
login, a password reset - would let anonymous clients fill the cache.

Runs the real routes and helpers; only core's Identity and memcached are faked.
"""

import pytest
from flask.testing import FlaskClient
from pymemcache.test.utils import MockMemcacheClient

from tests.support import GOOD_PASSWORD, build_app, identity_entries

PROTECTED_URL = "/passwords/"


def is_logged_in(client: FlaskClient) -> bool:
    return client.get(PROTECTED_URL).status_code == 200


def test_viewing_login_page_stores_nothing(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.get("/auth/login")

    assert identity_entries(user_manager) == []


def test_failed_login_stores_nothing(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post("/auth/login", data={"username": "alice", "password": "wrong"})

    assert identity_entries(user_manager) == []


@pytest.mark.usefixtures("fake_core")
def test_repeated_failed_logins_from_new_clients_store_nothing(
    user_manager: MockMemcacheClient,
) -> None:
    # The attack: every request without a session cookie gets a fresh sid.
    app = build_app()

    for _ in range(5):
        app.test_client().post(
            "/auth/login", data={"username": "alice", "password": "wrong"}
        )

    assert identity_entries(user_manager) == []


def test_password_reset_stores_nothing(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post(
        "/auth/reset_password/new_password",
        data={
            "username": "alice",
            "backup_phrase": "some phrase",
            "password": "new",
            "password_confirm": "new",
        },
    )

    assert identity_entries(user_manager) == []


def test_successful_login_keeps_user_logged_in(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post("/auth/login", data={"username": "alice", "password": GOOD_PASSWORD})

    assert is_logged_in(client)
    assert len(identity_entries(user_manager)) == 1


def test_registering_logs_the_user_in(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post(
        "/auth/register",
        data={
            "username": "alice",
            "password": GOOD_PASSWORD,
            "password_confirm": GOOD_PASSWORD,
        },
    )

    assert is_logged_in(client)
    assert len(identity_entries(user_manager)) == 1


def test_stored_dek_is_never_plaintext(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post("/auth/login", data={"username": "alice", "password": GOOD_PASSWORD})

    [key] = identity_entries(user_manager)
    # FakeCoreIdentity's session key, as raw bytes and as stored hex.
    assert b"1234567890" not in user_manager.get(key.decode())
    assert b"1234567890".hex().encode() not in user_manager.get(key.decode())
