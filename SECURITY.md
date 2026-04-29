# Security Policy

## Reporting a vulnerability

If you believe you've found a security issue in this codebase, please **do not open a public GitHub issue**. Instead, report it privately:

1. Use GitHub's [private security advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) feature on this repository, or
2. Email the maintainer directly with the details.

Please include:

- A clear description of the issue and its impact.
- Steps to reproduce, or a proof-of-concept.
- Affected commit / version, if known.
- Whether you intend to disclose publicly, and on what timeline.

You can expect an acknowledgement within a reasonable time. Fixes are released as soon as practical; coordinated disclosure is appreciated for high-severity issues.

## Scope

In scope:

- Code in this repository (the Telegram bot itself).
- Default configuration shipped here (`deploy/jobsbot.service`, `Dockerfile`, `docker-compose.yml`).

Out of scope:

- Bugs in third-party dependencies (please report those upstream).
- Issues caused by user-modified deployments.
- Social-engineering against deployers, applicants, or admins.
- Vulnerabilities that require an attacker to already control the server, the bot token, or the admin Telegram account.

## Deployer responsibility (important)

This software collects personal data — applicants' names, phone numbers, email addresses, and CV files. **If you deploy this bot, you are the data controller** for the personal data collected through your deployment, including obligations under any applicable laws (e.g., the Republic of Uzbekistan's _Law on Personal Data_, GDPR if you process EU residents' data, and any other regional privacy law).

Maintainers and contributors of this project:

- Provide the software "AS IS" under the [Apache License 2.0](./LICENSE).
- Are not responsible for how you deploy, configure, secure, or operate this bot.
- Are not responsible for handling, storage, retention, or deletion of personal data submitted to your deployment.
- Are not responsible for compliance with local laws in your jurisdiction.

You should, at minimum:

- Keep `BOT_TOKEN`, `ADMIN_CHAT_ID`, and the SQLite database protected (file permissions, access controls).
- Define a retention policy for stored applications and delete them when no longer needed.
- Inform applicants of how their data is handled (a privacy notice is your responsibility).
- Restrict admin access to those with a legitimate business need.
- Apply security updates to this bot and to the host operating system promptly.

## Known limitations

- Telegram itself stores CV documents on its CDN; the bot uses `file_id` passthrough and never writes CVs to local disk. CV retention is therefore subject to Telegram's policies in addition to yours.
- Long-polling is used; no inbound HTTP surface is exposed by default. If you change to webhooks, securing the HTTPS endpoint is your responsibility.
