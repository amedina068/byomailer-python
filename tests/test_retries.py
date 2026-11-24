"""Retry rules: 429, 5xx and connection errors, with backoff and Retry-After."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Any

import pytest

from byomailer import (
    APIConnectionError,
    APITimeoutError,
    BYOMailer,
    RateLimitError,
    ServerError,
)
from byomailer._client import BACKOFF_MAX, backoff, parse_retry_after
from tests.conftest import FakeTransport, SleepRecorder
from tests.payloads import (
    BLOCK,
    CONTACT,
    ENDPOINT,
    LIST,
    PROJECT,
    STEP,
    TAG,
    TOPIC,
    VARIABLES,
    data,
)


def test_get_retries_a_5xx_then_succeeds(
    client: BYOMailer, transport: FakeTransport, sleeps: SleepRecorder
) -> None:
    transport.reply(503).reply(500).reply(200, data([TAG]))
    assert client.tags.list()[0].name == "vip"
    assert len(transport.requests) == 3
    assert len(sleeps.delays) == 2


def test_retries_stop_at_max_retries(
    client: BYOMailer, transport: FakeTransport, sleeps: SleepRecorder
) -> None:
    transport.reply(500).reply(502).reply(503)
    with pytest.raises(ServerError) as caught:
        client.tags.list()
    assert caught.value.status_code == 503
    assert len(transport.requests) == 3
    assert len(sleeps.delays) == 2


def test_max_retries_zero_sends_once(transport: FakeTransport) -> None:
    client = BYOMailer("https://mail.example.com", "t", max_retries=0, transport=transport)
    transport.reply(500)
    with pytest.raises(ServerError):
        client.tags.list()
    assert len(transport.requests) == 1


def test_max_retries_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="max_retries"):
        BYOMailer("https://mail.example.com", "t", max_retries=-1)


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.tags.create("vip"),
        lambda c: c.contacts.add(3, "ana@example.com"),
        lambda c: c.newsletters.update(7, title="News"),
        lambda c: c.newsletters.pick_winner(7, "a"),
        lambda c: c.webhook_endpoints.rotate_secret(12),
    ],
    ids=["create", "contacts.add", "newsletters.update", "pick_winner", "rotate_secret"],
)
def test_a_request_that_is_not_idempotent_is_not_retried_on_5xx(
    client: BYOMailer, transport: FakeTransport, call: Callable[[BYOMailer], object]
) -> None:
    transport.reply(500)
    with pytest.raises(ServerError):
        call(client)
    assert len(transport.requests) == 1


IDEMPOTENT_WRITES: list[tuple[str, Callable[[BYOMailer], object], Any]] = [
    ("contacts.update", lambda c: c.contacts.update(42, name="Ana"), data(CONTACT)),
    ("contacts.unsubscribe", lambda c: c.contacts.unsubscribe(42), data(CONTACT)),
    ("contacts.subscribe", lambda c: c.contacts.subscribe(42), data(CONTACT)),
    ("newsletters.count_recipients", lambda c: c.newsletters.count_recipients(), {"count": 1}),
    ("tags.rename", lambda c: c.tags.rename(5, "gold"), data(TAG)),
    ("lists.rename", lambda c: c.lists.rename(3, "Buyers"), data(LIST)),
    ("topics.update", lambda c: c.topics.update(3, 8, name="Offers"), data(TOPIC)),
    (
        "blocks.update",
        lambda c: c.blocks.update(2, name="footer", html_content="<p>Bye</p>"),
        data(BLOCK),
    ),
    ("projects.rename", lambda c: c.projects.rename(4, "Shop"), data(PROJECT)),
    (
        "newsletters.replace_variables",
        lambda c: c.newsletters.replace_variables(7, {}),
        data(VARIABLES),
    ),
    (
        "sequences.replace_variables",
        lambda c: c.sequences.replace_variables(3, {}),
        data(VARIABLES),
    ),
    (
        "sequences.replace_step_filters",
        lambda c: c.sequences.replace_step_filters(3, 11, []),
        data(STEP),
    ),
    (
        "webhook_endpoints.update",
        lambda c: c.webhook_endpoints.update(12, active=True),
        data(ENDPOINT),
    ),
]


@pytest.mark.parametrize(
    ("call", "reply"),
    [(call, reply) for _, call, reply in IDEMPOTENT_WRITES],
    ids=[name for name, _, _ in IDEMPOTENT_WRITES],
)
def test_each_operation_of_the_idempotent_list_is_retried_on_5xx(
    client: BYOMailer, transport: FakeTransport, call: Callable[[BYOMailer], object], reply: Any
) -> None:
    transport.reply(503).reply(200, reply)
    call(client)
    assert len(transport.requests) == 2


def test_a_5xx_with_retry_after_waits_for_that_time(
    client: BYOMailer, transport: FakeTransport, sleeps: SleepRecorder
) -> None:
    transport.reply(503, {"message": "Down"}, headers={"Retry-After": "4"})
    transport.reply(200, data([TAG]))
    client.tags.list()
    assert sleeps.delays == [4.0]


def test_delete_is_retried_on_5xx(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(502).reply(204)
    client.tags.delete(5)
    assert len(transport.requests) == 2


def test_post_is_retried_on_429_with_retry_after(
    client: BYOMailer, transport: FakeTransport, sleeps: SleepRecorder
) -> None:
    transport.reply(429, {"message": "Too Many Attempts."}, headers={"Retry-After": "7"})
    transport.reply(200, {"message": "Test email sent", "sent_to": "admin@example.com"})
    client.newsletters.send_test(7)
    assert len(transport.requests) == 2
    assert sleeps.delays == [7.0]


def test_429_without_retry_after_uses_backoff(
    client: BYOMailer, transport: FakeTransport, sleeps: SleepRecorder
) -> None:
    transport.reply(429).reply(200, {"count": 1})
    client.newsletters.count_recipients()
    assert 0.25 <= sleeps.delays[0] <= 0.5


def test_429_with_a_long_retry_after_is_not_retried(
    client: BYOMailer, transport: FakeTransport, sleeps: SleepRecorder
) -> None:
    transport.reply(429, {"message": "Too Many Attempts."}, headers={"Retry-After": "120"})
    with pytest.raises(RateLimitError) as caught:
        client.webhook_endpoints.send_test(12)
    assert caught.value.retry_after == 120.0
    assert len(transport.requests) == 1
    assert sleeps.delays == []


def test_429_that_never_ends_raises_rate_limit_error(
    client: BYOMailer, transport: FakeTransport
) -> None:
    for _ in range(3):
        transport.reply(429, {"message": "Too Many Attempts."}, headers={"Retry-After": "1"})
    with pytest.raises(RateLimitError):
        client.tags.list()
    assert len(transport.requests) == 3


@pytest.mark.parametrize(
    "error",
    [
        APIConnectionError("Name or service not known", request_sent=False),
        APIConnectionError("Connection refused", request_sent=False),
        APITimeoutError("The connection timed out", request_sent=False),
    ],
    ids=["dns", "refused", "connect-timeout"],
)
def test_connection_error_before_the_send_is_retried_for_post(
    client: BYOMailer, transport: FakeTransport, error: APIConnectionError
) -> None:
    transport.fail(error)
    transport.reply(201, data(TAG))
    assert client.tags.create("vip").id == 5
    assert len(transport.requests) == 2


def test_reset_after_the_send_is_not_retried_for_post(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.fail(APIConnectionError("Connection reset by peer", request_sent=True))
    with pytest.raises(APIConnectionError):
        client.tags.create("vip")
    assert len(transport.requests) == 1


def test_timeout_is_retried_for_an_idempotent_post(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.fail(APITimeoutError("Read timed out", request_sent=True))
    transport.reply(200, data(CONTACT))
    assert client.contacts.unsubscribe(42).id == CONTACT["id"]
    assert len(transport.requests) == 2


def test_connection_error_after_the_request_is_not_retried_for_post(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.fail(APITimeoutError("Read timed out", request_sent=True))
    with pytest.raises(APITimeoutError):
        client.tags.create("vip")
    assert len(transport.requests) == 1


def test_connection_error_after_the_request_is_retried_for_get(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.fail(APITimeoutError("Read timed out", request_sent=True))
    transport.reply(200, data([TAG]))
    assert len(client.tags.list()) == 1
    assert len(transport.requests) == 2


def test_connection_errors_stop_at_max_retries(client: BYOMailer, transport: FakeTransport) -> None:
    for _ in range(3):
        transport.fail(APIConnectionError("Connection refused", request_sent=False))
    with pytest.raises(APIConnectionError):
        client.tags.list()
    assert len(transport.requests) == 3


def test_each_retry_sends_the_same_request(client: BYOMailer, transport: FakeTransport) -> None:
    transport.fail(APIConnectionError("Connection refused", request_sent=False))
    transport.reply(201, data(TAG))
    client.tags.create("vip")
    assert transport.requests[0] == transport.requests[1]


def test_backoff_grows_and_has_a_ceiling() -> None:
    for attempt in range(10):
        ceiling = min(BACKOFF_MAX, 0.5 * 2**attempt)
        delay = backoff(attempt)
        assert ceiling / 2 <= delay <= ceiling


def test_backoff_has_jitter() -> None:
    assert len({backoff(3) for _ in range(20)}) > 1


def test_parse_retry_after() -> None:
    assert parse_retry_after(None) is None
    assert parse_retry_after("30") == 30.0
    assert parse_retry_after("-5") == 0.0
    assert parse_retry_after("soon") is None
    later = datetime.now(timezone.utc) + timedelta(seconds=20)
    seconds = parse_retry_after(format_datetime(later, usegmt=True))
    assert seconds is not None
    assert 15 <= seconds <= 21
