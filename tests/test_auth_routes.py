"""Login, logout, registration and password change through the real routes."""

import pytest
from flask.testing import FlaskClient
from pymemcache.test.utils import MockMemcacheClient

from passlair_api.helpers.functions import LOGIN_ATTEMPT_LIMIT
from tests.support import GOOD_PASSWORD, FakeCoreIdentity, build_app, identity_entries

LOGIN = {"username": "alice", "password": GOOD_PASSWORD}
BAD_LOGIN = {"username": "alice", "password": "wrong"}
REGISTER = {
    "username": "alice",
    "password": GOOD_PASSWORD,
    "password_confirm": GOOD_PASSWORD,
}
PROTECTED_URL = "/passwords/"


def session_cookie(client: FlaskClient) -> str:
    cookie = client.get_cookie("session")
    assert cookie is not None
    return cookie.value


@pytest.mark.parametrize(
    ("url", "form"),
    [("/auth/login", LOGIN), ("/auth/register", REGISTER)],
    ids=["login", "register"],
)
def test_session_id_planted_before_login_stays_logged_out(
    client: FlaskClient, url: str, form: dict[str, str]
) -> None:
    client.get(url)
    planted = session_cookie(client)

    client.post(url, data=form)

    assert session_cookie(client) != planted
    assert client.get(PROTECTED_URL).status_code == 200

    other_browser = client.application.test_client()
    other_browser.set_cookie("session", planted)
    assert other_browser.get(PROTECTED_URL).status_code == 302


def test_session_data_survives_the_new_session_id(client: FlaskClient) -> None:
    client.post("/auth/register", data=REGISTER)

    body = client.get("/auth/user").get_data(as_text=True)

    assert "<strong>alice</strong>" in body


def test_anonymous_redirect_creates_no_session(client: FlaskClient) -> None:
    response = client.get(PROTECTED_URL)

    assert response.status_code == 302
    assert "Set-Cookie" not in response.headers


def test_logout_removes_the_identity(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post("/auth/login", data=LOGIN)

    response = client.post("/auth/logout")

    assert response.headers["Location"].endswith("/auth/login")
    assert identity_entries(user_manager) == []
    assert client.get(PROTECTED_URL).status_code == 302


def test_logout_page_does_not_log_out(client: FlaskClient) -> None:
    client.post("/auth/login", data=LOGIN)

    assert client.get("/auth/logout").status_code == 200
    assert client.get(PROTECTED_URL).status_code == 200


def test_logged_in_user_is_redirected_away_from_login(client: FlaskClient) -> None:
    client.post("/auth/login", data=LOGIN)

    response = client.get("/auth/login")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(PROTECTED_URL)


@pytest.mark.parametrize(
    ("form", "message"),
    [
        ({"password": "x", "password_confirm": "x"}, "All field must be filled."),
        (
            {"username": "alice", "password": "x", "password_confirm": "y"},
            "must be identical",
        ),
    ],
    ids=["missing-username", "passwords-differ"],
)
def test_invalid_registration_is_rejected(
    client: FlaskClient,
    user_manager: MockMemcacheClient,
    form: dict[str, str],
    message: str,
) -> None:
    response = client.post("/auth/register", data=form, follow_redirects=True)

    assert message in response.get_data(as_text=True)
    assert identity_entries(user_manager) == []


def post_password_change(client: FlaskClient, **overrides: str) -> str:
    form = {
        "current_password": GOOD_PASSWORD,
        "password": "new",
        "password_confirm": "new",
    } | overrides
    response = client.post("/auth/user", data=form, follow_redirects=True)
    return response.get_data(as_text=True)


def test_password_change_shows_new_backup_phrase(client: FlaskClient) -> None:
    client.post("/auth/login", data=LOGIN)

    body = post_password_change(client)

    assert "new-backup-phrase" in body
    assert "Password changed successfully." in body


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"current_password": ""}, "Required fields are missing."),
        ({"password_confirm": "other"}, "New passwords do not match"),
        ({"current_password": "wrong"}, "Old password incorrect."),
    ],
    ids=["missing-field", "confirm-differs", "wrong-current"],
)
def test_rejected_password_change_explains_why(
    client: FlaskClient, overrides: dict[str, str], message: str
) -> None:
    client.post("/auth/login", data=LOGIN)

    body = post_password_change(client, **overrides)

    assert message in body
    assert "new-backup-phrase" not in body


def test_password_change_requires_login(client: FlaskClient) -> None:
    response = client.post("/auth/user", data={})

    assert response.headers["Location"].endswith("/auth/login")


def fail_logins(client: FlaskClient, times: int, ip: str = "203.0.113.1") -> None:
    for _ in range(times):
        client.post("/auth/login", data=BAD_LOGIN, headers={"X-Real-IP": ip})


def test_correct_password_is_refused_once_the_limit_is_reached(
    client: FlaskClient,
) -> None:
    fail_logins(client, LOGIN_ATTEMPT_LIMIT)

    response = client.post(
        "/auth/login", data=LOGIN, headers={"X-Real-IP": "203.0.113.1"}
    )

    assert response.status_code == 429
    assert "Too many failed attempts" in response.get_data(as_text=True)
    assert client.get(PROTECTED_URL).status_code == 302


def test_login_works_just_below_the_limit(client: FlaskClient) -> None:
    fail_logins(client, LOGIN_ATTEMPT_LIMIT - 1)

    response = client.post(
        "/auth/login", data=LOGIN, headers={"X-Real-IP": "203.0.113.1"}
    )

    assert response.status_code == 302
    assert client.get(PROTECTED_URL).status_code == 200


def test_blocked_attempts_skip_the_password_check(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fail_logins(client, LOGIN_ATTEMPT_LIMIT)

    def must_not_run(*_: object) -> None:
        pytest.fail("password was checked for a blocked client")

    monkeypatch.setattr(FakeCoreIdentity, "login", must_not_run)

    fail_logins(client, 1)


def test_limit_only_affects_the_offending_client(client: FlaskClient) -> None:
    fail_logins(client, LOGIN_ATTEMPT_LIMIT)

    response = client.post(
        "/auth/login", data=LOGIN, headers={"X-Real-IP": "203.0.113.2"}
    )

    assert response.status_code == 302


@pytest.mark.usefixtures("fake_core")
def test_limit_cannot_be_avoided_by_dropping_the_session_cookie() -> None:
    app = build_app()

    for _ in range(LOGIN_ATTEMPT_LIMIT):
        app.test_client().post("/auth/login", data=BAD_LOGIN)

    response = app.test_client().post("/auth/login", data=BAD_LOGIN)

    assert response.status_code == 429


def test_successful_login_does_not_reset_the_count(client: FlaskClient) -> None:
    # Otherwise an attacker's own account would allow unlimited guessing.
    fail_logins(client, LOGIN_ATTEMPT_LIMIT - 1)
    client.post("/auth/login", data=LOGIN, headers={"X-Real-IP": "203.0.113.1"})
    client.post("/auth/logout")

    fail_logins(client, 1)

    response = client.post(
        "/auth/login", data=LOGIN, headers={"X-Real-IP": "203.0.113.1"}
    )
    assert response.status_code == 429
