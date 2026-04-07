from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import get_today_meals, get_user
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
    if not meals:
        await message.answer(
            "Сегодня ещё ничего не записано. Отправь фото или напиши что съел! 🍽"
        )
        return

    totals = calculate_daily_totals(meals)
    goal = user.get("goal_calories") or 0

    now = datetime.now()
    date_str = f"{now.day} {_MONTH_NAMES[now.month - 1]}"

    meal_lines = []
    for meal in meals:
        created = meal.get("created_at", "")
        time_str = created[11:16] if len(created) >= 16 else "??:??"
        desc = meal.get("description", "Приём пищи")
        kcal = meal.get("calories", 0)
        meal_lines.append(f"• {desc} ({time_str}) — {kcal:.0f} ккал")

    remaining = max(goal - totals["calories"], 0) if goal else 0

    parts = [f"📊 Сегодня, {date_str}:\n"]
    parts.extend(meal_lines)
    parts.append("")

    if goal:
        parts.append(
            f"Итого: {totals['calories']:.0f} / {goal} ккал\n"
            f"Б: {totals['protein']:.0f} г | Ж: {totals['fat']:.0f} г | У: {totals['carbs']:.0f} г\n\n"
            f"Осталось: {remaining:.0f} ккал"
        )
    else:
        parts.append(
            f"Итого: {totals['calories']:.0f} ккал\n"
            f"Б: {totals['protein']:.0f} г | Ж: {totals['fat']:.0f} г | У: {totals['carbs']:.0f} г"
        )

    await message.answer("\n".join(parts))
