# Changelog

All notable changes to this package are in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The package uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
