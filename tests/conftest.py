import pytest
from flask.testing import FlaskClient
from pymemcache.test.utils import MockMemcacheClient

# Create a fully functional in-memory mock memcached client
from passlair_api.helpers import functions as identity_functions
from passlair_api.routes import auth as auth_routes
from tests.support import FakeCoreIdentity, build_app


@pytest.fixture(autouse=True)
def user_manager(monkeypatch: pytest.MonkeyPatch) -> MockMemcacheClient:
    """Fresh identity store per test, since the real one is module-global."""
    store = MockMemcacheClient()
    monkeypatch.setattr(identity_functions, "cache", store)
    return store


@pytest.fixture
def fake_core(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace core's Identity everywhere the app constructs one."""
    monkeypatch.setattr(identity_functions, "Identity", FakeCoreIdentity)
    monkeypatch.setattr(auth_routes, "Identity", FakeCoreIdentity)


@pytest.fixture
def client(fake_core: None) -> FlaskClient:
    """Client for the real routes and identity store, backed by the fake core."""
    return build_app().test_client()
