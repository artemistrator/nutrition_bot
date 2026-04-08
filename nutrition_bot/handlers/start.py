from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import create_user, get_user_profile, update_user_profile


router = Router(name="start")


SEX_LABELS = {
    "male": "Мужской",
    "female": "Женский",
}
ACTIVITY_LABELS = {
    "low": "Низкая активность",
    "medium": "Средняя активность",
    "high": "Высокая активность",
}
GOAL_LABELS = {
    "lose": "Похудение",
    "maintain": "Поддержание",
    "gain": "Набор массы",
}


class OnboardingState(StatesGroup):
    waiting_for_sex = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_activity = State()
    waiting_for_goal = State()


def _sex_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨 Мужской", callback_data="profile:sex:male")],
            [InlineKeyboardButton(text="👩 Женский", callback_data="profile:sex:female")],
        ]
    )


def _activity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛋 Низкая", callback_data="profile:activity:low")],
            [InlineKeyboardButton(text="🚶 Средняя", callback_data="profile:activity:medium")],
            [InlineKeyboardButton(text="🏃 Высокая", callback_data="profile:activity:high")],
        ]
    )


def _goal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Похудеть", callback_data="profile:goal:lose")],
            [InlineKeyboardButton(text="⚖️ Поддержать", callback_data="profile:goal:maintain")],
            [InlineKeyboardButton(text="💪 Набрать", callback_data="profile:goal:gain")],
        ]
    )


def _profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Обновить профиль", callback_data="profile:edit")],
        ]
    )


async def _prompt_sex(target: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingState.waiting_for_sex)
    await target.answer("Выбери пол:", reply_markup=_sex_keyboard())


async def _prompt_age(target: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingState.waiting_for_age)
    await target.answer("Сколько тебе лет? Напиши число от 10 до 100.")


async def _prompt_height(target: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingState.waiting_for_height)
    await target.answer("Какой у тебя рост? Напиши в сантиметрах, например `178`.", parse_mode="Markdown")


async def _prompt_weight(target: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingState.waiting_for_weight)
    await target.answer("Какой у тебя текущий вес? Напиши в килограммах, например `72.5`.", parse_mode="Markdown")


async def _prompt_activity(target: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingState.waiting_for_activity)
    await target.answer(
        "Какой у тебя уровень активности?",
        reply_markup=_activity_keyboard(),
    )


async def _prompt_goal(target: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingState.waiting_for_goal)
    await target.answer(
        "Какая у тебя цель?",
        reply_markup=_goal_keyboard(),
    )


async def _finish_profile_flow(target: Message, state: FSMContext, user: dict) -> None:
    await state.clear()
    goal_calories = user.get("goal_calories")
    if goal_calories:
        await target.answer(
            "Готово ✅\n"
            f"Твоя дневная цель: {goal_calories} ккал",
            reply_markup=_profile_keyboard(),
        )
        return
    await target.answer(
        "Профиль сохранён, но для расчёта цели не хватает данных. "
        "Проверь поля через /profile.",
        reply_markup=_profile_keyboard(),
    )


def _format_profile_summary(user: dict) -> str:
    sex = SEX_LABELS.get(user.get("sex"), "не указан")
    activity = ACTIVITY_LABELS.get(user.get("activity_level"), "не указана")
    goal = GOAL_LABELS.get(user.get("goal_type"), "не указана")
    age = user.get("age") or "—"
    height_cm = user.get("height_cm") or "—"
    weight_kg = user.get("weight_kg") or "—"
    goal_calories = user.get("goal_calories")
    goal_text = f"{goal_calories} ккал/день" if goal_calories else "пока не рассчитана"

    return (
        "Твой профиль:\n"
        f"• Пол: {sex}\n"
        f"• Возраст: {age}\n"
        f"• Рост: {height_cm}\n"
        f"• Вес: {weight_kg}\n"
        f"• Активность: {activity}\n"
        f"• Цель: {goal}\n\n"
        f"Дневная цель: {goal_text}"
    )


async def _ensure_user(message: Message) -> dict | None:
    if message.from_user is None:
        return None
    user = await get_user_profile(message.from_user.id)
    if user is not None:
        return user
    return await create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )


async def _ask_next_profile_step(target: Message, state: FSMContext, user: dict) -> None:
    if user.get("sex") is None:
        await _prompt_sex(target, state)
        return

    if user.get("age") is None:
        await _prompt_age(target, state)
        return

    if user.get("height_cm") is None:
        await _prompt_height(target, state)
        return

    if user.get("weight_kg") is None:
        await _prompt_weight(target, state)
        return

    if user.get("activity_level") is None:
        await _prompt_activity(target, state)
        return

    if user.get("goal_type") is None:
        await _prompt_goal(target, state)
        return

    await _finish_profile_flow(target, state, user)


async def _refresh_user(user_id: int) -> dict | None:
    return await get_user_profile(user_id)


async def _save_profile_update(message: Message, payload: dict) -> dict | None:
    if message.from_user is None:
        return None
    try:
        await update_user_profile(message.from_user.id, payload)
    except ValueError as exc:
        await message.answer(str(exc))
        return None

    user = await _refresh_user(message.from_user.id)
    if user is None:
        await message.answer("Не удалось обновить профиль. Попробуй ещё раз через минуту.")
        return None
    return user


def _onboarding_help_text(state_name: str | None) -> str:
    prompts = {
        OnboardingState.waiting_for_sex.state: "Выбери пол кнопкой ниже.",
        OnboardingState.waiting_for_age.state: "Напиши возраст числом от 10 до 100.",
        OnboardingState.waiting_for_height.state: "Напиши рост в сантиметрах, например `178`.",
        OnboardingState.waiting_for_weight.state: "Напиши вес в килограммах, например `72` или `72.5`.",
        OnboardingState.waiting_for_activity.state: "Выбери уровень активности кнопкой ниже.",
        OnboardingState.waiting_for_goal.state: "Выбери цель кнопкой ниже.",
    }
    return prompts.get(state_name, "Продолжим заполнение профиля. Следуй подсказке выше.")


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    user = await _ensure_user(message)
    if user is None:
        return

    if user.get("profile_complete") and user.get("goal_calories"):
        await state.clear()
        await message.answer(
            "Привет ещё раз! 👋\n"
            f"Твоя текущая цель: **{user['goal_calories']} ккал/день**.\n"
            "Отправляй фото еды, голосовое или напиши что съел!",
            reply_markup=_profile_keyboard(),
            parse_mode="Markdown",
        )
        return

    await message.answer(
        "Привет! 👋 Я бот для учёта питания.\n"
        "Давай настроим профиль и рассчитаем твою дневную цель калорий."
    )
    await _ask_next_profile_step(message, state, user)


@router.message(Command("profile"))
async def profile_command(message: Message, state: FSMContext) -> None:
    user = await _ensure_user(message)
    if user is None:
        return

    await message.answer(_format_profile_summary(user), reply_markup=_profile_keyboard())
    if not user.get("profile_complete"):
        await message.answer("Профиль заполнен не до конца. Давай закончим настройку.")
        await _ask_next_profile_step(message, state, user)


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if not current_state:
        await message.answer("Сейчас нечего отменять.")
        return

    await state.clear()
    await message.answer("Текущее действие отменено. Теперь можно снова отправлять еду или использовать команды.")


@router.callback_query(F.data == "profile:edit")
async def handle_profile_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    user = await get_user_profile(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправь /start", show_alert=True)
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer("Обновим профиль по шагам.")
        await _prompt_sex(callback.message, state)


@router.callback_query(F.data.startswith("profile:sex:"))
async def handle_sex_selection(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or callback.data is None or callback.message is None:
        return
    sex = callback.data.rsplit(":", 1)[1]
    try:
        await update_user_profile(callback.from_user.id, {"sex": sex})
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.answer("Пол сохранён")
    await _prompt_age(callback.message, state)


@router.callback_query(F.data.startswith("profile:activity:"))
async def handle_activity_selection(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or callback.data is None or callback.message is None:
        return
    activity_level = callback.data.rsplit(":", 1)[1]
    try:
        await update_user_profile(callback.from_user.id, {"activity_level": activity_level})
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.answer("Активность сохранена")
    await _prompt_goal(callback.message, state)


@router.callback_query(F.data.startswith("profile:goal:"))
async def handle_goal_selection(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or callback.data is None or callback.message is None:
        return
    goal_type = callback.data.rsplit(":", 1)[1]
    try:
        updated = await update_user_profile(callback.from_user.id, {"goal_type": goal_type})
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await state.clear()
    await callback.answer("Цель сохранена")
    await _finish_profile_flow(callback.message, state, updated)


@router.message(OnboardingState.waiting_for_age, F.text)
async def handle_age(message: Message, state: FSMContext) -> None:
    user = await _save_profile_update(message, {"age": message.text})
    if user is not None:
        await _prompt_height(message, state)


@router.message(OnboardingState.waiting_for_height, F.text)
async def handle_height(message: Message, state: FSMContext) -> None:
    user = await _save_profile_update(message, {"height_cm": message.text})
    if user is not None:
        await _prompt_weight(message, state)


@router.message(OnboardingState.waiting_for_weight, F.text)
async def handle_weight(message: Message, state: FSMContext) -> None:
    user = await _save_profile_update(message, {"weight_kg": message.text})
    if user is not None:
        await _prompt_activity(message, state)


@router.message(OnboardingState.waiting_for_sex, F.text)
@router.message(OnboardingState.waiting_for_activity, F.text)
@router.message(OnboardingState.waiting_for_goal, F.text)
async def handle_choice_text(message: Message) -> None:
    await message.answer("Выбери вариант кнопкой ниже, чтобы я не ошибся.")


@router.message(
    OnboardingState.waiting_for_sex,
    OnboardingState.waiting_for_age,
    OnboardingState.waiting_for_height,
    OnboardingState.waiting_for_weight,
    OnboardingState.waiting_for_activity,
    OnboardingState.waiting_for_goal,
)
async def handle_onboarding_unexpected_input(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    await message.answer(_onboarding_help_text(current_state), parse_mode="Markdown")
