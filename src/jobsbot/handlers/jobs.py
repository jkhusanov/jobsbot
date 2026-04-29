from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from .. import keyboards, texts
from ..services.jobs_api import Job, JobsApi, JobsApiError

log = logging.getLogger(__name__)
router = Router(name="jobs")

PAGE_SIZE = 5
# Telegram caps sendMessage at 4096 chars. Leave a tiny margin so the
# whole rendered card (template + title + meta + description) always fits.
MAX_MESSAGE_CHARS = 4000


@router.callback_query(F.data.startswith("nav:jobs:"))
async def handle_browse_jobs(callback: CallbackQuery, jobs_api: JobsApi) -> None:
    if callback.data is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    try:
        page = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        page = 0
    try:
        jobs = await jobs_api.fetch()
    except JobsApiError:
        log.exception("jobs api fetch failed")
        await callback.message.answer(texts.JOBS_FETCH_ERROR)
        await callback.answer()
        return

    if not jobs:
        await callback.message.answer(
            texts.NO_JOBS, reply_markup=keyboards.main_menu()
        )
        await callback.answer()
        return

    total_pages = max(1, (len(jobs) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    for job in jobs[start:end]:
        await callback.message.answer(
            render_job_card(job),
            parse_mode="HTML",
            reply_markup=keyboards.job_card(job.id),
            disable_web_page_preview=True,
        )

    await callback.message.answer(
        texts.JOBS_PAGE_INDICATOR.format(page=page + 1, total=total_pages),
        reply_markup=keyboards.jobs_pagination(page, total_pages),
    )
    await callback.answer()


def render_job_card(job: Job) -> str:
    meta_parts: list[str] = []
    if job.company:
        meta_parts.append(f"🏢 {escape(job.company)}")
    if job.location:
        meta_parts.append(f"📍 {escape(job.location)}")
    if job.employment_type:
        meta_parts.append(f"🕒 {escape(job.employment_type)}")
    if job.salary:
        meta_parts.append(f"💰 {escape(job.salary)}")
    meta = "\n".join(meta_parts)
    title = escape(job.title)
    description = escape((job.description or "").strip())

    # Budget the description so the whole rendered card stays under
    # Telegram's hard 4096-char sendMessage limit.
    overhead = len(texts.JOB_CARD.format(title=title, meta=meta, description=""))
    budget = max(0, MAX_MESSAGE_CHARS - overhead)
    if len(description) > budget:
        description = description[: max(0, budget - 3)] + "..."
    return texts.JOB_CARD.format(title=title, meta=meta, description=description)
