# Changelog

All notable changes to this package are in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The package uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - Unreleased

This release adopts the API changes of BYOMailer app pull requests #114 and #115.

### Added

- `contacts.subscribe()` subscribes again a contact that an admin or the API unsubscribed. It calls `POST /contacts/{contactId}/subscribe`. A contact that unsubscribed through an email link raises `ValidationError` with the field `contact`. A blacklisted address raises `ValidationError` with the field `email`.
- The model `SequenceSummary`, for the items of `sequences.list()` and `sequences.iter()`.

### Changed

- `sequences.list()` returns `Page[SequenceSummary]`, and `sequences.iter()` yields `SequenceSummary`. `sequences.get()` still returns `Sequence`. If your code reads `steps`, `filters` or `content_variables` from a list item, call `sequences.get()`.
- `Sequence` fields `steps_count`, `contacts_count`, `completed_count`, `active_count`, `filters` and `content_variables` are always set. They are not optional now.
- The docs of `contacts.update()` say that an update never changes the subscription. The instance no longer subscribes a contact again on `PUT` or `PATCH`.
- The docs of `contacts.add()` say that it subscribes again a contact that an admin unsubscribed. On a list with opt-in, the instance sends the opt-in email only when the contact is new on the list.
- The webhook docs say that `newsletter.sent` arrives one time for an A/B newsletter, when the instance picks the winner.

### Removed

- The README caution that said that `contacts.update()` subscribes again a contact that an admin unsubscribed.

## [0.1.0] - Unreleased

### Added

- The client `BYOMailer`, with the settings `base_url`, `token`, `timeout`, `max_retries` and `transport`. `BYOMAILER_URL` and `BYOMAILER_TOKEN` are the defaults.
- The default transport `UrllibTransport`. It uses only the standard library and does not follow redirects.
- Contacts: `list()`, `iter()`, `get()`, `add()`, `update()`, `unsubscribe()` and `remove_from_list()`. `add()` sets `Contact.created` to `True` when the instance made a new contact.
- Custom attributes of a contact as one `attributes` map. The client sends its keys at the top level of the request body.
- Lists: `list()`, `iter()`, `create()`, `rename()` and `delete()`.
- Topics: `list()`, `create()`, `update()` and `delete()`.
- Tags: `list()`, `create()`, `rename()` and `delete()`.
- Newsletters: `list()`, `iter()`, `get()`, `create()`, `update()`, `delete()`, `count_recipients()`, `send_test()`, `pick_winner()`, `variables()` and `replace_variables()`.
- Sequences: `list()`, `iter()`, `get()`, `stats()`, `step()`, `step_stats()`, `replace_step_filters()`, `variables()`, `replace_variables()` and `export_step_mails()`.
- Blocks: `list()`, `get()`, `create()`, `update()` and `delete()`.
- Email templates: `list()`, `iter()`, `get()` and `default()`.
- Email identities: `list()`, `iter()` and `get()`.
- Email logs: `list()`, `iter()` and `get()`.
- Projects: `list()`, `iter()`, `get()`, `create()`, `rename()` and `delete()`.
- Webhook endpoints: `list()`, `iter()`, `get()`, `create()`, `update()`, `delete()`, `deliveries()`, `iter_deliveries()`, `rotate_secret()` and `test()`.
- Cursor pagination with `Page`, and `iter()` methods that get one page at a time.
- Frozen dataclass response models with a `raw` field.
- `verify_webhook()` and `sign()` for the webhook signatures, with a tolerance of 300 seconds that the caller can change.
- An error class for each failure, under `BYOMailerError`.
- Retries for 429, 5xx and connection errors, with exponential backoff, jitter and `Retry-After`.
- Type hints and a `py.typed` file.
