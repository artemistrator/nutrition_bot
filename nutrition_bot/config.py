import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    telegram_token: str
    openai_api_key: str
    database_path: Path
    bot_token: str

    def validate(self) -> None:
        if not self.telegram_token:
            raise ValueError(
                "TELEGRAM_TOKEN не задан в .env. "
                "Скопируйте .env.example в .env и укажите токен бота."
            )
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY не задан в .env. "
                "Скопируйте .env.example в .env и укажите ключ OpenAI."
            )
        if not self.bot_token:
            raise ValueError(
                "BOT_TOKEN не задан в .env. "
                "Скопируйте .env.example в .env и укажите токен бота."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        telegram_token=os.getenv("TELEGRAM_TOKEN", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        database_path=Path(
            os.getenv("DATABASE_PATH", str(BASE_DIR / "nutrition_bot.sqlite3"))
        ),
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
    )
