# BYOMailer Python SDK: update 0.2.0 report

## Pull request

https://github.com/amedina068/byomailer-python/pull/1 (branch `update/0.2.0` to `main`, not merged)

## Changes

1. **`contacts.subscribe(contact_id)`.** New method. It calls `POST /contacts/{contactId}/subscribe` and returns the `Contact`. A refusal raises `ValidationError`. If the contact unsubscribed through an email link, `error.errors` has the field `contact`. If the address is blacklisted, `error.errors` has the field `email`.
2. **`contacts.update()`.** The docstring and the README say that an update never changes the subscription. The README caution about an update that undoes an admin unsubscribe is removed.
3. **`contacts.add()`.** The docstring and the README say that the call subscribes again a contact that an admin or the API unsubscribed. An unsubscribe that the contact made stays. On a list with opt-in, only a contact that is new on the list gets the opt-in email.
4. **PUT contact.** No change was necessary. The SDK uses `PATCH`. The repository had no note that PUT returns 422.
5. **PATCH `operationId`.** No change was necessary. The SDK, its tests and its docs do not use operation IDs.
6. **Sequences.**
   - New model `SequenceSummary` for `sequences.list()` and `sequences.iter()`. `sequences.get()` returns `Sequence`, with `steps`, `filters` and `content_variables`.
   - `steps_count`, `contacts_count`, `completed_count` and `active_count` are required `int` fields in both models.
   - The `status` filter was already `Literal["draft", "live", "paused"]`.
7. **Step mail export.** No change was necessary. Version 0.1.0 did not have the `current_only` argument.
8. **Cursor lists.** No code change was necessary. The helper reads only `data`, `meta.next_cursor` and `meta.prev_cursor`. A new test shows that the helper ignores `links`.
9. **Webhooks.** The README says that `newsletter.sent` arrives one time for an A/B newsletter, when the instance picks the winner. The signature code did not change. All vectors pass.

Other changes:

- The package version is `0.2.0`.
- `CHANGELOG.md` has a `0.2.0 - Unreleased` section.

## Tests

- `pytest`: 205 passed, 3 skipped (the integration suite, because `BYOMAILER_TEST_URL` and `BYOMAILER_TEST_TOKEN` are not set). The result is the same on Python 3.13 and 3.10.
- New tests: the `contacts.subscribe` operation, the two 422 cases of `subscribe()`, the `SequenceSummary` type from `list()` and `iter()`, the required counts of `Sequence`, and the pagination test for `links`.
- `ruff format --check`: pass. `ruff check`: pass. `mypy --strict`: pass on Python 3.13 and 3.10.
- `uv build` makes `byomailer-0.2.0-py3-none-any.whl` and `byomailer-0.2.0.tar.gz`.
- CI on the pull request: all checks pass (Python 3.10 to 3.14, and the package build).

## Open points

1. **Spec and source do not agree on `subscribe`.** The spec of `POST /contacts/{contactId}/subscribe` shows no 422 response. `ContactSubscribeController` raises 422 with the field `contact` or `email`. The SDK follows the source.
2. **Breaking change.** `sequences.list()` and `sequences.iter()` return `SequenceSummary`, not `Sequence`. Code that reads `steps`, `filters` or `content_variables` from a list item must call `sequences.get()`. The version is 0.x, so a minor release can break the API.
3. **Retries for `subscribe()`.** The endpoint is a POST, so the client does not retry it after a 5xx or a read timeout. The source makes the operation idempotent: a second call does not change a subscribed contact. Must the client retry `subscribe()` like a GET?
4. **`project_ids`.** The spec marks `project_ids` as not required, because the resources use `whenLoaded`. Both sequence endpoints load the projects, so the field is always in the response. The SDK keeps `project_ids` optional.
5. **Integration suite.** The live integration suite did not run, because no test instance was set.
