from __future__ import annotations

from typing import Any


SEX_CHOICES = {"male", "female"}
ACTIVITY_MULTIPLIERS = {
    "low": 1.2,
    "medium": 1.375,
    "high": 1.55,
}
GOAL_TYPES = {"lose", "maintain", "gain"}

PROFILE_FIELDS = (
    "sex",
    "age",
    "height_cm",
    "weight_kg",
    "activity_level",
    "goal_type",
)


def normalize_profile_value(field: str, value: Any) -> Any:
    if value is None:
        return None

    if field in {"sex", "activity_level", "goal_type"}:
        text = str(value).strip().lower()
        return text or None

    if field == "age":
        if isinstance(value, str):
            value = value.strip()
        return int(value)

    if field in {"height_cm", "weight_kg"}:
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return float(value)

    return value


def validate_profile_field(field: str, value: Any) -> Any:
    normalized = normalize_profile_value(field, value)
    if normalized is None:
        return None

    if field == "sex":
        if normalized not in SEX_CHOICES:
            raise ValueError("Пол должен быть male или female.")
        return normalized

    if field == "activity_level":
        if normalized not in ACTIVITY_MULTIPLIERS:
            raise ValueError("Уровень активности должен быть low, medium или high.")
        return normalized

    if field == "goal_type":
        if normalized not in GOAL_TYPES:
            raise ValueError("Цель должна быть lose, maintain или gain.")
        return normalized

    if field == "age":
        if normalized < 10 or normalized > 100:
            raise ValueError("Возраст должен быть в диапазоне 10–100.")
        return normalized

    if field == "height_cm":
        if normalized < 100 or normalized > 250:
            raise ValueError("Рост должен быть в диапазоне 100–250 см.")
        return normalized

    if field == "weight_kg":
        if normalized < 30 or normalized > 300:
            raise ValueError("Вес должен быть в диапазоне 30–300 кг.")
        return normalized

    return normalized


def sanitize_profile_input(payload: dict[str, Any], *, partial: bool = True) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for field in PROFILE_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if value is None and partial:
            cleaned[field] = None
            continue
        cleaned[field] = validate_profile_field(field, value)

    if not partial:
        missing = [field for field in PROFILE_FIELDS if cleaned.get(field) is None]
        if missing:
            raise ValueError("Заполни все поля профиля.")

    return cleaned


def is_profile_complete(profile: dict[str, Any] | None) -> bool:
    if not profile:
        return False
    for field in PROFILE_FIELDS:
        if profile.get(field) is None:
            return False
    try:
        sanitize_profile_input({field: profile.get(field) for field in PROFILE_FIELDS}, partial=False)
    except (TypeError, ValueError):
        return False
    return True


def calculate_bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    if sex == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    if sex == "female":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    raise ValueError("Unknown sex.")


def calculate_goal_calories(profile: dict[str, Any]) -> int:
    cleaned = sanitize_profile_input(
        {field: profile.get(field) for field in PROFILE_FIELDS},
        partial=False,
    )

    sex = cleaned["sex"]
    age = cleaned["age"]
    height_cm = cleaned["height_cm"]
    weight_kg = cleaned["weight_kg"]
    activity_level = cleaned["activity_level"]
    goal_type = cleaned["goal_type"]

    bmr = calculate_bmr(sex, weight_kg, height_cm, age)
    tdee = bmr * ACTIVITY_MULTIPLIERS[activity_level]

    if goal_type == "lose":
        goal = tdee * 0.85
    elif goal_type == "gain":
        goal = tdee * 1.15
    else:
        goal = tdee

    minimum = 1400 if sex == "male" else 1200
    return max(round(goal), minimum)


def build_profile_meta(profile: dict[str, Any] | None) -> dict[str, Any]:
    if not profile:
        return {"profile_complete": False}

    result = dict(profile)
    result["profile_complete"] = is_profile_complete(result)
    return result
