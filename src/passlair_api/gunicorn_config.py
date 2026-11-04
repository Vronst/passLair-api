import os

workers = int(os.environ.get("GUNICORN_PROCESSES", "2"))

threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8888")

# Only nginx can reach the app (compose publishes no app port), so its
# forwarded headers can be trusted whatever its container IP is.
forwarded_allow_ips = "*"

secure_scheme_headers = {"X-Forwarded-Proto": "https"}

# This file runs once in the master, so every worker, including respawned ones,
# inherits the same keys. Generating them in the app would give each worker its
# own. A restart rotates them unless they are set in the environment.
os.environ.setdefault("SESSION_WRAP_KEY", os.urandom(32).hex())
os.environ.setdefault("SECRET_KEY", os.urandom(32).hex())
