"""Which requests may leave an Identity in helpers.functions.user_manager.

The store lives in process memory and nothing evicts from it, so only a
logged-in user may be stored. Anything else - a page view, a failed login,
a password reset - would let anonymous clients grow it without bound.

Runs the real routes and the real store; only core's Identity is faked.
"""

import pytest
from flask.testing import FlaskClient
from pymemcache.test.utils import MockMemcacheClient

from tests.support import build_app

PROTECTED_URL = "/passwords/"


def is_logged_in(client: FlaskClient) -> bool:
    return client.get(PROTECTED_URL).status_code == 200


def test_viewing_login_page_stores_nothing(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.get("/auth/login")
    assert (user_manager.stats().get("curr_items", 0)) == 0


def test_failed_login_stores_nothing(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post("/auth/login", data={"username": "alice", "password": "wrong"})

    assert (user_manager.stats().get("curr_items", 0)) == 0


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

    assert (user_manager.stats().get("curr_items", 0)) == 0


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

    assert (user_manager.stats().get("curr_items", 0)) == 0


# def test_successful_login_keeps_user_logged_in(
#     client: FlaskClient, user_manager: MockMemcacheClient
# ) -> None:
#     client.post("/auth/login", data={"username": "alice", "password": GOOD_PASSWORD})
#
#     assert is_logged_in(client)
#     assert (user_manager.stats().get("curr_items", 0)) == 1
#
#
# def test_registering_logs_the_user_in(
#     client: FlaskClient, user_manager: MockMemcacheClient
# ) -> None:
#     client.post(
#         "/auth/register",
#         data={
#             "username": "alice",
#             "password": GOOD_PASSWORD,
#             "password_confirm": GOOD_PASSWORD,
#         },
#     )
#
#     assert is_logged_in(client)
#     assert (user_manager.stats().get("curr_items", 0)) == 1
