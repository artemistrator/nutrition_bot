import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import get_settings
from database import init_db
from handlers import all_routers
from scheduler import run_scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    await init_db()
    settings = get_settings()
    settings.validate()

    bot = Bot(token=settings.telegram_token)
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)

    for router in all_routers:
        dispatcher.include_router(router)

    logging.info("Nutrition bot is starting...")

    # Запускаем планировщик уведомлений
    asyncio.create_task(run_scheduler())

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
