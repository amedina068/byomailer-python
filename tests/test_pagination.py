"""The pagination helper: iter() walks all pages with cursor and per_page."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from byomailer import BYOMailer
from tests.conftest import FakeTransport
from tests.payloads import (
    CONTACT,
    DELIVERY,
    EMAIL_LOG,
    ENDPOINT,
    IDENTITY,
    LIST,
    NEWSLETTER,
    PROJECT,
    SEQUENCE_SUMMARY,
    TEMPLATE,
    cursor_page,
)


def test_iter_follows_next_cursor_until_the_last_page(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, cursor_page([CONTACT, {**CONTACT, "id": 43}], next_cursor="c2"))
    transport.reply(200, cursor_page([{**CONTACT, "id": 44}], next_cursor="c3"))
    transport.reply(200, cursor_page([]))

    ids = [contact.id for contact in client.contacts.iter(per_page=2)]

    assert ids == [42, 43, 44]
    assert transport.query(0) == [("per_page", "2")]
    assert transport.query(1) == [("per_page", "2"), ("cursor", "c2")]
    assert transport.query(2) == [("per_page", "2"), ("cursor", "c3")]


def test_iter_sends_the_default_per_page(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([LIST]))
    assert len(list(client.lists.iter())) == 1
    assert transport.query() == [("per_page", "25")]


def test_iter_gets_a_page_only_when_the_caller_needs_it(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, cursor_page([CONTACT], next_cursor="c2"))
    contacts = client.contacts.iter()
    assert transport.requests == []
    assert next(contacts).id == 42
    assert len(transport.requests) == 1


def test_iter_sends_the_filters_on_each_page(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([CONTACT], next_cursor="c2"))
    transport.reply(200, cursor_page([CONTACT]))

    def tags() -> Iterator[int]:
        yield 5

    list(client.contacts.iter(tags=tags(), search="ana"))

    for index in (0, 1):
        assert ("tags[]", "5") in transport.query(index)
        assert ("search", "ana") in transport.query(index)


@pytest.mark.parametrize("per_page", [0, 101, -1])
def test_per_page_must_be_from_1_to_100(client: BYOMailer, per_page: int) -> None:
    with pytest.raises(ValueError, match="per_page must be from 1 to 100"):
        client.contacts.list(per_page=per_page)


@pytest.mark.parametrize("per_page", [1, 100])
def test_per_page_limits_are_valid(
    client: BYOMailer, transport: FakeTransport, per_page: int
) -> None:
    transport.reply(200, cursor_page([]))
    client.projects.list(per_page=per_page)
    assert transport.query() == [("per_page", str(per_page))]


PAGINATED: list[tuple[str, Callable[[BYOMailer], Iterator[Any]], Any, str]] = [
    ("contacts", lambda c: c.contacts.iter(), CONTACT, "/contacts"),
    ("lists", lambda c: c.lists.iter(), LIST, "/lists"),
    ("newsletters", lambda c: c.newsletters.iter(status="draft"), NEWSLETTER, "/newsletters"),
    ("sequences", lambda c: c.sequences.iter(search="w"), SEQUENCE_SUMMARY, "/sequences"),
    ("templates", lambda c: c.email_templates.iter(archived=True), TEMPLATE, "/email-templates"),
    ("identities", lambda c: c.email_identities.iter(), IDENTITY, "/email-identities"),
    ("logs", lambda c: c.email_logs.iter(recipient="ana"), EMAIL_LOG, "/email-logs"),
    ("projects", lambda c: c.projects.iter(), PROJECT, "/projects"),
    ("endpoints", lambda c: c.webhook_endpoints.iter(), ENDPOINT, "/webhook-endpoints"),
    (
        "deliveries",
        lambda c: c.webhook_endpoints.iter_deliveries(12),
        DELIVERY,
        "/webhook-endpoints/12/deliveries",
    ),
]


@pytest.mark.parametrize(
    ("name", "call", "item", "path"), PAGINATED, ids=[case[0] for case in PAGINATED]
)
def test_each_paginated_resource_walks_two_pages(
    client: BYOMailer,
    transport: FakeTransport,
    name: str,
    call: Callable[[BYOMailer], Iterator[Any]],
    item: Any,
    path: str,
) -> None:
    transport.reply(200, cursor_page([item], next_cursor="next"))
    transport.reply(200, cursor_page([item]))

    assert len(list(call(client))) == 2
    assert transport.path(0).split("?")[0] == path
    assert ("cursor", "next") in transport.query(1)


def test_page_without_meta_has_no_next_cursor(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, {"data": [LIST]})
    page = client.lists.list()
    assert page.next_cursor is None
    assert page.data[0].name == "Readers"
