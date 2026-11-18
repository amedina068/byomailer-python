"""The map from each failure to its error class."""

from __future__ import annotations

import pytest

from byomailer import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    AuthorizationError,
    BYOMailer,
    BYOMailerError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from tests.conftest import FakeTransport


@pytest.mark.parametrize(
    ("status", "message", "error_class"),
    [
        (401, "Unauthenticated.", AuthenticationError),
        (403, "You have read-only access.", AuthorizationError),
        (404, "Not found.", NotFoundError),
        (422, "The name field is required.", ValidationError),
        (429, "Too Many Attempts.", RateLimitError),
        (500, "Server Error", ServerError),
        (503, "Service Unavailable", ServerError),
        (400, "Bad request.", APIError),
        (409, "Conflict.", APIError),
    ],
)
def test_status_maps_to_error_class(
    transport: FakeTransport, status: int, message: str, error_class: type[APIError]
) -> None:
    client = BYOMailer("https://mail.example.com", "t", max_retries=0, transport=transport)
    transport.reply(status, {"message": message})
    with pytest.raises(error_class) as caught:
        client.tags.create("vip")
    error = caught.value
    assert type(error) is error_class
    assert error.status_code == status
    assert error.message == message
    assert str(error) == f"{status}: {message}"
    assert isinstance(error, BYOMailerError)


def test_validation_error_has_the_field_errors(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(
        422,
        {
            "message": "The email field must be a valid email address. (and 1 more error)",
            "errors": {
                "email": ["The email field must be a valid email address."],
                "remove_tags": ["These tags are in tags and in remove_tags: vip."],
            },
        },
    )
    with pytest.raises(ValidationError) as caught:
        client.contacts.add(3, "not-an-email")
    assert caught.value.errors == {
        "email": ["The email field must be a valid email address."],
        "remove_tags": ["These tags are in tags and in remove_tags: vip."],
    }


def test_validation_error_without_errors_field(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(422, {"message": "Invalid."})
    with pytest.raises(ValidationError) as caught:
        client.tags.create("vip")
    assert caught.value.errors == {}


def test_rate_limit_error_has_retry_after(transport: FakeTransport) -> None:
    client = BYOMailer("https://mail.example.com", "t", max_retries=0, transport=transport)
    transport.reply(429, {"message": "Too Many Attempts."}, headers={"Retry-After": "42"})
    with pytest.raises(RateLimitError) as caught:
        client.newsletters.send_test(7)
    assert caught.value.retry_after == 42.0
    assert caught.value.headers["retry-after"] == "42"


def test_error_with_a_body_that_is_not_json(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(404, body=b"<html>Not Found</html>", headers={"Content-Type": "text/html"})
    with pytest.raises(NotFoundError) as caught:
        client.contacts.get(1)
    assert caught.value.message == "HTTP 404"
    assert caught.value.body == "<html>Not Found</html>"


def test_redirect_is_an_error(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(302, body=b"", headers={"Location": "https://mail.example.com/login"})
    with pytest.raises(APIError) as caught:
        client.tags.list()
    assert caught.value.status_code == 302


def test_success_that_is_not_json_raises(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, body=b"<html>Login</html>", headers={"Content-Type": "text/html"})
    with pytest.raises(BYOMailerError, match="not JSON"):
        client.tags.list()


def test_success_without_data_raises(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, {"items": []})
    with pytest.raises(BYOMailerError, match="no 'data' field"):
        client.tags.list()


def test_success_with_data_that_is_not_an_object(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, {"data": "text"})
    with pytest.raises(BYOMailerError, match="not a JSON object"):
        client.tags.create("vip")


def test_success_with_data_that_is_not_a_list(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, {"data": {"id": 1}})
    with pytest.raises(BYOMailerError, match="no list"):
        client.tags.list()


@pytest.mark.parametrize("error_class", [APIConnectionError, APITimeoutError])
def test_connection_errors_reach_the_caller(
    transport: FakeTransport, error_class: type[APIConnectionError]
) -> None:
    client = BYOMailer("https://mail.example.com", "t", max_retries=0, transport=transport)
    transport.fail(error_class("No route to host", request_sent=False))
    with pytest.raises(error_class) as caught:
        client.tags.list()
    assert caught.value.request_sent is False
    assert isinstance(caught.value, BYOMailerError)
