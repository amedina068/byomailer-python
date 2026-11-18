"""The base of each resource, and the helpers that the resources share."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Final, TypeVar

from byomailer.errors import BYOMailerError
from byomailer.models import M, Page

if TYPE_CHECKING:
    from byomailer._client import BYOMailer

T = TypeVar("T")

DEFAULT_PER_PAGE: Final = 25
MAX_PER_PAGE: Final = 100


class Unset:
    """The type of ``UNSET``: an argument that the caller did not give.

    An update method sends only the fields that the caller gives. ``None``
    is a real value, because it clears a field.
    """

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Final = Unset()


class Resource:
    def __init__(self, client: BYOMailer) -> None:
        self._client = client


def given(**fields: Any) -> dict[str, Any]:
    """Return the fields that are not ``UNSET``, with dates in ISO 8601."""
    return {name: _encode(value) for name, value in fields.items() if not isinstance(value, Unset)}


def not_none(**fields: Any) -> dict[str, Any]:
    """Return the fields that are not ``None``, with dates in ISO 8601."""
    return {name: _encode(value) for name, value in fields.items() if value is not None}


def _encode(value: Any) -> Any:
    """Make a value ready for JSON: a date, a mapping or another iterable."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return list(value)
    return value


def page_params(per_page: int | None, cursor: str | None) -> dict[str, Any]:
    if per_page is not None and not 1 <= per_page <= MAX_PER_PAGE:
        raise ValueError(f"per_page must be from 1 to {MAX_PER_PAGE}, not {per_page}")
    return not_none(per_page=per_page, cursor=cursor)


def one(model: type[M], body: Any) -> M:
    """Build one model from a ``{"data": {...}}`` body."""
    return model.from_dict(_object(_data(body)))


def many(model: type[M], body: Any) -> list[M]:
    """Build a list of models from a ``{"data": [...]}`` body."""
    items = _data(body)
    if not isinstance(items, list):
        raise BYOMailerError("The instance sent a response with no list in 'data'.")
    return [model.from_dict(_object(item)) for item in items]


def page(model: type[M], body: Any) -> Page[M]:
    """Build a page from a cursor-paginated body: ``data`` and ``meta``."""
    meta = body.get("meta") if isinstance(body, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    return Page(
        data=tuple(many(model, body)),
        next_cursor=meta.get("next_cursor"),
        prev_cursor=meta.get("prev_cursor"),
    )


def paginate(fetch: Callable[[str | None], Page[T]], cursor: str | None = None) -> Iterator[T]:
    """Yield each item of each page. Get the next page only when the caller needs it."""
    while True:
        current = fetch(cursor)
        yield from current
        if not current.next_cursor:
            return
        cursor = current.next_cursor


def _data(body: Any) -> Any:
    if not isinstance(body, dict) or "data" not in body:
        raise BYOMailerError(
            "The instance sent a response with no 'data' field. "
            "Make sure that base_url is the URL of a BYOMailer instance."
        )
    return body["data"]


def _object(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise BYOMailerError("The instance sent a response that is not a JSON object.")
    return value
