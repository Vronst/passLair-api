"""WSGI app for test_session_key.py: reports which worker answered and its key.

Sleeps so that overlapping requests can't all land on one worker.
"""

import hashlib
import json
import os
import time
from collections.abc import Callable, Iterable

from passlair_api.helpers.functions import SESSION_WRAP_KEY


def app(_: dict[str, object], start_response: Callable[..., object]) -> Iterable[bytes]:
    time.sleep(0.1)
    start_response("200 OK", [("Content-Type", "application/json")])
    fingerprint = hashlib.sha256(SESSION_WRAP_KEY).hexdigest()
    return [json.dumps({"pid": os.getpid(), "key": fingerprint}).encode()]
