"""The errors that the BYOMailer client raises.

All errors come from :class:`BYOMailerError`::

    BYOMailerError
    +-- APIConnectionError         the client did not get a response
    |   +-- APITimeoutError        the request took more time than the timeout
    +-- APIError                   the instance sent an error status
    |   +-- AuthenticationError    401
    |   +-- AuthorizationError     403
    |   +-- NotFoundError          404
    |   +-- ValidationError        422, with the field errors
    |   +-- RateLimitError         429, with the Retry-After value
    |   +-- ServerError            5xx
    +-- WebhookVerificationError   a webhook delivery is not valid
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

__all__ = [
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AuthenticationError",
    "AuthorizationError",
    "BYOMailerError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "ValidationError",
    "WebhookVerificationError",
]


class BYOMailerError(Exception):
    """The base class of every error that this package raises."""


class APIConnectionError(BYOMailerError):
    """The client did not get a response from the instance.

    The cause is a DNS error, a refused connection, a closed connection or a
    TLS error. The original exception is in ``__cause__``.

    Attributes:
        request_sent: ``False`` when the instance did not receive the request:
            a DNS failure, a refused connection or a connect timeout. Then
            the client retries each operation, also a write that is not
            idempotent.
    """

    def __init__(self, message: str, *, request_sent: bool) -> None:
        super().__init__(message)
        self.message = message
        self.request_sent = request_sent


class APITimeoutError(APIConnectionError):
    """The request took more time than the timeout of the client."""


class APIError(BYOMailerError):
    """The instance sent a response with an error status.

    Attributes:
        status_code: The HTTP status code.
        message: The ``message`` field of the body, or ``HTTP <status>``.
        body: The decoded JSON body, or the text body.
        headers: The response headers, with lowercase names.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body
        self.headers: Mapping[str, str] = headers or {}

    def __str__(self) -> str:
        return f"{self.status_code}: {self.message}"


class AuthenticationError(APIError):
    """The token is missing, not valid or expired (401)."""


class AuthorizationError(APIError):
    """The token cannot do this action (403).

    A read-only token gets 403 on each request that changes data. A token of a
    user who is not an admin gets 403 on the webhook endpoints.
    """


class NotFoundError(APIError):
    """The record does not exist in the data of your client (404)."""


class ValidationError(APIError):
    """A field of the request failed a validation rule (422).

    Attributes:
        errors: The field errors, for example ``{"email": ["..."]}``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body, headers=headers)
        self.errors: dict[str, list[str]] = _field_errors(body)


class RateLimitError(APIError):
    """The instance received too many requests (429).

    Attributes:
        retry_after: The seconds to wait, from the ``Retry-After`` header, or ``None``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body, headers=headers)
        self.retry_after = retry_after


class ServerError(APIError):
    """The instance had an internal error (5xx)."""


class WebhookVerificationError(BYOMailerError):
    """A webhook delivery did not pass the verification.

    Attributes:
        reason: ``"signature"`` when the signature is missing or wrong.
            ``"timestamp"`` when the timestamp is missing, is not a Unix time,
            or is outside the tolerance. ``"payload"`` when the signature is
            valid, but the body is not a JSON object.
    """

    def __init__(
        self, message: str, *, reason: Literal["signature", "timestamp", "payload"]
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason


def _field_errors(body: Any) -> dict[str, list[str]]:
    raw = body.get("errors") if isinstance(body, dict) else None
    if not isinstance(raw, dict):
        return {}
    return {
        str(field): [str(item) for item in messages]
        if isinstance(messages, list)
        else [str(messages)]
        for field, messages in raw.items()
    }
