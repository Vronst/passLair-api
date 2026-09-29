import os
from pathlib import Path

from flask import Flask
from flask_session import Session
from flask_talisman import Talisman
from passlair.core.database import db
from redis import Redis

from .config import config_mapping
from .helpers.functions import check_login_status
from .routes.auth import auth
from .routes.data import data
from .routes.password_manager import password_manager

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

DATABASE = os.getenv("DATABASE", "sqlite")

SQLITE_PATH = os.getenv(
    "SQLITE_PATH", str(Path(__file__).resolve().parent) + "passlair_api.db"
)
MARIA_DB = os.getenv("MARIA_DB", None)


app = Flask(__name__)
app.config.from_mapping(config_mapping)
app.config.update(
    {"SESSION_TYPE": "redis", "SESSION_REDIS": Redis(host=REDIS_HOST, port=6379)}
)
app.register_blueprint(auth)
app.register_blueprint(password_manager)
app.register_blueprint(data)

Session(app)
Talisman(app)


@app.context_processor
def inject_auth_state() -> dict[str, bool]:
    return {"logged_in": check_login_status()}


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
