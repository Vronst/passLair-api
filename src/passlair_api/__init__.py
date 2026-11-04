import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def main() -> None:
    # gunicorn_config.py provides this under gunicorn; the dev server is one app.
    os.environ.setdefault("SESSION_WRAP_KEY", os.urandom(32).hex())

    from .app import app

    app.run(debug=True)
