from __future__ import annotations

import logging
from typing import Any, cast

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

from src.handlers.handlers import (
    CONFIRM_CATEGORIES,
    classify_message,
    delete_message,
    process_message,
    update_message,
    user_message_from_error,
)
from src.handlers.states import ConfirmCategory, NoteAction


logger = logging.getLogger(__name__)

notes_router = Router()

CATEGORY_LABELS: dict[str, str] = {
    "Note": "Заметка",
    "Idea": "Идея",
    "Noise": "Шум",
    "Search": "Поиск",
    "ListAll": "Все заметки",
    "GetById": "Единая заметка",
    "Trash": "Мусор",
}


def _category_label(key: str | None) -> str:
    return CATEGORY_LABELS.get(key, key) if key else "Неизвестно"


def _category_keyboard(suggested: str) -> InlineKeyboardMarkup:
    label = _category_label(suggested)
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


async def _reply_with_process_result(message: Message, response: dict[str, Any]) -> None:
    action: str | None = response.get("action")  # type: ignore[assignment]

    if action == "created_note":
        note: dict[str, Any] = response.get("note", {})  # type: ignore[assignment]
        await message.answer(
            f"Заметка сохранена!\n\n"
            f"Категория: {_category_label(response.get('category'))}\n"
            f"ID: {note.get('note_id')}\n" # type: ignore[assignment]
            f"Заголовок: {note.get('title')}\n" # type: ignore[assignment]
            f"Резюме: {note.get('summary')}" # type: ignore[assignment]
        )
        return

    if action == "search":
        search_data: dict[str, Any] = response.get("search") or {}
        results: list[dict[str, Any]] = search_data.get("results", [])
        if not results:
            await message.answer("Ничего не найдено по вашему запросу.")
            return
        text = "Результаты поиска:\n"
        for item in results[:5]:
            payload: dict[str, Any] = item.get("payload", {})  # type: ignore[assignment]
            text += (
                f"\nID: {item.get('id')}\n"
                f"Заголовок: {payload.get('title')}\n"
                f"Резюме: {payload.get('summary')}\n"
            )
        await message.answer(text)
        return

    if action == "get_by_id":
        note: dict[str, Any] | None = response.get("note")  # type: ignore[assignment]
        if not note:
            await message.answer("Заметка не найдена.")
            return
        await message.answer(
            f"Заметка ID {note.get('id')}:\n\n"
            f"Категория: {_category_label(response.get('category'))}\n"
            f"Заголовок: {note.get('title')}\n"
            f"Резюме: {note.get('summary')}\n"
            f"Полный текст: {note.get('full_text')}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✏️ Редактировать",
                            callback_data=f"edit:{note.get('id')}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🗑 Удалить", callback_data=f"delete:{note.get('id')}"
                        )
                    ],
                ]
            ),
        )
        return

    if action == "list_all":
        notes: list[dict[str, Any]] = response.get("notes", [])  # type: ignore[assignment]
        if not notes:
            await message.answer("У вас нет сохраненных заметок.")
            return
        text = "Ваши заметки:\n"
        for note in notes[:5]:
            payload: dict[str, Any] = note.get("payload", {})  # type: ignore[assignment]
            text += (
                f"\nID: {note.get('id')}\n"
                f"Категория: {_category_label(payload.get('category'))}\n"
                f"Заголовок: {payload.get('title')}\n"
                f"Резюме: {payload.get('summary')}\n"
            )
        await message.answer(text)
        return

    await message.answer(
        response.get("message", "Сообщение не похоже на заметку или запрос поиска.")
    )


# === Helpers ===

def _get_user_id(user: User | None) -> int:
    return user.id if user else 0


def _get_user_name(user: User | None) -> str:
    return user.full_name if user else "пользователь"


# === Handlers ===

@notes_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    name = _get_user_name(message.from_user)
    await message.answer(
        f"Привет, {name}! "
        "Отправь мне текст, и я помогу сохранить его как заметку или найти похожие заметки."
    )


@notes_router.message(ConfirmCategory.waiting)
async def handle_waiting_category(message: Message) -> None:
    await message.answer(
        "Выбери категорию кнопками под предыдущим сообщением или нажми /start."
    )


@notes_router.message(StateFilter(None))
async def handle_message(message: Message, state: FSMContext) -> None:
    text = message.text
    if not text:
        await message.answer("Пожалуйста, отправь текст заметки.")
        return

    user_id = _get_user_id(message.from_user)
    if not user_id:
        await message.answer("Не удалось определить пользователя.")
        return

    try:
        category: dict[str, Any] = await classify_message(user_id, text)
    except Exception as exc:
        logger.exception("Classification failed for user %s", user_id)
        await message.answer(user_message_from_error(exc))
        return

    category_label: str | None = category.get("category")
    note_id: int | None = category.get("note_id", None)

    if category_label in CONFIRM_CATEGORIES:
        await state.set_state(ConfirmCategory.waiting)
        await state.update_data(text=text, suggested_category=category_label)
        await message.answer(
            f"Похоже на: **{_category_label(category_label)}**\n\n"
            f"Подтверди или выбери другую категорию:",
            reply_markup=_category_keyboard(category_label or "Note"),
            parse_mode="Markdown",
        )
        return

    try:
        response = await process_message(
            user_id=user_id, text=text, category=category_label, note_id=note_id
        )
    except Exception as exc:
        logger.exception("Process failed for user %s", user_id)
        await message.answer(user_message_from_error(exc))
        return

    logger.info(
        ">>>> DEBUG: Process response for user %s: %s. Action: %s",
        user_id,
        response,
        response.get("action"),
    )

    await _reply_with_process_result(message, response)


@notes_router.callback_query(F.data.startswith("cat:"))
async def handle_category_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data:
        await callback.answer("Ошибка: пустой callback", show_alert=True)
        return

    action = callback.data.split(":", 1)[1]

    if action == "cancel":
        await state.clear()
        msg = callback.message
        if isinstance(msg, Message):
            await msg.edit_text("Отменено.")
        await callback.answer()
        return

    data = await state.get_data()
    text: str | None = data.get("text")
    if not text:
        await state.clear()
        await callback.answer("Сессия устарела. Отправь текст заново.", show_alert=True)
        return

    if action == "confirm":
        category_label: str | None = data.get("suggested_category")
    else:
        category_label = action

    user_id = _get_user_id(callback.from_user)
    msg = callback.message
    if isinstance(msg, Message):
        await msg.edit_text("Обрабатываю…")
    await callback.answer()

    try:
        response = await process_message(
            user_id=user_id, text=text, category=category_label, note_id=None
        )
    except Exception as exc:
        await state.clear()
        logger.exception("Process failed (callback) for user %s", user_id)
        if isinstance(msg, Message):
            await msg.edit_text(user_message_from_error(exc))
        return

    await state.clear()
    if isinstance(msg, Message):
        await _reply_with_process_result(msg, response)


@notes_router.callback_query(F.data.startswith("edit:"))
async def handle_edit_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data:
        await callback.answer("Ошибка", show_alert=True)
        return

    note_id = int(callback.data.split(":", 1)[1])
    await state.set_state(NoteAction.waiting_for_edit_text)
    await state.update_data(edit_note_id=note_id)
    msg = callback.message
    if isinstance(msg, Message):
        await msg.edit_text(
            f"✏️ Редактирование заметки ID {note_id}\n\nОтправь новый текст:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Отмена", callback_data="edit:cancel")],
                ]
            ),
        )
    await callback.answer()


@notes_router.callback_query(F.data == "edit:cancel")
async def handle_edit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    msg = callback.message
    if isinstance(msg, Message):
        await msg.edit_text("Отменено.")
    await callback.answer()


@notes_router.message(NoteAction.waiting_for_edit_text)
async def handle_edit_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    note_id: int | None = data.get("edit_note_id")
    if not note_id:
        await state.clear()
        await message.answer("Что-то пошло не так. Попробуй снова.")
        return

    new_text = message.text or ""
    user_id = _get_user_id(message.from_user)

    try:
        await update_message(user_id, note_id, new_text)
        await message.answer(f"✅ Заметка ID {note_id} обновлена!")
    except Exception as exc:
        logger.exception("Update failed for user %s", user_id)
        await message.answer(user_message_from_error(exc))
    await state.clear()


@notes_router.callback_query(F.data.startswith("delete:"))
async def handle_delete_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data:
        await callback.answer("Ошибка", show_alert=True)
        return

    note_id = int(callback.data.split(":", 1)[1])
    user_id = _get_user_id(callback.from_user)

    try:
        await delete_message(user_id, note_id)
        msg = callback.message
        if isinstance(msg, Message):
            await msg.edit_text(f"🗑 Заметка ID {note_id} удалена.")
    except Exception as exc:
        logger.exception("Delete failed for user %s", user_id)
        msg = callback.message
        if isinstance(msg, Message):
            await msg.edit_text(user_message_from_error(exc))
    await callback.answer()