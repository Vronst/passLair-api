"""Shared test setup.

passlair_api.app isn't imported in tests because it wires up Redis and a
database at import time, so tests build a throwaway app instead.
"""

from cachelib import SimpleCache
from flask import Flask
from flask_session import Session
from passlair.dataclasses.facade_result import FacadeResult

from passlair_api.routes.auth import auth
from passlair_api.routes.data import data
from passlair_api.routes.password_manager import password_manager


def build_app() -> Flask:
    """App with the real blueprints (base.html links to all of them) and an
    in-memory session backend."""
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test",
        SESSION_TYPE="cachelib",
        SESSION_CACHELIB=SimpleCache(),
        TESTING=True,
    )
    Session(app)
    app.register_blueprint(auth)
    app.register_blueprint(password_manager)
    app.register_blueprint(data)
    return app


GOOD_PASSWORD = "right-password"


class FakeCoreIdentity:
    """Stands in for passlair.core.Identity: no database, same login state."""

    def __init__(self, *_: object, **__: object) -> None:
        self._logged_in = False

    @property
    def login_status(self) -> FacadeResult:
        return FacadeResult(success=self._logged_in, message="", data={})

    def login(self, username: str, password: str) -> FacadeResult:
        self._logged_in = password == GOOD_PASSWORD
        return FacadeResult(success=self._logged_in, message="", data={})

    def register_user(self, login: str, password: str) -> FacadeResult:
        # Core logs the new user in as part of registering.
        self._logged_in = True
        return FacadeResult(success=True, message="", data={"backup_phrase": "p"})

    def reset_user_password(
        self, username: str, backup_phrase: str, new_password: str
    ) -> FacadeResult:
        return FacadeResult(success=False, message="Decryption failed.", data={})
