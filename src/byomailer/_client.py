"""The client: settings, request building, error mapping and retries."""

from __future__ import annotations

import email.utils
import json
import os
import random
import time
from collections.abc import Iterable, Mapping
from typing import Any, Final
from urllib.parse import urlencode

from byomailer._account import EmailIdentities, EmailLogs, Projects, WebhookEndpoints
from byomailer._campaigns import Blocks, EmailTemplates, Newsletters, Sequences
from byomailer._contacts import Contacts, Lists, Tags, Topics
from byomailer._http import Request, Response, Transport, UrllibTransport
from byomailer._version import __version__
from byomailer.errors import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    BYOMailerError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

__all__ = ["BYOMailer"]

DEFAULT_TIMEOUT: Final = 30.0
DEFAULT_MAX_RETRIES: Final = 2

BACKOFF_BASE: Final = 0.5
BACKOFF_MAX: Final = 8.0

# The client does not wait longer than this for one Retry-After value. If the
# instance asks for a longer wait, the client raises RateLimitError at once.
MAX_RETRY_AFTER: Final = 60.0

# A second copy of a request with one of these methods does no new action.
IDEMPOTENT_METHODS: Final = frozenset({"GET", "HEAD", "PUT", "DELETE"})

USER_AGENT: Final = f"byomailer-python/{__version__}"

_ERRORS_BY_STATUS: Final[dict[int, type[APIError]]] = {
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    422: ValidationError,
}


# The tests replace this function, so that a retry does not wait.
def _sleep(seconds: float) -> None:
    time.sleep(seconds)


class BYOMailer:
    """A client for one BYOMailer instance.

    Example::

        client = BYOMailer("https://mail.example.com", token="...")
        for contact in client.contacts.iter():
            print(contact.email)

    Args:
        base_url: The URL of your instance. The default is ``$BYOMAILER_URL``.
            The client adds ``/api/v1``.
        token: A personal API token. The default is ``$BYOMAILER_TOKEN``.
        timeout: The seconds to wait for the connection and for each read.
            The default is 30. ``None`` means no timeout.
        max_retries: The number of retries after a 429, a 5xx or a connection
            error. The default is 2. Use 0 to stop all retries.
        transport: Sends the HTTP requests. The default uses ``urllib``.
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        *,
        timeout: float | None = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: Transport | None = None,
    ) -> None:
        base_url = base_url or os.environ.get("BYOMAILER_URL")
        token = token or os.environ.get("BYOMAILER_TOKEN")
        if not base_url:
            raise ValueError(
                "Give the URL of your BYOMailer instance as base_url, "
                "or set the BYOMAILER_URL environment variable."
            )
        if not token:
            raise ValueError(
                "Give an API token as token, or set the BYOMAILER_TOKEN environment variable."
            )
        if max_retries < 0:
            raise ValueError("max_retries must be 0 or more")

        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.max_retries = max_retries
        self._token = token
        self._transport: Transport = transport or UrllibTransport()

        self.contacts = Contacts(self)
        self.lists = Lists(self)
        self.topics = Topics(self)
        self.tags = Tags(self)
        self.newsletters = Newsletters(self)
        self.sequences = Sequences(self)
        self.blocks = Blocks(self)
        self.email_templates = EmailTemplates(self)
        self.email_identities = EmailIdentities(self)
        self.email_logs = EmailLogs(self)
        self.projects = Projects(self)
        self.webhook_endpoints = WebhookEndpoints(self)

    def __repr__(self) -> str:
        # Never show the token.
        return f"BYOMailer(base_url={self.base_url!r})"

    def _get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params).json()

    def _post(self, path: str, body: Mapping[str, Any] | None = None) -> Any:
        return self._request("POST", path, body=body).json()

    def _patch(self, path: str, body: Mapping[str, Any]) -> Any:
        return self._request("PATCH", path, body=body).json()

    def _delete(self, path: str) -> None:
        self._request("DELETE", path)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Response:
        request = self._build_request(method, path, params, body)
        attempt = 0
        while True:
            try:
                response = self._transport(request, self.timeout)
            except APIConnectionError as error:
                delay = self._connection_retry_delay(error, method, attempt)
                if delay is None:
                    raise
            else:
                if 200 <= response.status_code < 300:
                    return _checked(response)
                delay = self._response_retry_delay(response, method, attempt)
                if delay is None:
                    raise error_from_response(response)
            _sleep(delay)
            attempt += 1

    def _build_request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None,
        body: Mapping[str, Any] | None,
    ) -> Request:
        url = f"{self.base_url}/api/v1{path}"
        query = urlencode(query_pairs(params or {}))
        if query:
            url = f"{url}?{query}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            # Laravel sends JSON errors only when the request accepts JSON.
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        return Request(method, url, headers, data)

    def _connection_retry_delay(
        self, error: APIConnectionError, method: str, attempt: int
    ) -> float | None:
        if attempt >= self.max_retries:
            return None
        if error.request_sent and method not in IDEMPOTENT_METHODS:
            return None
        return backoff(attempt)

    def _response_retry_delay(self, response: Response, method: str, attempt: int) -> float | None:
        """Return the wait before the next attempt, or ``None`` for no retry.

        The client retries a 429 for every method, because the rate limiter
        refuses the request before the app does the action. The client retries
        a 5xx only for an idempotent method.
        """
        if attempt >= self.max_retries:
            return None
        status = response.status_code
        if status == 429:
            retry_after = parse_retry_after(response.header("retry-after"))
            if retry_after is None:
                return backoff(attempt)
            return retry_after if retry_after <= MAX_RETRY_AFTER else None
        if status >= 500 and method in IDEMPOTENT_METHODS:
            return backoff(attempt)
        return None


def normalize_base_url(base_url: str) -> str:
    """Return the instance URL with no trailing ``/``, ``/api`` or ``/api/v1``."""
    url = base_url.strip().rstrip("/")
    if not url.startswith(("https://", "http://")):
        raise ValueError(f"base_url must start with https:// or http://, not {base_url!r}")
    for suffix in ("/api/v1", "/api"):
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url


def query_pairs(params: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Encode query parameters the way Laravel reads them.

    A list becomes ``name[]=a&name[]=b``. A boolean becomes ``1`` or ``0``,
    because the Laravel ``boolean`` rule does not accept ``true``.
    """
    pairs: list[tuple[str, str]] = []
    for name, value in params.items():
        if value is None:
            continue
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            pairs.extend((f"{name}[]", _query_value(item)) for item in value)
        else:
            pairs.append((name, _query_value(value)))
    return pairs


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def backoff(attempt: int) -> float:
    """Return the wait before retry number ``attempt + 1``: exponential, with jitter."""
    ceiling = min(BACKOFF_MAX, BACKOFF_BASE * (2.0**attempt))
    return ceiling * random.uniform(0.5, 1.0)


def parse_retry_after(value: str | None) -> float | None:
    """Read a ``Retry-After`` header: a number of seconds or an HTTP date."""
    if value is None:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        moment = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, moment.timestamp() - time.time())


def _checked(response: Response) -> Response:
    content_type = response.header("content-type") or ""
    if response.body and "json" not in content_type and "csv" not in content_type:
        raise BYOMailerError(
            f"The instance sent {content_type or 'a response with no content type'}, "
            "not JSON. Make sure that base_url is the URL of a BYOMailer instance."
        )
    return response


def decode_body(response: Response) -> Any:
    """Return the JSON body, or the text body when the body is not JSON."""
    try:
        return response.json()
    except ValueError:
        return response.text


def error_from_response(response: Response) -> APIError:
    """Convert an error response to the matching error class."""
    body = decode_body(response)
    status = response.status_code
    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, str) or not message:
        message = f"HTTP {status}"

    if status == 429:
        return RateLimitError(
            message,
            status_code=status,
            body=body,
            headers=response.headers,
            retry_after=parse_retry_after(response.header("retry-after")),
        )
    if status >= 500:
        return ServerError(message, status_code=status, body=body, headers=response.headers)
    error_class = _ERRORS_BY_STATUS.get(status, APIError)
    return error_class(message, status_code=status, body=body, headers=response.headers)
