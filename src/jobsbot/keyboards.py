from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from . import texts


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_VIEW_JOBS, callback_data="nav:jobs:0")],
        ]
    )


def jobs_pagination(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text=texts.BTN_PREV, callback_data=f"nav:jobs:{page - 1}")
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(text=texts.BTN_NEXT, callback_data=f"nav:jobs:{page + 1}")
        )
    rows: list[list[InlineKeyboardButton]] = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data="nav:start")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def job_card(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_APPLY, callback_data=f"job:apply:{job_id}")],
        ]
    )


def cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="apply:cancel")],
        ]
    )


def request_phone() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_SHARE_PHONE, request_contact=True)],
            [KeyboardButton(text=texts.BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data="apply:confirm"),
                InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="apply:cancel"),
            ]
        ]
    )
