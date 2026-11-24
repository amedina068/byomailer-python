"""Verify the webhook deliveries of BYOMailer.

BYOMailer signs each delivery with the secret of the endpoint. The
``X-Byomailer-Signature`` header is ``sha256=`` and the HMAC-SHA256 hex digest
of ``<X-Byomailer-Timestamp>.<raw body>``.

Use this module only on a server. The endpoint secret is a secret.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from byomailer.errors import WebhookVerificationError

__all__ = [
    "DEFAULT_TOLERANCE",
    "DELIVERY_HEADER",
    "EVENT_HEADER",
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "WebhookEvent",
    "sign",
    "verify_webhook",
]

SIGNATURE_HEADER: Final = "X-Byomailer-Signature"
TIMESTAMP_HEADER: Final = "X-Byomailer-Timestamp"
EVENT_HEADER: Final = "X-Byomailer-Event"
DELIVERY_HEADER: Final = "X-Byomailer-Delivery"

DEFAULT_TOLERANCE: Final = 300
"""The maximum age of a delivery, in seconds, before or after the current time."""


@dataclass(frozen=True)
class WebhookEvent:
    """A webhook delivery that passed the verification.

    Attributes:
        type: The event type: ``event`` of the payload, or the
            ``X-Byomailer-Event`` header.
        payload: The decoded JSON body.
        timestamp: The Unix time when the instance signed the delivery.
        delivery_id: The UUID of the delivery, from the ``X-Byomailer-Delivery``
            header. Use it to ignore a delivery that you received before.
            ``None`` when the header is missing, because an older instance
            does not send it.
    """

    type: str
    payload: dict[str, Any]
    timestamp: int
    delivery_id: str | None


def verify_webhook(
    payload: bytes | str,
    headers: Mapping[str, str],
    secret: str,
    *,
    tolerance: int = DEFAULT_TOLERANCE,
    now: float | None = None,
) -> WebhookEvent:
    """Verify one webhook delivery and return the verified event.

    Example::

        event = verify_webhook(request.body, request.headers, settings.BYOMAILER_WEBHOOK_SECRET)
        if event.type == "contact.unsubscribed":
            email = event.payload["contact"]["email"]

    The checks run in the same order as in the other SDKs: the signature
    header, the timestamp header, the signature, the tolerance and the body.

    Args:
        payload: The raw request body, byte for byte. Do not decode the JSON and
            encode it again: a new encoding gives other bytes.
        headers: The request headers. The names are not case-sensitive.
        secret: The secret of the endpoint, with its ``whsec_`` prefix.
        tolerance: The maximum age of the delivery in seconds. The default is 300.
        now: The current Unix time. The default is ``time.time()``. Tests use it.

    Raises:
        WebhookVerificationError: The signature is missing or wrong
            (``reason="signature"``), the timestamp is missing, not a Unix time
            or outside the tolerance (``reason="timestamp"``), or the body is
            not a JSON object (``reason="payload"``).
    """
    body = payload.encode("utf-8") if isinstance(payload, str) else payload
    signature = _header(headers, SIGNATURE_HEADER)
    timestamp = _header(headers, TIMESTAMP_HEADER)

    if signature is None:
        raise WebhookVerificationError(
            f"The {SIGNATURE_HEADER} header is missing.", reason="signature"
        )
    if timestamp is None or not (timestamp.isascii() and timestamp.isdigit()):
        raise WebhookVerificationError(
            f"The {TIMESTAMP_HEADER} header is missing or is not a Unix time.",
            reason="timestamp",
        )
    expected = sign(timestamp, body, secret)
    received = signature.strip().lower().encode("utf-8")
    if not hmac.compare_digest(expected.encode("utf-8"), received):
        raise WebhookVerificationError("The signature does not match.", reason="signature")

    current = time.time() if now is None else now
    if abs(current - int(timestamp)) > tolerance:
        raise WebhookVerificationError(
            f"The timestamp is more than {tolerance} seconds from the current time.",
            reason="timestamp",
        )

    try:
        data = json.loads(body)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise WebhookVerificationError(
            "The signature is valid, but the body is not a JSON object.", reason="payload"
        )

    event = data.get("event")
    return WebhookEvent(
        type=event if isinstance(event, str) else _header(headers, EVENT_HEADER) or "",
        payload=data,
        timestamp=int(timestamp),
        delivery_id=_header(headers, DELIVERY_HEADER) or None,
    )


def sign(timestamp: str, payload: bytes | str, secret: str) -> str:
    """Return the ``X-Byomailer-Signature`` value for a timestamp and a raw body.

    A test can use this function to make a signed delivery.
    """
    body = payload.encode("utf-8") if isinstance(payload, str) else payload
    signed_payload = timestamp.encode("utf-8") + b"." + body
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _header(headers: Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    if value is not None:
        return value
    wanted = name.lower()
    for key, item in headers.items():
        if key.lower() == wanted:
            return item
    return None
