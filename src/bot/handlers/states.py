from aiogram.fsm.state import State, StatesGroup


class ConfirmCategory(StatesGroup):
    waiting = State()
