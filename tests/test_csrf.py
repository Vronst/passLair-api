"""Every POST form carries a CSRF token, and a POST without one is refused."""

import re
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from tests.support import GOOD_PASSWORD, build_app

TEMPLATES = Path(__file__).parent.parent / "src" / "passlair_api" / "templates"
TOKEN_FIELD = re.compile(r'name="csrf_token" value="([^"]+)"')
POST_FORM = re.compile(
    r'<form method="post"[^>]*>(.*?)</form>', re.DOTALL | re.IGNORECASE
)
LOGIN = {"username": "alice", "password": GOOD_PASSWORD}


@pytest.fixture
def csrf_client(fake_core: None) -> FlaskClient:
    return build_app(csrf=True).test_client()


def test_post_without_token_is_rejected(csrf_client: FlaskClient) -> None:
    response = csrf_client.post("/auth/login", data=LOGIN)

    assert response.status_code == 400


def test_post_with_token_from_the_rendered_form_logs_in(
    csrf_client: FlaskClient,
) -> None:
    page = csrf_client.get("/auth/login").get_data(as_text=True)
    match = TOKEN_FIELD.search(page)
    assert match is not None

    response = csrf_client.post(
        "/auth/login", data={**LOGIN, "csrf_token": match.group(1)}
    )

    assert response.status_code == 302
    assert response.location == "/passwords/"


@pytest.mark.parametrize(
    "template", sorted(TEMPLATES.glob("*.html")), ids=lambda path: path.name
)
def test_every_post_form_has_a_csrf_field(template: Path) -> None:
    """Catches a new form at test time; CSRFProtect would only reject it
    once someone submits it."""
    for form in POST_FORM.findall(template.read_text()):
        assert 'name="csrf_token"' in form, f"POST form in {template.name}"
