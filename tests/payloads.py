"""Response bodies in the shapes of the app resources (app/Http/Resources)."""

from __future__ import annotations

from typing import Any

NOW = "2026-11-18T10:00:00.000000Z"
NOW_ISO = "2026-11-18T10:00:00+00:00"

TAG: dict[str, Any] = {"id": 5, "uuid": "tag-uuid", "name": "vip", "created_at": NOW}

LIST: dict[str, Any] = {
    "id": 3,
    "uuid": "list-uuid",
    "name": "Readers",
    "opt_in_enabled": False,
    "created_at": NOW,
}

TOPIC: dict[str, Any] = {
    "id": 8,
    "uuid": "topic-uuid",
    "list_id": 3,
    "name": "Releases",
    "description": None,
    "created_at": NOW,
}

CONTACT: dict[str, Any] = {
    "id": 42,
    "uuid": "contact-uuid",
    "name": "Ana",
    "email": "ana@example.com",
    "extra_attributes": {"company": "Example Inc"},
    "unsubscribed_at": None,
    "unsubscribed_by_contact": False,
    "tags": [TAG],
    "lists": [LIST],
    "topics": [TOPIC],
    "sequences": [{"id": 2, "name": "Welcome", "status": "live"}],
    "created_at": NOW,
}

IDENTITY: dict[str, Any] = {
    "id": 1,
    "uuid": "identity-uuid",
    "email": "news@example.com",
    "name": "Example News",
    "domain": "example.com",
    "identity_status": "verified",
    "verified_at": NOW,
    "created_at": NOW,
    "updated_at": NOW,
}

TEMPLATE: dict[str, Any] = {
    "id": 4,
    "name": "Default",
    "html_content": "<html>{{ content }}</html>",
    "is_default": True,
    "archived_at": None,
    "created_at": NOW,
    "updated_at": NOW,
}

NEWSLETTER: dict[str, Any] = {
    "id": 7,
    "uuid": "newsletter-uuid",
    "title": "November news",
    "status": "draft",
    "subject": "Hello",
    "preview_text": None,
    "email_identity_id": 1,
    "email_identity": IDENTITY,
    "email_template_id": None,
    "from_email": "news@example.com",
    "from_name": "Example News",
    "scheduled_at": None,
    "sent_at": None,
    "segment_id": None,
    "filters": [],
    "content_variables": [],
    "ab_test_enabled": False,
    "ab_test_winner_variant": None,
    "subject_b": None,
    "preview_text_b": None,
    "total_contacts_reached": 0,
    "project_ids": [1],
    "metrics": {
        "total": 0,
        "sent": 0,
        "pending": 0,
        "opened": 0,
        "bounced": 0,
        "unsubscribed": 0,
        "complained": 0,
        "open_rate": 0,
        "unsubscribe_rate": 0,
    },
    "created_at": NOW,
    "updated_at": NOW,
    "html_content": "<p>Hello</p>",
    "text_content": "Hello",
    "html_content_b": None,
    "text_content_b": None,
}

STEP: dict[str, Any] = {
    "id": 11,
    "sequence_id": 2,
    "delay_days": 1,
    "delay_type": "days",
    "status": "live",
    "filters": [],
    "message": {
        "id": 30,
        "subject": "Welcome",
        "preview_text": None,
        "html_content": "<p>Hi</p>",
        "text_content": "Hi",
        "email_identity_id": 1,
        "email_template_id": 4,
        "template_slot_content": "<p>Hi</p>",
        "email_template": TEMPLATE,
        "email_identity": IDENTITY,
    },
    "created_at": NOW,
}

SEQUENCE: dict[str, Any] = {
    "id": 2,
    "name": "Welcome",
    "status": "live",
    "contacts_count": 10,
    "completed_count": 4,
    "active_count": 6,
    "steps_count": 1,
    "steps": [STEP],
    "segment_id": None,
    "filters": [],
    "content_variables": {"first_name": "friend"},
    "created_at": NOW,
    "project_ids": [],
}

SEQUENCE_SUMMARY: dict[str, Any] = {
    "id": 2,
    "name": "Welcome",
    "status": "live",
    "steps_count": 1,
    "contacts_count": 10,
    "completed_count": 4,
    "active_count": 6,
}

CONTACT_STATS: dict[str, Any] = {"contacts": 10, "unsubscribed": 1, "clicked": 3}

MAIL_METRICS: dict[str, Any] = {
    "total": 10,
    "sent": 9,
    "delivered": 9,
    "pending": 1,
    "skipped": 0,
    "opened": 5,
    "bounced": 0,
    "unsubscribed": 1,
    "complained": 0,
    "delivery_rate": 100.0,
    "open_rate": 55.6,
    "unsubscribe_rate": None,
}

SEQUENCE_STATS: dict[str, Any] = {
    "id": 2,
    "name": "Welcome",
    "status": "live",
    "stats": CONTACT_STATS,
    "mail_metrics": MAIL_METRICS,
}

STEP_STATS: dict[str, Any] = {
    "id": 11,
    "sequence_id": 2,
    "subject": "Welcome",
    "delay_days": 1,
    "delay_type": "days",
    "status": "live",
    "stats": CONTACT_STATS,
    "mail_metrics": MAIL_METRICS,
}

BLOCK: dict[str, Any] = {
    "id": 6,
    "uuid": "block-uuid",
    "name": "footer",
    "html_content": "<p>Bye</p>",
    "created_at": NOW,
    "updated_at": NOW,
}

EMAIL_LOG: dict[str, Any] = {
    "id": 9,
    "provider": "ses",
    "operation": "SendEmail",
    "recipient": "ana@example.com",
    "message_id": "msg-1",
    "status": "success",
    "error": None,
    "request_payload": {"Destination": {}},
    "response_payload": {"MessageId": "msg-1"},
    "sns_payload": None,
    "logged_at": NOW,
    "created_at": NOW,
}

PROJECT: dict[str, Any] = {
    "id": 1,
    "uuid": "project-uuid",
    "name": "Launch",
    "newsletters_count": 2,
    "sequences_count": 1,
    "automations_count": 0,
    "visual_automations_count": 0,
    "created_at": NOW,
}

ENDPOINT: dict[str, Any] = {
    "id": 12,
    "uuid": "endpoint-uuid",
    "url": "https://hooks.example.com/byomailer",
    "description": None,
    "events": ["contact.subscribed"],
    "active": True,
    "disabled_reason": None,
    "consecutive_failures": 0,
    "last_triggered_at": None,
    "disabled_at": None,
    "created_at": NOW_ISO,
}

ENDPOINT_WITH_SECRET: dict[str, Any] = {**ENDPOINT, "secret": "whsec_example0000000000"}

DELIVERY: dict[str, Any] = {
    "id": 20,
    "uuid": "delivery-uuid",
    "event_type": "webhook.test",
    "status": "pending",
    "attempts": 0,
    "response_status": None,
    "response_body": None,
    "error": None,
    "payload": {"event": "webhook.test", "occurred_at": NOW_ISO},
    "dispatched_at": NOW_ISO,
    "delivered_at": None,
    "created_at": NOW_ISO,
}

VARIABLES: dict[str, Any] = {
    "newsletter_id": 7,
    "detected_variables": ["first_name"],
    "content_variables": {"first_name": ""},
}


def data(item: Any) -> dict[str, Any]:
    return {"data": item}


def cursor_page(items: list[Any], next_cursor: str | None = None) -> dict[str, Any]:
    """A body of a Laravel cursor paginator."""
    return {
        "data": items,
        "links": {"first": None, "last": None, "prev": None, "next": None},
        "meta": {
            "path": "https://mail.example.com/api/v1/x",
            "per_page": 25,
            "next_cursor": next_cursor,
            "prev_cursor": None,
        },
    }
