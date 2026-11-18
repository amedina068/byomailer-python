"""The urllib transport, against a local HTTP server on 127.0.0.1."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

import pytest

from byomailer import APIConnectionError, APITimeoutError, BYOMailer, Request, UrllibTransport

JSON = {"Content-Type": "application/json"}


class Handler(BaseHTTPRequestHandler):
    seen: ClassVar[list[dict[str, Any]]] = []

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send(self, status: int, body: bytes, headers: dict[str, str]) -> None:
        try:
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # The client stopped waiting. The timeout test does this.

    def _record(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        Handler.seen.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers),
                "body": self.rfile.read(length) if length else b"",
            }
        )

    def do_GET(self) -> None:
        self._record()
        if self.path.endswith("/tags"):
            body = json.dumps({"data": [{"id": 1, "uuid": "u", "name": "vip"}]}).encode()
            self._send(200, body, JSON)
        elif self.path.endswith("/missing"):
            self._send(404, b'{"message":"Not found."}', JSON)
        elif self.path.endswith("/redirect"):
            self._send(302, b"", {"Location": "https://other.example.com/steal"})
        elif self.path.endswith("/slow"):
            time.sleep(0.5)
            self._send(200, b"{}", JSON)

    def do_POST(self) -> None:
        self._record()
        self._send(201, b'{"data":{"id":2,"uuid":"u2","name":"new"}}', JSON)

    def do_DELETE(self) -> None:
        self._record()
        self._send(204, b"", {})


@pytest.fixture
def server() -> Iterator[str]:
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def test_client_round_trip(server: str) -> None:
    client = BYOMailer(server, "local-token")
    tags = client.tags.list()
    tag = client.tags.create("new")
    client.tags.delete(2)

    assert [t.name for t in tags] == ["vip"]
    assert tag.name == "new"
    get, post, delete = Handler.seen
    assert get["path"] == "/api/v1/tags"
    assert get["headers"]["Authorization"] == "Bearer local-token"
    assert get["headers"]["Accept"] == "application/json"
    assert post["method"] == "POST"
    assert json.loads(post["body"]) == {"name": "new"}
    assert post["headers"]["Content-Type"] == "application/json"
    assert delete["method"] == "DELETE"


def test_error_status_is_a_response(server: str) -> None:
    response = UrllibTransport()(Request("GET", f"{server}/missing", {}), 5)
    assert response.status_code == 404
    assert response.json() == {"message": "Not found."}
    assert response.header("Content-Type") == "application/json"


def test_redirect_is_not_followed(server: str) -> None:
    response = UrllibTransport()(Request("GET", f"{server}/redirect", {}), 5)
    assert response.status_code == 302
    assert response.header("location") == "https://other.example.com/steal"
    assert len(Handler.seen) == 1


def test_refused_connection_was_not_sent() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(APIConnectionError) as caught:
        UrllibTransport()(Request("GET", f"http://127.0.0.1:{port}/", {}), 2)
    assert caught.value.request_sent is False
    assert caught.value.__cause__ is not None


def test_read_timeout_was_sent(server: str) -> None:
    with pytest.raises(APITimeoutError) as caught:
        UrllibTransport()(Request("GET", f"{server}/slow", {}), 0.1)
    assert caught.value.request_sent is True
