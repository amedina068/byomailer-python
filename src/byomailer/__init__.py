"""Python client for BYOMailer, the self-hosted newsletter app for Amazon SES.

Example::

    from byomailer import BYOMailer

    client = BYOMailer("https://mail.example.com", token="...")
    contact = client.contacts.add(3, "ana@example.com", name="Ana", tags=["vip"])
    print(contact.id, contact.created)
"""

from byomailer._client import BYOMailer
from byomailer._http import Request, Response, Transport, UrllibTransport
from byomailer._resource import UNSET
from byomailer._version import __version__
from byomailer.errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    AuthorizationError,
    BYOMailerError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
    WebhookVerificationError,
)
from byomailer.models import (
    Block,
    Contact,
    ContactSequence,
    ContactStats,
    ContentVariables,
    EmailIdentity,
    EmailLog,
    EmailTemplate,
    MailList,
    MailMetrics,
    Newsletter,
    NewsletterMetrics,
    Page,
    Project,
    Sequence,
    SequenceStats,
    SequenceStep,
    SequenceStepStats,
    SequenceSummary,
    StepMessage,
    Tag,
    TestEmail,
    Topic,
    WebhookDelivery,
    WebhookEndpoint,
)
from byomailer.webhooks import WebhookEvent, verify_webhook

__all__ = [
    "UNSET",
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AuthenticationError",
    "AuthorizationError",
    "BYOMailer",
    "BYOMailerError",
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
    "NotFoundError",
    "Page",
    "Project",
    "RateLimitError",
    "Request",
    "Response",
    "Sequence",
    "SequenceStats",
    "SequenceStep",
    "SequenceStepStats",
    "SequenceSummary",
    "ServerError",
    "StepMessage",
    "Tag",
    "TestEmail",
    "Topic",
    "Transport",
    "UrllibTransport",
    "ValidationError",
    "WebhookDelivery",
    "WebhookEndpoint",
    "WebhookEvent",
    "WebhookVerificationError",
    "__version__",
    "verify_webhook",
]
