"""One test for each operation of each resource, with a mocked HTTP layer."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pytest

from byomailer import (
    UNSET,
    Block,
    BYOMailer,
    Contact,
    ContentVariables,
    EmailIdentity,
    EmailLog,
    EmailTemplate,
    MailList,
    Newsletter,
    Page,
    Project,
    Sequence,
    SequenceStats,
    SequenceStep,
    SequenceStepStats,
    SequenceSummary,
    Tag,
    TestEmail,
    Topic,
    ValidationError,
    WebhookDelivery,
    WebhookEndpoint,
)
from tests.conftest import FakeTransport
from tests.payloads import (
    BLOCK,
    CONTACT,
    DELIVERY,
    EMAIL_LOG,
    ENDPOINT,
    ENDPOINT_WITH_SECRET,
    IDENTITY,
    LIST,
    NEWSLETTER,
    PROJECT,
    SEQUENCE,
    SEQUENCE_STATS,
    SEQUENCE_SUMMARY,
    STEP,
    STEP_STATS,
    TAG,
    TEMPLATE,
    TOPIC,
    VARIABLES,
    cursor_page,
    data,
)

Call = Callable[[BYOMailer], Any]

# Each case: the call, the method, the path, the request body, the status,
# the response body and the type of the result.
CASES: list[tuple[str, Call, str, str, Any, int, Any, Any]] = [
    # Contacts
    ("contacts.list", lambda c: c.contacts.list(), "GET", "/contacts", None, 200, cursor_page([CONTACT]), Page),
    ("contacts.get", lambda c: c.contacts.get(42), "GET", "/contacts/42", None, 200, data(CONTACT), Contact),
    ("contacts.add", lambda c: c.contacts.add(3, "ana@example.com"), "POST", "/lists/3/contacts", {"email": "ana@example.com"}, 201, data(CONTACT), Contact),
    ("contacts.update", lambda c: c.contacts.update(42, name="Ana"), "PATCH", "/contacts/42", {"name": "Ana"}, 200, data(CONTACT), Contact),
    ("contacts.unsubscribe", lambda c: c.contacts.unsubscribe(42), "POST", "/contacts/42/unsubscribe", None, 200, data(CONTACT), Contact),
    ("contacts.subscribe", lambda c: c.contacts.subscribe(42), "POST", "/contacts/42/subscribe", None, 200, data(CONTACT), Contact),
    ("contacts.remove_from_list", lambda c: c.contacts.remove_from_list(3, 42), "DELETE", "/lists/3/contacts/42", None, 200, data(CONTACT), Contact),
    # Lists
    ("lists.list", lambda c: c.lists.list(), "GET", "/lists", None, 200, cursor_page([LIST]), Page),
    ("lists.create", lambda c: c.lists.create("Readers"), "POST", "/lists", {"name": "Readers"}, 201, data(LIST), MailList),
    ("lists.rename", lambda c: c.lists.rename(3, "Fans"), "PATCH", "/lists/3", {"name": "Fans"}, 200, data(LIST), MailList),
    ("lists.delete", lambda c: c.lists.delete(3), "DELETE", "/lists/3", None, 204, None, type(None)),
    # Topics
    ("topics.list", lambda c: c.topics.list(3), "GET", "/lists/3/topics", None, 200, data([TOPIC]), list),
    ("topics.create", lambda c: c.topics.create(3, "Releases"), "POST", "/lists/3/topics", {"name": "Releases", "description": None}, 201, data(TOPIC), Topic),
    ("topics.update", lambda c: c.topics.update(3, 8, name="News", description="Weekly"), "PATCH", "/lists/3/topics/8", {"name": "News", "description": "Weekly"}, 200, data(TOPIC), Topic),
    ("topics.delete", lambda c: c.topics.delete(3, 8), "DELETE", "/lists/3/topics/8", None, 204, None, type(None)),
    # Tags
    ("tags.list", lambda c: c.tags.list(), "GET", "/tags", None, 200, data([TAG]), list),
    ("tags.create", lambda c: c.tags.create("vip"), "POST", "/tags", {"name": "vip"}, 201, data(TAG), Tag),
    ("tags.rename", lambda c: c.tags.rename(5, "gold"), "PATCH", "/tags/5", {"name": "gold"}, 200, data(TAG), Tag),
    ("tags.delete", lambda c: c.tags.delete(5), "DELETE", "/tags/5", None, 204, None, type(None)),
    # Newsletters
    ("newsletters.list", lambda c: c.newsletters.list(), "GET", "/newsletters", None, 200, cursor_page([NEWSLETTER]), Page),
    ("newsletters.get", lambda c: c.newsletters.get(7), "GET", "/newsletters/7", None, 200, data(NEWSLETTER), Newsletter),
    ("newsletters.create", lambda c: c.newsletters.create(title="November news"), "POST", "/newsletters", {"title": "November news"}, 201, data(NEWSLETTER), Newsletter),
    ("newsletters.update", lambda c: c.newsletters.update(7, subject="Hi"), "PATCH", "/newsletters/7", {"subject": "Hi"}, 200, data(NEWSLETTER), Newsletter),
    ("newsletters.delete", lambda c: c.newsletters.delete(7), "DELETE", "/newsletters/7", None, 204, None, type(None)),
    ("newsletters.count_recipients", lambda c: c.newsletters.count_recipients(), "POST", "/newsletters/contacts/preview", {"filters": []}, 200, {"count": 12}, int),
    ("newsletters.send_test", lambda c: c.newsletters.send_test(7), "POST", "/newsletters/7/test-mail", None, 200, {"message": "Test email sent to admin@example.com", "sent_to": "admin@example.com"}, TestEmail),
    ("newsletters.pick_winner", lambda c: c.newsletters.pick_winner(7, "b"), "POST", "/newsletters/7/ab-winner", {"winner_variant": "b"}, 200, data(NEWSLETTER), Newsletter),
    ("newsletters.variables", lambda c: c.newsletters.variables(7), "GET", "/newsletters/7/variables", None, 200, data(VARIABLES), ContentVariables),
    ("newsletters.replace_variables", lambda c: c.newsletters.replace_variables(7, {"first_name": "friend"}), "PATCH", "/newsletters/7/variables", {"content_variables": {"first_name": "friend"}}, 200, data(VARIABLES), ContentVariables),
    # Sequences
    ("sequences.list", lambda c: c.sequences.list(), "GET", "/sequences", None, 200, cursor_page([SEQUENCE_SUMMARY]), Page),
    ("sequences.get", lambda c: c.sequences.get(2), "GET", "/sequences/2", None, 200, data(SEQUENCE), Sequence),
    ("sequences.stats", lambda c: c.sequences.stats(2), "GET", "/sequences/2/stats", None, 200, data(SEQUENCE_STATS), SequenceStats),
    ("sequences.step", lambda c: c.sequences.step(2, 11), "GET", "/sequences/2/steps/11", None, 200, data(STEP), SequenceStep),
    ("sequences.step_stats", lambda c: c.sequences.step_stats(2, 11), "GET", "/sequences/2/steps/11/stats", None, 200, data(STEP_STATS), SequenceStepStats),
    ("sequences.replace_step_filters", lambda c: c.sequences.replace_step_filters(2, 11, []), "PATCH", "/sequences/2/steps/11/filters", {"filters": []}, 200, data(STEP), SequenceStep),
    ("sequences.variables", lambda c: c.sequences.variables(2), "GET", "/sequences/2/variables", None, 200, data({**VARIABLES, "sequence_id": 2}), ContentVariables),
    ("sequences.replace_variables", lambda c: c.sequences.replace_variables(2, {}), "PATCH", "/sequences/2/variables", {"content_variables": {}}, 200, data(VARIABLES), ContentVariables),
    # Blocks
    ("blocks.list", lambda c: c.blocks.list(), "GET", "/blocks", None, 200, data([BLOCK]), list),
    ("blocks.get", lambda c: c.blocks.get(6), "GET", "/blocks/6", None, 200, data(BLOCK), Block),
    ("blocks.create", lambda c: c.blocks.create("footer", "<p>Bye</p>"), "POST", "/blocks", {"name": "footer", "html_content": "<p>Bye</p>"}, 201, data(BLOCK), Block),
    ("blocks.update", lambda c: c.blocks.update(6, name="footer", html_content="<p>B</p>"), "PATCH", "/blocks/6", {"name": "footer", "html_content": "<p>B</p>"}, 200, data(BLOCK), Block),
    ("blocks.delete", lambda c: c.blocks.delete(6), "DELETE", "/blocks/6", None, 204, None, type(None)),
    # Email templates
    ("email_templates.list", lambda c: c.email_templates.list(), "GET", "/email-templates", None, 200, cursor_page([TEMPLATE]), Page),
    ("email_templates.get", lambda c: c.email_templates.get(4), "GET", "/email-templates/4", None, 200, data(TEMPLATE), EmailTemplate),
    ("email_templates.default", lambda c: c.email_templates.default(), "GET", "/email-templates/default", None, 200, data(TEMPLATE), EmailTemplate),
    # Email identities
    ("email_identities.list", lambda c: c.email_identities.list(), "GET", "/email-identities", None, 200, cursor_page([IDENTITY]), Page),
    ("email_identities.get", lambda c: c.email_identities.get(1), "GET", "/email-identities/1", None, 200, data(IDENTITY), EmailIdentity),
    # Email logs
    ("email_logs.list", lambda c: c.email_logs.list(), "GET", "/email-logs", None, 200, cursor_page([EMAIL_LOG]), Page),
    ("email_logs.get", lambda c: c.email_logs.get(9), "GET", "/email-logs/9", None, 200, data(EMAIL_LOG), EmailLog),
    # Projects
    ("projects.list", lambda c: c.projects.list(), "GET", "/projects", None, 200, cursor_page([PROJECT]), Page),
    ("projects.get", lambda c: c.projects.get(1), "GET", "/projects/1", None, 200, data(PROJECT), Project),
    ("projects.create", lambda c: c.projects.create("Launch"), "POST", "/projects", {"name": "Launch"}, 201, data(PROJECT), Project),
    ("projects.rename", lambda c: c.projects.rename(1, "Relaunch"), "PATCH", "/projects/1", {"name": "Relaunch"}, 200, data(PROJECT), Project),
    ("projects.delete", lambda c: c.projects.delete(1), "DELETE", "/projects/1", None, 204, None, type(None)),
    # Webhook endpoints
    ("webhook_endpoints.list", lambda c: c.webhook_endpoints.list(), "GET", "/webhook-endpoints", None, 200, cursor_page([ENDPOINT]), Page),
    ("webhook_endpoints.get", lambda c: c.webhook_endpoints.get(12), "GET", "/webhook-endpoints/12", None, 200, data(ENDPOINT), WebhookEndpoint),
    ("webhook_endpoints.create", lambda c: c.webhook_endpoints.create("https://hooks.example.com/byomailer", ["contact.subscribed"]), "POST", "/webhook-endpoints", {"url": "https://hooks.example.com/byomailer", "events": ["contact.subscribed"]}, 201, data(ENDPOINT_WITH_SECRET), WebhookEndpoint),
    ("webhook_endpoints.update", lambda c: c.webhook_endpoints.update(12, active=False), "PATCH", "/webhook-endpoints/12", {"active": False}, 200, data(ENDPOINT), WebhookEndpoint),
    ("webhook_endpoints.delete", lambda c: c.webhook_endpoints.delete(12), "DELETE", "/webhook-endpoints/12", None, 204, None, type(None)),
    ("webhook_endpoints.deliveries", lambda c: c.webhook_endpoints.deliveries(12), "GET", "/webhook-endpoints/12/deliveries", None, 200, cursor_page([DELIVERY]), Page),
    ("webhook_endpoints.rotate_secret", lambda c: c.webhook_endpoints.rotate_secret(12), "POST", "/webhook-endpoints/12/secret", None, 200, data(ENDPOINT_WITH_SECRET), WebhookEndpoint),
    ("webhook_endpoints.send_test", lambda c: c.webhook_endpoints.send_test(12), "POST", "/webhook-endpoints/12/test", None, 202, data(DELIVERY), WebhookDelivery),
]  # fmt: skip


@pytest.mark.parametrize(
    ("name", "call", "method", "path", "body", "status", "response", "result_type"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_operation(
    client: BYOMailer,
    transport: FakeTransport,
    name: str,
    call: Call,
    method: str,
    path: str,
    body: Any,
    status: int,
    response: Any,
    result_type: Any,
) -> None:
    transport.reply(status, response)
    result = call(client)
    assert transport.last.method == method
    assert transport.path() == path
    assert transport.json() == body
    assert isinstance(result, result_type)


def test_every_resource_method_has_a_case() -> None:
    covered = {case[0] for case in CASES}
    extra = {
        "contacts.iter",
        "lists.iter",
        "newsletters.iter",
        "sequences.iter",
        "sequences.export_step_mails",
        "email_templates.iter",
        "email_identities.iter",
        "email_logs.iter",
        "projects.iter",
        "webhook_endpoints.iter",
        "webhook_endpoints.iter_deliveries",
    }
    client = BYOMailer("https://mail.example.com", "t", transport=FakeTransport())
    public: set[str] = set()
    for resource_name, resource in vars(client).items():
        if resource_name.startswith("_") or not hasattr(resource, "_client"):
            continue
        public |= {
            f"{resource_name}.{method}"
            for method in dir(resource)
            if not method.startswith("_") and callable(getattr(resource, method))
        }
    assert public == covered | extra


def test_add_contact_reports_a_new_contact(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(201, data(CONTACT))
    assert client.contacts.add(3, "ana@example.com").created is True


def test_add_contact_reports_an_existing_contact(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, data(CONTACT))
    assert client.contacts.add(3, "ana@example.com").created is False


def test_add_contact_sends_attributes_at_the_top_level(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(201, data(CONTACT))
    client.contacts.add(
        3,
        "ana@example.com",
        name="Ana",
        tags=("vip",),
        attributes={"company": "Example Inc", "plan": "pro"},
    )
    assert transport.json() == {
        "email": "ana@example.com",
        "name": "Ana",
        "tags": ["vip"],
        "company": "Example Inc",
        "plan": "pro",
    }


@pytest.mark.parametrize("field", ["email", "name", "tags", "remove_tags"])
def test_an_attribute_cannot_have_the_name_of_a_contact_field(
    client: BYOMailer, field: str
) -> None:
    with pytest.raises(ValueError, match="contact fields"):
        client.contacts.update(42, attributes={field: "x"})


def test_update_contact_sends_only_the_given_fields(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, data(CONTACT))
    client.contacts.update(42, name=None, remove_tags=["trial"], attributes={"plan": None})
    assert transport.json() == {"name": None, "remove_tags": ["trial"], "plan": None}


@pytest.mark.parametrize(
    ("field", "message"),
    [
        (
            "contact",
            "The contact unsubscribed through an email link. Only the contact can subscribe again.",
        ),
        ("email", "This email address has been blacklisted."),
    ],
)
def test_subscribe_refusal_is_a_validation_error(
    client: BYOMailer, transport: FakeTransport, field: str, message: str
) -> None:
    transport.reply(422, {"message": message, "errors": {field: [message]}})
    with pytest.raises(ValidationError) as caught:
        client.contacts.subscribe(42)
    assert caught.value.errors == {field: [message]}
    assert len(transport.requests) == 1


def test_contact_model(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, data(CONTACT))
    contact = client.contacts.get(42)
    assert contact.attributes == {"company": "Example Inc"}
    assert contact.created_at == datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)
    assert contact.tags[0] == Tag.from_dict(TAG)
    assert contact.lists[0].name == "Readers"
    assert contact.topics[0].list_id == 3
    assert contact.sequences[0].status == "live"
    assert contact.raw == CONTACT


def test_contact_list_filters(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([CONTACT], next_cursor="abc"))
    result = client.contacts.list(
        lists=[3, 4],
        tags=[5],
        topics=[],
        search="ana",
        include_unsubscribed=True,
        per_page=50,
        cursor="xyz",
    )
    assert transport.query() == [
        ("lists[]", "3"),
        ("lists[]", "4"),
        ("tags[]", "5"),
        ("search", "ana"),
        ("include_unsubscribed", "1"),
        ("per_page", "50"),
        ("cursor", "xyz"),
    ]
    assert result.next_cursor == "abc"
    assert result.prev_cursor is None
    assert [contact.id for contact in result] == [42]
    assert len(result) == 1


def test_newsletter_create_with_a_schedule(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(201, data(NEWSLETTER))
    client.newsletters.create(
        subject="Hello",
        html_content="<p>Hello</p>",
        status="live",
        scheduled_at=datetime(2026, 12, 1, 9, 0, tzinfo=timezone.utc),
        email_identity_id=1,
        filters=[{"category": "lists", "mode": "any", "values": [3]}],
        project_ids=(1,),
    )
    assert transport.json() == {
        "subject": "Hello",
        "html_content": "<p>Hello</p>",
        "status": "live",
        "scheduled_at": "2026-12-01T09:00:00+00:00",
        "email_identity_id": 1,
        "filters": [{"category": "lists", "mode": "any", "values": [3]}],
        "project_ids": [1],
    }


def test_newsletter_update_sends_none_to_clear_a_field(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, data(NEWSLETTER))
    client.newsletters.update(7, preview_text=None, email_template_id=None, subject=UNSET)
    assert transport.json() == {"preview_text": None, "email_template_id": None}


def test_newsletter_update_needs_a_field(client: BYOMailer) -> None:
    with pytest.raises(ValueError, match="at least one field"):
        client.newsletters.update(7)


def test_newsletter_list_filters(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([NEWSLETTER]))
    client.newsletters.list(status="sent", search="news", project=1, per_page=10)
    assert transport.query() == [
        ("status", "sent"),
        ("search", "news"),
        ("project", "1"),
        ("per_page", "10"),
    ]


def test_newsletter_model(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, data(NEWSLETTER))
    newsletter = client.newsletters.get(7)
    # PHP sends [] for an empty map. The model gives {}.
    assert newsletter.content_variables == {}
    assert newsletter.email_identity is not None
    assert newsletter.email_identity.domain == "example.com"
    assert newsletter.metrics is not None
    assert newsletter.metrics.open_rate == 0
    assert newsletter.project_ids == (1,)
    assert newsletter.html_content == "<p>Hello</p>"


def test_newsletter_summary_has_no_content(client: BYOMailer, transport: FakeTransport) -> None:
    summary = {key: value for key, value in NEWSLETTER.items() if "content" not in key}
    transport.reply(200, cursor_page([{**summary, "content_variables": {}}]))
    newsletter = client.newsletters.list().data[0]
    assert newsletter.html_content is None
    assert newsletter.text_content_b is None


def test_count_recipients_sends_the_filters(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, {"count": 3})
    filters = [{"category": "tags", "mode": "all", "values": ["vip"]}]
    assert client.newsletters.count_recipients(filters) == 3
    assert transport.json() == {"filters": filters}


def test_send_test_result(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, {"message": "Test email sent", "sent_to": "admin@example.com"})
    assert client.newsletters.send_test(7).sent_to == "admin@example.com"


def test_sequence_model(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, data(SEQUENCE))
    sequence = client.sequences.get(2)
    assert isinstance(sequence, Sequence)
    assert (sequence.contacts_count, sequence.completed_count, sequence.active_count) == (10, 4, 6)
    assert sequence.steps_count == 1
    assert sequence.steps[0].message is not None
    assert sequence.steps[0].message.email_template is not None
    assert sequence.steps[0].message.email_template.is_default is True
    assert sequence.filters == ()
    assert sequence.content_variables == {"first_name": "friend"}


def test_sequence_summary_model(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([SEQUENCE_SUMMARY]))
    sequence = client.sequences.list(status="live").data[0]
    assert isinstance(sequence, SequenceSummary)
    assert (sequence.contacts_count, sequence.completed_count, sequence.active_count) == (10, 4, 6)
    assert not hasattr(sequence, "steps")
    assert transport.query() == [("status", "live")]


def test_sequence_iter_yields_summaries(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([SEQUENCE_SUMMARY]))
    assert all(isinstance(item, SequenceSummary) for item in client.sequences.iter())


def test_sequence_stats_model(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, data(STEP_STATS))
    stats = client.sequences.step_stats(2, 11)
    assert stats.stats.clicked == 3
    assert stats.mail_metrics.open_rate == 55.6
    assert stats.mail_metrics.unsubscribe_rate is None


def test_export_step_mails_returns_csv_text(client: BYOMailer, transport: FakeTransport) -> None:
    csv = b"email,name,status\nana@example.com,Ana,opened\n"
    transport.reply(200, body=csv, headers={"Content-Type": "text/csv; charset=UTF-8"})
    text = client.sequences.export_step_mails(
        2,
        11,
        status="opened",
        sent_after=datetime(2026, 11, 1, tzinfo=timezone.utc),
        direction="desc",
    )
    assert text.splitlines() == ["email,name,status", "ana@example.com,Ana,opened"]
    assert transport.path().startswith("/sequences/2/steps/11/contact-mails/export?")
    assert transport.query() == [
        ("status", "opened"),
        ("sent_after", "2026-11-01T00:00:00+00:00"),
        ("direction", "desc"),
    ]


def test_email_template_list_filters(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([TEMPLATE]))
    client.email_templates.list(archived=False, is_default=True)
    assert transport.query() == [("archived", "0"), ("is_default", "1")]


def test_email_identity_and_email_log_filters(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(200, cursor_page([IDENTITY])).reply(200, cursor_page([EMAIL_LOG]))
    client.email_identities.list(identity_status="verified")
    logs = client.email_logs.list(status="failed", operation="SendEmail", recipient="ana")
    assert transport.query(0) == [("identity_status", "verified")]
    assert transport.query(1) == [
        ("status", "failed"),
        ("operation", "SendEmail"),
        ("recipient", "ana"),
    ]
    assert logs.data[0].response_payload == {"MessageId": "msg-1"}


def test_webhook_endpoint_secret_is_not_in_repr(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(201, data(ENDPOINT_WITH_SECRET))
    endpoint = client.webhook_endpoints.create(
        "https://hooks.example.com/byomailer",
        ["contact.subscribed", "newsletter.sent"],
        description="CRM",
    )
    assert endpoint.secret == "whsec_example0000000000"
    assert "whsec_" not in repr(endpoint)
    assert transport.json()["description"] == "CRM"


def test_webhook_endpoint_from_a_read_has_no_secret(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, data(ENDPOINT))
    endpoint = client.webhook_endpoints.get(12)
    assert endpoint.secret is None
    assert endpoint.events == ("contact.subscribed",)


def test_webhook_endpoint_update_needs_a_field(client: BYOMailer) -> None:
    with pytest.raises(ValueError, match="active, description"):
        client.webhook_endpoints.update(12)


def test_webhook_endpoint_update_can_clear_the_description(
    client: BYOMailer, transport: FakeTransport
) -> None:
    transport.reply(200, data(ENDPOINT))
    client.webhook_endpoints.update(12, description=None)
    assert transport.json() == {"description": None}


def test_webhook_delivery_model(client: BYOMailer, transport: FakeTransport) -> None:
    transport.reply(202, data(DELIVERY))
    delivery = client.webhook_endpoints.send_test(12)
    assert delivery.event_type == "webhook.test"
    assert delivery.payload["event"] == "webhook.test"
    assert delivery.dispatched_at == datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)
