from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - optional until dependencies are installed
    AsyncOpenAI = None


_JSON_PROMPT = (
    "Проанализируй приём пищи и верни результат строго в формате JSON с полями:\n"
    "- description: краткое описание блюда на русском языке\n"
    "- calories: калории (число)\n"
    "- protein: белки в граммах (число)\n"
    "- fat: жиры в граммах (число)\n"
    "- carbs: углеводы в граммах (число)\n"
    "Никакого дополнительного текста, только JSON."
)

_STRUCTURE_PROMPT = (
    "Ты — система извлечения структуры еды.\n"
    "Твоя задача — определить продукты и их примерный вес в граммах.\n"
    "Не считай калории и БЖУ.\n"
    "Отвечай строго в JSON без текста.\n\n"
    "Формат:\n"
    '{"items": [{"name": "string", "grams": number, "confidence": number (0-1)}]}\n\n'
    "Если не уверен в продукте — ставь confidence < 0.7.\n"
    "Оцени граммы по фото или описанию реалистично."
)

_ACTIVITY_PROMPT = (
    "Пользователь описал физическую активность. Верни JSON:\n"
    "{description, calories_burned, duration_minutes}\n"
    "calories_burned — приблизительный расход калорий для человека 70-80кг.\n"
    "Только JSON, никакого текста."
)


class OpenAIClient:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.client = (
            AsyncOpenAI(api_key=self.api_key, timeout=30.0, max_retries=0)
            if AsyncOpenAI and self.api_key
            else None
        )
        self.chat_model = "gpt-5.4-nano"
        self.vision_model = "gpt-5.4-nano"
        self.audio_model = "whisper-1"

    async def analyze_food_photo(self, image_bytes: bytes) -> dict[str, Any]:
        """Анализирует фото еды через gpt-4o vision и возвращает структуру: items."""
        if self.client is None:
            raise RuntimeError("OpenAI client not configured (no API key)")

        b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = await self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                        {"type": "text", "text": _STRUCTURE_PROMPT},
                    ],
                }
            ],
            max_completion_tokens=512,
        )

        raw = response.choices[0].message.content or ""
        logger.info(f"LLM (photo) → {raw}")
        return _extract_json(raw)

    async def analyze_food_text(self, text: str) -> dict[str, Any]:
        """Анализирует текст еды через gpt-4o и возвращает структуру: items."""
        if self.client is None:
            raise RuntimeError("OpenAI client not configured (no API key)")

        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": _STRUCTURE_PROMPT},
                {"role": "user", "content": text.strip()},
            ],
            max_completion_tokens=512,
        )

        raw = response.choices[0].message.content or ""
        logger.info(f"LLM (text) → {raw}")
        return _extract_json(raw)

    async def transcribe_voice(self, audio_bytes: bytes) -> str:
        """Транскрибирует голосовое сообщение через whisper-1."""
        if self.client is None:
            raise RuntimeError("OpenAI client not configured (no API key)")

        # Whisper требует файл — сохраняем во временный .ogg
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                response = await self.client.audio.transcriptions.create(
                    model=self.audio_model,
                    file=f,
                )
            return response.text
        finally:
            os.unlink(tmp_path)

    async def analyze_activity(self, text: str) -> dict[str, Any]:
        """Анализирует текстовое описание активности и возвращает JSON с расходом калорий."""
        if self.client is None:
            raise RuntimeError("OpenAI client not configured (no API key)")

        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": _ACTIVITY_PROMPT},
                {"role": "user", "content": text.strip()},
            ],
            max_completion_tokens=256,
        )

        raw = response.choices[0].message.content or ""
        return _extract_json(raw)


def _extract_json(raw: str) -> dict[str, Any]:
    """Извлекает JSON из ответа модели (убирает ```json ... ``` обёртку если есть)."""
    cleaned = raw.strip()

    # Убираем markdown-обёртку ```json ... ```
    if cleaned.startswith("```"):
        # Находим первую строку (может быть ````json` или просто ```json)
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline:]

        # Убираем закрывающие ```
        last_backticks = cleaned.rfind("```")
        if last_backticks != -1:
            cleaned = cleaned[:last_backticks]

        cleaned = cleaned.strip()

    return json.loads(cleaned)
