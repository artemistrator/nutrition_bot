from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import get_today_activities, get_today_meals, get_user
from services.nutrition import calculate_daily_totals


router = Router(name="stats")

_MONTH_NAMES = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


@router.message(Command("today"))
async def today_command(message: Message) -> None:
    if message.from_user is None:
        return

    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте /start, чтобы создать профиль.")
        return

    meals = await get_today_meals(message.from_user.id)
    activities = await get_today_activities(message.from_user.id)
    if not meals and not activities:
        await message.answer(
            "Сегодня ещё ничего не записано. Отправь еду или добавь активность через /activity."
        )
        return

    totals = calculate_daily_totals(meals)
    total_burned = sum(a.get("calories_burned", 0) or 0 for a in activities)
    goal = user.get("goal_calories") or 0

    now = datetime.now()
    date_str = f"{now.day} {_MONTH_NAMES[now.month - 1]}"

    meal_lines: list[str] = []
    for meal in meals:
        created = meal.get("created_at", "")
        time_str = created[11:16] if len(created) >= 16 else "??:??"
        desc = meal.get("description", "Приём пищи")
        kcal = meal.get("calories", 0)
        meal_lines.append(f"• {desc} ({time_str}) — {kcal:.0f} ккал")

    activity_lines: list[str] = []
    for activity in activities:
        created = activity.get("created_at", "")
        time_str = created[11:16] if len(created) >= 16 else "??:??"
        desc = activity.get("description", "Активность")
        burned = activity.get("calories_burned", 0)
        duration = activity.get("duration_minutes")
        duration_text = f", {duration} мин" if duration else ""
        activity_lines.append(f"• {desc} ({time_str}{duration_text}) — −{burned:.0f} ккал")

    net_calories = totals["calories"] - total_burned
    remaining = max(goal - net_calories, 0) if goal else 0

    parts = [f"📊 Сегодня, {date_str}:\n"]
    if meal_lines:
        parts.append("🍽 Еда:")
        parts.extend(meal_lines)
        parts.append("")

    if activity_lines:
        parts.append("🏃 Активности:")
        parts.extend(activity_lines)
        parts.append("")

    eaten_text = f"Съедено: {totals['calories']:.0f} ккал"
    burned_text = f"Сожжено: {total_burned:.0f} ккал"
    macros_text = (
        f"Б: {totals['protein']:.0f} г | Ж: {totals['fat']:.0f} г | У: {totals['carbs']:.0f} г"
    )

    if goal:
        parts.append(
            f"{eaten_text}\n"
            f"{burned_text}\n"
            f"Цель: {goal} ккал\n"
            f"{macros_text}\n\n"
            f"Осталось: {remaining:.0f} ккал"
        )
    else:
        parts.append(
            f"{eaten_text}\n"
            f"{burned_text}\n"
            f"{macros_text}"
        )

    await message.answer("\n".join(parts))
