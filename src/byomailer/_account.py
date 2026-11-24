"""The account resources: email identities, email logs, projects and webhook endpoints."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from byomailer._resource import (
    DEFAULT_PER_PAGE,
    UNSET,
    Resource,
    Unset,
    given,
    not_none,
    one,
    page,
    page_params,
    paginate,
)
from byomailer.models import (
    EmailIdentity,
    EmailLog,
    Page,
    Project,
    WebhookDelivery,
    WebhookEndpoint,
)


class EmailIdentities(Resource):
    """Read the sender identities of Amazon SES."""

    def list(
        self,
        *,
        identity_status: str | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> Page[EmailIdentity]:
        params = {"identity_status": identity_status, **page_params(per_page, cursor)}
        return page(EmailIdentity, self._client._get("/email-identities", params))

    def iter(
        self, *, identity_status: str | None = None, per_page: int = DEFAULT_PER_PAGE
    ) -> Iterator[EmailIdentity]:
        return paginate(
            lambda cursor: self.list(
                identity_status=identity_status, per_page=per_page, cursor=cursor
            )
        )

    def get(self, identity_id: int) -> EmailIdentity:
        return one(EmailIdentity, self._client._get(f"/email-identities/{identity_id}"))


class EmailLogs(Resource):
    """Read the log of the calls to Amazon SES and of its notifications."""

    def list(
        self,
        *,
        status: str | None = None,
        operation: str | None = None,
        recipient: str | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> Page[EmailLog]:
        """Return one page of logs, newest first. ``recipient`` matches part of the address."""
        params = {
            "status": status,
            "operation": operation,
            "recipient": recipient,
            **page_params(per_page, cursor),
        }
        return page(EmailLog, self._client._get("/email-logs", params))

    def iter(
        self,
        *,
        status: str | None = None,
        operation: str | None = None,
        recipient: str | None = None,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> Iterator[EmailLog]:
        return paginate(
            lambda cursor: self.list(
                status=status,
                operation=operation,
                recipient=recipient,
                per_page=per_page,
                cursor=cursor,
            )
        )

    def get(self, log_id: int) -> EmailLog:
        return one(EmailLog, self._client._get(f"/email-logs/{log_id}"))


class Projects(Resource):
    """Read, create, rename and delete projects."""

    def list(self, *, per_page: int | None = None, cursor: str | None = None) -> Page[Project]:
        return page(Project, self._client._get("/projects", page_params(per_page, cursor)))

    def iter(self, *, per_page: int = DEFAULT_PER_PAGE) -> Iterator[Project]:
        return paginate(lambda cursor: self.list(per_page=per_page, cursor=cursor))

    def get(self, project_id: int) -> Project:
        return one(Project, self._client._get(f"/projects/{project_id}"))

    def create(self, name: str) -> Project:
        return one(Project, self._client._post("/projects", {"name": name}))

    def rename(self, project_id: int, name: str) -> Project:
        path = f"/projects/{project_id}"
        return one(Project, self._client._patch(path, {"name": name}, idempotent=True))

    def delete(self, project_id: int) -> None:
        self._client._delete(f"/projects/{project_id}")


class WebhookEndpoints(Resource):
    """Manage webhook endpoints. Each method needs the token of an admin user."""

    def list(
        self, *, per_page: int | None = None, cursor: str | None = None
    ) -> Page[WebhookEndpoint]:
        params = page_params(per_page, cursor)
        return page(WebhookEndpoint, self._client._get("/webhook-endpoints", params))

    def iter(self, *, per_page: int = DEFAULT_PER_PAGE) -> Iterator[WebhookEndpoint]:
        return paginate(lambda cursor: self.list(per_page=per_page, cursor=cursor))

    def get(self, endpoint_id: int) -> WebhookEndpoint:
        return one(WebhookEndpoint, self._client._get(f"/webhook-endpoints/{endpoint_id}"))

    def create(
        self, url: str, events: Iterable[str], *, description: str | None = None
    ) -> WebhookEndpoint:
        """Create an endpoint. Keep ``secret`` from the result: the instance shows it only once.

        ``url`` must be a public ``https`` URL.
        """
        body = not_none(url=url, events=list(events), description=description)
        return one(WebhookEndpoint, self._client._post("/webhook-endpoints", body))

    def update(
        self,
        endpoint_id: int,
        *,
        active: bool | Unset = UNSET,
        description: str | Unset | None = UNSET,
    ) -> WebhookEndpoint:
        """Turn an endpoint on or off, or change its description.

        To change the URL or the events, delete the endpoint and create a new one.
        """
        body = given(active=active, description=description)
        if not body:
            raise ValueError("Give active, description or both.")
        path = f"/webhook-endpoints/{endpoint_id}"
        return one(WebhookEndpoint, self._client._patch(path, body, idempotent=True))

    def delete(self, endpoint_id: int) -> None:
        self._client._delete(f"/webhook-endpoints/{endpoint_id}")

    def deliveries(
        self, endpoint_id: int, *, per_page: int | None = None, cursor: str | None = None
    ) -> Page[WebhookDelivery]:
        """Return one page of the deliveries of an endpoint, newest first."""
        path = f"/webhook-endpoints/{endpoint_id}/deliveries"
        return page(WebhookDelivery, self._client._get(path, page_params(per_page, cursor)))

    def iter_deliveries(
        self, endpoint_id: int, *, per_page: int = DEFAULT_PER_PAGE
    ) -> Iterator[WebhookDelivery]:
        return paginate(
            lambda cursor: self.deliveries(endpoint_id, per_page=per_page, cursor=cursor)
        )

    def rotate_secret(self, endpoint_id: int) -> WebhookEndpoint:
        """Make a new secret. The old secret stops at once. Keep ``secret`` from the result."""
        path = f"/webhook-endpoints/{endpoint_id}/secret"
        return one(WebhookEndpoint, self._client._post(path))

    def send_test(self, endpoint_id: int) -> WebhookDelivery:
        """Queue a ``webhook.test`` delivery to the endpoint.

        The instance allows 10 of these requests a minute for each client.
        """
        path = f"/webhook-endpoints/{endpoint_id}/test"
        return one(WebhookDelivery, self._client._post(path))
