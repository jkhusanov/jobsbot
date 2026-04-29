# jobsbot

Telegram bot that fetches open jobs from an HTTP endpoint and lets users apply (name, Uzbek phone, email, CV). Submitted applications are forwarded to an admin Telegram chat. Uzbek-language UI.

---

> ## DISCLAIMER — READ BEFORE USING
>
> **This project is vibecoded** — built quickly with heavy AI assistance and lightly hand-reviewed. It has not been independently audited or formally verified.
>
> It is provided **AS IS** under the [Apache License 2.0](./LICENSE), **with no warranty of any kind**, express or implied. The author accepts **no responsibility and no liability** for any damages, data loss, privacy incidents, regulatory violations, downtime, financial loss, or any other harm arising from your use of, deployment of, or inability to use this software.
>
> **You run it entirely at your own risk.**
>
> If you deploy this bot, **you** become the data controller for the personal data it collects (applicant names, phone numbers, email addresses, CV files). Compliance with applicable laws — including but not limited to data-protection, employment, and privacy regulations in your jurisdiction — is **your responsibility**, not the author's. See [`SECURITY.md`](./SECURITY.md) for more.

---

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the design rationale and decisions log.

---

## Quickstart (development)

Requires Python 3.11+.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env — paste your BOT_TOKEN and JOBS_API_URL.
# Leave ADMIN_CHAT_ID=0 for the bootstrap below.

python -m jobsbot
```

### Bootstrap the admin chat id

A Telegram bot cannot DM a user by username — it needs a numeric `chat_id`. To obtain one:

1. Start the bot with `ADMIN_CHAT_ID=0`.
2. From the admin's Telegram account, send `/start` to the bot.
3. The bot logs a line like:
   ```
   [BOOTSTRAP] Received /start from chat_id=123456789 username=hr_uzbot
   ```
4. Copy the `chat_id` into `.env` as `ADMIN_CHAT_ID`, restart the bot.

For a private group/channel: add the bot as a member/admin, post any message in it, look at the bot logs for the chat id (a group id is negative, a channel/supergroup id starts with `-100…`). Use that as `ADMIN_CHAT_ID`.

Until `ADMIN_CHAT_ID` is set to a non-zero value, applications are stored in SQLite but admin delivery is skipped (and logged as ERROR).

---

## Run tests

```bash
pytest
ruff check .
mypy src
```

---

## Deploy on a Linux VPS (systemd)

```bash
# As root:
useradd -r -s /usr/sbin/nologin jobsbot
mkdir -p /opt/jobsbot /var/lib/jobsbot
chown -R jobsbot:jobsbot /var/lib/jobsbot

# As you:
git clone <your repo url> /opt/jobsbot
cd /opt/jobsbot
python3.11 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
chmod 600 .env
# edit /opt/jobsbot/.env with real values, then:

cp deploy/jobsbot.service /etc/systemd/system/jobsbot.service
systemctl daemon-reload
systemctl enable --now jobsbot
journalctl -u jobsbot -f
```

The service uses long-polling, so no inbound port / TLS / webhook setup is required.

### Update procedure

```bash
cd /opt/jobsbot
git pull
.venv/bin/pip install -e .
systemctl restart jobsbot
```

The SQLite file at `DATABASE_PATH` (default `/var/lib/jobsbot/bot.db` if you set it that way in `.env`) survives restarts.

---

## Deploy with Docker (alternative)

```bash
cp .env.example .env  # fill it in
docker compose up -d
docker compose logs -f
```

---

## Project layout

```
src/jobsbot/        # bot package
  bot.py            # entrypoint
  config.py         # pydantic settings
  texts.py          # all Uzbek strings (translation-ready)
  states.py         # FSM states
  validation.py     # phone / email / name / file checks
  keyboards.py      # inline + reply markup builders
  middlewares.py    # per-user throttling
  handlers/         # routers
  services/         # storage, jobs API, admin delivery
deploy/             # systemd unit
tests/              # pytest suite
```
