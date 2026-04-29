from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import keyboards, texts

log = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    user = message.from_user
    log.info(
        texts.LOG_BOOTSTRAP.format(
            chat_id=message.chat.id,
            username=(user.username if user else None) or "",
        ),
        extra={"chat_id": message.chat.id},
    )
    await state.clear()
    await message.answer(
        texts.WELCOME,
        reply_markup=keyboards.main_menu(),
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(texts.HELP)


@router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer(texts.HELP, reply_markup=keyboards.remove_reply_keyboard())
        return
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.remove_reply_keyboard())
    await message.answer(texts.WELCOME, reply_markup=keyboards.main_menu())


@router.callback_query(F.data == "nav:start")
async def handle_back_to_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.WELCOME, reply_markup=keyboards.main_menu()
        )
    await callback.answer()
