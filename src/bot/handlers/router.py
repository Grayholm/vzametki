import logging

from aiogram import F, Router, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.handlers.handlers import (
    CONFIRM_CATEGORIES,
    classify_message,
    process_message,
    user_message_from_error,
)
from src.bot.handlers.states import ConfirmCategory


logger = logging.getLogger(__name__)


notes_router = Router()

CATEGORY_LABELS = {
    "Note": "Заметка",
    "Idea": "Идея",
    "Noise": "Шум",
    "Search": "Поиск",
    "ListAll": "Все заметки",
    "GetById": "Заметка по ID",
    "Trash": "Мусор",
}


def _category_keyboard(suggested: str) -> InlineKeyboardMarkup:
    label = CATEGORY_LABELS.get(suggested, suggested)
    change_buttons = [
        InlineKeyboardButton(
            text=CATEGORY_LABELS[key],
            callback_data=f"cat:{key}",
        )
        for key in ("Note", "Idea", "Noise", "Search")
        if key != suggested
    ]
    rows = [
        [InlineKeyboardButton(text=f"✓ {label}", callback_data="cat:confirm")],
    ]
    if change_buttons:
        rows.append(change_buttons)
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="cat:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _reply_with_process_result(message: types.Message, response: dict) -> None:
    action = response.get("action")

    if action == "created_note":
        note = response.get("note", {})
        await message.answer(
            f"Заметка сохранена!\n\n"
            f"Категория: {CATEGORY_LABELS.get(response.get('category'), response.get('category'))}\n"
            f"ID: {note.get('note_id')}\n"
            f"Заголовок: {note.get('title')}\n"
            f"Резюме: {note.get('summary')}"
        )
        return

    if action == "search":
        results = response.get("search", {}).get("results", [])
        if not results:
            await message.answer("Ничего не найдено по вашему запросу.")
            return
        text = "Результаты поиска:\n"
        for item in results[:5]:
            payload = item.get("payload", {})
            text += (
                f"\nID: {item.get('id')}\n"
                f"Заголовок: {payload.get('title')}\n"
                f"Резюме: {payload.get('summary')}\n"
            )
        await message.answer(text)
        return
    
    if action == "get_by_id":
        note = response.get("note")
        if not note:
            await message.answer("Заметка не найдена.")
            return
        await message.answer(
            f"Заметка ID {note.get('id')}:\n\n"
            f"Категория: {CATEGORY_LABELS.get(note.get('category'), note.get('category'))}\n"
            f"Заголовок: {note.get('title')}\n"
            f"Резюме: {note.get('summary')}\n"
            f"Полный текст: {note.get('full_text')}"
        )
        return
    
    if action == "list_all":
        notes = response.get("notes", [])
        if not notes:
            await message.answer("У вас нет сохраненных заметок.")
            return
        text = "Ваши заметки:\n"
        for note in notes[:5]:
            payload = note.get("payload", {})
            text += (
                f"\nID: {note.get('id')}\n"
                f"Категория: {CATEGORY_LABELS.get(payload.get('category'), payload.get('category'))}\n"
                f"Заголовок: {payload.get('title')}\n"
                f"Резюме: {payload.get('summary')}\n"
            )
        await message.answer(text)
        return

    await message.answer(
        response.get("message", "Сообщение не похоже на заметку или запрос поиска.")
    )


@notes_router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет, {message.from_user.full_name}! "
        "Отправь мне текст, и я помогу сохранить его как заметку или найти похожие заметки."
    )


@notes_router.message(ConfirmCategory.waiting)
async def handle_waiting_category(message: types.Message):
    await message.answer("Выбери категорию кнопками под предыдущим сообщением или нажми /start.")


@notes_router.message(StateFilter(None))
async def handle_message(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправь текст заметки.")
        return

    user_id = message.from_user.id
    text = message.text

    try:
        category = await classify_message(user_id, text)
    except Exception as exc:
        logger.exception("Classification failed for user %s", user_id)
        await message.answer(user_message_from_error(exc))
        return

    category_label = category.get("category")
    note_id = category.get("note_id", None)

    if category_label in CONFIRM_CATEGORIES:
        await state.set_state(ConfirmCategory.waiting)
        await state.update_data(text=text, suggested_category=category_label)
        label = CATEGORY_LABELS.get(category_label, category_label)
        await message.answer(
            f"Похоже на: **{label}**\n\nПодтверди или выбери другую категорию:",
            reply_markup=_category_keyboard(category_label),
            parse_mode="Markdown",
        )
        return

    try:
        response = await process_message(user_id=user_id, text=text, category=category_label, note_id=note_id)
    except Exception as exc:
        logger.exception("Process failed for user %s", user_id)
        await message.answer(user_message_from_error(exc))
        return
    
    logger.info(">>>> DEBUG: Process response for user %s: %s. Action: %s", user_id, response, response.get("action"))

    await _reply_with_process_result(message, response)


@notes_router.callback_query(F.data.startswith("cat:"))
async def handle_category_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 1)[1]

    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("Отменено.")
        await callback.answer()
        return

    data = await state.get_data()
    text = data.get("text")
    if not text:
        await state.clear()
        await callback.answer("Сессия устарела. Отправь текст заново.", show_alert=True)
        return

    if action == "confirm":
        category_label = data.get("suggested_category")
    else:
        category_label = action

    user_id = callback.from_user.id
    await callback.message.edit_text("Обрабатываю…")
    await callback.answer()

    try:
        response = await process_message(user_id=user_id, text=text, category=category_label, note_id=None)
    except Exception as exc:
        await state.clear()
        logger.exception("Process failed (callback) for user %s", user_id)
        await callback.message.edit_text(user_message_from_error(exc))
        return

    await state.clear()
    await _reply_with_process_result(callback.message, response)
