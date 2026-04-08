from __future__ import annotations

import re
from dataclasses import dataclass


ACTIVITY_METS = {
    "walking": 3.5,
    "running": 8.0,
    "cycling": 6.0,
    "swimming": 6.0,
    "workout": 5.0,
}

ACTIVITY_LABELS = {
    "walking": "Ходьба",
    "running": "Бег",
    "cycling": "Велосипед",
    "swimming": "Плавание",
    "workout": "Тренировка",
}

_ACTIVITY_ALIASES = {
    "walking": ("ходьба", "ходил", "ходила", "walking", "walk"),
    "running": ("бег", "пробежка", "бежал", "бежала", "running", "run"),
    "cycling": ("велосипед", "велотренажер", "велотренажёр", "cycling", "bike"),
    "swimming": ("плавание", "бассейн", "swimming", "swim"),
    "workout": ("зал", "тренировка", "силовая", "воркаут", "workout", "gym"),
}

_MINUTE_PATTERN = re.compile(r"(?P<value>\d{1,3})\s*(?:мин|минута|минуты|минут)\b", re.IGNORECASE)
_HOUR_PATTERN = re.compile(r"(?P<value>\d{1,2}(?:[.,]\d+)?)\s*(?:час|часа|часов)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ActivityAnalysis:
    activity_type: str
    duration_minutes: int
    burned_calories: int
    description: str


def normalize_activity_text(text: str) -> str:
    cleaned = text.strip().lower().replace("ё", "е")
    cleaned = cleaned.replace("—", "-").replace("–", "-")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def parse_activity_type(text: str) -> str:
    normalized = normalize_activity_text(text)
    for activity_type, aliases in _ACTIVITY_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return activity_type
    raise ValueError(
        "Не понял тип активности. Поддерживаю: ходьба, бег, велосипед, плавание и зал."
    )


def parse_duration_minutes(text: str) -> int:
    normalized = normalize_activity_text(text)

    minute_match = _MINUTE_PATTERN.search(normalized)
    if minute_match:
        value = int(minute_match.group("value"))
        return _validate_duration(value)

    hour_match = _HOUR_PATTERN.search(normalized)
    if hour_match:
        value = float(hour_match.group("value").replace(",", "."))
        return _validate_duration(round(value * 60))

    raise ValueError("Не вижу длительность. Напиши, например: `бег 30 минут`.")


def _validate_duration(duration_minutes: int) -> int:
    if duration_minutes < 1 or duration_minutes > 600:
        raise ValueError("Длительность должна быть от 1 до 600 минут.")
    return duration_minutes


def build_activity_description(activity_type: str, duration_minutes: int) -> str:
    label = ACTIVITY_LABELS[activity_type]
    return f"{label} — {duration_minutes} мин"


def calculate_burned_calories(
    activity_type: str,
    weight_kg: float | int | None,
    duration_minutes: int,
) -> int:
    if weight_kg is None or float(weight_kg) <= 0:
        raise ValueError("Укажи вес в профиле, чтобы я мог посчитать расход калорий.")
    if activity_type not in ACTIVITY_METS:
        raise ValueError("Неизвестный тип активности.")

    duration_minutes = _validate_duration(int(duration_minutes))
    hours = duration_minutes / 60
    burned = ACTIVITY_METS[activity_type] * float(weight_kg) * hours
    return max(round(burned), 1)


def analyze_activity_text(text: str, weight_kg: float | int | None) -> ActivityAnalysis:
    if not text or not text.strip():
        raise ValueError("Напиши активность, например: `ходьба 45 минут`.")

    activity_type = parse_activity_type(text)
    duration_minutes = parse_duration_minutes(text)
    burned_calories = calculate_burned_calories(activity_type, weight_kg, duration_minutes)
    return ActivityAnalysis(
        activity_type=activity_type,
        duration_minutes=duration_minutes,
        burned_calories=burned_calories,
        description=build_activity_description(activity_type, duration_minutes),
    )
