import os
from datetime import timedelta
from pathlib import Path

from flask import Flask
from flask_session import Session
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from passlair.core.database import db
from redis import Redis
from sqlalchemy.exc import OperationalError

from .config import config_mapping
from .helpers.functions import check_login_status
from .helpers.uploads import apply_upload_limits
from .routes.auth import auth
from .routes.data import data
from .routes.password_manager import password_manager

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

DATABASE = os.getenv("DATABASE", "sqlite")

SQLITE_PATH = os.getenv(
    "SQLITE_PATH", str(Path(__file__).resolve().parent) + "/passlair_api.db"
)
MARIA_DB = os.getenv("MARIA_DB", None)


app = Flask(__name__)
app.config.from_mapping(config_mapping)
app.config.update(
    {
        "SESSION_TYPE": "redis",
        "SESSION_REDIS": Redis(host=REDIS_HOST, port=REDIS_PORT),
        # Rendering a form stores a CSRF token, so anonymous visitors create
        # sessions too; expire them instead of keeping them for Flask's 31 days.
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=1),
    }
)
apply_upload_limits(app)
app.register_blueprint(auth)
app.register_blueprint(password_manager)
app.register_blueprint(data)

Session(app)
talisman = Talisman(app)
CSRFProtect(app)


@app.context_processor
def inject_auth_state() -> dict[str, bool]:
    return {"logged_in": check_login_status()}


@app.route("/health")
@talisman(force_https=False)  # The container healthcheck calls over plain HTTP.
def health() -> str:
    """Liveness only: a Redis or memcached outage shouldn't restart the app."""
    return "ok"


try:
    match DATABASE:
        case "sqlite":
            db.init_sqlite(SQLITE_PATH)

        case "mariadb":
            if not MARIA_DB:
                raise RuntimeError("MARIA_DB env value missing")

            db.init_mariadb(MARIA_DB)

        case "dual_db":
            ...  # TODO

        case _:
            raise RuntimeError("DATABASE env value missing")
except OperationalError as e:
    if "already exists" in str(e):
        pass  # Tables already created by a concurrent worker, safe to ignore
    else:
        raise


if __name__ == "__main__":
    app.run()
