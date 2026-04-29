from aiogram.fsm.state import State, StatesGroup


class ApplyStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_cv = State()
    waiting_for_confirmation = State()
