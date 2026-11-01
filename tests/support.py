"""Shared test setup.

passlair_api.app isn't imported in tests because it wires up Redis and a
database at import time, so tests build a throwaway app instead.
"""

from unittest.mock import Mock

from cachelib import SimpleCache
from flask import Flask
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from passlair.dataclasses.facade_result import FacadeResult

from passlair_api.helpers.uploads import apply_upload_limits
from passlair_api.routes.auth import auth
from passlair_api.routes.data import data
from passlair_api.routes.password_manager import password_manager


def build_app(csrf: bool = False) -> Flask:
    """App with the real blueprints (base.html links to all of them) and an
    in-memory session backend.

    CSRFProtect is always installed, since templates call csrf_token(); its
    check is off by default so tests can post forms without scraping a token.
    """
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test",
        SESSION_TYPE="cachelib",
        SESSION_CACHELIB=SimpleCache(),
        TESTING=True,
        WTF_CSRF_ENABLED=csrf,
    )
    apply_upload_limits(app)
    Session(app)
    _ = CSRFProtect(app)
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
    def manager(self) -> object:
        manager = Mock(user_id="Alice")
        manager.get_session_key = Mock(return_value=b"1234567890")
        return manager

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

    def restore_session(self, user_id, dek) -> FacadeResult:
        self._logged_in = True
        return FacadeResult(
            success=True, message="Loged by DEK for user alice. BE CAREFUL", data={}
        )
