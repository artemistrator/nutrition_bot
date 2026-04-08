from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Path as FastAPIPath, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from auth import verify_telegram_init_data
from database import (
    sync_delete_meal,
    ensure_db_schema_sync,
    init_db,
    sync_add_activity,
    sync_add_meal,
    sync_get_meal_template,
    sync_create_user,
    sync_get_activities_history,
    sync_get_meal_by_id,
    sync_get_meals_history,
    sync_get_today_activities,
    sync_get_today_meals,
    sync_get_user,
    sync_get_user_profile,
    sync_list_meal_templates,
    sync_update_meal,
    sync_update_user_profile,
)
from services.activity import ACTIVITY_METS, analyze_activity_text, build_activity_description, calculate_burned_calories
from services.nutrition import calculate_daily_totals
from services.nutrition_db import calculate_meal
from services.openai_client import OpenAIClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


ensure_db_schema_sync()

# ── Auth dependency ──────────────────────────────────────────────

async def get_current_user(x_init_data: Optional[str] = Header(default=None)) -> dict:
    if not x_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Init-Data header")
    user = verify_telegram_init_data(x_init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    return user


# ── Pydantic models ──────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    sex: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    goal_type: Optional[str] = None


class MealCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    calories: float = Field(default=0.0, ge=0, le=5000)
    protein: float = Field(default=0.0, ge=0, le=500)
    fat: float = Field(default=0.0, ge=0, le=500)
    carbs: float = Field(default=0.0, ge=0, le=500)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Название записи не может быть пустым.")
        return value


class MealUpdate(MealCreate):
    pass


class TextAnalyzeRequest(BaseModel):
    text: str


class ActivityCreate(BaseModel):
    activity_type: str
    duration_minutes: int = Field(ge=1, le=600)
    description: Optional[str] = Field(default=None, max_length=200)

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ACTIVITY_METS:
            raise ValueError("Неизвестный тип активности.")
        return normalized

    @field_validator("description")
    @classmethod
    def validate_activity_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Описание активности не может быть пустым.")
        return cleaned


# ── App setup ────────────────────────────────────────────────────

app = FastAPI(title="Nutrition Bot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared OpenAI client (async — we'll run its calls in the event loop)
openai_client = OpenAIClient()


# ── Profile routes ───────────────────────────────────────────────

@app.get("/profile")
def get_profile(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    telegram_id = user['id']
    db_user = sync_get_user_profile(telegram_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/profile")
def update_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user['id']
    db_user = sync_get_user_profile(telegram_id)
    if db_user is None:
        sync_create_user(
            telegram_id=telegram_id,
            username=user.get("username"),
        )

    try:
        updated = sync_update_user_profile(
            telegram_id,
            {
                "sex": body.sex,
                "age": body.age,
                "height_cm": body.height_cm,
                "weight_kg": body.weight_kg,
                "activity_level": body.activity_level,
                "goal_type": body.goal_type,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return updated


# ── Meals: today ─────────────────────────────────────────────────

@app.get("/meals/today")
def get_today_meals(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    telegram_id = user['id']
    db_user = sync_get_user(telegram_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    meals = sync_get_today_meals(telegram_id)
    activities = sync_get_today_activities(telegram_id)
    totals = calculate_daily_totals(meals)
    total_burned = sum(a.get("calories_burned", 0) or 0 for a in activities)
    net_calories = totals["calories"] - total_burned

    goal = db_user.get("goal_calories") or 0
    remaining = goal - net_calories if goal else 0

    return {
        "meals": meals,
        "activities": activities,
        "totals": totals,
        "total_burned": total_burned,
        "net_calories": net_calories,
        "goal_calories": goal,
        "remaining": remaining,
    }


@app.get("/templates")
def get_templates(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    telegram_id = user["id"]
    rows = sync_list_meal_templates(telegram_id)
    templates = []
    for row in rows:
        structure = None
        try:
            structure = row.get("structure")  # sync rows do not include it
        except AttributeError:
            structure = None
        if structure is None:
            template = sync_get_meal_template(row["id"], telegram_id)
        else:
            template = row
        if template is None:
            continue
        meal_calc = calculate_meal((template.get("structure") or {}).get("items", []))
        templates.append({
            "id": template["id"],
            "title": template["title"],
            "created_at": template["created_at"],
            "calories": meal_calc["calories"],
            "protein": meal_calc["protein"],
            "fat": meal_calc["fat"],
            "carbs": meal_calc["carbs"],
        })
    return {"templates": templates}


@app.post("/templates/{template_id}/use")
def use_template(
    template_id: int = FastAPIPath(ge=1),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user["id"]
    template = sync_get_meal_template(template_id, telegram_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    structure = template.get("structure")
    if not structure:
        raise HTTPException(status_code=422, detail="Template structure is invalid")

    meal_calc = calculate_meal(structure.get("items", []))
    meal_id = sync_add_meal(
        user_id=telegram_id,
        description=template["title"],
        calories=meal_calc["calories"],
        protein=meal_calc["protein"],
        fat=meal_calc["fat"],
        carbs=meal_calc["carbs"],
    )
    return {
        "id": meal_id,
        "template_id": template_id,
        "description": template["title"],
        "calories": meal_calc["calories"],
        "protein": meal_calc["protein"],
        "fat": meal_calc["fat"],
        "carbs": meal_calc["carbs"],
    }


# ── Meals: create ────────────────────────────────────────────────

@app.post("/meals")
def create_meal(
    body: MealCreate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user['id']
    db_user = sync_get_user(telegram_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    meal_id = sync_add_meal(
        user_id=telegram_id,
        description=body.description,
        calories=body.calories,
        protein=body.protein,
        fat=body.fat,
        carbs=body.carbs,
    )

    return {
        "id": meal_id,
        "user_id": telegram_id,
        "description": body.description,
        "calories": body.calories,
        "protein": body.protein,
        "fat": body.fat,
        "carbs": body.carbs,
    }


@app.put("/meals/{meal_id}")
def update_meal_entry(
    meal_id: int = FastAPIPath(ge=1),
    body: MealUpdate = ...,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user['id']
    meal = sync_update_meal(
        meal_id=meal_id,
        telegram_user_id=telegram_id,
        description=body.description,
        calories=body.calories,
        protein=body.protein,
        fat=body.fat,
        carbs=body.carbs,
    )
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal not found")
    return meal


@app.delete("/meals/{meal_id}")
def delete_meal_entry(
    meal_id: int = FastAPIPath(ge=1),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user['id']
    existing = sync_get_meal_by_id(meal_id, telegram_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Meal not found")

    deleted = sync_delete_meal(meal_id, telegram_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meal not found")
    return {"ok": True, "deleted_id": meal_id}


# ── Meals: history ───────────────────────────────────────────────

@app.get("/meals/history")
def get_meals_history(
    days: int = Query(default=7, ge=1, le=90),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user['id']
    db_user = sync_get_user(telegram_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    rows = sync_get_meals_history(telegram_id, days)
    activity_rows = sync_get_activities_history(telegram_id, days)

    # Merge burned data by date
    burned_map = {r["date"]: r["calories_burned"] for r in activity_rows}
    for row in rows:
        row["calories_burned"] = burned_map.get(row["date"], 0)

    return {"days": rows}


# ── Activities ───────────────────────────────────────────────────

@app.get("/activities/today")
def get_today_activities(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    telegram_id = user['id']
    activities = sync_get_today_activities(telegram_id)
    total_burned = sum(a.get("calories_burned", 0) or 0 for a in activities)
    return {"activities": activities, "total_burned": total_burned}


@app.post("/activities")
def create_activity(
    body: ActivityCreate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user['id']
    db_user = sync_get_user(telegram_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        calories_burned = calculate_burned_calories(
            body.activity_type,
            db_user.get("weight_kg"),
            body.duration_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    description = body.description or build_activity_description(
        body.activity_type,
        body.duration_minutes,
    )

    activity_id = sync_add_activity(
        user_id=telegram_id,
        activity_type=body.activity_type,
        description=description,
        calories_burned=calories_burned,
        duration_minutes=body.duration_minutes,
    )

    return {
        "id": activity_id,
        "user_id": telegram_id,
        "activity_type": body.activity_type,
        "description": description,
        "calories_burned": calories_burned,
        "duration_minutes": body.duration_minutes,
    }


# ── Analyze (no save) ────────────────────────────────────────────

@app.post("/analyze/text")
async def analyze_text(
    body: TextAnalyzeRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    structure = await openai_client.analyze_food_text(body.text)
    result = calculate_meal(structure.get("items", []))
    return result


@app.post("/analyze/photo")
async def analyze_photo(
    file: UploadFile,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    data = await file.read()
    structure = await openai_client.analyze_food_photo(data)
    result = calculate_meal(structure.get("items", []))
    return result


@app.post("/analyze/activity")
async def analyze_activity(
    body: TextAnalyzeRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    telegram_id = user["id"]
    db_user = sync_get_user(telegram_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = analyze_activity_text(body.text, db_user.get("weight_kg"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "activity_type": result.activity_type,
        "description": result.description,
        "calories_burned": result.burned_calories,
        "duration_minutes": result.duration_minutes,
    }
