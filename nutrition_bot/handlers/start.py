from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import create_user, get_user, update_user_goal


router = Router(name="start")


class OnboardingState:
    waiting_for_goal = "waiting_for_goal"


GOAL_MAP = {
    "lose": ("🔥 Похудеть", 1500),
    "maintain": ("⚖️ Поддержать вес", 2000),
    "gain": ("💪 Набрать массу", 2500),
}


def _goal_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"goal:{key}")]
        for key, (label, _) in GOAL_MAP.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    user = await get_user(message.from_user.id)

    if user is not None and user.get("goal_calories"):
        await message.answer(
            f"Привет ещё раз! 👋\n"
            f"Твоя текущая цель: **{user['goal_calories']} ккал/день**.\n"
            f"Отправляй фото еды, голосовое или напиши что съел!"
        )
        return

    await message.answer(
        "Привет! 👋 Я бот для учёта питания.\n"
        "Давай настроим твою цель. Выбери, что тебе подходит:",
        reply_markup=_goal_keyboard(),
    )
    await state.set_state(OnboardingState.waiting_for_goal)


@router.callback_query(F.data.startswith("goal:"))
async def handle_goal_selection(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or callback.data is None:
        return

    goal_key = callback.data.split(":", 1)[1]
    if goal_key not in GOAL_MAP:
        return

    label, goal_calories = GOAL_MAP[goal_key]

    user = await get_user(callback.from_user.id)
    if user is None:
        await create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            goal_calories=goal_calories,
        )
    else:
        await update_user_goal(callback.from_user.id, goal_calories)

    await state.clear()

    await callback.message.edit_text(
        f"Отлично! 🎯 Твоя цель: **{goal_calories} ккал/день**.\n\n"
        f"Отправляй фото еды, голосовое или просто напиши что съел — "
        f"я посчитаю калории и БЖУ."
    )
    await callback.answer()
