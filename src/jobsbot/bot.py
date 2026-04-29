from __future__ import annotations

import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType

from .config import Settings, load_settings
from .handlers import apply as apply_handler
from .handlers import jobs as jobs_handler
from .handlers import start as start_handler
from .logging_setup import setup_logging
from .middlewares import ThrottlingMiddleware
from .services.admin_notify import AdminNotifier
from .services.jobs_api import JobsApi
from .services.storage import Storage

log = logging.getLogger(__name__)


async def run() -> None:
    settings: Settings = load_settings()
    setup_logging(settings.log_level)
    log.info(
        "starting jobsbot",
        extra={
            "admin_chat_id": settings.admin_chat_id,
            "admin_username": settings.admin_username,
            "jobs_api_url": settings.jobs_api_url,
        },
    )

    storage = Storage(settings.database_path)
    await storage.init()

    jobs_api = JobsApi(
        url=settings.jobs_api_url,
        auth_header=settings.jobs_api_auth_header,
        timeout_seconds=settings.jobs_api_timeout_seconds,
        cache_ttl_seconds=settings.jobs_cache_ttl_seconds,
    )

    bot = Bot(token=settings.bot_token)
    admin_notifier = AdminNotifier(bot, settings.admin_chat_id, storage)

    dp = Dispatcher()
    dp["settings"] = settings
    dp["jobs_api"] = jobs_api
    dp["storage"] = storage
    dp["admin_notifier"] = admin_notifier

    # Per-user throttle to absorb floods of messages or button taps.
    throttle = ThrottlingMiddleware(max_events=30, window_seconds=60.0)
    dp.message.middleware(throttle)
    dp.callback_query.middleware(throttle)

    # Restrict the bot to private chats. If someone adds the bot to a group,
    # all messages and inline-keyboard callbacks from that chat are dropped:
    # the apply FSM collects PII (name, phone, email, CV) that must never be
    # exposed in shared chat history.
    private_msg = F.chat.type == ChatType.PRIVATE
    private_cb = F.message.chat.type == ChatType.PRIVATE
    for r in (start_handler.router, jobs_handler.router, apply_handler.router):
        r.message.filter(private_msg)
        r.callback_query.filter(private_cb)

    dp.include_router(start_handler.router)
    dp.include_router(jobs_handler.router)
    dp.include_router(apply_handler.router)

    retry_task = asyncio.create_task(admin_notifier.retry_loop(), name="admin_retry")
    try:
        await dp.start_polling(bot, handle_signals=True)
    finally:
        retry_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await retry_task
        await bot.session.close()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(run())


if __name__ == "__main__":
    main()
