from flask import Flask
from .routes.auth import auth
from .routes.password_manager import password_manager
from .routes.data import data

app = Flask(__name__)

app.register_blueprint(auth)
app.register_blueprint(password_manager)
app.register_blueprint(data)
