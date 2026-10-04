"""Tests for the login_required decorator (src/passlair_api/helpers/wrapers.py).

Builds a minimal, throwaway Flask app instead of importing the real
passlair_api.app, since that app hard-wires a real Redis client at import
time. The session backend here is cachelib's in-memory SimpleCache, so
these tests need no external services.
"""

import pytest
from cachelib import SimpleCache
from flask import Blueprint, Flask
from flask_session import Session

from passlair_api.helpers import functions as identity_functions
from passlair_api.helpers.wrapers import login_required


class FakeLoginStatus:
    def __init__(self, success: bool) -> None:
        self.success = success


class FakeIdentity:
    def __init__(self, success: bool) -> None:
        self.login_status = FakeLoginStatus(success)


def make_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test",
        SESSION_TYPE="cachelib",
        SESSION_CACHELIB=SimpleCache(),
        TESTING=True,
    )
    Session(app)

    auth = Blueprint("auth", __name__)

    @auth.route("/login")
    def login() -> str:
        return "login page"

    app.register_blueprint(auth)

    @app.route("/protected")
    @login_required
    def protected() -> str:
        return "secret"

    return app


def test_login_required_blocks_anonymous_request() -> None:
    app = make_app()
    client = app.test_client()

    response = client.get("/protected")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_login_required_allows_logged_in_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app()
    client = app.test_client()

    # Establishing the session is what assigns it a sid. NOTE: a session
    # containing only Flask-Session's internal "_permanent" key is treated
    # as empty (see ServerSideSession.__bool__ in flask_session/base.py) and
    # never gets cookie'd to the client, so the sid would never survive to
    # the next request. Writing a real key here mirrors what
    # save_identity() does with session["init"].
    with client.session_transaction() as sess:
        sess["_test_marker"] = True
        sid = sess.sid

    # login_required's check reads identity_functions.user_manager directly,
    # so planting a "logged in" identity there is what a real login() call
    # would have done via save_identity(). setitem undoes it after the
    # test, since the dict is module-global and shared across tests.
    monkeypatch.setitem(
        identity_functions.user_manager, sid, FakeIdentity(success=True)
    )

    response = client.get("/protected")

    assert response.status_code == 200
    assert response.data == b"secret"


def test_login_required_blocks_user_with_failed_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app()
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["_test_marker"] = True
        sid = sess.sid

    monkeypatch.setitem(
        identity_functions.user_manager, sid, FakeIdentity(success=False)
    )

    response = client.get("/protected")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
