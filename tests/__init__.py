import os

# helpers.functions requires this at import; gunicorn_config.py sets it in production.
os.environ.setdefault("SESSION_WRAP_KEY", os.urandom(32).hex())
