"""The account page shows the (unchangeable) username for every way of
getting logged in."""

from flask.testing import FlaskClient

from tests.support import GOOD_PASSWORD

USERNAME = "alice"


def test_user_page_shows_username_after_login(client: FlaskClient) -> None:
    client.post("/auth/login", data={"username": USERNAME, "password": GOOD_PASSWORD})

    body = client.get("/auth/user").get_data(as_text=True)

    assert f"<strong>{USERNAME}</strong>" in body


def test_user_page_shows_username_after_register(client: FlaskClient) -> None:
    client.post(
        "/auth/register",
        data={
            "username": USERNAME,
            "password": GOOD_PASSWORD,
            "password_confirm": GOOD_PASSWORD,
        },
    )

    body = client.get("/auth/user").get_data(as_text=True)

    assert f"<strong>{USERNAME}</strong>" in body


def test_user_page_has_no_username_field(client: FlaskClient) -> None:
    client.post("/auth/login", data={"username": USERNAME, "password": GOOD_PASSWORD})

    body = client.get("/auth/user").get_data(as_text=True)

    assert 'name="username"' not in body
