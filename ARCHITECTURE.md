# Architecture

This document captures the *why* behind jobsbot's design — the things that aren't obvious from reading the code. For *what* the project does and *how* to run it, see [`README.md`](./README.md).

---

## Overview

A Telegram bot that lets users browse open jobs (fetched on demand from an HTTP endpoint) and apply by submitting their **name, Uzbek phone number, email, and CV file**. Submitted applications are forwarded to an administrator's Telegram chat. The bot is deployed to a Linux VPS as a long-running service.

Audience: end users (job seekers). Interface is **Uzbek only** (Latin script).

---

## Goals & non-goals

**Goals**

- Fetch jobs from an HTTP endpoint and present them as a browsable list.
- Collect applications via a guided multi-step conversation (FSM).
- Forward each completed application (text fields + CV document) to an admin chat.
- Robust, simple, free to operate (no third-party file storage, no paid APIs).
- Production-ready on a Linux VPS via `systemd` (Docker optional).

**Non-goals**

- No admin web UI or admin-side bot commands.
- No multi-language support.
- No payments, scheduling, or notifications back to applicants.
- No CV parsing or scoring.

---

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Mature ecosystem; the `aiogram`/`aiohttp`/`aiosqlite` triad is async-native. |
| Bot framework | **aiogram 3.x** | Modern async framework with clean FSM; the de-facto standard for Python Telegram bots. |
| Storage | **SQLite** via **aiosqlite** | Zero-ops; fits a single-VPS deployment; easy backups. |
| Config | **pydantic-settings** + `.env` | Type-safe; fails fast on missing or malformed values. |
| Validation | **email-validator** + custom regex | Email handling is full of edge cases — don't reinvent. |
| Logging | stdlib `logging` → stdout (JSON) | systemd / journalctl captures it; easy to ship to a log aggregator later. |
| Process | **systemd** (primary), **Docker** (optional) | Standard Linux VPS pattern. |

---

## CV file handling — `file_id` passthrough

When the user uploads a CV document, Telegram returns a `file_id`. The bot stores that id alongside the application metadata, then forwards the document to the admin chat by calling `bot.send_document(chat_id=ADMIN_CHAT_ID, document=file_id, ...)`. **The bot never downloads or stores the CV.**

Why this matters:

- **Free** — no S3 / GCS bill, no disk pressure on the VPS.
- **Secure** — files never touch the server's disk; nothing to exfiltrate from a compromised VPS.
- **Simple** — fewer moving parts and no upload pipeline.
- **Resilient** — `file_id`s are stable per bot, so the admin can re-fetch a document later via the same bot.

Caveats:

- A `file_id` is bound to the bot that received it. Regenerating the bot token invalidates old `file_id`s — but documents already delivered live in the admin's chat history, so applications already delivered are unaffected.
- Telegram retains files indefinitely *in practice*, but this isn't a contractual SLA. If long-term archival becomes a hard requirement, swap in S3; the data model already has `cv_file_unique_id` which makes deduplication straightforward.

---

## Why `ADMIN_CHAT_ID` (not `@username`)

Telegram bots **cannot** DM a user by `@username` — they need the user's numeric `chat_id`, which only becomes available after that user has sent the bot at least one message. So the bot uses `ADMIN_CHAT_ID` (numeric) and provides a bootstrap procedure (see [`README.md`](./README.md)). `ADMIN_USERNAME` is kept as a display-only field.

The same `ADMIN_CHAT_ID` works for a private group or channel (negative ids starting with `-100…`) — handy if multiple admins need access to applications.

---

## Long polling, not webhooks

The bot uses Telegram's `getUpdates` long-polling endpoint:

- **No inbound HTTP surface** to harden — the firewall stays trivially small.
- **No TLS** to manage on the bot's side.
- **Performance is fine** at this scale (thousands of users, single instance).

If you ever need horizontal scaling or sub-second update latency, switch to webhooks — but be ready to operate the HTTPS endpoint yourself.

---

## Security & privacy

- `BOT_TOKEN` lives only in `.env` (mode `0600`, owned by the `jobsbot` user).
- All outbound HTTP uses HTTPS; certificate verification is on by default and **never disabled**.
- All user-supplied strings are HTML-escaped before being sent with `parse_mode="HTML"` (admin chat, job cards, confirmation summary). This prevents Telegram-formatting injection.
- All SQL is parameterised. The schema is the only static SQL string.
- Bot is restricted to private chats — group additions are silently ignored. The apply FSM collects PII (name, phone, email, CV) that must never be exposed in shared chat history.
- Per-user throttling middleware caps each account at 30 events / 60 seconds.
- CV documents are validated by both extension AND mime type to prevent spoofing (e.g., `cv.html` with mime `application/pdf`).
- Phone numbers from Telegram's contact-share button are checked against `contact.user_id == from_user.id` so applications can't be submitted with someone else's contact card.
- Job applications are rate-limited per `(user, job_id, day)` to a small number per day; unknown job ids are refused so an attacker can't bypass the limit by minting fake ids.
- Jobs API responses are capped at 5 MB to prevent memory exhaustion from a misbehaving upstream.
- No PII is logged at `INFO` level — only identifiers (`app_id`, `job_id`, `chat_id`).

For deployer-side privacy obligations (you are the data controller), see [`SECURITY.md`](./SECURITY.md).

---

## Edge cases

| Scenario | Behaviour |
|---|---|
| Jobs API unreachable | User-friendly Uzbek error; log ERROR; user can retry. |
| Jobs API returns zero jobs | "Hozircha vakansiyalar yo'q" ("no vacancies right now"). |
| User taps "Apply" on a job id no longer in the API | Refused — minimum surface for fake-id abuse. |
| User sends a CV that's too large or wrong type | Re-prompt with the allowed formats / size limit; FSM state preserved. |
| Admin chat blocks the bot | Application is stored (`status=pending_admin_send`); retried every 60 s up to 5 times; after that, status → `failed`. |
| Bot restarts mid-FSM | aiogram's in-memory FSM storage drops in-progress flows. Acceptable trade-off for v1; switching to `RedisStorage` is a one-line change. |
| User sends `/start` mid-FSM | The current FSM state is cleared; user returns to the main menu. |

---

## Decisions log

The "why" behind choices that aren't obvious from the code.

| Decision | Reason |
|---|---|
| Python + aiogram 3 | The mainstream stack for Python Telegram bots — async-native, clean FSM API, well-maintained. |
| SQLite over Postgres | Single VPS, single instance, expected load < 1k applications/day. Postgres would add operational burden for no benefit. The data model is simple enough to migrate later if needed. |
| Long polling over webhooks | No inbound TLS/firewall to manage, simpler ops. Performance is fine at this scale. |
| `file_id` passthrough for CVs | Free, secure, simple. Files never touch the bot's disk. See above. |
| Admin delivery via numeric `chat_id`, not `@username` | Bots cannot DM by username — Telegram requires a `chat_id` available only after first contact. |
| In-memory FSM storage | Simplicity. Acceptable loss model for v1 (rare restarts, users can redo the short flow). Redis swap is a one-line change. |
| All Uzbek strings in `texts.py` | A future translation pass becomes a single-file diff. |
| Both extension AND mime required for CVs | Either-or accepted obvious spoofs (e.g., `cv.html` with PDF mime). |
| Private-chat-only filter | The apply FSM collects PII; group exposure of those prompts would be a serious leak. |
