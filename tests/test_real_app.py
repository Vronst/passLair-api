"""The real passlair_api.app: wiring that build_app() in support.py leaves out,
such as Talisman, the login-state context processor and the health route.

Redis connects lazily, so importing the app needs no server. Sessions are moved
to memory for requests that would store one.
"""

import importlib
import json
from datetime import timedelta
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pymemcache.test.utils import MockMemcacheClient

from tests.support import GOOD_PASSWORD, build_app, identity_entries

HTTPS = "https://localhost"
HTTP = "http://localhost"
REDIS_PORT = 6390


@pytest.fixture
def real_app(fake_core: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Flask:
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("REDIS_PORT", str(REDIS_PORT))

    app = importlib.import_module("passlair_api.app").app
    monkeypatch.setattr(app, "session_interface", build_app().session_interface)
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", False)
    return app


@pytest.fixture
def https_client(real_app: Flask) -> FlaskClient:
    return real_app.test_client()


def log_in(client: FlaskClient) -> None:
    client.post(
        "/auth/login",
        data={"username": "alice", "password": GOOD_PASSWORD},
        base_url=HTTPS,
    )


def test_health_answers_over_plain_http_like_the_container_healthcheck(
    https_client: FlaskClient,
) -> None:
    response = https_client.get("/health", base_url=HTTP)

    assert response.status_code == 200
    assert "Set-Cookie" not in response.headers


def test_other_pages_are_forced_to_https(https_client: FlaskClient) -> None:
    response = https_client.get("/auth/login", base_url=HTTP)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("https://")


def test_redis_port_setting_is_used(real_app: Flask) -> None:
    connection = real_app.config["SESSION_REDIS"].connection_pool.connection_kwargs

    assert connection["port"] == REDIS_PORT


def test_sessions_expire_after_an_hour(real_app: Flask) -> None:
    assert real_app.permanent_session_lifetime == timedelta(hours=1)


def test_session_cookie_is_https_only(https_client: FlaskClient) -> None:
    response = https_client.get("/auth/login", base_url=HTTPS)

    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie
    assert "HttpOnly" in cookie


def test_navigation_reflects_login_state(https_client: FlaskClient) -> None:
    anonymous = https_client.get("/auth/register", base_url=HTTPS)
    assert b"/auth/logout" not in anonymous.data

    log_in(https_client)

    logged_in = https_client.get("/passwords/", base_url=HTTPS)
    assert b"/auth/logout" in logged_in.data


def test_entry_from_before_a_restart_does_not_break_any_page(
    https_client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    # The context processor reads the identity on every rendered page, so an
    # unreadable entry used to turn every page into a 500.
    log_in(https_client)
    [key] = identity_entries(user_manager)
    user_manager.set(key.decode(), json.dumps({"user_id": "Alice"}))

    for url in ("/auth/register", "/auth/login", "/auth/reset_password"):
        assert https_client.get(url, base_url=HTTPS).status_code == 200

    assert https_client.get("/passwords/", base_url=HTTPS).status_code == 302
