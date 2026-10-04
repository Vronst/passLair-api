"""Tests for the single-form password reset (POST /auth/reset_password/new_password).

Like test_login_required.py, this builds a throwaway Flask app instead of
importing passlair_api.app, which wires up Redis and a database at import
time. Core is replaced by a fake identity, so these tests only cover what
the route does with the form and with core's result.
"""

import pytest
from cachelib import SimpleCache
from flask import Flask
from flask.testing import FlaskClient
from flask_session import Session
from passlair.dataclasses.facade_result import FacadeResult

from passlair_api.routes import auth as auth_routes
from passlair_api.routes.auth import auth
from passlair_api.routes.data import data
from passlair_api.routes.password_manager import password_manager

RESET_URL = "/auth/reset_password/new_password"

USERNAME = "alice"
PHRASE = "old backup phrase words"
NEW_PHRASE = "fresh backup phrase words"
NEW_PASSWORD = "new-password"

VALID_FORM = {
    "username": USERNAME,
    "backup_phrase": PHRASE,
    "password": NEW_PASSWORD,
    "password_confirm": NEW_PASSWORD,
}


class FakeIdentity:
    def __init__(self, result: FacadeResult) -> None:
        self.result = result
        self.reset_calls: list[tuple[str, str, str]] = []

    def reset_user_password(
        self, username: str, backup_phrase: str, new_password: str
    ) -> FacadeResult:
        self.reset_calls.append((username, backup_phrase, new_password))
        return self.result


def success() -> FacadeResult:
    return FacadeResult(
        success=True, message="Password was reset.", data={"backup_phrase": NEW_PHRASE}
    )


def failure(message: str) -> FacadeResult:
    return FacadeResult(success=False, message=message, data={})


def make_client(monkeypatch: pytest.MonkeyPatch, identity: FakeIdentity) -> FlaskClient:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test",
        SESSION_TYPE="cachelib",
        SESSION_CACHELIB=SimpleCache(),
        TESTING=True,
    )
    Session(app)
    # Real blueprints, because base.html links to all of them.
    app.register_blueprint(auth)
    app.register_blueprint(password_manager)
    app.register_blueprint(data)

    monkeypatch.setattr(auth_routes, "get_create_identity", lambda: identity)
    return app.test_client()


def post_reset(client: FlaskClient, form: dict[str, str]) -> str:
    response = client.post(RESET_URL, data=form, follow_redirects=True)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_reset_passes_form_fields_to_core(monkeypatch: pytest.MonkeyPatch) -> None:
    identity = FakeIdentity(success())
    client = make_client(monkeypatch, identity)

    post_reset(client, VALID_FORM)

    assert identity.reset_calls == [(USERNAME, PHRASE, NEW_PASSWORD)]


def test_successful_reset_shows_new_backup_phrase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(monkeypatch, FakeIdentity(success()))

    body = post_reset(client, VALID_FORM)

    assert 'id="backup-phrase-dialog"' in body
    assert NEW_PHRASE in body


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"password_confirm": "something-else"}, id="passwords-differ"),
        pytest.param({"password": "", "password_confirm": ""}, id="empty-password"),
        pytest.param({"backup_phrase": ""}, id="empty-phrase"),
        pytest.param({"username": ""}, id="empty-username"),
    ],
)
def test_invalid_form_is_rejected_before_core(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, str]
) -> None:
    identity = FakeIdentity(success())
    client = make_client(monkeypatch, identity)

    body = post_reset(client, VALID_FORM | overrides)

    assert identity.reset_calls == []
    assert 'class="flash-error"' in body
    assert 'id="backup-phrase-dialog"' not in body


def test_failed_reset_shows_error_without_new_phrase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client(monkeypatch, FakeIdentity(failure("Decryption failed")))

    body = post_reset(client, VALID_FORM)

    assert 'class="flash-error"' in body
    assert 'id="backup-phrase-dialog"' not in body


def test_unknown_user_and_wrong_phrase_look_identical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Different error text for "no such user" vs "wrong phrase" would let
    # anyone probe which usernames exist.
    unknown_user = post_reset(
        make_client(monkeypatch, FakeIdentity(failure("User doesn't exists!"))),
        VALID_FORM,
    )
    wrong_phrase = post_reset(
        make_client(monkeypatch, FakeIdentity(failure("Decryption failed"))),
        VALID_FORM,
    )

    assert unknown_user == wrong_phrase
