from __future__ import annotations

import asyncio
import logging
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from .. import texts
from .storage import Application, Storage

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
RETRY_INTERVAL_SECONDS = 60


class AdminNotifier:
    def __init__(self, bot: Bot, admin_chat_id: int, storage: Storage) -> None:
        self._bot = bot
        self._chat_id = admin_chat_id
        self._storage = storage

    @property
    def configured(self) -> bool:
        return self._chat_id != 0

    async def deliver(self, app: Application) -> bool:
        if not self.configured:
            log.error(
                "admin_chat_id not configured; cannot deliver application",
                extra={"app_id": app.id},
            )
            return False
        try:
            if app.tg_username:
                tg_link = f"@{escape(app.tg_username)}"
            else:
                tg_link = (
                    f'<a href="tg://user?id={app.tg_user_id}">user</a>'
                )
            summary = texts.ADMIN_NEW_APPLICATION.format(
                job_title=escape(app.job_title),
                job_id=escape(app.job_id),
                name=escape(app.full_name),
                phone=escape(app.phone),
                email=escape(app.email),
                tg_link=tg_link,
                tg_user_id=app.tg_user_id,
                created_at=escape(app.created_at),
            )
            await self._bot.send_message(
                self._chat_id,
                summary,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            caption = texts.ADMIN_CV_CAPTION.format(
                name=app.full_name, job_id=app.job_id
            )
            await self._bot.send_document(
                self._chat_id, document=app.cv_file_id, caption=caption
            )
            await self._storage.mark_sent(app.id)
            log.info("application delivered to admin", extra={"app_id": app.id})
            return True
        except TelegramAPIError as e:
            log.warning(
                "admin delivery failed",
                extra={"app_id": app.id, "error": str(e)},
            )
            terminal = (app.delivery_attempts + 1) >= MAX_ATTEMPTS
            await self._storage.record_delivery_failure(
                app.id, str(e), terminal=terminal
            )
            if terminal:
                log.error(
                    "application permanently failed delivery",
                    extra={"app_id": app.id},
                )
            return False

    async def retry_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(RETRY_INTERVAL_SECONDS)
                if not self.configured:
                    continue
                pending = await self._storage.list_pending()
                for app in pending:
                    if app.delivery_attempts >= MAX_ATTEMPTS:
                        continue
                    await self.deliver(app)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("retry_loop iteration failed")
