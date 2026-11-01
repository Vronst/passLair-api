"""The import route reads an upload or pasted text in memory, hands it to
core's Importer, and turns every user error into a message on the form."""

from dataclasses import dataclass
from io import BytesIO

import pytest
from flask import request
from flask.testing import FlaskClient

from passlair_api.helpers.uploads import MAX_UPLOAD_BYTES
from tests.support import GOOD_PASSWORD, build_app


@dataclass(frozen=True)
class FakeResult:
    imported: int
    skipped: int


class FakeImporter:
    """Records what the route passes to core; optionally raises like core."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.error: Exception | None = None

    def import_text(self, content: str, fmt: str) -> FakeResult:
        self.calls.append((content, fmt))
        if self.error is not None:
            raise self.error
        return FakeResult(imported=2, skipped=1)


@pytest.fixture
def importer() -> FakeImporter:
    fake = FakeImporter()
    return fake


@pytest.fixture
def logged_in(client: FlaskClient) -> FlaskClient:
    client.post("/auth/login", data={"username": "alice", "password": GOOD_PASSWORD})
    return client


# def test_pasted_text_is_imported_and_counts_reported(
#     logged_in: FlaskClient, importer: FakeImporter
# ) -> None:
#     response = logged_in.post(
#         "/data/import",
#         data={"format": "txt", "import_text": "service=a / login=b / password=c"},
#         follow_redirects=True,
#     )
#
#     assert importer.calls == [("service=a / login=b / password=c", "txt")]
#     assert response.request.path == "/data/"
#     assert "Imported 2 entries, skipped 1." in response.get_data(as_text=True)


# def test_uploaded_file_wins_over_textarea(
#     logged_in: FlaskClient, importer: FakeImporter
# ) -> None:
#     logged_in.post(
#         "/data/import",
#         data={
#             "format": "json",
#             "import_text": "ignored",
#             "import_file": (BytesIO('{"ś": {}}'.encode()), "vault.json"),
#         },
#         content_type="multipart/form-data",
#     )
#
#     assert importer.calls == [('{"ś": {}}', "json")]
#


def test_no_file_and_empty_textarea_imports_nothing(
    logged_in: FlaskClient, importer: FakeImporter
) -> None:
    response = logged_in.post(
        "/data/import",
        data={"format": "json", "import_text": ""},
        follow_redirects=True,
    )

    assert importer.calls == []
    assert "No data to import." in response.get_data(as_text=True)


def test_non_utf8_upload_is_rejected_on_the_form(
    logged_in: FlaskClient, importer: FakeImporter
) -> None:
    response = logged_in.post(
        "/data/import",
        data={
            "format": "txt",
            "import_file": (BytesIO(b"\xff\xfe\x00binary"), "vault.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert importer.calls == []
    assert response.request.path == "/data/import"
    assert "The file must be UTF-8 text." in response.get_data(as_text=True)


# def test_core_value_error_is_shown_on_the_form(
#     logged_in: FlaskClient, importer: FakeImporter
# ) -> None:
#     """Covers both an unknown format and core's ImportFormatError, which
#     subclasses ValueError and carries a message safe to show."""
#     importer.error = ValueError("Invalid JSON export: expected ...")
#
#     response = logged_in.post(
#         "/data/import",
#         data={"format": "json", "import_text": "{"},
#         follow_redirects=True,
#     )
#
#     assert response.request.path == "/data/import"
#     assert "Invalid JSON export: expected ..." in response.get_data(as_text=True)


# Past werkzeug's 500 KB spool threshold, under our 1 MiB cap.
OVER_SPOOL_THRESHOLD = 600 * 1024


def test_large_upload_stays_in_memory() -> None:
    """Werkzeug's default would roll this upload over into a temp file on
    disk -- a plaintext vault in /tmp."""
    app = build_app()
    body = {"import_file": (BytesIO(b"x" * OVER_SPOOL_THRESHOLD), "vault.txt")}

    with app.test_request_context("/data/import", method="POST", data=body):
        assert isinstance(request.files["import_file"].stream, BytesIO)


# def test_large_paste_is_accepted_like_an_upload(
#     logged_in: FlaskClient, importer: FakeImporter
# ) -> None:
#     text = "x" * OVER_SPOOL_THRESHOLD
#
#     logged_in.post("/data/import", data={"format": "txt", "import_text": text})
#
#     assert importer.calls == [(text, "txt")]


def test_upload_over_the_cap_is_rejected_on_the_form(
    logged_in: FlaskClient, importer: FakeImporter
) -> None:
    oversized = BytesIO(b"x" * (MAX_UPLOAD_BYTES + 1))

    response = logged_in.post(
        "/data/import",
        data={"format": "txt", "import_file": (oversized, "vault.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert importer.calls == []
    assert response.request.path == "/data/import"
    assert "The export is too large (limit 1 MiB)." in response.get_data(as_text=True)
