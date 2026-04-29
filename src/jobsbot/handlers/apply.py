from __future__ import annotations

import datetime as dt
import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import keyboards, texts
from ..config import Settings
from ..services.admin_notify import AdminNotifier
from ..services.jobs_api import JobsApi, JobsApiError
from ..services.storage import NewApplication, Storage
from ..states import ApplyStates
from ..validation import (
    validate_cv_document,
    validate_email_address,
    validate_name,
    validate_phone,
)

log = logging.getLogger(__name__)
router = Router(name="apply")

RATE_LIMIT_PER_DAY = 3


# --- Entry: user tapped "Apply" on a job card ---------------------------------


@router.callback_query(F.data.startswith("job:apply:"))
async def handle_apply_start(
    callback: CallbackQuery,
    state: FSMContext,
    jobs_api: JobsApi,
    storage: Storage,
) -> None:
    if (
        callback.data is None
        or callback.from_user is None
        or not isinstance(callback.message, Message)
    ):
        await callback.answer()
        return

    job_id = callback.data.split(":", 2)[-1]
    job = jobs_api.find_in_cache(job_id)
    if job is None:
        try:
            await jobs_api.fetch()
            job = jobs_api.find_in_cache(job_id)
        except JobsApiError:
            log.warning("could not refresh jobs to resolve title", exc_info=True)
    # Refuse unknown job ids — the callback_data is attacker-controlled, and
    # accepting arbitrary ids would let a user spam fake applications past
    # the per-job rate limit by minting a unique id each time.
    if job is None:
        await callback.message.answer(texts.JOB_NOT_AVAILABLE)
        await callback.answer()
        return
    job_title = job.title

    since = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
    recent = await storage.count_recent_for_user_and_job(
        callback.from_user.id, job_id, since
    )
    if recent >= RATE_LIMIT_PER_DAY:
        await callback.message.answer(texts.RATE_LIMITED)
        await callback.answer()
        return

    await state.clear()
    await state.update_data(job_id=job_id, job_title=job_title)
    await state.set_state(ApplyStates.waiting_for_name)
    await callback.message.answer(
        texts.ASK_NAME, reply_markup=keyboards.cancel_inline()
    )
    await callback.answer()


# --- Cancel from inline button ------------------------------------------------


@router.callback_query(F.data == "apply:cancel")
async def handle_apply_cancel_callback(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.CANCELLED, reply_markup=keyboards.remove_reply_keyboard()
        )
        await callback.message.answer(
            texts.WELCOME, reply_markup=keyboards.main_menu()
        )
    await callback.answer()


# --- Step 1: name -------------------------------------------------------------


@router.message(ApplyStates.waiting_for_name, F.text)
async def handle_name(message: Message, state: FSMContext) -> None:
    if message.text is None:
        return
    if message.text.strip() == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(
            texts.CANCELLED, reply_markup=keyboards.remove_reply_keyboard()
        )
        await message.answer(texts.WELCOME, reply_markup=keyboards.main_menu())
        return

    result = validate_name(message.text)
    if not result.ok or result.value is None:
        await message.answer(texts.INVALID_NAME)
        return

    await state.update_data(name=result.value)
    await state.set_state(ApplyStates.waiting_for_phone)
    await message.answer(texts.ASK_PHONE, reply_markup=keyboards.request_phone())


# --- Step 2: phone (contact button OR typed) ---------------------------------


@router.message(ApplyStates.waiting_for_phone, F.contact)
async def handle_phone_contact(message: Message, state: FSMContext) -> None:
    if message.contact is None or not message.contact.phone_number:
        return
    # Telegram lets users share *another* person's contact card; reject those
    # so applications are tied to the submitting account's own phone.
    if (
        message.from_user is None
        or message.contact.user_id != message.from_user.id
    ):
        await message.answer(texts.SHARED_CONTACT_REJECTED)
        return
    raw = message.contact.phone_number
    if not raw.startswith("+"):
        raw = "+" + raw
    result = validate_phone(raw)
    if not result.ok or result.value is None:
        await message.answer(texts.INVALID_PHONE)
        return
    await _accept_phone_and_ask_email(message, state, result.value)


@router.message(ApplyStates.waiting_for_phone, F.text)
async def handle_phone_text(message: Message, state: FSMContext) -> None:
    if message.text is None:
        return
    if message.text.strip() == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(
            texts.CANCELLED, reply_markup=keyboards.remove_reply_keyboard()
        )
        await message.answer(texts.WELCOME, reply_markup=keyboards.main_menu())
        return
    result = validate_phone(message.text)
    if not result.ok or result.value is None:
        await message.answer(texts.INVALID_PHONE)
        return
    await _accept_phone_and_ask_email(message, state, result.value)


async def _accept_phone_and_ask_email(
    message: Message, state: FSMContext, phone: str
) -> None:
    await state.update_data(phone=phone)
    await state.set_state(ApplyStates.waiting_for_email)
    # Drop the reply keyboard with a brief confirmation, then ask for email
    # with an inline cancel button.
    await message.answer(
        texts.PHONE_ACCEPTED, reply_markup=keyboards.remove_reply_keyboard()
    )
    await message.answer(texts.ASK_EMAIL, reply_markup=keyboards.cancel_inline())


# --- Step 3: email ------------------------------------------------------------


@router.message(ApplyStates.waiting_for_email, F.text)
async def handle_email(
    message: Message, state: FSMContext, settings: Settings
) -> None:
    if message.text is None:
        return
    if message.text.strip() == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(
            texts.CANCELLED, reply_markup=keyboards.remove_reply_keyboard()
        )
        await message.answer(texts.WELCOME, reply_markup=keyboards.main_menu())
        return
    result = validate_email_address(message.text)
    if not result.ok or result.value is None:
        await message.answer(texts.INVALID_EMAIL)
        return
    await state.update_data(email=result.value)
    await state.set_state(ApplyStates.waiting_for_cv)
    await message.answer(
        texts.ASK_CV.format(max_mb=settings.max_cv_size_mb),
        reply_markup=keyboards.cancel_inline(),
    )


# --- Step 4: CV ---------------------------------------------------------------


@router.message(ApplyStates.waiting_for_cv, F.document)
async def handle_cv(
    message: Message, state: FSMContext, settings: Settings
) -> None:
    if message.document is None:
        return
    doc = message.document
    result = validate_cv_document(
        mime_type=doc.mime_type,
        file_name=doc.file_name,
        size_bytes=doc.file_size,
        max_size_bytes=settings.max_cv_size_bytes,
    )
    if not result.ok:
        if result.error == "invalid_cv_size":
            await message.answer(
                texts.INVALID_CV_SIZE.format(max_mb=settings.max_cv_size_mb)
            )
        else:
            await message.answer(texts.INVALID_CV_TYPE)
        return

    cv_file_name = (doc.file_name or "")[:255] or None
    await state.update_data(
        cv_file_id=doc.file_id,
        cv_file_unique_id=doc.file_unique_id,
        cv_file_name=cv_file_name,
        cv_mime_type=doc.mime_type,
        cv_size_bytes=doc.file_size,
    )
    data = await state.get_data()
    summary = texts.CONFIRMATION_SUMMARY.format(
        job_title=escape(str(data.get("job_title", ""))),
        name=escape(str(data.get("name", ""))),
        phone=escape(str(data.get("phone", ""))),
        email=escape(str(data.get("email", ""))),
        cv_name=escape(cv_file_name or "CV"),
    )
    await state.set_state(ApplyStates.waiting_for_confirmation)
    await message.answer(
        f"{summary}\n\n{texts.ASK_CONFIRM}",
        parse_mode="HTML",
        reply_markup=keyboards.confirm(),
        disable_web_page_preview=True,
    )


@router.message(ApplyStates.waiting_for_cv)
async def handle_cv_wrong_type(message: Message) -> None:
    await message.answer(texts.NEED_DOCUMENT)


# --- Step 5: confirm ----------------------------------------------------------


@router.callback_query(
    ApplyStates.waiting_for_confirmation, F.data == "apply:confirm"
)
async def handle_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    storage: Storage,
    admin_notifier: AdminNotifier,
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    data = await state.get_data()
    new_app = NewApplication(
        job_id=str(data.get("job_id", "")),
        job_title=str(data.get("job_title", "")),
        tg_user_id=callback.from_user.id,
        tg_username=callback.from_user.username,
        full_name=str(data.get("name", "")),
        phone=str(data.get("phone", "")),
        email=str(data.get("email", "")),
        cv_file_id=str(data.get("cv_file_id", "")),
        cv_file_unique_id=str(data.get("cv_file_unique_id", "")),
        cv_file_name=data.get("cv_file_name"),
        cv_mime_type=data.get("cv_mime_type"),
        cv_size_bytes=data.get("cv_size_bytes"),
    )
    app_id = await storage.insert_application(new_app)
    log.info("application stored", extra={"app_id": app_id, "job_id": new_app.job_id})
    await state.clear()
    await callback.message.answer(
        texts.APPLICATION_RECEIVED, reply_markup=keyboards.main_menu()
    )
    await callback.answer()

    stored = await storage.get(app_id)
    if stored is not None:
        await admin_notifier.deliver(stored)
