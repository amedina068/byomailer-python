"""Webhook verification, with the vectors that the app code made (gen-vectors.php)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from byomailer import WebhookVerificationError, verify_webhook
from byomailer.webhooks import DEFAULT_TOLERANCE, sign

VECTORS: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "webhook-signature-vectors.json").read_text("utf-8")
)
CASES: list[dict[str, Any]] = VECTORS["cases"]
VALID = [case for case in CASES if case["valid"]]
INVALID = [case for case in CASES if not case["valid"]]

SECRET = "whsec_test0123456789abcdefghijklmnopqrstuvwxyz"


def headers_of(case: dict[str, Any]) -> dict[str, str]:
    return {
        "X-Byomailer-Signature": case["signature"],
        "X-Byomailer-Timestamp": case["timestamp"],
        "X-Byomailer-Event": json.loads(case["body"])["event"],
        "X-Byomailer-Delivery": "6f1c2d3e-0000-4000-8000-000000000000",
    }


def signed_headers(body: str, timestamp: str) -> dict[str, str]:
    return {
        "X-Byomailer-Timestamp": timestamp,
        "X-Byomailer-Signature": sign(timestamp, body, SECRET),
    }


def test_the_vectors_have_valid_and_invalid_cases() -> None:
    assert len(VALID) == 4
    assert len(INVALID) == 6
    assert VECTORS["tolerance_seconds"] == DEFAULT_TOLERANCE


@pytest.mark.parametrize("case", VALID, ids=[case["name"] for case in VALID])
def test_valid_vector_is_accepted(case: dict[str, Any]) -> None:
    body = case["body"].encode("utf-8")
    event = verify_webhook(body, headers_of(case), case["secret"], now=case["now"])
    assert event == json.loads(case["body"])
    assert event["event"]
    assert event["occurred_at"]


@pytest.mark.parametrize("case", INVALID, ids=[case["name"] for case in INVALID])
def test_invalid_vector_is_rejected_with_its_reason(case: dict[str, Any]) -> None:
    body = case["body"].encode("utf-8")
    with pytest.raises(WebhookVerificationError) as caught:
        verify_webhook(body, headers_of(case), case["secret"], now=case["now"])
    assert caught.value.reason == case["reason"]


@pytest.mark.parametrize("case", VALID, ids=[case["name"] for case in VALID])
def test_sign_matches_the_app(case: dict[str, Any]) -> None:
    assert sign(case["timestamp"], case["body"], case["secret"]) == case["signature"]


def test_a_body_with_unicode_escapes_is_verified_as_raw_bytes() -> None:
    case = next(case for case in VALID if "unicode" in case["name"])
    assert "\\u00e9" in case["body"]
    event = verify_webhook(case["body"], headers_of(case), SECRET, now=case["now"])
    assert event["contact"]["company"] == "Café Ñandú"
    # A new encoding of the same payload gives other bytes, and fails.
    encoded_again = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    with pytest.raises(WebhookVerificationError):
        verify_webhook(encoded_again, headers_of(case), SECRET, now=case["now"])


def test_header_names_are_not_case_sensitive() -> None:
    case = VALID[0]
    headers = {name.lower(): value for name, value in headers_of(case).items()}
    assert verify_webhook(case["body"], headers, SECRET, now=case["now"])["event"]


def test_missing_signature_header() -> None:
    case = VALID[0]
    headers = {"X-Byomailer-Timestamp": case["timestamp"]}
    with pytest.raises(WebhookVerificationError) as caught:
        verify_webhook(case["body"], headers, SECRET, now=case["now"])
    assert caught.value.reason == "signature"


def test_missing_timestamp_header() -> None:
    case = VALID[0]
    headers = {"X-Byomailer-Signature": case["signature"]}
    with pytest.raises(WebhookVerificationError) as caught:
        verify_webhook(case["body"], headers, SECRET, now=case["now"])
    assert caught.value.reason == "timestamp"


def test_timestamp_that_is_not_a_number() -> None:
    body = '{"event":"webhook.test"}'
    with pytest.raises(WebhookVerificationError) as caught:
        verify_webhook(body, signed_headers(body, "yesterday"), SECRET)
    assert caught.value.reason == "timestamp"


def test_signature_with_non_ascii_characters_is_rejected() -> None:
    case = VALID[0]
    headers = {**headers_of(case), "X-Byomailer-Signature": "sha256=é"}
    with pytest.raises(WebhookVerificationError) as caught:
        verify_webhook(case["body"], headers, SECRET, now=case["now"])
    assert caught.value.reason == "signature"


def test_tolerance_can_change() -> None:
    case = next(case for case in INVALID if case["name"] == "timestamp older than the tolerance")
    event = verify_webhook(case["body"], headers_of(case), SECRET, tolerance=600, now=case["now"])
    assert event["event"] == "newsletter.sent"
    with pytest.raises(WebhookVerificationError):
        verify_webhook(case["body"], headers_of(case), SECRET, tolerance=10, now=case["now"])


def test_the_tolerance_limit_is_inclusive() -> None:
    case = VALID[0]
    at_limit = int(case["timestamp"]) + DEFAULT_TOLERANCE
    assert verify_webhook(case["body"], headers_of(case), SECRET, now=at_limit)


def test_default_now_is_the_current_time() -> None:
    body = '{"event":"webhook.test","occurred_at":"2026-11-18T10:00:00+00:00"}'
    headers = signed_headers(body, str(int(time.time())))
    assert verify_webhook(body, headers, SECRET)["event"] == "webhook.test"


def test_unknown_event_type_is_accepted() -> None:
    body = '{"event":"contact.tagged","occurred_at":"2026-11-18T10:00:00+00:00","tag":{"id":1}}'
    event = verify_webhook(body, signed_headers(body, "1763460000"), SECRET, now=1763460000)
    assert event["event"] == "contact.tagged"
    assert event["tag"] == {"id": 1}
