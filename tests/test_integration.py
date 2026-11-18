"""Integration tests against a live instance.

The tests run only when BYOMAILER_TEST_URL and BYOMAILER_TEST_TOKEN are set.
They only read data. They never send email, never schedule a newsletter and
never send a webhook test delivery.
"""

from __future__ import annotations

import os
import time

import pytest

from byomailer import BYOMailer, _client

URL = os.environ.get("BYOMAILER_TEST_URL")
TOKEN = os.environ.get("BYOMAILER_TEST_TOKEN")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (URL and TOKEN), reason="Set BYOMAILER_TEST_URL and BYOMAILER_TEST_TOKEN."
    ),
]


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> BYOMailer:
    # The autouse fixture replaces the sleep function. A live retry needs the real one.
    monkeypatch.setattr(_client, "_sleep", time.sleep)
    return BYOMailer(URL, TOKEN)


def test_list_contacts(live: BYOMailer) -> None:
    page = live.contacts.list(per_page=5)
    assert len(page) <= 5
    for contact in page:
        assert contact.id
        assert contact.email


def test_list_lists(live: BYOMailer) -> None:
    page = live.lists.list(per_page=5)
    assert all(mail_list.name for mail_list in page)


def test_list_tags(live: BYOMailer) -> None:
    tags = live.tags.list()
    assert all(tag.id for tag in tags)
