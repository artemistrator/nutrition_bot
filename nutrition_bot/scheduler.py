from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

from config import get_settings
from database import (
    get_today_totals,
    get_user_goal_calories,
    get_users_for_notifications,
    has_sent_notification_today,
    log_notification,
)

logger = logging.getLogger(__name__)

# ── Notification logic ────────────────────────────────────────────

def build_evening_notification(
    today_totals: dict,
    goal_calories: Optional[int],
) -> tuple[str, str] | None:
    """Выбирает текст уведомления по приоритету.

    Priority: no_meals > over_goal > under_goal

    Returns:
        (text, notif_type) or None if no notification needed.
    """
    meals_count = today_totals.get("meals_count", 0)
    calories = today_totals.get("calories", 0)

    # 1. Нет записей
    if meals_count == 0:
        return "🍽 Ты сегодня ещё не записал еду.", "no_meals"

    # Если цели нет — больше ничего не шлём
    if goal_calories is None or goal_calories <= 0:
        return None

    # 2. Перебор (>120%)
    if calories > goal_calories * 1.2:
        return (
            f"🔴 Сегодня уже {calories:.0f} из {goal_calories} ккал.\n"
            f"Похоже, цель превышена — проверь дневник."
        ), "over_goal"

    # 3. Недобор (<60%)
    if calories < goal_calories * 0.6:
        return (
            f"📉 Сегодня пока только {calories:.0f} из {goal_calories} ккал.\n"
            f"Если ещё будешь есть — не забудь записать 👌"
        ), "under_goal"

    # В пределах нормы — не беспокоим
    return None


# ── Scheduler ─────────────────────────────────────────────────────

async def send_evening_reminder() -> None:
    """Отправляет умные уведомления в 20:00."""
    bot = Bot(token=get_settings().bot_token)
    users = await get_users_for_notifications()

    sent = 0
    skipped = 0
    errors = 0

    for user in users:
        telegram_id = user["telegram_id"]

        try:
            # Проверка дубликатов
            if await has_sent_notification_today(telegram_id):
                logger.debug(f"User {telegram_id}: уже было уведомление сегодня — пропускаю")
                skipped += 1
                continue

            # Собираем данные
            totals = await get_today_totals(telegram_id)
            goal = await get_user_goal_calories(telegram_id)

            # Выбираем уведомление
            result = build_evening_notification(totals, goal)
            if result is None:
                logger.debug(f"User {telegram_id}: уведомление не требуется (cal={totals['calories']:.0f}, goal={goal})")
                skipped += 1
                continue

            text, notif_type = result

            # Отправляем
            await bot.send_message(chat_id=telegram_id, text=text)

            # Логируем
            await log_notification(telegram_id, notif_type)
            logger.info(f"✅ User {telegram_id}: отправлено [{notif_type}] — {text[:50]}...")
            sent += 1

            # Не спамим Telegram API
            await asyncio.sleep(0.1)

        except TelegramError as e:
            errors += 1
            if "bot was blocked" in str(e).lower() or "forbidden" in str(e).lower():
                logger.warning(f"User {telegram_id}: заблокировал бота — пропускаю ({e})")
            else:
                logger.error(f"User {telegram_id}: ошибка Telegram API ({e})")

        except Exception as e:
            errors += 1
            logger.error(f"User {telegram_id}: неожиданная ошибка ({e})")

    logger.info(f"Evening reminder done: sent={sent}, skipped={skipped}, errors={errors}")
    await bot.session.close()


async def run_scheduler() -> None:
    while True:
        now = datetime.now()
        if now.hour == 20 and now.minute == 0:
            logger.info("Scheduler trigger: 20:00 — sending evening reminders")
            await send_evening_reminder()
            await asyncio.sleep(60)  # ждём минуту чтоб не отправить дважды
        await asyncio.sleep(30)  # проверяем каждые 30 секунд
