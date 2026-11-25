# byomailer

[![CI](https://github.com/amedina068/byomailer-python/actions/workflows/ci.yml/badge.svg)](https://github.com/amedina068/byomailer-python/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/amedina068/byomailer-python/badge)](https://scorecard.dev/viewer/?uri=github.com/amedina068/byomailer-python)

The Python client for BYOMailer. BYOMailer is a self-hosted app that sends newsletters and email sequences through your own Amazon SES account.

Each user runs their own BYOMailer instance, so the URL of your instance is a required setting.

```python
from byomailer import BYOMailer

client = BYOMailer("https://mail.example.com", token="...")

contact = client.contacts.add(3, "ana@example.com", name="Ana", tags=["vip"])
print(contact.id, contact.created)  # created is True for a new contact

for contact in client.contacts.iter(tags=[5]):
    print(contact.email)
```

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Resources](#resources)
- [Pagination](#pagination)
- [Webhook verification](#webhook-verification)
- [Errors](#errors)
- [Retries](#retries)
- [Django and FastAPI](#django-and-fastapi)
- [Supported Python versions](#supported-python-versions)
- [License](#license)

## Install

The package is not on PyPI yet. Install it from the repository:

```bash
pip install "git+https://github.com/amedina068/byomailer-python.git"
# or
uv add "git+https://github.com/amedina068/byomailer-python.git"
```

The package has no dependencies. It uses only the Python standard library.

## Quick start

1. Open your BYOMailer instance and go to the settings for API tokens.
2. Create a personal API token. Give it read access, or read and write access.
3. Keep the token in an environment variable, for example `BYOMAILER_TOKEN`.
4. Make a client and send a request:

   ```python
   from byomailer import BYOMailer

   client = BYOMailer("https://mail.example.com")  # reads $BYOMAILER_TOKEN
   for mail_list in client.lists.iter():
       print(mail_list.id, mail_list.name)
   ```

A read-only token gets `AuthorizationError` (403) on each request that changes data.

## Configuration

```python
from byomailer import BYOMailer

client = BYOMailer(
    "https://mail.example.com",  # default: $BYOMAILER_URL
    token="...",  # default: $BYOMAILER_TOKEN
    timeout=30.0,  # seconds. None: no timeout
    max_retries=2,  # 0 stops all retries
)
```

| Setting | Default | Description |
|---|---|---|
| `base_url` | `$BYOMAILER_URL` | The URL of your instance. The client adds `/api/v1`. It removes a trailing `/`, `/api` or `/api/v1`. |
| `token` | `$BYOMAILER_TOKEN` | A personal API token. The client sends it as `Authorization: Bearer <token>`. |
| `timeout` | 30 seconds | The time to wait for the connection and for each read. |
| `max_retries` | 2 | The number of retries. Read [Retries](#retries). |
| `transport` | `UrllibTransport()` | The object that sends the HTTP requests. |

The client does not show the token in `repr()`. The client does not follow redirects, because a redirect can send the token to another host.

### Custom transport

A transport is a callable. It takes a `Request` and a timeout, and it returns a `Response`. Give your own transport to use another HTTP library:

```python
from byomailer import BYOMailer, Request, Response


def my_transport(request: Request, timeout: float | None) -> Response:
    # Send request.method, request.url, request.headers and request.body.
    ...


client = BYOMailer("https://mail.example.com", token="...", transport=my_transport)
```

The transport must return a `Response` for each status code. When it gets no response, it must raise `APIConnectionError`. Set `request_sent=False` only when the instance did not receive the request.

## Resources

Each method returns a frozen dataclass. The `raw` field of a model holds the JSON object from the instance. Use `raw` to read a field that this version of the package does not know.

IDs are integers. Dates are `datetime` objects in UTC.

### Contacts

```python
page = client.contacts.list(lists=[3], tags=[5], search="ana", per_page=50)
for contact in client.contacts.iter(include_unsubscribed=True):
    ...
contact = client.contacts.get(42)
```

`lists`, `tags` and `topics` are IDs. The list leaves out unsubscribed contacts, unless `include_unsubscribed=True`.

Add a contact to a list. If the contact does not exist, the instance creates it:

```python
contact = client.contacts.add(
    3,  # list ID
    "ana@example.com",
    name="Ana",
    tags=["vip"],  # tag names. The instance creates a tag that does not exist.
    attributes={"company": "Example Inc", "plan": "pro"},
)
if contact.created:
    print("New contact")
```

`contact.created` is `True` when the instance created the contact (201), and `False` when the contact existed (200).

If an admin or the API unsubscribed the contact, `add()` subscribes the contact again. An unsubscribe that the contact made stays. On a list with opt-in, the instance sends the opt-in email only when the contact is new on the list.

Change a contact. Only the fields that you give change:

```python
contact = client.contacts.update(
    42, name="Ana P.", remove_tags=["trial"], attributes={"plan": "team"}
)
print(contact.attributes)
```

`tags` adds tags and `remove_tags` removes tags. `attributes` sets custom attributes and keeps the other attributes. The client sends each attribute at the top level of the request body, as the API expects. An attribute cannot have the name `email`, `name`, `tags` or `remove_tags`.

`update()` never changes the subscription of the contact.

Unsubscribe a contact, subscribe a contact again, or remove a contact from one list:

```python
client.contacts.unsubscribe(42)  # stops all email. The contact stays on its lists.
contact = client.contacts.subscribe(42)  # clears an unsubscribe that an admin or the API made
contact = client.contacts.remove_from_list(3, 42)  # list 3, contact 42. Returns the contact.
```

`subscribe()` does not change a subscribed contact. It raises `ValidationError` in two cases:

- The contact unsubscribed through an email link. The error is in `errors["contact"]`. Only the contact can subscribe again.
- The email address is blacklisted. The error is in `errors["email"]`.

```python
from byomailer import ValidationError

try:
    client.contacts.subscribe(42)
except ValidationError as error:
    if "contact" in error.errors:
        print("The contact unsubscribed through an email link.")
```

### Lists

```python
page = client.lists.list()
for mail_list in client.lists.iter():
    ...
mail_list = client.lists.create("Readers")
mail_list = client.lists.rename(3, "Fans")
client.lists.delete(3)
```

### Topics

A topic is a subject inside a list. A contact can unsubscribe from one topic and stay on the list.

```python
topics = client.topics.list(3)  # all topics of list 3. No pages.
topic = client.topics.create(3, "Releases", description="One email for each release")
topic = client.topics.update(3, 8, name="News", description=None)  # replaces both fields
client.topics.delete(3, 8)
```

### Tags

```python
tags = client.tags.list()  # all tags. No pages.
tag = client.tags.create("vip")
tag = client.tags.rename(5, "gold")
client.tags.delete(5)
```

### Newsletters

```python
page = client.newsletters.list(status="draft", search="November", project=1)
for newsletter in client.newsletters.iter(status="sent"):
    print(newsletter.title, newsletter.metrics)
newsletter = client.newsletters.get(7)  # includes html_content and text_content
```

`list()` and `iter()` do not include the content fields. For a newsletter from a list, `html_content` is `None`.

Create a draft:

```python
newsletter = client.newsletters.create(
    title="November news",
    subject="What is new in November",
    html_content="<p>Hello {{ first_name }}</p>",
    email_identity_id=1,
    filters=[{"category": "lists", "mode": "any", "values": [3]}],
    content_variables={"first_name": "friend"},
)
```

Change a draft or a scheduled newsletter. Only the fields that you give change. `None` clears a field:

```python
newsletter = client.newsletters.update(7, subject="New subject", preview_text=None)
```

> **CAUTION:** `status="live"` with `scheduled_at` schedules the newsletter. If `scheduled_at` is the current time, the instance sends the newsletter at once.

A `scheduled_at` that is more than 60 seconds in the past raises `ValidationError`. A `scheduled_at` without `status="live"` also raises `ValidationError`.

```python
from datetime import datetime, timezone

send_at = datetime(2026, 12, 1, 9, 0, tzinfo=timezone.utc)
client.newsletters.update(7, status="live", scheduled_at=send_at)
client.newsletters.update(7, status="draft")  # sets a scheduled newsletter back to a draft
```

The other newsletter methods:

```python
client.newsletters.delete(7)  # drafts only
vip = {"category": "tags", "mode": "all", "values": ["vip"]}
count = client.newsletters.count_recipients([vip])
result = client.newsletters.send_test(7)  # sends to the email address of the token user
print(result.sent_to)
newsletter = client.newsletters.pick_winner(7, "b")  # the newsletter must be in "ab_testing"
variables = client.newsletters.variables(7)
print(variables.detected_variables, variables.content_variables)
# replace_variables() replaces all defaults.
variables = client.newsletters.replace_variables(7, {"first_name": "reader"})
```

A filter is a dict in the format of the BYOMailer dashboard. It has `category`, `values` and, for some categories, `mode`, `operator` or `field`.

### Sequences

```python
page = client.sequences.list(status="live")
for sequence in client.sequences.iter(search="Welcome"):
    ...
sequence = client.sequences.get(2)  # includes the steps, the filters and the content variables
print(sequence.contacts_count, sequence.completed_count, sequence.active_count)
stats = client.sequences.stats(2)
print(stats.stats.contacts, stats.mail_metrics.open_rate)
step = client.sequences.step(2, 11)
step_stats = client.sequences.step_stats(2, 11)
not_customer = {"category": "tags", "mode": "none", "values": ["customer"]}
step = client.sequences.replace_step_filters(2, 11, [not_customer])
variables = client.sequences.variables(2)
variables = client.sequences.replace_variables(2, {"first_name": "friend"})
```

`list()` and `iter()` return `SequenceSummary` objects. A summary has the counts but no steps, filters or content variables. `get()` returns a `Sequence` with all fields. `active_count` is the number of contacts that did not complete the sequence. The `status` filter accepts `"draft"`, `"live"` or `"paused"`.

A contact who does not match the filters of a step skips only that step. An empty list removes the filters.

Export the mails of a step as CSV text:

```python
csv_text = client.sequences.export_step_mails(2, 11, status="opened", direction="desc")
with open("step-11.csv", "w", encoding="utf-8") as file:
    file.write(csv_text)
```

### Blocks

A block is a piece of HTML that you can put in a newsletter or a step.

```python
blocks = client.blocks.list()  # all blocks. No pages.
block = client.blocks.get(6)
block = client.blocks.create("footer", "<p>See you next week</p>")  # name: a-z, 0-9 and _
block = client.blocks.update(6, name="footer", html_content="<p>Bye</p>")  # replaces both fields
client.blocks.delete(6)
```

### Email templates

```python
page = client.email_templates.list(archived=False)
for template in client.email_templates.iter(is_default=True):
    ...
template = client.email_templates.get(4)
template = client.email_templates.default()  # NotFoundError when no template is the default
```

### Email identities

```python
page = client.email_identities.list(identity_status="verified")
for identity in client.email_identities.iter():
    print(identity.email, identity.domain, identity.identity_status)
identity = client.email_identities.get(1)
```

### Email logs

The email logs record each call to Amazon SES and each notification from it.

```python
page = client.email_logs.list(status="failed", operation="SendEmail", recipient="example.com")
for log in client.email_logs.iter(recipient="ana@example.com"):
    print(log.logged_at, log.status, log.error)
log = client.email_logs.get(9)
```

### Projects

```python
page = client.projects.list()
for project in client.projects.iter():
    ...
project = client.projects.get(1)
project = client.projects.create("Launch")
project = client.projects.rename(1, "Relaunch")
client.projects.delete(1)
```

### Webhook endpoints

Only the token of an admin user can manage webhook endpoints. Other tokens get `AuthorizationError` (403).

```python
endpoint = client.webhook_endpoints.create(
    "https://app.example.com/hooks/byomailer",
    ["contact.subscribed", "contact.unsubscribed"],
    description="CRM sync",
)
print(endpoint.secret)  # keep it now. The instance shows it only one time.

page = client.webhook_endpoints.list()
for endpoint in client.webhook_endpoints.iter():
    ...
endpoint = client.webhook_endpoints.get(12)
endpoint = client.webhook_endpoints.update(12, active=False, description="Paused")
client.webhook_endpoints.delete(12)

page = client.webhook_endpoints.deliveries(12)
for delivery in client.webhook_endpoints.iter_deliveries(12):
    print(delivery.event_type, delivery.status, delivery.response_status)

endpoint = client.webhook_endpoints.rotate_secret(12)  # the old secret stops at once
delivery = client.webhook_endpoints.send_test(12)  # queues a webhook.test delivery
```

The URL must be a public `https` URL. To change the URL or the events, delete the endpoint and create a new one.

The `repr()` of an endpoint never shows the secret.

## Pagination

Most list endpoints use cursor pagination. `list()` returns one `Page`. `iter()` walks all pages.

```python
page = client.contacts.list(per_page=100)
print(len(page), page.next_cursor, page.prev_cursor)
for contact in page:
    ...

next_page = client.contacts.list(per_page=100, cursor=page.next_cursor)

for contact in client.contacts.iter(per_page=100):  # gets one page at a time
    ...
```

- `per_page` is 1 to 100. The default is 25. A value outside this range raises `ValueError`.
- `iter()` gets the next page only when the loop needs it.
- `tags.list()`, `blocks.list()` and `topics.list()` return a plain list with all items. These endpoints have no pages.

## Webhook verification

BYOMailer signs each webhook delivery with the secret of the endpoint. Verify each delivery before you use it.

> **WARNING:** The endpoint secret is a secret. Verify webhooks only on your server. Do not send the secret to a browser.

```python
from byomailer import WebhookVerificationError, verify_webhook

try:
    event = verify_webhook(raw_body, headers, secret)
except WebhookVerificationError as error:
    print(error.reason)  # "signature", "timestamp" or "payload"
    raise

if event.type == "contact.unsubscribed":
    print(event.payload["contact"]["email"], event.delivery_id)
```

1. Give the raw request body, byte for byte. Do not parse the JSON and encode it again. The app escapes Unicode as `\uXXXX`, so a new encoding gives other bytes.
2. Give the request headers. The header names are not case-sensitive.
3. Give the full secret, with its `whsec_` prefix.

`verify_webhook()` returns a `WebhookEvent`:

| Field | Description |
|---|---|
| `type` | The event type: `event` of the payload, or the `X-Byomailer-Event` header. |
| `payload` | The decoded JSON body, as a `dict`. |
| `timestamp` | The Unix time when the instance signed the delivery. |
| `delivery_id` | The `X-Byomailer-Delivery` header (a UUID). `None` when the header is missing or empty. |

Use `delivery_id` to ignore a delivery that you received before. An older instance does not send the delivery header. Then the verification passes and `delivery_id` is `None`.

When the delivery is not valid, `verify_webhook()` raises `WebhookVerificationError`. Its `reason` is:

| `reason` | Cause |
|---|---|
| `"signature"` | The `X-Byomailer-Signature` header is missing, or the signature does not match. |
| `"timestamp"` | The `X-Byomailer-Timestamp` header is missing, is not a Unix time, or is more than 300 seconds before or after the current time. |
| `"payload"` | The signature is valid, but the body is not a JSON object. |

The checks run in this order: the signature header, the timestamp header, the signature, the tolerance and the body. The client changes the signature header to lowercase, then compares it in constant time. The JS, PHP and Ruby SDKs give the same fields and the same reasons.

To change the tolerance, give `tolerance` in seconds. In a test, give `now` as the current Unix time:

```python
event = verify_webhook(raw_body, headers, secret, tolerance=600)
event = verify_webhook(raw_body, headers, secret, now=1763460030)
```

To make a signed delivery in your own tests, use `sign()`:

```python
from byomailer.webhooks import sign

headers = {
    "X-Byomailer-Timestamp": "1763460000",
    "X-Byomailer-Signature": sign("1763460000", body, "whsec_test"),
}
```

### Events

| Event | Payload fields after `event` and `occurred_at` |
|---|---|
| `contact.subscribed` | `contact` |
| `contact.unsubscribed` | `contact` |
| `contact.resubscribed` | `contact` |
| `newsletter.sent` | `newsletter`: `id`, `uuid`, `title`, `sent_at` |
| `sequence_step.sent` | `contact`, `sequence`: `id`, `name`, `sequence_step`: `id` |
| `sequence.completed` | `contact`, `sequence`: `id`, `name` |
| `webhook.test` | `message` |

`contact` has `id`, `uuid`, `email`, `name` and the custom attributes of the contact. For an A/B newsletter, `newsletter.sent` arrives one time, when the instance picks the winner. The app can add new events. Make your code accept an event type that it does not know.

Each delivery also has the headers `X-Byomailer-Event` (the event type) and `X-Byomailer-Delivery` (a UUID for the delivery). The app can send a delivery again after a failure. Use `X-Byomailer-Delivery` to find a delivery that you received before.

## Errors

All errors come from `BYOMailerError`:

```text
BYOMailerError
├── APIConnectionError        the client did not get a response
│   └── APITimeoutError       the request took more time than the timeout
├── APIError                  the instance sent an error status
│   ├── AuthenticationError   401: the token is missing or not valid
│   ├── AuthorizationError    403: the token cannot do this action
│   ├── NotFoundError         404
│   ├── ValidationError       422: .errors has the field errors
│   ├── RateLimitError        429: .retry_after has the seconds to wait
│   └── ServerError           5xx
└── WebhookVerificationError  .reason is "signature", "timestamp" or "payload"
```

Each `APIError` has `status_code`, `message`, `body` and `headers`. Another status, for example 400 or a 3xx redirect, raises `APIError`.

`APIConnectionError` has `request_sent`. It is `False` when the instance did not receive the request.

```python
from byomailer import RateLimitError, ValidationError

try:
    client.contacts.add(3, "not-an-email")
except ValidationError as error:
    for field, messages in error.errors.items():
        print(field, messages)
except RateLimitError as error:
    print("Wait", error.retry_after, "seconds")
```

An argument that breaks a rule before the request, for example `per_page=500`, raises `ValueError`.

## Retries

The client retries a failed request two times by default. The timeout of one attempt is 30 seconds. The wait before each retry grows exponentially (0.5, 1, 2 ... seconds, 8 seconds maximum) and has random jitter. The JS, PHP and Ruby SDKs use the same values and the same rule.

| Failure | Idempotent operation | Other operation |
|---|---|---|
| 429 | Retry | Retry |
| 5xx | Retry | No retry |
| DNS failure, refused connection, connect timeout | Retry | Retry. The instance did not get the request. |
| Read timeout or reset after the send | Retry | No retry |
| Other 4xx | No retry | No retry |

These operations are idempotent:

- Each GET and each DELETE.
- `newsletters.count_recipients()`, because it only reads.
- `contacts.update()`, `contacts.unsubscribe()` and `contacts.subscribe()`.
- `lists.rename()`, `tags.rename()`, `projects.rename()`, `topics.update()`, `blocks.update()` and `webhook_endpoints.update()`.
- `newsletters.replace_variables()`, `sequences.replace_variables()` and `sequences.replace_step_filters()`.

The other writes are not idempotent. For example, a repeat of `contacts.add()` changes `created` from `True` to `False`. `newsletters.update()` with `status="live"` can start the send, and a repeat then gets a 422.

- The client retries a 429 for each operation, because the rate limiter refuses the request before the app does the action.
- If a response has a `Retry-After` header, the client waits for that time.
- If `Retry-After` is more than 60 seconds, the client does not wait. It raises `RateLimitError` at once.
- Set `max_retries=0` to stop all retries.

Three endpoints have a rate limit:

| Method | Limit |
|---|---|
| `newsletters.count_recipients()` | 30 a minute for each user |
| `newsletters.send_test()` | 5 a minute for each user |
| `webhook_endpoints.send_test()` | 10 a minute for each client |

## Django and FastAPI

The package has no framework code. The examples below show how to connect it.

### Django

Put the settings in `settings.py`:

```python
# settings.py
BYOMAILER_URL = env("BYOMAILER_URL")
BYOMAILER_TOKEN = env("BYOMAILER_TOKEN")
BYOMAILER_WEBHOOK_SECRET = env("BYOMAILER_WEBHOOK_SECRET")
```

Make one client for the project, for example in `newsletter/byomailer.py`:

```python
from django.conf import settings
from byomailer import BYOMailer

client = BYOMailer(settings.BYOMAILER_URL, settings.BYOMAILER_TOKEN)
```

Add a contact after a user signs up. `transaction.on_commit()` sends the request only after the database saves the user:

```python
from django.db import transaction

from newsletter.byomailer import client


def subscribe(user) -> None:
    transaction.on_commit(lambda: client.contacts.add(3, user.email, name=user.get_full_name()))
```

Receive webhooks in a view. BYOMailer does not send a CSRF token, so the view must be `csrf_exempt`:

```python
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from byomailer import WebhookVerificationError, verify_webhook


@csrf_exempt
@require_POST
def byomailer_webhook(request: HttpRequest) -> HttpResponse:
    try:
        event = verify_webhook(request.body, request.headers, settings.BYOMAILER_WEBHOOK_SECRET)
    except WebhookVerificationError:
        return HttpResponseBadRequest()

    if event.type == "contact.unsubscribed":
        mark_unsubscribed(event.payload["contact"]["email"])
    return HttpResponse(status=204)
```

`request.body` is the raw body and `request.headers` is not case-sensitive.

### FastAPI

Make one client when the application starts. Then give it to each route with dependency injection:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from byomailer import BYOMailer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.byomailer = BYOMailer()  # reads BYOMAILER_URL and BYOMAILER_TOKEN
    yield


app = FastAPI(lifespan=lifespan)


def get_byomailer(request: Request) -> BYOMailer:
    return request.app.state.byomailer


Mailer = Annotated[BYOMailer, Depends(get_byomailer)]


@app.post("/signup")
def signup(email: str, mailer: Mailer) -> dict[str, bool]:
    contact = mailer.contacts.add(3, email)
    return {"created": contact.created}
```

The client is synchronous. Declare a route that calls it with `def`, not `async def`. FastAPI then runs the route in a thread pool, and the event loop does not stop. In an `async def` route, use `await run_in_threadpool(mailer.contacts.add, 3, email)` from `fastapi.concurrency`.

In a test, replace the dependency with `app.dependency_overrides[get_byomailer]`.

Receive webhooks in a route. Read the raw body with `await request.body()`:

```python
import os

from fastapi import HTTPException, Request, Response
from byomailer import WebhookVerificationError, verify_webhook

WEBHOOK_SECRET = os.environ["BYOMAILER_WEBHOOK_SECRET"]


@app.post("/hooks/byomailer", status_code=204)
async def byomailer_webhook(request: Request) -> Response:
    try:
        event = verify_webhook(await request.body(), request.headers, WEBHOOK_SECRET)
    except WebhookVerificationError as error:
        raise HTTPException(status_code=400, detail=error.reason) from error

    if event.type == "contact.unsubscribed":
        await mark_unsubscribed(event.payload["contact"]["email"])
    return Response(status_code=204)
```

Do not declare the body as a Pydantic model in this route. FastAPI then parses the JSON, and the raw bytes are not available.

## Supported Python versions

The package supports Python 3.10, 3.11, 3.12, 3.13 and 3.14. CI runs the tests, the lint and the type check on each version.

The package has full type hints and a `py.typed` file. `mypy --strict` passes on the package.

## License

MIT. Read [LICENSE](LICENSE).

## Development

Read [CONTRIBUTING.md](CONTRIBUTING.md).
