"""Client settings and the requests that the client builds."""

from __future__ import annotations

import pytest

from byomailer import BYOMailer, UrllibTransport, __version__
from byomailer._client import query_pairs
from tests.conftest import TOKEN, FakeTransport
from tests.payloads import TAG, data


@pytest.mark.parametrize(
    "base_url",
    [
        "https://mail.example.com",
        "https://mail.example.com/",
        "https://mail.example.com/api",
        "https://mail.example.com/api/v1/",
        "  https://mail.example.com  ",
    ],
)
def test_base_url_is_normalized(base_url: str) -> None:
    assert BYOMailer(base_url, "t").base_url == "https://mail.example.com"


def test_base_url_keeps_a_path_prefix() -> None:
    client = BYOMailer("https://example.com/mailer", "t")
    assert client.base_url == "https://example.com/mailer"


def test_base_url_needs_a_scheme() -> None:
    with pytest.raises(ValueError, match="https://"):
        BYOMailer("mail.example.com", "t")


def test_settings_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BYOMAILER_URL", "https://env.example.com")
    monkeypatch.setenv("BYOMAILER_TOKEN", "env-token")
    client = BYOMailer()
    assert client.base_url == "https://env.example.com"
    assert client._token == "env-token"


def test_arguments_win_over_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BYOMAILER_URL", "https://env.example.com")
    monkeypatch.setenv("BYOMAILER_TOKEN", "env-token")
    client = BYOMailer("https://mail.example.com", "arg-token")
    assert client.base_url == "https://mail.example.com"
    assert client._token == "arg-token"


def test_base_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BYOMAILER_URL", raising=False)
    with pytest.raises(ValueError, match="BYOMAILER_URL"):
        BYOMailer(token="t")


def test_token_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BYOMAILER_TOKEN", raising=False)
    with pytest.raises(ValueError, match="BYOMAILER_TOKEN"):
        BYOMailer("https://mail.example.com")


def test_repr_does_not_show_the_token() -> None:
    client = BYOMailer("https://mail.example.com", "secret-token-value")
    assert "secret-token-value" not in repr(client)
    assert repr(client) == "BYOMailer(base_url='https://mail.example.com')"


def test_default_settings() -> None:
    client = BYOMailer("https://mail.example.com", "t")
    assert client.timeout == 30.0
    assert client.max_retries == 2
    assert isinstance(client._transport, UrllibTransport)


def test_request_headers(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(201, data(TAG))
    client.tags.create("vip")
    headers = transport.last.headers
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"] == f"byomailer-python/{__version__}"
    assert transport.last.url == "https://mail.example.com/api/v1/tags"


def test_get_has_no_body_and_no_content_type(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, data([TAG]))
    client.tags.list()
    assert transport.last.body is None
    assert "Content-Type" not in transport.last.headers


def test_body_keeps_unicode(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(201, data(TAG))
    client.tags.create("Café Ñandú")
    assert transport.json() == {"name": "Café Ñandú"}


def test_timeout_goes_to_the_transport(transport: FakeTransport) -> None:
    client = BYOMailer("https://mail.example.com", "t", timeout=5.0, transport=transport)
    transport.reply(200, data([TAG]))
    client.tags.list()
    assert transport.timeouts == [5.0]


def test_timeout_none_means_no_timeout(transport: FakeTransport) -> None:
    client = BYOMailer("https://mail.example.com", "t", timeout=None, transport=transport)
    transport.reply(200, data([TAG]))
    client.tags.list()
    assert transport.timeouts == [None]


def test_query_pairs_encoding() -> None:
    assert query_pairs(
        {"lists": [1, 2], "flag": True, "off": False, "skip": None, "search": "a b", "ids": ()}
    ) == [("lists[]", "1"), ("lists[]", "2"), ("flag", "1"), ("off", "0"), ("search", "a b")]


def test_path_ids_are_in_the_url(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, data(TAG))
    client.tags.rename(5, "gold")
    assert transport.last.url == "https://mail.example.com/api/v1/tags/5"
