"""The campaign resources: newsletters, sequences, blocks and email templates."""

from __future__ import annotations

import builtins
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime
from typing import Any, Literal

from byomailer._resource import (
    DEFAULT_PER_PAGE,
    UNSET,
    Resource,
    Unset,
    given,
    many,
    not_none,
    one,
    page,
    page_params,
    paginate,
)
from byomailer.models import (
    Block,
    ContentVariables,
    EmailTemplate,
    Newsletter,
    Page,
    Sequence,
    SequenceStats,
    SequenceStep,
    SequenceStepStats,
    SequenceSummary,
    TestEmail,
)

Filter = Mapping[str, Any]
NewsletterStatus = Literal["draft", "scheduled", "queued", "ab_testing", "sent", "failed"]
SequenceStatus = Literal["draft", "live", "paused"]


class Newsletters(Resource):
    """Read, create, change and test newsletters."""

    def list(
        self,
        *,
        status: NewsletterStatus | None = None,
        search: str | None = None,
        project: int | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> Page[Newsletter]:
        """Return one page of newsletters, without their content fields."""
        params = {
            "status": status,
            "search": search,
            "project": project,
            **page_params(per_page, cursor),
        }
        return page(Newsletter, self._client._get("/newsletters", params))

    def iter(
        self,
        *,
        status: NewsletterStatus | None = None,
        search: str | None = None,
        project: int | None = None,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> Iterator[Newsletter]:
        return paginate(
            lambda cursor: self.list(
                status=status, search=search, project=project, per_page=per_page, cursor=cursor
            )
        )

    def get(self, newsletter_id: int) -> Newsletter:
        return one(Newsletter, self._client._get(f"/newsletters/{newsletter_id}"))

    def create(
        self,
        *,
        title: str | None = None,
        subject: str | None = None,
        preview_text: str | None = None,
        html_content: str | None = None,
        status: Literal["draft", "live"] | None = None,
        scheduled_at: datetime | str | None = None,
        email_identity_id: int | None = None,
        email_template_id: int | None = None,
        ab_test_enabled: bool | None = None,
        subject_b: str | None = None,
        preview_text_b: str | None = None,
        html_content_b: str | None = None,
        content_variables: Mapping[str, str | None] | None = None,
        filters: Iterable[Filter] | None = None,
        project_ids: Iterable[int] | None = None,
    ) -> Newsletter:
        """Create a newsletter. The default status is ``"draft"``.

        ``status="live"`` with ``scheduled_at`` schedules the newsletter. The
        instance sends it at once when ``scheduled_at`` is the current time. A
        time more than 60 seconds in the past raises ``ValidationError``.
        """
        body = not_none(
            title=title,
            subject=subject,
            preview_text=preview_text,
            html_content=html_content,
            status=status,
            scheduled_at=scheduled_at,
            email_identity_id=email_identity_id,
            email_template_id=email_template_id,
            ab_test_enabled=ab_test_enabled,
            subject_b=subject_b,
            preview_text_b=preview_text_b,
            html_content_b=html_content_b,
            content_variables=content_variables,
            filters=filters,
            project_ids=project_ids,
        )
        return one(Newsletter, self._client._post("/newsletters", body))

    def update(
        self,
        newsletter_id: int,
        *,
        title: str | Unset | None = UNSET,
        subject: str | Unset | None = UNSET,
        preview_text: str | Unset | None = UNSET,
        html_content: str | Unset | None = UNSET,
        status: Literal["draft", "live"] | Unset = UNSET,
        scheduled_at: datetime | str | Unset | None = UNSET,
        email_identity_id: int | Unset | None = UNSET,
        email_template_id: int | Unset | None = UNSET,
        ab_test_enabled: bool | Unset = UNSET,
        subject_b: str | Unset | None = UNSET,
        preview_text_b: str | Unset | None = UNSET,
        html_content_b: str | Unset | None = UNSET,
        content_variables: Mapping[str, str | None] | Unset | None = UNSET,
        filters: Iterable[Filter] | Unset = UNSET,
        project_ids: Iterable[int] | Unset = UNSET,
    ) -> Newsletter:
        """Change a draft or a scheduled newsletter. Only the given fields change.

        ``status="live"`` with ``scheduled_at`` schedules the newsletter.
        ``status="draft"`` takes a scheduled newsletter back to a draft.
        """
        body = given(
            title=title,
            subject=subject,
            preview_text=preview_text,
            html_content=html_content,
            status=status,
            scheduled_at=scheduled_at,
            email_identity_id=email_identity_id,
            email_template_id=email_template_id,
            ab_test_enabled=ab_test_enabled,
            subject_b=subject_b,
            preview_text_b=preview_text_b,
            html_content_b=html_content_b,
            content_variables=content_variables,
            filters=filters,
            project_ids=project_ids,
        )
        if not body:
            raise ValueError("Give at least one field to change.")
        return one(Newsletter, self._client._patch(f"/newsletters/{newsletter_id}", body))

    def delete(self, newsletter_id: int) -> None:
        """Delete a draft newsletter."""
        self._client._delete(f"/newsletters/{newsletter_id}")

    def count_recipients(self, filters: Iterable[Filter] | None = None) -> int:
        """Return the number of contacts that match the filters. Nothing is saved.

        The instance allows 30 of these requests a minute.
        """
        body = {"filters": builtins.list(filters or [])}
        result = self._client._post("/newsletters/contacts/preview", body)
        return int(result["count"])

    def send_test(self, newsletter_id: int) -> TestEmail:
        """Send the newsletter to the email address of the token user.

        The instance allows 5 of these requests a minute.
        """
        result = self._client._post(f"/newsletters/{newsletter_id}/test-mail")
        return TestEmail.from_dict(result)

    def pick_winner(self, newsletter_id: int, variant: Literal["a", "b"]) -> Newsletter:
        """Pick the winner of an A/B test. The newsletter must have the status ``ab_testing``."""
        body = {"winner_variant": variant}
        return one(Newsletter, self._client._post(f"/newsletters/{newsletter_id}/ab-winner", body))

    def variables(self, newsletter_id: int) -> ContentVariables:
        """Return the content variables and their default values."""
        return one(ContentVariables, self._client._get(f"/newsletters/{newsletter_id}/variables"))

    def replace_variables(
        self, newsletter_id: int, variables: Mapping[str, str | None]
    ) -> ContentVariables:
        """Replace all default values of the variables of a draft or scheduled newsletter."""
        body = {"content_variables": dict(variables)}
        result = self._client._patch(f"/newsletters/{newsletter_id}/variables", body)
        return one(ContentVariables, result)


class Sequences(Resource):
    """Read sequences, their steps and their statistics."""

    def list(
        self,
        *,
        status: SequenceStatus | None = None,
        search: str | None = None,
        project: int | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> Page[SequenceSummary]:
        """Return one page of sequences, as summaries without steps."""
        params = {
            "status": status,
            "search": search,
            "project": project,
            **page_params(per_page, cursor),
        }
        return page(SequenceSummary, self._client._get("/sequences", params))

    def iter(
        self,
        *,
        status: SequenceStatus | None = None,
        search: str | None = None,
        project: int | None = None,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> Iterator[SequenceSummary]:
        return paginate(
            lambda cursor: self.list(
                status=status, search=search, project=project, per_page=per_page, cursor=cursor
            )
        )

    def get(self, sequence_id: int) -> Sequence:
        """Return one sequence with its steps."""
        return one(Sequence, self._client._get(f"/sequences/{sequence_id}"))

    def stats(self, sequence_id: int) -> SequenceStats:
        return one(SequenceStats, self._client._get(f"/sequences/{sequence_id}/stats"))

    def step(self, sequence_id: int, step_id: int) -> SequenceStep:
        return one(SequenceStep, self._client._get(f"/sequences/{sequence_id}/steps/{step_id}"))

    def step_stats(self, sequence_id: int, step_id: int) -> SequenceStepStats:
        path = f"/sequences/{sequence_id}/steps/{step_id}/stats"
        return one(SequenceStepStats, self._client._get(path))

    def replace_step_filters(
        self, sequence_id: int, step_id: int, filters: Iterable[Filter]
    ) -> SequenceStep:
        """Replace the filters of a step. A contact who does not match skips this step.

        An empty list removes all filters.
        """
        path = f"/sequences/{sequence_id}/steps/{step_id}/filters"
        body = {"filters": builtins.list(filters)}
        return one(SequenceStep, self._client._patch(path, body))

    def variables(self, sequence_id: int) -> ContentVariables:
        """Return the content variables and their default values."""
        return one(ContentVariables, self._client._get(f"/sequences/{sequence_id}/variables"))

    def replace_variables(
        self, sequence_id: int, variables: Mapping[str, str | None]
    ) -> ContentVariables:
        """Replace all default values of the content variables of the sequence."""
        body = {"content_variables": dict(variables)}
        result = self._client._patch(f"/sequences/{sequence_id}/variables", body)
        return one(ContentVariables, result)

    def export_step_mails(
        self,
        sequence_id: int,
        step_id: int,
        *,
        contact_id: int | None = None,
        status: str | None = None,
        filter: str | None = None,
        search: str | None = None,
        sent_after: datetime | str | None = None,
        sent_before: datetime | str | None = None,
        sort: str | None = None,
        direction: Literal["asc", "desc"] | None = None,
    ) -> str:
        """Return the mails of a step as CSV text, with a header row."""
        path = f"/sequences/{sequence_id}/steps/{step_id}/contact-mails/export"
        params = {
            "contact_id": contact_id,
            "status": status,
            "filter": filter,
            "search": search,
            "sent_after": sent_after,
            "sent_before": sent_before,
            "sort": sort,
            "direction": direction,
        }
        return self._client._request("GET", path, params=params).body.decode("utf-8")


class Blocks(Resource):
    """Read, create, change and delete blocks of reusable HTML."""

    def list(self) -> builtins.list[Block]:
        """Return all blocks. This endpoint has no pages."""
        return many(Block, self._client._get("/blocks"))

    def get(self, block_id: int) -> Block:
        return one(Block, self._client._get(f"/blocks/{block_id}"))

    def create(self, name: str, html_content: str) -> Block:
        """Create a block. ``name`` has only lowercase letters, digits and ``_``."""
        body = {"name": name, "html_content": html_content}
        return one(Block, self._client._post("/blocks", body))

    def update(self, block_id: int, *, name: str, html_content: str) -> Block:
        """Replace the name and the HTML of a block."""
        body = {"name": name, "html_content": html_content}
        return one(Block, self._client._patch(f"/blocks/{block_id}", body))

    def delete(self, block_id: int) -> None:
        self._client._delete(f"/blocks/{block_id}")


class EmailTemplates(Resource):
    """Read email templates."""

    def list(
        self,
        *,
        archived: bool | None = None,
        is_default: bool | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> Page[EmailTemplate]:
        """Return one page of templates. ``archived=True`` returns only archived templates."""
        params = {"archived": archived, "is_default": is_default, **page_params(per_page, cursor)}
        return page(EmailTemplate, self._client._get("/email-templates", params))

    def iter(
        self,
        *,
        archived: bool | None = None,
        is_default: bool | None = None,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> Iterator[EmailTemplate]:
        return paginate(
            lambda cursor: self.list(
                archived=archived, is_default=is_default, per_page=per_page, cursor=cursor
            )
        )

    def get(self, template_id: int) -> EmailTemplate:
        return one(EmailTemplate, self._client._get(f"/email-templates/{template_id}"))

    def default(self) -> EmailTemplate:
        """Return the default template. Raise ``NotFoundError`` when no template is the default."""
        return one(EmailTemplate, self._client._get("/email-templates/default"))
