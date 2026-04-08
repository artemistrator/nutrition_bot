from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database import add_activity, get_user
from services.activity import analyze_activity_text


router = Router(name="activity")


class ActivityState(StatesGroup):
    waiting_for_entry = State()


_ACTIVITY_HELP = (
    "Опиши активность одной строкой.\n\n"
    "Примеры:\n"
    "• бег 30 минут\n"
    "• ходьба 45 минут\n"
    "• велосипед 40 минут\n"
    "• плавание 20 минут\n"
    "• зал 60 минут"
)


async def _ensure_user(message: Message) -> dict | None:
    if message.from_user is None:
        return None

    user = await get_user(message.from_user.id)
    if user is not None:
        return user

    await message.answer("Сначала отправь /start, чтобы создать профиль.")
    return None


async def _save_activity_from_text(message: Message, state: FSMContext, raw_text: str) -> None:
    user = await _ensure_user(message)
    if user is None or message.from_user is None:
        return

    try:
        result = analyze_activity_text(raw_text, user.get("weight_kg"))
    except ValueError as exc:
        await message.answer(f"{exc}\n\n{_ACTIVITY_HELP}")
        await state.set_state(ActivityState.waiting_for_entry)
        return

    await add_activity(
        user_id=message.from_user.id,
        activity_type=result.activity_type,
        description=result.description,
        calories_burned=result.burned_calories,
        duration_minutes=result.duration_minutes,
    )
    await state.clear()
    await message.answer(
        f"🏃 {result.description}\n"
        f"Сожжено: ~{result.burned_calories} ккал ✅"
    )


@router.message(Command("activity"))
async def activity_command(message: Message, state: FSMContext) -> None:
    raw_text = (message.text or "").split(maxsplit=1)
    if len(raw_text) > 1 and raw_text[1].strip():
        await _save_activity_from_text(message, state, raw_text[1].strip())
        return

    await state.set_state(ActivityState.waiting_for_entry)
    await message.answer(_ACTIVITY_HELP)


@router.message(ActivityState.waiting_for_entry, F.text & ~F.text.startswith("/"))
async def handle_activity_entry(message: Message, state: FSMContext) -> None:
    await _save_activity_from_text(message, state, message.text or "")


@router.message(ActivityState.waiting_for_entry)
async def handle_activity_unexpected(message: Message) -> None:
    await message.answer("Опиши активность текстом, например: `бег 30 минут`.", parse_mode="Markdown")
