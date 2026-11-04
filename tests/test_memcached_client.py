"""The memcached client as gunicorn's threads use it: concurrently, over real
sockets. One shared connection mixes up its replies under this load; a pool
can't, so this test can't fail by bad luck on correct code.
"""

import socketserver
import threading
import time
from collections.abc import Iterator

import pytest

from passlair_api.helpers.functions import _build_cache

THREADS = 4
CALLS_PER_THREAD = 200


def value_for(thread: int) -> bytes:
    return b"secret-of-user-%d" % thread


class MemcachedGetHandler(socketserver.StreamRequestHandler):
    """Just enough of memcached's protocol to answer `get`."""

    def handle(self) -> None:
        while line := self.rfile.readline():
            _, key = line.split()
            time.sleep(0.0005)  # Leaves time for requests to overlap.
            value = value_for(int(key.rsplit(b":", 1)[1]))
            self.wfile.write(
                b"VALUE %s 0 %d\r\n%s\r\nEND\r\n" % (key, len(value), value)
            )


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@pytest.fixture
def server_address() -> Iterator[tuple[str, int]]:
    with Server(("127.0.0.1", 0), MemcachedGetHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        yield str(host), port
        server.shutdown()


def test_concurrent_threads_each_get_their_own_answer(
    server_address: tuple[str, int],
) -> None:
    client = _build_cache(server_address)
    problems: list[object] = []

    def read_repeatedly(thread: int) -> None:
        for _ in range(CALLS_PER_THREAD):
            try:
                value = client.get(f"user_dek:{thread}")
            except Exception as err:  # noqa: BLE001 - any error is the failure
                problems.append(err)
            else:
                if value != value_for(thread):
                    problems.append(value)

    threads = [
        threading.Thread(target=read_repeatedly, args=(i,)) for i in range(THREADS)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    client.close()

    assert problems == []
