from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import verify_telegram_init_data
from database import (
    ensure_db_schema_sync,
    init_db,
    sync_add_activity,
    sync_add_meal,
    sync_create_user,
    sync_get_activities_history,
    sync_get_meals_history,
    sync_get_today_activities,
    sync_get_today_meals,
    sync_get_user,
    sync_get_user_profile,
    sync_update_user_profile,
)
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
    description: str
    calories: float = 0.0
    protein: float = 0.0
    fat: float = 0.0
    carbs: float = 0.0


class TextAnalyzeRequest(BaseModel):
    text: str


class ActivityCreate(BaseModel):
    description: str
    calories_burned: float = 0.0
    duration_minutes: Optional[int] = None


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
    remaining = max(goal - net_calories, 0) if goal else 0

    return {
        "meals": meals,
        "activities": activities,
        "totals": totals,
        "total_burned": total_burned,
        "net_calories": net_calories,
        "goal_calories": goal,
        "remaining": remaining,
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

    activity_id = sync_add_activity(
        user_id=telegram_id,
        description=body.description,
        calories_burned=body.calories_burned,
        duration_minutes=body.duration_minutes,
    )

    return {
        "id": activity_id,
        "user_id": telegram_id,
        "description": body.description,
        "calories_burned": body.calories_burned,
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
    result = await openai_client.analyze_activity(body.text)
    return result
