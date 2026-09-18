from flask import Flask
from flask_session import Session
from flask_talisman import Talisman
from redis import Redis
from .routes.auth import auth
from .routes.password_manager import password_manager
from .routes.data import data


app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(
    {
        "SESSION_TYPE": "redis",
    }
)
app.register_blueprint(auth)
app.register_blueprint(password_manager)
app.register_blueprint(data)

SESSION_TYPE = "redis"
SESSION_REDIS = Redis(host="localhost", port=6379)
Session(app)
Talisman(app)
