from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass
class MealAnalysis:
    description: str
    calories: float
    protein: float
    fat: float
    carbs: float


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_nutrition_response(raw: str | Mapping[str, Any]) -> MealAnalysis:
    """Парсит ответ от GPT (строку или dict) и возвращает MealAnalysis.

    Если raw — строка, обрабатывает JSON с ````json ... ```` обёрткой.
    Если raw — dict, берёт значения напрямую.
    При ошибке возвращает заглушку с нулями.
    """
    try:
        if isinstance(raw, Mapping):
            payload = raw
        else:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.find("\n")
                if first_newline != -1:
                    cleaned = cleaned[first_newline:]
                last_backticks = cleaned.rfind("```")
                if last_backticks != -1:
                    cleaned = cleaned[:last_backticks]
                cleaned = cleaned.strip()
            payload = json.loads(cleaned)

        return MealAnalysis(
            description=str(payload.get("description", "Приём пищи")).strip() or "Приём пищи",
            calories=_to_float(payload.get("calories")),
            protein=_to_float(payload.get("protein")),
            fat=_to_float(payload.get("fat")),
            carbs=_to_float(payload.get("carbs")),
        )
    except (json.JSONDecodeError, AttributeError, TypeError):
        return MealAnalysis(
            description="Не удалось распознать",
            calories=0.0,
            protein=0.0,
            fat=0.0,
            carbs=0.0,
        )


def calculate_daily_totals(meals: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    totals = {
        "calories": 0.0,
        "protein": 0.0,
        "fat": 0.0,
        "carbs": 0.0,
    }

    for meal in meals:
        totals["calories"] += _to_float(meal.get("calories"))
        totals["protein"] += _to_float(meal.get("protein"))
        totals["fat"] += _to_float(meal.get("fat"))
        totals["carbs"] += _to_float(meal.get("carbs"))

    return totals


def format_meal_confirmation(meal: MealAnalysis, source_label: str) -> str:
    return (
        f"{source_label}: запись добавлена.\n"
        f"{meal.description}\n"
        f"Калории: {meal.calories:.0f} ккал\n"
        f"Б: {meal.protein:.1f} г | Ж: {meal.fat:.1f} г | У: {meal.carbs:.1f} г"
    )
