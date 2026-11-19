"""Typed response models.

Each model is a frozen dataclass. The ``raw`` field keeps the JSON object from
the instance, so you can read a field that this version of the package does
not know. A field that the response does not have is ``None``.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Generic, TypeVar

__all__ = [
    "Block",
    "Contact",
    "ContactSequence",
    "ContactStats",
    "ContentVariables",
    "EmailIdentity",
    "EmailLog",
    "EmailTemplate",
    "MailList",
    "MailMetrics",
    "Newsletter",
    "NewsletterMetrics",
    "Page",
    "Project",
    "Sequence",
    "SequenceStats",
    "SequenceStep",
    "SequenceStepStats",
    "SequenceSummary",
    "StepMessage",
    "Tag",
    "TestEmail",
    "Topic",
    "WebhookDelivery",
    "WebhookEndpoint",
]

T = TypeVar("T")
M = TypeVar("M", bound="Model")


def _raw() -> Any:
    return field(default_factory=dict, repr=False, compare=False)


class Model:
    """The base of each response model. It builds the model from a JSON object."""

    raw: Mapping[str, Any]

    # Fields that the client sets itself. They do not come from the JSON object.
    _local_fields: ClassVar[frozenset[str]] = frozenset({"raw"})

    @classmethod
    def from_dict(cls: type[M], data: Mapping[str, Any]) -> M:
        hints = typing.get_type_hints(cls)
        values: dict[str, Any] = {
            item.name: _convert(hints[item.name], data.get(item.metadata.get("key", item.name)))
            for item in dataclasses.fields(cls)  # type: ignore[arg-type]
            if item.name not in cls._local_fields
        }
        values["raw"] = data
        return cls(**values)


def _convert(hint: Any, value: Any) -> Any:
    """Convert one JSON value to the type of its field.

    The function converts ISO 8601 strings to ``datetime``, objects to nested
    models, and lists to tuples. It keeps each other value as it is.
    """
    optional = _is_optional(hint)
    hint = _without_none(hint)
    origin = typing.get_origin(hint)

    if value is None:
        if optional:
            return None
        if origin is tuple:
            return ()
        if origin in (dict, Mapping):
            return {}
        return None
    if hint is datetime:
        return _datetime(value)
    if isinstance(hint, type) and issubclass(hint, Model) and isinstance(value, Mapping):
        return hint.from_dict(value)
    if origin is tuple and isinstance(value, list):
        item_hint = typing.get_args(hint)[0]
        return tuple(_convert(item_hint, item) for item in value)
    if origin in (dict, Mapping) and isinstance(value, list) and not value:
        # PHP encodes an empty associative array as [], not {}.
        return {}
    return value


def _is_optional(hint: Any) -> bool:
    return isinstance(hint, types.UnionType) and type(None) in typing.get_args(hint)


def _without_none(hint: Any) -> Any:
    if not isinstance(hint, types.UnionType):
        return hint
    args = [arg for arg in typing.get_args(hint) if arg is not type(None)]
    return args[0] if len(args) == 1 else hint


def _datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        # The raw field keeps the original string.
        return None


@dataclass(frozen=True)
class Page(Generic[T]):
    """One page of a list. Give ``next_cursor`` as ``cursor`` to get the next page."""

    data: tuple[T, ...]
    next_cursor: str | None = None
    prev_cursor: str | None = None

    def __iter__(self) -> Iterator[T]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class Tag(Model):
    id: int
    uuid: str
    name: str
    created_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class MailList(Model):
    """A mailing list."""

    id: int
    uuid: str
    name: str
    opt_in_enabled: bool | None
    created_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class Topic(Model):
    id: int
    uuid: str
    list_id: int
    name: str
    description: str | None
    created_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class ContactSequence(Model):
    """A sequence that a contact is in."""

    id: int
    name: str
    status: str
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class Contact(Model):
    """A contact.

    ``attributes`` holds the custom attributes. ``created`` is ``True`` only
    when ``contacts.add()`` made a new contact (the instance sent 201).
    """

    _local_fields: ClassVar[frozenset[str]] = frozenset({"raw", "created"})

    id: int
    uuid: str
    email: str
    name: str | None
    attributes: Mapping[str, Any] = field(metadata={"key": "extra_attributes"})
    unsubscribed_at: datetime | None
    unsubscribed_by_contact: bool | None
    tags: tuple[Tag, ...]
    lists: tuple[MailList, ...]
    topics: tuple[Topic, ...]
    sequences: tuple[ContactSequence, ...]
    created_at: datetime | None
    created: bool = False
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class EmailIdentity(Model):
    """A verified sender address or domain in Amazon SES."""

    id: int
    uuid: str
    email: str | None
    name: str | None
    domain: str | None
    identity_status: str | None
    verified_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class EmailTemplate(Model):
    id: int
    name: str
    html_content: str | None
    is_default: bool
    archived_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class NewsletterMetrics(Model):
    """The delivery counts of a newsletter. The rates are percentages."""

    total: int
    sent: int
    pending: int
    opened: int
    bounced: int
    unsubscribed: int
    complained: int
    open_rate: float
    unsubscribe_rate: float
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class Newsletter(Model):
    """A newsletter.

    ``newsletters.list()`` does not send the content fields ``html_content``,
    ``text_content``, ``html_content_b`` and ``text_content_b``. For a
    newsletter from a list, they are ``None``.
    """

    id: int
    uuid: str
    title: str
    status: str
    subject: str | None
    preview_text: str | None
    email_identity_id: int | None
    email_identity: EmailIdentity | None
    email_template_id: int | None
    from_email: str | None
    from_name: str | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    segment_id: int | None
    filters: tuple[Mapping[str, Any], ...]
    content_variables: Mapping[str, str]
    ab_test_enabled: bool
    ab_test_winner_variant: str | None
    subject_b: str | None
    preview_text_b: str | None
    total_contacts_reached: int
    metrics: NewsletterMetrics | None
    created_at: datetime | None
    updated_at: datetime | None
    project_ids: tuple[int, ...] | None = None
    html_content: str | None = None
    text_content: str | None = None
    html_content_b: str | None = None
    text_content_b: str | None = None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class TestEmail(Model):
    """The result of ``newsletters.send_test()``."""

    __test__ = False  # Not a pytest test class.

    message: str
    sent_to: str
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class ContentVariables(Model):
    """The ``{{ variables }}`` of a newsletter or a sequence.

    ``detected_variables`` lists the variables that the content uses.
    ``content_variables`` maps each variable to its default value. The
    default fills the variable when the contact has no value for it.
    """

    detected_variables: tuple[str, ...]
    content_variables: Mapping[str, str]
    newsletter_id: int | None = None
    sequence_id: int | None = None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class StepMessage(Model):
    """The email of a sequence step."""

    id: int
    subject: str | None
    preview_text: str | None
    html_content: str | None
    text_content: str | None
    email_identity_id: int | None
    email_template_id: int | None
    template_slot_content: str | None
    email_template: EmailTemplate | None
    email_identity: EmailIdentity | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class SequenceStep(Model):
    id: int
    sequence_id: int
    delay_days: int | None
    delay_type: str | None
    status: str
    filters: tuple[Mapping[str, Any], ...]
    message: StepMessage | None
    created_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class SequenceSummary(Model):
    """A sequence in the result of ``sequences.list()``. Get the steps with ``sequences.get()``.

    ``active_count`` is the number of contacts that did not complete the sequence.
    """

    id: int
    name: str
    status: str
    steps_count: int
    contacts_count: int
    completed_count: int
    active_count: int
    project_ids: tuple[int, ...] | None = None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class Sequence(Model):
    """A sequence with its steps, its filters and its content variables.

    ``active_count`` is the number of contacts that did not complete the sequence.
    """

    id: int
    name: str
    status: str
    steps_count: int
    contacts_count: int
    completed_count: int
    active_count: int
    steps: tuple[SequenceStep, ...]
    segment_id: int | None
    filters: tuple[Mapping[str, Any], ...]
    content_variables: Mapping[str, str]
    created_at: datetime | None
    project_ids: tuple[int, ...] | None = None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class ContactStats(Model):
    contacts: int
    unsubscribed: int
    clicked: int
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class MailMetrics(Model):
    """The mail counts of a sequence or a step. A rate is ``None`` when no mail went out."""

    total: int
    sent: int
    delivered: int
    pending: int
    skipped: int
    opened: int
    bounced: int
    unsubscribed: int
    complained: int
    delivery_rate: float | None
    open_rate: float | None
    unsubscribe_rate: float | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class SequenceStats(Model):
    id: int
    name: str
    status: str
    stats: ContactStats
    mail_metrics: MailMetrics
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class SequenceStepStats(Model):
    """The statistics of one step, for the contacts whose furthest step is this step."""

    id: int
    sequence_id: int
    subject: str | None
    delay_days: int | None
    delay_type: str | None
    status: str
    stats: ContactStats
    mail_metrics: MailMetrics
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class Block(Model):
    """A reusable piece of HTML."""

    id: int
    uuid: str
    name: str
    html_content: str
    created_at: datetime | None
    updated_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class EmailLog(Model):
    """One call to Amazon SES, or one notification from it."""

    id: int
    provider: str | None
    operation: str | None
    recipient: str | None
    message_id: str | None
    status: str | None
    error: str | None
    request_payload: Any
    response_payload: Any
    sns_payload: Any
    logged_at: datetime | None
    created_at: datetime | None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class Project(Model):
    id: int
    uuid: str
    name: str
    created_at: datetime | None
    newsletters_count: int | None = None
    sequences_count: int | None = None
    automations_count: int | None = None
    visual_automations_count: int | None = None
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class WebhookEndpoint(Model):
    """A webhook endpoint.

    ``secret`` is set only in the result of ``create()`` and ``rotate_secret()``.
    The instance does not send it again. ``repr()`` never shows it.
    """

    id: int
    uuid: str
    url: str
    description: str | None
    events: tuple[str, ...]
    active: bool
    disabled_reason: str | None
    consecutive_failures: int
    last_triggered_at: datetime | None
    disabled_at: datetime | None
    created_at: datetime | None
    secret: str | None = field(default=None, repr=False)
    raw: Mapping[str, Any] = _raw()


@dataclass(frozen=True)
class WebhookDelivery(Model):
    """One delivery of an event to a webhook endpoint."""

    id: int
    uuid: str
    event_type: str
    status: str
    attempts: int
    response_status: int | None
    response_body: str | None
    error: str | None
    payload: Mapping[str, Any]
    dispatched_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime | None
    raw: Mapping[str, Any] = _raw()
