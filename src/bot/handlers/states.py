from aiogram.fsm.state import State, StatesGroup


class ConfirmCategory(StatesGroup):
    waiting = State()


class NoteAction(StatesGroup):
    waiting_for_edit_text = State()
