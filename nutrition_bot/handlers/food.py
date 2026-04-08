"""
food.py — анализ еды (текст / фото / голос).
НЕ сохраняет в БД напрямую — сохраняет draft в FSM и передаёт управление meal_confirm.
"""

import logging
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import get_user
from handlers.meal_confirm import MealConfirmState, _format_meal_preview, _confirm_keyboard
from services.nutrition_db import calculate_meal
from services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

router = Router(name="food")
openai_client = OpenAIClient()


def _to_bytes(blob: object) -> bytes:
    if isinstance(blob, bytes):
        return blob
    if hasattr(blob, "read"):
        return blob.read()
    raise TypeError(f"Unsupported blob type: {type(blob)!r}")


async def _ensure_user(message: Message) -> bool:
    if message.from_user is None:
        return False

    user = await get_user(message.from_user.id)
    if user is not None:
        return True

    await message.answer("Сначала отправьте /start, чтобы создать профиль.")
    return False


async def _show_draft(
    message: Message,
    state: FSMContext,
    structure: dict,
    source_label: str,
) -> None:
    """Показывает карточку распознанной еды с кнопками Сохранить/Изменить/Отмена."""
    # Рассчитываем для превью
    meal_calc = calculate_meal(structure.get("items", []))

    # Сохраняем черновик в FSM
    await state.update_data(
        structure=structure,
        source_label=source_label,
    )
    await state.set_state(MealConfirmState.awaiting_confirmation)

    # Показываем превью
    preview = _format_meal_preview(structure, meal_calc)
    await message.answer(preview, reply_markup=_confirm_keyboard(), parse_mode="Markdown")

    logger.info(f"Draft saved: {source_label}, {len(structure.get('items', []))} items")


@router.message(StateFilter(None), F.photo)
async def handle_food_photo(message: Message, state: FSMContext) -> None:
    if not await _ensure_user(message):
        return

    progress = await message.answer("⏳ Анализирую фото...")
    try:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        image_file = await message.bot.download_file(file.file_path)
        image_bytes = _to_bytes(image_file)

        structure = await openai_client.analyze_food_photo(image_bytes)
    except Exception:
        logger.exception("Photo analysis failed")
        await progress.delete()
        await message.answer(
            "Не удалось обработать фото. Попробуй отправить его ещё раз через пару секунд."
        )
        return

    await progress.delete()
    await _show_draft(message, state, structure, source_label="Фото")


@router.message(StateFilter(None), F.voice)
async def handle_food_voice(message: Message, state: FSMContext) -> None:
    if not await _ensure_user(message):
        return

    progress = await message.answer("⏳ Распознаю голос...")
    try:
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        audio_file = await message.bot.download_file(file.file_path)
        audio_bytes = _to_bytes(audio_file)

        text = await openai_client.transcribe_voice(audio_bytes)
        structure = await openai_client.analyze_food_text(text)
    except Exception:
        logger.exception("Voice analysis failed")
        await progress.delete()
        await message.answer(
            "Не удалось обработать голосовое. Попробуй ещё раз через пару секунд."
        )
        return

    await progress.delete()
    await _show_draft(message, state, structure, source_label="Голос")


@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def handle_food_text(message: Message, state: FSMContext) -> None:
    if not message.text:
        return

    if not await _ensure_user(message):
        return

    progress = await message.answer("⏳ Анализирую текст...")
    try:
        structure = await openai_client.analyze_food_text(message.text)
    except Exception:
        logger.exception("Text analysis failed")
        await progress.delete()
        await message.answer(
            "Не удалось обработать запрос к OpenAI. Попробуй ещё раз через пару секунд."
        )
        return

    await progress.delete()
    await _show_draft(message, state, structure, source_label="Текст")
