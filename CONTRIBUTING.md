# Contributing

Thanks for your interest in improving jobsbot. Pull requests, issues, and security reports are all welcome.

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # leave BOT_TOKEN/JOBS_API_URL placeholders if you only run tests
pytest
ruff check .
```

The project targets **Python 3.11+** and uses [aiogram 3](https://docs.aiogram.dev/en/latest/) for the Telegram bot framework, [aiosqlite](https://aiosqlite.omnilib.dev/) for storage, and [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for configuration.

## Running the bot locally

You'll need:

1. A bot token from [@BotFather](https://t.me/BotFather).
2. A jobs API endpoint that returns a JSON array of `{id, title, ...}` objects. The bot logs and gracefully skips items missing `id` or `title`; all other fields are optional.
3. Your numeric `chat_id` for `ADMIN_CHAT_ID` — see [`README.md`](./README.md) for the bootstrap procedure.

Then:

```bash
python -m jobsbot
```

## Pull requests

- Keep changes focused. Small, well-scoped PRs are easier to review than large ones.
- **Add or update tests** for any behaviour change. Aim to keep the existing suite passing on every commit (`pytest -q`).
- Run the linter (`ruff check .`) and fix anything it flags.
- Avoid adding features beyond what the task requires. The code style favours minimalism — see [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the project's scope and the decisions log.
- For non-trivial changes, please open an issue first to discuss the approach.

## Reporting bugs

Open an issue on the project's issue tracker with:

- What you expected to happen.
- What actually happened.
- Steps to reproduce, plus the relevant log output (with secrets redacted).
- Versions: Python, aiogram, OS, deployment mode (systemd / Docker).

## Reporting security vulnerabilities

**Do not open a public issue for security problems.** See [`SECURITY.md`](./SECURITY.md) for the private reporting process.

## Licensing of contributions

By submitting a pull request, you agree that your contribution is licensed under the [Apache License 2.0](./LICENSE), the same as the rest of the project. This is the standard contribution model described in §5 of the Apache License — no additional CLA paperwork required.

## Coding conventions

- Type hints on all public functions; `mypy --strict` is configured but not yet enforced in CI — try to keep new code clean.
- All user-facing strings live in [`src/jobsbot/texts.py`](./src/jobsbot/texts.py) so future translations are a single-file diff.
- All SQL is parameterised — never interpolate user data into a query.
- All user-supplied content sent with `parse_mode="HTML"` must go through `html.escape()` first.
- Avoid logging PII at `INFO` level; restrict to identifiers (`app_id`, `job_id`, `chat_id`).
