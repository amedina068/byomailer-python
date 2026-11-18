"""The audience resources: contacts, lists, topics and tags."""

from __future__ import annotations

import builtins
import dataclasses
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

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
from byomailer.models import Contact, MailList, Page, Tag, Topic

# These body fields of a contact request are not custom attributes.
_CONTACT_FIELDS = frozenset({"email", "name", "tags", "remove_tags"})


class Contacts(Resource):
    """Read, add, change and unsubscribe contacts."""

    def list(
        self,
        *,
        lists: Iterable[int] | None = None,
        tags: Iterable[int] | None = None,
        topics: Iterable[int] | None = None,
        search: str | None = None,
        include_unsubscribed: bool | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> Page[Contact]:
        """Return one page of contacts.

        ``lists``, ``tags`` and ``topics`` are IDs. A contact matches when it
        has one of the IDs. The list leaves out unsubscribed contacts, unless
        ``include_unsubscribed`` is ``True``.
        """
        params = {
            "lists": lists,
            "tags": tags,
            "topics": topics,
            "search": search,
            "include_unsubscribed": include_unsubscribed,
            **page_params(per_page, cursor),
        }
        return page(Contact, self._client._get("/contacts", params))

    def iter(
        self,
        *,
        lists: Iterable[int] | None = None,
        tags: Iterable[int] | None = None,
        topics: Iterable[int] | None = None,
        search: str | None = None,
        include_unsubscribed: bool | None = None,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> Iterator[Contact]:
        """Iterate over all contacts that match. The client gets one page at a time."""
        # A generator gives its items only one time. Each page needs them again.
        filters = {"lists": _ids(lists), "tags": _ids(tags), "topics": _ids(topics)}
        return paginate(
            lambda cursor: self.list(
                **filters,
                search=search,
                include_unsubscribed=include_unsubscribed,
                per_page=per_page,
                cursor=cursor,
            )
        )

    def get(self, contact_id: int) -> Contact:
        return one(Contact, self._client._get(f"/contacts/{contact_id}"))

    def add(
        self,
        list_id: int,
        email: str,
        *,
        name: str | Unset | None = UNSET,
        tags: Iterable[str] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Contact:
        """Add a contact to a list. Make the contact first, if it does not exist.

        ``tags`` are tag names. The instance makes a tag that does not exist.
        ``attributes`` are custom attributes. The result has ``created=True``
        when the instance made a new contact.
        """
        body = {
            **_attributes(attributes),
            **given(email=email, name=name),
            **not_none(tags=tags),
        }
        response = self._client._request("POST", f"/lists/{list_id}/contacts", body=body)
        contact = one(Contact, response.json())
        return dataclasses.replace(contact, created=response.status_code == 201)

    def update(
        self,
        contact_id: int,
        *,
        email: str | Unset = UNSET,
        name: str | Unset | None = UNSET,
        tags: Iterable[str] | None = None,
        remove_tags: Iterable[str] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Contact:
        """Change a contact. Only the given fields change.

        ``tags`` adds tags and ``remove_tags`` removes tags, by name.
        ``attributes`` sets custom attributes and keeps the other attributes.
        A ``None`` value stores ``null``.
        """
        body = {
            **_attributes(attributes),
            **given(email=email, name=name),
            **not_none(tags=tags, remove_tags=remove_tags),
        }
        return one(Contact, self._client._patch(f"/contacts/{contact_id}", body))

    def unsubscribe(self, contact_id: int) -> Contact:
        """Unsubscribe a contact from all email. The contact stays on its lists."""
        return one(Contact, self._client._post(f"/contacts/{contact_id}/unsubscribe"))

    def remove_from_list(self, contact_id: int, list_id: int) -> Contact:
        """Remove a contact from one list. Return the contact with its other lists."""
        response = self._client._request("DELETE", f"/lists/{list_id}/contacts/{contact_id}")
        return one(Contact, response.json())


class Lists(Resource):
    """Read, create, rename and delete mailing lists."""

    def list(self, *, per_page: int | None = None, cursor: str | None = None) -> Page[MailList]:
        return page(MailList, self._client._get("/lists", page_params(per_page, cursor)))

    def iter(self, *, per_page: int = DEFAULT_PER_PAGE) -> Iterator[MailList]:
        return paginate(lambda cursor: self.list(per_page=per_page, cursor=cursor))

    def create(self, name: str) -> MailList:
        return one(MailList, self._client._post("/lists", {"name": name}))

    def rename(self, list_id: int, name: str) -> MailList:
        return one(MailList, self._client._patch(f"/lists/{list_id}", {"name": name}))

    def delete(self, list_id: int) -> None:
        self._client._delete(f"/lists/{list_id}")


class Topics(Resource):
    """Read and change the topics of a list. A contact can unsubscribe from one topic."""

    def list(self, list_id: int) -> builtins.list[Topic]:
        """Return all topics of a list. This endpoint has no pages."""
        return many(Topic, self._client._get(f"/lists/{list_id}/topics"))

    def create(self, list_id: int, name: str, *, description: str | None = None) -> Topic:
        body = {"name": name, "description": description}
        return one(Topic, self._client._post(f"/lists/{list_id}/topics", body))

    def update(
        self, list_id: int, topic_id: int, *, name: str, description: str | None = None
    ) -> Topic:
        """Replace the name and the description. ``None`` clears the description."""
        body = {"name": name, "description": description}
        return one(Topic, self._client._patch(f"/lists/{list_id}/topics/{topic_id}", body))

    def delete(self, list_id: int, topic_id: int) -> None:
        self._client._delete(f"/lists/{list_id}/topics/{topic_id}")


class Tags(Resource):
    """Read, create, rename and delete tags."""

    def list(self) -> builtins.list[Tag]:
        """Return all tags. This endpoint has no pages."""
        return many(Tag, self._client._get("/tags"))

    def create(self, name: str) -> Tag:
        return one(Tag, self._client._post("/tags", {"name": name}))

    def rename(self, tag_id: int, name: str) -> Tag:
        return one(Tag, self._client._patch(f"/tags/{tag_id}", {"name": name}))

    def delete(self, tag_id: int) -> None:
        self._client._delete(f"/tags/{tag_id}")


def _ids(values: Iterable[int] | None) -> builtins.list[int] | None:
    return builtins.list(values) if values is not None else None


def _attributes(attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return the custom attributes, which the API reads at the top level of the body."""
    attributes = attributes or {}
    reserved = _CONTACT_FIELDS.intersection(attributes)
    if reserved:
        raise ValueError(
            f"{sorted(reserved)} are contact fields, not custom attributes. Give them as arguments."
        )
    return dict(attributes)
