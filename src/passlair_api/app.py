import os

from flask import Flask
from flask_session import Session
from flask_talisman import Talisman
from redis import Redis

from .config import config_mapping
from .routes.auth import auth
from .routes.data import data
from .routes.password_manager import password_manager

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

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
