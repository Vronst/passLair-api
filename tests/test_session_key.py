"""The key protecting DEKs in memcached, and entries it can no longer read.

Every worker must use the same key, or a user logged in through one worker
fails on all the others. These tests start real gunicorn workers, because a
single test process can't show that.
"""

import concurrent.futures
import json
import os
import runpy
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from flask.testing import FlaskClient
from passlair.core.crypto import encrypt
from pymemcache.test.utils import MockMemcacheClient

import passlair_api
from tests.support import GOOD_PASSWORD, FakeCoreIdentity, identity_entries

GUNICORN_CONFIG = Path(passlair_api.__file__).parent / "gunicorn_config.py"
REPO_ROOT = Path(__file__).parent.parent
LOGIN = {"username": "alice", "password": GOOD_PASSWORD}


def environment_without_keys() -> dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if name not in ("SESSION_WRAP_KEY", "SECRET_KEY")
    }


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def probe_url() -> Iterator[str]:
    """Three real single-threaded workers running tests/gunicorn_probe.py."""
    port = free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--config",
            str(GUNICORN_CONFIG),
            "tests.gunicorn_probe:app",
        ],
        cwd=REPO_ROOT,
        env=environment_without_keys()
        | {
            "GUNICORN_PROCESSES": "3",
            "GUNICORN_THREADS": "1",
            "GUNICORN_BIND": f"127.0.0.1:{port}",
        },
    )
    url = f"http://127.0.0.1:{port}/"
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                urllib.request.urlopen(url, timeout=2).read()
                break
            except OSError:  # Also covers URLError: not accepting connections yet.
                if server.poll() is not None or time.monotonic() > deadline:
                    pytest.fail("gunicorn did not start")
                time.sleep(0.1)
        yield url
    finally:
        server.terminate()
        server.wait(timeout=10)


def read_probe(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def test_all_gunicorn_workers_share_one_key(probe_url: str) -> None:
    # Overlapping requests to slow single-threaded workers reach several of them.
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        answers = list(pool.map(read_probe, [probe_url] * 36))

    assert len({answer["pid"] for answer in answers}) >= 2, "only one worker answered"
    assert len({answer["key"] for answer in answers}) == 1


def test_respawned_worker_keeps_the_key(probe_url: str) -> None:
    first = read_probe(probe_url)

    os.kill(first["pid"], 9)

    answers: list[dict[str, Any]] = []
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and len(answers) < 12:
        try:
            answers.append(read_probe(probe_url))
        except OSError:  # Also covers URLError: the killed worker's connection.
            time.sleep(0.1)

    assert len(answers) == 12
    assert {answer["key"] for answer in answers} == {first["key"]}


def test_importing_without_a_key_fails_loudly() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import passlair_api.helpers.functions"],
        cwd=REPO_ROOT,
        env=environment_without_keys(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SESSION_WRAP_KEY is not set" in result.stderr


def test_gunicorn_config_generates_missing_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SESSION_WRAP_KEY")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    runpy.run_path(str(GUNICORN_CONFIG))

    assert len(bytes.fromhex(os.environ["SESSION_WRAP_KEY"])) == 32
    assert os.environ["SECRET_KEY"]


def test_gunicorn_config_keeps_configured_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SESSION_WRAP_KEY", "ab" * 32)
    monkeypatch.setenv("SECRET_KEY", "configured")

    runpy.run_path(str(GUNICORN_CONFIG))

    assert os.environ["SESSION_WRAP_KEY"] == "ab" * 32
    assert os.environ["SECRET_KEY"] == "configured"


def test_saved_identity_is_restored_with_its_dek(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    restored: list[tuple[str, bytes]] = []
    original = FakeCoreIdentity.restore_session

    def spy(self: FakeCoreIdentity, user_id: str, dek: bytes) -> object:
        restored.append((user_id, dek))
        return original(self, user_id, dek)

    monkeypatch.setattr(FakeCoreIdentity, "restore_session", spy)
    client.post("/auth/login", data=LOGIN)

    assert client.get("/passwords/").status_code == 200
    assert restored[-1] == ("Alice", b"1234567890")


def entry_from_another_key() -> bytes:
    ciphertext, nonce = encrypt(b"k" * 32, os.urandom(32))
    return json.dumps(
        {"user_id": "Alice", "dek": ciphertext.hex(), "nonce": nonce.hex()}
    ).encode()


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(entry_from_another_key(), id="written-under-another-key"),
        pytest.param(b"not json", id="not-json"),
        pytest.param(b"null", id="json-null"),
        pytest.param(b"[]", id="json-list"),
        pytest.param(b'{"user_id": "Alice"}', id="missing-fields"),
        pytest.param(b'{"user_id": "Alice", "dek": "zz", "nonce": "zz"}', id="not-hex"),
        pytest.param(b'{"user_id": "Alice", "dek": "", "nonce": ""}', id="empty"),
    ],
)
def test_unreadable_entry_logs_the_user_out_instead_of_crashing(
    client: FlaskClient, user_manager: MockMemcacheClient, entry: bytes
) -> None:
    client.post("/auth/login", data=LOGIN)
    [key] = identity_entries(user_manager)
    user_manager.set(key.decode(), entry)

    response = client.get("/passwords/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")
    assert identity_entries(user_manager) == []


def test_user_can_log_in_again_after_unreadable_entry(
    client: FlaskClient, user_manager: MockMemcacheClient
) -> None:
    client.post("/auth/login", data=LOGIN)
    [key] = identity_entries(user_manager)
    user_manager.set(key.decode(), entry_from_another_key())

    assert client.get("/auth/login").status_code == 200
    client.post("/auth/login", data=LOGIN)

    assert client.get("/passwords/").status_code == 200
