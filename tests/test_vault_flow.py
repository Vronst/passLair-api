"""Whole user journeys through the real core, crypto and a temporary database.

Only memcached is faked. Unlike the fake-core tests, these fail if a restored
session can't actually decrypt the vault.
"""

import io
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from flask.testing import FlaskClient
from passlair.core.database import db

from tests.support import build_app

USERNAME = "alice"
PASSWORD = "correct horse battery staple"
ENTRY = {"service": "github", "login": "alice@example.com", "password": "hunter2-xyz"}
LANDING = "/passwords/"


@pytest.fixture
def real_db(tmp_path: Path) -> Iterator[None]:
    db.init_sqlite(str(tmp_path / "vault.db"), force=True)
    yield
    db.dispose()


@pytest.fixture
def user(real_db: None) -> FlaskClient:
    """A browser logged in as a freshly registered user."""
    client = build_app().test_client()
    response = client.post(
        "/auth/register",
        data={
            "username": USERNAME,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
        },
    )
    assert response.status_code == 302
    return client


def save_entry(client: FlaskClient) -> None:
    response = client.post("/passwords/save", data=ENTRY)
    assert response.status_code == 302


def text(client: FlaskClient, url: str, form: dict[str, str]) -> str:
    response = client.post(url, data=form, follow_redirects=True)
    return response.get_data(as_text=True)


def test_saved_password_can_be_retrieved(user: FlaskClient) -> None:
    save_entry(user)

    body = text(user, "/passwords/retrieve", {"service": ENTRY["service"]})

    assert ENTRY["login"] in body
    assert ENTRY["password"] in body


def test_saving_again_overwrites_the_entry(user: FlaskClient) -> None:
    save_entry(user)
    user.post("/passwords/save", data=ENTRY | {"password": "replacement"})

    body = text(user, "/passwords/retrieve", {"service": ENTRY["service"]})

    assert "replacement" in body
    assert ENTRY["password"] not in body


@pytest.mark.parametrize("missing", ["service", "login", "password"])
def test_save_requires_all_fields(user: FlaskClient, missing: str) -> None:
    body = text(user, "/passwords/save", ENTRY | {missing: ""})

    assert "All fields must be filled" in body


def test_retrieve_requires_a_service(user: FlaskClient) -> None:
    assert "Service must not be empty" in text(user, "/passwords/retrieve", {})


def test_retrieving_unknown_service_shows_a_warning(user: FlaskClient) -> None:
    body = text(user, "/passwords/retrieve", {"service": "nothing-here"})

    assert "flash-error" in body


def test_deleting_redirects_with_a_message_and_removes_the_entry(
    user: FlaskClient,
) -> None:
    save_entry(user)

    response = user.post("/passwords/delete", data={"service": ENTRY["service"]})

    assert response.status_code == 302
    assert response.headers["Location"].endswith(LANDING)
    assert "flash-info" in user.get(LANDING).get_data(as_text=True)

    body = text(user, "/passwords/retrieve", {"service": ENTRY["service"]})
    assert ENTRY["password"] not in body


def test_deleting_unknown_service_shows_a_warning(user: FlaskClient) -> None:
    response = user.post("/passwords/delete", data={"service": "nothing-here"})

    assert response.status_code == 200
    assert "flash-error" in response.get_data(as_text=True)


def test_delete_requires_a_service(user: FlaskClient) -> None:
    body = text(user, "/passwords/delete", {})

    assert "Service not found" in body


def test_users_cannot_read_each_others_entries(user: FlaskClient) -> None:
    save_entry(user)
    other = user.application.test_client()
    other.post(
        "/auth/register",
        data={"username": "bob", "password": "x" * 12, "password_confirm": "x" * 12},
    )

    body = text(other, "/passwords/retrieve", {"service": ENTRY["service"]})

    assert ENTRY["password"] not in body


def test_vault_stays_readable_after_logging_out_and_in(user: FlaskClient) -> None:
    save_entry(user)
    user.post("/auth/logout")

    user.post("/auth/login", data={"username": USERNAME, "password": PASSWORD})

    body = text(user, "/passwords/retrieve", {"service": ENTRY["service"]})
    assert ENTRY["password"] in body


def test_vault_stays_readable_after_a_password_change(user: FlaskClient) -> None:
    save_entry(user)
    user.post(
        "/auth/user",
        data={
            "current_password": PASSWORD,
            "password": "brand-new-password",
            "password_confirm": "brand-new-password",
        },
    )
    user.post("/auth/logout")

    user.post("/auth/login", data={"username": USERNAME, "password": PASSWORD})
    assert user.get(LANDING).status_code == 302

    user.post(
        "/auth/login",
        data={"username": USERNAME, "password": "brand-new-password"},
    )
    body = text(user, "/passwords/retrieve", {"service": ENTRY["service"]})
    assert ENTRY["password"] in body


def export(client: FlaskClient, fmt: str, password: str = PASSWORD) -> bytes:
    response = client.post("/data/export", data={"format": fmt, "password": password})
    assert response.status_code == 200
    assert f"password_export.{fmt}" in response.headers["Content-Disposition"]
    return response.data


def test_export_json_contains_the_entry(user: FlaskClient) -> None:
    save_entry(user)

    exported = json.loads(export(user, "json"))

    assert exported[ENTRY["service"]]["password"] == ENTRY["password"]


@pytest.mark.parametrize("fmt", ["csv", "txt"])
def test_export_other_formats_contain_the_entry(user: FlaskClient, fmt: str) -> None:
    save_entry(user)

    assert ENTRY["password"].encode() in export(user, fmt)


def test_export_with_wrong_password_shows_why_on_the_export_page(
    user: FlaskClient,
) -> None:
    save_entry(user)

    response = user.post(
        "/data/export",
        data={"format": "json", "password": "wrong"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)

    assert "Wrong password" in body
    assert "Export passwords" in body
    assert ENTRY["password"] not in body


@pytest.mark.parametrize(
    "form",
    [{"format": "bogus"}, {}],
    ids=["unknown-format", "missing-format"],
)
def test_export_with_bad_format_is_refused_without_crashing(
    user: FlaskClient, form: dict[str, str]
) -> None:
    response = user.post(
        "/data/export", data=form | {"password": PASSWORD}, follow_redirects=True
    )

    assert response.status_code == 200
    assert "Choose a valid export format." in response.get_data(as_text=True)


def test_export_can_be_imported_into_another_account(user: FlaskClient) -> None:
    save_entry(user)
    exported = export(user, "json")
    other = user.application.test_client()
    other.post(
        "/auth/register",
        data={"username": "bob", "password": "x" * 12, "password_confirm": "x" * 12},
    )

    response = other.post(
        "/data/import",
        data={"format": "json", "import_file": (io.BytesIO(exported), "export.json")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert "Imported 1 entries" in response.get_data(as_text=True)
    body = text(other, "/passwords/retrieve", {"service": ENTRY["service"]})
    assert ENTRY["password"] in body


@pytest.mark.parametrize(
    "url",
    ["/passwords/", "/passwords/retrieve", "/data/export", "/auth/user"],
)
def test_sensitive_pages_are_not_cached(user: FlaskClient, url: str) -> None:
    assert user.get(url).headers["Cache-Control"] == "no-store"


def test_retrieved_password_response_is_not_cached(user: FlaskClient) -> None:
    save_entry(user)

    response = user.post("/passwords/retrieve", data={"service": ENTRY["service"]})

    assert response.headers["Cache-Control"] == "no-store"


def test_exported_file_is_not_cached(user: FlaskClient) -> None:
    response = user.post("/data/export", data={"format": "json", "password": PASSWORD})

    assert response.headers["Cache-Control"] == "no-store"
